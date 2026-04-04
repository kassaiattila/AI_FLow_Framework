"""
@test_registry:
    suite: prompts-unit
    component: prompts.schema
    covers: [src/aiflow/prompts/schema.py]
    phase: 3
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [prompts, schema, pydantic, jinja2, compile]
"""

import pytest
from jinja2 import UndefinedError

from aiflow.prompts.schema import (
    LangfuseSettings,
    PromptConfig,
    PromptDefinition,
    PromptExample,
    PromptMetadata,
)


class TestPromptConfig:
    def test_default_values(self):
        config = PromptConfig()
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.response_format is None

    def test_custom_values(self):
        config = PromptConfig(
            model="claude-3-opus",
            temperature=0.2,
            max_tokens=4096,
            response_format="json_object",
        )
        assert config.model == "claude-3-opus"
        assert config.temperature == 0.2
        assert config.max_tokens == 4096
        assert config.response_format == "json_object"


class TestPromptExample:
    def test_example_creation(self):
        ex = PromptExample(input="What is 2+2?", output="4")
        assert ex.input == "What is 2+2?"
        assert ex.output == "4"
        assert ex.explanation == ""

    def test_example_with_explanation(self):
        ex = PromptExample(
            input="Translate hello",
            output="Bonjour",
            explanation="French translation",
        )
        assert ex.explanation == "French translation"


class TestLangfuseSettings:
    def test_defaults(self):
        settings = LangfuseSettings()
        assert settings.sync is True
        assert settings.labels == ["dev", "test", "staging", "prod"]

    def test_custom_labels(self):
        settings = LangfuseSettings(sync=False, labels=["dev", "prod"])
        assert settings.sync is False
        assert len(settings.labels) == 2


class TestPromptDefinition:
    def test_minimal_creation(self):
        prompt = PromptDefinition(name="test-prompt")
        assert prompt.name == "test-prompt"
        assert prompt.version == "1.0"
        assert prompt.description == ""
        assert prompt.system == ""
        assert prompt.user == ""
        assert isinstance(prompt.config, PromptConfig)
        assert isinstance(prompt.metadata, PromptMetadata)
        assert prompt.examples == []

    def test_full_creation(self):
        prompt = PromptDefinition(
            name="classifier",
            version="2.1",
            description="Classifies documents by topic",
            system="You are a document classifier. Language: {{ language }}.",
            user="Classify this: {{ text }}",
            config=PromptConfig(model="gpt-4o", temperature=0.3),
            metadata=PromptMetadata(language="en", tags=["classification", "nlp"]),
            examples=[
                PromptExample(input="A cat sat on a mat", output="animals"),
            ],
            langfuse=LangfuseSettings(sync=True, labels=["dev", "prod"]),
        )
        assert prompt.name == "classifier"
        assert prompt.version == "2.1"
        assert prompt.config.model == "gpt-4o"
        assert prompt.metadata.tags == ["classification", "nlp"]
        assert len(prompt.examples) == 1

    def test_compile_system_only(self):
        prompt = PromptDefinition(
            name="sys-only",
            system="You are a helpful {{ role }}.",
        )
        messages = prompt.compile({"role": "assistant"})
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."

    def test_compile_user_only(self):
        prompt = PromptDefinition(
            name="user-only",
            user="Summarize: {{ text }}",
        )
        messages = prompt.compile({"text": "Long document content"})
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Long document content" in messages[0]["content"]

    def test_compile_system_and_user(self):
        prompt = PromptDefinition(
            name="full",
            system="You are a {{ role }}.",
            user="Do this: {{ task }}",
        )
        messages = prompt.compile({"role": "translator", "task": "translate hello"})
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a translator."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Do this: translate hello"

    def test_compile_with_examples(self):
        prompt = PromptDefinition(
            name="few-shot",
            system="Classify the sentiment.",
            user="Classify: {{ text }}",
            examples=[
                PromptExample(input="I love this!", output="positive"),
                PromptExample(input="Terrible product.", output="negative"),
            ],
        )
        messages = prompt.compile({"text": "Not bad"})
        # system + 2 examples (user+assistant each) + user = 6
        assert len(messages) == 6
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "I love this!"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "positive"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Terrible product."
        assert messages[4]["role"] == "assistant"
        assert messages[4]["content"] == "negative"
        assert messages[5]["role"] == "user"
        assert "Not bad" in messages[5]["content"]

    def test_compile_no_variables(self):
        prompt = PromptDefinition(
            name="static",
            system="You are a helper.",
            user="What is 2+2?",
        )
        messages = prompt.compile()
        assert len(messages) == 2
        assert messages[0]["content"] == "You are a helper."
        assert messages[1]["content"] == "What is 2+2?"

    def test_compile_missing_variable_raises(self):
        prompt = PromptDefinition(
            name="missing-var",
            system="Hello {{ name }}",
        )
        with pytest.raises(UndefinedError):
            prompt.compile({})

    def test_compile_empty_prompt(self):
        prompt = PromptDefinition(name="empty")
        messages = prompt.compile()
        assert messages == []

    def test_model_dump_roundtrip(self):
        prompt = PromptDefinition(
            name="roundtrip",
            version="1.5",
            system="Hello {{ name }}",
            config=PromptConfig(model="gpt-4o-mini", temperature=0.5),
        )
        data = prompt.model_dump()
        restored = PromptDefinition(**data)
        assert restored.name == prompt.name
        assert restored.version == prompt.version
        assert restored.config.model == prompt.config.model
