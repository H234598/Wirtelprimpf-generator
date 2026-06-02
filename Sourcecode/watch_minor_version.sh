#!/usr/bin/env bash
set -euo pipefail
umask 077
IFS=$'\n\t'

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON_BIN:-}" && "${PYTHON_BIN}" == *[[:space:]]* ]]; then
  log "PYTHON_BIN must not contain whitespace: ${PYTHON_BIN}"
  exit 1
fi

log() {
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
}

resolve_python() {
  local candidates=("${PYTHON_BIN:-}")
  if [[ -z "${candidates[0]:-}" ]]; then
    candidates=("python3" "python")
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    local resolved
    if [[ "$candidate" =~ [[:space:]] || "$candidate" == -* ]]; then
      continue
    fi
    resolved="$(command -v -- "$candidate" 2>/dev/null || true)"
    if [[ -n "$resolved" && -x "$resolved" ]]; then
      echo "$resolved"
      return 0
    fi
  done

  return 1
}

if ! PY="$(resolve_python)"; then
  log "no usable python interpreter found (tried: ${PYTHON_BIN:+$PYTHON_BIN }python3 python)"
  exit 1
fi
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
validate_repo_path() {
  local path="$1"
  if [[ -z "$path" ]]; then
    log "repository path is empty"
    exit 1
  fi
  if [[ "$path" == *[[:space:]]* ]]; then
    log "repository path contains whitespace: ${path}"
    exit 1
  fi
  if [[ -L "$path" ]]; then
    log "repository path must not be a symlink: ${path}"
    exit 1
  fi
  if [[ ! -d "$path" ]]; then
    log "repository path is not a directory: ${path}"
    exit 1
  fi
  if [[ ! -r "$path" || ! -x "$path" ]]; then
    log "repository path is not accessible (must be readable and searchable): ${path}"
    exit 1
  fi
  cd -- "$path" >/dev/null 2>&1
  printf '%s\n' "$(pwd)"
}

validate_publish_state_path() {
  local publish_state_file="$1"
  local parent_dir
  parent_dir="$(dirname "$publish_state_file")"

  if [[ -L "$publish_state_file" ]]; then
    log "publish state file must not be a symlink: ${publish_state_file}"
    exit 1
  fi
  if [[ -e "$publish_state_file" ]]; then
    if ! is_regular_file "$publish_state_file"; then
      log "publish state file must be a regular file: ${publish_state_file}"
      exit 1
    fi
  fi
  if [[ -L "$parent_dir" ]]; then
    log "publish state directory must not be a symlink: ${parent_dir}"
    exit 1
  fi
  if [[ -e "$parent_dir" && ! -d "$parent_dir" ]]; then
    log "publish state parent path is not a directory: ${parent_dir}"
    exit 1
  fi
}

validate_publish_state_file() {
  local publish_state_file="$1"
  if [[ -e "$publish_state_file" ]]; then
    if ! is_regular_file "$publish_state_file"; then
      log "publish state file must be a regular file: ${publish_state_file}"
      exit 1
    fi
    if [[ ! -r "$publish_state_file" ]]; then
      log "publish state file is not readable: ${publish_state_file}"
      exit 1
    fi
  fi
}

REPO_PATH="$(validate_repo_path "${WIRTELPRIMPF_REPO_PATH:-$ROOT_DIR}")"
if [[ "$(basename "$REPO_PATH")" == ".git" ]]; then
  if [[ -L "$REPO_PATH" ]]; then
    log "publish state path must not be a symlink directory: ${REPO_PATH}"
    exit 1
  fi
  if [[ -L "$REPO_PATH/wirtelprimpf_publish_state.json" ]]; then
    log "publish state path must not be a symlink file: ${REPO_PATH}/wirtelprimpf_publish_state.json"
    exit 1
  fi
  PUBLISH_STATE_FILE="$REPO_PATH/wirtelprimpf_publish_state.json"
else
  if [[ -L "$REPO_PATH/.git" ]]; then
    log ".git path must not be a symlink: ${REPO_PATH}/.git"
    exit 1
  fi
  if [[ -L "$REPO_PATH/.git/wirtelprimpf_publish_state.json" ]]; then
    log "publish state path must not be a symlink file: ${REPO_PATH}/.git/wirtelprimpf_publish_state.json"
    exit 1
  fi
  PUBLISH_STATE_FILE="$REPO_PATH/.git/wirtelprimpf_publish_state.json"
