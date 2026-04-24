"""
@test_registry:
    suite: unit-core
    component: aiflow.core.config.PromptWorkflowSettings (Sprint R / S139)
    covers:
        - src/aiflow/core/config.py
    phase: sprint-r-s139
    priority: medium
    estimated_duration_ms: 500
    requires_services: []
    tags: [unit, core, settings, prompts, sprint-r, s139]
"""

from __future__ import annotations

import pytest

from aiflow.core.config import AIFlowSettings, PromptWorkflowSettings


def test_defaults() -> None:
    s = PromptWorkflowSettings()
    assert s.enabled is False
    assert s.workflows_dir == "prompts/workflows"
    assert s.cache_ttl_seconds == 300


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIFLOW_PROMPT_WORKFLOWS__ENABLED", "true")
    monkeypatch.setenv("AIFLOW_PROMPT_WORKFLOWS__WORKFLOWS_DIR", "custom/dir")
    monkeypatch.setenv("AIFLOW_PROMPT_WORKFLOWS__CACHE_TTL_SECONDS", "60")
    s = PromptWorkflowSettings()
    assert s.enabled is True
    assert s.workflows_dir == "custom/dir"
    assert s.cache_ttl_seconds == 60


def test_mounted_on_aiflow_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIFLOW_PROMPT_WORKFLOWS__ENABLED", "true")
    parent = AIFlowSettings()
    assert parent.prompt_workflows.enabled is True


def test_skills_csv_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV",
        "invoice_processor, email_intent_processor",
    )
    s = PromptWorkflowSettings()
    assert s.skills == ["invoice_processor", "email_intent_processor"]


def test_skills_csv_default_empty() -> None:
    s = PromptWorkflowSettings()
    assert s.skills == []
    assert s.skills_csv == ""
