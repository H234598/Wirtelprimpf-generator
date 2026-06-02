#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${PYTHON_BIN:-}" && "${PYTHON_BIN}" == *[[:space:]]* ]]; then
  echo "PYTHON_BIN must not contain whitespace: ${PYTHON_BIN}" >&2
  exit 1
fi

resolve_python() {
  local candidates=("${PYTHON_BIN:-}")
  if [[ -z "${candidates[0]:-}" ]]; then
    candidates=("python3" "python")
  fi

  local candidate resolved
  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" =~ [[:space:]] || "$candidate" == -* ]]; then
      continue
    fi
    if ! resolved="$(command -v -- "$candidate" 2>/dev/null || true)"; then
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
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
if ! CHECK_TMPDIR="$(mktemp -d -t wirtelprimpf-check-XXXXXX)"; then
  echo "Failed to create temporary directory" >&2
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
  if [[ -L "$path" ]]; then
    echo "${label} must not be a symlink: ${path}" >&2
    return 1
  fi
  if ! is_regular_file "$path"; then
    echo "${label} missing or not a regular file: ${path}" >&2
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
  local arg
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
    exit 1
  fi
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
  for arg in "${cmd[@]}"; do
    case "$arg" in
      *$'\n'* | *$'\r'* | *$'\t'*)
        echo "Invalid control character in command argument for ${label}: ${arg}" >&2
        return 1
        ;;
      [!a-zA-Z0-9._/\-]*)
        echo "Invalid command argument for ${label}: ${arg}" >&2
        return 1
        ;;
    esac
  done
  if ! "${cmd[@]}"; then
    echo "Check failed: ${label}" >&2
    return 1
  fi
}

run_check_to_file() {
  local label="$1"
  local output="$2"
  shift 2

  if [[ -z "$output" ]]; then
    echo "No output path for check: $label" >&2
    return 1
  fi
  if [[ "$output" != "$CHECK_TMPDIR/"* ]]; then
    echo "Output path must be under check tmpdir: $output" >&2
    return 1
  fi
  if [[ ! "$output" =~ ^[A-Za-z0-9._/\-]+$ ]]; then
    echo "Invalid output path characters: $output" >&2
    return 1
  fi
  if [[ "${output##*/}" == "." || "${output##*/}" == ".." || "${output##*/}" == "" ]]; then
    echo "Output path must include filename: $output" >&2
    return 1
  fi
  local output_real
  if ! output_real="$(realpath -m "$output")"; then
    echo "Unable to resolve output path: $output" >&2
    return 1
  fi
  if [[ "$output_real" != "$CHECK_TMPDIR"/* ]]; then
    echo "Resolved output path escapes check tmpdir: $output (resolved $output_real)" >&2
    return 1
  fi
  case "$label" in
    status-json|check-config-json|dry-run-json)
      if [[ "$output" != *.json ]]; then
        echo "JSON label requires .json output path: $output" >&2
        return 1
      fi
      ;;
    status-text|check-config-text|dry-run-text)
      if [[ "$output" != *.txt ]]; then
        echo "Text label requires .txt output path: $output" >&2
        return 1
      fi
      ;;
    *)
      echo "Unknown check label for output validation: $label" >&2
      return 1
      ;;
  esac
  local output_dir
  output_dir="$(dirname "$output")"
  if [[ ! -d "$output_dir" ]]; then
    echo "Output directory missing for check: $output_dir" >&2
    return 1
  fi
  if [[ -L "$output_dir" || ( -e "$output_dir" && ! -d "$output_dir" ) ]]; then
    echo "Invalid output directory for check: $output_dir" >&2
    return 1
  fi
  if [[ -e "$output" ]] && ! is_regular_file "$output"; then
    echo "Output file must be regular: $output" >&2
    return 1
  fi

  if ! run_check "$label" "$@"; then
    return 1
  fi > "$output"
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
  if [[ ! "$file" =~ ^[A-Za-z0-9._/\-]+$ ]]; then
    echo "Invalid path contains unsafe character: $file" >&2
    return 1
  fi
  if [[ "$file" != "$CHECK_TMPDIR"/* ]]; then
    echo "validate_json path is outside check tempdir: $file" >&2
    return 1
  fi
  if ! is_regular_file "$file"; then
    echo "Expected regular JSON file: $file" >&2
    return 1
  fi
  case "$mode" in
    status|check_config|dry_run|run) ;;
    *) echo "Invalid mode argument: $mode" >&2; return 1 ;;
  esac
  case "$strategy" in
    any|first) ;;
    *) echo "Invalid strategy argument: $strategy" >&2; return 1 ;;
  esac
  if [[ ! -r "$file" ]]; then
    echo "JSON file missing or unreadable: $file" >&2
    return 1
  fi

  "$PY" - "$file" "$mode" "$strategy" <<'PY'
import json
import re
import sys

path, mode, strategy = sys.argv[1], sys.argv[2], sys.argv[3]

records = []
with open(path, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line.startswith('{'):
            continue
        records.append(json.loads(line))

if not records:
    raise SystemExit(f"No JSON records in {path}")

required = {"ok", "version", "timestamp", "mode", "status", "exit_code"}
if strategy == "any":
    if not any(r.get("mode") == mode for r in records):
        raise SystemExit(f"Expected mode {mode!r} in at least one record from {path}")
    data = next(r for r in records if r.get("mode") == mode)
else:
    data = records[-1]
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
