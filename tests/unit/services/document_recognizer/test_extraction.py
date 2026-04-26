"""
@test_registry:
    suite: core-unit
    component: services.document_recognizer.extraction
    covers:
        - src/aiflow/services/document_recognizer/extraction.py
    phase: v1.7.0
    priority: critical
    estimated_duration_ms: 80
    requires_services: []
    tags: [unit, services, doc_recognizer, extraction, sprint_w, sw_1]
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiflow.contracts.doc_recognition import (
    DocTypeDescriptor,
    ExtractionConfig,
    FieldSpec,
    IntentRoutingConfig,
    RuleSpec,
    TypeClassifierConfig,
)
from aiflow.core.errors import CostGuardrailRefused
from aiflow.guardrails.cost_preflight import PreflightDecision
from aiflow.services.document_recognizer.classifier import ClassifierInput
from aiflow.services.document_recognizer.extraction import (
    _extract_json_block,
    build_extract_fn,
)


def _hu_invoice_descriptor() -> DocTypeDescriptor:
    return DocTypeDescriptor(
        name="hu_invoice",
        display_name="HU Invoice",
        type_classifier=TypeClassifierConfig(
            rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"\bSzámla\b")]
        ),
        extraction=ExtractionConfig(
            workflow="invoice_extraction_chain",
            fields=[
                FieldSpec(name="invoice_number", type="string", required=True),
                FieldSpec(name="total_gross", type="money", required=True),
                FieldSpec(name="vendor_name", type="string", required=False),
            ],
        ),
        intent_routing=IntentRoutingConfig(default="process"),
    )


def _stub_prompt(model: str = "openai/gpt-4o-mini", max_tokens: int = 1024):
    """Stub PromptDefinition with `compile()` returning a list of message dicts."""
    pd = MagicMock()
    pd.config = SimpleNamespace(model=model, temperature=0.0, max_tokens=max_tokens)
    pd.compile = MagicMock(return_value=[{"role": "user", "content": "extract this"}])
    return pd


def _stub_workflow_executor(prompt_map: dict | None, workflow_steps: list | None = None):
    """Build a fake PromptWorkflowExecutor whose `resolve_for_skill` returns
    (workflow, prompt_map) or None when prompt_map is None."""
    fake_executor = MagicMock()

    if prompt_map is None:
        fake_executor.resolve_for_skill = MagicMock(return_value=None)
        return fake_executor

    workflow = MagicMock()
    if workflow_steps is None:
        # Default: one required step `extract` whose prompt is in prompt_map
        step = SimpleNamespace(
            id="extract",
            prompt_name="document-recognizer/extract",
            required=True,
            metadata={"cost_ceiling_usd": 0.05},
        )
        workflow.steps = [step]
    else:
        workflow.steps = workflow_steps

    fake_executor.resolve_for_skill = MagicMock(return_value=(workflow, prompt_map))
    return fake_executor


def _stub_generate_response(payload_dict: dict, cost_usd: float = 0.001):
    """Build a stub LLM response object matching ModelClient.generate's shape."""
    import json

    return SimpleNamespace(
        output=SimpleNamespace(text=json.dumps(payload_dict), structured=None),
        cost_usd=cost_usd,
        input_tokens=100,
        output_tokens=50,
    )


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------


class TestExtractJsonBlock:
    def test_clean_json(self):
        result = _extract_json_block('{"a": 1, "b": "hello"}')
        assert result == {"a": 1, "b": "hello"}

    def test_with_prose(self):
        result = _extract_json_block('Here is the result:\n{"a": 1}\nThanks!')
        assert result == {"a": 1}

    def test_with_code_fence(self):
        result = _extract_json_block('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_invalid_returns_none(self):
        assert _extract_json_block("no json here") is None
        assert _extract_json_block("") is None
        assert _extract_json_block("{not valid") is None

    def test_array_top_level_returns_none(self):
        # Helper expects an object; arrays return None
        assert _extract_json_block("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# build_extract_fn — workflow resolution
# ---------------------------------------------------------------------------


class TestExtractFnWorkflowResolution:
    @pytest.mark.asyncio
    async def test_unresolved_workflow_returns_empty_with_warning(self):
        """When PromptWorkflowExecutor.resolve_for_skill returns None
        (flag-off, descriptor missing, etc.), the extract_fn returns
        an empty result + warning."""
        executor = _stub_workflow_executor(prompt_map=None)
        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=AsyncMock(),
        )
        ctx = ClassifierInput(text="Számla 2026")
        result = await extract_fn(_hu_invoice_descriptor(), ctx, "tenant-1")

        assert result.extracted_fields == {}
        assert any("not resolved" in w for w in result.validation_warnings)
        assert result.cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_resolved_workflow_calls_generate(self):
        """When the workflow resolves to (workflow, prompt_map), the
        extract_fn calls generate_fn for each required step with a
        resolved prompt."""
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})
        gen = AsyncMock(
            return_value=_stub_generate_response(
                {"invoice_number": "INV-1", "total_gross": 12500},
                cost_usd=0.0042,
            )
        )

        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="Számla 2026"),
            "tenant-1",
        )

        gen.assert_called_once()
        assert result.extracted_fields["invoice_number"].value == "INV-1"
        assert result.extracted_fields["total_gross"].value == 12500
        assert result.cost_usd == pytest.approx(0.0042)
        assert result.extraction_time_ms >= 0.0

    @pytest.mark.asyncio
    async def test_optional_step_with_no_prompt_skipped(self):
        """An optional step (required=False) with no resolved prompt is
        skipped (no warning). Required steps with no prompt warn."""
        prompt = _stub_prompt()
        # 2 steps: one required (resolved), one optional (unresolved)
        steps = [
            SimpleNamespace(
                id="extract",
                prompt_name="ext",
                required=True,
                metadata=None,
            ),
            SimpleNamespace(
                id="validate",
                prompt_name="val",
                required=False,
                metadata=None,
            ),
        ]
        executor = _stub_workflow_executor(prompt_map={"extract": prompt}, workflow_steps=steps)
        gen = AsyncMock(return_value=_stub_generate_response({"invoice_number": "INV-1"}))

        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="Számla"),
            "tenant-1",
        )

        # Validate was skipped silently — no warning about missing prompt
        # because it was optional.
        assert all("validate" not in w for w in result.validation_warnings)


