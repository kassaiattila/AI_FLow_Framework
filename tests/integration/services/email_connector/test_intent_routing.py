"""
@test_registry:
    suite: integration-services
    component: services.email_connector.orchestrator
    covers:
        - src/aiflow/services/email_connector/orchestrator.py
        - src/aiflow/policy/intent_routing.py
        - src/aiflow/services/classifier/service.py
    phase: 1d
    priority: critical
    estimated_duration_ms: 7000
    requires_services: [postgres]
    tags: [integration, email_connector, intent_routing, uc3, sprint_k]

UC3 Sprint K S107 — intent routing end-to-end against real PostgreSQL.
Four fixture emails (invoice / support / spam / unknown) → EmailSourceAdapter
(fake IMAP) → IntakePackageSink → ClassifierService (sklearn_only) →
IntentRoutingPolicy.decide → StateRepository.workflow_runs rows.

Asserts:
    1. ``output_data.routing_action`` / ``routing_target`` persisted correctly
       for all four intents (including default fallback for ``unknown``).
    2. Four ``email_connector.scan_and_classify.routed`` structlog events with
       matching action/target payload.
    3. No ``prompt_fetched`` event when ``prompt_manager`` is not supplied.

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
from aiflow.policy.intent_routing import (
    IntentAction,
    IntentRoutingPolicy,
    IntentRoutingRule,
)
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
    {
        "id": "spam",
        "display_name": "Spam / Promotional",
        "description": "Unsolicited promotional or giveaway emails.",
        "keywords": ["win", "prize", "lottery", "unsubscribe", "offer"],
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
    """Build an RFC822 email with one tiny text attachment (see S106 note)."""
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


async def test_scan_and_classify_applies_intent_routing_policy(tmp_path: Path) -> None:
    tenant_id = f"tenant-s107-{uuid4().hex[:8]}"
    storage_root = tmp_path / "email_storage"

    # Four emails — each deterministically triggers a different routing outcome.
    inbox = [
        (
            301,
            _build_email(
                subject="Invoice question",
                sender="acc@example.com",
                body="I received an invoice and need help with the billing and payment.",
            ),
        ),
        (
            302,
            _build_email(
                subject="Bug report",
                sender="dev@example.com",
                body="There is a bug causing an error, please support with this hiba.",
            ),
        ),
        (
            303,
            _build_email(
                subject="You win a prize!",
                sender="promo@example.com",
                body="Win a lottery prize! Click to unsubscribe or see our offer.",
            ),
        ),
        (
            304,
            _build_email(
                subject="Hello",
                sender="friend@example.com",
                body="Just saying hi, the weather is nice today.",
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

    # Policy: three explicit rules + a MANUAL_REVIEW default for "unknown".
    # ``min_confidence=0.0`` keeps the sklearn keyword scores from gating the
    # rule firing — the test exercises the label→action mapping, not score
    # tuning (that is a separate responsibility of ClassifierConfig).
    policy = IntentRoutingPolicy(
        tenant_id=tenant_id,
        default_action=IntentAction.MANUAL_REVIEW,
        default_target="inbox",
        rules=[
            IntentRoutingRule(
                intent_label="invoice_question",
                action=IntentAction.EXTRACT,
                target="invoice_pipeline",
                min_confidence=0.0,
            ),
            IntentRoutingRule(
                intent_label="support_request",
                action=IntentAction.NOTIFY_DEPT,
                target="helpdesk",
                min_confidence=0.0,
            ),
            IntentRoutingRule(
                intent_label="spam",
                action=IntentAction.ARCHIVE,
                target="",
                min_confidence=0.0,
            ),
        ],
    )

    expected_by_label: dict[str, tuple[str, str]] = {
        "invoice_question": (IntentAction.EXTRACT.value, "invoice_pipeline"),
        "support_request": (IntentAction.NOTIFY_DEPT.value, "helpdesk"),
        "spam": (IntentAction.ARCHIVE.value, ""),
        "unknown": (IntentAction.MANUAL_REVIEW.value, "inbox"),
    }

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
                routing_policy=policy,
            )

        # --- Return value -----------------------------------------------
        assert len(results) == 4, f"expected 4 results, got {results}"
        labels_seen = {r.label for _, r in results}
        assert labels_seen == set(expected_by_label), (
            f"expected labels {set(expected_by_label)}, got {labels_seen}"
        )

        # --- workflow_runs rows with routing payload --------------------
        async with engine.begin() as conn:
            run_rows = (
                await conn.execute(
                    sa_text(
                        """SELECT id, status, output_data
                           FROM workflow_runs
                           WHERE workflow_name = :wf AND skill_name = :sk
                             AND (output_data->>'tenant_id') = :tid
                           ORDER BY created_at"""
                    ),
                    {"wf": WORKFLOW_NAME, "sk": SKILL_NAME, "tid": tenant_id},
                )
            ).all()

        assert len(run_rows) == 4, f"expected 4 workflow_runs rows, got {len(run_rows)}"
        action_by_label: dict[str, tuple[str, str]] = {}
        for row in run_rows:
            assert row.status == "completed"
            od = row.output_data
            assert "routing_action" in od, f"routing_action missing in {od}"
            assert "routing_target" in od
            assert "prompt_version" not in od, (
                "prompt_version must be absent when no PromptManager was supplied"
            )
            action_by_label[od["label"]] = (od["routing_action"], od["routing_target"])

        for label, expected in expected_by_label.items():
            assert action_by_label[label] == expected, (
                f"{label} → expected {expected}, got {action_by_label[label]}"
            )

        # --- Observability: routed events -------------------------------
        routed_events = [
            e for e in events if e.get("event") == "email_connector.scan_and_classify.routed"
        ]
        assert len(routed_events) == 4, (
            f"expected 4 routed events, got {len(routed_events)}: "
            f"{[e.get('event') for e in events]}"
        )
        for ev in routed_events:
            assert ev["tenant_id"] == tenant_id
            assert "package_id" in ev
            assert "workflow_run_id" in ev
            expected_action, expected_target = expected_by_label[ev["label"]]
            assert ev["action"] == expected_action
            assert ev["target"] == expected_target

        # --- No prompt fetch attempted when no PromptManager supplied ---
        prompt_events = [
            e
            for e in events
            if str(e.get("event", "")).startswith("email_connector.scan_and_classify.prompt_")
        ]
        assert prompt_events == [], (
            f"expected no prompt_* events without PromptManager, got {prompt_events}"
        )

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
