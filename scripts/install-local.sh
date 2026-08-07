#!/usr/bin/env bash
set -euo pipefail
UUID="wirtelprimfgenerator@H234598"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${HOME}/.local/share/cinnamon/applets/${UUID}"
DIRECTIVES_CLI="${HOME}/.local/bin/wirtelprimpf-story-directives"
SETTINGS_CLI="${ROOT}/.venv/bin/wirtelprimpf-settings"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
if [[ ! -f "${SETTINGS_CLI}" || ! -x "${SETTINGS_CLI}" || -L "${SETTINGS_CLI}" ]]; then
  printf 'Missing trusted settings CLI: %s\n' "${SETTINGS_CLI}" >&2
  exit 1
fi
install -d -m0700 -- "${HOME}/.config/wirtelprimpf" "${HOME}/.config/cloudflare"
install -d -m0700 -- "${HOME}/.config/systemd/user/wirtelprimpf.timer.d"
install -d -m0700 -- "${HOME}/.config/systemd/user/wirtelprimpf-atelier.timer.d"
install -Dm0644 -- "${ROOT}/Sourcecode/systemd-user/wirtelprimpf.service" "${SYSTEMD_DIR}/wirtelprimpf.service"
install -Dm0644 -- "${ROOT}/Sourcecode/systemd-user/wirtelprimpf.timer" "${SYSTEMD_DIR}/wirtelprimpf.timer"
install -Dm0644 -- "${ROOT}/Sourcecode/systemd-user/wirtelprimpf-atelier.service" "${SYSTEMD_DIR}/wirtelprimpf-atelier.service"
install -Dm0644 -- "${ROOT}/Sourcecode/systemd-user/wirtelprimpf-atelier.timer" "${SYSTEMD_DIR}/wirtelprimpf-atelier.timer"
rm -rf -- "${HOME}/.local/share/cinnamon/applets/wirtelprimfgenerator@local"
mkdir -p -- "$(dirname -- "${DEST}")"
rm -rf -- "${DEST}"
cp -a -- "${ROOT}/files/${UUID}" "${DEST}"
chmod +x -- "${DEST}/helper.py" "${DEST}/SettingsLogo.py" "${DEST}/StoryDirectives.py" "${DEST}/story_directives_core.py"
install -Dm0755 -- "${ROOT}/files/${UUID}/story_directives_core.py" "${DIRECTIVES_CLI}"
printf 'Installed %s to %s\n' "${UUID}" "${DEST}"
printf 'Installed story-directives CLI to %s\n' "${DIRECTIVES_CLI}"
printf 'Reload Cinnamon or re-login, then add the applet.\n'
