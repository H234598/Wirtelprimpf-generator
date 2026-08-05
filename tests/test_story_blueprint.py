"""Contract tests for the versioned story blueprint primitives."""

from __future__ import annotations

import fcntl
import tempfile
import unittest
from pathlib import Path
from random import Random

from wirtelprimpf_platform.story_blueprint import (
    StoryBlueprintError,
    StoryCheckpoint,
    RiskRoll,
    advance_checkpoint,
    blueprint_sha256,
    read_checkpoint,
    roll_risk,
    roll_stubbornness,
    choose_decision,
    exclusive_story_checkpoint_lock,
    select_bounded_traits,
    start_story,
    start_next_story,
    stubbornness_weights,
    validate_story_blueprint,
    weighted_die_weights,
    write_checkpoint,
)


def blueprint() -> dict[str, object]:
    beats = [
        {
            "id": f"beat-{index:04d}",
            "purpose": "advance the conflict",
            "learning_function": "make the lesson felt",
            "completion_condition": "the beat is rendered and checked",
            "participants": ["weisspfote", "schwarzkralle", "moehre", "maus"],
            "allowed_risks": ["minor setback"],
            "possible_followups": ["continue", "recover"],
        }
        for index in range(400)
    ]
    cast = [
        {"id": "weisspfote", "name": "Weißpfote", "bonuses": {f"curiosity-{index}": 1 for index in range(8)}, "maluses": {f"pride-{index}": 1 for index in range(5)}, "love": 3, "stubbornness": 2},
        {"id": "schwarzkralle", "name": "Schwarzkralle", "bonuses": {f"warmth-{index}": 1 for index in range(8)}, "maluses": {f"sleepiness-{index}": 1 for index in range(5)}, "love": 3, "stubbornness": 3},
        {"id": "moehre", "name": "die Möhre", "bonuses": {"list_subversivitaet": 2, "planung": 1, "einfallsreichtum": 1, "handwerk": 1, "beamten_tarnung": 1, "support": 4}, "maluses": {"angst_schreckhaftigkeit": 2, "quengeln": 0.5, "befuerchtungen_vorahnungen": 4, "geistige_blockiertheit": 2, "vergesslichkeit": 0.5}, "love": 3, "stubbornness": 4},
        {"id": "maus", "name": "die Maus", "bonuses": {"intelligenz": 3, "it_faehigkeiten": 5, "aussehen_tanz_charme": 2, "hyperfokus": 3, "geistiger_geschmack": 2, "rettung_aus_dummen_aktionen": 4.5, "glueck": 2, "fuersorge": 3}, "maluses": {"nichtzuhoeren_vergesslichkeit": 3, "ablenkbarkeit": 3, "gefaehrliche_aktionen": 3, "tanzen_beenden": 1, "wichtige_details": 2, "zu_viel_reden": 2, "selbstverliebtheit": 2, "linksradikal": 1}, "love": 3, "stubbornness": 5},
    ]
    return {
        "blueprint_version": "story-blueprint/v1",
        "story_id": "story-fixture-001",
        "title_seed": "The measured detour",
        "length": {"min_parts": 400, "target_parts": 400, "max_parts": 2000},
        "style": {"genre": "bureaucratic comedy", "voice": "warm and literary", "era": "near future", "setting": "shared apartment", "novelty_constraints": ["no repeated central conflict"]},
        "lesson": {"subject": "patience", "desired_insight": "small acts compound", "integration_rule": "show it through action"},
        "ending": {"type": "happy", "success_condition": "the friends solve the conflict together", "closure_beats": ["beat-0399"]},
        "cast": cast,
        "world": {"description": "fixture world"},
        "authorities": {
            "traffic_authority": {"anger": 2, "maluses": {"dummheit": 5, "fahrlaessigkeit": 6, "selbstverliebtheit": 3}},
            "police": {
                "maluses": {"dummheit": 5, "fahrlaessigkeit": 6, "selbstverliebtheit": 3},
                "additional_maluses": [{"id": f"police-malus-{index:02d}", "description": "a targeted fixture setback", "severity": "medium", "target_beat_id": f"beat-{index:04d}"} for index in range(10)],
            },
        },
        "beats": beats,
        "risk_policy": {"version": "weighted-dice/v1", "d12": {"sides": 12, "peak_ratio": 3}, "d100": {"sides": 100, "peak_ratio": 20}, "escalate_on": [1, 2], "max_followup_rolls": 1},
        "continuation": {"next_story_allowed": "only_after_finished", "checkpoint": "per_part"},
        "seed": "fixture-seed",
        "skill_refs": [],
    }


