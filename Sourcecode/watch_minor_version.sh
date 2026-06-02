#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=${PYTHON_BIN:-python3}
PY_SCRIPT="$ROOT_DIR/Sourcecode/wirtelprimpf_generator.py"
STATE_FILE="$ROOT_DIR/Sourcecode/.minor_version_state"
SLEEP_SECONDS=${SLEEP_SECONDS:-300}
CHECKS_SCRIPT="$ROOT_DIR/Sourcecode/check_wirtelprimpf.sh"

get_minor_version() {
  "$PY" - "$PY_SCRIPT" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
m = re.search(r"VERSION:\s*Final\s*=\s*\"([^\"]+)\"", text)
if not m:
    raise SystemExit(1)
version = m.group(1)
m2 = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
if not m2:
    raise SystemExit(1)
print(f"{m2.group(1)}.{m2.group(2)}")
PY
}

init_state=$(get_minor_version)
if [[ ! -f "$STATE_FILE" ]]; then
  printf '%s\n' "$init_state" > "$STATE_FILE"
fi

if [[ "${1:-}" == "--once" ]]; then
  prev=$(cat "$STATE_FILE")
  current=$(get_minor_version)
  if [[ "$current" != "$prev" ]]; then
    printf '%s\n' "$current" > "$STATE_FILE"
    "$CHECKS_SCRIPT"
  fi
  exit 0
fi

while true; do
  prev=$(cat "$STATE_FILE")
  current=$(get_minor_version)

  if [[ "$current" != "$prev" ]]; then
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] minor version changed: $prev -> $current"
    printf '%s\n' "$current" > "$STATE_FILE"
    set +e
    "$CHECKS_SCRIPT"
    code=$?
    set -e
    if [[ "$code" -ne 0 ]]; then
      echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] checks failed with exit code $code"
    fi
    echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] checks finished for version $current"
  fi

  sleep "$SLEEP_SECONDS"
done
