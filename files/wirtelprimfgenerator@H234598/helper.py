#!/usr/bin/env python3
"""Helper for wirtelprimfgenerator@H234598.

Repo-specific defaults target H234598/Katzenbilder / Sourcecode/wirtelprimpf_generator.py:
- local outdir: $HOME/Hintergrundbilder
- working dir: $HOME/Hintergrundbilder/working
- repo subdir: Wirtelprimpf
- latest story triplet: working/latest.png, latest.txt, latest.md
- full story link: working/Full_Story.md
- generated stems: wirtelprimpf_YYYY-MM-DD_HH-MM-SS-ffffff[_classic-01|_story-01]
"""
from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import html
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

UUID = "wirtelprimfgenerator@H234598"
DEFAULT_STATE_DIR = Path.home() / ".local" / "state" / "wirtelprimfgenerator-applet"
LEGACY_STATE_DIR = Path.home() / ".config" / "wirtelprimfgenerator-applet"
PROJECT_URL = "https://github.com/H234598/Katzenbilder"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".avif"}
TEXT_EXTS = {".md", ".markdown", ".txt", ".text"}
FULL_EXTS = {".md", ".markdown", ".epub"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache"}
RECENT_PART_LIMIT = 15
ROMAN_RE = re.compile(r"Story_([IVXLCDM]+)", re.IGNORECASE)
WIRTEL_STEM_RE = re.compile(r"^wirtelprimpf_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(?:-\d+)?)(?:_(classic|story)-\d+)?$", re.IGNORECASE)
ENTRY_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)
FULL_STORY_NAMES = {"full_story.md", "full_story.markdown"}
WORKING_DIR_NAME = "working"
WORKING_IMAGE_NAME = "latest.png"
WORKING_STORY_NAME = "latest.md"
WORKING_FULL_STORY_NAME = "Full_Story.md"

STOP_REQUESTED = False
CURRENT_CHILD: Optional[subprocess.Popen[Any]] = None
CURRENT_LOCK_FILE: Optional[Path] = None


@dataclasses.dataclass
class ScanArgs:
    output_dir: str = ""
    state_dir: Path = DEFAULT_STATE_DIR
    open_command: str = "xdg-open"
    tts_command: str = ""
    story_image_glob: str = ""
    generated_image_glob: str = ""
    full_story_glob: str = ""
    part_glob: str = ""
    max_depth: int = 4


