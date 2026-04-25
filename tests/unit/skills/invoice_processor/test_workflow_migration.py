"""
@test_registry:
    suite: unit-skills
    component: skills.invoice_processor.workflows.process (Sprint T / S149)
    covers:
        - skills/invoice_processor/__init__.py
        - skills/invoice_processor/workflows/process.py
    phase: sprint-t-s149
    priority: critical
    estimated_duration_ms: 4000
    requires_services: []
    tags: [unit, skills, invoice_processor, workflow, executor, sprint-t, s149, s141-fu-2]

Sprint T S149 (S141-FU-2) — invoice_processor consumes
``invoice_extraction_chain`` via :class:`PromptWorkflowExecutor`. Tests
cover:
    * flag-off → executor returns ``None``, three LLM helpers call
      ``prompt_manager.get(...)`` byte-stable;
    * flag-on + skill in CSV → executor resolves descriptor, helpers
      receive the workflow's resolved ``classify`` / ``extract_header``
      / ``extract_lines`` PromptDefinitions;
    * flag-on but skill not in CSV → fall-through;
    * descriptor lookup failure → fall-through;
    * cost-ceiling enforced on ``extract_header`` (0.02) +
      ``extract_lines`` (0.03) only on flag-on;
    * ``CostGuardrailRefused`` propagates upward (not silently
      swallowed by the bare except in the legacy catch);
    * extracted-fields schema parity — flag-off vs flag-on produce the
      same dict shape on a deterministic mock LLM.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skills.invoice_processor.workflows import process as pmod

from aiflow.core.config import PromptWorkflowSettings
from aiflow.core.errors import CostGuardrailRefused
from aiflow.prompts.manager import PromptManager
from aiflow.prompts.schema import PromptConfig, PromptDefinition
from aiflow.prompts.workflow_executor import PromptWorkflowExecutor
from aiflow.prompts.workflow_loader import PromptWorkflowLoader

REPO_ROOT = Path(__file__).resolve().parents[4]


# --- Fixtures -----------------------------------------------------------------


def _settings(*, enabled: bool, skills_csv: str = "") -> PromptWorkflowSettings:
    return PromptWorkflowSettings(enabled=enabled, skills_csv=skills_csv)


@pytest.fixture
def workflow_aware_manager() -> PromptManager:
    """A PromptManager wired to the repo's workflow YAMLs + every skill."""
    loader = PromptWorkflowLoader(REPO_ROOT / "prompts" / "workflows")
    loader.register_dir()
    mgr = PromptManager(workflows_enabled=True, workflow_loader=loader)
    for skill_dir in (REPO_ROOT / "skills").glob("*/prompts"):
        if skill_dir.is_dir():
            mgr.register_yaml_dir(skill_dir)
    return mgr


def _stub_prompt(
    name: str, *, model: str = "openai/gpt-4o-mini", max_tokens: int = 256
) -> PromptDefinition:
    return PromptDefinition(
        name=name,
        version="0.0.1-test",
        system="Sprint T test override system",
        user="Sprint T test override user: {{ invoice_text }}",
        config=PromptConfig(model=model, temperature=0.0, max_tokens=max_tokens),
    )


def _llm_response(text: str) -> SimpleNamespace:
    """Build the ModelClient.generate(...) return shape consumed by helpers."""
    return SimpleNamespace(
        output=SimpleNamespace(text=text),
        input_tokens=100,
        output_tokens=50,
    )


# --- _resolve_workflow_step ---------------------------------------------------


