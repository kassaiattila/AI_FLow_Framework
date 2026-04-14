"""IntakeRepository unit tests — SQL mapping, transition validation, helpers.

These tests validate the repository logic without a live database:
- _parse_jsonb / _row_to_package helper correctness
- transition_status idempotency and validation delegation
- list_packages tenant isolation (query parameter assertions)
- insert_package parameter ordering
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from aiflow.intake.exceptions import InvalidStateTransitionError
from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakePackageStatus,
    IntakeSourceType,
)
from aiflow.state.repositories.intake import IntakeRepository, _parse_jsonb, _row_to_package

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file(**overrides: object) -> IntakeFile:
    defaults: dict = {
        "file_path": "/tmp/test.pdf",
        "file_name": "test.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1024,
        "sha256": "a" * 64,
    }
    defaults.update(overrides)
    return IntakeFile(**defaults)


def _make_description(**overrides: object) -> IntakeDescription:
    defaults: dict = {
        "text": "Test description",
    }
    defaults.update(overrides)
    return IntakeDescription(**defaults)


def _make_package(**overrides: object) -> IntakePackage:
    defaults: dict = {
        "source_type": IntakeSourceType.EMAIL,
        "tenant_id": "test_tenant",
        "files": [_make_file()],
    }
    defaults.update(overrides)
    return IntakePackage(**defaults)


def _make_db_row(
    *,
    package_id: UUID | None = None,
    source_type: str = "email",
    tenant_id: str = "test_tenant",
    status: str = "received",
    source_metadata: str = "{}",
    package_context: str = "{}",
    cross_document_signals: str = "{}",
    received_by: str | None = None,
    provenance_chain: list | None = None,
    routing_decision_id: UUID | None = None,
    review_task_id: UUID | None = None,
) -> dict:
    now = datetime.now(tz=UTC)
    return {
        "package_id": package_id or uuid4(),
        "source_type": source_type,
        "tenant_id": tenant_id,
        "status": status,
        "source_metadata": source_metadata,
        "package_context": package_context,
        "cross_document_signals": cross_document_signals,
        "created_at": now,
        "updated_at": now,
        "received_by": received_by,
        "provenance_chain": provenance_chain or [],
        "routing_decision_id": routing_decision_id,
        "review_task_id": review_task_id,
    }


def _mock_pool() -> tuple[MagicMock, AsyncMock]:
    """Create a mock asyncpg pool with nested connection + transaction context managers."""
    pool = MagicMock()
    conn = AsyncMock()

    # asyncpg's conn.transaction() is a sync call returning an async context manager
    tx = MagicMock()
    tx.__aenter__ = AsyncMock(return_value=tx)
    tx.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=tx)

    acq = MagicMock()
    acq.__aenter__ = AsyncMock(return_value=conn)
    acq.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acq)

    return pool, conn


# ---------------------------------------------------------------------------
# _parse_jsonb tests
# ---------------------------------------------------------------------------


class TestParseJsonb:
    def test_none_returns_empty_dict(self) -> None:
        assert _parse_jsonb(None) == {}

    def test_dict_passthrough(self) -> None:
        d = {"key": "value"}
        assert _parse_jsonb(d) is d

    def test_json_string_parsed(self) -> None:
        assert _parse_jsonb('{"a": 1}') == {"a": 1}

    def test_empty_string_object(self) -> None:
        assert _parse_jsonb("{}") == {}


# ---------------------------------------------------------------------------
# _row_to_package tests
# ---------------------------------------------------------------------------


class TestRowToPackage:
    def test_basic_conversion(self) -> None:
        pid = uuid4()
        row = _make_db_row(package_id=pid, tenant_id="acme")
        pkg = _row_to_package(row)

        assert pkg.package_id == pid
        assert pkg.tenant_id == "acme"
        assert pkg.source_type == IntakeSourceType.EMAIL
        assert pkg.status == IntakePackageStatus.RECEIVED
        assert pkg.files == []
        assert pkg.descriptions == []

    def test_all_statuses_parseable(self) -> None:
        for status in IntakePackageStatus:
            row = _make_db_row(status=status.value)
            pkg = _row_to_package(row)
            assert pkg.status == status

    def test_all_source_types_parseable(self) -> None:
        for st in IntakeSourceType:
            row = _make_db_row(source_type=st.value)
            pkg = _row_to_package(row)
            assert pkg.source_type == st

    def test_jsonb_fields_parsed(self) -> None:
        row = _make_db_row(
            source_metadata='{"email_from": "test@example.com"}',
            package_context='{"case_id": "C-100"}',
            cross_document_signals='{"has_invoice": true}',
        )
        pkg = _row_to_package(row)
        assert pkg.source_metadata == {"email_from": "test@example.com"}
        assert pkg.package_context == {"case_id": "C-100"}
        assert pkg.cross_document_signals == {"has_invoice": True}

    def test_provenance_chain_none_becomes_empty_list(self) -> None:
        row = _make_db_row(provenance_chain=None)
        pkg = _row_to_package(row)
        assert pkg.provenance_chain == []

    def test_provenance_chain_preserved(self) -> None:
        chain = [uuid4(), uuid4()]
        row = _make_db_row(provenance_chain=chain)
        pkg = _row_to_package(row)
        assert pkg.provenance_chain == chain


# ---------------------------------------------------------------------------
# insert_package tests
# ---------------------------------------------------------------------------


class TestInsertPackage:
    @pytest.mark.asyncio
    async def test_insert_calls_execute_for_package(self) -> None:
        pool, conn = _mock_pool()
        repo = IntakeRepository(pool)
        pkg = _make_package()

        await repo.insert_package(pkg)

        calls = conn.execute.call_args_list
        assert len(calls) >= 1
        first_sql = calls[0].args[0]
        assert "INSERT INTO intake_packages" in first_sql

    @pytest.mark.asyncio
    async def test_insert_passes_correct_package_params(self) -> None:
        pool, conn = _mock_pool()
        repo = IntakeRepository(pool)
        pkg = _make_package(
            source_type=IntakeSourceType.FILE_UPLOAD,
            tenant_id="acme_corp",
        )

        await repo.insert_package(pkg)

        args = conn.execute.call_args_list[0].args
        assert args[1] == pkg.package_id
        assert args[2] == "file_upload"
        assert args[3] == "acme_corp"
        assert args[4] == "received"

    @pytest.mark.asyncio
    async def test_insert_serializes_jsonb_fields(self) -> None:
        pool, conn = _mock_pool()
        repo = IntakeRepository(pool)
        pkg = _make_package(
            source_metadata={"email_from": "x@y.com"},
            package_context={"case_id": "C-1"},
        )

        await repo.insert_package(pkg)

        args = conn.execute.call_args_list[0].args
        assert json.loads(args[5]) == {"email_from": "x@y.com"}
        assert json.loads(args[6]) == {"case_id": "C-1"}

    @pytest.mark.asyncio
    async def test_insert_with_files_calls_file_insert(self) -> None:
        pool, conn = _mock_pool()
        repo = IntakeRepository(pool)
        f1 = _make_file(file_name="a.pdf")
        f2 = _make_file(file_name="b.pdf")
        pkg = _make_package(files=[f1, f2])

        await repo.insert_package(pkg)

        file_calls = [
            c for c in conn.execute.call_args_list if "INSERT INTO intake_files" in c.args[0]
        ]
        assert len(file_calls) == 2
        assert file_calls[0].args[4] == "a.pdf"
        assert file_calls[1].args[4] == "b.pdf"

    @pytest.mark.asyncio
    async def test_insert_with_descriptions_calls_desc_insert(self) -> None:
        pool, conn = _mock_pool()
        repo = IntakeRepository(pool)
        d1 = _make_description(text="First")
        d2 = _make_description(text="Second")
        pkg = _make_package(descriptions=[d1, d2])

        await repo.insert_package(pkg)

        desc_calls = [
            c for c in conn.execute.call_args_list if "INSERT INTO intake_descriptions" in c.args[0]
        ]
        assert len(desc_calls) == 2
        assert desc_calls[0].args[3] == "First"
        assert desc_calls[1].args[3] == "Second"

    @pytest.mark.asyncio
    async def test_insert_with_associations(self) -> None:
        pool, conn = _mock_pool()
        repo = IntakeRepository(pool)
        f = _make_file()
        d = _make_description(associated_file_ids=[f.file_id])
        pkg = _make_package(files=[f], descriptions=[d])

        await repo.insert_package(pkg)

        assoc_calls = [
            c
            for c in conn.execute.call_args_list
            if "INSERT INTO package_associations" in c.args[0]
        ]
        assert len(assoc_calls) == 1
        assert assoc_calls[0].args[1] == f.file_id
        assert assoc_calls[0].args[2] == d.description_id


# ---------------------------------------------------------------------------
# get_package tests
# ---------------------------------------------------------------------------


class TestGetPackage:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchrow.return_value = None
        repo = IntakeRepository(pool)

        result = await repo.get_package(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_hydrated_package(self) -> None:
        pool, conn = _mock_pool()
        pid = uuid4()
        fid = uuid4()
        did = uuid4()
        now = datetime.now(tz=UTC)

        conn.fetchrow.return_value = {
            "package_id": pid,
            "source_type": "email",
            "tenant_id": "acme",
            "status": "received",
            "source_metadata": {},
            "package_context": {},
            "cross_document_signals": {},
            "created_at": now,
            "updated_at": now,
            "received_by": None,
            "provenance_chain": [],
            "routing_decision_id": None,
            "review_task_id": None,
        }

        conn.fetch.side_effect = [
            [
                {
                    "file_id": fid,
                    "file_path": "/tmp/test.pdf",
                    "file_name": "test.pdf",
                    "mime_type": "application/pdf",
                    "size_bytes": 1024,
                    "sha256": "a" * 64,
                    "source_metadata": {},
                    "sequence_index": 0,
                },
            ],
            [
                {
                    "description_id": did,
                    "text": "Hello",
                    "language": "en",
                    "role": "free_text",
                    "association_confidence": None,
                    "association_method": None,
                },
            ],
            [],
        ]

        repo = IntakeRepository(pool)
        result = await repo.get_package(pid)

        assert result is not None
        assert result.package_id == pid
        assert result.tenant_id == "acme"
        assert len(result.files) == 1
        assert result.files[0].file_id == fid
        assert len(result.descriptions) == 1
        assert result.descriptions[0].description_id == did
        assert result.descriptions[0].role == DescriptionRole.FREE_TEXT


# ---------------------------------------------------------------------------
# transition_status tests
# ---------------------------------------------------------------------------


class TestTransitionStatus:
    @pytest.mark.asyncio
    async def test_raises_on_missing_package(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = None
        repo = IntakeRepository(pool)

        with pytest.raises(ValueError, match="not found"):
            await repo.transition_status(uuid4(), IntakePackageStatus.NORMALIZED)

    @pytest.mark.asyncio
    async def test_idempotent_skip_same_status(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = "received"
        repo = IntakeRepository(pool)

        await repo.transition_status(uuid4(), IntakePackageStatus.RECEIVED)

        update_calls = [c for c in conn.execute.call_args_list if "UPDATE" in str(c)]
        assert len(update_calls) == 0

    @pytest.mark.asyncio
    async def test_valid_transition_updates_status(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = "received"
        repo = IntakeRepository(pool)
        pid = uuid4()

        await repo.transition_status(pid, IntakePackageStatus.NORMALIZED)

        update_calls = [c for c in conn.execute.call_args_list if "UPDATE" in c.args[0]]
        assert len(update_calls) == 1
        assert update_calls[0].args[1] == "normalized"
        assert update_calls[0].args[2] == pid

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = "received"
        repo = IntakeRepository(pool)

        with pytest.raises(InvalidStateTransitionError):
            await repo.transition_status(uuid4(), IntakePackageStatus.ARCHIVED)

    @pytest.mark.asyncio
    async def test_recovery_transition_from_failed(self) -> None:
        pool, conn = _mock_pool()
        conn.fetchval.return_value = "failed"
        repo = IntakeRepository(pool)

        await repo.transition_status(uuid4(), IntakePackageStatus.RECEIVED)

        update_calls = [c for c in conn.execute.call_args_list if "UPDATE" in c.args[0]]
        assert len(update_calls) == 1
        assert update_calls[0].args[1] == "received"


# ---------------------------------------------------------------------------
# list_packages tests
# ---------------------------------------------------------------------------


class TestListPackages:
    @pytest.mark.asyncio
    async def test_list_passes_tenant_id_filter(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []
        repo = IntakeRepository(pool)

        await repo.list_packages("acme_corp")

        sql, tenant_arg = conn.fetch.call_args.args[0], conn.fetch.call_args.args[1]
        assert "WHERE tenant_id = $1" in sql
        assert tenant_arg == "acme_corp"

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []
        repo = IntakeRepository(pool)

        await repo.list_packages("acme", status=IntakePackageStatus.ROUTED)

        sql = conn.fetch.call_args.args[0]
        assert "status = $2" in sql
        assert conn.fetch.call_args.args[2] == "routed"

    @pytest.mark.asyncio
    async def test_list_respects_limit_offset(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []
        repo = IntakeRepository(pool)

        await repo.list_packages("t1", limit=10, offset=20)

        args = conn.fetch.call_args.args
        assert args[2] == 10
        assert args[3] == 20

    @pytest.mark.asyncio
    async def test_list_returns_lightweight_packages(self) -> None:
        pool, conn = _mock_pool()
        row = _make_db_row(tenant_id="t1")
        conn.fetch.return_value = [row]
        repo = IntakeRepository(pool)

        results = await repo.list_packages("t1")

        assert len(results) == 1
        assert results[0].tenant_id == "t1"
        assert results[0].files == []
        assert results[0].descriptions == []

    @pytest.mark.asyncio
    async def test_list_different_tenant_isolation(self) -> None:
        pool, conn = _mock_pool()
        conn.fetch.return_value = []
        repo = IntakeRepository(pool)

        await repo.list_packages("tenant_a")
        call1_tenant = conn.fetch.call_args_list[0].args[1]

        await repo.list_packages("tenant_b")
        call2_tenant = conn.fetch.call_args_list[1].args[1]

        assert call1_tenant == "tenant_a"
        assert call2_tenant == "tenant_b"
