#!/usr/bin/env python3
"""Build and optionally validate one deterministic Wirtelprimpf site profile."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

try:
    from .validate_pages_artifact import ArtifactError, validate_artifact
    from .validate_web_budgets import BudgetError, _load_limits, measure_budgets
except ImportError:
    from validate_pages_artifact import ArtifactError, validate_artifact
    from validate_web_budgets import BudgetError, _load_limits, measure_budgets


PROFILE_DOMAINS = {
    "hub": "wirtelprimpf.telacore.org",
    "archive": "wirtelprimpf-0001.telacore.org",
}
DEFAULT_CATGPT_ENDPOINT = "https://catgpt.wirtelprimpf.telacore.org/v1/chat"


class WebBuildError(RuntimeError):
    """The site could not be built or its artifact failed validation."""


def _run_build(root: Path, *, profile: str, site_url: str, data_root: Path) -> float:
    environment = os.environ.copy()
    environment.update(
        {
            "WIRTELPRIMPF_DATA_ROOT": str(data_root),
            "WIRTELPRIMPF_SITE_PROFILE": profile,
            "WIRTELPRIMPF_SITE_URL": site_url,
            "PUBLIC_CATGPT_LIGHT_ENDPOINT": environment.get(
                "PUBLIC_CATGPT_LIGHT_ENDPOINT", DEFAULT_CATGPT_ENDPOINT
            ),
        }
    )
    started = time.perf_counter()
    result = subprocess.run(
        ["npm", "--prefix", "web", "run", "build"],
        cwd=root,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    duration = time.perf_counter() - started
    if result.returncode:
        raise WebBuildError(f"web build failed with {result.returncode}:\n{result.stdout[-4000:]}")
    return duration


def build_site(
    root: Path,
    *,
    profile: str,
    site_url: str,
    data_root: Path,
    expected_domain: str,
    budget_config: Path,
    check: bool,
) -> dict[str, object]:
    root = root.resolve()
    if not (root / "web" / "package.json").is_file():
        raise WebBuildError("web/package.json is missing")
    duration = _run_build(root, profile=profile, site_url=site_url, data_root=data_root.resolve())
    report: dict[str, object] = {
        "profile": profile,
        "site_url": site_url,
        "expected_domain": expected_domain,
        "build_seconds": round(duration, 3),
    }
    if not check:
        return report

    artifact_root = root / "web" / "dist"
    try:
        artifact = validate_artifact(artifact_root, expected_domain=expected_domain)
        budgets = measure_budgets(artifact_root, limits=_load_limits(budget_config.resolve()), build_seconds=duration)
    except (ArtifactError, BudgetError, OSError, ValueError) as exc:
        raise WebBuildError(f"built web artifact rejected: {exc}") from exc
    report["artifact"] = asdict(artifact)
    report["budgets"] = budgets
    errors = budgets.get("errors", [])
    if isinstance(errors, list) and errors:
        raise WebBuildError("web budgets rejected: " + "; ".join(str(error) for error in errors))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--profile", choices=tuple(PROFILE_DOMAINS), default=os.environ.get("WIRTELPRIMPF_SITE_PROFILE", "hub"))
    parser.add_argument("--site-url")
    parser.add_argument("--expected-domain")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/web-budgets.json"))
    parser.add_argument("--check", action="store_true", help="validate the generated Pages artifact and budgets")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    profile = args.profile
    expected_domain = args.expected_domain or PROFILE_DOMAINS[profile]
    site_url = args.site_url or os.environ.get("WIRTELPRIMP_SITE_URL", f"https://{expected_domain}")
    data_root = (args.data_root or Path(os.environ.get("WIRTELPRIMP_DATA_ROOT", str(root / "data")))).resolve()
    budget_config = args.config if args.config.is_absolute() else root / args.config
    try:
        report = build_site(
            root,
            profile=profile,
            site_url=site_url,
            data_root=data_root,
            expected_domain=expected_domain,
            budget_config=budget_config,
            check=args.check,
        )
    except (OSError, WebBuildError) as exc:
        parser.exit(2, f"web site build failed: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
