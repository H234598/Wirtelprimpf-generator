#!/usr/bin/env bash
set -euo pipefail
umask 077
IFS=$'\n\t'

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_UID="$(id -u)"
readonly CURRENT_UID
if [[ -n "${PYTHON_BIN:-}" && ("${PYTHON_BIN}" == *[[:space:]]* || "${PYTHON_BIN}" == *[$'\r\n\t\v\f']* || "${PYTHON_BIN}" != "${PYTHON_BIN//[^a-zA-Z0-9._-]/}") ]]; then
  log "PYTHON_BIN contains invalid characters: ${PYTHON_BIN}"
  exit 1
fi

log() {
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
}

declare -ar SECURITY_PATHS_ARRAY=(/usr/local/sbin /usr/local/bin /usr/sbin /usr/bin /sbin /bin)
declare -r SECURITY_BIN_NAME_PATTERNS="python3|python3\.[0-9]+"
declare -ar SECURITY_PYTHON_CANDIDATES=("python3")
declare -i HAS_FINDMNT_CMD=0
declare -i HAS_FILE_CMD=0
if command -v findmnt >/dev/null 2>&1; then
  HAS_FINDMNT_CMD=1
fi
if command -v file >/dev/null 2>&1; then
  HAS_FILE_CMD=1
fi
readonly HAS_FINDMNT_CMD HAS_FILE_CMD

