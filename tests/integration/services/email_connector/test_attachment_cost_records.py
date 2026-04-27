"""
@test_registry:
    suite: integration-services
    component: services.email_connector.orchestrator (FU-7 cost emission)
    covers:
        - src/aiflow/services/email_connector/orchestrator.py
        - src/aiflow/tools/attachment_cost.py
        - src/aiflow/api/cost_recorder.py
    phase: sprint-o-fu-7
    priority: critical
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, email_connector, cost, sprint-o, fu-7]

Sprint O FU-7 — asserts the orchestrator emits one ``cost_records`` row
per processed attachment when flag-on. Uses a monkeypatched
AttachmentProcessor stub (hermetic — no docling cold start) but a real
Postgres connection, so the cost_recorder SQL path is exercised.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import asyncpg
import pytest

from aiflow.api.deps import get_pool
from aiflow.core.config import UC3AttachmentIntentSettings
from aiflow.intake.package import (
    DescriptionRole,
    IntakeDescription,
    IntakeFile,
    IntakePackage,
    IntakeSourceType,
)
from aiflow.services.classifier.service import (
    ClassificationResult,
)
from aiflow.services.email_connector.orchestrator import scan_and_classify
from aiflow.tools.attachment_processor import ProcessedAttachment

pytestmark = pytest.mark.asyncio

PG_DSN = (
    os.getenv("AIFLOW_DATABASE__URL")
    or os.getenv("AIFLOW_TEST_DSN")
    or "postgresql://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev"
).replace("postgresql+asyncpg://", "postgresql://")


# -----------------------------------------------------------------------------
# Minimal doubles — no DB session, no real classifier, no docling.
# -----------------------------------------------------------------------------


class _StubProcessor:
    """Returns a deterministic Azure-DI-shaped attachment so cost > 0."""

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    async def process(self, filename: str, content: bytes, mime_type: str) -> ProcessedAttachment:
        return ProcessedAttachment(
            filename=filename,
            mime_type=mime_type,
            text="FU-7 stub invoice",
            processor_used="azure_di",
            metadata={"pages": 3},
        )


class _FakeAdapter:
    def __init__(self, packages: list[IntakePackage]) -> None:
        self._pkgs = list(packages)

    async def fetch_next(self) -> IntakePackage | None:
        return self._pkgs.pop(0) if self._pkgs else None

    async def acknowledge(self, package_id: UUID) -> None:
        return None


class _FakeSink:
    async def handle(self, package: IntakePackage) -> None:
        return None


class _FakeClassifier:
    async def classify(self, **kwargs: Any) -> ClassificationResult:
        return ClassificationResult(
            label="invoice_received",
            display_name="Invoice",
            confidence=0.7,
            method="keywords",
        )


class _FakeRun:
    def __init__(self, run_id: UUID) -> None:
        self.id = run_id


class _FakeRepo:
    """Persists a real ``workflow_runs`` row so cost_recorder's FK holds.

    Earlier versions returned a synthetic UUID without seeding the DB,
    which silently broke cost emission (cost_recorder swallowed the
    asyncpg ``ForeignKeyViolationError`` and the test asserted on zero
    rows). The cost_recorder writes through :func:`get_pool` — using the
    same pool here keeps the test hermetic to a single DB connection.
    """

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []
        self.last_run_id: UUID | None = None

    async def create_workflow_run(
        self,
        workflow_name: str = "test_workflow",
        workflow_version: str = "1.0",
        input_data: dict[str, Any] | None = None,
        *,
        skill_name: str | None = None,
        **_: Any,
    ) -> _FakeRun:
        import json

        from aiflow.api.deps import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_runs
                    (workflow_name, workflow_version, skill_name, status, input_data)
                VALUES ($1, $2, $3, 'running', $4::jsonb)
                RETURNING id
                """,
                workflow_name,
                workflow_version,
                skill_name,
                json.dumps(input_data or {}),
            )
        run_id: UUID = row["id"]
        self.last_run_id = run_id
        return _FakeRun(run_id)

    async def update_workflow_run_status(
        self, run_id: UUID, status: str, *, output_data: dict[str, Any] | None = None
    ) -> None:
        self.updates.append({"run_id": run_id, "output_data": output_data or {}})


