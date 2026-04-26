"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.repository
    covers:
        - src/aiflow/services/document_recognizer/repository.py
    phase: v1.6.0
    priority: high
    estimated_duration_ms: 60
    requires_services: []
    tags: [unit, services, doc_recognizer, repository, sprint_v, sv_3]
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.contracts.doc_recognition import (
    DocExtractionResult,
    DocFieldValue,
    DocIntentDecision,
    DocTypeMatch,
)
from aiflow.services.document_recognizer.repository import DocRecognitionRepository


def _fake_pool_with_capture() -> tuple[MagicMock, dict]:
    """Return a MagicMock asyncpg.Pool whose acquire().execute capture is exposed."""
    captured: dict[str, list] = {"execute_args": []}

    fake_conn = MagicMock()
    fake_conn.execute = AsyncMock()
    fake_conn.fetch = AsyncMock(return_value=[])
    fake_conn.fetchrow = AsyncMock(return_value=None)

    async def fake_execute(*args, **kwargs):
        captured["execute_args"].append((args, kwargs))

    fake_conn.execute.side_effect = fake_execute

    fake_acquire_cm = MagicMock()
    fake_acquire_cm.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_acquire_cm.__aexit__ = AsyncMock(return_value=None)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=fake_acquire_cm)
    return pool, captured


class TestInsertRun:
    @pytest.mark.asyncio
    async def test_inserts_with_correct_payload(self):
        pool, captured = _fake_pool_with_capture()
        repo = DocRecognitionRepository(pool)

        match = DocTypeMatch(
            doc_type="hu_invoice",
            confidence=0.92,
            alternatives=[("pdf_contract", 0.05)],
        )
        extraction = DocExtractionResult(
            doc_type="hu_invoice",
            extracted_fields={
                "invoice_number": DocFieldValue(value="INV-1", confidence=0.95),
                "total_gross": DocFieldValue(value=12500, confidence=0.88),
            },
            cost_usd=0.0042,
            extraction_time_ms=245.3,
        )
        intent = DocIntentDecision(intent="process", reason="ok")

        run_id = await repo.insert_run(
            tenant_id="acme",
            match=match,
            extraction=extraction,
            intent=intent,
            filename_hint="szamla_001.pdf",
            classification_method="rule_engine",
            pii_redaction=False,
        )

        assert isinstance(run_id, uuid.UUID)
        assert len(captured["execute_args"]) == 1
        sql, args = captured["execute_args"][0][0][0], captured["execute_args"][0][0][1:]
        assert "INSERT INTO doc_recognition_runs" in sql
        # Positional args: (id, tenant_id, doc_type, confidence, alternatives, fields,
        #                   intent, intent_reason, cost, time, filename_hint, method, pii_redacted)
        assert args[1] == "acme"
        assert args[2] == "hu_invoice"
        assert args[3] == pytest.approx(0.92)
        # alternatives JSON
        alts = json.loads(args[4])
        assert alts == [{"doc_type": "pdf_contract", "confidence": 0.05}]
        # extracted_fields JSON
        fields = json.loads(args[5])
        assert fields["invoice_number"]["value"] == "INV-1"
        assert fields["total_gross"]["value"] == 12500
        # intent + cost + filename_hint + method + pii flag
        assert args[6] == "process"
        assert args[8] == pytest.approx(0.0042)
        assert args[10] == "szamla_001.pdf"
        assert args[11] == "rule_engine"
        assert args[12] is False

    @pytest.mark.asyncio
    async def test_pii_redaction_replaces_values(self):
        pool, captured = _fake_pool_with_capture()
        repo = DocRecognitionRepository(pool)

        match = DocTypeMatch(doc_type="hu_id_card", confidence=0.95)
        extraction = DocExtractionResult(
            doc_type="hu_id_card",
            extracted_fields={
                "id_number": DocFieldValue(value="123456AB", confidence=0.92),
                "full_name": DocFieldValue(value="Kiss Anna", confidence=0.95),
            },
        )
        intent = DocIntentDecision(intent="route_to_human", reason="PII")

        await repo.insert_run(
            tenant_id="acme",
            match=match,
            extraction=extraction,
            intent=intent,
            classification_method="rule_engine",
            pii_redaction=True,
        )

        args = captured["execute_args"][0][0][1:]
        fields = json.loads(args[5])
        # Values redacted; confidences preserved
        assert fields["id_number"]["value"] == "<redacted>"
        assert fields["id_number"]["confidence"] == pytest.approx(0.92)
        assert fields["full_name"]["value"] == "<redacted>"
        # pii_redacted flag persisted
        assert args[12] is True

    @pytest.mark.asyncio
    async def test_classification_method_passed_through(self):
        pool, captured = _fake_pool_with_capture()
        repo = DocRecognitionRepository(pool)

        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.5)
        extraction = DocExtractionResult(doc_type="hu_invoice")
        intent = DocIntentDecision(intent="route_to_human", reason="low conf")

        await repo.insert_run(
            tenant_id="acme",
            match=match,
            extraction=extraction,
            intent=intent,
            classification_method="llm_fallback",
            pii_redaction=False,
        )

        args = captured["execute_args"][0][0][1:]
        assert args[11] == "llm_fallback"

    @pytest.mark.asyncio
    async def test_returns_unique_uuids(self):
        pool, _ = _fake_pool_with_capture()
        repo = DocRecognitionRepository(pool)

        match = DocTypeMatch(doc_type="hu_invoice", confidence=0.9)
        extraction = DocExtractionResult(doc_type="hu_invoice")
        intent = DocIntentDecision(intent="process")

        ids = set()
        for _ in range(5):
            run_id = await repo.insert_run(
                tenant_id="acme",
                match=match,
                extraction=extraction,
                intent=intent,
                classification_method="rule_engine",
            )
            ids.add(run_id)
        assert len(ids) == 5