@dataclasses.dataclass
class PartInfo:
    path: Path
    rel: str
    dt: datetime
    dt_source: str
    mtime: float
    roman: Optional[str] = None
    roman_int: int = 0
    part_no: int = 0

    @property
    def date_label(self) -> str:
        return self.dt.strftime("%d.%m.%Y")

    @property
    def tooltip(self) -> str:
        suffix = "" if self.dt_source != "mtime" else " (mtime)"
        return self.dt.strftime("%d.%m.%Y %H:%M") + suffix


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def expand_path(value: Optional[str], base: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> Optional[Path]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if env is not None:
        for key, val in env.items():
            raw = raw.replace("${" + key + "}", val).replace("$" + key, val)
    raw = os.path.expandvars(os.path.expanduser(raw))
    p = Path(raw)
    if not p.is_absolute() and base is not None:
        p = base / p
    return p


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        try:
            dir_fd = os.open(str(path.parent), os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            pass
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def migrate_legacy_state_dir(state_dir: Path) -> None:
    """Move old ~/.config runtime state toward ~/.local/state without losing the TTS marker."""
    try:
        if state_dir.resolve() == LEGACY_STATE_DIR.resolve():
            return
    except Exception:
        pass
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        for name in ("state.json", "stat.json"):
            src = LEGACY_STATE_DIR / name
            dst = state_dir / name
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
    except Exception:
        pass


def state_paths(state_dir: Path) -> Dict[str, Path]:
    migrate_legacy_state_dir(state_dir)
    return {"state": state_dir / "state.json", "stat": state_dir / "stat.json", "lock": state_dir / "tts.lock"}


def parse_shell_env_file(path: Path) -> Dict[str, str]:
    env = dict(os.environ)
    parsed: Dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return parsed
    try:
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
                continue
            value = value.strip()
            if " #" in value and not (value.startswith("'") or value.startswith('"')):
                value = value.split(" #", 1)[0].strip()
            try:
                parts = shlex.split(value, posix=True)
                value = parts[0] if parts else ""
            except Exception:
                value = value.strip('"\'')
            for k, v in {**env, **parsed}.items():
                value = value.replace("${" + k + "}", v).replace("$" + k, v)
            value = os.path.expandvars(os.path.expanduser(value))
            parsed[key] = value
    except Exception as exc:
        eprint(f"Could not parse env file {path}: {exc}")
    return parsed


def wirtel_env_files() -> List[Path]:
    home = Path.home()
    return [
        home / ".config" / "wirtelprimpf" / "openai.env",
        home / ".config" / "wirtelprimf" / "openai.env",
        home / "GitHub" / "Katzenbilder" / "Sourcecode" / "env.example",
        home / "github" / "Katzenbilder" / "Sourcecode" / "env.example",
    ]


def wirtel_env() -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for path in wirtel_env_files():
        vals = parse_shell_env_file(path)
        if vals:
            merged.update(vals)
            # Prefer real private openai.env; env.example is only a final hint.
            if path.name == "openai.env":
                break
    return merged


def candidate_output_dirs_from_env(env: Dict[str, str]) -> List[Tuple[Path, str]]:
    out: List[Tuple[Path, str]] = []
    local = expand_path(env.get("WIRTELPRIMPF_LOCAL_OUTDIR"), env=env)
    if local:
        out.append((local, "WIRTELPRIMPF_LOCAL_OUTDIR"))
    story_doc = expand_path(env.get("WIRTELPRIMPF_STORY_DOCUMENT"), env=env)
    if story_doc:
        out.append((story_doc.parent, "WIRTELPRIMPF_STORY_DOCUMENT parent"))
    working = expand_path(env.get("WIRTELPRIMPF_WORKING_DIR"), env=env)
    if working:
        out.append((working.parent, "WIRTELPRIMPF_WORKING_DIR parent"))
        out.append((working, "WIRTELPRIMPF_WORKING_DIR"))
    repo_path = expand_path(env.get("WIRTELPRIMPF_REPO_PATH"), env=env)
    repo_sub = env.get("WIRTELPRIMPF_REPO_SUBDIR") or "Wirtelprimpf"
    if repo_path:
        out.append((repo_path / repo_sub, "WIRTELPRIMPF_REPO_PATH/subdir"))
    return out


def resolve_output_dir(user_dir: str) -> Tuple[Optional[Path], str, List[str]]:
    errors: List[str] = []
    chosen = expand_path(user_dir)
    if chosen and chosen.exists() and chosen.is_dir():
        return chosen.resolve(), "settings", errors
    if chosen and user_dir.strip():
        errors.append(f"Konfigurierter Outputordner existiert nicht: {chosen}")

    direct_env = expand_path(os.environ.get("WIRTELPRIMPF_LOCAL_OUTDIR") or os.environ.get("WIRTEL_OUTPUT_DIR"))
    if direct_env and direct_env.exists() and direct_env.is_dir():
        return direct_env.resolve(), "environment", errors

    env = wirtel_env()
    for path, label in candidate_output_dirs_from_env(env):
        if path.exists() and path.is_dir():
            return path.resolve(), label, errors

    home = Path.home()
    candidates = [
        home / "Hintergrundbilder",
        home / "GitHub" / "Katzenbilder" / "Wirtelprimpf",
        home / "github" / "Katzenbilder" / "Wirtelprimpf",
        home / "Github" / "Katzenbilder" / "Wirtelprimpf",
        home / "Projects" / "Katzenbilder" / "Wirtelprimpf",
        home / "Code" / "Katzenbilder" / "Wirtelprimpf",
        home / "GitHub" / "Katzenbilder",
        home / "github" / "Katzenbilder",
        home / "Github" / "Katzenbilder",
    ]
    for path in candidates:
        if path.exists() and path.is_dir():
            return path.resolve(), f"fallback:{path}", errors

    errors.append("Kein Outputordner gefunden. Setze den Katzenbilder-/Outputordner in den Applet-Einstellungen oder WIRTELPRIMPF_LOCAL_OUTDIR.")
    return None, "not-found", errors


def iter_files(root: Path, max_depth: int) -> Iterable[Path]:
    max_depth = max(1, int(max_depth or 1))
    stack = [(root, 1)]
    while stack:
        current, depth = stack.pop()
        try:
            entries = list(current.iterdir())
        except Exception:
            continue
        for entry in entries:
            if entry.name in SKIP_DIRS:
                continue
            try:
                if entry.is_dir() and not entry.is_symlink():
                    if depth < max_depth:
                        stack.append((entry, depth + 1))
                elif entry.is_file() or entry.is_symlink():
                    yield entry
            except Exception:
                continue


def rel_str(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return path.name


def split_patterns(patterns: str) -> List[str]:
    return [p.strip() for p in re.split(r"[;\n]+", patterns or "") if p.strip()]


def pattern_match(root: Path, path: Path, patterns: str) -> bool:
    rel = rel_str(root, path).replace(os.sep, "/")
    name = path.name
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel, pat.replace(os.sep, "/")) for pat in split_patterns(patterns))


def mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return 0.0


def roman_to_int(value: Optional[str]) -> int:
    if not value:
        return 0
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(value.upper()):
        cur = vals.get(ch, 0)
        if cur < prev:
            total -= cur
        else:
            total += cur
            prev = cur
    return total


def parse_roman_from_path(path: Path) -> Tuple[Optional[str], int]:
    candidates = [path.name, str(path.parent)]
    try:
        if path.is_symlink():
            candidates.append(path.resolve(strict=False).name)
    except Exception:
        pass
    for text in candidates:
        m = ROMAN_RE.search(text)
        if m:
            roman = m.group(1).upper()
            return roman, roman_to_int(roman)
    return None, 0


def parse_datetime_from_filename(path: Path) -> Tuple[datetime, str]:
    name = path.stem
    m = re.search(r"(20\d{2}|19\d{2})[-_](\d{2})[-_](\d{2})[_T -](\d{2})[-_:](\d{2})[-_:](\d{2})", name)
    if m:
        try:
            y, mo, d, h, mi, s = map(int, m.groups())
            return datetime(y, mo, d, h, mi, s), "filename"
        except Exception:
            pass
    m = re.search(r"(20\d{2}|19\d{2})[-_](\d{2})[-_](\d{2})", name)
    if m:
        try:
            y, mo, d = map(int, m.groups())
            return datetime(y, mo, d), "filename"
        except Exception:
            pass
    return datetime.fromtimestamp(mtime(path) or time.time()), "mtime"


def parse_entry_heading_datetime(path: Path) -> Tuple[Optional[datetime], Optional[str]]:
    try:
        # Only read the beginning; generated part file starts with the heading.
        with path.open("r", encoding="utf-8", errors="replace") as f:
            head = f.read(4096)
    except Exception:
        return None, None
    m = ENTRY_HEADING_RE.search(head)
    if not m:
        return None, None
    stamp = f"{m.group(1)} {m.group(2)}"
    try:
        return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S"), stamp
    except Exception:
        return None, stamp


def is_wirtel_generated_stem(path: Path) -> Tuple[bool, Optional[str]]:
    m = WIRTEL_STEM_RE.match(path.stem)
    if not m:
        return False, None
    return True, (m.group(2).lower() if m.group(2) else None)


def is_in_working(root: Path, path: Path) -> bool:
    return WORKING_DIR_NAME in rel_str(root, path).split(os.sep)


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def choose_latest(paths: Sequence[Path]) -> Optional[Path]:
    if not paths:
        return None
    return sorted(paths, key=lambda p: (1 if "latest" in p.name.lower() else 0, mtime(p), str(p)))[-1]


def has_matching_story_part(path: Path) -> bool:
    return (path.parent / (path.stem + ".md")).exists() or (path.parent / (path.stem + ".markdown")).exists()


def scan_images(root: Path, files: List[Path], args: ScanArgs) -> Dict[str, Optional[Dict[str, str]]]:
    images = [p for p in files if is_image(p)]

    if args.story_image_glob:
        story = choose_latest([p for p in images if pattern_match(root, p, args.story_image_glob)])
    else:
        working_latest = [root / WORKING_DIR_NAME / name for name in ["latest.png", "latest.jpg", "latest.jpeg", "latest.webp"]]
        candidates = [p for p in working_latest if p.exists() or p.is_symlink()]
        if not candidates:
            candidates = []
            for p in images:
                generated, kind = is_wirtel_generated_stem(p)
                if kind == "story" or has_matching_story_part(p):
                    candidates.append(p)
            if not candidates:
                candidates = [p for p in images if "story" in rel_str(root, p).lower()]
        story = choose_latest(candidates)

    if args.generated_image_glob:
        generated = choose_latest([p for p in images if pattern_match(root, p, args.generated_image_glob)])
    else:
        candidates = []
        for p in images:
            if is_in_working(root, p):
                continue
            generated_stem, kind = is_wirtel_generated_stem(p)
            if kind == "classic":
                candidates.append(p)
            elif generated_stem and kind is None and not has_matching_story_part(p):
                # Legacy classic mode had no _classic suffix and no md story-part twin.
                candidates.append(p)
        generated = choose_latest(candidates)

    def pack(p: Optional[Path]) -> Optional[Dict[str, str]]:
        if not p:
            return None
        return {"path": str(p), "label": p.name}
    return {"story": pack(story), "generated": pack(generated)}


def scan_full_stories(root: Path, files: List[Path], args: ScanArgs) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Path]] = {}
    for p in files:
        if p.suffix.lower() not in FULL_EXTS:
            continue
        if is_in_working(root, p) and p.name.lower() not in FULL_STORY_NAMES:
            continue
        if args.full_story_glob and not pattern_match(root, p, args.full_story_glob):
            continue
        roman, _num = parse_roman_from_path(p)
        if not roman and p.name.lower() in FULL_STORY_NAMES:
            try:
                roman, _num = parse_roman_from_path(p.resolve(strict=False))
            except Exception:
                pass
        if not roman:
            continue
        # Exclude generated single part files; they start wirtelprimpf_<timestamp>.
        generated, _kind = is_wirtel_generated_stem(p)
        if generated:
            continue
        grouped.setdefault(roman, []).append(p)

    out: List[Dict[str, Any]] = []
    for roman, paths in grouped.items():
        def pref(p: Path) -> Tuple[int, int, float]:
            ext_score = 3 if p.suffix.lower() == ".epub" else 2
            working_score = 0 if is_in_working(root, p) else 1
            return (ext_score, working_score, mtime(p))
        chosen = sorted(paths, key=pref)[-1]
        if chosen.is_symlink():
            try:
                resolved = chosen.resolve(strict=False)
                if resolved.exists():
                    chosen = resolved
            except Exception:
                pass
        out.append({"label": f"Story_{roman}", "roman": roman, "roman_int": roman_to_int(roman), "path": str(chosen), "mtime": mtime(chosen)})
    out.sort(key=lambda item: (item["roman_int"], item["mtime"]))
    return out


