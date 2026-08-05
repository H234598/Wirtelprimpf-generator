"""Strict story-blueprint validation and restart-safe planning primitives."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from random import Random
from typing import Any

STORY_BLUEPRINT_VERSION = "story-blueprint/v1"
STORY_STATE_VERSION = "story-state/v1"
REQUIRED_CHARACTER_IDS = frozenset({"weisspfote", "schwarzkralle", "moehre", "maus"})
MOEHRE_BONUSES = {
    "list_subversivitaet": 2,
    "planung": 1,
    "einfallsreichtum": 1,
    "handwerk": 1,
    "beamten_tarnung": 1,
    "support": 4,
}
MOEHRE_MALUSES = {
    "angst_schreckhaftigkeit": 2,
    "quengeln": 0.5,
    "befuerchtungen_vorahnungen": 4,
    "geistige_blockiertheit": 2,
    "vergesslichkeit": 0.5,
}
MAUS_BONUSES = {
    "intelligenz": 3,
    "it_faehigkeiten": 5,
    "aussehen_tanz_charme": 2,
    "hyperfokus": 3,
    "geistiger_geschmack": 2,
    "rettung_aus_dummen_aktionen": 4.5,
    "glueck": 2,
    "fuersorge": 3,
}
MAUS_MALUSES = {
    "nichtzuhoeren_vergesslichkeit": 3,
    "ablenkbarkeit": 3,
    "gefaehrliche_aktionen": 3,
    "tanzen_beenden": 1,
    "wichtige_details": 2,
    "zu_viel_reden": 2,
    "selbstverliebtheit": 2,
    "linksradikal": 1,
}
AUTHORITY_START_MALUSES = {"dummheit": 5, "fahrlaessigkeit": 6, "selbstverliebtheit": 3}
CAT_TRAIT_COUNTS = {"bonuses": 8, "maluses": 5}
DECISION_TAGS = frozenset(
    {"virtue", "diligence", "immoral", "friendship", "danger", "swimming", "cheese", "not_swimming"}
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "blueprint_version",
        "story_id",
        "title_seed",
        "length",
        "style",
        "lesson",
        "ending",
        "cast",
        "world",
        "authorities",
        "beats",
        "risk_policy",
        "continuation",
        "seed",
        "skill_refs",
    }
)


class StoryBlueprintError(ValueError):
    """Raised when a blueprint or checkpoint violates its versioned contract."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StoryBlueprintError(f"{label} must be an object")
    return value