is_valid_python_binary_name() {
  local candidate="$1"
  [[ "$candidate" != */* ]]
  [[ "$candidate" =~ ^($SECURITY_BIN_NAME_PATTERNS)$ ]]
}

is_valid_python_candidate() {
  local candidate="$1"
  [[ -n "$candidate" ]]
  [[ "$candidate" != -* ]]
  is_valid_python_binary_name "$candidate"
}

resolve_python() {
  local candidates=("${PYTHON_BIN:-}")
  if [[ -n "${PYTHON_BIN:-}" ]] && ! is_valid_python_binary_name "$PYTHON_BIN"; then
    return 1
  fi
  local fallback_set=1
  if [[ -z "${candidates[0]:-}" ]]; then
    candidates=("${SECURITY_PYTHON_CANDIDATES[@]}")
    fallback_set=0
  fi

  local candidate resolved search_path resolved_canonical
  for candidate in "${candidates[@]}"; do
    if ! is_valid_python_candidate "$candidate"; then
      continue
    fi
    for search_path in "${SECURITY_PATHS_ARRAY[@]}"; do
      resolved="${search_path}/${candidate}"
      if ! [[ -f "$resolved" && -x "$resolved" && ! -L "$resolved" ]]; then
        continue
      fi
      resolved_canonical=""
      if ! resolved_canonical="$(readlink -f -- "$resolved" 2>/dev/null)"; then
        continue
      fi
      if [[ "$resolved_canonical" != "$resolved" || ! -x "$resolved_canonical" || -L "$resolved_canonical" ]]; then
        continue
      fi
      case "$resolved_canonical" in
        /usr/local/sbin/*|/usr/local/bin/*|/usr/sbin/*|/usr/bin/*|/sbin/*|/bin/*)
          ;;
        *)
          continue
          ;;
      esac
      echo "$resolved_canonical"
      return 0
    done
    if (( fallback_set == 1 )); then
      break
    fi
  done

  return 1
}

validate_python_binary() {
  local path="$1"

  local resolved mountpoint mount_opts parent_dir
  local resolved_mode resolved_owner parent_mode parent_owner mountpoint_owner mountpoint_mode
  local file_type

  if [[ -z "$path" ]]; then
    return 1
  fi
  if [[ "$path" != /* ]]; then
    return 1
  fi
  if [[ -L "$path" ]]; then
    return 1
  fi
  if ! resolved="$(readlink -f -- "$path" 2>/dev/null)"; then
    return 1
  fi
  if [[ ! -f "$resolved" || ! -r "$resolved" ]]; then
    return 1
  fi
  parent_dir="$(dirname -- "$resolved")"
  if [[ -L "$parent_dir" || ! -d "$parent_dir" ]]; then
    return 1
  fi
  case "$resolved" in
    /usr/local/sbin/*|/usr/local/bin/*|/usr/sbin/*|/usr/bin/*|/sbin/*|/bin/*)
      ;;
    *)
      return 1
      ;;
  esac
  local base_name="${resolved##*/}"
  if [[ ! "$base_name" =~ ^($SECURITY_BIN_NAME_PATTERNS)$ ]]; then
    return 1
  fi
  if [[ "$resolved" == /tmp/* || "$resolved" == /var/tmp/* || "$resolved" == /run/* || "$resolved" == /dev/* ]]; then
    return 1
  fi
  if ! read -r resolved_mode resolved_owner mountpoint <<<"$(stat -c '%a %u %m' "$resolved" 2>/dev/null)"; then
    return 1
  fi
  if [[ ! -d "$mountpoint" ]]; then
    return 1
  fi
  if [[ -L "$mountpoint" ]]; then
    return 1
  fi
  if ! read -r parent_mode parent_owner <<<"$(stat -c '%a %u' "$parent_dir" 2>/dev/null)"; then
    return 1
  fi
  if ! read -r mountpoint_mode mountpoint_owner <<<"$(stat -c '%a %u' "$mountpoint" 2>/dev/null)"; then
    return 1
  fi
  if [[ "$resolved_owner" != "$CURRENT_UID" && "$resolved_owner" != 0 ]]; then
    return 1
  fi
  if [[ "$mountpoint_owner" != "$CURRENT_UID" && "$mountpoint_owner" != 0 ]]; then
    return 1
  fi
  if [[ "$parent_owner" != "$CURRENT_UID" && "$parent_owner" != 0 ]]; then
    return 1
  fi
  if (( 10#$mountpoint_mode & 022 )); then
    return 1
  fi
  if (( 10#$parent_mode & 022 )); then
    return 1
  fi
  if (( 10#$resolved_mode & 022 )); then
    return 1
  fi
  if (( 10#$resolved_mode & 06000 )); then
    return 1
  fi
  if (( (10#$resolved_mode & 0111) == 0 )); then
    return 1
  fi
  if (( HAS_FINDMNT_CMD )); then
    mount_opts="$(findmnt -n -o OPTIONS "$mountpoint" 2>/dev/null || true)"
    if [[ ",${mount_opts}," == *",noexec,"* ]]; then
      return 1
    fi
    if [[ ",${mount_opts}," == *",nosuid,"* ]]; then
      return 1
    fi
    if [[ ",${mount_opts}," == *",nodev,"* ]]; then
      return 1
    fi
  else
    return 1
  fi
  if (( HAS_FILE_CMD )); then
    if ! file_type="$(file -b -- "$resolved" 2>/dev/null || true)"; then
      return 1
    fi
    if [[ "$file_type" != *ELF* && "$file_type" != *"Python script"* ]]; then
      return 1
    fi
  else
    return 1
  fi
  return 0
}

if ! PY="$(resolve_python)"; then
  log "no usable python interpreter found (tried: ${PYTHON_BIN:+$PYTHON_BIN }python3 python)"
  exit 1
fi
if ! validate_python_binary "$PY"; then
  log "invalid or insecure python interpreter: ${PY}"
  exit 1
fi
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
for WATCH_BASH_PATH in /usr/bin/bash /bin/bash; do
  if [[ -f "$WATCH_BASH_PATH" && -x "$WATCH_BASH_PATH" && ! -L "$WATCH_BASH_PATH" ]]; then
    break
  fi
  WATCH_BASH_PATH=""
done
if [[ -z "$WATCH_BASH_PATH" ]]; then
  log "required bash interpreter unavailable: neither /usr/bin/bash nor /bin/bash is present/executable"
  exit 1
fi
readonly WATCH_BASH_PATH

run_isolated_env() {
  env -i \
    PATH="/usr/local/bin:/usr/bin:/bin" \
    HOME="/tmp" \
    TMPDIR="/tmp" \
    TMP="/tmp" \
    TEMP="/tmp" \
    USER="" \
    LOGNAME="" \
    SHELL="/bin/bash" \
    BASH_ENV="" \
    ENV="" \
    BASH_XTRACEFD="" \
    HISTFILE="/dev/null" \
    SHLVL="0" \
    PROMPT_COMMAND="" \
    LD_PRELOAD="" \
    LD_LIBRARY_PATH="" \
    PYTHONINSPECT="" \
    PYTHONOPTIMIZE="" \
    PYTHONFAULTHANDLER="" \
    PYTHONMALLOC="" \
    PYTHONSTARTUP= \
    PYTHONPATH= \
    PYTHONHOME= \
    PYTHONSAFEPATH=1 \
    PYTHONUSERBASE= \
    PYTHONNOUSERSITE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    LC_ALL="C.UTF-8" \
    LANG="C.UTF-8" \
    TERM="xterm-256color" \
    "$@"
}

run_python_sandbox() {
  run_isolated_env "$@"
}

run_check_script_sandboxed() {
  local script_path="$1"
  local script_canonical
  local bash_mode
  local bash_canonical
  if [[ -z "$script_path" ]]; then
    log "checks script path is empty"
    return 1
  fi
  if [[ "$script_path" != /* ]]; then
    log "checks script path must be absolute: ${script_path}"
    return 1
  fi
  if [[ -L "$script_path" || ! -f "$script_path" || ! -x "$script_path" ]]; then
    log "checks script must be a non-symlink executable file: ${script_path}"
    return 1
  fi
  script_canonical="$(readlink -f -- "$script_path" 2>/dev/null || true)"
  if [[ -z "$script_canonical" || "$script_canonical" != "$script_path" ]]; then
    log "checks script path must be canonical and non-symlinked: ${script_path}"
    return 1
  fi
  if ! is_owned_by_current_user "$script_canonical"; then
    log "checks script must be owned by current user: ${script_path}"
    return 1
  fi
  local script_perm
  if ! script_perm="$(stat -c '%a' "$script_canonical" 2>/dev/null)"; then
    log "checks script permissions unavailable: ${script_path}"
    return 1
  fi
  if (( 10#$script_perm & 022 )); then
    log "checks script must not be group/world writable: ${script_path}"
    return 1
  fi
  if (( 10#$script_perm & 06000 )); then
    log "checks script must not contain setuid/setgid bits: ${script_path}"
    return 1
  fi
  local script_dir
  script_dir="$(dirname -- "$script_path")"
  if [[ -L "$script_dir" ]]; then
    log "checks script directory must not be a symlink: ${script_dir}"
    return 1
  fi
  if ! is_owned_by_current_user "$script_dir"; then
    log "checks script directory must be owned by current user: ${script_dir}"
    return 1
  fi
  local script_dir_perm
  if ! script_dir_perm="$(stat -c '%a' "$script_dir" 2>/dev/null)"; then
    log "checks script directory permissions unavailable: ${script_dir}"
    return 1
  fi
  if (( 10#$script_dir_perm & 022 )); then
    log "checks script directory must not be group/world writable: ${script_dir}"
    return 1
  fi
  if [[ -z "$WATCH_BASH_PATH" || -L "$WATCH_BASH_PATH" || ! -x "$WATCH_BASH_PATH" ]]; then
    log "required bash interpreter unavailable or insecure: ${WATCH_BASH_PATH:-not-found}"
    return 1
  fi
  if ! is_owned_by_current_user "$WATCH_BASH_PATH"; then
    log "required bash interpreter must be owned by current user: ${WATCH_BASH_PATH}"
    return 1
  fi
  if ! bash_mode="$(stat -c '%a' "$WATCH_BASH_PATH" 2>/dev/null)"; then
    log "required bash permissions unavailable: ${WATCH_BASH_PATH}"
    return 1
  fi
  bash_canonical="$(readlink -f -- "$WATCH_BASH_PATH" 2>/dev/null || true)"
  if [[ -z "$bash_canonical" || "$bash_canonical" != "$WATCH_BASH_PATH" ]]; then
    log "required bash path must be canonical and non-symlinked: ${WATCH_BASH_PATH}"
    return 1
  fi
  if (( 10#$bash_mode & 022 )); then
    log "required bash interpreter must not be group/world writable: ${WATCH_BASH_PATH}"
    return 1
  fi
  if (( 10#$bash_mode & 06000 )); then
    log "required bash interpreter must not have setuid/setgid bits: ${WATCH_BASH_PATH}"
    return 1
  fi
  if ! run_isolated_env "$bash_canonical" --noprofile --norc "$script_canonical"; then
    log "checks script execution failed: ${script_path}"
    return 1
  fi
  return 0
}

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
  if [[ -e "$parent_dir" ]]; then
    require_directory "$parent_dir" "publish state directory" "rx"
  fi
}

validate_publish_state_file() {
  local publish_state_file="$1"
  if [[ -e "$publish_state_file" ]]; then
    if ! is_regular_file "$publish_state_file"; then
      log "publish state file must be a regular file: ${publish_state_file}"
      exit 1
    fi
    if [[ -L "$publish_state_file" ]]; then
      log "publish state file must not be a symlink: ${publish_state_file}"
      exit 1
    fi
    if ! is_owned_by_current_user "$publish_state_file"; then
      log "publish state file must be owned by current user: ${publish_state_file}"
      exit 1
    fi
    if [[ ! -r "$publish_state_file" ]]; then
      log "publish state file is not readable: ${publish_state_file}"
      exit 1
    fi
    local publish_state_perm
    if ! publish_state_perm="$(stat -c '%a' "$publish_state_file" 2>/dev/null)"; then
      log "publish state file metadata unavailable: ${publish_state_file}"
      exit 1
    fi
    if (( 10#$publish_state_perm & 022 )); then
      log "publish state file must not be group/world writable: ${publish_state_file}"
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
validate_watch_runtime_file_path "$STATE_FILE" "State file"
validate_watch_runtime_file_path "$LOCK_FILE" "Lock file"
validate_watch_runtime_file_path "$TIMESTAMP_FILE" "Timestamp file"

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

TIMESTAMP_FILE="${TIMESTAMP_FILE:-$STATE_FILE.started_at}"

dependency_signature() {
  local path="$1"
  local parent
  local signature
  local parent_mode parent_meta owner group mode mtime inode size
  if [[ "$path" != "$PY_SCRIPT" && "$path" != "$PUBLISH_STATE_FILE" ]]; then
    return 1
  fi
  if [[ -z "$path" ]]; then
    return 1
  fi
  if [[ -L "$path" || ! -f "$path" || ! -r "$path" ]]; then
    return 1
  fi
  parent="$(dirname -- "$path")"
  if [[ "$parent" == /tmp/* || "$parent" == /var/tmp/* || "$parent" == /run/* || "$parent" == /dev/* ]]; then
    return 1
  fi
  if [[ -L "$parent" ]]; then
    return 1
  fi
  if [[ ! -d "$parent" ]]; then
    return 1
  fi
  if [[ ! -r "$parent" || ! -x "$parent" || ! -w "$parent" ]]; then
    return 1
  fi
  if ! parent_meta="$(stat -c '%a:%u' "$parent" 2>/dev/null)"; then
    return 1
  fi
  if ! IFS=':' read -r parent_mode parent_owner <<< "$parent_meta"; then
    return 1
  fi
  if [[ "$parent_owner" != "$CURRENT_UID" ]]; then
    return 1
  fi
  if (( 10#$parent_mode & 022 )); then
    return 1
  fi
  if [[ ! -f "$path" ]]; then
    return 1
  fi
  if [[ ! -r "$path" ]]; then
    return 1
  fi
  local owner group mode mtime inode size meta
  if ! meta="$(stat -c '%u:%g:%a:%Y:%i:%s' "$path" 2>/dev/null)"; then
    return 1
  fi
  IFS=':' read -r owner group mode mtime inode size <<< "$meta"
  if [[ -z "$owner" || -z "$group" || -z "$mode" || -z "$mtime" || -z "$inode" || -z "$size" ]]; then
    return 1
  fi
  if (( 10#$owner != CURRENT_UID )); then
    return 1
  fi
  if (( 10#$owner < 1 )); then
    return 1
  fi
  if (( 10#$mode & 022 )); then
    return 1
  fi
  if (( 10#$mode & 06000 )); then
    return 1
  fi
  signature="$(printf '%s:%s:%s:%s:%s:%s\n' "$owner" "$group" "$mode" "$mtime" "$inode" "$size")"
  echo "$signature"
  return 0
}

require_directory() {
  local path="$1"
  local label="$2"
  local mode="${3:-rx}"
  local perm owner
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
  if ! owner="$(stat -c '%u' "$path" 2>/dev/null || true)"; then
    log "${label} failed to read owner: $path"
    exit 1
  fi
  if [[ "$owner" != "$CURRENT_UID" ]]; then
    log "${label} must be owned by current user: $path"
    exit 1
  fi
  if ! perm="$(stat -c '%a' "$path" 2>/dev/null || true)"; then
    log "${label} failed to read permissions: $path"
    exit 1
  fi
  if (( 10#$perm & 022 )); then
    log "${label} must not be group/world writable: $path"
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

is_secure_regular_file() {
  local path="$1"
  local owner perm

  if [[ -z "$path" ]]; then
    return 1
  fi
  if [[ -L "$path" ]]; then
    return 1
  fi
  if ! is_regular_file "$path"; then
    return 1
  fi
  if [[ ! -r "$path" || ! -w "$path" || ! -x "$path" ]]; then
    return 1
  fi
  if ! owner="$(stat -c '%u' "$path" 2>/dev/null)"; then
    return 1
  fi
  if [[ "$owner" != "$CURRENT_UID" ]]; then
    return 1
  fi
  if ! perm="$(stat -c '%a' "$path" 2>/dev/null)"; then
    return 1
  fi
  if (( 10#$perm & 022 )); then
    return 1
  fi
  return 0
}

is_owned_by_current_user() {
  local path="$1"
  local owner
  if ! owner="$(stat -c '%u' "$path" 2>/dev/null)"; then
    return 1
  fi
  [[ "$owner" == "$CURRENT_UID" ]]
}

require_file() {
  local path="$1"
  local label="$2"
  local perm
  if [[ ! -f "$path" ]]; then
    log "${label} missing: $path"
    exit 1
  fi
  if [[ -L "$path" ]]; then
    log "${label} must not be a symlink: $path"
    exit 1
  fi
  if ! is_secure_regular_file "$path"; then
    log "${label} must be a secure regular file owned by current user: $path"
    exit 1
  fi
  if ! perm="$(stat -c '%a' "$path" 2>/dev/null)"; then
    log "${label} failed to read permissions: $path"
    exit 1
  fi
  if (( 10#$perm & 022 )); then
    log "${label} must not be group/world writable: $path"
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

validate_watch_runtime_file_path() {
  local path="$1"
  local label="$2"
  local parent
  local canonical
  if [[ -z "$path" ]]; then
    log "${label} path is empty"
    exit 1
  fi
  if ! canonical="$(readlink -f -- "$path" 2>/dev/null || true)"; then
    log "${label} path is not canonicalizable: ${path}"
    exit 1
  fi
  if [[ -z "$canonical" || "$canonical" != "$path" ]]; then
    log "${label} path must be canonical and non-symlinked: ${path}"
    exit 1
  fi
  if [[ "$canonical" != "${ROOT_DIR}/Sourcecode/"* ]]; then
    log "${label} path must be under ${ROOT_DIR}/Sourcecode/: $path"
    exit 1
  fi
  if [[ "$path" == *[[:space:]]* ]]; then
    log "${label} path contains whitespace: ${path}"
    exit 1
  fi
  if [[ "$canonical" == /tmp/* || "$canonical" == /var/tmp/* || "$canonical" == /run/* || "$canonical" == /dev/* ]]; then
    log "${label} path points into transient/unsafe location: $path"
    exit 1
  fi
  parent="$(dirname -- "$canonical")"
  if [[ -L "$parent" ]]; then
    log "${label} parent directory must not be a symlink: $parent"
    exit 1
  fi
  require_directory "$parent" "${label} parent directory" "rwx"
}

require_file "$PY_SCRIPT" "Generator script"

write_state() {
  local value="$1"
  if [[ -e "$STATE_FILE" ]] && ! is_regular_file "$STATE_FILE"; then
    log "state file must be regular file (no symlink or special file): $STATE_FILE"
    return 1
  fi
  if [[ -L "$STATE_FILE" ]]; then
    log "state file must not be a symlink: $STATE_FILE"
    return 1
  fi
  if [[ -e "$STATE_FILE" ]] && ! is_owned_by_current_user "$STATE_FILE"; then
    log "state file must be owned by current user: $STATE_FILE"
    return 1
  fi
  if [[ -e "$STATE_FILE" ]] && [[ ! -w "$STATE_FILE" ]]; then
    log "state file not writable: $STATE_FILE"
    return 1
  fi
  if [[ -e "$STATE_FILE" ]]; then
    local state_perm
    if ! state_perm="$(stat -c '%a' "$STATE_FILE" 2>/dev/null)"; then
      log "failed to read state file permissions: $STATE_FILE"
      return 1
    fi
    if (( 10#$state_perm & 022 )); then
      log "state file must not be group/world writable: $STATE_FILE"
      return 1
    fi
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
  if [[ "$state_tmp" != "$(dirname -- "$STATE_FILE")"/* ]]; then
    log "state temporary file escaped state directory: $state_tmp"
    rm -f "$state_tmp" 2>/dev/null || true
    return 1
  fi
  if [[ -L "$state_tmp" || ! -f "$state_tmp" ]]; then
    log "state temporary file must be regular and non-symlink: $state_tmp"
    rm -f "$state_tmp" 2>/dev/null || true
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
  local value
  if [[ -e "$TIMESTAMP_FILE" ]] && ! is_regular_file "$TIMESTAMP_FILE"; then
    log "timestamp file must be regular file (no symlink or special file): $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -L "$TIMESTAMP_FILE" ]]; then
    log "timestamp file must not be a symlink: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -e "$TIMESTAMP_FILE" ]] && ! is_owned_by_current_user "$TIMESTAMP_FILE"; then
    log "timestamp file must be owned by current user: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -e "$TIMESTAMP_FILE" ]] && [[ ! -w "$TIMESTAMP_FILE" ]]; then
    log "timestamp file not writable: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -e "$TIMESTAMP_FILE" ]]; then
    local timestamp_perm
    if ! timestamp_perm="$(stat -c '%a' "$TIMESTAMP_FILE" 2>/dev/null)"; then
      log "failed to read timestamp file permissions: $TIMESTAMP_FILE"
      return 1
    fi
    if (( 10#$timestamp_perm & 022 )); then
      log "timestamp file must not be group/world writable: $TIMESTAMP_FILE"
      return 1
    fi
  fi
  local state_dir
  state_dir="$(dirname "$TIMESTAMP_FILE")"
  require_directory "$state_dir" "timestamp directory" "rwx"

  local timestamp_tmp
  if ! timestamp_tmp="$(mktemp "$TIMESTAMP_FILE.tmp.XXXXXX")"; then
    log "failed to create timestamp temp file from base: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ "$timestamp_tmp" != "$(dirname -- "$TIMESTAMP_FILE")"/* ]]; then
    log "timestamp temporary file escaped timestamp directory: $timestamp_tmp"
    rm -f "$timestamp_tmp" 2>/dev/null || true
    return 1
  fi
  if [[ -L "$timestamp_tmp" || ! -f "$timestamp_tmp" ]]; then
    log "timestamp temporary file must be regular and non-symlink: $timestamp_tmp"
    rm -f "$timestamp_tmp" 2>/dev/null || true
    return 1
  fi
  value="$(date +%s)"
  if ! printf '%s\n' "$value" > "$timestamp_tmp"; then
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

read_timestamp_epoch() {
  local value
  local timestamp_perm
  if ! validate_runtime_file_for_read "$TIMESTAMP_FILE" "Timestamp file"; then
    return 1
  fi
  if ! timestamp_perm="$(stat -c '%a' "$TIMESTAMP_FILE" 2>/dev/null)"; then
    log "failed to read timestamp metadata: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -e "$TIMESTAMP_FILE" ]] && ! is_regular_file "$TIMESTAMP_FILE"; then
    log "timestamp file is not a regular file: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -e "$TIMESTAMP_FILE" ]] && ! is_owned_by_current_user "$TIMESTAMP_FILE"; then
    log "timestamp file not owned by current user: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -e "$TIMESTAMP_FILE" ]] && [[ ! -r "$TIMESTAMP_FILE" ]]; then
    log "timestamp file not readable: $TIMESTAMP_FILE"
    return 1
  fi
  if (( 10#$timestamp_perm & 022 )); then
    log "timestamp file has insecure permissions (group/world writable): $TIMESTAMP_FILE"
    return 1
  fi
  if ! value="$(cat "$TIMESTAMP_FILE" 2>/dev/null || true)"; then
    log "failed to read timestamp file: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ -z "$value" ]]; then
    log "timestamp file is empty: $TIMESTAMP_FILE"
    return 1
  fi
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    log "timestamp file is not numeric: $TIMESTAMP_FILE"
    return 1
  fi
  echo "$value"
}

cleanup_lock_tmp() {
  if [[ -n "$LOCK_TMP" ]]; then
    rm -f "$LOCK_TMP" 2>/dev/null || true
  fi
}

safe_unlink_runtime_file() {
  local path="$1"
  local owner perm
  if [[ -z "$path" ]]; then
    return 1
  fi
  if [[ -L "$path" ]]; then
    return 1
  fi
  if [[ ! -e "$path" ]]; then
    return 0
  fi
  if ! owner="$(stat -c '%u' "$path" 2>/dev/null)"; then
    return 1
  fi
  if [[ "$owner" != "$CURRENT_UID" ]]; then
    return 1
  fi
  if ! perm="$(stat -c '%a' "$path" 2>/dev/null)"; then
    return 1
  fi
  if (( 10#$perm & 022 )); then
    return 1
  fi
  if ! is_regular_file "$path"; then
    return 1
  fi
  rm -f "$path" 2>/dev/null || return 1
}

cleanup_lock_fd() {
  exec 9>&- 2>/dev/null || true
}

is_strict_positive_pid() {
  local candidate="$1"

  if [[ -z "$candidate" ]]; then
    return 1
  fi
  if [[ "$candidate" == *[[:space:]]* ]]; then
    return 1
  fi
  if ! [[ "$candidate" =~ ^[1-9][0-9]*$ ]]; then
    return 1
  fi
  return 0
}

validate_lock_file() {
  local path="$1"
  local mode
  if [[ -L "$path" ]]; then
    log "lock file must not be a symlink: $path"
    return 1
  fi
  if [[ -e "$path" ]]; then
    if ! is_secure_regular_file "$path"; then
      log "lock file must be a secure regular file: $path"
      return 1
    fi
    if ! mode="$(stat -c '%a' "$path" 2>/dev/null)"; then
      log "lock file metadata unavailable: $path"
      return 1
    fi
    if (( 10#$mode & 022 )); then
      log "lock file must not be group/world writable: $path"
      return 1
    fi
  fi
  return 0
}

validate_runtime_file_for_read() {
  local path="$1"
  local label="$2"
  local canonical parent

  if [[ -z "$path" ]]; then
    log "${label} path is empty"
    return 1
  fi
  if ! canonical="$(readlink -f -- "$path" 2>/dev/null || true)"; then
    log "${label} path is not canonicalizable: $path"
    return 1
  fi
  if [[ -z "$canonical" || "$canonical" != "$path" ]]; then
    log "${label} path must be canonical and non-symlinked: $path"
    return 1
  fi
  if [[ -L "$canonical" ]]; then
    log "${label} must not be a symlink: $path"
    return 1
  fi
  parent="$(dirname -- "$canonical")"
  if [[ "$parent" == /tmp/* || "$parent" == /var/tmp/* || "$parent" == /run/* || "$parent" == /dev/* ]]; then
    log "${label} points into transient/unsafe location: $path"
    return 1
  fi
  if [[ -L "$parent" ]]; then
    log "${label} parent directory must not be a symlink: $parent"
    return 1
  fi
  if ! require_directory "$parent" "${label} parent directory" "rwx"; then
    return 1
  fi
}

acquire_lock() {
  is_running_pid() {
    local candidate="$1"
    if ! is_strict_positive_pid "$candidate"; then
      return 1
    fi
    if [[ ! -r "/proc/$candidate" ]]; then
      return 1
    fi
    if [[ "$(stat -c '%u' "/proc/$candidate" 2>/dev/null)" != "$CURRENT_UID" ]]; then
      return 1
    fi
    kill -0 "$candidate" 2>/dev/null
  }

  if ! validate_lock_file "$LOCK_FILE"; then
    log "invalid lock file for watcher: $LOCK_FILE"
    return 1
  fi

  if command -v -- flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
      local pid
      if ! pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"; then
        log "failed to read lock holder pid, exiting: $LOCK_FILE"
        cleanup_lock_fd
        return 1
      fi
      pid="${pid//$'\r'/}"
      pid="${pid//$'\n'/}"
      pid="$(printf '%s' "$pid")"
      if ! is_strict_positive_pid "$pid"; then
        log "invalid lock holder pid in $LOCK_FILE: ${pid:-unknown}, exiting"
        cleanup_lock_fd
        return 1
      fi
      if ! is_owned_by_current_user "$LOCK_FILE"; then
        log "lock file not owned by current user: $LOCK_FILE"
        cleanup_lock_fd
        return 1
      fi
      log "another watcher instance is running (flock), exiting (holder=${pid:-unknown})"
      cleanup_lock_fd
      return 1
    fi
    printf '%s\n' "$$" 1>&9
    trap 'flock -u 9 2>/dev/null || true; exec 9>&- 2>/dev/null || true; safe_unlink_runtime_file "$LOCK_FILE" || true; safe_unlink_runtime_file "$TIMESTAMP_FILE" || true' EXIT
    return
  fi

  if ! LOCK_TMP="$(mktemp "${LOCK_FILE}.tmp.XXXXXX")"; then
    log "failed to create temporary lock file under $(dirname "$LOCK_FILE")"
    return 1
  fi
  if [[ "$LOCK_TMP" != "$(dirname -- "$LOCK_FILE")"/* ]]; then
    log "fallback lock temporary file escaped lock directory: $LOCK_TMP"
    cleanup_lock_tmp
    return 1
  fi
  if [[ -L "$LOCK_TMP" ]]; then
    log "fallback lock temporary file must not be a symlink: $LOCK_TMP"
    cleanup_lock_tmp
    return 1
  fi
  if ! printf '%s\n' "$$" > "$LOCK_TMP"; then
    log "failed to write temporary lock holder pid: $LOCK_TMP"
    cleanup_lock_tmp
    return 1
  fi

  if [[ -e "$LOCK_FILE" ]]; then
    local pid
    if ! pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"; then
      log "failed to read lock file, exiting: $LOCK_FILE"
      cleanup_lock_tmp
      return 1
    fi
    pid="${pid//$'\r'/}"
    pid="${pid//$'\n'/}"
    pid="$(printf '%s' "$pid")"
    if ! is_strict_positive_pid "$pid"; then
      log "invalid lock holder pid in $LOCK_FILE: ${pid:-unknown}, exiting"
      cleanup_lock_tmp
      return 1
    fi
    if ! validate_lock_file "$LOCK_FILE"; then
      log "invalid lock file state after reading pid: $LOCK_FILE"
      cleanup_lock_tmp
      return 1
    fi
    if [[ -f "$LOCK_FILE" ]]; then
      local now
      now=$(date +%s)
      local lock_mtime age
      lock_mtime=$(stat -c '%Y' "$LOCK_FILE" 2>/dev/null || echo "$now")
      age=$((now - lock_mtime))
      if ! is_strict_positive_pid "$pid"; then
        log "fallback lock file has invalid pid value (${pid:-unknown}), refusing to steal fresh lock"
        cleanup_lock_tmp
        return 1
      fi
      if [[ "$age" -lt "$MAX_STALE_LOCK_SECONDS" ]] && is_running_pid "$pid"; then
        log "another watcher instance is running (fallback lock), exiting"
        cleanup_lock_tmp
        return 1
      fi
      log "stale fallback lock detected (${age}s), stealing lock"
      if ! safe_unlink_runtime_file "$LOCK_FILE"; then
        log "failed to remove stale fallback lock: $LOCK_FILE"
        cleanup_lock_tmp
        return 1
      fi
    fi
  fi

  if ! mv "$LOCK_TMP" "$LOCK_FILE"; then
    log "failed to acquire fallback lock file via rename: $LOCK_TMP -> $LOCK_FILE"
    cleanup_lock_tmp
    return 1
  fi
  if [[ ! -f "$LOCK_TMP" && ! -f "$LOCK_FILE" ]]; then
    log "lock file not materialized after rename: $LOCK_FILE"
    return 1
  fi
  if [[ -L "$LOCK_FILE" ]]; then
    log "lock file became symlink: $LOCK_FILE"
    safe_unlink_runtime_file "$LOCK_FILE" || true
    return 1
  fi
  if ! is_owned_by_current_user "$LOCK_FILE"; then
    log "lock file not owned by current user after acquisition: $LOCK_FILE"
    safe_unlink_runtime_file "$LOCK_FILE" || true
    return 1
  fi
  trap 'cleanup_lock_tmp; safe_unlink_runtime_file "$LOCK_FILE" || true; safe_unlink_runtime_file "$TIMESTAMP_FILE" || true' EXIT
}

get_minor_version() {
  run_python_sandbox "$PY" - "$PY_SCRIPT" "$PUBLISH_STATE_FILE" <<'PY'
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
  if ! validate_runtime_file_for_read "$STATE_FILE" "State file"; then
    echo ""
    return
  fi
  if [[ -e "$STATE_FILE" ]] && ! is_regular_file "$STATE_FILE"; then
    log "state file is not a regular file: $STATE_FILE"
    echo ""
    return
  fi
  if [[ -e "$STATE_FILE" ]] && [[ -L "$STATE_FILE" ]]; then
    log "state file is a symlink: $STATE_FILE"
    echo ""
    return
  fi
  if [[ -e "$STATE_FILE" ]] && ! is_owned_by_current_user "$STATE_FILE"; then
    log "state file not owned by current user: $STATE_FILE"
    echo ""
    return
  fi
  if [[ -e "$STATE_FILE" ]] && [[ ! -r "$STATE_FILE" ]]; then
    log "state file not readable: $STATE_FILE"
    echo ""
    return
  fi
  if [[ -e "$STATE_FILE" ]]; then
    local state_perm
    if ! state_perm="$(stat -c '%a' "$STATE_FILE" 2>/dev/null)"; then
      log "failed to read state file permissions: $STATE_FILE"
      echo ""
      return
    fi
    if (( 10#$state_perm & 022 )); then
      log "state file has insecure permissions (group/world writable): $STATE_FILE"
      echo ""
      return
    fi
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

  log "minor version changed: $previous -> $current"

  if run_check_script_sandboxed "$CHECKS_SCRIPT"; then
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

SCRIPT_DEPENDENCY_SIGNATURE="$(dependency_signature "$PY_SCRIPT")" || {
  log "failed to read generator script signature: $PY_SCRIPT"
  exit 1
}
PUBLISH_STATE_SIGNATURE="$(dependency_signature "$PUBLISH_STATE_FILE")" || {
  log "failed to read publish state signature: $PUBLISH_STATE_FILE"
  exit 1
}
CURRENT_VERSION="$init_state"

if ! state_file_value="$(sync_state_file "$init_state")"; then
  log "failed to sync minor version state file"
  exit 1
fi
if [[ -z "$state_file_value" ]]; then
  log "state synchronization produced empty version"
  exit 1
fi

if [[ "${1:-}" == "--once" ]]; then
  prev="$state_file_value"
  if ! is_valid_version "$prev"; then
    log "invalid previous version in state: $prev"
    exit 1
  fi
  next_script_sig="$(dependency_signature "$PY_SCRIPT")" || {
    log "failed to read generator script signature: $PY_SCRIPT"
    exit 1
  }
  next_state_sig="$(dependency_signature "$PUBLISH_STATE_FILE")" || {
    log "failed to read publish state signature: $PUBLISH_STATE_FILE"
    exit 1
  }
  if [[ "$next_script_sig" != "$SCRIPT_DEPENDENCY_SIGNATURE" || "$next_state_sig" != "$PUBLISH_STATE_SIGNATURE" ]]; then
    if ! current="$(get_minor_version)"; then
      log "failed to compute current minor version"
      exit 1
    fi
    SCRIPT_DEPENDENCY_SIGNATURE="$next_script_sig"
    PUBLISH_STATE_SIGNATURE="$next_state_sig"
    CURRENT_VERSION="$current"
  else
    current="$CURRENT_VERSION"
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
  next_script_sig="$(dependency_signature "$PY_SCRIPT")" || {
    log "failed to read generator script signature: $PY_SCRIPT"
    exit 1
  }
  next_state_sig="$(dependency_signature "$PUBLISH_STATE_FILE")" || {
    log "failed to read publish state signature: $PUBLISH_STATE_FILE"
    exit 1
  }
  if [[ "$next_script_sig" != "$SCRIPT_DEPENDENCY_SIGNATURE" || "$next_state_sig" != "$PUBLISH_STATE_SIGNATURE" ]]; then
    if ! current="$(get_minor_version)"; then
      log "failed to compute current minor version"
      exit 1
    fi
    SCRIPT_DEPENDENCY_SIGNATURE="$next_script_sig"
    PUBLISH_STATE_SIGNATURE="$next_state_sig"
    CURRENT_VERSION="$current"
  else
    current="$CURRENT_VERSION"
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
    if ! last_epoch="$(read_timestamp_epoch)"; then
      log "failed to read timestamp epoch from file: $TIMESTAMP_FILE"
      if ! refresh_state_timestamp; then
        log "failed to refresh timestamp file: $TIMESTAMP_FILE"
        exit 1
      fi
      sleep "$DEFAULT_RETRY_DELAY_SECONDS"
      continue
    fi
    if [[ ! "$last_epoch" =~ ^[0-9]+$ ]]; then
      log "invalid timestamp epoch from file: $last_epoch"
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
