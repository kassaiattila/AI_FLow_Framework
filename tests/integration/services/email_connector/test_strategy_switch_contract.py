"""
@test_registry:
    suite: integration-services
    component: services.email_connector.orchestrator (S132 strategy + contract)
    covers:
        - src/aiflow/services/classifier/service.py (_keywords_first early-return)
        - src/aiflow/services/email_connector/orchestrator.py
        - src/aiflow/core/config.py (UC3AttachmentIntentSettings.classifier_strategy)
    phase: sprint-p-s132
    priority: critical
    estimated_duration_ms: 20000
    requires_services: [postgres]
    tags: [integration, email_connector, classifier, sprint-p, s132, contract]

Sprint P S132 — the contract fixture ``009_contract_nda`` should land on
``order`` via the pre-LLM attachment-signal early-return when the Sprint P
default (SKLEARN_FIRST) is in play. Exercises the full stack
(EmailSourceAdapter → IntakePackageSink → ClassifierService →
StateRepository) on real Postgres.

Separately, the body-only fixture ``013_inquiry_pricing`` should land on
``inquiry`` via the LLM fallback — proving body_only cohort coverage
works end-to-end.
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

# Load OPENAI_API_KEY + AZURE_DI_* from the repo's .env for the LLM fallback
# path. CI sets these via workflow env so load_dotenv is a no-op there.
load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)

from aiflow.api.deps import get_pool  # noqa: E402
from aiflow.core.config import UC3AttachmentIntentSettings  # noqa: E402
from aiflow.models.backends.litellm_backend import LiteLLMBackend  # noqa: E402
from aiflow.models.client import ModelClient  # noqa: E402
from aiflow.services.classifier.service import (  # noqa: E402
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
)
from aiflow.services.email_connector.orchestrator import (  # noqa: E402
    WORKFLOW_NAME,
    scan_and_classify,
)
from aiflow.sources import EmailSourceAdapter, IntakePackageSink  # noqa: E402
from aiflow.sources.email_adapter import ImapBackendProtocol  # noqa: E402
from aiflow.state.repositories.intake import IntakeRepository  # noqa: E402
from aiflow.state.repository import StateRepository  # noqa: E402

pytestmark = pytest.mark.asyncio

REPO_ROOT = Path(__file__).resolve().parents[4]
INTENT_SCHEMA_PATH = (
    REPO_ROOT / "skills" / "email_intent_processor" / "schemas" / "v1" / "intents.json"
)
FIXTURES = REPO_ROOT / "data" / "fixtures" / "emails_sprint_o"

DATABASE_URL = os.getenv(
    "AIFLOW_DATABASE__URL",
    "postgresql+asyncpg://aiflow:aiflow_dev_password@localhost:5433/aiflow_dev",
)


def _schema_labels() -> list[dict]:
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


class _SingleBackend(ImapBackendProtocol):
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


async def _cleanup(pool: asyncpg.Pool, engine, tenant_id: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            sa_text(
                """DELETE FROM cost_records WHERE workflow_run_id IN (
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


async def _run_fixture(fixture_id: str, tmp_path: Path) -> tuple[str, str, str]:
    """Run one Sprint O fixture through scan_and_classify on real PG with
    the Sprint P defaults (SKLEARN_FIRST + attachment-signal early-return).
    Returns (predicted_label, method, tenant_id)."""
    tenant_id = f"s132-{uuid4().hex[:8]}"
    raw = (FIXTURES / f"{fixture_id}.eml").read_bytes()
    backend = _SingleBackend(raw)
    adapter = EmailSourceAdapter(
        backend=backend, storage_root=tmp_path / tenant_id, tenant_id=tenant_id
    )

    pool = await get_pool()
    intake_repo = IntakeRepository(pool)
    sink = IntakePackageSink(repo=intake_repo)

    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    state_repo = StateRepository(session_factory)

    backend_client = ModelClient(
        generation_backend=LiteLLMBackend(default_model="openai/gpt-4o-mini")
    )
    classifier = ClassifierService(
        config=ClassifierConfig(
            strategy=ClassificationStrategy.SKLEARN_FIRST, confidence_threshold=0.6
        ),
        models_client=backend_client,
    )
    await classifier.start()

    settings_on = UC3AttachmentIntentSettings(
        enabled=True, total_budget_seconds=60.0, classifier_strategy="sklearn_first"
    )

    try:
        results = await scan_and_classify(
            adapter,
            sink,
            classifier,
            state_repo,
            tenant_id=tenant_id,
            max_items=1,
            schema_labels=_schema_labels(),
            attachment_intent_settings=settings_on,
        )
    finally:
        await classifier.stop()
        await _cleanup(pool, engine, tenant_id)
        await engine.dispose()

    assert len(results) == 1, f"expected 1 classification, got {results}"
    _pkg, classification = results[0]
    return classification.label, classification.method, tenant_id


async def test_contract_nda_fixture_resolves_to_order(tmp_path: Path) -> None:
    """S132 contract-fix target — 009_contract_nda should land on ``order``
    via the pre-LLM attachment-signal early-return, not on ``feedback`` or
    ``internal`` (both the keyword-only and LLM-fallback failure modes)."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — S132 integration needs the LLM fallback path")

    label, method, _ = await _run_fixture("009_contract_nda", tmp_path)
    assert label == "order", (
        f"009_contract_nda must resolve to 'order' via the attachment-signal "
        f"early-return, got {label!r} via {method!r}"
    )
    assert "attachment" in method, f"expected attachment-path method, got {method!r}"


async def test_body_only_inquiry_fixture_resolves_via_llm(tmp_path: Path) -> None:
    """S132 body_only cohort coverage — 013_inquiry_pricing (no attachment)
    should land on ``inquiry`` via the LLM fallback under SKLEARN_FIRST."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — body-only fixture needs LLM fallback")

    label, method, _ = await _run_fixture("013_inquiry_pricing", tmp_path)
    assert label == "inquiry", (
        f"013_inquiry_pricing must resolve to 'inquiry' via LLM fallback, "
        f"got {label!r} via {method!r}"
    )
