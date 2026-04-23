"""
@test_registry:
    suite: integration-services
    component: services.email_connector.orchestrator
    covers:
        - src/aiflow/services/email_connector/orchestrator.py
        - src/aiflow/services/classifier/service.py
        - src/aiflow/sources/email_adapter.py
        - src/aiflow/sources/sink.py
        - src/aiflow/state/repository.py
    phase: 1d
    priority: critical
    estimated_duration_ms: 5000
    requires_services: [postgres]
    tags: [integration, email_connector, scan_classify, uc3, sprint_k]

UC3 Sprint K S106 — scan-and-classify end-to-end against real PostgreSQL.
Two fixture emails (HU + EN) → EmailSourceAdapter (fake IMAP) → IntakePackageSink
→ ClassifierService (sklearn_only) → StateRepository.workflow_runs rows.

NOTE (feedback_asyncpg_pool_event_loop.md): all DB-touching assertions live
in one ``@pytest.mark.asyncio`` method to share a single event-loop-bound
pool across them.
"""

from __future__ import annotations

import os
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from structlog.testing import capture_logs

from aiflow.api.deps import get_pool
from aiflow.services.classifier.service import (
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
)
from aiflow.services.email_connector.orchestrator import (
    SKILL_NAME,
    WORKFLOW_NAME,
    scan_and_classify,
)
from aiflow.sources import EmailSourceAdapter, IntakePackageSink
from aiflow.sources.email_adapter import ImapBackendProtocol
from aiflow.state.repositories.intake import IntakeRepository
from aiflow.state.repository import StateRepository

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)

_SCHEMA_LABELS = [
    {
        "id": "invoice_question",
        "display_name": "Invoice Question",
        "description": "Questions about invoices, billing, payments.",
        "keywords": ["invoice", "számla", "billing", "payment", "fizetés"],
        "examples": [],
    },
    {
        "id": "support_request",
        "display_name": "Support Request",
        "description": "Technical support requests or bug reports.",
        "keywords": ["bug", "error", "hiba", "support", "segítség"],
        "examples": [],
    },
]


class _FakeImapBackend(ImapBackendProtocol):
    """In-memory IMAP backend — fixture pattern shared with tests/e2e/sources/."""

    def __init__(self, inbox: list[tuple[int, bytes]]) -> None:
        self.inbox = list(inbox)
        self.seen: set[int] = set()
        self.flagged: dict[int, str] = {}

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return [(u, r) for u, r in self.inbox if u not in self.seen]

    async def mark_seen(self, uid: int) -> None:
        self.seen.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        self.flagged[uid] = reason

    async def ping(self) -> bool:
        return True


def _build_email(*, subject: str, sender: str, body: str) -> bytes:
    """Build an RFC822 email with one tiny text attachment.

    The attachment is required only to satisfy the intake CHECK constraint
    (``association_mode`` must be set when descriptions exist); 1 file + 1
    description yields ORDER mode in ``_infer_mode``. Production text-only
    emails are a separate wiring concern tracked for S107.
    """
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "intake@example.com"
    msg.set_content(body)
    msg.add_attachment(
        b"fixture marker\n",
        maintype="text",
        subtype="plain",
        filename="note.txt",
    )
    return msg.as_bytes()