def active_full_story(root: Path, full_stories: List[Dict[str, Any]]) -> Optional[Path]:
    link = root / WORKING_DIR_NAME / WORKING_FULL_STORY_NAME
    if link.exists() or link.is_symlink():
        try:
            resolved = link.resolve(strict=False)
            if resolved.exists():
                return resolved
        except Exception:
            return link
    if not full_stories:
        return None
    newest = sorted(full_stories, key=lambda s: (s.get("roman_int", 0), s.get("mtime", 0)))[-1]
    return Path(str(newest["path"]))


def story_entry_stamps(full_story: Optional[Path]) -> set[str]:
    if not full_story or not full_story.exists() or full_story.suffix.lower() not in {".md", ".markdown"}:
        return set()
    try:
        text = full_story.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return set()
    return {f"{m.group(1)} {m.group(2)}" for m in ENTRY_HEADING_RE.finditer(text)}


def is_part_candidate(root: Path, p: Path, args: ScanArgs) -> bool:
    if p.suffix.lower() not in {".md", ".markdown"}:
        return False
    if is_in_working(root, p):
        return False
    if args.part_glob:
        return pattern_match(root, p, args.part_glob)
    if p.name.lower() in FULL_STORY_NAMES:
        return False
    if ROMAN_RE.search(p.name):
        return False
    generated, _kind = is_wirtel_generated_stem(p)
    if generated:
        return True
    dt, stamp = parse_entry_heading_datetime(p)
    del dt
    return stamp is not None


