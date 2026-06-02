#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=${PYTHON_BIN:-python3}
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
REPO_PATH="${WIRTELPRIMPF_REPO_PATH:-$ROOT_DIR}"
if [[ "$(basename "$REPO_PATH")" == ".git" ]]; then
  PUBLISH_STATE_FILE="$REPO_PATH/wirtelprimpf_publish_state.json"
else
  PUBLISH_STATE_FILE="$REPO_PATH/.git/wirtelprimpf_publish_state.json"
fi
STATE_FILE="$ROOT_DIR/Sourcecode/.minor_version_state"
LOCK_FILE="$ROOT_DIR/Sourcecode/.minor_version_watch.lock"
LOCK_TMP="${LOCK_FILE}.tmp.$$"
TIMESTAMP_FILE="$STATE_FILE.started_at"
CHECKS_SCRIPT="$ROOT_DIR/Sourcecode/check_wirtelprimpf.sh"
SLEEP_SECONDS="${SLEEP_SECONDS:-300}"
MAX_STALE_LOCK_SECONDS="${MAX_STALE_LOCK_SECONDS:-900}"
DEFAULT_RETRY_DELAY_SECONDS="${DEFAULT_RETRY_DELAY_SECONDS:-5}"

parse_positive_int() {
  local value="$1"
  local fallback="$2"
  local min="${3:-1}"
  if [[ -z "$value" || ! "$value" =~ ^[0-9]+$ ]]; then
    echo "$fallback"
    return
  fi
  if (( value < min )); then
    echo "$fallback"
    return
  fi
  echo "$value"
}

SLEEP_SECONDS="$(parse_positive_int "$SLEEP_SECONDS" 300 1)"
MAX_STALE_LOCK_SECONDS="$(parse_positive_int "$MAX_STALE_LOCK_SECONDS" 900 10)"
DEFAULT_RETRY_DELAY_SECONDS="$(parse_positive_int "$DEFAULT_RETRY_DELAY_SECONDS" 5 1)"

log() {
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    log "${label} missing: $path"
    exit 1
  fi
}

require_executable() {
  local path="$1"
  local label="$2"
  if [[ ! -x "$path" ]]; then
    log "${label} is not executable: $path"
    exit 1
  fi
}

require_executable "$PY" "Python interpreter"
require_file "$PY_SCRIPT" "Generator script"

write_state() {
  local value="$1"
  mkdir -p "$(dirname "$STATE_FILE")"
  printf '%s\n' "$value" > "$STATE_FILE.tmp.$$"
  mv -f "$STATE_FILE.tmp.$$" "$STATE_FILE"
}

refresh_state_timestamp() {
  date +%s > "$TIMESTAMP_FILE"
}