class TestResolveWorkflowStep:
    def test_flag_off_returns_none_pair(self) -> None:
        executor_off = PromptWorkflowExecutor(
            pmod.prompt_manager, _settings(enabled=False, skills_csv="invoice_processor")
        )
        with patch.object(pmod, "prompt_workflow_executor", executor_off):
            prompt, ceiling = pmod._resolve_workflow_step("extract_header")
        assert prompt is None
        assert ceiling is None

    def test_flag_on_skill_not_in_csv_returns_none_pair(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_other = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="email_intent_processor"),
        )
        with patch.object(pmod, "prompt_workflow_executor", executor_other):
            prompt, ceiling = pmod._resolve_workflow_step("extract_header")
        assert prompt is None
        assert ceiling is None

    def test_flag_on_resolves_step_with_ceiling(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        with patch.object(pmod, "prompt_workflow_executor", executor_on):
            prompt_h, ceiling_h = pmod._resolve_workflow_step("extract_header")
            prompt_l, ceiling_l = pmod._resolve_workflow_step("extract_lines")
            prompt_c, ceiling_c = pmod._resolve_workflow_step("classify")
        assert isinstance(prompt_h, PromptDefinition)
        assert prompt_h.name == "invoice/header_extractor"
        assert ceiling_h == 0.02
        assert isinstance(prompt_l, PromptDefinition)
        assert prompt_l.name == "invoice/line_extractor"
        assert ceiling_l == 0.03
        # classify step has no cost_ceiling_usd in the descriptor.
        assert isinstance(prompt_c, PromptDefinition)
        assert prompt_c.name == "invoice/classifier"
        assert ceiling_c is None

    def test_descriptor_lookup_failure_falls_through(self) -> None:
        empty_loader = PromptWorkflowLoader(
            REPO_ROOT / "tests" / "unit" / "skills" / "invoice_processor"
        )  # no YAMLs in this dir
        empty_mgr = PromptManager(workflows_enabled=True, workflow_loader=empty_loader)
        executor_missing = PromptWorkflowExecutor(
            empty_mgr,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        with patch.object(pmod, "prompt_workflow_executor", executor_missing):
            prompt, ceiling = pmod._resolve_workflow_step("extract_header")
        assert prompt is None
        assert ceiling is None


# --- _enforce_step_cost_ceiling -----------------------------------------------


class TestEnforceStepCostCeiling:
    def test_under_ceiling_does_not_raise(self) -> None:
        prompt = _stub_prompt(
            "invoice/header_extractor", model="openai/gpt-4o-mini", max_tokens=128
        )
        # gpt-4o-mini ~ "cheap" tier — well under 1 USD on tiny payloads.
        pmod._enforce_step_cost_ceiling(prompt, "short text", 0.10, "extract_header")

    def test_over_ceiling_raises_cost_guardrail_refused(self) -> None:
        prompt = _stub_prompt("invoice/header_extractor", model="openai/gpt-4o", max_tokens=4096)
        with pytest.raises(CostGuardrailRefused) as exc_info:
            pmod._enforce_step_cost_ceiling(prompt, "x" * 8000, 0.0001, "extract_header")
        err = exc_info.value
        assert err.reason == "step_cost_ceiling_exceeded"
        assert err.tenant_id == "default"
        assert err.period == "per_step"
        assert err.remaining_usd == 0.0001


# --- _classify_with_llm — flag-off vs flag-on --------------------------------


class TestClassifyWithLlmOverride:
    @pytest.mark.asyncio
    async def test_flag_off_uses_manager_get(self) -> None:
        mock_pm = MagicMock()
        compiled = [{"role": "user", "content": "classify"}]
        registered_prompt = MagicMock()
        registered_prompt.compile.return_value = compiled
        registered_prompt.config = SimpleNamespace(
            model="gpt-4o-mini", temperature=0.0, max_tokens=256
        )
        mock_pm.get.return_value = registered_prompt

        with (
            patch.object(pmod, "prompt_manager", mock_pm),
            patch.object(pmod, "models_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_response('{"direction": "outgoing"}'))
            direction = await pmod._classify_with_llm("invoice text")

        mock_pm.get.assert_called_once_with("invoice/classifier")
        assert direction == "outgoing"

    @pytest.mark.asyncio
    async def test_flag_on_supplied_definition_skips_manager(self) -> None:
        mock_pm = MagicMock()
        override = _stub_prompt("invoice/classifier")
        with (
            patch.object(pmod, "prompt_manager", mock_pm),
            patch.object(pmod, "models_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_response('{"direction": "incoming"}'))
            direction = await pmod._classify_with_llm("invoice text", prompt_definition=override)

        mock_pm.get.assert_not_called()
        assert direction == "incoming"


# --- _extract_header / _extract_lines — workflow + cost-ceiling --------------


class TestExtractHelpersWorkflowWiring:
    @pytest.mark.asyncio
    async def test_header_flag_off_uses_manager_get(self) -> None:
        mock_pm = MagicMock()
        registered = MagicMock()
        registered.compile.return_value = [{"role": "user", "content": "h"}]
        registered.config = SimpleNamespace(model="gpt-4o", temperature=0.0, max_tokens=1024)
        mock_pm.get.return_value = registered

        with (
            patch.object(pmod, "prompt_manager", mock_pm),
            patch.object(pmod, "models_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_response('{"vendor":{"name":"X"}}'))
            out = await pmod._extract_header("hu invoice text")

        mock_pm.get.assert_called_once_with("invoice/header_extractor")
        assert out["vendor"] == {"name": "X"}

    @pytest.mark.asyncio
    async def test_header_flag_on_uses_override_and_skips_manager(self) -> None:
        mock_pm = MagicMock()
        override = _stub_prompt("invoice/header_extractor", model="openai/gpt-4o-mini")

        with (
            patch.object(pmod, "prompt_manager", mock_pm),
            patch.object(pmod, "models_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_response('{"vendor":{"name":"Y"}}'))
            out = await pmod._extract_header(
                "invoice text",
                prompt_definition=override,
                cost_ceiling_usd=0.10,  # generous → no refusal
            )

        mock_pm.get.assert_not_called()
        assert out["vendor"] == {"name": "Y"}

    @pytest.mark.asyncio
    async def test_header_cost_ceiling_exceeded_propagates(self) -> None:
        # gpt-4o + max_tokens=4096 + 8000-char text far exceeds 0.0001 USD.
        override = _stub_prompt("invoice/header_extractor", model="openai/gpt-4o", max_tokens=4096)
        with patch.object(pmod, "models_client") as mc:
            mc.generate = AsyncMock(return_value=_llm_response('{"vendor":{"name":"Z"}}'))
            with pytest.raises(CostGuardrailRefused) as exc_info:
                await pmod._extract_header(
                    "x" * 8000,
                    prompt_definition=override,
                    cost_ceiling_usd=0.0001,
                )
        # Generic LLM errors get caught; CostGuardrailRefused must escape.
        assert exc_info.value.reason == "step_cost_ceiling_exceeded"
        # The LLM was never called — refusal is pre-flight.
        mc.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_lines_cost_ceiling_exceeded_propagates(self) -> None:
        override = _stub_prompt("invoice/line_extractor", model="openai/gpt-4o", max_tokens=4096)
        with patch.object(pmod, "models_client") as mc:
            mc.generate = AsyncMock(return_value=_llm_response('{"line_items":[]}'))
            with pytest.raises(CostGuardrailRefused):
                await pmod._extract_lines(
                    "x" * 9000,
                    "y" * 4000,
                    prompt_definition=override,
                    cost_ceiling_usd=0.0001,
                )
        mc.generate.assert_not_called()


# --- extract_invoice_data step — flag-off vs flag-on schema parity ----------


def _mock_models_client_for_extraction() -> MagicMock:
    """A models_client.generate that returns alternating header/lines JSON
    so the two parallel calls inside extract_invoice_data pick up valid data."""
    mc = MagicMock()
    header_json = '{"vendor":{"name":"Sz Kft"},"buyer":{"name":"Vevo Kft"},"header":{"invoice_number":"INV-001","currency":"HUF"},"confidence":0.9}'
    lines_json = '{"line_items":[{"line_number":1,"description":"a","quantity":1,"unit":"db","unit_price":100,"net_amount":100,"vat_rate":27,"vat_amount":27,"gross_amount":127}],"totals":{"net_total":100,"vat_total":27,"gross_total":127},"confidence":0.85}'

    call_state = {"i": 0}

    async def fake_generate(*_args, **_kwargs):
        idx = call_state["i"]
        call_state["i"] += 1
        # Even calls → header (matches asyncio.gather scheduling order in practice;
        # both branches accept either body so order isn't strictly enforced).
        if idx % 2 == 0:
            return _llm_response(header_json)
        return _llm_response(lines_json)

    mc.generate = AsyncMock(side_effect=fake_generate)
    return mc


class TestExtractInvoiceDataFlagParity:
    @pytest.mark.asyncio
    async def test_flag_off_produces_extracted_fields_shape(self) -> None:
        executor_off = PromptWorkflowExecutor(
            pmod.prompt_manager, _settings(enabled=False, skills_csv="invoice_processor")
        )
        mc = _mock_models_client_for_extraction()
        data = {
            "files": [
                {
                    "raw_text": "ACME Kft 1234567-8-90 INV-001 100 HUF",
                    "raw_markdown": "",
                    "tables": [],
                }
            ]
        }
        with (
            patch.object(pmod, "prompt_workflow_executor", executor_off),
            patch.object(pmod, "models_client", mc),
        ):
            out = await pmod.extract_invoice_data(data)

        f = out["files"][0]
        # Shape contract used by Sprint Q EmailDetailResponse.extracted_fields.
        for key in ("vendor", "buyer", "header", "line_items", "totals", "extraction_confidence"):
            assert key in f, f"missing key {key} in flag-off output"

    @pytest.mark.asyncio
    async def test_flag_on_byte_identical_extracted_fields(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        # Build TWO executors backed by the same mocked LLM so the only
        # variable is workflow resolution. Header/lines mock returns are
        # deterministic, so the resulting dicts must be identical.
        executor_off = PromptWorkflowExecutor(
            workflow_aware_manager, _settings(enabled=False, skills_csv="invoice_processor")
        )
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager, _settings(enabled=True, skills_csv="invoice_processor")
        )

        async def run(executor: PromptWorkflowExecutor) -> dict:
            data = {
                "files": [
                    {
                        "raw_text": "ACME Kft 1234567-8-90 INV-001 100 HUF",
                        "raw_markdown": "",
                        "tables": [],
                        "filename": "f.pdf",
                    }
                ]
            }
            mc = _mock_models_client_for_extraction()
            with (
                patch.object(pmod, "prompt_workflow_executor", executor),
                patch.object(pmod, "models_client", mc),
            ):
                return await pmod.extract_invoice_data(data)

        off = await run(executor_off)
        on = await run(executor_on)

        # extraction_time_ms is a wall-clock measurement — drop before compare.
        for d in (off["files"][0], on["files"][0]):
            d.pop("extraction_time_ms", None)

        assert off["files"][0] == on["files"][0]


# --- Module-level singletons --------------------------------------------------


class TestModuleLevelExecutor:
    def test_executor_uses_workflow_settings_from_app_config(self) -> None:
        assert pmod.prompt_workflow_executor._settings is not None  # type: ignore[attr-defined]
        assert pmod.SKILL_NAME == "invoice_processor"
        assert pmod.WORKFLOW_NAME == "invoice_extraction_chain"