class StoryBlueprintTests(unittest.TestCase):
    def test_valid_blueprint_is_strict_and_hash_stable(self) -> None:
        payload = blueprint()
        self.assertEqual(len(validate_story_blueprint(payload)["beats"]), 400)
        self.assertEqual(blueprint_sha256(payload), blueprint_sha256(payload))
        payload["unexpected"] = True  # type: ignore[index]
        with self.assertRaises(StoryBlueprintError):
            validate_story_blueprint(payload)

    def test_blueprint_rejects_wrong_length_cast_or_police_targets(self) -> None:
        payload = blueprint()
        payload["length"] = {"min_parts": 1, "target_parts": 400, "max_parts": 2000}
        with self.assertRaises(StoryBlueprintError):
            validate_story_blueprint(payload)
        payload = blueprint()
        payload["cast"] = list(payload["cast"])[1:]  # type: ignore[arg-type]
        with self.assertRaises(StoryBlueprintError):
            validate_story_blueprint(payload)
        payload = blueprint()
        authorities = dict(payload["authorities"])  # type: ignore[arg-type]
        police = dict(authorities["police"])
        police["additional_maluses"] = list(police["additional_maluses"])
        police["additional_maluses"][0] = {"severity": "heavy", "target_beat_id": "missing"}
        authorities["police"] = police
        payload["authorities"] = authorities
        with self.assertRaises(StoryBlueprintError):
            validate_story_blueprint(payload)

    def test_weighted_curves_have_requested_end_ratios(self) -> None:
        d12 = weighted_die_weights(12, 3)
        d100 = weighted_die_weights(100, 20)
        self.assertEqual(d12[-1] / d12[0], 3)
        self.assertEqual(d100[-1] / d100[0], 20)
        self.assertEqual(stubbornness_weights(), ((2, 4), (3, 3), (4, 2), (5, 1)))

    def test_cat_traits_are_deterministic_and_bounded_to_the_supplied_catalog(self) -> None:
        catalog = {
            "bonuses": {f"bonus-{index}": index + 1 for index in range(10)},
            "maluses": {f"malus-{index}": index + 1 for index in range(6)},
        }
        first = select_bounded_traits("fixture-seed", "weisspfote", catalog)
        second = select_bounded_traits("fixture-seed", "weisspfote", catalog)
        self.assertEqual(first, second)
        self.assertEqual(len(first["bonuses"]), 8)
        self.assertEqual(len(first["maluses"]), 5)
        self.assertTrue(set(first["bonuses"]).issubset(catalog["bonuses"]))
        self.assertTrue(set(first["maluses"]).issubset(catalog["maluses"]))
        with self.assertRaises(StoryBlueprintError):
            select_bounded_traits("fixture-seed", "moehre", catalog)

    def test_decision_priorities_are_automatic_and_ordered(self) -> None:
        chosen = choose_decision(
            [
                {"id": "danger-swim", "priorities": ["danger", "swimming"]},
                {"id": "friendship-cheese", "priorities": ["friendship", "cheese"]},
                {"id": "virtue-not-swim", "priorities": ["virtue", "not_swimming"]},
            ]
        )
        self.assertEqual(chosen["id"], "virtue-not-swim")
        self.assertEqual(
            choose_decision(
                [
                    {"id": "danger", "priorities": ["danger"]},
                    {"id": "friendship", "priorities": ["friendship"]},
                ]
            )["id"],
            "friendship",
        )

    def test_risk_roll_only_escalates_for_one_or_two(self) -> None:
        class SequenceRng:
            def __init__(self, values: list[int]) -> None:
                self.values = values

            def choices(self, _population: object, *, weights: object, k: int) -> list[int]:
                self.assert_k = k
                return [self.values.pop(0)]

        low = roll_risk(SequenceRng([1, 37]))
        self.assertEqual((low.d12, low.d100), (1, 37))
        high = roll_risk(SequenceRng([2, 99]))
        self.assertEqual((high.d12, high.d100), (2, 99))
        normal = roll_risk(SequenceRng([3]))
        self.assertEqual((normal.d12, normal.d100), (3, None))
        record = roll_risk(
            SequenceRng([1, 88]),
            roll_id="roll-0001",
            part_id="part-0001",
            actor="maus",
            action="open the locked drawer",
            seed="fixture-seed",
        )
        self.assertEqual(record.to_dict()["actor"], "maus")
        self.assertEqual(record.to_dict()["d100"], 88)
        with self.assertRaises(StoryBlueprintError):
            RiskRoll(d12=1)
        self.assertIn(roll_stubbornness(Random(2)), range(2, 6))

    def test_checkpoint_advancement_is_idempotent_and_finishes_cleanly(self) -> None:
        checkpoint = StoryCheckpoint("a" * 64, "story-fixture-001", "beat-0001")
        advanced = advance_checkpoint(checkpoint, part_id="part-0001", next_beat_id="beat-0002")
        self.assertEqual(advanced.part_number, 1)
        self.assertEqual(advance_checkpoint(advanced, part_id="part-0001", next_beat_id="beat-0002"), advanced)
        finished = advance_checkpoint(advanced, part_id="part-0002", next_beat_id=None, finished=True)
        self.assertEqual(finished.status, "finished")
        with self.assertRaises(StoryBlueprintError):
            advance_checkpoint(finished, part_id="part-0003", next_beat_id=None)

    def test_checkpoint_roundtrip_is_private_and_atomic(self) -> None:
        checkpoint = StoryCheckpoint("b" * 64, "story-fixture-001", "beat-0001")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "story.json"
            write_checkpoint(path, checkpoint)
            self.assertEqual(read_checkpoint(path), checkpoint)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_checkpoint_rejects_intermediate_symlink_directories(self) -> None:
        checkpoint = StoryCheckpoint("c" * 64, "story-fixture-001", "beat-0001")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            linked = root / "linked"
            linked.symlink_to(real, target_is_directory=True)
            with self.assertRaises(StoryBlueprintError):
                write_checkpoint(linked / "nested" / "story.json", checkpoint)

    def test_checkpoint_lock_is_exclusive_private_and_released(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "fixture-story" / "state.json"
            lock_path = state_path.with_name(".state.json.lock")
            with exclusive_story_checkpoint_lock(state_path):
                self.assertEqual(lock_path.stat().st_mode & 0o777, 0o600)
                with lock_path.open("a+b") as competitor, self.assertRaises(BlockingIOError):
                    fcntl.flock(competitor.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with lock_path.open("a+b") as competitor:
                fcntl.flock(competitor.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(competitor.fileno(), fcntl.LOCK_UN)

    def test_checkpoint_lock_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "fixture-story" / "state.json"
            state_path.parent.mkdir()
            target = state_path.parent / "target.lock"
            target.touch()
            state_path.with_name(".state.json.lock").symlink_to(target)
            with self.assertRaises(StoryBlueprintError), exclusive_story_checkpoint_lock(state_path):
                pass

    def test_fixture_story_start_is_hash_bound_and_restartable(self) -> None:
        payload = blueprint()
        checkpoint = start_story(payload)
        self.assertEqual(checkpoint.story_id, "story-fixture-001")
        self.assertEqual(checkpoint.next_beat_id, "beat-0000")
        self.assertEqual(checkpoint.part_number, 0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture-story" / "state.json"
            write_checkpoint(path, checkpoint)
            resumed = advance_checkpoint(
                read_checkpoint(path),
                part_id="part-0001",
                next_beat_id="beat-0001",
            )
            write_checkpoint(path, resumed)
            self.assertEqual(read_checkpoint(path).part_number, 1)
            self.assertEqual(read_checkpoint(path).blueprint_sha256, blueprint_sha256(payload))

    def test_next_story_requires_finished_state_and_a_new_story_id(self) -> None:
        running = start_story(blueprint())
        with self.assertRaises(StoryBlueprintError):
            start_next_story(running, blueprint())
        finished = advance_checkpoint(running, part_id="part-0399", next_beat_id=None, finished=True)
        next_payload = blueprint()
        next_payload["story_id"] = "story-fixture-002"
        next_checkpoint = start_next_story(finished, next_payload)
        self.assertEqual(next_checkpoint.story_id, "story-fixture-002")
        with self.assertRaises(StoryBlueprintError):
            start_next_story(finished, blueprint())


if __name__ == "__main__":
    unittest.main()
