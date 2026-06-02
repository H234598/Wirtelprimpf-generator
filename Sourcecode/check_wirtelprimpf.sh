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
if ! CHECK_TMPDIR="$(mktemp -d)"; then
  echo "Failed to create temporary directory" >&2
  exit 1
fi
readonly CHECK_TMPDIR
readonly PY_SCRIPT
readonly PY

if [[ ! -x "$PY" ]]; then
  echo "Python path is not executable: ${PY}" >&2
  exit 1
fi

if [[ ! -f "$PY_SCRIPT" ]]; then
  echo "Generator script missing: $PY_SCRIPT" >&2
  exit 1
fi

cleanup_checks() {
  if [[ -n "${CHECK_TMPDIR-}" && -d "$CHECK_TMPDIR" ]]; then
    rm -rf "$CHECK_TMPDIR"
  fi
}
trap cleanup_checks EXIT

log(){
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >&2
}

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
  for arg in "${cmd[@]}"; do
    case "$arg" in
      *$'\n'* | *$'\r'* | *$'\t'*)
        echo "Invalid control character in command argument for ${label}: ${arg}" >&2
        return 1
        ;;
    esac
  done
  if ! "${cmd[@]}"; then
    echo "Check failed: ${label}" >&2
    return 1
  fi
}

assert_file_non_empty() {
  local file="$1"
  if [[ ! -f "$file" || ! -s "$file" ]]; then
    echo "Expected non-empty output in $file" >&2
    return 1
  fi
}

validate_json() {
  local file="$1"
  local mode="${2}"
  local strategy="${3:-any}"
  case "$file" in
    *$'\n'* | *$'\r'* | *$'\t'*)
      echo "Invalid path contains control characters: $file" >&2
      return 1
      ;;
  esac
  case "$mode" in
    status|check_config|dry_run|run) ;;
    *) echo "Invalid mode argument: $mode" >&2; return 1 ;;
  esac
  case "$strategy" in
    any|first) ;;
    *) echo "Invalid strategy argument: $strategy" >&2; return 1 ;;
  esac
  if [[ ! -f "$file" || ! -r "$file" ]]; then
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
run_check "status-json" "$PY" "$PY_SCRIPT" --status --json > "$status_json"
run_check "check-config-json" "$PY" "$PY_SCRIPT" --check-config --json > "$check_config_json"
run_check "dry-run-json" "$PY" "$PY_SCRIPT" --dry-run --json > "$dry_run_json"
run_check "status-text" "$PY" "$PY_SCRIPT" --status > "$status_text"
run_check "check-config-text" "$PY" "$PY_SCRIPT" --check-config > "$check_config_text"
run_check "dry-run-text" "$PY" "$PY_SCRIPT" --dry-run > "$dry_run_text"

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
