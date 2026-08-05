#!/usr/bin/env python3
"""Run the named EPUB contract gate from the canonical web test suite."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"


def main() -> int:
    command = ["node", "--test", "--experimental-strip-types", "tests/story-navigation.test.ts"]
    result = subprocess.run(command, cwd=WEB_ROOT, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
