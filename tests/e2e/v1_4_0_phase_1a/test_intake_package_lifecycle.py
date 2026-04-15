"""IntakePackage lifecycle E2E — state machine + repository contract.

@test_registry
suite: phase_1a_e2e
tags: [e2e, phase_1a, intake, state_machine]

Exercises the full IntakePackageStatus happy-path transition chain plus
IntakeRepository CRUD with a mocked asyncpg Pool (matches existing unit
test style to avoid the asyncpg pool + event-loop trap).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from aiflow.intake.exceptions import InvalidStateTransitionError
from aiflow.intake.package import (
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakePackageStatus,
    IntakeSourceType,
)
from aiflow.intake.state_machine import PACKAGE_SM, validate_package_transition
from aiflow.state.repositories.intake import IntakeRepository


def _file(**overrides: object) -> IntakeFile:
    defaults: dict = {
        "file_path": "/tmp/phase1a.pdf",
        "file_name": "phase1a.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 2048,
        "sha256": "b" * 64,
    }
    defaults.update(overrides)
    return IntakeFile(**defaults)


def _package(**overrides: object) -> IntakePackage:
    defaults: dict = {
        "source_type": IntakeSourceType.EMAIL,
        "tenant_id": "phase_1a_test_tenant",
        "files": [_file()],
    }
    defaults.update(overrides)
    return IntakePackage(**defaults)


class TestHappyPathTransitions:
    """Received → Normalized → Routed → Parsed → Classified → Extracted → Archived."""

    def test_received_initial_status(self) -> None:
        pkg = _package()
        assert pkg.status == IntakePackageStatus.RECEIVED

    def test_received_to_normalized(self) -> None:
        pkg = _package()
        record = PACKAGE_SM.apply(pkg, IntakePackageStatus.NORMALIZED, actor_id="normalizer")
        assert pkg.status == IntakePackageStatus.NORMALIZED
        assert record is not None
        assert record.from_status == "received"
        assert record.to_status == "normalized"
        assert record.actor_id == "normalizer"

    def test_full_happy_chain(self) -> None:
        pkg = _package()
        chain = [
            IntakePackageStatus.NORMALIZED,
            IntakePackageStatus.ROUTED,
            IntakePackageStatus.PARSED,
            IntakePackageStatus.CLASSIFIED,
            IntakePackageStatus.EXTRACTED,
            IntakePackageStatus.ARCHIVED,
        ]
        for target in chain:
            PACKAGE_SM.apply(pkg, target)
        assert pkg.status == IntakePackageStatus.ARCHIVED
        assert PACKAGE_SM.is_terminal(pkg.status)

    def test_idempotent_reapply_is_noop(self) -> None:
        pkg = _package()
        PACKAGE_SM.apply(pkg, IntakePackageStatus.NORMALIZED)
        record = PACKAGE_SM.apply(pkg, IntakePackageStatus.NORMALIZED)
        assert record is None
        assert pkg.status == IntakePackageStatus.NORMALIZED


class TestInvalidTransitions:
    def test_skip_ahead_rejected(self) -> None:
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(
                IntakePackageStatus.RECEIVED,
                IntakePackageStatus.EXTRACTED,
            )

    def test_terminal_archived_has_no_transitions(self) -> None:
        assert PACKAGE_SM.get_allowed(IntakePackageStatus.ARCHIVED) == set()
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(
                IntakePackageStatus.ARCHIVED,
                IntakePackageStatus.RECEIVED,
            )

    def test_quarantined_is_terminal(self) -> None:
        assert PACKAGE_SM.is_terminal(IntakePackageStatus.QUARANTINED)
        assert PACKAGE_SM.get_allowed(IntakePackageStatus.QUARANTINED) == set()

    def test_failed_can_resume_to_received_or_normalized(self) -> None:
        pkg = _package()
        PACKAGE_SM.apply(pkg, IntakePackageStatus.NORMALIZED)
        PACKAGE_SM.apply(pkg, IntakePackageStatus.FAILED)
        record = PACKAGE_SM.resume_from_checkpoint(
            pkg, IntakePackageStatus.NORMALIZED, actor_id="admin"
        )
        assert record is not None
        assert pkg.status == IntakePackageStatus.NORMALIZED


class TestMultiFilePackage:
    def test_package_with_multiple_files(self) -> None:
        files = [
            _file(file_name=f"doc_{i}.pdf", sha256=f"{i:064x}", sequence_index=i) for i in range(3)
        ]
        pkg = _package(files=files)
        assert len(pkg.files) == 3
        assert [f.sequence_index for f in pkg.files] == [0, 1, 2]

    def test_package_with_files_and_descriptions(self) -> None:
        pkg = _package(
            descriptions=[IntakeDescription(text="Case context note", language="en")],
        )
        assert len(pkg.files) == 1
        assert len(pkg.descriptions) == 1

    def test_empty_package_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one file"):
            IntakePackage(source_type=IntakeSourceType.EMAIL, tenant_id="t")


class TestIntakeRepositoryCrud:
    """Exercise repository methods against a mocked asyncpg pool."""

    @pytest.mark.asyncio
    async def test_insert_package_runs_transaction(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        pkg = _package()
        repo = IntakeRepository(pool)
        await repo.insert_package(pkg)

        conn.transaction.assert_called_once()
        assert conn.execute.await_count >= 2

    @pytest.mark.asyncio
    async def test_get_package_returns_none_when_missing(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        conn.fetchrow.return_value = None
        repo = IntakeRepository(pool)

        result = await repo.get_package(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_transition_status_idempotent(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        conn.fetchval.return_value = "normalized"
        repo = IntakeRepository(pool)

        await repo.transition_status(uuid4(), IntakePackageStatus.NORMALIZED)
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_transition_status_applies_valid_transition(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        conn.fetchval.return_value = "received"
        repo = IntakeRepository(pool)

        await repo.transition_status(uuid4(), IntakePackageStatus.NORMALIZED)
        conn.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transition_status_rejects_invalid(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        conn.fetchval.return_value = "received"
        repo = IntakeRepository(pool)

        with pytest.raises(InvalidStateTransitionError):
            await repo.transition_status(uuid4(), IntakePackageStatus.EXTRACTED)

    @pytest.mark.asyncio
    async def test_transition_status_missing_package_raises(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        conn.fetchval.return_value = None
        repo = IntakeRepository(pool)

        with pytest.raises(ValueError, match="not found"):
            await repo.transition_status(uuid4(), IntakePackageStatus.NORMALIZED)

    @pytest.mark.asyncio
    async def test_list_packages_enforces_tenant(self, mock_pool: tuple) -> None:
        pool, conn = mock_pool
        conn.fetch.return_value = []
        repo = IntakeRepository(pool)

        await repo.list_packages("acme", status=IntakePackageStatus.PARSED, limit=10)
        args = conn.fetch.await_args.args
        assert "acme" in args
        assert "parsed" in args


class TestProvenance:
    def test_transition_record_has_audit_fields(self) -> None:
        pkg = _package()
        record = PACKAGE_SM.apply(
            pkg,
            IntakePackageStatus.NORMALIZED,
            actor_id="intake_service",
            metadata={"trigger": "webhook"},
        )
        assert record is not None
        assert record.actor_id == "intake_service"
        assert record.metadata["trigger"] == "webhook"
        assert isinstance(record.timestamp, datetime)