fi
validate_publish_state_path "$PUBLISH_STATE_FILE"
validate_publish_state_file "$PUBLISH_STATE_FILE"
STATE_FILE="$ROOT_DIR/Sourcecode/.minor_version_state"
require_directory "$(dirname "$STATE_FILE")" "State directory" "rwx"
LOCK_FILE="$ROOT_DIR/Sourcecode/.minor_version_watch.lock"
require_directory "$(dirname "$LOCK_FILE")" "Lock directory" "rwx"
LOCK_TMP=""
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

require_directory() {
  local path="$1"
  local label="$2"
  local mode="${3:-rx}"
  if [[ ! -d "$path" ]]; then
    log "${label} must be a directory: $path"
    exit 1
  fi
  if [[ -L "$path" ]]; then
    log "${label} must not be a symlink: $path"
    exit 1
  fi
  if [[ ! -r "$path" || ! -x "$path" ]]; then
    log "${label} must be readable and searchable: $path"
    exit 1
  fi
  if [[ "$mode" == *w* && ! -w "$path" ]]; then
    log "${label} must be writable: $path"
    exit 1
  fi
}

SLEEP_SECONDS="$(parse_positive_int "$SLEEP_SECONDS" 300 1)"
MAX_STALE_LOCK_SECONDS="$(parse_positive_int "$MAX_STALE_LOCK_SECONDS" 900 10)"
DEFAULT_RETRY_DELAY_SECONDS="$(parse_positive_int "$DEFAULT_RETRY_DELAY_SECONDS" 5 1)"

validate_runtime_env() {
  local value
  local name
  value="${WIRTELPRIMPF_PATCHES_PER_MINOR:-100}"
  if [[ ! "$value" =~ ^[0-9]+$ ]] || [[ "$value" -ne 100 ]]; then
    log "invalid WIRTELPRIMPF_PATCHES_PER_MINOR (must be 100): ${value}"
    exit 1
  fi

  value="${WIRTELPRIMPF_MAJOR_VERSION_BUMP:-0}"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    log "invalid WIRTELPRIMPF_MAJOR_VERSION_BUMP: ${value}"
    exit 1
  fi

  value="${WIRTELPRIMPF_BREAKING_CHANGE:-0}"
  case "${value,,}" in
    1|true|yes|on|enabled|enable|0|false|no|off|disabled|disable) ;;
    *)
      log "invalid WIRTELPRIMPF_BREAKING_CHANGE: ${value}"
      exit 1
      ;;
  esac
}

validate_runtime_env

is_regular_file() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    return 1
  fi
  if [[ -L "$path" ]]; then
    return 2
  fi
  [[ -f "$path" ]]
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    log "${label} missing: $path"
    exit 1
  fi
  if [[ -L "$path" ]]; then
    log "${label} must not be a symlink: $path"
    exit 1
  fi
  if ! is_regular_file "$path"; then
    log "${label} is not a regular file: $path"
    exit 1
  fi
}

require_executable() {
  local path="$1"
  local label="$2"
  require_file "$path" "$label"
  if [[ ! -x "$path" ]]; then
    log "${label} is not executable: $path"
    exit 1
  fi
}

require_file "$PY_SCRIPT" "Generator script"

write_state() {
  local value="$1"
  if [[ -e "$STATE_FILE" ]] && ! is_regular_file "$STATE_FILE"; then
    log "state file must be regular file (no symlink or special file): $STATE_FILE"
    return 1
  fi
  local state_dir
  state_dir="$(dirname "$STATE_FILE")"
  if ! mkdir -p "$state_dir"; then
    log "failed to create state directory: $state_dir"
    return 1
  fi
  local state_tmp
  if ! state_tmp="$(mktemp "$STATE_FILE.tmp.XXXXXX")"; then
    log "failed to create state temp file from base: $STATE_FILE"
    return 1
  fi
  if ! printf '%s\n' "$value" > "$state_tmp"; then
    log "failed to write state temp file: $state_tmp"
    rm -f "$state_tmp" 2>/dev/null || true
    return 1
  fi
  if ! mv -f "$state_tmp" "$STATE_FILE"; then
    log "failed to persist state file: $STATE_FILE"
    rm -f "$state_tmp" 2>/dev/null || true
    return 1
  fi
}

