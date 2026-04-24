"""
@test_registry:
    suite: services-unit
    component: services.classifier.service (S132 strategy + early-return)
    covers:
        - src/aiflow/services/classifier/service.py (_keywords_first, _attachment_signal_is_strong)
        - src/aiflow/core/config.py (UC3AttachmentIntentSettings.classifier_strategy)
    phase: sprint-p-s132
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [classifier, attachment, uc3, sprint-p, s132, early-return]

Sprint P S132 — ``_keywords_first`` short-circuits the LLM fallback when
attachment signals carry a strong EXTRACT hint, restoring Sprint O
behaviour on contract fixtures (009/011/012) that the LLM otherwise
mis-labels as ``internal``. Also covers the new
``UC3AttachmentIntentSettings.classifier_strategy`` knob.
"""

from __future__ import annotations

from typing import Any

import pytest

from aiflow.core.config import UC3AttachmentIntentSettings
from aiflow.services.classifier.service import (
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
    _attachment_signal_is_strong,
)

_SCHEMA = [
    {"id": "invoice_received", "display_name": "Invoice", "keywords": ["szamla"]},
    {"id": "order", "display_name": "Order", "keywords": ["szerzodes"]},
    {"id": "internal", "display_name": "Internal", "keywords": ["internal"]},
]


class _RecordingClient:
    def __init__(self) -> None:
        self.generate_calls = 0

    async def generate(self, *, messages, model, temperature, max_tokens):
        self.generate_calls += 1

        class _Out:
            class _Output:
                text = (
                    '{"label": "internal", "confidence": 0.9, '
                    '"reasoning": "wrong", "sub_label": null}'
                )

            output = _Output()

        return _Out()


class TestSettingsKnob:
    def test_default_is_sklearn_first(self) -> None:
        s = UC3AttachmentIntentSettings()
        assert s.classifier_strategy == "sklearn_first"

    def test_env_override(self, monkeypatch) -> None:
        monkeypatch.setenv("AIFLOW_UC3_ATTACHMENT_INTENT__CLASSIFIER_STRATEGY", "sklearn_only")
        s = UC3AttachmentIntentSettings()
        assert s.classifier_strategy == "sklearn_only"


class TestAttachmentSignalStrong:
    def test_empty_context_not_strong(self) -> None:
        assert _attachment_signal_is_strong(None) is False
        assert _attachment_signal_is_strong({}) is False
        assert _attachment_signal_is_strong({"attachment_features": {}}) is False

    def test_invoice_number_is_strong(self) -> None:
        ctx: dict[str, Any] = {"attachment_features": {"invoice_number_detected": True}}
        assert _attachment_signal_is_strong(ctx) is True

    def test_total_value_is_strong(self) -> None:
        ctx: dict[str, Any] = {"attachment_features": {"total_value_detected": True}}
        assert _attachment_signal_is_strong(ctx) is True

    def test_contract_bucket_is_strong(self) -> None:
        ctx: dict[str, Any] = {
            "attachment_features": {"keyword_buckets": {"contract": 2}},
        }
        assert _attachment_signal_is_strong(ctx) is True

    def test_other_buckets_not_strong(self) -> None:
        ctx: dict[str, Any] = {
            "attachment_features": {"keyword_buckets": {"support": 5, "report": 3}},
        }
        assert _attachment_signal_is_strong(ctx) is False


@pytest.mark.asyncio
class TestKeywordsFirstEarlyReturn:
    """Low-confidence keyword + strong attachment signal → skip LLM."""

    async def _svc(self, client: _RecordingClient) -> ClassifierService:
        svc = ClassifierService(
            config=ClassifierConfig(
                strategy=ClassificationStrategy.SKLEARN_FIRST,
                confidence_threshold=0.6,
            ),
            models_client=client,
        )
        await svc.start()
        return svc

    async def test_early_return_on_strong_attachment_signal(self) -> None:
        rec = _RecordingClient()
        svc = await self._svc(rec)
        try:
            out = await svc.classify(
                text="contract attached please sign",
                schema_labels=_SCHEMA,
                context={
                    "attachment_features": {
                        "invoice_number_detected": False,
                        "total_value_detected": False,
                        "keyword_buckets": {"contract": 3},
                    }
                },
            )
        finally:
            await svc.stop()

        # LLM must NOT be called.
        assert rec.generate_calls == 0
        # The signal-aligned EXTRACT label wins via the post-process boost.
        assert out.label == "order"
        assert "attachment_signal" in out.method or "attachment_rule" in out.method

    async def test_llm_fallback_still_runs_without_attachment_signal(self) -> None:
        rec = _RecordingClient()
        svc = await self._svc(rec)
        try:
            out = await svc.classify(
                text="hello please tell me more about your service",
                schema_labels=_SCHEMA,
                context=None,
            )
        finally:
            await svc.stop()

        # Keyword score low → LLM fallback exercised.
        assert rec.generate_calls == 1
        assert "hybrid" in out.method or out.method == "llm"

    async def test_attachment_signal_with_weak_bucket_still_falls_to_llm(self) -> None:
        rec = _RecordingClient()
        svc = await self._svc(rec)
        try:
            await svc.classify(
                text="random email no keywords",
                schema_labels=_SCHEMA,
                context={
                    "attachment_features": {
                        "keyword_buckets": {"support": 7},  # not contract
                    }
                },
            )
        finally:
            await svc.stop()
        assert rec.generate_calls == 1
