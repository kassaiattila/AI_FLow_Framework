"""
@test_registry:
    suite: integration-services
    component: services.email_connector.orchestrator (S135 extraction real-stack)
    covers:
        - src/aiflow/services/email_connector/orchestrator.py
        - skills/invoice_processor/workflows/process.py
    phase: 1
    priority: critical
    estimated_duration_ms: 60000
    requires_services: [postgres, openai, docling]
    tags: [integration, email_connector, extraction, sprint-q, s135, real-stack]

Sprint Q / S135 — live extraction on Sprint O fixture `001_invoice_march`.
Seeds the email through scan_and_classify against real Postgres with a
real docling + real OpenAI LLM call. Asserts the invoice_number is
extracted and persisted under `workflow_runs.output_data.extracted_fields`.

Skipped when OPENAI_API_KEY is missing or docling can't read the fixture
PDF (same pattern as test_attachment_intent_classify.py).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from dotenv import load_dotenv
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)

from aiflow.api.deps import get_pool  # noqa: E402
from aiflow.core.config import UC3AttachmentIntentSettings, UC3ExtractionSettings  # noqa: E402
from aiflow.models.backends.litellm_backend import LiteLLMBackend  # noqa: E402
from aiflow.models.client import ModelClient  # noqa: E402
from aiflow.services.classifier.service import (  # noqa: E402
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
)
from aiflow.services.email_connector.orchestrator import (  # noqa: E402
    SKILL_NAME,
    WORKFLOW_NAME,
    scan_and_classify,
)
from aiflow.sources import EmailSourceAdapter, IntakePackageSink  # noqa: E402
from aiflow.sources.email_adapter import ImapBackendProtocol  # noqa: E402
from aiflow.state.repositories.intake import IntakeRepository  # noqa: E402
from aiflow.state.repository import StateRepository  # noqa: E402

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
        self._flag: dict[int, str] = {}

    async def fetch_unseen(self) -> list[tuple[int, bytes]]:
        return [(u, r) for u, r in self._inbox if u not in self._seen]

    async def mark_seen(self, uid: int) -> None:
        self._seen.add(uid)

    async def mark_flagged(self, uid: int, reason: str) -> None:
        self._flag[uid] = reason

    async def ping(self) -> bool:
        return True


async def _docling_can_read_fixture() -> bool:
    """Gate for Linux CI where docling silently returns empty text on
    reportlab-generated PDFs."""
    import email
    from email.message import Message

    from aiflow.tools.attachment_processor import AttachmentProcessor

    msg: Message = email.message_from_bytes(FIXTURE_PATH.read_bytes())
    pdf_part = next(
        (
            p
            for p in msg.walk()
            if not p.is_multipart() and (p.get_filename() or "").lower().endswith(".pdf")
        ),
        None,
    )
    if pdf_part is None:
        return False
    payload = pdf_part.get_payload(decode=True) or b""
    try:
        result = await AttachmentProcessor().process(
            pdf_part.get_filename(), payload, pdf_part.get_content_type()
        )
    except Exception:
        return False
    return bool(result.text) and "INV-2026" in result.text


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
                """DELETE FROM package_associations
                   WHERE file_id IN (
                     SELECT file_id FROM intake_files WHERE package_id = ANY($1::uuid[])
                   )""",
                ids,
            )
            await conn.execute(
                "DELETE FROM intake_descriptions WHERE package_id = ANY($1::uuid[])", ids
            )
            await conn.execute("DELETE FROM intake_files WHERE package_id = ANY($1::uuid[])", ids)
            await conn.execute(
                "DELETE FROM intake_packages WHERE package_id = ANY($1::uuid[])", ids
            )


async def test_extraction_fixture_001_invoice_march_end_to_end(tmp_path: Path) -> None:
    """Real stack: scan → classify → extract → persist on 001_invoice_march."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY missing — S135 integration needs the LLM")
    if not await _docling_can_read_fixture():
        pytest.skip(
            "Local docling cannot extract 'INV-2026-...' from the fixture PDF — "
            "typical on Linux CI without the docling text-layer extractor."
        )

    tenant_id = f"tenant-s135-{uuid4().hex[:8]}"
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

    llm_backend = LiteLLMBackend(default_model="openai/gpt-4o-mini")
    classifier = ClassifierService(
        config=ClassifierConfig(
            strategy=ClassificationStrategy.SKLEARN_FIRST, confidence_threshold=0.6
        ),
        models_client=ModelClient(generation_backend=llm_backend),
    )
    await classifier.start()

    attachment_settings = UC3AttachmentIntentSettings(
        enabled=True, total_budget_seconds=60.0, classifier_strategy="sklearn_first"
    )
    extraction_settings = UC3ExtractionSettings(
        enabled=True, total_budget_seconds=120.0, extraction_budget_usd=0.10
    )

    try:
        results = await scan_and_classify(
            adapter,
            sink,
            classifier,
            state_repo,
            tenant_id=tenant_id,
            max_items=1,
            schema_labels=_load_schema_labels(),
            attachment_intent_settings=attachment_settings,
            extraction_settings=extraction_settings,
        )

        assert len(results) == 1
        _pkg, classification = results[0]

        # Sprint P behaviour: classifier lands on an EXTRACT label.
        assert classification.label in {"invoice_received", "order"}

        # Sprint Q behaviour: extracted_fields must be present with
        # non-empty invoice_number for the single PDF attachment.
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
        assert "extracted_fields" in od
        files = od["extracted_fields"]
        assert len(files) >= 1
        # First file must have a populated header with an invoice_number
        # starting with "INV-2026-" (Sprint O fixture pattern).
        first_key = next(iter(files))
        first = files[first_key]
        assert "error" not in first, f"extraction raised: {first.get('error')}"
        invoice_number = (first.get("header") or {}).get("invoice_number", "")
        assert isinstance(invoice_number, str) and "INV-2026" in invoice_number.upper()

    finally:
        await classifier.stop()
        async with engine.begin() as conn:
            await conn.execute(
                sa_text(
                    """DELETE FROM step_runs WHERE workflow_run_id IN (
                         SELECT id FROM workflow_runs WHERE workflow_name = :wf
                           AND (output_data->>'tenant_id') = :tid)"""
                ),
                {"wf": WORKFLOW_NAME, "tid": tenant_id},
            )
            await conn.execute(
                sa_text(
                    "DELETE FROM workflow_runs WHERE workflow_name = :wf "
                    "AND (output_data->>'tenant_id') = :tid"
                ),
                {"wf": WORKFLOW_NAME, "tid": tenant_id},
            )
        await _cleanup_tenant(pool, tenant_id)
        await engine.dispose()
