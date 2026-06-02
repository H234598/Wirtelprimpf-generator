#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT_UID="$(id -u)"
readonly CURRENT_UID
declare -r SECURITY_PATHS="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
declare -r SECURITY_BIN_NAME_PATTERNS="python|python3|python3.[0-9]+|python2|python2.[0-9]+"
declare -ar SECURITY_PYTHON_CANDIDATES=("python3" "python")
if [[ -n "${PYTHON_BIN:-}" && "${PYTHON_BIN}" == *[[:space:]]* ]]; then
  echo "PYTHON_BIN must not contain whitespace: ${PYTHON_BIN}" >&2
  exit 1
fi

resolve_python() {
  local candidates=("${PYTHON_BIN:-}")
  if [[ -z "${candidates[0]:-}" ]]; then
    candidates=("${SECURITY_PYTHON_CANDIDATES[@]}")
  fi

  local candidate resolved
  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" =~ [[:space:]] || "$candidate" == -* ]]; then
      continue
    fi
    if ! resolved="$(env PATH="$SECURITY_PATHS" command -v -- "$candidate" 2>/dev/null || true)"; then
      continue
    fi
    if [[ -n "$resolved" && -x "$resolved" ]]; then
      echo "$resolved"
      return 0
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
  local resolved owner mode mountpoint mount_opts file_type
  if [[ -z "$path" || ! -x "$path" ]]; then
    return 1
  fi
  if ! resolved="$(readlink -f -- "$path" 2>/dev/null)"; then
    return 1
  fi
  if [[ ! -f "$resolved" || ! -r "$resolved" ]]; then
    return 1
  fi
  case "$resolved" in
    /usr/bin/*|/usr/local/bin/*|/bin/*|/opt/*|/nix/store/*)
      ;;
    *)
      return 1
      ;;
  esac
  local base_name
  base_name="$(basename -- "$resolved")"
  if [[ ! "$base_name" =~ ^($SECURITY_BIN_NAME_PATTERNS)$ ]]; then
    return 1
  fi
  if [[ "$resolved" == /tmp/* || "$resolved" == /var/tmp/* || "$resolved" == /run/* || "$resolved" == /dev/* ]]; then
    return 1
  fi
  if ! owner="$(stat -c '%u' "$resolved" 2>/dev/null)"; then
    return 1
  fi
  if [[ "$owner" != "$CURRENT_UID" && "$owner" != 0 ]]; then
    return 1
  fi
  if ! mode="$(stat -c '%a' "$resolved" 2>/dev/null)"; then
    return 1
  fi
  if (( 10#$mode & 022 )); then
    return 1
  fi
  if ! mountpoint="$(stat -c '%m' "$resolved" 2>/dev/null)"; then
    return 1
  fi
  if command -v findmnt >/dev/null 2>&1; then
    mount_opts="$(findmnt -n -o OPTIONS "$mountpoint" 2>/dev/null || true)"
    if [[ ",${mount_opts}," == *",noexec,"* ]]; then
      return 1
    fi
  fi
  if command -v file >/dev/null 2>&1; then
    if ! file_type="$(file -b -- "$resolved" 2>/dev/null || true)"; then
      return 1
    fi
    if [[ "$file_type" != *ELF* && "$file_type" != *"Python script"* ]]; then
      return 1
    fi
  fi
}
if ! validate_python_binary "$PY"; then
  echo "Invalid/insecure Python interpreter: ${PY}" >&2
  exit 1
fi
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
if ! CHECK_TMPDIR="$(mktemp -d -t wirtelprimpf-check-XXXXXX)"; then
  echo "Failed to create temporary directory" >&2
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
  rm -rf "$CHECK_TMPDIR"
  exit 1
fi
readonly CHECK_TMPDIR
readonly PY_SCRIPT
readonly PY

cleanup_checks() {
  if [[ -n "${CHECK_TMPDIR-}" && -d "$CHECK_TMPDIR" ]]; then
    rm -rf "$CHECK_TMPDIR"
  fi
}
trap cleanup_checks EXIT

run_python_sandbox() {
  env -i \
    PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
    HOME="${HOME:-/tmp}" \
    PYTHONNOUSERSITE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    "$@"
}

run_command_sandboxed() {
  local -a cmd=("$@")
  if (( ${#cmd[@]} == 0 )); then
    echo "No command supplied" >&2
    return 1
  fi
  if [[ "${cmd[0]}" == "$PY" ]]; then
    run_python_sandbox "${cmd[@]}"
  else
    "${cmd[@]}"
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

  if [[ "$output" != "$CHECK_TMPDIR"/* ]]; then
    echo "Output path must be under check tmpdir: $output" >&2
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
import re
import sys

path, mode, strategy = sys.argv[1], sys.argv[2], sys.argv[3]

last_record = None
matched = None
with open(path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line.startswith('{'):
            continue
        record = json.loads(line)
        last_record = record
        if record.get("mode") == mode and matched is None:
            matched = record

if last_record is None:
    raise SystemExit(f"No JSON records in {path}")

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
if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version.strip()):
    raise SystemExit(f"'version' must be semantic version in {path}: {version!r}")

print(f"ok:{data['ok']} exit:{data['exit_code']} mode:{data['mode']} version:{data['version']}")
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

validate_json "$status_json" status first
validate_json "$check_config_json" check_config first
validate_json "$dry_run_json" dry_run any

log "Checks completed"
