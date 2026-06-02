#!/usr/bin/env bash
set -euo pipefail
umask 077

declare -r SAFE_EXEC_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PATH="$SAFE_EXEC_PATH"

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_UID="$(id -u)"
readonly CURRENT_UID
declare -ar SECURITY_PATHS_ARRAY=(/usr/local/sbin /usr/local/bin /usr/sbin /usr/bin /sbin /bin)
declare -r SECURITY_BIN_NAME_PATTERNS="python3|python3\.[0-9]+"
declare -ar SECURITY_PYTHON_CANDIDATES=("python3")
declare -i HAS_FINDMNT_CMD=0
declare -i HAS_FILE_CMD=0
declare -g FINDMNT_COMMAND=""
declare -g FILE_COMMAND=""
CHECK_TIMEOUT_SECONDS="${CHECK_TIMEOUT_SECONDS:-30}"
declare -g CHECK_TIMEOUT_COMMAND=""

case "$CHECK_TIMEOUT_SECONDS" in
  ''|*[!0-9]*)
    echo "CHECK_TIMEOUT_SECONDS must be a positive integer" >&2
    exit 1
    ;;
esac
if (( CHECK_TIMEOUT_SECONDS < 10 || CHECK_TIMEOUT_SECONDS > 900 )); then
  echo "CHECK_TIMEOUT_SECONDS must be between 10 and 900" >&2
  exit 1
fi
readonly CHECK_TIMEOUT_SECONDS

