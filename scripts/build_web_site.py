#!/usr/bin/env python3
"""Build and optionally validate one deterministic Wirtelprimpf site profile."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, replace
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
ALLOWED_GENERATED_PATH = "web/src/generated/status.json"
RENAME_EXCHANGE = 2


class WebBuildError(RuntimeError):
    """The site could not be built or its artifact failed validation."""


def _git_status(root: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "--untracked-files=all", "-z"],
        check=False,
        text=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise WebBuildError(f"cannot inspect source worktree: {detail or result.returncode}")
    entries: list[str] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        entry = raw.decode("utf-8", errors="surrogateescape")
        path = entry[3:] if len(entry) >= 4 else ""
        if path == ALLOWED_GENERATED_PATH:
            continue
        entries.append(entry)
    return tuple(entries)


def _source_date_epoch(root: Path) -> str:
    configured = os.environ.get("SOURCE_DATE_EPOCH")
    if configured is not None:
        return configured
    result = subprocess.run(
        ["git", "-C", str(root), "show", "-s", "--format=%ct", "HEAD"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value.isdigit() else "0"


def _run_build(root: Path, *, profile: str, site_url: str, data_root: Path, output_dir: Path) -> float:
    environment = os.environ.copy()
    environment.update(
        {
            "WIRTELPRIMPF_DATA_ROOT": str(data_root),
            "WIRTELPRIMPF_SITE_PROFILE": profile,
            "WIRTELPRIMPF_SITE_URL": site_url,
            "PUBLIC_CATGPT_LIGHT_ENDPOINT": environment.get(
                "PUBLIC_CATGPT_LIGHT_ENDPOINT", DEFAULT_CATGPT_ENDPOINT
            ),
            "WIRTELPRIMPF_OUTPUT_DIR": str(output_dir),
            "SOURCE_DATE_EPOCH": _source_date_epoch(root),
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


def _rename_exchange(left: Path, right: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise WebBuildError("atomic directory exchange is unavailable on this platform")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(-100, os.fsencode(left), -100, os.fsencode(right), RENAME_EXCHANGE)
    if result != 0:
        error = ctypes.get_errno()
        raise WebBuildError(f"atomic directory exchange failed: {os.strerror(error)}")


def _publish_atomically(staged: Path, target: Path) -> None:
    if staged.is_symlink() or not staged.is_dir():
        raise WebBuildError(f"staged artifact is not a directory: {staged}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise WebBuildError(f"existing artifact target is not a directory: {target}")
    if target.exists():
        _rename_exchange(staged, target)
        return
    os.replace(staged, target)


def _remove_staging(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_dir():
            path.unlink()
        else:
            shutil.rmtree(path)


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
    before_status = _git_status(root)
    staging_root = root / "web" / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    session = Path(tempfile.mkdtemp(prefix=".site-build-", dir=staging_root))
    staged_artifact = session / "dist"
    artifact_root = root / "web" / "dist"
    try:
        duration = _run_build(
            root,
            profile=profile,
            site_url=site_url,
            data_root=data_root.resolve(),
            output_dir=staged_artifact,
        )
        report: dict[str, object] = {
            "profile": profile,
            "site_url": site_url,
            "expected_domain": expected_domain,
            "build_seconds": round(duration, 3),
            "source_date_epoch": _source_date_epoch(root),
        }
        if check:
            try:
                artifact = validate_artifact(staged_artifact, expected_domain=expected_domain)
                budgets = measure_budgets(
                    staged_artifact,
                    limits=_load_limits(budget_config.resolve()),
                    build_seconds=duration,
                )
            except (ArtifactError, BudgetError, OSError, ValueError) as exc:
                raise WebBuildError(f"built web artifact rejected: {exc}") from exc
            errors = budgets.get("errors", [])
            if isinstance(errors, list) and errors:
                raise WebBuildError("web budgets rejected: " + "; ".join(str(error) for error in errors))
            report["artifact"] = asdict(replace(artifact, root=str(artifact_root.resolve())))
            report["budgets"] = budgets
        if _git_status(root) != before_status:
            raise WebBuildError(
                "build changed tracked or untracked source files outside "
                f"{ALLOWED_GENERATED_PATH}"
            )
        _publish_atomically(staged_artifact, artifact_root)
        return report
    except WebBuildError:
        try:
            if _git_status(root) != before_status:
                raise WebBuildError(
                    "failed build changed tracked or untracked source files outside "
                    f"{ALLOWED_GENERATED_PATH}"
                )
        finally:
            _remove_staging(session)
            _remove_staging(staging_root)
        raise
    except (OSError, ValueError) as exc:
        _remove_staging(session)
        _remove_staging(staging_root)
        raise WebBuildError(f"web site build failed: {exc}") from exc
    finally:
        _remove_staging(session)
        _remove_staging(staging_root)


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
