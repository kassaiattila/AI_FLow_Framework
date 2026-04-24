"""
@test_registry:
    suite: unit-prompts
    component: aiflow.prompts.workflow_loader (Sprint R / S139)
    covers:
        - src/aiflow/prompts/workflow_loader.py
    phase: sprint-r-s139
    priority: high
    estimated_duration_ms: 2000
    requires_services: []
    tags: [unit, prompts, workflow, loader, sprint-r, s139]

PromptWorkflowLoader filesystem YAML loader tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiflow.prompts.workflow_loader import PromptWorkflowLoader, WorkflowYamlError

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


class TestPromptWorkflowLoader:
    def test_repo_example_round_trips(self) -> None:
        loader = PromptWorkflowLoader(REPO_ROOT / "prompts" / "workflows")
        wf = loader.load_from_yaml(
            REPO_ROOT / "prompts" / "workflows" / "uc3_intent_and_extract.yaml"
        )
        assert wf.name == "uc3_intent_and_extract"
        assert wf.version == "0.1.0"
        assert wf.step_ids() == ["classify", "extract_header", "extract_lines"]
        assert wf.get_step("extract_header").required is False
        assert wf.get_step("extract_header").metadata["cost_ceiling_usd"] == 0.02

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        loader = PromptWorkflowLoader(tmp_path)
        with pytest.raises(WorkflowYamlError, match="not found"):
            loader.load_from_yaml(tmp_path / "nope.yaml")

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        bad = _write(tmp_path / "bad.yaml", "name: x\n  bad: indent\n :\n")
        loader = PromptWorkflowLoader(tmp_path)
        with pytest.raises(WorkflowYamlError, match="invalid YAML"):
            loader.load_from_yaml(bad)

    def test_missing_required_field_raises(self, tmp_path: Path) -> None:
        # Missing `name` — pydantic validation error wrapped as WorkflowYamlError
        bad = _write(
            tmp_path / "no_name.yaml",
            "version: '0.1.0'\nsteps:\n  - id: a\n    prompt_name: p\n",
        )
        loader = PromptWorkflowLoader(tmp_path)
        with pytest.raises(WorkflowYamlError, match="parse failed"):
            loader.load_from_yaml(bad)

    def test_register_dir_discovers_and_skips_bad(self, tmp_path: Path) -> None:
        good = _write(
            tmp_path / "good.yaml",
            "name: good\nversion: '0.1.0'\nsteps:\n  - id: a\n    prompt_name: p\n",
        )
        _write(tmp_path / "broken.yaml", "::: not-yaml :::\n  - foo\n")
        loader = PromptWorkflowLoader(tmp_path)
        assert loader.register_dir() == 1
        assert loader.list_local() == ["good"]
        assert loader.path_for("good") == good
        assert loader.path_for("broken") is None

    def test_register_missing_dir_returns_zero(self, tmp_path: Path) -> None:
        loader = PromptWorkflowLoader(tmp_path / "does_not_exist")
        assert loader.register_dir() == 0