refresh_state_timestamp() {
  if [[ -e "$TIMESTAMP_FILE" ]] && ! is_regular_file "$TIMESTAMP_FILE"; then
    log "timestamp file must be regular file (no symlink or special file): $TIMESTAMP_FILE"
    return 1
  fi
  local timestamp_tmp
  if ! timestamp_tmp="$(mktemp "$TIMESTAMP_FILE.tmp.XXXXXX")"; then
    log "failed to create timestamp temp file from base: $TIMESTAMP_FILE"
    return 1
  fi
  if ! date +%s > "$timestamp_tmp"; then
    log "failed to refresh timestamp file: $TIMESTAMP_FILE"
    rm -f "$timestamp_tmp" 2>/dev/null || true
    return 1
  fi
  if ! mv -f "$timestamp_tmp" "$TIMESTAMP_FILE"; then
    log "failed to persist timestamp file: $TIMESTAMP_FILE"
    rm -f "$timestamp_tmp" 2>/dev/null || true
    return 1
  fi
}

acquire_lock() {
  is_running_pid() {
    local candidate="$1"
    [[ -n "$candidate" && "$candidate" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$candidate" 2>/dev/null
  }

  if [[ -L "$LOCK_FILE" || ( -e "$LOCK_FILE" && ! -f "$LOCK_FILE" ) ]]; then
    log "invalid lock file type (symlink or non-regular): $LOCK_FILE"
    rm -f "$LOCK_TMP" 2>/dev/null || true
    return 1
  fi

  if command -v -- flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
      local pid
      if ! pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"; then
        log "failed to read lock holder pid, exiting: $LOCK_FILE"
        return 1
      fi
      pid="${pid//$'\r'/}"
      pid="${pid//$'\n'/}"
      pid="$(printf '%s' "$pid")"
      if [[ "$pid" == *[[:space:]]* ]]; then
        log "invalid lock holder pid in $LOCK_FILE: whitespace-containing value, exiting"
        return 1
      fi
      if [[ -n "$pid" && ! "$pid" =~ ^[0-9]+$ ]]; then
        log "invalid lock holder pid in $LOCK_FILE: ${pid:-unknown}, exiting"
        return 1
      fi
      log "another watcher instance is running (flock), exiting (holder=${pid:-unknown})"
      return 1
    fi
    printf '%s\n' "$$" 1>&9
    trap 'flock -u 9 2>/dev/null || true; exec 9>&- 2>/dev/null || true; rm -f "$LOCK_FILE" "$TIMESTAMP_FILE" 2>/dev/null || true' EXIT
    return
  fi

  if ! LOCK_TMP="$(mktemp "${LOCK_FILE}.tmp.XXXXXX")"; then
    log "failed to create temporary lock file under $(dirname "$LOCK_FILE")"
    return 1
  fi
  if ! printf '%s\n' "$$" > "$LOCK_TMP"; then
    log "failed to write temporary lock holder pid: $LOCK_TMP"
    rm -f "$LOCK_TMP" 2>/dev/null || true
    return 1
  fi

  if [[ -e "$LOCK_FILE" ]]; then
    local pid
    if ! pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"; then
      log "failed to read lock file, exiting: $LOCK_FILE"
      rm -f "$LOCK_TMP" 2>/dev/null || true
      return 1
    fi
    pid="${pid//$'\r'/}"
    pid="${pid//$'\n'/}"
    pid="$(printf '%s' "$pid")"
    if [[ "$pid" == *[[:space:]]* ]]; then
      log "invalid lock holder pid in $LOCK_FILE: whitespace-containing value, exiting"
      rm -f "$LOCK_TMP" 2>/dev/null || true
      return 1
    fi
    if [[ -f "$LOCK_FILE" ]]; then
      local now
      now=$(date +%s)
      local lock_mtime age
      lock_mtime=$(stat -c '%Y' "$LOCK_FILE" 2>/dev/null || echo "$now")
      age=$((now - lock_mtime))
      if [[ -n "$pid" && ! "$pid" =~ ^[0-9]+$ ]]; then
        log "fallback lock file has invalid pid value (${pid}), refusing to steal fresh lock"
        rm -f "$LOCK_TMP" 2>/dev/null || true
        return 1
      fi
      if [[ "$age" -lt "$MAX_STALE_LOCK_SECONDS" ]] && is_running_pid "$pid"; then
        log "another watcher instance is running (fallback lock), exiting"
        rm -f "$LOCK_TMP" 2>/dev/null || true
        return 1
      fi
      log "stale fallback lock detected (${age}s), stealing lock"
      if ! rm -f "$LOCK_FILE"; then
        log "failed to remove stale fallback lock: $LOCK_FILE"
        rm -f "$LOCK_TMP" 2>/dev/null || true
        return 1
      fi
    fi
  fi

  if ! mv "$LOCK_TMP" "$LOCK_FILE"; then
    log "failed to acquire fallback lock file via rename: $LOCK_TMP -> $LOCK_FILE"
    rm -f "$LOCK_TMP" 2>/dev/null || true
    return 1
  fi
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
        raise SystemExit(f"invalid publish state file: {state_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid publish state: expected JSON object in {state_path}")
    if payload is not None:
        if "patch_count" in payload:
            state_patch_count = payload["patch_count"]
        elif "patch_version" in payload:
            state_patch_count = payload["patch_version"]
        else:
            raise SystemExit(f"invalid publish state: missing patch_count and patch_version in {state_path}")
    if not isinstance(state_patch_count, int) or isinstance(state_patch_count, bool):
        raise SystemExit(
            f"invalid publish state: patch_count must be a non-boolean integer in {state_path}: {state_patch_count!r}"
        )
    if state_patch_count < 0:
        raise SystemExit(
            f"invalid publish state: patch_count must be >= 0 in {state_path}: {state_patch_count!r}"
        )

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
breaking_raw = os.environ.get("WIRTELPRIMPF_BREAKING_CHANGE", "0")

def parse_positive_int(name, value):
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        raise SystemExit(f"invalid {name} value: {value!r}. Expected integer >= 1")
    if parsed < 1:
        raise SystemExit(f"invalid {name} value: {value!r}. Expected integer >= 1")
    return parsed

def parse_non_negative_int(name, value):
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        raise SystemExit(f"invalid {name} value: {value!r}. Expected integer >= 0")
    if parsed < 0:
        raise SystemExit(f"invalid {name} value: {value!r}. Expected integer >= 0")
    return parsed

def parse_bool(name, value):
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled", "enable"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled", "disable"}:
        return False
    raise SystemExit(f"invalid {name} value: {value!r}")

patches_per_minor = parse_positive_int("WIRTELPRIMPF_PATCHES_PER_MINOR", patches_per_minor_raw)
if patches_per_minor != PATCHES_PER_MINOR:
    raise SystemExit(f"invalid WIRTELPRIMPF_PATCHES_PER_MINOR value: {patches_per_minor!r}, expected {PATCHES_PER_MINOR}")
major_bump = parse_non_negative_int("WIRTELPRIMPF_MAJOR_VERSION_BUMP", major_bump_raw)
breaking_change = parse_bool("WIRTELPRIMPF_BREAKING_CHANGE", breaking_raw)

if state_patch_count == 0:
    print(f"{major_str}.{minor_str}.0{suffix}")
    raise SystemExit(0)

patch_version = state_patch_count % patches_per_minor
if patch_version == 0:
    patch_version = PATCHES_PER_MINOR_FOR_MINOR

minor_increments = state_patch_count // patches_per_minor
major_addition, minor_offset = divmod(int(minor_str) + minor_increments, MINORS_PER_MAJOR)
major_version = int(major_str) + major_addition + major_bump + (1 if breaking_change else 0)
print(f"{major_version}.{minor_offset}.{patch_version}{suffix}")

PY
}

read_state_version() {
  local value
  if [[ -e "$STATE_FILE" ]] && ! is_regular_file "$STATE_FILE"; then
    log "state file is not a regular file: $STATE_FILE"
    echo ""
    return
  fi
  if ! value="$(cat "$STATE_FILE" 2>/dev/null || true)"; then
    log "failed to read state file: $STATE_FILE"
    echo ""
    return
  fi
  if [[ -z "$value" ]]; then
    echo ""
    return
  fi
  if is_valid_version "$value"; then
    echo "$value"
    return
  fi
  log "state file contains invalid version: $value"
  echo ""
}

is_valid_version() {
  local value="$1"
  [[ "$value" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9._-]+)?$ ]]
}