is_secure_tool_path() {
  local path="$1"
  local owner mode parent parent_owner parent_mode
  if [[ -z "$path" || "$path" != /* || -L "$path" || ! -f "$path" || ! -x "$path" ]]; then
    return 1
  fi
  parent="$(dirname -- "$path")"
  if [[ -L "$parent" || ! -d "$parent" ]]; then
    return 1
  fi
  if ! read -r owner mode <<<"$(stat -c '%u %a' "$path" 2>/dev/null)"; then
    return 1
  fi
  if ! read -r parent_owner parent_mode <<<"$(stat -c '%u %a' "$parent" 2>/dev/null)"; then
    return 1
  fi
  if [[ "$owner" != "$CURRENT_UID" && "$owner" != 0 ]]; then
    return 1
  fi
  if [[ "$parent_owner" != "$CURRENT_UID" && "$parent_owner" != 0 ]]; then
    return 1
  fi
  if (( 10#$mode & 022 || 10#$mode & 06000 || 10#$parent_mode & 022 )); then
    return 1
  fi
  return 0
}

for findmnt_candidate in /usr/bin/findmnt /bin/findmnt; do
  if is_secure_tool_path "$findmnt_candidate"; then
    FINDMNT_COMMAND="$findmnt_candidate"
    HAS_FINDMNT_CMD=1
    break
  fi
done
for file_candidate in /usr/bin/file /bin/file; do
  if is_secure_tool_path "$file_candidate"; then
    FILE_COMMAND="$file_candidate"
    HAS_FILE_CMD=1
    break
  fi
done
readonly HAS_FINDMNT_CMD HAS_FILE_CMD FINDMNT_COMMAND FILE_COMMAND
if [[ -n "${PYTHON_BIN:-}" && ("${PYTHON_BIN}" == *[[:space:]]* || "${PYTHON_BIN}" == *[$'\r\n\t\v\f']* || "${PYTHON_BIN}" != "${PYTHON_BIN//[^a-zA-Z0-9._-]/}") ]]; then
  echo "PYTHON_BIN contains invalid characters: ${PYTHON_BIN}" >&2
  exit 1
fi

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

if ! PY="$(resolve_python)"; then
  echo "Python executable not found: ${PYTHON_BIN:-python3/python}" >&2
  exit 1
fi
validate_python_binary() {
  local path="$1"
  local resolved mountpoint mount_opts file_type parent_dir
  local resolved_mode resolved_owner parent_mode parent_owner mountpoint_owner mountpoint_mode
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
    mount_opts="$("$FINDMNT_COMMAND" -n -o OPTIONS "$mountpoint" 2>/dev/null || true)"
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
    if ! file_type="$("$FILE_COMMAND" -b -- "$resolved" 2>/dev/null || true)"; then
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
if ! validate_python_binary "$PY"; then
  echo "Invalid/insecure Python interpreter: ${PY}" >&2
  exit 1
fi
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
CHECK_TMP_BASE_DIR="${ROOT_DIR}/Sourcecode/.check_runtime_tmp"
if [[ -L "$CHECK_TMP_BASE_DIR" ]]; then
  echo "Check temp base directory must not be a symlink: ${CHECK_TMP_BASE_DIR}" >&2
  exit 1
fi
if ! mkdir -p "$CHECK_TMP_BASE_DIR"; then
  echo "Failed to create check temp base directory: ${CHECK_TMP_BASE_DIR}" >&2
  exit 1
fi
if ! is_strict_secure_directory "$CHECK_TMP_BASE_DIR" "Check temp base directory"; then
  exit 1
fi
if ! CHECK_TMPDIR="$(mktemp -d -p "$CHECK_TMP_BASE_DIR" -t wirtelprimpf-check-XXXXXX)"; then
  echo "Failed to create temporary directory" >&2
  exit 1
fi
if [[ "$CHECK_TMPDIR" != "$CHECK_TMP_BASE_DIR"/* ]]; then
  rmdir "$CHECK_TMPDIR" 2>/dev/null || true
  echo "Check temporary directory must be under ${CHECK_TMP_BASE_DIR}: ${CHECK_TMPDIR}" >&2
  exit 1
fi

is_owned_by_current_user() {
  local path="$1"
  local owner
  if ! owner="$(stat -c '%u' "$path" 2>/dev/null)"; then
    return 1
  fi
  [[ "$owner" == "$CURRENT_UID" ]]
}

is_strict_secure_directory() {
  local path="$1"
  local label="$2"
  local perm
  if [[ -L "$path" ]]; then
    echo "${label} must not be a symlink: ${path}" >&2
    return 1
  fi
  if [[ ! -d "$path" ]]; then
    echo "${label} must be a directory: ${path}" >&2
    return 1
  fi
  if [[ ! -r "$path" || ! -w "$path" || ! -x "$path" ]]; then
    echo "${label} must be readable/writable/searchable: ${path}" >&2
    return 1
  fi
  if ! perm="$(stat -c '%a' "$path" 2>/dev/null)"; then
    echo "${label} failed to read permissions: ${path}" >&2
    return 1
  fi
  if (( 10#$perm & 022 )); then
    echo "${label} must not be group/world writable: ${path}" >&2
    return 1
  fi
  if ! is_owned_by_current_user "$path"; then
    echo "${label} must be owned by current user: ${path}" >&2
    return 1
  fi
  return 0
}

if ! is_strict_secure_directory "$CHECK_TMPDIR" "Check temporary directory"; then
  rmdir "$CHECK_TMPDIR" 2>/dev/null || true
  exit 1
fi
readonly CHECK_TMPDIR
readonly PY_SCRIPT
readonly PY
for BASH_PATH in /usr/bin/bash /bin/bash; do
  if [[ -f "$BASH_PATH" && -x "$BASH_PATH" && ! -L "$BASH_PATH" ]]; then
    break
  fi
  BASH_PATH=""
done
if [[ -z "$BASH_PATH" ]]; then
  echo "Required bash interpreter unavailable: neither /usr/bin/bash nor /bin/bash is present/executable" >&2
  exit 1
fi
readonly BASH_PATH
for CHECK_TIMEOUT_COMMAND in /usr/bin/timeout /bin/timeout; do
  if is_secure_tool_path "$CHECK_TIMEOUT_COMMAND"; then
    break
  fi
  CHECK_TIMEOUT_COMMAND=""
done
if [[ -z "$CHECK_TIMEOUT_COMMAND" ]]; then
  echo "Required timeout command unavailable: neither /usr/bin/timeout nor /bin/timeout is available" >&2
  exit 1
fi
readonly CHECK_TIMEOUT_COMMAND

remove_check_tmpdir() {
  local path="${1:-}"
  if [[ -z "$path" || -L "$path" || ! -d "$path" ]]; then
    return 1
  fi
  if [[ "$path" != "$CHECK_TMP_BASE_DIR"/* || "$path" == "$CHECK_TMP_BASE_DIR" ]]; then
    return 1
  fi
  if ! is_owned_by_current_user "$path"; then
    return 1
  fi
  rm -rf --one-file-system -- "$path"
}

cleanup_checks() {
  if [[ -n "${CHECK_TMPDIR-}" && -d "$CHECK_TMPDIR" ]]; then
    remove_check_tmpdir "$CHECK_TMPDIR" || true
  fi
  if [[ -n "${CHECK_TMP_BASE_DIR-}" && -d "$CHECK_TMP_BASE_DIR" && ! -L "$CHECK_TMP_BASE_DIR" ]]; then
    if rmdir --ignore-fail-on-non-empty "$CHECK_TMP_BASE_DIR" 2>/dev/null; then
      :
    fi
  fi
}
trap cleanup_checks EXIT INT TERM HUP

run_python_sandbox() {
  "$CHECK_TIMEOUT_COMMAND" "$CHECK_TIMEOUT_SECONDS" env -i \
    PATH="/usr/local/bin:/usr/bin:/bin" \
    HOME="/tmp" \
    USER="" \
    LOGNAME="" \
    LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PYTHONSTARTUP= \
    PYTHONPATH= \
    PYTHONHOME= \
    PYTHONSAFEPATH=1 \
    PYTHONUSERBASE= \
    PYTHONNOUSERSITE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    "$@"
}

run_command_sandboxed() {
  local -a cmd=("$@")
  local command_canonical
  local command_path_dir
  local command_dir_mode
  local bash_canonical
  local bash_mode
  local command_mode
  if (( ${#cmd[@]} == 0 )); then
    echo "No command supplied" >&2
    return 1
  fi
  if [[ "${cmd[0]}" == "$PY" ]]; then
    command_canonical="$(readlink -f -- "${cmd[0]}" 2>/dev/null || true)"
    if [[ -z "$command_canonical" || "$command_canonical" != "${cmd[0]}" ]]; then
      echo "Python command path must be canonical and non-symlinked: ${cmd[0]}" >&2
      return 1
    fi
    if ! is_owned_by_current_user "$command_canonical"; then
      echo "Python command must be owned by current user: ${cmd[0]}" >&2
      return 1
    fi
    if ! command_mode="$(stat -c '%a' "$command_canonical" 2>/dev/null)"; then
      echo "Failed to read python command permissions: ${cmd[0]}" >&2
      return 1
    fi
    if (( 10#$command_mode & 022 )); then
      echo "Python command must not be group/world writable: ${cmd[0]}" >&2
      return 1
    fi
    if (( 10#$command_mode & 06000 )); then
      echo "Python command must not have setuid/setgid bits: ${cmd[0]}" >&2
      return 1
    fi
    command_path_dir="$(dirname -- "$command_canonical")"
    if [[ -L "$command_path_dir" ]]; then
      echo "Python command directory must not be a symlink: ${command_path_dir}" >&2
      return 1
    fi
    if ! is_owned_by_current_user "$command_path_dir"; then
      echo "Python command directory must be owned by current user: ${command_path_dir}" >&2
      return 1
    fi
    if ! command_dir_mode="$(stat -c '%a' "$command_path_dir" 2>/dev/null)"; then
      echo "Failed to read python command directory permissions: ${command_path_dir}" >&2
      return 1
    fi
    if (( 10#$command_dir_mode & 022 )); then
      echo "Python command directory must not be group/world writable: ${command_path_dir}" >&2
      return 1
    fi
    run_python_sandbox "${cmd[@]}"
  elif [[ "${cmd[0]}" != /* ]]; then
    echo "Only absolute command paths are allowed in sandboxed execution: ${cmd[0]}" >&2
    return 1
  elif [[ -L "${cmd[0]}" || ! -x "${cmd[0]}" ]]; then
    echo "Sandboxed command must be an executable non-symlink file: ${cmd[0]}" >&2
    return 1
  elif ! is_owned_by_current_user "${cmd[0]}"; then
    echo "Sandboxed command must be owned by current user: ${cmd[0]}" >&2
    return 1
  elif [[ -z "${BASH_PATH}" || -L "${BASH_PATH}" || ! -x "${BASH_PATH}" ]]; then
    echo "Required bash interpreter unavailable or insecure: ${BASH_PATH:-not-found}" >&2
    return 1
  else
    command_canonical="$(readlink -f -- "${cmd[0]}" 2>/dev/null || true)"
    if [[ -z "$command_canonical" || "$command_canonical" != "${cmd[0]}" ]]; then
      echo "Sandboxed command path must be canonical and non-symlinked: ${cmd[0]}" >&2
      return 1
    fi
    command_path_dir="$(dirname -- "$command_canonical")"
    if [[ -L "$command_path_dir" ]]; then
      echo "Sandboxed command directory must not be a symlink: ${command_path_dir}" >&2
      return 1
    fi
    if ! is_owned_by_current_user "$command_path_dir"; then
      echo "Sandboxed command directory must be owned by current user: ${command_path_dir}" >&2
      return 1
    fi
    if ! command_dir_mode="$(stat -c '%a' "$command_path_dir" 2>/dev/null)"; then
      echo "Failed to read sandboxed command directory permissions: ${command_path_dir}" >&2
      return 1
    fi
    if (( 10#$command_dir_mode & 022 )); then
      echo "Sandboxed command directory must not be group/world writable: ${command_path_dir}" >&2
      return 1
    fi
    bash_canonical="$(readlink -f -- "$BASH_PATH" 2>/dev/null || true)"
    if [[ -z "$bash_canonical" ]]; then
      echo "Failed to read bash interpreter canonical path: ${BASH_PATH:-not-found}" >&2
      return 1
    fi
    if ! is_owned_by_current_user "$bash_canonical"; then
      echo "Bash interpreter must be owned by current user: $bash_canonical" >&2
      return 1
    fi
    if ! bash_mode="$(stat -c '%a' "$bash_canonical" 2>/dev/null)"; then
      echo "Failed to read bash interpreter permissions: $bash_canonical" >&2
      return 1
    fi
    if (( 10#$bash_mode & 022 )); then
      echo "Bash interpreter must not be group/world writable: $bash_canonical" >&2
      return 1
    fi
    if (( 10#$bash_mode & 06000 )); then
      echo "Bash interpreter must not have setuid/setgid bits: $bash_canonical" >&2
      return 1
    fi
    if ! command_mode="$(stat -c '%a' "$command_canonical" 2>/dev/null)"; then
      echo "Failed to read sandboxed command permissions: ${cmd[0]}" >&2
      return 1
    fi
    if (( 10#$command_mode & 022 )); then
      echo "Sandboxed command must not be group/world writable: ${cmd[0]}" >&2
      return 1
    fi
    if (( 10#$command_mode & 06000 )); then
      echo "Sandboxed command must not have setuid/setgid bits: ${cmd[0]}" >&2
      return 1
    fi
    "$CHECK_TIMEOUT_COMMAND" "$CHECK_TIMEOUT_SECONDS" env -i \
      PATH="/usr/local/bin:/usr/bin:/bin" \
      HOME="/tmp" \
      LANG="C.UTF-8" \
      LC_ALL="C.UTF-8" \
      TERM="xterm-256color" \
      USER="" \
      LOGNAME="" \
      "$command_canonical" "${cmd[@]:1}"
  fi
}

log(){
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >&2
}

is_regular_file() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    return 1
  fi
  if [[ -L "$path" ]]; then
    return 1
  fi
  [[ -f "$path" ]]
}

require_file() {
  local path="$1"
  local label="$2"
  local perm
  if [[ -L "$path" ]]; then
    echo "${label} must not be a symlink: ${path}" >&2
    return 1
  fi
  if ! is_regular_file "$path"; then
    echo "${label} missing or not a regular file: ${path}" >&2
    return 1
  fi
  if ! is_owned_by_current_user "$path"; then
    echo "${label} must be owned by current user: ${path}" >&2
    return 1
  fi
  if [[ ! -r "$path" ]]; then
    echo "${label} is not readable: ${path}" >&2
    return 1
  fi
  if ! perm="$(stat -c '%a' "$path" 2>/dev/null)"; then
    echo "${label} failed to read permissions: ${path}" >&2
    return 1
  fi
  if (( 10#$perm & 022 )); then
    echo "${label} must not be group/world writable: ${path}" >&2
    return 1
  fi
}

require_executable() {
  local path="$1"
  local label="$2"
  if ! require_file "$path" "$label"; then
    return 1
  fi
  if ! [[ -x "$path" ]]; then
    echo "${label} is not executable: ${path}" >&2
    return 1
  fi
}

if ! require_executable "$PY" "Python interpreter"; then
  exit 1
fi
if ! require_file "$PY_SCRIPT" "Generator script"; then
  exit 1
fi

run_check() {
  local label="$1"
  shift
  log "running: $label"
  local -a cmd=("$@")
  local command
  local i
  case "$label" in
    py_compile|compileall|version|status-json|check-config-json|dry-run-json|status-text|check-config-text|dry-run-text)
      ;;
    *)
      echo "Invalid check label: ${label}" >&2
      return 1
      ;;
  esac
  if [[ $# -eq 0 ]]; then
    echo "No command supplied for check: $label" >&2
    return 1
  fi
  for i in "${!cmd[@]}"; do
    command="${cmd[$i]}"
    if [[ -z "$command" ]]; then
      echo "Invalid command element at index ${i} for ${label}" >&2
      return 1
    fi
  done
  case "$label" in
    py_compile)
      if [[ "${#cmd[@]}" -ne 4 || "${cmd[0]}" != "$PY" || "${cmd[1]}" != -m || "${cmd[2]}" != py_compile || "${cmd[3]}" != "$PY_SCRIPT" ]]; then
        echo "Invalid command for ${label}: ${cmd[*]-}" >&2
        return 1
      fi
      ;;
    compileall)
      if [[ "${#cmd[@]}" -ne 5 || "${cmd[0]}" != "$PY" || "${cmd[1]}" != -m || "${cmd[2]}" != compileall || "${cmd[3]}" != -q || "${cmd[4]}" != "$ROOT_DIR/Sourcecode" ]]; then
        echo "Invalid command for ${label}: ${cmd[*]-}" >&2
        return 1
      fi
      ;;
    version)
      if [[ "${#cmd[@]}" -ne 3 || "${cmd[0]}" != "$PY" || "${cmd[1]}" != "$PY_SCRIPT" || "${cmd[2]}" != --version ]]; then
        echo "Invalid command for ${label}: ${cmd[*]-}" >&2
        return 1
      fi
      ;;
    status-json|check-config-json|dry-run-json|status-text|check-config-text|dry-run-text)
      if [[ "${#cmd[@]}" -ne 3 || "${cmd[0]}" != "$PY" || "${cmd[1]}" != "$PY_SCRIPT" ]]; then
        echo "Invalid command for ${label}: ${cmd[*]-}" >&2
        return 1
      fi
      case "$label" in
        status-json|status-text)
          if [[ "${cmd[2]}" != --status ]]; then
            echo "Invalid command for ${label}: ${cmd[*]-}" >&2
            return 1
          fi
          ;;
        check-config-json|check-config-text)
          if [[ "${cmd[2]}" != --check-config ]]; then
            echo "Invalid command for ${label}: ${cmd[*]-}" >&2
            return 1
          fi
          ;;
        dry-run-json|dry-run-text)
          if [[ "${cmd[2]}" != --dry-run ]]; then
            echo "Invalid command for ${label}: ${cmd[*]-}" >&2
            return 1
          fi
          ;;
      esac
      ;;
  esac
  if ! run_command_sandboxed "${cmd[@]}"; then
    echo "Check failed: ${label}" >&2
    return 1
  fi
}

run_check_to_file() {
  local label="$1"
  local output="$2"
  shift 2
  local output_canonical
  local output_parent

  case "$label" in
    status-json|check-config-json|dry-run-json|status-text|check-config-text|dry-run-text)
      ;;
    *)
      echo "Invalid check label for output validation: $label" >&2
      return 1
      ;;
  esac
  if [[ -z "$output" ]]; then
    echo "No output path for check: $label" >&2
    return 1
  fi

  case "$label" in
    status-json)
      if [[ "$output" != "$CHECK_TMPDIR/status.json" ]]; then
        echo "Unexpected output path for status-json: $output" >&2
        return 1
      fi
      ;;
    check-config-json)
      if [[ "$output" != "$CHECK_TMPDIR/check-config.json" ]]; then
        echo "Unexpected output path for check-config-json: $output" >&2
        return 1
      fi
      ;;
    dry-run-json)
      if [[ "$output" != "$CHECK_TMPDIR/dry-run.json" ]]; then
        echo "Unexpected output path for dry-run-json: $output" >&2
        return 1
      fi
      ;;
    status-text)
      if [[ "$output" != "$CHECK_TMPDIR/status.txt" ]]; then
        echo "Unexpected output path for status-text: $output" >&2
        return 1
      fi
      ;;
    check-config-text)
      if [[ "$output" != "$CHECK_TMPDIR/check-config.txt" ]]; then
        echo "Unexpected output path for check-config-text: $output" >&2
        return 1
      fi
      ;;
    dry-run-text)
      if [[ "$output" != "$CHECK_TMPDIR/dry-run.txt" ]]; then
        echo "Unexpected output path for dry-run-text: $output" >&2
        return 1
      fi
      ;;
    *)
      echo "Unknown check label for output validation: $label" >&2
      return 1
      ;;
  esac

  if ! output_canonical="$(readlink -f -- "$output" 2>/dev/null)"; then
    echo "Output path must be canonicalizable: $output" >&2
    return 1
  fi
  if [[ -z "$output_canonical" || "$output_canonical" != "$output" ]]; then
    echo "Output path must be canonical and non-symlinked: $output" >&2
    return 1
  fi
  if [[ "$output" != "$CHECK_TMPDIR"/* ]]; then
    echo "Output path must be under check tmpdir: $output" >&2
    return 1
  fi
  if [[ "$output" == *[[:space:]]* ]]; then
    echo "Output path contains whitespace: $output" >&2
    return 1
  fi
  if [[ "$output_canonical" == *[[:space:]]* ]]; then
    echo "Output path contains whitespace: $output_canonical" >&2
    return 1
  fi
  output_parent="$(dirname -- "$output_canonical")"
  if [[ ! -d "$output_parent" || -L "$output_parent" || "$output_parent" != "$CHECK_TMPDIR" ]]; then
    echo "Invalid output parent directory: $output_parent" >&2
    return 1
  fi
  if [[ -e "$output" ]] && ! is_regular_file "$output"; then
    echo "Output file must be regular: $output" >&2
    return 1
  fi
  if [[ -e "$output" ]] && ! is_owned_by_current_user "$output"; then
    echo "Output file must be owned by current user: $output" >&2
    return 1
  fi

  local output_tmp
  if ! output_tmp="$(mktemp "${output}.tmp.XXXXXX")"; then
    echo "Failed to create temporary output file for ${label}" >&2
    return 1
  fi
  if [[ -L "$output_tmp" || ! -e "$output_tmp" || ! -f "$output_tmp" ]]; then
    echo "Temporary output file is not a valid regular file: $output_tmp" >&2
    rm -f "$output_tmp"
    return 1
  fi
  if [[ ! "$output_tmp" == "$CHECK_TMPDIR"/* ]]; then
    echo "Temporary output path escaped check tmpdir: $output_tmp" >&2
    rm -f "$output_tmp"
    return 1
  fi
  if ! is_regular_file "$output_tmp"; then
    echo "Temp output file must be regular: $output_tmp" >&2
    rm -f "$output_tmp"
    return 1
  fi
  if ! is_owned_by_current_user "$output_tmp"; then
    echo "Temporary output file must be owned by current user: $output_tmp" >&2
    rm -f "$output_tmp"
    return 1
  fi
  if ! run_command_sandboxed "$@" > "$output_tmp"; then
    local rc=$?
    echo "Check failed: ${label}" >&2
    rm -f "$output_tmp"
    return $rc
  fi
  if ! is_regular_file "$output_tmp"; then
    echo "Temp output file must be regular: $output_tmp" >&2
    rm -f "$output_tmp"
    return 1
  fi
  if ! mv -f -- "$output_tmp" "$output"; then
    echo "Failed to move temp output file into place: $output" >&2
    rm -f "$output_tmp"
    return 1
  fi
}

assert_file_non_empty() {
  local file="$1"
  if ! is_regular_file "$file"; then
    echo "Expected regular output file in $file" >&2
    return 1
  fi
  if [[ ! -s "$file" ]]; then
    echo "Expected non-empty output in $file" >&2
    return 1
  fi
}

validate_json() {
  local file="$1"
  local mode="${2}"
  local strategy="${3:-any}"
  if [[ -z "$file" ]]; then
    echo "No file supplied to validate_json" >&2
    return 1
  fi
  local expected_json
  case "$mode" in
    status)
      expected_json="$CHECK_TMPDIR/status.json"
      ;;
    check_config)
      expected_json="$CHECK_TMPDIR/check-config.json"
      ;;
    dry_run)
      expected_json="$CHECK_TMPDIR/dry-run.json"
      ;;
    run)
      expected_json="$CHECK_TMPDIR/status.json"
      ;;
    *)
      echo "Invalid mode argument: $mode" >&2
      return 1
      ;;
  esac
  if [[ "$file" != "$expected_json" ]]; then
    echo "validate_json path mismatch for mode ${mode}: ${file} != ${expected_json}" >&2
    return 1
  fi
  if ! is_regular_file "$file"; then
    echo "Expected regular JSON file: $file" >&2
    return 1
  fi
  case "$strategy" in
    any|first) ;;
    *) echo "Invalid strategy argument: $strategy" >&2; return 1 ;;
  esac
  if [[ ! -r "$file" ]]; then
    echo "JSON file missing or unreadable: $file" >&2
    return 1
  fi

  run_python_sandbox "$PY" - "$file" "$mode" "$strategy" <<'PY'
import json
import sys

path, mode, strategy = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(path, encoding='utf-8') as f:
        payload = json.load(f)
except json.JSONDecodeError:
    payload = None

if isinstance(payload, dict):
    records = [payload]
elif isinstance(payload, list):
    records = payload
else:
    with open(path, encoding='utf-8') as f:
        records = []
        for line in f:
            line = line.strip()
            if not line.startswith('{'):
                continue
            records.append(json.loads(line))

if not records:
    raise SystemExit(f"No JSON records in {path}")

last_record = records[-1]
matched = None
for record in records:
    if not isinstance(record, dict):
        raise SystemExit(f"JSON record is not an object in {path}")
    if record.get("mode") == mode and matched is None:
        matched = record

required = {"ok", "version", "timestamp", "mode", "status", "exit_code"}
if strategy == "any":
    if matched is None:
        raise SystemExit(f"Expected mode {mode!r} in at least one record from {path}")
    data = matched
else:
    data = last_record
    if data.get("mode") != mode:
        raise SystemExit(f"Expected trailing mode {mode!r} in {path}, got {data.get('mode')!r}")

missing = sorted(required - set(data))
if missing:
    raise SystemExit(f"Missing fields {missing} in {path}")

if not isinstance(data.get("ok"), bool):
    raise SystemExit(f"'ok' must be bool in {path}: {data.get('ok')!r}")
if not isinstance(data.get("status"), str):
    raise SystemExit(f"'status' must be string in {path}: {data.get('status')!r}")
if data.get("status") not in {"ok", "error"}:
    raise SystemExit(f"invalid status value in {path}: {data.get('status')!r}")
if data.get("mode") not in {"status", "check_config", "dry_run", "run"}:
    raise SystemExit(f"invalid mode value in {path}: {data.get('mode')!r}")
if not isinstance(data.get("exit_code"), int):
    raise SystemExit(f"exit_code must be int in {path}: {data.get('exit_code')!r}")
if not isinstance(data.get("timestamp"), str) or not data.get("timestamp"):
    raise SystemExit(f"'timestamp' must be non-empty string in {path}")

version = data.get("version")
if not isinstance(version, str) or not version.strip():
    raise SystemExit(f"'version' must be non-empty string in {path}: {version!r}")
parts = version.split("-", 1)[0].split("+", 1)[0].split(".")
if len(parts) != 3 or not all(segment.isdigit() for segment in parts):
    raise SystemExit(f"'version' must be semantic version in {path}: {version!r}")

print(f"ok:{data['ok']} exit:{data['exit_code']} mode:{data['mode']} version:{data['version']}")
PY
}

validate_json_bundle() {
  local status_file="$1"
  local check_config_file="$2"
  local dry_run_file="$3"

  if [[ -z "$status_file" || -z "$check_config_file" || -z "$dry_run_file" ]]; then
    echo "Missing required JSON path for bundle validation" >&2
    return 1
  fi
  if [[ "$status_file" != "$CHECK_TMPDIR/status.json" ]]; then
    echo "Unexpected status path in bundle validation: $status_file" >&2
    return 1
  fi
  if [[ "$check_config_file" != "$CHECK_TMPDIR/check-config.json" ]]; then
    echo "Unexpected check-config path in bundle validation: $check_config_file" >&2
    return 1
  fi
  if [[ "$dry_run_file" != "$CHECK_TMPDIR/dry-run.json" ]]; then
    echo "Unexpected dry-run path in bundle validation: $dry_run_file" >&2
    return 1
  fi

  run_python_sandbox "$PY" - "$status_file" "$check_config_file" "$dry_run_file" <<'PY'
import json
import sys

required = {"ok", "version", "timestamp", "mode", "status", "exit_code"}


def load_and_validate(path, mode, strategy):
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        records = [payload]
    elif isinstance(payload, list):
        records = payload
    else:
        with open(path, encoding="utf-8") as f:
            records = []
            for line in f:
                line = line.strip()
                if not line.startswith("{"):
                    continue
                records.append(json.loads(line))

    if not records:
        raise SystemExit(f"No JSON records in {path}")

    matched = None
    for record in records:
        if not isinstance(record, dict):
            raise SystemExit(f"JSON record is not an object in {path}")
        if record.get("mode") == mode and matched is None:
            matched = record

    data = records[-1]
    if strategy == "any":
        if matched is None:
            raise SystemExit(f"Expected mode {mode!r} in at least one record from {path}")
        data = matched
    elif data.get("mode") != mode:
        raise SystemExit(f"Expected trailing mode {mode!r} in {path}, got {data.get('mode')!r}")

    missing = sorted(required - set(data))
    if missing:
        raise SystemExit(f"Missing fields {missing} in {path}")

    if not isinstance(data.get("ok"), bool):
        raise SystemExit(f"'ok' must be bool in {path}: {data.get('ok')!r}")
    if not isinstance(data.get("status"), str):
        raise SystemExit(f"'status' must be string in {path}: {data.get('status')!r}")
    if data.get("status") not in {"ok", "error"}:
        raise SystemExit(f"invalid status value in {path}: {data.get('status')!r}")
    if data.get("mode") not in {"status", "check_config", "dry_run", "run"}:
        raise SystemExit(f"invalid mode value in {path}: {data.get('mode')!r}")
    if not isinstance(data.get("exit_code"), int):
        raise SystemExit(f"exit_code must be int in {path}: {data.get('exit_code')!r}")
    if not isinstance(data.get("timestamp"), str) or not data.get("timestamp"):
        raise SystemExit(f"'timestamp' must be non-empty string in {path}")

    version = data.get("version")
    if not isinstance(version, str) or not version.strip():
        raise SystemExit(f"'version' must be non-empty string in {path}: {version!r}")
    parts = version.split("-", 1)[0].split("+", 1)[0].split(".")
    if len(parts) != 3 or not all(segment.isdigit() for segment in parts):
        raise SystemExit(f"'version' must be semantic version in {path}: {version!r}")

    return f"ok:{data['ok']} exit:{data['exit_code']} mode:{data['mode']} version:{data['version']}"


status_file, check_config_file, dry_run_file = sys.argv[1], sys.argv[2], sys.argv[3]

print(load_and_validate(status_file, "status", "first"))
print(load_and_validate(check_config_file, "check_config", "first"))
print(load_and_validate(dry_run_file, "dry_run", "any"))
PY
}

log "Running full check suite for Wirtelprimpf"

status_json="$CHECK_TMPDIR/status.json"
check_config_json="$CHECK_TMPDIR/check-config.json"
dry_run_json="$CHECK_TMPDIR/dry-run.json"
status_text="$CHECK_TMPDIR/status.txt"
check_config_text="$CHECK_TMPDIR/check-config.txt"
dry_run_text="$CHECK_TMPDIR/dry-run.txt"

run_check "py_compile" "$PY" -m py_compile "$PY_SCRIPT"
run_check "compileall" "$PY" -m compileall -q "$ROOT_DIR/Sourcecode"
run_check "version" "$PY" "$PY_SCRIPT" --version
run_check_to_file "status-json" "$status_json" "$PY" "$PY_SCRIPT" --status --json
run_check_to_file "check-config-json" "$check_config_json" "$PY" "$PY_SCRIPT" --check-config --json
run_check_to_file "dry-run-json" "$dry_run_json" "$PY" "$PY_SCRIPT" --dry-run --json
run_check_to_file "status-text" "$status_text" "$PY" "$PY_SCRIPT" --status
run_check_to_file "check-config-text" "$check_config_text" "$PY" "$PY_SCRIPT" --check-config
run_check_to_file "dry-run-text" "$dry_run_text" "$PY" "$PY_SCRIPT" --dry-run

assert_file_non_empty "$status_json"
assert_file_non_empty "$check_config_json"
assert_file_non_empty "$dry_run_json"
assert_file_non_empty "$status_text"
assert_file_non_empty "$check_config_text"
assert_file_non_empty "$dry_run_text"

required_files=(
  "$status_json"
  "$check_config_json"
  "$dry_run_json"
  "$status_text"
  "$check_config_text"
  "$dry_run_text"
)

if [[ ${#required_files[@]} -ne 6 ]]; then
  echo "Expected 6 verification artifacts, got ${#required_files[@]}" >&2
  exit 1
fi

for file in "${required_files[@]}"; do
  if [[ ! -e "$file" ]]; then
    echo "Missing expected artifact: $file" >&2
    exit 1
  fi
done

validate_json_bundle "$status_json" "$check_config_json" "$dry_run_json"

log "Checks completed"
