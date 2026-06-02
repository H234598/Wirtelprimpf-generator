#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=${PYTHON_BIN:-python3}
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"

log(){
  printf '%s\n' "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" >&2
}

run_check() {
  local label="$1"
  shift
  log "running: $label"
  "$@"
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

run_check "py_compile" "$PY" -m py_compile "$PY_SCRIPT"
run_check "compileall" "$PY" -m compileall -q "$ROOT_DIR/Sourcecode"
run_check "version" "$PY" "$PY_SCRIPT" --version
run_check "status-json" "$PY" "$PY_SCRIPT" --status --json > /tmp/wirtelprimpf-status.json
run_check "check-config-json" "$PY" "$PY_SCRIPT" --check-config --json > /tmp/wirtelprimpf-check-config.json
run_check "dry-run-json" "$PY" "$PY_SCRIPT" --dry-run --json > /tmp/wirtelprimpf-dry-run.json
run_check "status-text" "$PY" "$PY_SCRIPT" --status > /tmp/wirtelprimpf-status.txt
run_check "check-config-text" "$PY" "$PY_SCRIPT" --check-config > /tmp/wirtelprimpf-check-config.txt
run_check "dry-run-text" "$PY" "$PY_SCRIPT" --dry-run > /tmp/wirtelprimpf-dry-run.txt

validate_json /tmp/wirtelprimpf-status.json status first
validate_json /tmp/wirtelprimpf-check-config.json check_config first
validate_json /tmp/wirtelprimpf-dry-run.json dry_run any

log "Checks completed"