def part_info(root: Path, path: Path, active_roman: Optional[str], active_roman_int: int) -> Tuple[PartInfo, Optional[str]]:
    entry_dt, stamp = parse_entry_heading_datetime(path)
    if entry_dt is not None:
        dt, source = entry_dt, "heading"
    else:
        dt, source = parse_datetime_from_filename(path)
    return PartInfo(path=path, rel=rel_str(root, path), dt=dt, dt_source=source, mtime=mtime(path), roman=active_roman, roman_int=active_roman_int), stamp


def scan_parts(root: Path, files: List[Path], args: ScanArgs, full_stories: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[PartInfo]]:
    active = active_full_story(root, full_stories)
    active_roman, active_roman_int = parse_roman_from_path(active) if active else (None, 0)
    stamps = story_entry_stamps(active)

    infos: List[PartInfo] = []
    for p in files:
        if not is_part_candidate(root, p, args):
            continue
        info, stamp = part_info(root, p, active_roman, active_roman_int)
        if stamps and stamp not in stamps:
            continue
        infos.append(info)

    if not infos:
        return [], [], []
    infos.sort(key=lambda fi: (fi.dt, fi.mtime, fi.rel))
    for i, fi in enumerate(infos, start=1):
        fi.part_no = i
    desc = list(reversed(infos))
    recent = desc[:RECENT_PART_LIMIT]

    recent_out = [{
        "label": f"Last {idx}h",
        "path": str(fi.path),
        "date_label": fi.date_label,
        "tooltip": f"Part{fi.part_no} – {fi.tooltip}",
        "part_no": fi.part_no,
        "roman": fi.roman,
    } for idx, fi in enumerate(recent, start=1)]
    all_out = [{
        "label": fi.date_label,
        "path": str(fi.path),
        "tooltip": f"Part{fi.part_no} – {fi.tooltip}",
        "part_no": fi.part_no,
        "roman": fi.roman,
    } for fi in desc]
    return recent_out, all_out, infos


def pid_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
        if pid_int <= 0:
            return False
        os.kill(pid_int, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def read_lock(path: Path) -> Dict[str, Any]:
    data = read_json(path, {})
    if not data:
        return {}
    if pid_alive(data.get("pid")) or pid_alive(data.get("child_pid")):
        return data
    try:
        path.unlink()
    except Exception:
        pass
    return {}


def scan(args: ScanArgs) -> Dict[str, Any]:
    args.state_dir.mkdir(parents=True, exist_ok=True)
    paths = state_paths(args.state_dir)
    output, source, errors = resolve_output_dir(args.output_dir)
    state = read_json(paths["state"], {})
    stat = read_json(paths["stat"], {})
    lock = read_lock(paths["lock"])

    result: Dict[str, Any] = {
        "ok": output is not None,
        "output_dir": str(output) if output else "",
        "output_source": source,
        "state_dir": str(args.state_dir),
        "images": {"story": None, "generated": None},
        "full_stories": [],
        "recent_parts": [],
        "all_current_story_parts": [],
        "stats": {
            "previous_full_story_count": stat.get("known_full_story_count"),
            "known_full_story_count": stat.get("known_full_story_count", 0),
            "current_full_story_count": 0,
        },
        "tts": {
            "last_file": state.get("last_file", ""),
            "last_file_label": Path(state.get("last_file", "")).name if state.get("last_file") else "",
            "running": bool(lock),
            "pid": lock.get("pid") if lock else None,
        },
        "errors": errors,
    }
    if output is None:
        return result

    files = list(iter_files(output, args.max_depth))
    result["images"] = scan_images(output, files, args)
    full = scan_full_stories(output, files, args)
    result["full_stories"] = full
    recent, all_parts, _infos = scan_parts(output, files, args, full)
    result["recent_parts"] = recent
    result["all_current_story_parts"] = all_parts

    count = len(full)
    result["stats"]["current_full_story_count"] = count
    if count > 1:
        previous = stat.get("known_full_story_count")
        new_stat = dict(stat)
        new_stat.update({"known_full_story_count": count, "last_scan_at": datetime.now().isoformat(timespec="seconds"), "output_dir": str(output)})
        atomic_write_json(paths["stat"], new_stat)
        result["stats"]["previous_full_story_count"] = previous
        result["stats"]["known_full_story_count"] = count
    return result


def open_path(path: str, args: ScanArgs) -> Dict[str, Any]:
    p = expand_path(path)
    if not p or not (p.exists() or p.is_symlink()):
        return {"ok": False, "errors": [f"Datei/Ordner existiert nicht: {path}"]}
    cmd = shlex.split(args.open_command or "xdg-open") or ["xdg-open"]
    try:
        subprocess.Popen(cmd + [str(p)], start_new_session=True)
        return {"ok": True, "path": str(p)}
    except Exception as exc:
        return {"ok": False, "errors": [str(exc)]}


class HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self.skip = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() in {"script", "style", "nav"}:
            self.skip = True
        if tag.lower() in {"p", "br", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "nav"}:
            self.skip = False
        if tag.lower() in {"p", "div", "h1", "h2", "h3", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        return cleanup_text(" ".join(self.parts))


def cleanup_text(text: str) -> str:
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"```.*?```", "\n", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"[*_~>#]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt", ".text"}:
        return cleanup_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".epub":
        chunks: List[str] = []
        with zipfile.ZipFile(path) as zf:
            for name in sorted(n for n in zf.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))):
                try:
                    parser = HtmlTextExtractor()
                    parser.feed(zf.read(name).decode("utf-8", errors="replace"))
                    txt = parser.text()
                    if txt:
                        chunks.append(txt)
                except Exception:
                    continue
        return cleanup_text("\n\n".join(chunks))
    return cleanup_text(path.read_text(encoding="utf-8", errors="replace"))


