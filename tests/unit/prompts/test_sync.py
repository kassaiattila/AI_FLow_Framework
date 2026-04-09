"""
@test_registry:
    suite: prompts-unit
    component: prompts.sync
    covers: [src/aiflow/prompts/sync.py]
    phase: 3
    priority: medium
    estimated_duration_ms: 200
    requires_services: []
    tags: [prompts, sync, langfuse, yaml, diff]
"""

import pytest

from aiflow.prompts.sync import DiffResult, PromptSyncer, SyncResult


@pytest.fixture
def sample_prompt_yaml(tmp_path):
    """Create a sample YAML prompt file for sync tests."""
    content = """\
name: sync-test
version: "2.0"
description: "Sync test prompt"
system: "You are a test assistant."
user: "Answer: {{ question }}"
config:
  model: gpt-4o
  temperature: 0.4
langfuse:
  sync: true
  labels: [dev, staging, prod]
"""
    p = tmp_path / "sync-test.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def no_sync_yaml(tmp_path):
    """Create a YAML prompt file with sync disabled."""
    content = """\
name: no-sync
version: "1.0"
system: "Static prompt."
langfuse:
  sync: false
"""
    p = tmp_path / "no-sync.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def sample_dir(tmp_path):
    """Directory with multiple YAML files for sync_directory."""
    for name in ["prompt-a", "prompt-b"]:
        content = f"""\
name: {name}
version: "1.0"
system: "You are {name}."
langfuse:
  sync: true
"""
        (tmp_path / f"{name}.yaml").write_text(content, encoding="utf-8")
    return tmp_path


class TestPromptSyncer:
    def test_sync_prompt_success(self, sample_prompt_yaml):
        syncer = PromptSyncer(dry_run=True)
        result = syncer.sync_prompt(sample_prompt_yaml, label="dev")
        assert isinstance(result, SyncResult)
        assert result.success is True
        assert result.prompt_name == "sync-test"
        assert result.version == "2.0"
        assert result.label == "dev"

    def test_sync_prompt_sync_disabled(self, no_sync_yaml):
        syncer = PromptSyncer(dry_run=True)
        result = syncer.sync_prompt(no_sync_yaml, label="prod")
        assert result.success is True
        assert "sync disabled" in result.error

    def test_sync_prompt_file_not_found(self, tmp_path):
        syncer = PromptSyncer(dry_run=True)
        result = syncer.sync_prompt(tmp_path / "missing.yaml", label="dev")
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_sync_directory(self, sample_dir):
        syncer = PromptSyncer(dry_run=True)
        results = syncer.sync_directory(sample_dir, label="staging")
        assert len(results) == 2
        assert all(r.success for r in results)
        names = {r.prompt_name for r in results}
        assert "prompt-a" in names
        assert "prompt-b" in names

    def test_diff_new_prompt(self, sample_prompt_yaml):
        """Diff against a prompt that does not exist remotely."""
        syncer = PromptSyncer(dry_run=True)
        diff = syncer.diff(sample_prompt_yaml)
        assert isinstance(diff, DiffResult)
        assert diff.prompt_name == "sync-test"
        assert diff.local_version == "2.0"
        assert diff.remote_version is None
        assert diff.has_changes is True
        assert "*new_prompt*" in diff.changed_fields