# ---------------------------------------------------------------------------
# build_extract_fn — cost preflight
# ---------------------------------------------------------------------------


class TestExtractFnCostPreflight:
    @pytest.mark.asyncio
    async def test_ceiling_refused_raises(self):
        """When cost_guardrail.check_step refuses, extract_fn raises
        CostGuardrailRefused. The caller (orchestrator) propagates."""
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})

        guardrail = MagicMock()
        guardrail.check_step = MagicMock(
            return_value=PreflightDecision(
                allowed=False,
                projected_usd=0.10,
                remaining_usd=0.05,
                reason="step_over_ceiling",
                period="daily",
                dry_run=False,
            )
        )

        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=guardrail,
            generate_fn=AsyncMock(),
        )

        with pytest.raises(CostGuardrailRefused):
            await extract_fn(
                _hu_invoice_descriptor(),
                ClassifierInput(text="Számla"),
                "tenant-1",
            )

    @pytest.mark.asyncio
    async def test_ceiling_allowed_proceeds(self):
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})

        guardrail = MagicMock()
        guardrail.check_step = MagicMock(
            return_value=PreflightDecision(
                allowed=True,
                projected_usd=0.001,
                remaining_usd=0.05,
                reason="step_under_ceiling",
                period="daily",
                dry_run=False,
            )
        )

        gen = AsyncMock(return_value=_stub_generate_response({"invoice_number": "INV-1"}))
        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=guardrail,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="Számla"),
            "tenant-1",
        )

        guardrail.check_step.assert_called_once()
        gen.assert_called_once()
        assert result.extracted_fields["invoice_number"].value == "INV-1"


# ---------------------------------------------------------------------------
# build_extract_fn — field mapping & nested payloads
# ---------------------------------------------------------------------------


class TestExtractFnFieldMapping:
    @pytest.mark.asyncio
    async def test_nested_header_payload(self):
        """LLM returns ``{"header": {"invoice_number": "..."}}``; the helper
        descends one level to find the field."""
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})
        gen = AsyncMock(
            return_value=_stub_generate_response(
                {"header": {"invoice_number": "INV-1", "total_gross": 12500}}
            )
        )
        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="Számla"),
            "tenant-1",
        )
        assert result.extracted_fields["invoice_number"].value == "INV-1"
        assert result.extracted_fields["total_gross"].value == 12500

    @pytest.mark.asyncio
    async def test_per_field_confidence_used_when_present(self):
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})
        gen = AsyncMock(
            return_value=_stub_generate_response(
                {
                    "invoice_number": "INV-1",
                    "per_field_confidence": {"invoice_number": 0.95},
                }
            )
        )
        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="Számla"),
            "tenant-1",
        )
        assert result.extracted_fields["invoice_number"].confidence == pytest.approx(0.95)

    @pytest.mark.asyncio
    async def test_default_confidence_when_missing(self):
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})
        gen = AsyncMock(return_value=_stub_generate_response({"invoice_number": "INV-1"}))
        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="Számla"),
            "tenant-1",
        )
        # Default 0.7 fallback
        assert result.extracted_fields["invoice_number"].confidence == pytest.approx(0.7)

    @pytest.mark.asyncio
    async def test_invalid_json_response_warns(self):
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})
        gen = AsyncMock(
            return_value=SimpleNamespace(
                output=SimpleNamespace(text="not json", structured=None),
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
            )
        )
        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="x"),
            "tenant-1",
        )
        assert any("not valid JSON" in w for w in result.validation_warnings)
        assert result.extracted_fields == {}

    @pytest.mark.asyncio
    async def test_llm_call_failure_warns_no_crash(self):
        prompt = _stub_prompt()
        executor = _stub_workflow_executor(prompt_map={"extract": prompt})
        gen = AsyncMock(side_effect=RuntimeError("API down"))

        extract_fn = build_extract_fn(
            workflow_executor=executor,
            cost_guardrail=None,
            generate_fn=gen,
        )
        result = await extract_fn(
            _hu_invoice_descriptor(),
            ClassifierInput(text="x"),
            "tenant-1",
        )
        # Result returned (no exception) with warnings
        assert any("LLM call failed" in w for w in result.validation_warnings)
        assert result.extracted_fields == {}


