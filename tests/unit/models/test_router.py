"""
@test_registry:
    suite: models-unit
    component: models.router
    covers: [src/aiflow/models/router.py]
    phase: 2
    priority: high
    estimated_duration_ms: 200
    requires_services: []
    tags: [models, router, routing, fallback]
"""
import pytest

from aiflow.models.metadata import ModelMetadata, ModelType
from aiflow.models.registry import ModelRegistry
from aiflow.models.router import ModelRouter, RoutingStrategy


@pytest.fixture
def registry():
    reg = ModelRegistry()
    reg.register(ModelMetadata(name="openai/gpt-4o", model_type=ModelType.LLM, provider="openai",
                               priority=10, cost_per_input_token=0.0000025, cost_per_output_token=0.00001,
                               avg_latency_ms=800, fallback_model="openai/gpt-4o-mini",
                               capabilities=["chat", "json_mode"]))
    reg.register(ModelMetadata(name="openai/gpt-4o-mini", model_type=ModelType.LLM, provider="openai",
                               priority=20, cost_per_input_token=0.00000015, cost_per_output_token=0.0000006,
                               avg_latency_ms=400, capabilities=["chat", "json_mode"]))
    reg.register(ModelMetadata(name="openai/text-embedding-3-small", model_type=ModelType.EMBEDDING,
                               provider="openai", priority=10, cost_per_input_token=0.00000002))
    return reg

@pytest.fixture
def router(registry):
    return ModelRouter(registry)

class TestModelRouter:
    def test_fallback_chain_route(self, router):
        result = router.route(ModelType.LLM)
        assert result is not None
        assert result.name == "openai/gpt-4o"  # lowest priority number

    def test_cost_optimized(self, router):
        result = router.route(ModelType.LLM, strategy=RoutingStrategy.COST_OPTIMIZED)
        assert result.name == "openai/gpt-4o-mini"  # cheapest

    def test_latency_optimized(self, router):
        result = router.route(ModelType.LLM, strategy=RoutingStrategy.LATENCY_OPTIMIZED)
        assert result.name == "openai/gpt-4o-mini"  # lowest latency

    def test_preferred_model(self, router):
        result = router.route(ModelType.LLM, preferred_model="openai/gpt-4o-mini")
        assert result.name == "openai/gpt-4o-mini"

    def test_no_model_found(self, router):
        result = router.route(ModelType.VISION)
        assert result is None

    def test_capability_filter(self, router):
        result = router.route(ModelType.LLM, required_capability="json_mode")
        assert result is not None

    def test_capability_filter_no_match(self, router):
        result = router.route(ModelType.LLM, required_capability="nonexistent")
        assert result is None

    def test_get_fallback_chain(self, router):
        chain = router.get_fallback_chain("openai/gpt-4o")
        assert len(chain) == 2
        assert chain[0].name == "openai/gpt-4o"
        assert chain[1].name == "openai/gpt-4o-mini"

    def test_route_with_fallback(self, router):
        result = router.route_with_fallback("openai/gpt-4o")
        assert result is not None
        assert result.name == "openai/gpt-4o"

    def test_route_embedding(self, router):
        result = router.route(ModelType.EMBEDDING)
        assert result is not None
        assert result.name == "openai/text-embedding-3-small"
