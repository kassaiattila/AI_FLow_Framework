"""
@test_registry:
    suite: core-unit
    component: models.metadata
    covers: [src/aiflow/models/metadata.py]
    phase: 1
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [models, metadata, enums]
"""
from aiflow.models.metadata import ModelType, ModelLifecycle, ServingMode, ModelMetadata


class TestModelType:
    def test_values(self):
        assert ModelType.LLM == "llm"
        assert ModelType.EMBEDDING == "embedding"
        assert ModelType.VISION == "vision"
        assert ModelType.SPEECH_TO_TEXT == "speech_to_text"

class TestModelLifecycle:
    def test_progression(self):
        stages = [ModelLifecycle.REGISTERED, ModelLifecycle.TESTED,
                  ModelLifecycle.STAGING, ModelLifecycle.PRODUCTION,
                  ModelLifecycle.DEPRECATED, ModelLifecycle.RETIRED]
        assert len(stages) == 6

class TestModelMetadata:
    def test_defaults(self):
        meta = ModelMetadata(name="openai/gpt-4o", model_type=ModelType.LLM,
                             provider="openai", version="latest")
        assert meta.lifecycle == ModelLifecycle.REGISTERED
        assert meta.serving_mode == ServingMode.API
        assert meta.cost_per_input_token == 0.0
        assert meta.priority == 100
        assert meta.tags == []

    def test_full_metadata(self):
        meta = ModelMetadata(
            name="openai/gpt-4o", model_type=ModelType.LLM,
            provider="openai", version="2024-05-13",
            lifecycle=ModelLifecycle.PRODUCTION, serving_mode=ServingMode.API,
            cost_per_input_token=0.000005, cost_per_output_token=0.000015,
            priority=10, fallback_model="openai/gpt-4o-mini",
            capabilities=["chat", "json_mode", "function_calling"],
            tags=["production", "primary"],
        )
        assert meta.fallback_model == "openai/gpt-4o-mini"
        assert "chat" in meta.capabilities
