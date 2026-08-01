#!/usr/bin/env bash
set -euo pipefail
UUID="wirtelprimfgenerator@H234598"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${HOME}/.local/share/cinnamon/applets/${UUID}"
DIRECTIVES_CLI="${HOME}/.local/bin/wirtelprimpf-story-directives"
SETTINGS_CLI="${HOME}/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings"
if [[ ! -f "${SETTINGS_CLI}" || ! -x "${SETTINGS_CLI}" || -L "${SETTINGS_CLI}" ]]; then
  printf 'Missing trusted settings CLI: %s\n' "${SETTINGS_CLI}" >&2
  exit 1
fi
install -d -m0700 -- "${HOME}/.config/wirtelprimpf" "${HOME}/.config/cloudflare"
install -d -m0700 -- "${HOME}/.config/systemd/user/wirtelprimpf.timer.d"
rm -rf -- "${HOME}/.local/share/cinnamon/applets/wirtelprimfgenerator@local"
mkdir -p -- "$(dirname -- "${DEST}")"
rm -rf -- "${DEST}"
cp -a -- "${ROOT}/files/${UUID}" "${DEST}"
chmod +x -- "${DEST}/helper.py" "${DEST}/SettingsLogo.py" "${DEST}/StoryDirectives.py" "${DEST}/story_directives_core.py"
install -Dm0755 -- "${ROOT}/files/${UUID}/story_directives_core.py" "${DIRECTIVES_CLI}"
printf 'Installed %s to %s\n' "${UUID}" "${DEST}"
printf 'Installed story-directives CLI to %s\n' "${DIRECTIVES_CLI}"
printf 'Reload Cinnamon or re-login, then add the applet.\n'
