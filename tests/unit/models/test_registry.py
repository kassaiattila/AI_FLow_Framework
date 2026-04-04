"""
@test_registry:
    suite: core-unit
    component: models.registry
    covers: [src/aiflow/models/registry.py]
    phase: 1
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [models, registry, lookup]
"""

import pytest

from aiflow.models.metadata import ModelMetadata, ModelType
from aiflow.models.registry import ModelRegistry


@pytest.fixture
def reg():
    r = ModelRegistry()
    r.register(
        ModelMetadata(
            name="openai/gpt-4o",
            model_type=ModelType.LLM,
            provider="openai",
            priority=10,
            fallback_model="openai/gpt-4o-mini",
        )
    )
    r.register(
        ModelMetadata(
            name="openai/gpt-4o-mini", model_type=ModelType.LLM, provider="openai", priority=20
        )
    )
    r.register(
        ModelMetadata(
            name="openai/text-embedding-3-small",
            model_type=ModelType.EMBEDDING,
            provider="openai",
            priority=10,
        )
    )
    return r


class TestModelRegistry:
    def test_register_and_get(self, reg):
        meta = reg.get("openai/gpt-4o")
        assert meta.provider == "openai"

    def test_get_missing_raises(self, reg):
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_find_by_type_llm(self, reg):
        llms = reg.find_by_type(ModelType.LLM)
        assert len(llms) == 2
        assert llms[0].name == "openai/gpt-4o"  # lower priority number = first

    def test_find_by_type_embedding(self, reg):
        embeddings = reg.find_by_type(ModelType.EMBEDDING)
        assert len(embeddings) == 1

    def test_get_fallback(self, reg):
        fb = reg.get_fallback("openai/gpt-4o")
        assert fb is not None
        assert fb.name == "openai/gpt-4o-mini"

    def test_get_fallback_none(self, reg):
        fb = reg.get_fallback("openai/gpt-4o-mini")
        assert fb is None

    def test_list_all(self, reg):
        assert len(reg.list_all()) == 3

    def test_len(self, reg):
        assert len(reg) == 3
