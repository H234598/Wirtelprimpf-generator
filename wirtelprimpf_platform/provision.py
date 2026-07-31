"""Restart-safe orchestration for creating the next publication archive."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .catalog import CatalogEntry, CatalogStore
from .state import (
    PlatformState,
    RotationPhase,
    StateStore,
    finish_rotation,
)


class ProvisionPending(RuntimeError):
    """Provisioning is healthy but an external certificate or Pages state is pending."""


class GitHubProvisioning(Protocol):
    def reserve_repository(self, repository: str, *, transaction_id: str) -> None: ...

    def ensure_repository(self, repository: str, *, transaction_id: str) -> int: ...

    def ensure_local_checkout(self, repository: str) -> str: ...

    def initialize_archive(self, repository: str, *, archive_index: int, domain: str) -> str: ...

    def ensure_pages(self, repository: str, *, domain: str) -> None: ...

    def verify_pages_and_enable_https(self, repository: str, *, domain: str) -> bool: ...


class DNSProvisioning(Protocol):
    def ensure_cname(self, name: str, target: str, *, comment: str) -> None: ...


class TargetSwitching(Protocol):
    def switch_target(self, repository: str) -> None: ...


def _advance(state: PlatformState, phase: RotationPhase, **changes: object) -> PlatformState:
    if state.rotation is None:
        raise ValueError("no rotation is pending")
    transaction = replace(state.rotation, phase=phase, **changes)
    return replace(state, rotation=transaction)


class RotationOrchestrator:
    def __init__(
        self,
        *,
        owner: str,
        pages_target: str,
        state_store: StateStore,
        catalog_store: CatalogStore,
        github: GitHubProvisioning,
        dns: DNSProvisioning,
        target_switcher: TargetSwitching | None = None,
    ) -> None:
        self.owner = owner
        self.pages_target = pages_target
        self.state_store = state_store
        self.catalog_store = catalog_store
        self.github = github
        self.dns = dns
        self.target_switcher = target_switcher

    def _save_advanced(self, state: PlatformState, phase: RotationPhase, **changes: object) -> PlatformState:
        advanced = _advance(state, phase, **changes)
        self.state_store.save(advanced)
        return advanced

    def run(self) -> PlatformState:
        state = self.state_store.load()
        while state.rotation is not None:
            transaction = state.rotation
            target = transaction.target_repository
            phase = transaction.phase

            if phase is RotationPhase.ARCHIVE_FINALIZED:
                self.github.reserve_repository(target, transaction_id=transaction.transaction_id)
                state = self._save_advanced(state, RotationPhase.NEXT_REPOSITORY_RESERVED)
                continue

            if phase is RotationPhase.NEXT_REPOSITORY_RESERVED:
                remote_id = self.github.ensure_repository(target, transaction_id=transaction.transaction_id)
                state = self._save_advanced(state, RotationPhase.REMOTE_CREATED, remote_id=remote_id)
                continue

            if phase is RotationPhase.REMOTE_CREATED:
                revision = self.github.ensure_local_checkout(target)
                state = self._save_advanced(state, RotationPhase.LOCAL_CLONE_READY, target_revision=revision)
                continue

            if phase is RotationPhase.LOCAL_CLONE_READY:
                revision = self.github.initialize_archive(
                    target,
                    archive_index=transaction.target_archive_index,
                    domain=transaction.target_domain,
                )
                state = self._save_advanced(state, RotationPhase.RELEASE_AND_PAGES_READY, target_revision=revision)
                continue

            if phase is RotationPhase.RELEASE_AND_PAGES_READY:
                self.github.ensure_pages(target, domain=transaction.target_domain)
                self.dns.ensure_cname(
                    transaction.target_domain,
                    self.pages_target,
                    comment=f"Wirtelprimpf {transaction.transaction_id}"[:100],
                )
                state = self._save_advanced(state, RotationPhase.DNS_CREATED)
                continue

            if phase is RotationPhase.DNS_CREATED:
                if not self.github.verify_pages_and_enable_https(target, domain=transaction.target_domain):
                    raise ProvisionPending(
                        f"Pages/HTTPS is not ready for {target} at {transaction.target_domain}; "
                        "rotation remains blocked"
                    )
                state = self._save_advanced(state, RotationPhase.PAGES_DOMAIN_VERIFIED)
                continue

            if phase is RotationPhase.PAGES_DOMAIN_VERIFIED:
                catalog = self.catalog_store.load()
                source = CatalogEntry.for_archive(
                    transaction.source_archive_index,
                    owner=self.owner,
                    active=False,
                    sealed=True,
                    verified=True,
                    revision=transaction.source_revision,
                )
                target_entry = CatalogEntry.for_archive(
                    transaction.target_archive_index,
                    owner=self.owner,
                    active=False,
                    sealed=False,
                    verified=True,
                    revision=transaction.target_revision,
                )
                catalog = catalog.upsert(source).upsert(target_entry).with_active(transaction.target_archive_index)
                self.catalog_store.save(catalog)
                state = self._save_advanced(state, RotationPhase.CATALOG_UPDATED)
                continue

            if phase is RotationPhase.CATALOG_UPDATED:
                if self.target_switcher is not None:
                    self.target_switcher.switch_target(target)
                state = self._save_advanced(state, RotationPhase.ACTIVE_TARGET_SWITCHED)
                continue

            if phase is RotationPhase.ACTIVE_TARGET_SWITCHED:
                state = self._save_advanced(state, RotationPhase.ROTATION_COMPLETE)
                continue

            if phase is RotationPhase.ROTATION_COMPLETE:
                state = finish_rotation(state)
                self.state_store.save(state)
                catalog = self.catalog_store.load().with_active(state.active_archive_index)
                self.catalog_store.save(catalog)
                continue

            raise RuntimeError(f"unsupported rotation phase: {phase}")
        return state
