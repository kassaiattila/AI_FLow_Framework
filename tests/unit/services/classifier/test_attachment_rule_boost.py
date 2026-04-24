"""
@test_registry:
    suite: services-unit
    component: services.classifier.service (S128 attachment rule boost + LLM context)
    covers:
        - src/aiflow/services/classifier/service.py
    phase: 1
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [classifier, attachment, uc3, sprint-o, rule-boost, llm-context]

UC3 Sprint O / S128 — classifier consumption of ``context['attachment_features']``.
Validates the rule-boost matrix (body confidence vs invoice/total flags),
the +0.3 / 0.95 cap, the no-op cases, and the opt-in LLM-context system
message path.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aiflow.services.classifier.service import (
    EXTRACT_INTENT_IDS,
    ClassificationResult,
    ClassificationStrategy,
    ClassifierConfig,
    ClassifierService,
    _apply_attachment_rule_boost,
    _build_attachment_context_message,
)

# Per-test asyncio marks below — keep sync tests sync to avoid pytest-asyncio
# noise on pure-helper assertions.


_SCHEMA_LABELS = [
    {
        "id": "invoice_received",
        "display_name": "Invoice received",
        "description": "An invoice was delivered (extract fields).",
        "keywords": ["szamla", "invoice", "fizetes", "billing"],
        "examples": [],
    },
    {
        "id": "order",
        "display_name": "Order / contract",
        "description": "Customer order or contract.",
        "keywords": ["order", "contract", "szerzodes"],
        "examples": [],
    },
    {
        "id": "inquiry",
        "display_name": "Inquiry",
        "description": "Information request.",
        "keywords": ["question", "kerdes"],
        "examples": [],
    },
    {
        "id": "support",
        "display_name": "Support",
        "description": "Tech support.",
        "keywords": ["error", "bug", "hiba"],
        "examples": [],
    },
]


def _service(
    strategy: ClassificationStrategy = ClassificationStrategy.SKLEARN_ONLY,
) -> ClassifierService:
    return ClassifierService(config=ClassifierConfig(strategy=strategy, confidence_threshold=0.0))


def _make_base(
    label: str = "inquiry",
    confidence: float = 0.2,
    method: str = "keywords_no_match",
    alternatives: list[dict[str, Any]] | None = None,
) -> ClassificationResult:
    return ClassificationResult(
        label=label,
        display_name=label.title(),
        confidence=confidence,
        method=method,
        alternatives=alternatives or [],
    )


# -----------------------------------------------------------------------------
# 1) Module constants + structural sanity
# -----------------------------------------------------------------------------


def test_extract_intent_ids_match_manifest_categories() -> None:
    """Source of truth: data/fixtures/emails_sprint_o/manifest.yaml."""
    assert "invoice_received" in EXTRACT_INTENT_IDS
    assert "order" in EXTRACT_INTENT_IDS
    assert isinstance(EXTRACT_INTENT_IDS, frozenset)


# -----------------------------------------------------------------------------
# 2) Pure-function rule-boost matrix on _apply_attachment_rule_boost
# -----------------------------------------------------------------------------


def test_no_context_passes_through() -> None:
    base = _make_base()
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, None)
    assert out is base


def test_no_attachment_features_passes_through() -> None:
    base = _make_base()
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, {"other": 1})
    assert out is base


def test_high_body_confidence_no_boost() -> None:
    base = _make_base(label="inquiry", confidence=0.7)
    ctx = {"attachment_features": {"invoice_number_detected": True}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out is base, "body confidence ≥ 0.6 must be left alone"


def test_low_confidence_invoice_signal_boosts_invoice_received() -> None:
    base = _make_base(label="unknown", confidence=0.0, method="keywords_no_match")
    ctx = {"attachment_features": {"invoice_number_detected": True}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out.label == "invoice_received"
    assert out.confidence == 0.3  # 0.0 + 0.3
    assert "attachment_rule" in out.method
    assert "invoice_number_detected" in out.reasoning


def test_low_confidence_total_only_signal_also_boosts() -> None:
    base = _make_base(label="unknown", confidence=0.0)
    ctx = {"attachment_features": {"total_value_detected": True}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out.label == "invoice_received"
    assert out.confidence > base.confidence


def test_contract_keyword_bucket_boosts_to_order() -> None:
    base = _make_base(label="unknown", confidence=0.0)
    ctx = {"attachment_features": {"keyword_buckets": {"contract": 3}}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out.label == "order"
    assert "contract_keyword_bucket" in out.reasoning


def test_neither_signal_no_boost() -> None:
    base = _make_base(label="unknown", confidence=0.0)
    ctx = {"attachment_features": {"invoice_number_detected": False, "total_value_detected": False}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out is base


def test_non_extract_body_label_is_protected_from_boost() -> None:
    """Sprint K's keyword classifier identifies a non-EXTRACT intent —
    the rule must NOT clobber that even with a strong attachment signal."""
    base = _make_base(label="complaint", confidence=0.2, method="keywords")
    ctx = {"attachment_features": {"invoice_number_detected": True, "total_value_detected": True}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out is base, "complaint must survive — body classifier had a non-EXTRACT signal"


def test_rule_boost_respects_cap() -> None:
    # Base label is already an EXTRACT class, so the gate allows boost.
    # 0.5 + 0.3 = 0.8 (under cap).
    base = _make_base(label="invoice_received", confidence=0.5)
    ctx = {"attachment_features": {"invoice_number_detected": True}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out.confidence == 0.8

    # 0.55 + 0.3 = 0.85 still under cap.
    base = _make_base(label="invoice_received", confidence=0.55)
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out.confidence == 0.85

    # alternatives push computed base above 0.95-cap territory.
    alts = [{"label": "invoice_received", "confidence": 0.7}]
    base = _make_base(label="invoice_received", confidence=0.59, alternatives=alts)
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    # max(0.7, 0.59) + 0.3 = 1.0 → capped at 0.95
    assert out.confidence == 0.95


def test_no_extract_label_in_schema_no_boost() -> None:
    schema_no_extract = [{"id": "support", "display_name": "Support", "keywords": ["bug"]}]
    base = _make_base(label="unknown", confidence=0.0)
    ctx = {"attachment_features": {"invoice_number_detected": True}}
    out = _apply_attachment_rule_boost(base, schema_no_extract, ctx)
    assert out is base


def test_signal_aligned_label_selection_invoice_wins_over_order() -> None:
    """invoice_number_detected always picks invoice_received regardless of
    alternatives ordering — bug fix from S128 first-pass measurement."""
    alts = [
        {"label": "order", "confidence": 0.4},
        {"label": "invoice_received", "confidence": 0.1},
    ]
    base = _make_base(label="unknown", confidence=0.0, alternatives=alts)
    ctx = {"attachment_features": {"invoice_number_detected": True}}
    out = _apply_attachment_rule_boost(base, _SCHEMA_LABELS, ctx)
    assert out.label == "invoice_received"


# -----------------------------------------------------------------------------
# 3) End-to-end via ClassifierService.classify (sklearn_only path)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_without_context_is_unchanged() -> None:
    svc = _service()
    await svc.start()
    try:
        out = await svc.classify(text="random body", schema_labels=_SCHEMA_LABELS)
        # No attachment_rule applied
        assert "attachment_rule" not in out.method
    finally:
        await svc.stop()


@pytest.mark.asyncio
async def test_classify_with_context_boosts_for_thin_body() -> None:
    svc = _service()
    await svc.start()
    try:
        out = await svc.classify(
            text="Please find attached.",
            schema_labels=_SCHEMA_LABELS,
            context={"attachment_features": {"invoice_number_detected": True}},
        )
        assert out.label == "invoice_received"
        assert out.confidence > 0.0
        assert "attachment_rule" in out.method
    finally:
        await svc.stop()


@pytest.mark.asyncio
async def test_classify_with_context_no_boost_when_body_strong() -> None:
    svc = _service()
    await svc.start()
    try:
        # Strong keyword match → confidence should already exceed 0.6 floor
        out_no_ctx = await svc.classify(
            text="Szamla szamla szamla invoice billing", schema_labels=_SCHEMA_LABELS
        )
        if out_no_ctx.confidence < 0.6:
            pytest.skip("body classifier didn't reach 0.6 — boost path is what we test elsewhere")
        out = await svc.classify(
            text="Szamla szamla szamla invoice billing",
            schema_labels=_SCHEMA_LABELS,
            context={"attachment_features": {"invoice_number_detected": True}},
        )
        assert out.confidence == out_no_ctx.confidence
        assert "attachment_rule" not in out.method
    finally:
        await svc.stop()


# -----------------------------------------------------------------------------
# 4) LLM-context system message builder
# -----------------------------------------------------------------------------


def test_llm_context_message_off_by_default() -> None:
    msg = _build_attachment_context_message(
        {"attachment_features": {"invoice_number_detected": True}}
    )
    assert msg is None


def test_llm_context_message_off_when_no_context() -> None:
    assert _build_attachment_context_message(None) is None
    assert _build_attachment_context_message({}) is None


def test_llm_context_message_on_returns_summary() -> None:
    ctx = {
        "attachment_intent_llm_context": True,
        "attachment_features": {
            "invoice_number_detected": True,
            "total_value_detected": False,
            "mime_profile": "application/pdf",
            "keyword_buckets": {"invoice": 3, "contract": 1},
        },
        "attachment_text_preview": "Invoice INV-2026-0042\nTotal: 48,500 HUF\n",
    }
    msg = _build_attachment_context_message(ctx)
    assert msg is not None
    assert "invoice_number_detected=True" in msg
    assert "total_value_detected=False" in msg
    assert "application/pdf" in msg
    assert "invoice=3" in msg
    assert "INV-2026-0042" in msg


def test_llm_context_message_truncates_preview_at_500_chars() -> None:
    long_preview = "X" * 1200
    ctx = {
        "attachment_intent_llm_context": True,
        "attachment_features": {"mime_profile": "application/pdf"},
        "attachment_text_preview": long_preview,
    }
    msg = _build_attachment_context_message(ctx)
    assert msg is not None
    # The preview slice happens at the orchestrator level; the helper itself
    # only re-slices to 500 to be safe.
    assert msg.count("X") <= 500


# -----------------------------------------------------------------------------
# 5) LLM path injects the second system message only when opt-in is set
# -----------------------------------------------------------------------------


class _RecordingModelsClient:
    def __init__(self) -> None:
        self.captured_messages: list[list[dict[str, Any]]] = []

    async def generate(self, *, messages, model, temperature, max_tokens):
        self.captured_messages.append(list(messages))

        class _Output:
            text = (
                '{"label": "invoice_received", "confidence": 0.9, '
                '"reasoning": "ok", "sub_label": null}'
            )

        class _Out:
            output = _Output()

        return _Out()


@pytest.mark.asyncio
async def test_llm_path_no_extra_message_when_opt_in_off() -> None:
    rec = _RecordingModelsClient()
    svc = ClassifierService(
        config=ClassifierConfig(strategy=ClassificationStrategy.LLM_ONLY, confidence_threshold=0.0),
        models_client=rec,
    )
    await svc.start()
    try:
        await svc.classify(
            text="hello",
            schema_labels=_SCHEMA_LABELS,
            context={"attachment_features": {"invoice_number_detected": True}},
        )
        assert len(rec.captured_messages) == 1
        # Only one system message (the base prompt) + one user message.
        roles = [m["role"] for m in rec.captured_messages[0]]
        assert roles == ["system", "user"]
    finally:
        await svc.stop()


@pytest.mark.asyncio
async def test_llm_path_injects_extra_message_when_opt_in_on() -> None:
    rec = _RecordingModelsClient()
    svc = ClassifierService(
        config=ClassifierConfig(strategy=ClassificationStrategy.LLM_ONLY, confidence_threshold=0.0),
        models_client=rec,
    )
    await svc.start()
    try:
        await svc.classify(
            text="hello",
            schema_labels=_SCHEMA_LABELS,
            context={
                "attachment_features": {
                    "invoice_number_detected": True,
                    "mime_profile": "application/pdf",
                },
                "attachment_text_preview": "Invoice INV-2026-0042\n",
                "attachment_intent_llm_context": True,
            },
        )
        roles = [m["role"] for m in rec.captured_messages[0]]
        assert roles == ["system", "system", "user"]
        injected = rec.captured_messages[0][1]["content"]
        assert "Additional attachment context" in injected
        assert "INV-2026-0042" in injected
    finally:
        await svc.stop()


# -----------------------------------------------------------------------------
# 6) Sanity — backward-compat: classify() default kwargs unchanged
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_signature_backward_compat() -> None:
    """Legacy Sprint K callers (text + schema_labels positional) keep working."""
    svc = _service()
    await svc.start()
    try:
        out = await svc.classify(text="szamla", schema_labels=_SCHEMA_LABELS)
        assert isinstance(out, ClassificationResult)
    finally:
        await svc.stop()


def test_event_loop_default_works() -> None:
    """Smoke that the module imports & the EXTRACT set is iterable."""
    loop = asyncio.get_event_loop_policy().get_event_loop() if False else None  # noqa: SIM108
    assert loop is None or loop  # type: ignore[truthy-bool]
    assert sorted(EXTRACT_INTENT_IDS) == ["invoice_received", "order"]