def _make_file(tmp_path: Any) -> IntakeFile:
    """A real on-disk file so the orchestrator's read_bytes() works."""
    p = tmp_path / "fu7_invoice.pdf"
    p.write_bytes(b"%PDF-1.4 FU-7 stub")
    return IntakeFile(
        file_path=str(p),
        file_name=p.name,
        mime_type="application/pdf",
        size_bytes=p.stat().st_size,
        sha256="0" * 64,
    )


def _make_package(tmp_path: Any) -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id=f"fu7-{uuid4().hex[:8]}",
        files=[_make_file(tmp_path)],
        descriptions=[
            IntakeDescription(
                text="please pay the invoice", language="en", role=DescriptionRole.EMAIL_BODY
            )
        ],
    )


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


@pytest.fixture()
async def pg_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """A direct asyncpg connection for assertions + cleanup."""
    conn = await asyncpg.connect(PG_DSN)
    try:
        yield conn
    finally:
        await conn.close()


async def test_cost_records_row_per_processed_attachment(
    tmp_path: Any, pg_conn: asyncpg.Connection
) -> None:
    """Flag-on scan with one Azure-DI attachment lands one cost_records row
    with cost > 0 and step_name tagged with the processor."""
    package = _make_package(tmp_path)
    adapter = _FakeAdapter([package])
    repo = _FakeRepo()
    settings_on = UC3AttachmentIntentSettings(enabled=True, total_budget_seconds=30.0)

    # Ensure the pool is the same one the cost_recorder picks up.
    await get_pool()

    with patch("aiflow.tools.attachment_processor.AttachmentProcessor", _StubProcessor):
        await scan_and_classify(
            adapter,
            _FakeSink(),
            _FakeClassifier(),
            repo,
            tenant_id="fu7-tenant",
            attachment_intent_settings=settings_on,
        )

    assert repo.last_run_id is not None
    run_id = repo.last_run_id

    # cost_records row must be present for this run, tagged with the
    # attachment processor, and carry a non-zero USD cost.
    rows = await pg_conn.fetch(
        """SELECT step_name, model, cost_usd
             FROM cost_records
            WHERE workflow_run_id = $1""",
        run_id,
    )
    try:
        assert len(rows) == 1, f"expected 1 cost_records row, got {len(rows)}"
        r = rows[0]
        assert r["step_name"] == "attachment:azure_di"
        assert r["model"] == "azure_di"
        assert float(r["cost_usd"]) > 0.0
    finally:
        await pg_conn.execute("DELETE FROM cost_records WHERE workflow_run_id = $1", run_id)
        await pg_conn.execute("DELETE FROM workflow_runs WHERE id = $1", run_id)


async def test_failed_attachment_does_not_emit_cost_record(
    tmp_path: Any, pg_conn: asyncpg.Connection
) -> None:
    """A processor returning an error string must not charge the tenant."""

    class _FailingProcessor:
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

        async def process(
            self, filename: str, content: bytes, mime_type: str
        ) -> ProcessedAttachment:
            return ProcessedAttachment(
                filename=filename,
                mime_type=mime_type,
                error="timeout",
                processor_used="azure_failed",
            )

    package = _make_package(tmp_path)
    adapter = _FakeAdapter([package])
    repo = _FakeRepo()
    settings_on = UC3AttachmentIntentSettings(enabled=True, total_budget_seconds=30.0)

    await get_pool()

    with patch("aiflow.tools.attachment_processor.AttachmentProcessor", _FailingProcessor):
        await scan_and_classify(
            adapter,
            _FakeSink(),
            _FakeClassifier(),
            repo,
            tenant_id="fu7-tenant-fail",
            attachment_intent_settings=settings_on,
        )

    run_id = repo.last_run_id
    rows = await pg_conn.fetch("SELECT id FROM cost_records WHERE workflow_run_id = $1", run_id)
    try:
        assert len(rows) == 0, "failed attachments must not emit cost_records"
    finally:
        if rows:
            await pg_conn.execute("DELETE FROM cost_records WHERE workflow_run_id = $1", run_id)
        if run_id is not None:
            await pg_conn.execute("DELETE FROM workflow_runs WHERE id = $1", run_id)
