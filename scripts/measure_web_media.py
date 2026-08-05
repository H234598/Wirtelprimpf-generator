#!/usr/bin/env python3
"""Measure repeated static builds and media growth without publishing anything."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from wirtelprimpf_platform.media import MEDIA_TRANSFORM_TOOL_VERSION
    from wirtelprimpf_platform.media_cache import TRANSFORM_CONFIG_VERSION, media_cache_key
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from wirtelprimpf_platform.media import MEDIA_TRANSFORM_TOOL_VERSION
    from wirtelprimpf_platform.media_cache import TRANSFORM_CONFIG_VERSION, media_cache_key

try:
    from .validate_pages_artifact import ArtifactError, validate_artifact
    from .validate_web_budgets import BudgetError, _load_limits, measure_budgets
except ImportError:
    from validate_pages_artifact import ArtifactError, validate_artifact
    from validate_web_budgets import BudgetError, _load_limits, measure_budgets


class MediaMeasurementError(RuntimeError):
    """The read-only measurement could not produce a trustworthy report."""


def _percentile(values: list[float], percentile: float) -> float:
    if not values or not 0 <= percentile <= 100:
        raise ValueError("percentile requires values and a range from 0 to 100")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _git_status(root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def _run_build(root: Path) -> dict[str, float | int]:
    started = time.perf_counter()
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=root / "web",
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )
    duration = time.perf_counter() - started
    if result.returncode != 0:
        raise MediaMeasurementError(f"web build failed with {result.returncode}:\n{result.stdout[-4000:]}")
    return {
        "duration_seconds": duration,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    }


def _manifest_stats(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MediaMeasurementError(f"cannot read media manifest: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("media"), list):
        raise MediaMeasurementError("media manifest has no media list")
    media = payload["media"]
    source_bytes = sum(item.get("byte_size", 0) for item in media if isinstance(item, dict))
    widths = sorted(
        {
            variant.get("requested_width")
            for item in media
            if isinstance(item, dict)
            for variant in item.get("variants", [])
            if isinstance(variant, dict) and isinstance(variant.get("requested_width"), int)
        }
    )
    return {
        "path": str(path),
        "schema_version": payload.get("schema_version"),
        "media_count": len(media),
        "source_bytes": source_bytes,
        "shard_count": len(payload.get("shards", [])) if isinstance(payload.get("shards"), list) else 0,
        "variant_widths": widths,
    }


def _manifest_at_commit(root: Path, commit: str, relative_path: str) -> tuple[int, int] | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("media"), list):
        return None
    media = payload["media"]
    return len(media), sum(item.get("byte_size", 0) for item in media if isinstance(item, dict))


def _growth_report(root: Path, manifest_stats: dict[str, Any]) -> dict[str, Any]:
    relative_path = "data/media-manifest.json"
    result = subprocess.run(
        ["git", "log", "--format=%H%x09%ct", "--max-count=20", "--", relative_path],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    points: list[dict[str, int]] = []
    for line in result.stdout.splitlines():
        commit, _, raw_epoch = line.partition("\t")
        if not commit or not raw_epoch.isdigit():
            continue
        values = _manifest_at_commit(root, commit, relative_path)
        if values is not None:
            media_count, source_bytes = values
            points.append({"epoch": int(raw_epoch), "media_count": media_count, "source_bytes": source_bytes})
    if len(points) < 2 or points[0]["epoch"] <= points[-1]["epoch"]:
        return {"status": "insufficient_history", "points": points, "projections": {}}
    elapsed = points[0]["epoch"] - points[-1]["epoch"]
    byte_growth_per_second = max(0.0, (points[0]["source_bytes"] - points[-1]["source_bytes"]) / elapsed)
    media_growth_per_second = max(0.0, (points[0]["media_count"] - points[-1]["media_count"]) / elapsed)
    projections: dict[str, dict[str, float]] = {}
    for months in (12, 24, 36):
        seconds = months * 30.4375 * 24 * 60 * 60
        projections[str(months)] = {
            "projected_media_count": manifest_stats["media_count"] + media_growth_per_second * seconds,
            "projected_source_bytes": manifest_stats["source_bytes"] + byte_growth_per_second * seconds,
        }
    return {
        "status": "measured",
        "points": points,
        "growth_per_second": {
            "media_count": media_growth_per_second,
            "source_bytes": byte_growth_per_second,
        },
        "projections": projections,
    }


def _write_report(root: Path, output: Path, rendered: str) -> None:
    reports = (root / "build" / "reports").resolve()
    target = (output if output.is_absolute() else root / output).resolve()
    try:
        target.relative_to(reports)
    except ValueError as exc:
        raise MediaMeasurementError("measurement output must stay below build/reports") from exc
    reports.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=reports, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(rendered)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def measure(root: Path, *, runs: int, expected_domain: str, budget_config: Path) -> dict[str, object]:
    if runs < 1 or runs > 10:
        raise ValueError("runs must be between 1 and 10")
    root = root.resolve()
    before = _git_status(root)
    run_reports = [_run_build(root) for _ in range(runs)]
    after = _git_status(root)
    try:
        artifact = validate_artifact(root / "web" / "dist", expected_domain=expected_domain)
    except ArtifactError as exc:
        raise MediaMeasurementError(f"built artifact failed validation: {exc}") from exc
    manifest_stats = _manifest_stats(root / "data" / "media-manifest.json")
    try:
        budgets = measure_budgets(root / "web" / "dist", limits=_load_limits(budget_config))
    except (BudgetError, OSError, ValueError) as exc:
        raise MediaMeasurementError(f"budget measurement failed: {exc}") from exc
    durations = [float(report["duration_seconds"]) for report in run_reports]
    sample_sha = "0" * 64
    payload = json.loads((root / "data" / "media-manifest.json").read_text(encoding="utf-8"))
    if isinstance(payload, dict) and payload.get("media") and isinstance(payload["media"][0], dict):
        sample_sha = payload["media"][0].get("sha256", sample_sha)
    source_tree_unchanged = before == after
    errors = list(budgets.get("errors", []))
    if not source_tree_unchanged:
        errors.append("source tree changed during measurement")
    return {
        "schema_version": "1.0.0",
        "runs": {
            "count": runs,
            "durations_seconds": durations,
            "cold_seconds": durations[0],
            "warm_seconds": durations[1:] or durations,
            "median_seconds": _percentile(durations, 50),
            "p95_seconds": _percentile(durations, 95),
            "max_rss_kib": max(int(report["max_rss_kib"]) for report in run_reports),
        },
        "source_tree_unchanged": source_tree_unchanged,
        "manifest": manifest_stats,
        "growth": _growth_report(root, manifest_stats),
        "artifact": {
            "file_count": artifact.file_count,
            "html_count": artifact.html_count,
            "total_bytes": artifact.total_bytes,
            "internal_links_checked": artifact.internal_links_checked,
            "tree_sha256": artifact.tree_sha256,
        },
        "transfer": {
            "pages_artifact_bytes": artifact.total_bytes,
            "release_source_bytes": manifest_stats["source_bytes"],
            "pages_to_release_source_ratio": artifact.total_bytes / manifest_stats["source_bytes"]
            if manifest_stats["source_bytes"]
            else None,
        },
        "budgets": {
            "decision": "pass" if not budgets.get("errors") else "fail",
            "errors": budgets.get("errors", []),
            "limits": budgets.get("limits", {}),
        },
        "cache_contract": {
            "sample_key": media_cache_key(
                sample_sha,
                MEDIA_TRANSFORM_TOOL_VERSION,
                TRANSFORM_CONFIG_VERSION,
                "webp",
                640,
            ),
            "cache_hit_rate": None,
            "cache_scope": "release-media pipeline; static builds reuse manifest URLs",
        },
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
        "errors": sorted(set(errors)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--expected-domain", default="wirtelprimpf.telacore.org")
    parser.add_argument("--config", type=Path, default=Path("config/web-budgets.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        config = args.config if args.config.is_absolute() else root / args.config
        report = measure(root, runs=args.runs, expected_domain=args.expected_domain, budget_config=config)
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            _write_report(args.root.resolve(), args.output, rendered)
        else:
            print(rendered, end="")
    except (OSError, MediaMeasurementError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"web media measurement failed: {exc}\n")
    if args.strict and report["errors"]:
        parser.exit(2, "web media measurement rejected: " + "; ".join(report["errors"]) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
