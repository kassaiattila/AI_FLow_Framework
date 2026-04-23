"""
@test_registry:
    suite: integration-services
    component: services.email_connector.orchestrator (S128 attachment-aware classify)
    covers:
        - src/aiflow/services/email_connector/orchestrator.py
        - src/aiflow/services/classifier/service.py
        - src/aiflow/services/classifier/attachment_features.py
    phase: 1
    priority: critical
    estimated_duration_ms: 30000
    requires_services: [postgres]
    tags: [integration, email_connector, scan_classify, uc3, sprint-o, attachment_intent]

UC3 Sprint O / S128 — flag-on classification on a real fixture against
real PostgreSQL. Picks fixture ``001_invoice_march.eml`` which the Sprint K
body-only baseline misclassified as ``unknown`` (see
``docs/uc3_attachment_baseline.md``). With the attachment-intent flag ON,
the orchestrator extracts ``invoice_number_detected=True`` from the PDF
and the rule boost should land the run on a label in
``EXTRACT_INTENT_IDS``.

NOTE (feedback_asyncpg_pool_event_loop.md): single ``@pytest.mark.asyncio``
method to share a single event-loop-bound pool across DB assertions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aiflow.api.deps import get_pool
from aiflow.core.config import UC3AttachmentIntentSettings
from aiflow.services.classifier.service import (
    EXTRACT_INTENT_IDS,
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

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "emails_sprint_o" / "001_invoice_march.eml"
INTENT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "email_intent_processor" / "schemas" / "v1" / "intents.json"
)

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)


def _load_schema_labels() -> list[dict]:
    data = json.loads(INTENT_SCHEMA_PATH.read_text(encoding="utf-8"))
    out = []
    for intent in data["intents"]:
        kw = list(intent.get("keywords_hu", [])) + list(intent.get("keywords_en", []))
        out.append(
            {
                "id": intent["id"],
                "display_name": intent.get("display_name", intent["id"]),
                "description": intent.get("description", ""),
                "keywords": kw,
                "examples": intent.get("examples", []),
            }
        )
    return out


class _SingleFixtureBackend(ImapBackendProtocol):
    def __init__(self, raw: bytes, uid: int = 1) -> None:
        self._inbox = [(uid, raw)]
        self._seen: set[int] = set()
        self._flagged: dict[int, str] = {}

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return [(u, r) for u, r in self._inbox if u not in self._seen]

    async def mark_seen(self, uid: int) -> None:
        self._seen.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        self._flagged[uid] = reason

    async def ping(self) -> bool:
        return True


async def _cleanup_tenant(pool: asyncpg.Pool, tenant_id: str) -> None:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT package_id FROM intake_packages WHERE tenant_id = $1", tenant_id
        )
        if not rows:
            return
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
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )


async def test_invoice_fixture_with_flag_on_routes_to_extract(tmp_path: Path) -> None:
    tenant_id = f"tenant-s128-{uuid4().hex[:8]}"
    storage_root = tmp_path / "email_storage"
    raw = FIXTURE_PATH.read_bytes()
    backend = _SingleFixtureBackend(raw)
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

    schema_labels = _load_schema_labels()
    settings_on = UC3AttachmentIntentSettings(enabled=True, total_budget_seconds=60.0)

    try:
        results = await scan_and_classify(
            adapter,
            sink,
            classifier,
            state_repo,
            tenant_id=tenant_id,
            max_items=1,
            schema_labels=schema_labels,
            attachment_intent_settings=settings_on,
        )

        assert len(results) == 1, "expected exactly one classified package"
        _pkg_id, classification = results[0]
        assert classification.label in EXTRACT_INTENT_IDS, (
            f"S128 rule boost must promote '001_invoice_march' (Sprint K baseline 'unknown') "
            f"into EXTRACT_INTENT_IDS, got {classification.label!r}"
        )
        assert "attachment_rule" in classification.method

        # Verify persistence: workflow_runs row must carry both attachment_features
        # and the boosted label.
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    sa_text(
                        """SELECT output_data FROM workflow_runs
                           WHERE workflow_name = :wf AND skill_name = :sk
                             AND (output_data->>'tenant_id') = :tid"""
                    ),
                    {"wf": WORKFLOW_NAME, "sk": SKILL_NAME, "tid": tenant_id},
                )
            ).all()
        assert len(rows) == 1
        od = rows[0].output_data
        assert "attachment_features" in od
        assert od["attachment_features"]["invoice_number_detected"] is True
        assert od["label"] in EXTRACT_INTENT_IDS

    finally:
        await classifier.stop()
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
