"""
@test_registry:
    suite: unit-skills
    component: skills.aszf_rag_chat.workflows.query (Sprint T / S150)
    covers:
        - skills/aszf_rag_chat/__init__.py
        - skills/aszf_rag_chat/workflows/query.py
    phase: sprint-t-s150
    priority: critical
    estimated_duration_ms: 3000
    requires_services: []
    tags: [unit, skills, aszf_rag_chat, workflow, executor, sprint-t, s150, s141-fu-3]

Sprint T S150 (S141-FU-3) — aszf_rag_chat consumes ``aszf_rag_chain``
via :class:`PromptWorkflowExecutor` for the **baseline persona only**.
Tests cover:
    * baseline persona + flag-on + skill in CSV → executor resolves
      descriptor; ``rewrite_query`` / ``system_baseline`` / ``answer`` /
      ``extract_citations`` PromptDefinitions are returned;
    * expert / mentor persona always falls through (every flag state) so
      the legacy single-prompt path runs byte-stable;
    * flag-off → None even on baseline persona;
    * skill not in CSV → None;
    * descriptor lookup failure (empty loader) → None;
    * rewrite_query / extract_citations / generate_answer step-level
      wiring uses the workflow override on baseline + flag-on, and falls
      back to ``_prompt_manager.get(...)`` otherwise.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from skills.aszf_rag_chat.workflows import query as qmod

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


def _stub_prompt(
    name: str, *, model: str = "openai/gpt-4o-mini", max_tokens: int = 256
) -> PromptDefinition:
    return PromptDefinition(
        name=name,
        version="0.0.1-test",
        system="Sprint T S150 override system",
        user="Sprint T S150 override user: {{ question }}",
        config=PromptConfig(model=model, temperature=0.0, max_tokens=max_tokens),
    )


# --- Module-level singletons --------------------------------------------------


class TestModuleLevelSingletons:
    def test_constants_match_descriptor_and_skill(self) -> None:
        assert qmod.WORKFLOW_NAME == "aszf_rag_chain"
        assert qmod.SKILL_NAME == "aszf_rag_chat"
        assert qmod.BASELINE_PERSONA == "baseline"

    def test_executor_singleton_exists(self) -> None:
        assert isinstance(qmod.prompt_workflow_executor, PromptWorkflowExecutor)


# --- _resolve_workflow_for_persona -------------------------------------------


class TestResolveWorkflowForPersona:
    def test_baseline_flag_off_returns_none(self) -> None:
        executor_off = PromptWorkflowExecutor(
            qmod._prompt_manager, _settings(enabled=False, skills_csv="aszf_rag_chat")
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_off):
            assert qmod._resolve_workflow_for_persona("baseline") is None

    def test_baseline_flag_on_skill_not_in_csv_returns_none(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_other = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="email_intent_processor"),
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_other):
            assert qmod._resolve_workflow_for_persona("baseline") is None

    def test_baseline_flag_on_resolves_full_step_map(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_on):
            resolved = qmod._resolve_workflow_for_persona("baseline")
        assert resolved is not None
        workflow, prompt_map = resolved
        assert workflow.name == "aszf_rag_chain"
        # All four descriptor steps must resolve to a PromptDefinition.
        assert set(prompt_map.keys()) == {
            "rewrite_query",
            "system_baseline",
            "answer",
            "extract_citations",
        }
        assert prompt_map["rewrite_query"].name == "aszf-rag/query_rewriter"
        assert prompt_map["system_baseline"].name == "aszf-rag/system_prompt_baseline"
        assert prompt_map["answer"].name == "aszf-rag/answer_generator"
        assert prompt_map["extract_citations"].name == "aszf-rag/citation_extractor"

    def test_expert_persona_always_falls_through(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_on):
            assert qmod._resolve_workflow_for_persona("expert") is None

    def test_mentor_persona_always_falls_through(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_on):
            assert qmod._resolve_workflow_for_persona("mentor") is None

    def test_unknown_persona_falls_through(self, workflow_aware_manager: PromptManager) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_on):
            assert qmod._resolve_workflow_for_persona("nonexistent_role") is None

    def test_descriptor_lookup_failure_returns_none(self) -> None:
        # Empty loader dir → workflow descriptor cannot be resolved.
        empty_loader = PromptWorkflowLoader(
            REPO_ROOT / "tests" / "unit" / "skills" / "aszf_rag_chat"
        )
        empty_mgr = PromptManager(workflows_enabled=True, workflow_loader=empty_loader)
        executor_missing = PromptWorkflowExecutor(
            empty_mgr,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        with patch.object(qmod, "prompt_workflow_executor", executor_missing):
            assert qmod._resolve_workflow_for_persona("baseline") is None


# --- rewrite_query step wiring -----------------------------------------------


def _llm_text_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        output=SimpleNamespace(text=text),
        cost_usd=0.0,
        input_tokens=10,
        output_tokens=10,
    )


class TestRewriteQueryWorkflowWiring:
    @pytest.mark.asyncio
    async def test_baseline_flag_on_uses_workflow_prompt(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("rewritten"))
            out = await qmod.rewrite_query({"question": "Mi a GDPR?", "role": "baseline"})

        # The legacy manager.get must NOT be invoked when the workflow path runs.
        legacy_pm.get.assert_not_called()
        assert out["rewritten_query"] == "rewritten"
        assert out["original_question"] == "Mi a GDPR?"

    @pytest.mark.asyncio
    async def test_expert_flag_on_uses_legacy_prompt(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        legacy_pm.get.return_value = _stub_prompt("aszf-rag/query_rewriter")
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("legacy-rewrite"))
            await qmod.rewrite_query({"question": "Q?", "role": "expert"})

        legacy_pm.get.assert_called_once_with("aszf-rag/query_rewriter")

    @pytest.mark.asyncio
    async def test_flag_off_baseline_uses_legacy_prompt(self) -> None:
        executor_off = PromptWorkflowExecutor(
            qmod._prompt_manager, _settings(enabled=False, skills_csv="aszf_rag_chat")
        )
        legacy_pm = MagicMock()
        legacy_pm.get.return_value = _stub_prompt("aszf-rag/query_rewriter")
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_off),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("legacy"))
            await qmod.rewrite_query({"question": "Q?", "role": "baseline"})

        legacy_pm.get.assert_called_once_with("aszf-rag/query_rewriter")

    @pytest.mark.asyncio
    async def test_default_role_treated_as_baseline_on_flag_on(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        # No "role" key → defaults to RoleType.BASELINE → workflow path runs.
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("ok"))
            await qmod.rewrite_query({"question": "Q?"})

        legacy_pm.get.assert_not_called()


# --- generate_answer step wiring (system_baseline) ---------------------------


def _stub_system_prompt_with_user_message(name: str) -> PromptDefinition:
    """Workflow-resolved system_baseline prompt with both system + user roles
    so generate_answer's ``has_user_msg`` branch doesn't append another one."""
    return PromptDefinition(
        name=name,
        version="0.0.1-test",
        system="S150 baseline system override",
        user="S150 baseline user: {{ context }} :: {{ question }}",
        config=PromptConfig(model="openai/gpt-4o", temperature=0.3, max_tokens=2000),
    )


class TestGenerateAnswerWorkflowWiring:
    @pytest.mark.asyncio
    async def test_baseline_flag_on_uses_workflow_system_prompt(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("workflow-answer"))
            out = await qmod.generate_answer(
                {
                    "context": "ctx",
                    "question": "Q?",
                    "sources": [],
                    "search_results": [],
                    "role": "baseline",
                }
            )

        legacy_pm.get.assert_not_called()
        assert out["answer"] == "workflow-answer"
        assert out["role"] == "baseline"

    @pytest.mark.asyncio
    async def test_expert_persona_always_uses_legacy(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        legacy_pm.get.return_value = _stub_system_prompt_with_user_message(
            "aszf-rag/system_prompt_expert"
        )
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("expert-answer"))
            out = await qmod.generate_answer(
                {
                    "context": "ctx",
                    "question": "Q?",
                    "sources": [],
                    "search_results": [],
                    "role": "expert",
                }
            )

        legacy_pm.get.assert_called_once_with("aszf-rag/system_prompt_expert")
        assert out["role"] == "expert"

    @pytest.mark.asyncio
    async def test_mentor_persona_always_uses_legacy(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        legacy_pm.get.return_value = _stub_system_prompt_with_user_message(
            "aszf-rag/system_prompt_mentor"
        )
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_text_response("mentor-answer"))
            out = await qmod.generate_answer(
                {
                    "context": "ctx",
                    "question": "Q?",
                    "sources": [],
                    "search_results": [],
                    "role": "mentor",
                }
            )

        legacy_pm.get.assert_called_once_with("aszf-rag/system_prompt_mentor")
        assert out["role"] == "mentor"


# --- extract_citations step wiring -------------------------------------------


def _llm_structured_response() -> SimpleNamespace:
    return SimpleNamespace(
        output=SimpleNamespace(structured=[]),
        cost_usd=0.0,
        input_tokens=5,
        output_tokens=5,
    )


def _stub_citation_prompt(name: str = "aszf-rag/citation_extractor") -> PromptDefinition:
    """Citation prompt stub whose user template only references variables that
    extract_citations actually passes (answer / context / sources)."""
    return PromptDefinition(
        name=name,
        version="0.0.1-test",
        system="S150 citation system override",
        user="S150 citation user — answer={{ answer }} context={{ context }} sources={{ sources }}",
        config=PromptConfig(model="openai/gpt-4o-mini", temperature=0.0, max_tokens=512),
    )


class TestExtractCitationsWorkflowWiring:
    @pytest.mark.asyncio
    async def test_baseline_flag_on_uses_workflow_prompt(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_structured_response())
            out = await qmod.extract_citations(
                {
                    "answer": "ans",
                    "context": "ctx",
                    "sources": [],
                    "search_results": [],
                    "role": "baseline",
                }
            )

        legacy_pm.get.assert_not_called()
        assert out["citations"] == []

    @pytest.mark.asyncio
    async def test_expert_flag_on_uses_legacy_prompt(
        self, workflow_aware_manager: PromptManager
    ) -> None:
        executor_on = PromptWorkflowExecutor(
            workflow_aware_manager,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        legacy_pm = MagicMock()
        legacy_pm.get.return_value = _stub_citation_prompt("aszf-rag/citation_extractor")
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_on),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_structured_response())
            await qmod.extract_citations(
                {
                    "answer": "ans",
                    "context": "ctx",
                    "sources": [],
                    "search_results": [],
                    "role": "expert",
                }
            )

        legacy_pm.get.assert_called_once_with("aszf-rag/citation_extractor")

    @pytest.mark.asyncio
    async def test_flag_off_baseline_uses_legacy_prompt(self) -> None:
        executor_off = PromptWorkflowExecutor(
            qmod._prompt_manager, _settings(enabled=False, skills_csv="aszf_rag_chat")
        )
        legacy_pm = MagicMock()
        legacy_pm.get.return_value = _stub_citation_prompt("aszf-rag/citation_extractor")
        with (
            patch.object(qmod, "prompt_workflow_executor", executor_off),
            patch.object(qmod, "_prompt_manager", legacy_pm),
            patch.object(qmod, "_model_client") as mc,
        ):
            mc.generate = AsyncMock(return_value=_llm_structured_response())
            await qmod.extract_citations(
                {
                    "answer": "ans",
                    "context": "ctx",
                    "sources": [],
                    "search_results": [],
                    "role": "baseline",
                }
            )

        legacy_pm.get.assert_called_once_with("aszf-rag/citation_extractor")