sync_state_file() {
  local computed="$1"
  if ! is_valid_version "$computed"; then
    log "invalid computed version supplied to sync_state_file: $computed"
    return 1
  fi

  local current
  current="$(read_state_version)"

  if [[ -z "$current" ]]; then
    if [[ -f "$STATE_FILE" ]]; then
      log "state file missing or invalid; repaired with computed version $computed"
    fi
    if ! write_state "$computed"; then
      log "refusing to continue without state file: $STATE_FILE"
      return 1
    fi
    echo "$computed"
    return
  fi

  if [[ "$current" != "$computed" ]]; then
    log "state file stale; repaired to current version $computed"
    if ! write_state "$computed"; then
      log "refusing to continue without state file: $STATE_FILE"
      return 1
    fi
    echo "$computed"
    return
  fi

  echo "$current"
}

apply_version_change() {
  local previous="$1"
  local current="$2"

  if ! is_valid_version "$previous" || ! is_valid_version "$current"; then
    log "invalid version value in apply_version_change: $previous -> $current"
    return 1
  fi

  require_file "$CHECKS_SCRIPT" "Checks script"
  require_executable "$CHECKS_SCRIPT" "Checks script"

  log "minor version changed: $previous -> $current"

  if "$CHECKS_SCRIPT"; then
    if ! refresh_state_timestamp; then
      log "failed to refresh state timestamp; aborting"
      return 1
    fi
    log "checks completed for version $current"
  else
    log "checks failed for version $current"
    return 1
  fi

  if ! write_state "$current"; then
    log "refusing to continue because state update for version $current failed"
    return 1
  fi

  return 0
}