# ---------------------------------------------------------------------------
# Orchestrator integration with extract_fn
# ---------------------------------------------------------------------------


class TestOrchestratorWithExtractFn:
    @pytest.mark.asyncio
    async def test_orchestrator_uses_extract_fn(self):
        """When orchestrator is constructed with extract_fn, run() calls it
        and the resulting extracted_fields populate."""
        import tempfile

        from aiflow.contracts.doc_recognition import DocExtractionResult, DocFieldValue
        from aiflow.services.document_recognizer.orchestrator import (
            DocumentRecognizerOrchestrator,
        )
        from aiflow.services.document_recognizer.registry import DocTypeRegistry

        descriptor = _hu_invoice_descriptor()
        reg = DocTypeRegistry(bootstrap_dir=tempfile.mkdtemp())
        reg.register_doctype(descriptor)

        async def fake_extract(d, ctx, tenant):
            return DocExtractionResult(
                doc_type=d.name,
                extracted_fields={
                    "invoice_number": DocFieldValue(value="INV-1", confidence=0.9),
                    "total_gross": DocFieldValue(value=12500, confidence=0.85),
                },
                cost_usd=0.001,
            )

        orch = DocumentRecognizerOrchestrator(registry=reg, extract_fn=fake_extract)
        result = await orch.run(ClassifierInput(text="Számla 2026"), tenant_id="t1")
        assert result is not None
        match, extraction, intent = result
        assert extraction.extracted_fields["invoice_number"].value == "INV-1"
        assert intent.intent == "process"

    @pytest.mark.asyncio
    async def test_orchestrator_runs_validators_on_extract_result(self):
        """Field validators (apply_validators) run on extract_fn output."""
        import tempfile

        from aiflow.contracts.doc_recognition import DocExtractionResult, DocFieldValue
        from aiflow.services.document_recognizer.orchestrator import (
            DocumentRecognizerOrchestrator,
        )
        from aiflow.services.document_recognizer.registry import DocTypeRegistry

        # Descriptor with validators
        descriptor = DocTypeDescriptor(
            name="hu_invoice",
            display_name="X",
            type_classifier=TypeClassifierConfig(
                rules=[RuleSpec(kind="regex", weight=1.0, pattern=r"\bSzámla\b")]
            ),
            extraction=ExtractionConfig(
                workflow="invoice_extraction_chain",
                fields=[
                    FieldSpec(
                        name="invoice_number",
                        type="string",
                        required=True,
                        validators=["non_empty", "regex:^INV-\\d{4}$"],
                    ),
                ],
            ),
            intent_routing=IntentRoutingConfig(default="process"),
        )
        reg = DocTypeRegistry(bootstrap_dir=tempfile.mkdtemp())
        reg.register_doctype(descriptor)

        async def fake_extract(d, ctx, tenant):
            return DocExtractionResult(
                doc_type=d.name,
                extracted_fields={
                    "invoice_number": DocFieldValue(value="bad-format", confidence=0.9),
                },
            )

        orch = DocumentRecognizerOrchestrator(registry=reg, extract_fn=fake_extract)
        result = await orch.run(ClassifierInput(text="Számla 2026"), tenant_id="t1")
        assert result is not None
        _, extraction, _ = result
        # The descriptor's regex rejects "bad-format"; validator warning
        # surfaces on the merged validation_warnings list
        assert any("invoice_number" in w and "regex" in w for w in extraction.validation_warnings)

    @pytest.mark.asyncio
    async def test_no_extract_fn_preserves_sv2_placeholder(self):
        """Backward compat: orchestrator without extract_fn returns the SV-2
        empty placeholder + warning."""
        import tempfile

        from aiflow.services.document_recognizer.orchestrator import (
            DocumentRecognizerOrchestrator,
        )
        from aiflow.services.document_recognizer.registry import DocTypeRegistry

        reg = DocTypeRegistry(bootstrap_dir=tempfile.mkdtemp())
        reg.register_doctype(_hu_invoice_descriptor())

        orch = DocumentRecognizerOrchestrator(registry=reg, extract_fn=None)
        result = await orch.run(ClassifierInput(text="Számla"), tenant_id="t1")
        assert result is not None
        _, extraction, _ = result
        assert extraction.extracted_fields == {}
        assert any("extract_fn not configured" in w for w in extraction.validation_warnings)