def _non_empty_string(value: object, label: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise StoryBlueprintError(f"{label} must be a non-empty string of at most {maximum} characters")
    return value


def _integer(value: object, label: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise StoryBlueprintError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise StoryBlueprintError(f"{label} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise StoryBlueprintError(f"{label} must be at most {maximum}")
    return value


def _numeric_map(value: object, label: str) -> None:
    for key, item in _mapping(value, label).items():
        _non_empty_string(key, f"{label} key")
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise StoryBlueprintError(f"{label}.{key} must be numeric")


def _exact_numeric_map(value: object, expected: Mapping[str, int | float], label: str) -> None:
    _numeric_map(value, label)
    if dict(value) != dict(expected):
        raise StoryBlueprintError(f"{label} does not match the versioned start values")


def select_bounded_traits(seed: str, character_id: str, catalog: object) -> dict[str, dict[str, int | float]]:
    """Select reproducible cat traits from an explicitly supplied bounded catalog."""

    _non_empty_string(seed, "trait selection seed", maximum=512)
    if character_id not in {"weisspfote", "schwarzkralle"}:
        raise StoryBlueprintError("bounded random traits are only for the two cats")
    source = _mapping(catalog, "trait catalog")
    bonus_source = _mapping(source.get("bonuses"), "trait catalog.bonuses")
    malus_source = _mapping(source.get("maluses"), "trait catalog.maluses")
    _numeric_map(bonus_source, "trait catalog.bonuses")
    _numeric_map(malus_source, "trait catalog.maluses")
    if len(bonus_source) < CAT_TRAIT_COUNTS["bonuses"] or len(malus_source) < CAT_TRAIT_COUNTS["maluses"]:
        raise StoryBlueprintError("trait catalog is too small for the required cat selections")
    rng = Random(f"{seed}:{character_id}")  # nosec B311
    bonus_keys = rng.sample(sorted(bonus_source), CAT_TRAIT_COUNTS["bonuses"])
    malus_keys = rng.sample(sorted(malus_source), CAT_TRAIT_COUNTS["maluses"])
    return {
        "bonuses": {key: bonus_source[key] for key in bonus_keys},
        "maluses": {key: malus_source[key] for key in malus_keys},
    }


def choose_decision(options: object) -> dict[str, Any]:
    """Choose the highest-priority option without asking a runtime question."""

    if not isinstance(options, list) or not options:
        raise StoryBlueprintError("decision options must be a non-empty list")
    seen_ids: set[str] = set()
    ranked: list[tuple[tuple[int, int, int], int, dict[str, Any]]] = []
    for index, option in enumerate(options):
        item = dict(_mapping(option, "decision option"))
        option_id = _non_empty_string(item.get("id"), "decision option.id", maximum=128)
        if option_id in seen_ids:
            raise StoryBlueprintError(f"duplicate decision option: {option_id}")
        seen_ids.add(option_id)
        tags = item.get("priorities")
        if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) for tag in tags):
            raise StoryBlueprintError("decision option.priorities must contain tags")
        unknown = set(tags) - DECISION_TAGS
        if unknown:
            raise StoryBlueprintError(f"unknown decision priority tags: {sorted(unknown)}")
        first_axis = max(
            3 if tag == "virtue" else 2 if tag == "diligence" else 1 if tag == "immoral" else 0
            for tag in tags
        )
        second_axis = max((2 if tag == "friendship" else 1 if tag == "danger" else 0) for tag in tags)
        third_axis = max(
            3 if tag == "swimming" else 2 if tag == "cheese" else 1 if tag == "not_swimming" else 0
            for tag in tags
        )
        ranked.append(((first_axis, second_axis, third_axis), index, item))
    return max(ranked, key=lambda entry: (entry[0], -entry[1]))[2]


def validate_story_blueprint(payload: object) -> dict[str, Any]:
    """Validate and JSON-copy one complete ``story-blueprint/v1`` payload."""

    root = _mapping(payload, "blueprint")
    unknown = set(root) - _TOP_LEVEL_KEYS
    missing = _TOP_LEVEL_KEYS - set(root)
    if unknown:
        raise StoryBlueprintError(f"blueprint contains unknown fields: {sorted(unknown)}")
    if missing:
        raise StoryBlueprintError(f"blueprint misses fields: {sorted(missing)}")
    if root["blueprint_version"] != STORY_BLUEPRINT_VERSION:
        raise StoryBlueprintError("unsupported story blueprint version")
    _non_empty_string(root["story_id"], "story_id", maximum=128)
    _non_empty_string(root["title_seed"], "title_seed")
    _non_empty_string(root["seed"], "seed", maximum=512)

    length = _mapping(root["length"], "length")
    minimum = _integer(length.get("min_parts"), "length.min_parts", minimum=400, maximum=400)
    maximum = _integer(length.get("max_parts"), "length.max_parts", minimum=2000, maximum=2000)
    target = _integer(length.get("target_parts"), "length.target_parts", minimum=minimum, maximum=maximum)
    if minimum > target or target > maximum:
        raise StoryBlueprintError("length target must be within the declared bounds")

    style = _mapping(root["style"], "style")
    for key in ("genre", "voice", "era", "setting"):
        _non_empty_string(style.get(key), f"style.{key}")
    novelty = style.get("novelty_constraints")
    if (
        not isinstance(novelty, list)
        or not novelty
        or not all(isinstance(item, str) and item.strip() for item in novelty)
    ):
        raise StoryBlueprintError("style.novelty_constraints must contain text rules")

    lesson = _mapping(root["lesson"], "lesson")
    for key in ("subject", "desired_insight", "integration_rule"):
        _non_empty_string(lesson.get(key), f"lesson.{key}")

    ending = _mapping(root["ending"], "ending")
    if ending.get("type") != "happy":
        raise StoryBlueprintError("ending.type must be happy")
    _non_empty_string(ending.get("success_condition"), "ending.success_condition")
    closure_beats = ending.get("closure_beats")
    if (
        not isinstance(closure_beats, list)
        or not closure_beats
        or not all(isinstance(item, str) for item in closure_beats)
    ):
        raise StoryBlueprintError("ending.closure_beats must contain at least one beat id")

    beats = root["beats"]
    if not isinstance(beats, list) or not minimum <= len(beats) <= maximum:
        raise StoryBlueprintError("beats must contain between 400 and 2000 entries")
    beat_ids: set[str] = set()
    for beat in beats:
        item = _mapping(beat, "beat")
        beat_id = _non_empty_string(item.get("id"), "beat.id", maximum=128)
        if beat_id in beat_ids:
            raise StoryBlueprintError(f"duplicate beat id: {beat_id}")
        beat_ids.add(beat_id)
        for key in ("purpose", "learning_function", "completion_condition"):
            _non_empty_string(item.get(key), f"beat.{key}")
        participants = item.get("participants")
        if not isinstance(participants, list) or not participants:
            raise StoryBlueprintError("beat.participants must not be empty")
        if not set(participants).issubset(REQUIRED_CHARACTER_IDS):
            raise StoryBlueprintError("beat.participants contains an unknown character")
        allowed_risks = item.get("allowed_risks")
        if (
            not isinstance(allowed_risks, list)
            or not all(isinstance(risk, str) and risk.strip() for risk in allowed_risks)
        ):
            raise StoryBlueprintError("beat.allowed_risks must be a list of risk names")
        followups = item.get("possible_followups")
        if (
            not isinstance(followups, list)
            or not all(isinstance(followup, str) and followup.strip() for followup in followups)
        ):
            raise StoryBlueprintError("beat.possible_followups must be a list of state names")

    for beat_id in closure_beats:
        if beat_id not in beat_ids:
            raise StoryBlueprintError(f"ending references unknown beat: {beat_id}")

    _mapping(root["world"], "world")

    cast = root["cast"]
    if not isinstance(cast, list) or len(cast) != 4:
        raise StoryBlueprintError("cast must contain exactly four characters")
    cast_ids: set[str] = set()
    for character in cast:
        item = _mapping(character, "cast entry")
        character_id = _non_empty_string(item.get("id"), "cast.id", maximum=64)
        if character_id in cast_ids:
            raise StoryBlueprintError(f"duplicate character id: {character_id}")
        cast_ids.add(character_id)
        if character_id not in REQUIRED_CHARACTER_IDS:
            raise StoryBlueprintError(f"unknown required character: {character_id}")
        _non_empty_string(item.get("name"), "cast.name")
        _numeric_map(item.get("bonuses"), "cast.bonuses")
        _numeric_map(item.get("maluses"), "cast.maluses")
        if character_id == "moehre":
            _exact_numeric_map(item.get("bonuses"), MOEHRE_BONUSES, "cast.moehre.bonuses")
            _exact_numeric_map(item.get("maluses"), MOEHRE_MALUSES, "cast.moehre.maluses")
        elif character_id == "maus":
            _exact_numeric_map(item.get("bonuses"), MAUS_BONUSES, "cast.maus.bonuses")
            _exact_numeric_map(item.get("maluses"), MAUS_MALUSES, "cast.maus.maluses")
        else:
            if len(_mapping(item.get("bonuses"), "cast.bonuses")) != CAT_TRAIT_COUNTS["bonuses"]:
                raise StoryBlueprintError("each cat must receive exactly eight bonuses")
            if len(_mapping(item.get("maluses"), "cast.maluses")) != CAT_TRAIT_COUNTS["maluses"]:
                raise StoryBlueprintError("each cat must receive exactly five maluses")
        if item.get("love") != 3:
            raise StoryBlueprintError("every character must start with +3 love")
        _integer(item.get("stubbornness"), "cast.stubbornness", minimum=2, maximum=5)
    if cast_ids != REQUIRED_CHARACTER_IDS:
        raise StoryBlueprintError("cast must contain the four known protagonists")

    authorities = _mapping(root["authorities"], "authorities")
    for key in ("traffic_authority", "police"):
        _mapping(authorities.get(key), f"authorities.{key}")
        _exact_numeric_map(
            _mapping(authorities[key], f"authorities.{key}").get("maluses"),
            AUTHORITY_START_MALUSES,
            f"authorities.{key}.maluses",
        )
    traffic_authority = _mapping(authorities["traffic_authority"], "authorities.traffic_authority")
    if traffic_authority.get("anger") != 2:
        raise StoryBlueprintError("traffic authority must start with +2 anger")
    police = _mapping(authorities["police"], "authorities.police")
    additional = police.get("additional_maluses")
    if not isinstance(additional, list) or len(additional) != 10:
        raise StoryBlueprintError("police.additional_maluses must contain exactly ten entries")
    penalty_ids: set[str] = set()
    for penalty in additional:
        item = _mapping(penalty, "police malus")
        penalty_id = _non_empty_string(item.get("id"), "police malus.id", maximum=64)
        if penalty_id in penalty_ids:
            raise StoryBlueprintError(f"duplicate police malus id: {penalty_id}")
        penalty_ids.add(penalty_id)
        _non_empty_string(item.get("description"), "police malus.description")
        if item.get("severity") not in {"medium", "heavy"}:
            raise StoryBlueprintError("police malus severity must be medium or heavy")
        if item.get("target_beat_id") not in beat_ids:
            raise StoryBlueprintError("police malus targets an unknown beat")

    risk_policy = _mapping(root["risk_policy"], "risk_policy")
    if risk_policy.get("version") != "weighted-dice/v1":
        raise StoryBlueprintError("unsupported risk policy")
    d12 = _mapping(risk_policy.get("d12"), "risk_policy.d12")
    d100 = _mapping(risk_policy.get("d100"), "risk_policy.d100")
    if d12.get("sides") != 12 or d12.get("peak_ratio") != 3:
        raise StoryBlueprintError("risk_policy.d12 must use 12 sides and a 3x endpoint ratio")
    if d100.get("sides") != 100 or d100.get("peak_ratio") != 20:
        raise StoryBlueprintError("risk_policy.d100 must use 100 sides and a 20x endpoint ratio")
    if risk_policy.get("escalate_on") != [1, 2] or risk_policy.get("max_followup_rolls") != 1:
        raise StoryBlueprintError("risk policy must allow exactly one D100 after D12 results 1 or 2")
    continuation = _mapping(root["continuation"], "continuation")
    if continuation.get("next_story_allowed") != "only_after_finished" or continuation.get("checkpoint") != "per_part":
        raise StoryBlueprintError("continuation must require finished stories and per-part checkpoints")
    skill_refs = root["skill_refs"]
    if not isinstance(skill_refs, list) or not all(isinstance(item, str) and item.strip() for item in skill_refs):
        raise StoryBlueprintError("skill_refs must be a list of non-empty references")

    try:
        return json.loads(json.dumps(root, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise StoryBlueprintError("blueprint must be JSON serializable") from exc


def blueprint_sha256(payload: object) -> str:
    """Return the canonical hash of a validated blueprint."""

    validated = validate_story_blueprint(payload)
    canonical = json.dumps(validated, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(canonical).hexdigest()


def start_story(blueprint: object, *, first_beat_id: str | None = None) -> StoryCheckpoint:
    """Create a new running checkpoint from a validated blueprint fixture."""

    validated = validate_story_blueprint(blueprint)
    beats = validated["beats"]
    if not isinstance(beats, list) or not beats:
        raise StoryBlueprintError("blueprint beats must be a non-empty list")
    first_id = first_beat_id
    if first_id is None:
        first = _mapping(beats[0], "beat")
        first_id = _non_empty_string(first.get("id"), "beat.id", maximum=128)
    elif not any(_mapping(beat, "beat").get("id") == first_id for beat in beats):
        raise StoryBlueprintError("story start references an unknown first beat")
    return StoryCheckpoint(
        blueprint_sha256=blueprint_sha256(validated),
        story_id=_non_empty_string(validated["story_id"], "story_id", maximum=128),
        next_beat_id=first_id,
    )


def start_next_story(
    previous: StoryCheckpoint,
    blueprint: object,
    *,
    first_beat_id: str | None = None,
) -> StoryCheckpoint:
    """Start a distinct story only from a finished previous checkpoint."""

    if not isinstance(previous, StoryCheckpoint):
        raise StoryBlueprintError("previous story state is invalid")
    if previous.status != "finished":
        raise StoryBlueprintError("next story requires a finished previous story")
    next_checkpoint = start_story(blueprint, first_beat_id=first_beat_id)
    if next_checkpoint.story_id == previous.story_id:
        raise StoryBlueprintError("next story must have a distinct story id")
    return next_checkpoint


def weighted_die_weights(sides: int, peak_ratio: int) -> tuple[Fraction, ...]:
    """Return linear weights whose last face is ``peak_ratio`` times face one."""

    if sides < 2 or peak_ratio < 1:
        raise ValueError("sides must be at least 2 and peak_ratio must be positive")
    return tuple(Fraction(1) + Fraction(peak_ratio - 1) * Fraction(face - 1, sides - 1) for face in range(1, sides + 1))


def roll_weighted_die(sides: int, peak_ratio: int, rng: Random) -> int:
    weights = weighted_die_weights(sides, peak_ratio)
    return rng.choices(range(1, sides + 1), weights=tuple(float(weight) for weight in weights), k=1)[0]


def stubbornness_weights() -> tuple[tuple[int, int], ...]:
    return ((2, 4), (3, 3), (4, 2), (5, 1))


def roll_stubbornness(rng: Random) -> int:
    values, weights = zip(*stubbornness_weights(), strict=True)
    return rng.choices(values, weights=weights, k=1)[0]


@dataclass(frozen=True, slots=True)
class RiskRoll:
    d12: int
    d100: int | None = None
    roll_id: str | None = None
    part_id: str | None = None
    actor: str | None = None
    action: str | None = None
    seed: str | None = None

    def __post_init__(self) -> None:
        _integer(self.d12, "risk roll d12", minimum=1, maximum=12)
        if self.d100 is not None:
            _integer(self.d100, "risk roll d100", minimum=1, maximum=100)
        if self.d12 in {1, 2} and self.d100 is None:
            raise StoryBlueprintError("D12 results 1 or 2 require exactly one D100")
        if self.d12 not in {1, 2} and self.d100 is not None:
            raise StoryBlueprintError("D100 is only allowed after D12 results 1 or 2")
        metadata = (self.roll_id, self.part_id, self.actor, self.action, self.seed)
        if any(value is not None for value in metadata) and not all(
            isinstance(value, str) and value.strip() for value in metadata
        ):
            raise StoryBlueprintError("risk roll metadata must contain roll_id, part_id, actor, action and seed")

    @property
    def recovery_percent(self) -> int | None:
        return self.d100

    def to_dict(self) -> dict[str, Any]:
        return {
            "roll_id": self.roll_id,
            "part_id": self.part_id,
            "actor": self.actor,
            "action": self.action,
            "seed": self.seed,
            "d12": self.d12,
            "d100": self.d100,
            "recovery_percent": self.recovery_percent,
        }


def roll_risk(
    rng: Random,
    *,
    roll_id: str | None = None,
    part_id: str | None = None,
    actor: str | None = None,
    action: str | None = None,
    seed: str | None = None,
) -> RiskRoll:
    d12 = roll_weighted_die(12, 3, rng)
    return RiskRoll(
        d12=d12,
        d100=roll_weighted_die(100, 20, rng) if d12 in {1, 2} else None,
        roll_id=roll_id,
        part_id=part_id,
        actor=actor,
        action=action,
        seed=seed,
    )


@dataclass(frozen=True, slots=True)
class StoryCheckpoint:
    blueprint_sha256: str
    story_id: str
    next_beat_id: str | None
    part_number: int = 0
    revision: int = 0
    last_part_id: str | None = None
    status: str = "running"
    last_roll: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.blueprint_sha256, str)
            or len(self.blueprint_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.blueprint_sha256)
        ):
            raise StoryBlueprintError("checkpoint blueprint_sha256 must be lowercase hex")
        _non_empty_string(self.story_id, "checkpoint.story_id", maximum=128)
        if self.next_beat_id is not None:
            _non_empty_string(self.next_beat_id, "checkpoint.next_beat_id", maximum=128)
        _integer(self.part_number, "checkpoint.part_number", minimum=0)
        _integer(self.revision, "checkpoint.revision", minimum=0)
        if self.status not in {"running", "finished"}:
            raise StoryBlueprintError("checkpoint status must be running or finished")
        if self.status == "finished" and self.next_beat_id is not None:
            raise StoryBlueprintError("finished checkpoint cannot have an open beat")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STORY_STATE_VERSION,
            "blueprint_sha256": self.blueprint_sha256,
            "story_id": self.story_id,
            "next_beat_id": self.next_beat_id,
            "part_number": self.part_number,
            "revision": self.revision,
            "last_part_id": self.last_part_id,
            "status": self.status,
            "last_roll": self.last_roll,
        }

    @classmethod
    def from_dict(cls, payload: object) -> StoryCheckpoint:
        item = _mapping(payload, "checkpoint")
        if item.get("schema_version") != STORY_STATE_VERSION:
            raise StoryBlueprintError("unsupported story state version")
        return cls(
            blueprint_sha256=item.get("blueprint_sha256"),
            story_id=item.get("story_id"),
            next_beat_id=item.get("next_beat_id"),
            part_number=item.get("part_number", 0),
            revision=item.get("revision", 0),
            last_part_id=item.get("last_part_id"),
            status=item.get("status", "running"),
            last_roll=item.get("last_roll"),
        )


def advance_checkpoint(
    checkpoint: StoryCheckpoint,
    *,
    part_id: str,
    next_beat_id: str | None,
    roll: RiskRoll | None = None,
    finished: bool = False,
) -> StoryCheckpoint:
    """Apply one complete part; replaying the last part is idempotent."""

    _non_empty_string(part_id, "part_id", maximum=128)
    if checkpoint.status == "finished":
        if checkpoint.last_part_id == part_id:
            return checkpoint
        raise StoryBlueprintError("cannot advance a finished story")
    if checkpoint.last_part_id == part_id:
        return checkpoint
    if finished and next_beat_id is not None:
        raise StoryBlueprintError("finished part must not leave an open beat")
    return StoryCheckpoint(
        blueprint_sha256=checkpoint.blueprint_sha256,
        story_id=checkpoint.story_id,
        next_beat_id=next_beat_id,
        part_number=checkpoint.part_number + 1,
        revision=checkpoint.revision + 1,
        last_part_id=part_id,
        status="finished" if finished else "running",
        last_roll=roll.to_dict() if roll else checkpoint.last_roll,
    )


def write_checkpoint(path: Path, checkpoint: StoryCheckpoint) -> None:
    """Write a checkpoint with private mode and an atomic replace."""

    path = Path(path).expanduser()
    parent = path.parent
    _ensure_checkpoint_parent(parent)
    if path.is_symlink():
        raise StoryBlueprintError("checkpoint must not be a symlink")
    temporary = parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(checkpoint.to_dict(), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def exclusive_story_checkpoint_lock(path: Path) -> Iterator[None]:
    """Hold the per-story state lock across one generation transaction."""

    path = Path(path).expanduser()
    parent = path.parent
    _ensure_checkpoint_parent(parent)
    lock_path = path.with_name(f".{path.name}.lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise StoryBlueprintError("story checkpoint lock must not be a symlink") from exc
        raise StoryBlueprintError("cannot open story checkpoint lock") from exc
    locked = False
    try:
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise StoryBlueprintError("story checkpoint lock must be a regular file")
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError as exc:
            raise StoryBlueprintError("cannot acquire story checkpoint lock") from exc
        locked = True
        yield
    finally:
        try:
            if locked:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def read_checkpoint(path: Path) -> StoryCheckpoint:
    path = Path(path).expanduser()
    _assert_checkpoint_parent(path.parent)
    if path.is_symlink() or not path.is_file():
        raise StoryBlueprintError("checkpoint must be a regular file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StoryBlueprintError("checkpoint is not valid UTF-8 JSON") from exc
    return StoryCheckpoint.from_dict(payload)


def _assert_checkpoint_parent(parent: Path) -> None:
    current = Path(parent)
    while True:
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            raise StoryBlueprintError("checkpoint parent must exist") from exc
        if current.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            raise StoryBlueprintError("checkpoint parent must contain only real directories")
        if current.parent == current:
            return
        current = current.parent


def _ensure_checkpoint_parent(parent: Path) -> None:
    current = Path(parent)
    ancestors = [current]
    while ancestors[-1].parent != ancestors[-1]:
        ancestors.append(ancestors[-1].parent)
    for directory in reversed(ancestors):
        try:
            metadata = directory.lstat()
        except FileNotFoundError:
            directory.mkdir(mode=0o700)
            metadata = directory.lstat()
            if directory.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
                raise StoryBlueprintError(
                    "checkpoint parent must contain only real directories"
                ) from None
            os.chmod(directory, 0o700)
            continue
        if directory.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            raise StoryBlueprintError("checkpoint parent must contain only real directories")