async def _cleanup_tenant(pool: asyncpg.Pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1",
            tenant_id,
        )
        if rows:
            ids = [r["package_id"] for r in rows]
            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM package_associations
                    WHERE file_id IN (
                        SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[])
                    )
                    """,
                    ids,
                )
                await conn.execute(
                    "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])", ids
                )
                await conn.execute(
                    "DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids
                )
                await conn.execute(
                    "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
                )


async def test_scan_and_classify_two_emails_persist_workflow_runs(tmp_path: Path) -> None:
    tenant_id = f"tenant-s106-{uuid4().hex[:8]}"
    storage_root = tmp_path / "email_storage"

    inbox = [
        (
            101,
            _build_email(
                subject="Kérdés a márciusi számlához",
                sender="hu@example.com",
                body="Kaptam egy számlát, segítséget kérek a fizetéssel.",
            ),
        ),
        (
            202,
            _build_email(
                subject="Bug report — login page error",
                sender="en@example.com",
                body="I keep getting an error on the login page, please support.",
            ),
        ),
    ]
    backend = _FakeImapBackend(inbox)

    adapter = EmailSourceAdapter(backend=backend, storage_root=storage_root, tenant_id=tenant_id)

    pool = await get_pool()
    intake_repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=intake_repo)

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_repo = StateRepository(session_factory)

    classifier = ClassifierService(
        config=ClassifierConfig(
            strategy=ClassificationStrategy.SKLEARN_ONLY, confidence_threshold=0.0
        )
    )
    await classifier.start()

    created_run_ids: list[str] = []
    try:
        with capture_logs() as events:
            results = await scan_and_classify(
                adapter,
                sink,
                classifier,
                state_repo,
                tenant_id=tenant_id,
                max_items=10,
                schema_labels=_SCHEMA_LABELS,
            )

        # --- Return value assertions ------------------------------------
        assert len(results) == 2, f"expected 2 results, got {results}"
        package_ids = {pid for pid, _ in results}
        assert len(package_ids) == 2, "package_ids must be unique"

        # --- IntakePackage persistence ----------------------------------
        async with pool.acquire() as conn:
            pkg_count = await conn.fetchval(
                "SELECT COUNT(*) FROM intake_packages WHERE tenant_id = $1", tenant_id
            )
            assert pkg_count == 2, f"expected 2 intake_packages rows, got {pkg_count}"

        # --- workflow_runs persistence ----------------------------------
        async with engine.begin() as conn:
            run_rows = (
                await conn.execute(
                    sa_text(
                        """SELECT id, skill_name, workflow_name, status, output_data
                           FROM workflow_runs
                           WHERE workflow_name = :wf AND skill_name = :sk
                             AND (output_data->>'tenant_id') = :tid
                           ORDER BY created_at"""
                    ),
                    {"wf": WORKFLOW_NAME, "sk": SKILL_NAME, "tid": tenant_id},
                )
            ).all()

        assert len(run_rows) == 2, f"expected 2 workflow_runs, got {len(run_rows)}"
        for row in run_rows:
            assert row.status == "completed"
            assert row.skill_name == SKILL_NAME
            od = row.output_data
            assert od["tenant_id"] == tenant_id
            assert "package_id" in od
            assert "label" in od
            assert isinstance(od["confidence"], (int, float))
            created_run_ids.append(str(row.id))

        # --- Observability events --------------------------------------
        item_done = [
            e for e in events if e.get("event") == "email_connector.scan_and_classify.item_done"
        ]
        assert len(item_done) == 2, (
            f"expected 2 item_done events, got {len(item_done)}: {[e.get('event') for e in events]}"
        )
        for ev in item_done:
            assert ev["tenant_id"] == tenant_id
            assert "workflow_run_id" in ev
            assert "package_id" in ev
            assert "label" in ev

    finally:
        await classifier.stop()

        # Clean test data so repeated runs stay deterministic.
        async with engine.begin() as conn:
            await conn.execute(
                sa_text(
                    """DELETE FROM step_runs
                       WHERE workflow_run_id IN (
                           SELECT id FROM workflow_runs
                           WHERE workflow_name = :wf
                             AND (output_data->>'tenant_id') = :tid
                       )"""
                ),
                {"wf": WORKFLOW_NAME, "tid": tenant_id},
            )
            await conn.execute(
                sa_text(
                    """DELETE FROM workflow_runs
                       WHERE workflow_name = :wf
                         AND (output_data->>'tenant_id') = :tid"""
                ),
                {"wf": WORKFLOW_NAME, "tid": tenant_id},
            )
        await _cleanup_tenant(pool, tenant_id)
        await engine.dispose()
