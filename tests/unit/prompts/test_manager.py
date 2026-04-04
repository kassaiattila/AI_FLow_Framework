"""
@test_registry:
    suite: prompts-unit
    component: prompts.manager
    covers: [src/aiflow/prompts/manager.py]
    phase: 3
    priority: critical
    estimated_duration_ms: 400
    requires_services: []
    tags: [prompts, manager, cache, yaml, fallback, langfuse]
"""

import time

import pytest

from aiflow.prompts.manager import PromptManager


@pytest.fixture
def sample_yaml(tmp_path):
    """Create a sample YAML prompt file."""
    yaml_content = """\
name: greet-user
version: "1.0"
description: "Greeting prompt"
system: "You are a friendly greeter."
user: "Greet {{ name }} in {{ language }}."
config:
  model: gpt-4o
  temperature: 0.5
  max_tokens: 256
metadata:
  language: en
  tags: [greeting, demo]
examples:
  - input: "Greet Alice in English"
    output: "Hello, Alice!"
langfuse:
  sync: true
  labels: [dev, prod]
"""
    p = tmp_path / "greet-user.yaml"
    p.write_text(yaml_content, encoding="utf-8")
    return p


@pytest.fixture
def sample_yaml_dir(tmp_path):
    """Create a directory with multiple YAML prompt files."""
    for i, name in enumerate(["summarizer", "classifier", "translator"]):
        content = f"""\
name: {name}
version: "1.{i}"
description: "{name} prompt"
system: "You are a {name}."
user: "Process: {{{{ text }}}}"
config:
  model: gpt-4o
  temperature: 0.3
"""
        (tmp_path / f"{name}.yaml").write_text(content, encoding="utf-8")

    # Also add an invalid YAML to test skip
    (tmp_path / "broken.yaml").write_text("not: [valid: yaml: prompt", encoding="utf-8")
    return tmp_path


class TestPromptManagerLoadYaml:
    def test_load_yaml_success(self, sample_yaml):
        mgr = PromptManager()
        prompt = mgr.load_yaml(sample_yaml)
        assert prompt.name == "greet-user"
        assert prompt.version == "1.0"
        assert prompt.config.model == "gpt-4o"
        assert prompt.config.temperature == 0.5

    def test_load_yaml_file_not_found(self, tmp_path):
        mgr = PromptManager()
        with pytest.raises(FileNotFoundError):
            mgr.load_yaml(tmp_path / "nonexistent.yaml")

    def test_load_yaml_invalid_format(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("just a plain string", encoding="utf-8")
        mgr = PromptManager()
        with pytest.raises(ValueError, match="Invalid YAML"):
            mgr.load_yaml(bad)


class TestPromptManagerRegisterDir:
    def test_register_yaml_dir(self, sample_yaml_dir):
        mgr = PromptManager()
        count = mgr.register_yaml_dir(sample_yaml_dir)
        # 3 valid prompts, 1 broken (skipped)
        assert count == 3
        assert "summarizer" in mgr.registered_prompts
        assert "classifier" in mgr.registered_prompts
        assert "translator" in mgr.registered_prompts

    def test_register_yaml_dir_not_a_directory(self, tmp_path):
        mgr = PromptManager()
        fake = tmp_path / "not_a_dir.txt"
        fake.write_text("hello", encoding="utf-8")
        with pytest.raises(NotADirectoryError):
            mgr.register_yaml_dir(fake)


class TestPromptManagerGet:
    def test_get_from_yaml_fallback(self, sample_yaml):
        mgr = PromptManager()
        prompt_loaded = mgr.load_yaml(sample_yaml)
        mgr._yaml_registry[prompt_loaded.name] = sample_yaml

        result = mgr.get("greet-user", label="prod")
        assert result.name == "greet-user"
        assert result.config.temperature == 0.5

    def test_get_from_cache(self, sample_yaml):
        mgr = PromptManager()
        prompt_loaded = mgr.load_yaml(sample_yaml)
        mgr._yaml_registry[prompt_loaded.name] = sample_yaml

        # First call populates cache
        mgr.get("greet-user", label="prod")
        assert mgr.cache_size == 1

        # Second call hits cache
        result = mgr.get("greet-user", label="prod")
        assert result.name == "greet-user"

    def test_get_unknown_prompt_raises(self):
        mgr = PromptManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.get("nonexistent-prompt")

    def test_get_different_labels_are_separate(self, sample_yaml):
        mgr = PromptManager()
        prompt_loaded = mgr.load_yaml(sample_yaml)
        mgr._yaml_registry[prompt_loaded.name] = sample_yaml

        mgr.get("greet-user", label="dev")
        mgr.get("greet-user", label="prod")
        assert mgr.cache_size == 2


class TestPromptManagerCache:
    def test_cache_ttl_expiry(self, sample_yaml):
        mgr = PromptManager(cache_ttl=0.1)  # 100ms TTL
        prompt_loaded = mgr.load_yaml(sample_yaml)
        mgr._yaml_registry[prompt_loaded.name] = sample_yaml

        mgr.get("greet-user", label="prod")
        assert mgr.cache_size == 1

        # Wait for cache to expire
        time.sleep(0.15)

        # Should still work (reloads from YAML)
        result = mgr.get("greet-user", label="prod")
        assert result.name == "greet-user"

    def test_invalidate_specific_label(self, sample_yaml):
        mgr = PromptManager()
        prompt_loaded = mgr.load_yaml(sample_yaml)
        mgr._yaml_registry[prompt_loaded.name] = sample_yaml

        mgr.get("greet-user", label="dev")
        mgr.get("greet-user", label="prod")
        assert mgr.cache_size == 2

        mgr.invalidate("greet-user", label="dev")
        assert mgr.cache_size == 1

    def test_invalidate_all_labels(self, sample_yaml):
        mgr = PromptManager()
        prompt_loaded = mgr.load_yaml(sample_yaml)
        mgr._yaml_registry[prompt_loaded.name] = sample_yaml

        mgr.get("greet-user", label="dev")
        mgr.get("greet-user", label="prod")
        assert mgr.cache_size == 2

        mgr.invalidate("greet-user")
        assert mgr.cache_size == 0
