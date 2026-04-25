"""
@test_registry:
    suite: unit-skills
    component: skills.email_intent_processor.workflows.classify (Sprint T / S148)
    covers:
        - skills/email_intent_processor/__init__.py
        - skills/email_intent_processor/workflows/classify.py
        - skills/email_intent_processor/classifiers/__init__.py
        - skills/email_intent_processor/classifiers/llm_classifier.py
    phase: sprint-t-s148
    priority: critical
    estimated_duration_ms: 3000
    requires_services: []
    tags: [unit, skills, email_intent_processor, workflow, executor, sprint-t, s148, s141-fu-1]

Sprint T S148 (S141-FU-1) — email_intent_processor consumes
``email_intent_chain`` via :class:`PromptWorkflowExecutor`. Tests cover:
    * flag-off → executor returns ``None``, legacy single-prompt path runs
      unchanged (byte-stable);
    * flag-on + skill in CSV → executor resolves descriptor, classifier
      receives the workflow's resolved ``classify``-step prompt;
    * flag-on but skill not in CSV → fall-through;
    * descriptor lookup failure → fall-through;
    * sklearn ``high-confidence`` short-circuit (Sprint K body-only path)
      never invokes the LLM, so the executor is benign;
    * LLMClassifier honours an explicit ``prompt_definition`` override
      and skips the manager lookup entirely.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skills.email_intent_processor.classifiers import HybridClassifier
from skills.email_intent_processor.classifiers.llm_classifier import LLMClassifier
from skills.email_intent_processor.models import IntentResult
from skills.email_intent_processor.workflows import classify as cmod

from aiflow.core.config import PromptWorkflowSettings
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


@pytest.fixture
def llm_prompt() -> PromptDefinition:
    return PromptDefinition(
        name="email-intent/classifier",
        version="0.0.1-test",
        system="Sprint T test override system",
        user="Sprint T test override user: {{ subject }}",
        config=PromptConfig(model="gpt-4o-mini", temperature=0.0, max_tokens=128),
    )


# --- LLMClassifier override path ---------------------------------------------


class TestLLMClassifierPromptDefinitionOverride:
    @pytest.mark.asyncio
    async def test_override_skips_manager_lookup(self, llm_prompt: PromptDefinition) -> None:
        mock_mc = MagicMock()
        mock_pm = MagicMock()
        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(
            text='{"intent_id": "complaint", "confidence": 0.91, "reasoning": "ok"}'
        )
        mock_mc.generate = AsyncMock(return_value=mock_result)

        clf = LLMClassifier(mock_mc, mock_pm, prompt_name="email-intent/classifier")
        result = await clf.classify(
            "Reklamacio panaszom van",
            subject="Panasz",
            prompt_definition=llm_prompt,
        )

        assert result.intent_id == "complaint"
        assert result.method == "llm"
        # The override means the manager.get(...) path must NOT have been hit.
        mock_pm.get.assert_not_called()
        mock_mc.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_override_falls_back_to_manager(self) -> None:
        mock_mc = MagicMock()
        mock_pm = MagicMock()
        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = [{"role": "user", "content": "classify"}]
        mock_prompt.config = SimpleNamespace(model="gpt-4o-mini", temperature=0.1, max_tokens=512)
        mock_pm.get.return_value = mock_prompt

        mock_result = MagicMock()
        mock_result.output = SimpleNamespace(
            text='{"intent_id": "inquiry", "confidence": 0.7, "reasoning": "x"}'
        )
        mock_mc.generate = AsyncMock(return_value=mock_result)

        clf = LLMClassifier(mock_mc, mock_pm, prompt_name="email-intent/classifier")
        result = await clf.classify("Mikor erkezik a szamla?", subject="Erdeklodes")

        assert result.intent_id == "inquiry"
        mock_pm.get.assert_called_once_with("email-intent/classifier")


# --- HybridClassifier propagation --------------------------------------------


class TestHybridClassifierForwardsOverride:
    @pytest.mark.asyncio
    async def test_llm_only_path_forwards_prompt_definition(
        self, llm_prompt: PromptDefinition
    ) -> None:
        mock_llm = MagicMock()
        mock_llm.classify = AsyncMock(
            return_value=IntentResult(intent_id="order", confidence=0.83, method="llm")
        )

        hc = HybridClassifier(
            sklearn_classifier=None,
            llm_classifier=mock_llm,
            strategy="llm_only",
        )
        result = await hc.classify(
            "Uj szerzodest szeretnek",
            subject="Megrendeles",
            llm_prompt_definition=llm_prompt,
        )

        assert result.intent_id == "order"
        mock_llm.classify.assert_called_once()
        kwargs = mock_llm.classify.call_args.kwargs
        assert kwargs["prompt_definition"] is llm_prompt

    @pytest.mark.asyncio
    async def test_sklearn_high_confidence_skips_llm_and_override(
        self, llm_prompt: PromptDefinition
    ) -> None:
        # Sprint K body-only baseline: when sklearn is confident enough the
        # LLM (and the workflow override that goes with it) is never used.
        mock_sklearn = MagicMock()
        mock_sklearn.predict.return_value = {
            "intent": "complaint",
            "confidence": 0.92,
            "alternatives": [],
        }
        mock_llm = MagicMock()

        hc = HybridClassifier(
            sklearn_classifier=mock_sklearn,
            llm_classifier=mock_llm,
            strategy="sklearn_first",
            confidence_threshold=0.6,
        )
        result = await hc.classify(
            "Reklamacio",
            llm_prompt_definition=llm_prompt,
        )

        assert result.intent_id == "complaint"
        mock_llm.classify.assert_not_called()


# --- classify_intent step + executor wiring -----------------------------------


def _patched_classifier(intent_id: str = "invoice_received") -> MagicMock:
    """Build a hybrid_classifier mock that records the LLM-prompt arg."""
    mock_hc = MagicMock()
    mock_hc.classify = AsyncMock(
        return_value=IntentResult(intent_id=intent_id, confidence=0.88, method="llm")
    )
    return mock_hc


class TestClassifyIntentExecutorWiring:
    @pytest.mark.asyncio
    async def test_flag_off_falls_through_no_override(self) -> None:
        executor_off = PromptWorkflowExecutor(
            cmod.prompt_manager, _settings(enabled=False, skills_csv="email_intent_processor")
        )
        mock_hc = _patched_classifier()

        with (
            patch.object(cmod, "prompt_workflow_executor", executor_off),
            patch.object(cmod, "hybrid_classifier", mock_hc),
            patch.object(cmod, "schema_registry") as sr,
        ):
            sr.load_schema.return_value = {
                "intents": [{"id": "invoice_received", "display_name": "Szamla erkezett"}]
            }
            result = await cmod.classify_intent(
                {"subject": "Szamla", "body": "Csatolva a marciusi szamla.", "attachment_text": ""}
            )

        assert result["intent"]["intent_id"] == "invoice_received"
        kwargs = mock_hc.classify.call_args.kwargs
        assert kwargs["llm_prompt_definition"] is None

    @pytest.mark.asyncio
    async def test_flag_on_skill_listed_resolves_and_passes_prompt(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="email_intent_processor"),
        )
        mock_hc = _patched_classifier()

        with (
            patch.object(cmod, "prompt_workflow_executor", executor_on),
            patch.object(cmod, "hybrid_classifier", mock_hc),
            patch.object(cmod, "schema_registry") as sr,
        ):
            sr.load_schema.return_value = {
                "intents": [{"id": "invoice_received", "display_name": "Szamla erkezett"}]
            }
            await cmod.classify_intent(
                {"subject": "Szamla", "body": "Csatolva a szamla.", "attachment_text": ""}
            )

        kwargs = mock_hc.classify.call_args.kwargs
        forwarded = kwargs["llm_prompt_definition"]
        assert isinstance(forwarded, PromptDefinition)
        # The classify step in email_intent_chain references
        # email-intent/classifier — that must be what we resolved.
        assert forwarded.name == "email-intent/classifier"

    @pytest.mark.asyncio
    async def test_flag_on_skill_not_in_csv_falls_through(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_other_skill = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        mock_hc = _patched_classifier()

        with (
            patch.object(cmod, "prompt_workflow_executor", executor_other_skill),
            patch.object(cmod, "hybrid_classifier", mock_hc),
            patch.object(cmod, "schema_registry") as sr,
        ):
            sr.load_schema.return_value = {"intents": []}
            await cmod.classify_intent({"subject": "x", "body": "y", "attachment_text": ""})

        kwargs = mock_hc.classify.call_args.kwargs
        assert kwargs["llm_prompt_definition"] is None

    @pytest.mark.asyncio
    async def test_descriptor_lookup_failure_falls_through(self) -> None:
        # Manager has workflows enabled but no descriptors registered,
        # so resolve_for_skill returns None on KeyError.
        empty_loader = PromptWorkflowLoader(
            REPO_ROOT / "tests" / "unit" / "skills" / "email_intent_processor"
        )  # no YAMLs
        empty_mgr = PromptManager(workflows_enabled=True, workflow_loader=empty_loader)
        executor_descriptor_missing = PromptWorkflowExecutor(
            empty_mgr,
            _settings(enabled=True, skills_csv="email_intent_processor"),
        )
        mock_hc = _patched_classifier()

        with (
            patch.object(cmod, "prompt_workflow_executor", executor_descriptor_missing),
            patch.object(cmod, "hybrid_classifier", mock_hc),
            patch.object(cmod, "schema_registry") as sr,
        ):
            sr.load_schema.return_value = {"intents": []}
            await cmod.classify_intent({"subject": "x", "body": "y", "attachment_text": ""})

        kwargs = mock_hc.classify.call_args.kwargs
        assert kwargs["llm_prompt_definition"] is None

    @pytest.mark.asyncio
    async def test_attachment_text_still_concatenated_on_flag_on(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        # Sprint O attachment-aware path: attachment text is appended to body
        # before classification. Flag-on must not regress that contract.
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="email_intent_processor"),
        )
        mock_hc = _patched_classifier()

        with (
            patch.object(cmod, "prompt_workflow_executor", executor_on),
            patch.object(cmod, "hybrid_classifier", mock_hc),
            patch.object(cmod, "schema_registry") as sr,
        ):
            sr.load_schema.return_value = {"intents": []}
            await cmod.classify_intent(
                {
                    "subject": "Szamla",
                    "body": "Csatolva.",
                    "attachment_text": "[invoice.pdf]: 2026-03 SZ-0001 brutto 254000 Ft",
                }
            )

        called_text = mock_hc.classify.call_args.kwargs["text"]
        assert "Csatolva." in called_text
        assert "Csatolt dokumentumok" in called_text
        assert "SZ-0001" in called_text


# --- Module-level executor singleton ------------------------------------------


class TestModuleLevelExecutor:
    def test_executor_uses_workflow_settings_from_app_config(self) -> None:
        # The skill's module-level executor takes the global PromptWorkflow
        # settings as-is — no per-skill copy. Migration relies on this.
        assert cmod.prompt_workflow_executor._settings is not None  # type: ignore[attr-defined]
        assert cmod.SKILL_NAME == "email_intent_processor"
        assert cmod.WORKFLOW_NAME == "email_intent_chain"