acquire_lock

if ! init_state="$(get_minor_version)"; then
  log "failed to derive initial minor version from publish state"
  exit 1
fi
if [[ -z "$init_state" ]]; then
  log "failed to derive initial minor version from publish state"
  exit 1
fi
if ! is_valid_version "$init_state"; then
  log "invalid initial version from publish state: $init_state"
  exit 1
fi

if ! state_file_value="$(sync_state_file "$init_state")"; then
  log "failed to sync minor version state file"
  exit 1
fi
if [[ -z "$state_file_value" ]]; then
  log "state synchronization produced empty version"
  exit 1
fi

if [[ "${1:-}" == "--once" ]]; then
  require_file "$CHECKS_SCRIPT" "Checks script"
  require_executable "$CHECKS_SCRIPT" "Checks script"
  prev="$state_file_value"
  if ! is_valid_version "$prev"; then
    log "invalid previous version in state: $prev"
    exit 1
  fi
  if ! current="$(get_minor_version)"; then
    log "failed to compute current minor version"
    exit 1
  fi
  if [[ -z "$current" ]]; then
    log "current minor version is empty"
    exit 1
  fi
  if ! is_valid_version "$current"; then
    log "invalid derived current version: $current"
    exit 1
  fi
  if [[ "$current" != "$prev" ]]; then
    if ! apply_version_change "$prev" "$current"; then
      exit 1
    fi
  fi
  exit 0
fi

last_version="$state_file_value"
while true; do
	if ! current="$(get_minor_version)"; then
		log "failed to compute current minor version"
		exit 1
	fi
	if [[ -z "$current" ]]; then
		log "current minor version is empty"
		exit 1
	fi
	if ! is_valid_version "$current"; then
	  log "invalid derived current version: $current"
	  exit 1
	fi

  if [[ "$current" != "$last_version" ]]; then
	    if ! apply_version_change "$last_version" "$current"; then
	      exit 1
	    fi
      last_version="$current"
    sleep "$DEFAULT_RETRY_DELAY_SECONDS"
    continue
  fi

  if [[ -f "$TIMESTAMP_FILE" ]]; then
    now_epoch="$(date +%s)"
    if ! last_epoch="$(cat "$TIMESTAMP_FILE" 2>/dev/null || true)"; then
      log "failed to read timestamp file: $TIMESTAMP_FILE"
      last_epoch=""
    fi
    if [[ ! "$last_epoch" =~ ^[0-9]+$ ]]; then
      log "invalid timestamp file content, refreshing: $last_epoch"
      if ! refresh_state_timestamp; then
        log "failed to refresh timestamp file: $TIMESTAMP_FILE"
        exit 1
      fi
      sleep "$DEFAULT_RETRY_DELAY_SECONDS"
      continue
    fi
    if ((now_epoch - last_epoch < 1)); then
      sleep "$DEFAULT_RETRY_DELAY_SECONDS"
      continue
    fi
  fi

  sleep "$SLEEP_SECONDS"
done