def chunk_text(text: str, max_len: int = 2400) -> Iterable[str]:
    text = cleanup_text(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    buf = ""
    for para in paragraphs:
        if len(para) > max_len:
            for piece in textwrap.wrap(para, width=max_len, break_long_words=False, replace_whitespace=False):
                if buf:
                    yield buf
                    buf = ""
                yield piece
            continue
        if len(buf) + len(para) + 2 <= max_len:
            buf = (buf + "\n\n" + para).strip()
        else:
            if buf:
                yield buf
            buf = para
    if buf:
        yield buf


def candidate_piper_models() -> List[Path]:
    configured = [
        os.environ.get("WIRTELPRIMPF_TTS_PIPER_MODEL"),
        os.environ.get("PIPER_VOICE"),
        os.environ.get("PIPER_MODEL"),
    ]
    candidates: List[Path] = []
    for raw in configured:
        p = expand_path(raw)
        if p:
            candidates.append(p)
    home = Path.home()
    for base in [
        home / ".local" / "share" / "piper" / "voices",
        home / ".local" / "share" / "piper",
        home / ".config" / "piper",
        home / "piper" / "voices",
    ]:
        if not base.exists():
            continue
        try:
            candidates.extend(sorted(base.rglob("*de*.onnx")))
            candidates.extend(sorted(base.rglob("*.onnx")))
        except Exception:
            continue
    seen: set[Path] = set()
    out: List[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve(strict=False)
        except Exception:
            resolved = candidate.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_file():
            out.append(resolved)
    return out


def available_tts() -> Tuple[str, List[str]]:
    piper = shutil.which("piper")
    if piper:
        models = candidate_piper_models()
        if models:
            return "piper", [piper, "--model", str(models[0])]
    if shutil.which("spd-say"):
        return "spd-say", ["spd-say", "-w", "-l", "de", "-t", "female1", "-r", "-10", "-p", "-5"]
    if shutil.which("espeak-ng"):
        return "espeak-ng", ["espeak-ng", "-v", "de+f3", "-s", "155", "-p", "35"]
    if shutil.which("espeak"):
        return "espeak", ["espeak", "-v", "de+f3", "-s", "155", "-p", "35"]
    return "none", []


def write_lock(lock_path: Path, child_pid: Optional[int], current_file: Optional[Path], command: str) -> None:
    global CURRENT_LOCK_FILE
    CURRENT_LOCK_FILE = lock_path
    atomic_write_json(lock_path, {"pid": os.getpid(), "child_pid": child_pid, "current_file": str(current_file or ""), "command": command, "started_at": datetime.now().isoformat(timespec="seconds")})


def clear_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except Exception:
        pass


def install_signal_handlers() -> None:
    def handler(signum: int, frame: Any) -> None:
        global STOP_REQUESTED, CURRENT_CHILD
        STOP_REQUESTED = True
        child = CURRENT_CHILD
        if child and child.poll() is None:
            try:
                child.terminate()
                child.wait(timeout=2)
            except Exception:
                try:
                    child.kill()
                except Exception:
                    pass
        if CURRENT_LOCK_FILE:
            clear_lock(CURRENT_LOCK_FILE)
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


UNSAFE_COMMAND_TOKENS = {"|", "||", "&", "&&", ";", ">", ">>", "<", "2>", "2>>"}


def build_custom_tts_argv(command: str, text: str, text_file: Path, story_file: Path) -> List[str]:
    """Build a custom TTS command without invoking a shell.

    Template placeholders are substituted as literal argv values and shell
    operators are rejected. Users who need a shell can explicitly configure
    `sh -c ...`, making that choice visible instead of accidental.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError as exc:
        raise RuntimeError(f"Ungültiges TTS-Kommando: {exc}") from exc
    if not tokens:
        raise RuntimeError("Leeres TTS-Kommando")
    for token in tokens:
        if "\x00" in token or token in UNSAFE_COMMAND_TOKENS:
            raise RuntimeError(f"Unsicheres Shell-Token im TTS-Kommando: {token!r}")
    replacements = {"{text}": text, "{text_file}": str(text_file), "{file}": str(story_file)}
    out: List[str] = []
    for token in tokens:
        for key, value in replacements.items():
            token = token.replace(key, value)
        out.append(token)
    executable = out[0]
    if os.sep not in executable and shutil.which(executable) is None:
        raise RuntimeError(f"TTS-Kommando nicht gefunden: {executable}")
    return out


def run_custom_tts(command: str, text: str, text_file: Path, story_file: Path, lock_path: Path) -> int:
    global CURRENT_CHILD
    argv = build_custom_tts_argv(command, text, text_file, story_file)
    CURRENT_CHILD = subprocess.Popen(argv, start_new_session=True)
    write_lock(lock_path, CURRENT_CHILD.pid, story_file, "custom")
    rc = CURRENT_CHILD.wait()
    CURRENT_CHILD = None
    return rc


def run_auto_tts(text: str, story_file: Path, lock_path: Path) -> int:
    global CURRENT_CHILD
    engine, base = available_tts()
    if not base:
        eprint("No TTS engine found. Install piper plus a German voice model, speech-dispatcher/spd-say, or espeak-ng.")
        return 127
    for chunk in chunk_text(text):
        if STOP_REQUESTED:
            return 130
        if engine == "piper":
            player = shutil.which("aplay") or shutil.which("paplay")
            if not player:
                eprint("Piper is available, but no aplay/paplay audio player was found.")
                return 127
            with tempfile.NamedTemporaryFile(prefix="wirtel-tts-", suffix=".wav", dir=str(lock_path.parent), delete=False) as tmp_audio:
                audio_path = Path(tmp_audio.name)
            try:
                CURRENT_CHILD = subprocess.Popen(base + ["--output_file", str(audio_path)], stdin=subprocess.PIPE, text=True, start_new_session=True)
                assert CURRENT_CHILD.stdin is not None
                CURRENT_CHILD.stdin.write(chunk)
                CURRENT_CHILD.stdin.close()
                write_lock(lock_path, CURRENT_CHILD.pid, story_file, engine)
                rc = CURRENT_CHILD.wait()
                CURRENT_CHILD = None
                if rc != 0:
                    return rc
                play_cmd = [player, str(audio_path)] if Path(player).name == "paplay" else [player, "-q", str(audio_path)]
                CURRENT_CHILD = subprocess.Popen(play_cmd, start_new_session=True)
            finally:
                try:
                    if CURRENT_CHILD is None or CURRENT_CHILD.poll() is not None:
                        audio_path.unlink(missing_ok=True)
                except Exception:
                    pass
        else:
            CURRENT_CHILD = subprocess.Popen(base + [chunk], start_new_session=True)
        write_lock(lock_path, CURRENT_CHILD.pid, story_file, engine)
        rc = CURRENT_CHILD.wait()
        if engine == "piper":
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass
        CURRENT_CHILD = None
        if rc != 0:
            return rc
    return 0


def save_completed_state(state_path: Path, file_path: Path, output_dir: Optional[Path]) -> None:
    payload = read_json(state_path, {})
    payload.update({
        "last_file": str(file_path),
        "last_file_completed_at": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(output_dir) if output_dir else payload.get("output_dir", ""),
        "state_kind": "last_completed_file",
    })
    atomic_write_json(state_path, payload)


def tts_read_files(files: List[Path], args: ScanArgs, output_dir: Optional[Path]) -> Dict[str, Any]:
    install_signal_handlers()
    paths = state_paths(args.state_dir)
    args.state_dir.mkdir(parents=True, exist_ok=True)
    if not files:
        return {"ok": True, "message": "Keine neuen Storyteile zu lesen."}
    write_lock(paths["lock"], None, files[0], "starting")
    completed: List[str] = []
    try:
        for file_path in files:
            if STOP_REQUESTED:
                break
            file_path = file_path.expanduser().resolve()
            if not file_path.exists():
                continue
            text = extract_text(file_path)
            tmp_text = args.state_dir / "tts-current.txt"
            tmp_text.write_text(text, encoding="utf-8")
            rc = run_custom_tts(args.tts_command.strip(), text, tmp_text, file_path, paths["lock"]) if args.tts_command.strip() else run_auto_tts(text, file_path, paths["lock"])
            if rc != 0 or STOP_REQUESTED:
                return {"ok": False, "returncode": rc, "completed": completed, "stopped": STOP_REQUESTED}
            save_completed_state(paths["state"], file_path, output_dir)
            completed.append(str(file_path))
        return {"ok": True, "completed": completed, "stopped": STOP_REQUESTED}
    finally:
        clear_lock(paths["lock"])


def get_current_parts(args: ScanArgs) -> Tuple[Optional[Path], List[PartInfo], List[str]]:
    output, _source, errors = resolve_output_dir(args.output_dir)
    if not output:
        return None, [], errors
    files = list(iter_files(output, args.max_depth))
    full = scan_full_stories(output, files, args)
    _recent, _all, infos = scan_parts(output, files, args, full)
    infos.sort(key=lambda fi: (fi.dt, fi.mtime, fi.rel))
    return output, infos, errors


def same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except Exception:
        return str(a) == str(b)


def tts_continue(args: ScanArgs) -> Dict[str, Any]:
    output, infos, errors = get_current_parts(args)
    if not infos:
        return {"ok": False, "errors": errors + ["Keine Storyteile gefunden."]}
    state = read_json(state_paths(args.state_dir)["state"], {})
    last_raw = state.get("last_file", "")
    last = expand_path(last_raw) if last_raw else None
    start = 0
    if last:
        for i, fi in enumerate(infos):
            if same_file(fi.path, last):
                start = i + 1
                break
    return tts_read_files([fi.path for fi in infos[start:]], args, output)


def select_file_dialog(initial_dir: Path) -> Optional[Path]:
    initial = str(initial_dir) + os.sep
    if shutil.which("zenity"):
        proc = subprocess.run(["zenity", "--file-selection", "--title", "Storyteil für TTS setzen", "--filename", initial, "--file-filter", "Storydateien | *.md *.txt *.epub", "--file-filter", "Alle Dateien | *"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
        return None
    if shutil.which("kdialog"):
        proc = subprocess.run(["kdialog", "--getopenfilename", str(initial_dir), "*.md *.txt *.epub"], text=True, stdout=subprocess.PIPE)
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip())
        return None
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        value = filedialog.askopenfilename(initialdir=str(initial_dir), title="Storyteil für TTS setzen")
        root.destroy()
        return Path(value) if value else None
    except Exception as exc:
        eprint(f"No file dialog available: {exc}")
        return None


def tts_set(args: ScanArgs) -> Dict[str, Any]:
    output, infos, errors = get_current_parts(args)
    if not output:
        return {"ok": False, "errors": errors + ["Kein Outputordner gefunden."]}
    chosen = select_file_dialog(output)
    if not chosen:
        return {"ok": True, "cancelled": True}
    chosen = chosen.expanduser().resolve()
    if not chosen.exists() or not chosen.is_file():
        return {"ok": False, "errors": [f"Ausgewählte Datei existiert nicht: {chosen}"]}
    files: List[Path] = []
    for i, fi in enumerate(infos):
        if same_file(fi.path, chosen):
            files = [x.path for x in infos[i:]]
            break
    if not files:
        files = [chosen]
    return tts_read_files(files, args, output)


def tts_stop(args: ScanArgs) -> Dict[str, Any]:
    lock_path = state_paths(args.state_dir)["lock"]
    lock = read_json(lock_path, {})
    killed: List[int] = []
    errors: List[str] = []
    for key in ["child_pid", "pid"]:
        pid = lock.get(key)
        try:
            pid_int = int(pid)
        except Exception:
            continue
        if not pid_alive(pid_int):
            continue
        try:
            os.kill(pid_int, signal.SIGTERM)
            killed.append(pid_int)
        except Exception as exc:
            errors.append(f"SIGTERM {pid_int}: {exc}")
    deadline = time.time() + 2.0
    while time.time() < deadline and any(pid_alive(pid) for pid in killed):
        time.sleep(0.1)
    for pid in killed:
        if pid_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
    clear_lock(lock_path)
    if shutil.which("spd-say"):
        try:
            subprocess.run(["spd-say", "--cancel"], timeout=2)
        except Exception:
            pass
    return {"ok": not errors, "killed": killed, "errors": errors}




def command_exists(command: str) -> bool:
    try:
        parts = shlex.split(command or "")
    except Exception:
        return False
    if not parts:
        return False
    exe = parts[0]
    if os.sep in exe:
        return Path(exe).exists() and os.access(exe, os.X_OK)
    return shutil.which(exe) is not None


def file_dialog_available() -> str:
    if shutil.which("zenity"):
        return "zenity"
    if shutil.which("kdialog"):
        return "kdialog"
    try:
        import tkinter  # noqa: F401
        return "tkinter"
    except Exception:
        return "none"


def add_check(checks: List[Dict[str, Any]], name: str, ok: bool, message: str) -> None:
    checks.append({"name": name, "status": "ok" if ok else "error", "message": message})


def doctor(args: ScanArgs) -> Dict[str, Any]:
    result = scan(args)
    checks: List[Dict[str, Any]] = []
    output = Path(result["output_dir"]) if result.get("output_dir") else None
    add_check(checks, "Outputordner", bool(output), result.get("output_dir") or "Nicht gefunden")
    add_check(checks, "Story latest", bool(result.get("images", {}).get("story")), "working/latest.png oder Story-Bild gefunden" if result.get("images", {}).get("story") else "Kein aktuelles Story-Bild gefunden")
    add_check(checks, "Generated latest", bool(result.get("images", {}).get("generated")), "Generated/Classic-Bild gefunden" if result.get("images", {}).get("generated") else "Kein Generated/Classic-Bild gefunden")
    add_check(checks, "Full Story", len(result.get("full_stories", [])) > 0, f"{len(result.get('full_stories', []))} Story-Datei(en)")
    add_check(checks, "Storyteile", len(result.get("all_current_story_parts", [])) > 0, f"{len(result.get('all_current_story_parts', []))} Teil(e) in aktueller Story")
    add_check(checks, "Open command", command_exists(args.open_command), args.open_command or "xdg-open")
    if args.tts_command.strip():
        try:
            build_custom_tts_argv(args.tts_command, "Test", args.state_dir / "tts-current.txt", Path("test.md"))
            tts_ok = True
            tts_msg = "Custom TTS-Kommando ist parsebar und ohne Shell startbar"
        except Exception as exc:
            tts_ok = False
            tts_msg = str(exc)
    else:
        engine, _base = available_tts()
        tts_ok = engine != "none"
        tts_msg = engine if tts_ok else "Installiere piper mit deutschem Stimmenmodell, speech-dispatcher/spd-say oder espeak-ng"
    add_check(checks, "TTS", tts_ok, tts_msg)
    dialog = file_dialog_available()
    add_check(checks, "Dateidialog", dialog != "none", dialog if dialog != "none" else "Installiere zenity oder kdialog")
    try:
        args.state_dir.mkdir(parents=True, exist_ok=True)
        test = args.state_dir / ".write-test"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        state_ok = True
        state_msg = str(args.state_dir)
    except Exception as exc:
        state_ok = False
        state_msg = str(exc)
    add_check(checks, "State-Verzeichnis", state_ok, state_msg)
    ok = all(c["status"] == "ok" for c in checks)
    summary = f"{sum(1 for c in checks if c['status']=='ok')}/{len(checks)} Checks ok"
    return {"ok": ok, "summary": summary, "checks": checks, "scan": result, "errors": [] if ok else [c["message"] for c in checks if c["status"] != "ok"]}


def setup_plan(args: ScanArgs) -> Dict[str, Any]:
    diag = doctor(args)
    scan_result = diag.get("scan", {})
    output = scan_result.get("output_dir") or "<nicht gefunden>"
    checks = diag.get("checks", [])
    failing = [c for c in checks if c.get("status") != "ok"]
    output_arg = "" if output == "<nicht gefunden>" else str(output)
    lines = [
        "# Wirtelprimfgenerator Cinnamon Applet – Setup/Doctor",
        f"# Repo: {PROJECT_URL}",
        f"# Output: {output}",
        "",
        "# Empfohlene Laufzeitpakete:",
        "sudo apt install python3 xdg-utils speech-dispatcher zenity",
        "# Optionaler besserer TTS-Pfad: piper plus deutsches .onnx-Stimmenmodell, dann WIRTELPRIMPF_TTS_PIPER_MODEL setzen.",
        "# Optionaler TTS-Fallback:",
        "sudo apt install espeak-ng",
        "",
        "# Generator-Konfiguration prüfen:",
        "test -f ~/.config/wirtelprimpf/openai.env && sed -n '1,120p' ~/.config/wirtelprimpf/openai.env",
        "",
        "# Erwartete Katzenbilder-Defaults:",
        "echo \"WIRTELPRIMPF_LOCAL_OUTDIR=$HOME/Hintergrundbilder\"",
        "echo \"WIRTELPRIMPF_WORKING_DIR=$HOME/Hintergrundbilder/working\"",
        "ls -la \"$HOME/Hintergrundbilder\" \"$HOME/Hintergrundbilder/working\" 2>/dev/null || true",
        "",
        "# Applet-Helper direkt prüfen:",
        f"python3 {shlex.quote(str(Path(__file__).resolve()))} doctor --output-dir {shlex.quote(output_arg)}",
        "",
        "# Aktuelle Problemchecks:",
    ]
    if failing:
        for c in failing:
            lines.append(f"# - {c.get('name')}: {c.get('message')}")
    else:
        lines.append("# - keine")
    return {"ok": True, "text": "\n".join(lines) + "\n", "doctor": diag}


def reset_state(args: ScanArgs) -> Dict[str, Any]:
    paths = state_paths(args.state_dir)
    state = read_json(paths["state"], {})
    for key in ["last_file", "last_file_completed_at", "state_kind"]:
        state.pop(key, None)
    atomic_write_json(paths["state"], state)
    return {"ok": True, "state": str(paths["state"])}

def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wirtelprimfgenerator Cinnamon Applet helper")
    parser.add_argument("command", choices=["scan", "open", "tts-continue", "tts-set", "tts-stop", "doctor", "setup-plan", "reset-state"])
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR))
    parser.add_argument("--open-command", default="xdg-open")
    parser.add_argument("--tts-command", default="")
    parser.add_argument("--story-image-glob", default="")
    parser.add_argument("--generated-image-glob", default="")
    parser.add_argument("--full-story-glob", default="")
    parser.add_argument("--part-glob", default="")
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--path", default="")
    return parser.parse_args(argv)


def ns_to_scan_args(ns: argparse.Namespace) -> ScanArgs:
    return ScanArgs(
        output_dir=ns.output_dir or "",
        state_dir=Path(os.path.expanduser(os.path.expandvars(ns.state_dir or str(DEFAULT_STATE_DIR)))),
        open_command=ns.open_command or "xdg-open",
        tts_command=ns.tts_command or "",
        story_image_glob=ns.story_image_glob or "",
        generated_image_glob=ns.generated_image_glob or "",
        full_story_glob=ns.full_story_glob or "",
        part_glob=ns.part_glob or "",
        max_depth=max(1, int(ns.max_depth or 4)),
    )


def main(argv: Sequence[str]) -> int:
    ns = parse_args(argv)
    args = ns_to_scan_args(ns)
    try:
        if ns.command == "scan":
            result = scan(args)
        elif ns.command == "open":
            result = open_path(ns.path, args)
        elif ns.command == "tts-continue":
            result = tts_continue(args)
        elif ns.command == "tts-set":
            result = tts_set(args)
        elif ns.command == "tts-stop":
            result = tts_stop(args)
        elif ns.command == "doctor":
            result = doctor(args)
        elif ns.command == "setup-plan":
            result = setup_plan(args)
        elif ns.command == "reset-state":
            result = reset_state(args)
        else:
            result = {"ok": False, "errors": ["Unknown command"]}
    except SystemExit:
        raise
    except Exception as exc:
        result = {"ok": False, "errors": [repr(exc)]}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
