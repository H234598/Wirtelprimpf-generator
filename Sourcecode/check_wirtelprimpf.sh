#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=${PYTHON_BIN:-python3}
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
CHECK_TMPDIR="$(mktemp -d)"

cleanup_checks() {
  rm -rf "$CHECK_TMPDIR"
}
trap cleanup_checks EXIT

log(){
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >&2
}

run_check() {
  local label="$1"
  shift
  log "running: $label"
  "$@"
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

  "$PY" - "$file" "$mode" "$strategy" <<'PY'
import json
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
if not isinstance(data.get("exit_code"), int):
    raise SystemExit(f"exit_code must be int in {path}: {data.get('exit_code')!r}")

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

validate_json "$status_json" status first
validate_json "$check_config_json" check_config first
validate_json "$dry_run_json" dry_run any

log "Checks completed"
