#!/usr/bin/env python3
"""Fail-closed deterministic size and runtime-request checks for the static site."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


class BudgetError(RuntimeError):
    """The static site exceeds a published budget or contains a foreign runtime."""


DEFAULT_LIMITS = {
    "max_html_bytes": 2 * 1024 * 1024,
    "max_gallery_index_gzip_bytes": 150 * 1024,
    "max_initial_js_gzip_bytes": 35 * 1024,
    "max_initial_css_gzip_bytes": 40 * 1024,
    "max_eager_gallery_images": 6,
    "max_gallery_original_sources": 0,
    "max_external_runtime_requests": 0,
}


class _Resources(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []
        self.images: list[dict[str, str]] = []
        self.external_runtime: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"])
            if urlsplit(values["src"]).scheme or urlsplit(values["src"]).netloc:
                self.external_runtime.append(values["src"])
        if tag == "link" and values.get("rel", "").lower() == "stylesheet" and values.get("href"):
            self.stylesheets.append(values["href"])
            if urlsplit(values["href"]).scheme or urlsplit(values["href"]).netloc:
                self.external_runtime.append(values["href"])
        if tag == "img" and values.get("src"):
            self.images.append(values)


def _load_limits(path: Path) -> dict[str, int]:
    if not path.is_file():
        return dict(DEFAULT_LIMITS)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BudgetError(f"cannot read budget config {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0":
        raise BudgetError("unsupported web budget schema")
    raw_limits = payload.get("limits")
    if not isinstance(raw_limits, dict):
        raise BudgetError("budget config must contain limits")
    limits = dict(DEFAULT_LIMITS)
    for key, value in raw_limits.items():
        if key not in limits or isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BudgetError(f"invalid budget value for {key}")
        limits[key] = value
    return limits


def _local_file(root: Path, raw: str) -> Path | None:
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        return None
    path = (root / parsed.path.lstrip("/")).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise BudgetError(f"resource escaped artifact: {raw}") from exc
    if not path.is_file():
        raise BudgetError(f"linked resource is missing: {raw}")
    return path


def _gzip_size(path: Path) -> int:
    return len(gzip.compress(path.read_bytes(), compresslevel=9, mtime=0))


def measure_budgets(root: Path, *, limits: dict[str, int] | None = None, build_seconds: float | None = None) -> dict[str, object]:
    artifact = root.resolve()
    if not artifact.is_dir() or artifact.is_symlink():
        raise BudgetError(f"budget root must be a non-symlink directory: {root}")
    active_limits = limits or dict(DEFAULT_LIMITS)
    html_files = sorted(artifact.rglob("*.html"))
    if not html_files:
        raise BudgetError("artifact contains no HTML files")
    largest_html = max(html_files, key=lambda path: path.stat().st_size)
    gallery_path = artifact / "bilder" / "index.html"
    home_path = artifact / "index.html"
    if not gallery_path.is_file() or not home_path.is_file():
        raise BudgetError("home and gallery index are required for the baseline")

    referenced_scripts: set[Path] = set()
    referenced_styles: set[Path] = set()
    external_runtime: list[str] = []
    gallery_original_sources = 0
    gallery_eager_images = 0
    gallery_external_media = 0
    for page in (home_path, gallery_path):
        parser = _Resources()
        parser.feed(page.read_text(encoding="utf-8"))
        external_runtime.extend(parser.external_runtime)
        for raw in parser.scripts:
            resource = _local_file(artifact, raw)
            if resource is not None:
                referenced_scripts.add(resource)
        for raw in parser.stylesheets:
            resource = _local_file(artifact, raw)
            if resource is not None:
                referenced_styles.add(resource)
        if page == gallery_path:
            for image in parser.images:
                source = image["src"]
                suffix = Path(urlsplit(source).path).suffix.lower()
                gallery_original_sources += suffix in {".png", ".jpg", ".jpeg"}
                gallery_eager_images += image.get("loading", "").lower() != "lazy"
                parsed = urlsplit(source)
                gallery_external_media += bool(parsed.scheme or parsed.netloc)

    js_gzip = sum(_gzip_size(path) for path in sorted(referenced_scripts))
    css_gzip = sum(_gzip_size(path) for path in sorted(referenced_styles))
    errors: list[str] = []
    if largest_html.stat().st_size > active_limits["max_html_bytes"]:
        errors.append("largest HTML file exceeds max_html_bytes")
    if _gzip_size(gallery_path) > active_limits["max_gallery_index_gzip_bytes"]:
        errors.append("gallery index exceeds max_gallery_index_gzip_bytes")
    if js_gzip > active_limits["max_initial_js_gzip_bytes"]:
        errors.append("initial JavaScript exceeds max_initial_js_gzip_bytes")
    if css_gzip > active_limits["max_initial_css_gzip_bytes"]:
        errors.append("initial CSS exceeds max_initial_css_gzip_bytes")
    if gallery_eager_images > active_limits["max_eager_gallery_images"]:
        errors.append("gallery eager image count exceeds max_eager_gallery_images")
    if gallery_original_sources > active_limits["max_gallery_original_sources"]:
        errors.append("gallery contains original image sources")
    if len(external_runtime) > active_limits["max_external_runtime_requests"]:
        errors.append("foreign runtime requests exceed max_external_runtime_requests")

    report: dict[str, object] = {
        "root": str(artifact),
        "html_count": len(html_files),
        "largest_html": {
            "path": str(largest_html.relative_to(artifact)),
            "bytes": largest_html.stat().st_size,
        },
        "gallery_index": {
            "bytes": gallery_path.stat().st_size,
            "gzip_bytes": _gzip_size(gallery_path),
            "eager_images": gallery_eager_images,
            "original_sources": gallery_original_sources,
            "external_media_sources": gallery_external_media,
        },
        "initial_assets": {
            "javascript_files": [str(path.relative_to(artifact)) for path in sorted(referenced_scripts)],
            "javascript_gzip_bytes": js_gzip,
            "css_files": [str(path.relative_to(artifact)) for path in sorted(referenced_styles)],
            "css_gzip_bytes": css_gzip,
        },
        "external_runtime_requests": sorted(set(external_runtime)),
        "build_seconds": build_seconds,
        "limits": active_limits,
        "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
        "errors": sorted(set(errors)),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("web/dist"))
    parser.add_argument("--config", type=Path, default=Path("config/web-budgets.json"))
    parser.add_argument("--build-seconds", type=float)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        report = measure_budgets(args.root, limits=_load_limits(args.config), build_seconds=args.build_seconds)
    except BudgetError as exc:
        parser.exit(2, f"web budgets rejected: {exc}\n")
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    if args.strict and report["errors"]:
        parser.exit(2, "web budgets rejected: " + "; ".join(report["errors"]) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
