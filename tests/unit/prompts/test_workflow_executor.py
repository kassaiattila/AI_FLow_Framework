"""
@test_registry:
    suite: unit-prompts
    component: aiflow.prompts.workflow_executor (Sprint R / S141)
    covers:
        - src/aiflow/prompts/workflow_executor.py
    phase: sprint-r-s141
    priority: high
    estimated_duration_ms: 2000
    requires_services: []
    tags: [unit, prompts, workflow, executor, sprint-r, s141]

PromptWorkflowExecutor tests — opt-in matrix + lookup pass/fail +
nested resolution failure → graceful None return.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from aiflow.core.config import PromptWorkflowSettings
from aiflow.prompts.manager import PromptManager
from aiflow.prompts.workflow_executor import PromptWorkflowExecutor
from aiflow.prompts.workflow_loader import PromptWorkflowLoader

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def manager_with_workflows() -> Iterator[PromptManager]:
    """A PromptManager wired against the repo's local workflow YAMLs."""
    loader = PromptWorkflowLoader(REPO_ROOT / "prompts" / "workflows")
    loader.register_dir()
    mgr = PromptManager(workflows_enabled=True, workflow_loader=loader)
    # Register every skill's prompt YAMLs so nested step lookups resolve.
    for skill_dir in (REPO_ROOT / "skills").glob("*/prompts"):
        if skill_dir.is_dir():
            mgr.register_yaml_dir(skill_dir)
    yield mgr


def _settings(*, enabled: bool, skills_csv: str = "") -> PromptWorkflowSettings:
    return PromptWorkflowSettings(
        enabled=enabled,
        skills_csv=skills_csv,
    )


class TestIsSkillMigrated:
    def test_flag_off_returns_false(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows, _settings(enabled=False, skills_csv="invoice_processor")
        )
        assert ex.is_skill_migrated("invoice_processor") is False

    def test_flag_on_skill_listed_returns_true(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="invoice_processor,aszf_rag_chat"),
        )
        assert ex.is_skill_migrated("invoice_processor") is True
        assert ex.is_skill_migrated("aszf_rag_chat") is True

    def test_flag_on_skill_not_listed_returns_false(
        self, manager_with_workflows: PromptManager
    ) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        assert ex.is_skill_migrated("email_intent_processor") is False

    def test_empty_csv_means_no_skills(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(manager_with_workflows, _settings(enabled=True, skills_csv=""))
        assert ex.is_skill_migrated("invoice_processor") is False


class TestResolveForSkill:
    def test_skill_not_migrated_returns_none(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(manager_with_workflows, _settings(enabled=False))
        assert ex.resolve_for_skill("invoice_processor", "invoice_extraction_chain") is None

    def test_resolved_workflow_returns_real_chain(
        self, manager_with_workflows: PromptManager
    ) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        result = ex.resolve_for_skill("invoice_processor", "invoice_extraction_chain")
        assert result is not None
        wf, prompts = result
        assert wf.name == "invoice_extraction_chain"
        assert set(prompts.keys()) == {"classify", "extract_header", "extract_lines", "validate"}
        for step_id, p in prompts.items():
            assert p.system or p.user, f"step {step_id} resolved to empty prompt"

    def test_email_intent_chain_resolves(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="email_intent_processor"),
        )
        result = ex.resolve_for_skill("email_intent_processor", "email_intent_chain")
        assert result is not None
        wf, prompts = result
        assert wf.name == "email_intent_chain"
        assert "classify" in prompts

    def test_aszf_rag_chain_resolves(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="aszf_rag_chat"),
        )
        result = ex.resolve_for_skill("aszf_rag_chat", "aszf_rag_chain")
        assert result is not None
        wf, prompts = result
        assert wf.name == "aszf_rag_chain"
        assert "answer" in prompts

    def test_descriptor_missing_returns_none(self, manager_with_workflows: PromptManager) -> None:
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        assert ex.resolve_for_skill("invoice_processor", "no_such_workflow") is None

    def test_nested_prompt_missing_returns_none(self, tmp_path: Path) -> None:
        # Build a workflow whose step references an unregistered prompt.
        bad_yaml = (
            "name: bad_chain\nversion: '0.1.0'\n"
            "steps:\n  - id: only\n    prompt_name: not_registered\n"
        )
        (tmp_path / "bad_chain.yaml").write_text(bad_yaml, encoding="utf-8")
        loader = PromptWorkflowLoader(tmp_path)
        loader.register_dir()
        mgr = PromptManager(workflows_enabled=True, workflow_loader=loader)

        ex = PromptWorkflowExecutor(mgr, _settings(enabled=True, skills_csv="invoice_processor"))
        assert ex.resolve_for_skill("invoice_processor", "bad_chain") is None

    def test_label_override_propagates(self, manager_with_workflows: PromptManager) -> None:
        # Spy on the underlying manager to assert label propagation.
        captured: list[str | None] = []
        original_get_workflow = manager_with_workflows.get_workflow

        def spy(name: str, *, label: str | None = None):
            captured.append(label)
            return original_get_workflow(name, label=label)

        manager_with_workflows.get_workflow = spy  # type: ignore[method-assign]
        ex = PromptWorkflowExecutor(
            manager_with_workflows,
            _settings(enabled=True, skills_csv="invoice_processor"),
        )
        ex.resolve_for_skill("invoice_processor", "invoice_extraction_chain", label="staging")
        assert captured == ["staging"]


class TestSettingsCsvParsing:
    def test_empty_csv_parses_to_empty_list(self) -> None:
        assert PromptWorkflowSettings(skills_csv="").skills == []

    def test_single_skill(self) -> None:
        assert PromptWorkflowSettings(skills_csv="invoice_processor").skills == [
            "invoice_processor"
        ]

    def test_multiple_with_whitespace(self) -> None:
        s = PromptWorkflowSettings(skills_csv="  a , b ,  c")
        assert s.skills == ["a", "b", "c"]

    def test_trailing_commas_ignored(self) -> None:
        s = PromptWorkflowSettings(skills_csv="a,,b,")
        assert s.skills == ["a", "b"]