acquire_lock() {
  is_running_pid() {
    local candidate="$1"
    [[ -n "$candidate" && "$candidate" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$candidate" 2>/dev/null
  }

  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
      local pid
      pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
      log "another watcher instance is running (flock), exiting (holder=${pid:-unknown})"
      exit 0
    fi
    printf '%s\n' "$$" 1>&9
    trap 'flock -u 9 2>/dev/null || true; exec 9>&- 2>/dev/null || true; rm -f "$LOCK_FILE" "$LOCK_TMP" "$TIMESTAMP_FILE" 2>/dev/null || true' EXIT
    return
  fi

  if ! mkdir "$LOCK_TMP" 2>/dev/null; then
    local pid
    pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
    if [[ -f "$LOCK_FILE" ]]; then
      local now
      now=$(date +%s)
      local lock_mtime age
      lock_mtime=$(stat -c '%Y' "$LOCK_FILE" 2>/dev/null || echo "$now")
      age=$((now - lock_mtime))
      if [[ "$age" -lt "$MAX_STALE_LOCK_SECONDS" ]] && is_running_pid "$pid"; then
        log "another watcher instance is running (fallback lock), exiting"
        exit 0
      fi
      log "stale fallback lock detected (${age}s), stealing lock"
      rm -f "$LOCK_FILE"
    fi
    mkdir "$LOCK_TMP"
  fi

  mv "$LOCK_TMP" "$LOCK_FILE"
  printf '%s\n' "$$" > "$LOCK_FILE"
  trap 'rm -f "$LOCK_TMP" "$LOCK_FILE" "$TIMESTAMP_FILE" 2>/dev/null || true' EXIT
}

get_minor_version() {
  "$PY" - "$PY_SCRIPT" "$PUBLISH_STATE_FILE" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

PATCHES_PER_MINOR = 100
MINORS_PER_MAJOR = 100
PATCHES_PER_MINOR_FOR_MINOR = PATCHES_PER_MINOR

script_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
state_patch_count = 0
if state_path.exists():
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"invalid publish state file: {state_path}: {exc}")
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid publish state: expected JSON object in {state_path}")
    if "patch_count" in payload:
        state_patch_count = payload["patch_count"]
    elif "patch_version" in payload:
        state_patch_count = payload["patch_version"]
    else:
        raise SystemExit("invalid publish state: missing patch_count and patch_version")
    if not isinstance(state_patch_count, int) or isinstance(state_patch_count, bool):
        raise SystemExit(f"invalid publish state: patch_count must be a non-boolean integer, got {state_patch_count!r}")
    if state_patch_count < 0:
        raise SystemExit(f"invalid publish state: patch_count must be >= 0, got {state_patch_count!r}")

try:
    text = script_path.read_text(encoding="utf-8")
except OSError as exc:
    raise SystemExit(f"cannot read script: {exc}") from exc

match = re.search(r'VERSION:\s*Final\s*=\s*"([^"]+)"', text)
if not match:
    raise SystemExit("VERSION constant not found")

version = match.group(1).strip()
parsed = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", version)
if not parsed:
    raise SystemExit(f"invalid version format: {version!r}")
major_str, minor_str, _patch_str, suffix = parsed.groups()
patches_per_minor_raw = os.environ.get("WIRTELPRIMPF_PATCHES_PER_MINOR", "100")
major_bump_raw = os.environ.get("WIRTELPRIMPF_MAJOR_VERSION_BUMP", "0")
try:
    patches_per_minor = int(patches_per_minor_raw)
    if patches_per_minor < 1:
        raise ValueError
except ValueError:
    raise SystemExit(f"invalid WIRTELPRIMPF_PATCHES_PER_MINOR value: {patches_per_minor_raw!r}")
if patches_per_minor != PATCHES_PER_MINOR:
    raise SystemExit(f"invalid WIRTELPRIMPF_PATCHES_PER_MINOR value: {patches_per_minor!r}, expected {PATCHES_PER_MINOR}")
try:
    major_bump = int(major_bump_raw)
    if major_bump < 0:
        raise ValueError
except ValueError:
    raise SystemExit(f"invalid WIRTELPRIMPF_MAJOR_VERSION_BUMP value: {major_bump_raw!r}")

if state_patch_count == 0:
    print(f"{major_str}.{minor_str}.0{suffix}")
    raise SystemExit(0)

patch_version = state_patch_count % patches_per_minor
if patch_version == 0:
    patch_version = PATCHES_PER_MINOR_FOR_MINOR

minor_increments = state_patch_count // patches_per_minor
major_addition, minor_offset = divmod(int(minor_str) + minor_increments, MINORS_PER_MAJOR)
major_version = int(major_str) + major_addition + major_bump
print(f"{major_version}.{minor_offset}.{patch_version}{suffix}")

PY
}

acquire_lock

init_state=$(get_minor_version)
if [[ ! -f "$STATE_FILE" ]]; then
  write_state "$init_state"
fi

if [[ "${1:-}" == "--once" ]]; then
  require_file "$CHECKS_SCRIPT" "Checks script"
  require_executable "$CHECKS_SCRIPT" "Checks script"
  prev="$(cat "$STATE_FILE")"
  current="$(get_minor_version)"
  if [[ "$current" != "$prev" ]]; then
    write_state "$current"
    if "$CHECKS_SCRIPT"; then
      refresh_state_timestamp
      log "checks completed for version $current"
    else
      log "checks failed for version $current"
    fi
  fi
  exit 0
fi

while true; do
  prev="$(cat "$STATE_FILE")"
  current="$(get_minor_version)"

  if [[ "$current" != "$prev" ]]; then
    require_file "$CHECKS_SCRIPT" "Checks script"
    require_executable "$CHECKS_SCRIPT" "Checks script"
    log "minor version changed: $prev -> $current"
    write_state "$current"
    if "$CHECKS_SCRIPT"; then
      log "checks completed for version $current"
    else
      log "checks failed for version $current"
    fi
    refresh_state_timestamp
    sleep "$DEFAULT_RETRY_DELAY_SECONDS"
    continue
  fi

  if [[ -f "$TIMESTAMP_FILE" ]]; then
    now_epoch="$(date +%s)"
    last_epoch="$(cat "$TIMESTAMP_FILE")"
    if [[ -n "$last_epoch" && $((now_epoch - last_epoch)) -lt 1 ]]; then
      sleep "$DEFAULT_RETRY_DELAY_SECONDS"
      continue
    fi
  fi

  sleep "$SLEEP_SECONDS"
done
