#!/usr/bin/env bash
set -euo pipefail
UUID="wirtelprimfgenerator@H234598"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "${ROOT}/dist"
(
  cd "${ROOT}/files"
  zip -qr "${ROOT}/dist/wirtelprimfgenerator-cinnamon-applet.zip" "${UUID}"
)
printf '%s\n' "${ROOT}/dist/wirtelprimfgenerator-cinnamon-applet.zip"
