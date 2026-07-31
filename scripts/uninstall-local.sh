#!/usr/bin/env bash
set -euo pipefail
UUID="wirtelprimfgenerator@H234598"
DEST="${HOME}/.local/share/cinnamon/applets/${UUID}"
rm -rf -- "${DEST}"
printf 'Removed %s. Runtime state and shared ~/.local/bin/wirtelprimpf-story-directives is preserved.\n' "${UUID}"
