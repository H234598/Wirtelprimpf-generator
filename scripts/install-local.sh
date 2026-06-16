#!/usr/bin/env bash
set -euo pipefail
UUID="wirtelprimfgenerator@H234598"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${HOME}/.local/share/cinnamon/applets/${UUID}"
rm -rf -- "${HOME}/.local/share/cinnamon/applets/wirtelprimfgenerator@local"
mkdir -p -- "$(dirname -- "${DEST}")"
rm -rf -- "${DEST}"
cp -a -- "${ROOT}/files/${UUID}" "${DEST}"
chmod +x -- "${DEST}/helper.py" "${DEST}/SettingsLogo.py"
printf 'Installed %s to %s\n' "${UUID}" "${DEST}"
printf 'Reload Cinnamon or re-login, then add the applet.\n'
