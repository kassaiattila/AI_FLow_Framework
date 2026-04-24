"""
@test_registry:
    suite: unit-prompts
    component: aiflow.prompts.manager.get_workflow (Sprint R / S139)
    covers:
        - src/aiflow/prompts/manager.py
    phase: sprint-r-s139
    priority: high
    estimated_duration_ms: 2000
    requires_services: []
    tags: [unit, prompts, workflow, manager, sprint-r, s139]

PromptManager.get_workflow tests — flag gating + 3-layer resolution +
nested prompt resolution failure modes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aiflow.core.errors import FeatureDisabled
from aiflow.prompts.manager import PromptManager, WorkflowResolutionError
from aiflow.prompts.workflow_loader import PromptWorkflowLoader

REPO_ROOT = Path(__file__).resolve().parents[3]


def _build_manager(
    *,
    workflows_enabled: bool = True,
    langfuse_enabled: bool = False,
    langfuse_client=None,
    workflows_dir: Path | None = None,
) -> PromptManager:
    loader: PromptWorkflowLoader | None = None
    if workflows_dir is not None:
        loader = PromptWorkflowLoader(workflows_dir)
        loader.register_dir()
    mgr = PromptManager(
        cache_ttl=60.0,
        langfuse_enabled=langfuse_enabled,
        langfuse_client=langfuse_client,
        workflows_enabled=workflows_enabled,
        workflow_loader=loader,
    )
    # Register the existing skill prompts so step lookups can resolve.
    skills_root = REPO_ROOT / "skills"
    if (skills_root / "email_intent_processor" / "prompts").is_dir():
        mgr.register_yaml_dir(skills_root / "email_intent_processor" / "prompts")
    if (skills_root / "invoice_processor" / "prompts").is_dir():
        mgr.register_yaml_dir(skills_root / "invoice_processor" / "prompts")
    return mgr


class TestGetWorkflowFlagGating:
    def test_flag_off_raises_feature_disabled(self) -> None:
        mgr = _build_manager(workflows_enabled=False)
        with pytest.raises(FeatureDisabled) as exc_info:
            mgr.get_workflow("uc3_intent_and_extract")
        assert exc_info.value.feature == "prompt_workflows"


class TestGetWorkflowLocalYaml:
    def test_local_yaml_resolution_returns_workflow_and_steps(self) -> None:
        mgr = _build_manager(
            workflows_dir=REPO_ROOT / "prompts" / "workflows",
        )
        wf, resolved = mgr.get_workflow("uc3_intent_and_extract")
        assert wf.name == "uc3_intent_and_extract"
        assert set(resolved.keys()) == {"classify", "extract_header", "extract_lines"}
        # Every resolved entry should be a real PromptDefinition with non-empty system text
        for step_id, prompt_def in resolved.items():
            assert prompt_def.system or prompt_def.user, (
                f"step {step_id!r} resolved to an empty prompt"
            )

    def test_workflow_not_found_raises_keyerror(self) -> None:
        mgr = _build_manager(
            workflows_dir=REPO_ROOT / "prompts" / "workflows",
        )
        with pytest.raises(KeyError, match="not_a_real_workflow"):
            mgr.get_workflow("not_a_real_workflow")

    def test_missing_nested_prompt_raises_workflow_resolution_error(self, tmp_path: Path) -> None:
        # Build a workflow whose step references a non-existent prompt.
        wf_yaml = (
            "name: bad_chain\nversion: '0.1.0'\n"
            "steps:\n  - id: only\n    prompt_name: definitely_not_registered\n"
        )
        (tmp_path / "bad_chain.yaml").write_text(wf_yaml, encoding="utf-8")
        mgr = _build_manager(workflows_dir=tmp_path)
        with pytest.raises(WorkflowResolutionError) as exc_info:
            mgr.get_workflow("bad_chain")
        assert exc_info.value.workflow == "bad_chain"
        assert exc_info.value.step_id == "only"
        assert exc_info.value.prompt_name == "definitely_not_registered"

    def test_label_override_propagates(self, tmp_path: Path) -> None:
        # Spy that the inner get() is called with the override label.
        wf_yaml = (
            "name: label_check\nversion: '0.1.0'\ndefault_label: prod\n"
            "steps:\n  - id: only\n    prompt_name: x\n"
        )
        (tmp_path / "label_check.yaml").write_text(wf_yaml, encoding="utf-8")
        mgr = _build_manager(workflows_dir=tmp_path)

        captured: list[str] = []
        original_get = mgr.get

        def spy_get(name: str, label: str = "prod"):
            captured.append(label)
            # Return any registered prompt to avoid resolution error
            return original_get("email-intent/classifier" if name == "x" else name, label=label)

        mgr.get = spy_get  # type: ignore[method-assign]
        mgr.get_workflow("label_check", label="staging")
        assert captured == ["staging"]


class TestGetWorkflowLangfuseLayer:
    def test_langfuse_workflow_hit_skips_local_yaml(self, tmp_path: Path) -> None:
        # Pre-register a local YAML — Langfuse should win over it.
        local_yaml = (
            "name: pref_langfuse\nversion: '0.1.0'\n"
            "steps:\n  - id: a\n    prompt_name: email-intent/classifier\n"
        )
        (tmp_path / "pref_langfuse.yaml").write_text(local_yaml, encoding="utf-8")

        # Langfuse returns a different workflow for the same name. The
        # nested prompt lookup falls back to local YAML registry; we
        # only want the *workflow* fetch served from Langfuse.
        remote = MagicMock()
        remote.prompt = (
            '{"name": "pref_langfuse", "version": "9.9.9", '
            '"steps": [{"id": "a", "prompt_name": "email-intent/classifier"}]}'
        )
        client = MagicMock()

        def _get_prompt(*, name: str, label: str, type: str):  # noqa: A002 — Langfuse API kwarg name
            if name.startswith("workflow:"):
                return remote
            raise Exception("404 not found")  # noqa: TRY002 — mimics Langfuse miss

        client.get_prompt.side_effect = _get_prompt

        mgr = _build_manager(
            workflows_dir=tmp_path,
            langfuse_enabled=True,
            langfuse_client=client,
        )
        wf, _ = mgr.get_workflow("pref_langfuse")
        assert wf.version == "9.9.9", "Langfuse should have won over local YAML"
        # First call must be the workflow lookup with the workflow:<name> prefix.
        first_call = client.get_prompt.call_args_list[0]
        assert first_call.kwargs["name"] == "workflow:pref_langfuse"
        assert first_call.kwargs["label"] == "prod"
        assert first_call.kwargs["type"] == "text"

    def test_langfuse_miss_falls_back_to_local(self, tmp_path: Path) -> None:
        local_yaml = (
            "name: fallback\nversion: '0.1.0'\n"
            "steps:\n  - id: a\n    prompt_name: email-intent/classifier\n"
        )
        (tmp_path / "fallback.yaml").write_text(local_yaml, encoding="utf-8")

        client = MagicMock()
        client.get_prompt.side_effect = Exception("404 not found")

        mgr = _build_manager(
            workflows_dir=tmp_path,
            langfuse_enabled=True,
            langfuse_client=client,
        )
        wf, _ = mgr.get_workflow("fallback")
        assert wf.version == "0.1.0"
