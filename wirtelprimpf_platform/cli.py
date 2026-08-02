"""Command-line entrypoints for migration, administration, and rotation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from .admin import serve_admin
from .catalog import CatalogStore
from .cloudflare_credentials import CloudflareCredentialResolver
from .cloudflare_dns import CloudflareDNS, CloudflareHTTPTransport, resolve_zone_id
from .github_provision import GitHubProvisioner
from .media import (
    GitHubReleaseBackend,
    build_media_inventory,
    build_release_plan,
    materialize_release_plan,
    publish_release_plan,
)
from .naming import ARCHIVE_CAPACITY, archive_target_for_volume, book_target_for_story
from .operational_status import OperationalStatusCollector, StatusPaths
from .provision import RotationOrchestrator
from .settings import (
    ChangeRequest,
    SettingsApplyFailure,
    SettingsConflict,
    SettingsLockBusy,
    SettingsManager,
    SettingsPaths,
    SettingsValidationFailure,
)
from .state import PlatformState, StateStore, state_to_dict, status_to_dict
from .systemd_user import SystemdUserManager
from .target_switch import GeneratorTargetSwitcher, GitCatalogPublisher

CONFLICT_EXIT_CODE = 3
VALIDATION_ERROR_EXIT_CODE = 4
LOCK_BUSY_EXIT_CODE = 5
APPLY_FAILURE_EXIT_CODE = 6
UNAVAILABLE_ERROR_EXIT_CODE = 7


def _json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _copy_atomic(source: Path, target: Path, *, mode: int = 0o644) -> None:
    if target.is_symlink():
        raise RuntimeError(f"target must not be a symlink: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(f".{target.name}.{os.getpid()}.part")
    try:
        with source.open("rb") as input_handle, part.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.chmod(part, mode)
        os.replace(part, target)
    finally:
        part.unlink(missing_ok=True)


def _add_settings_parser(subparsers: argparse._SubParsersAction) -> None:
    settings = subparsers.add_parser("settings", help="transactional local settings JSON bridge")
    settings_subcommands = settings.add_subparsers(dest="settings_command", required=True)
    settings_subcommands.add_parser("snapshot", help="print one public settings snapshot")
    settings_subcommands.add_parser("apply", help="apply one sparse JSON request from stdin")


def _build_settings_only_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wirtelprimpf-settings")
    subcommands = parser.add_subparsers(dest="settings_command", required=True)
    subcommands.add_parser("snapshot", help="print one public settings snapshot")
    subcommands.add_parser("apply", help="apply one sparse JSON request from stdin")
    return parser


def build_settings_manager() -> SettingsManager:
    paths = SettingsPaths.for_home(Path.home())
    return SettingsManager(paths, systemd=SystemdUserManager(paths.timer_dropin))


def build_status_collector(manager: SettingsManager) -> OperationalStatusCollector:
    return OperationalStatusCollector(
        paths=StatusPaths.from_settings_paths(manager.paths),
        snapshot_reader=manager.snapshot,
        timer_reader=manager.systemd.observe_timer,
    )


def _read_bounded_stdin(maximum_bytes: int) -> str:
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    content = stream.read(maximum_bytes + 1)
    if isinstance(content, str):
        encoded = content.encode("utf-8")
        if len(encoded) > maximum_bytes:
            raise SettingsValidationFailure(f"settings request exceeds {maximum_bytes} bytes")
        return content
    if len(content) > maximum_bytes:
        raise SettingsValidationFailure(f"settings request exceeds {maximum_bytes} bytes")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SettingsValidationFailure("settings request must be UTF-8") from exc


def _run_settings_command(command: str, manager: SettingsManager) -> int:
    try:
        if command == "snapshot":
            _json({"ok": True, **manager.snapshot().to_public_dict()})
            return 0
        payload = _read_bounded_stdin(64 * 1024)
        request = ChangeRequest.from_payload(json.loads(payload))
        _json({"ok": True, **manager.apply(request).to_public_dict()})
        return 0
    except SettingsConflict as exc:
        _json(
            {
                "ok": False,
                "error": "conflict",
                "conflicts": list(exc.fields),
                "snapshot": exc.snapshot.to_public_dict(),
            }
        )
        return CONFLICT_EXIT_CODE
    except (UnicodeError, json.JSONDecodeError, SettingsValidationFailure) as exc:
        _json({"ok": False, "error": str(exc)})
        return VALIDATION_ERROR_EXIT_CODE
    except SettingsLockBusy:
        _json({"ok": False, "error": "settings lock is busy"})
        return LOCK_BUSY_EXIT_CODE
    except SettingsApplyFailure as exc:
        _json(
            {
                "ok": False,
                "error": "settings transaction failed",
                "rollback_succeeded": exc.rollback_succeeded,
            }
        )
        return APPLY_FAILURE_EXIT_CODE
    except Exception:
        _json({"ok": False, "error": "settings operation unavailable"})
        return UNAVAILABLE_ERROR_EXIT_CODE


def settings_main(argv: list[str] | None = None) -> int:
    command = _build_settings_only_parser().parse_args(argv)
    return _run_settings_command(command.settings_command, build_settings_manager())


def settings_entrypoint() -> int:
    return settings_main(sys.argv[1:])


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wirtelprimpf-platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    mapping = subparsers.add_parser("mapping", help="map a global story to its archive")
    mapping.add_argument("volume", type=int)

    status = subparsers.add_parser("status", help="show private platform state without secrets")
    status.add_argument("--state", type=Path, required=True)

    initialize = subparsers.add_parser("initialize-state", help="initialize state from completed stories")
    initialize.add_argument("--state", type=Path, required=True)
    initialize.add_argument("--completed-volumes", type=int, required=True)

    media = subparsers.add_parser("media-migrate", help="stage, optionally publish, and export a media manifest")
    media.add_argument("--source", type=Path, required=True)
    media.add_argument("--staging", type=Path, required=True)
    media.add_argument("--owner", default="H234598")
    media.add_argument("--repository", required=True)
    media.add_argument("--archive-index", type=int, required=True)
    media.add_argument("--manifest-output", type=Path, required=True)
    media.add_argument("--max-originals-per-shard", type=int, default=250)
    media.add_argument("--publish", action="store_true")

    admin = subparsers.add_parser("admin", help="serve the local settings interface")
    admin.add_argument("--settings", type=Path, default=Path.home() / ".config/wirtelprimpf/openai.env")
    admin.add_argument("--host", default="127.0.0.1")
    admin.add_argument("--port", type=int, default=8765)

    rotate = subparsers.add_parser("rotate", help="resume a staged five-book / 50-story repository rotation")
    rotate.add_argument("--state", type=Path, required=True)
    rotate.add_argument("--catalog", type=Path, required=True)
    rotate.add_argument("--generator-root", type=Path, required=True)
    rotate.add_argument("--archive-root", type=Path, required=True)
    rotate.add_argument("--factory-ref", required=True)
    rotate.add_argument("--owner", default="H234598")
    rotate.add_argument("--zone", default="telacore.org")
    rotate.add_argument("--zone-id")
    rotate.add_argument("--settings", type=Path, default=Path.home() / ".config/wirtelprimpf/openai.env")

    _add_settings_parser(subparsers)

    return parser


def _initialize_state(path: Path, completed: int) -> PlatformState:
    if isinstance(completed, bool) or completed < 0:
        raise ValueError("completed volumes must be non-negative")
    current = completed + 1
    active_archive_index = ((current - 1) // ARCHIVE_CAPACITY) + 1
    state = PlatformState(
        completed_volumes=completed,
        current_volume=current,
        active_archive_index=active_archive_index,
    )
    store = StateStore(path)
    existing = store.load()
    if path.exists() and existing != state:
        raise RuntimeError(f"refusing to replace non-identical platform state: {path}")
    store.save(state)
    return state


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "mapping":
        archive = archive_target_for_volume(args.volume)
        book = book_target_for_story(args.volume)
        _json({
            **asdict(archive),
            "book": {
                "book_in_archive": book.book_in_archive,
                "global_book": book.global_book,
                "story_in_book": book.story_in_book,
                "story_end": book.story_end,
                "story_start": book.story_start,
            },
        })
        return 0
    if args.command == "status":
        _json(status_to_dict(StateStore(args.state).load()))
        return 0
    if args.command == "initialize-state":
        _json(status_to_dict(_initialize_state(args.state, args.completed_volumes)))
        return 0
    if args.command == "media-migrate":
        inventory = build_media_inventory(args.source, archive_index=args.archive_index)
        plan = build_release_plan(
            inventory,
            owner=args.owner,
            repository=args.repository,
            max_originals_per_shard=args.max_originals_per_shard,
        )
        prepared = materialize_release_plan(plan, source_root=args.source, staging_root=args.staging)
        report = None
        if args.publish:
            report = publish_release_plan(
                prepared,
                backend=GitHubReleaseBackend(args.owner, args.repository),
            )
        _copy_atomic(prepared.manifest_path, args.manifest_output)
        _json(
            {
                "inventory_records": len(inventory.records),
                "ignored_working_paths": list(inventory.ignored_working_paths),
                "shards": len(prepared.shards),
                "manifest": str(args.manifest_output),
                "publish": asdict(report) if report else None,
            }
        )
        return 0
    if args.command == "admin":
        manager = build_settings_manager()
        if args.settings != manager.paths.env_file:
            _json(
                {
                    "ok": False,
                    "error": "admin settings path must match the transactional manager path",
                }
            )
            return VALIDATION_ERROR_EXIT_CODE
        serve_admin(
            manager,
            build_status_collector(manager),
            host=args.host,
            port=args.port,
        )
        return 0
    if args.command == "rotate":
        api_token = CloudflareCredentialResolver().resolve(
            explicit_token=os.environ.get("CLOUDFLARE_API_TOKEN")
        )
        transport = CloudflareHTTPTransport(api_token)
        zone_id = args.zone_id or resolve_zone_id(transport, args.zone)
        dns = CloudflareDNS(zone_id=zone_id, zone_name=args.zone, transport=transport)
        github = GitHubProvisioner(
            owner=args.owner,
            generator_root=args.generator_root,
            archive_root=args.archive_root,
            factory_ref=args.factory_ref,
        )
        catalog_publisher = GitCatalogPublisher(
            generator_root=args.generator_root,
            catalog_path=args.catalog,
        )
        state = RotationOrchestrator(
            owner=args.owner,
            pages_target=f"{args.owner.lower()}.github.io",
            state_store=StateStore(args.state),
            catalog_store=CatalogStore(args.catalog),
            github=github,
            dns=dns,
            target_switcher=GeneratorTargetSwitcher(
                settings_path=args.settings,
                archive_root=args.archive_root,
                owner=args.owner,
                publish_catalog=catalog_publisher.publish,
            ),
        ).run()
        _json(state_to_dict(state))
        return 0
    if args.command == "settings":
        return _run_settings_command(args.settings_command, build_settings_manager())
    raise AssertionError(f"unhandled command: {args.command}")


def admin_main() -> int:
    return main(["admin", *sys.argv[1:]])
