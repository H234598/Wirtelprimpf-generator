#!/usr/bin/env bash
set -euo pipefail
UUID="wirtelprimfgenerator@H234598"
DEST="${HOME}/.local/share/cinnamon/applets/${UUID}"
rm -rf -- "${DEST}"
printf 'Removed only %s. Preserved paths:\n' "${UUID}"
printf '  %s\n' \
  "${HOME}/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings" \
  "${HOME}/.local/bin/wirtelprimpf-story-directives" \
  "${HOME}/.config/wirtelprimpf/openai.env" \
  "${HOME}/.config/cloudflare/api-token.env" \
  "${HOME}/.config/wirtelprimpf/settings-state.json" \
  "${HOME}/.config/systemd/user/wirtelprimpf.timer.d/override.conf" \
  "${HOME}/.config/systemd/user/wirtelprimpf-atelier.timer.d/override.conf"
printf 'Shared ~/.local/bin/wirtelprimpf-story-directives is preserved.\n'
