"""
@test_registry:
    suite: core-unit
    component: models.protocols
    covers: [src/aiflow/models/protocols/base.py, src/aiflow/models/protocols/generation.py, src/aiflow/models/protocols/embedding.py]
    phase: 1
    priority: high
    estimated_duration_ms: 100
    requires_services: []
    tags: [models, protocols, generation, embedding]
"""
from aiflow.models.protocols.base import ModelCallResult
from aiflow.models.protocols.embedding import EmbeddingInput, EmbeddingOutput
from aiflow.models.protocols.generation import GenerationInput, GenerationOutput


class TestModelCallResult:
    def test_defaults(self):
        r = ModelCallResult(output={"text": "hi"}, model_used="gpt-4o")
        assert r.input_tokens == 0
        assert r.cost_usd == 0.0
        assert r.cached is False

    def test_full(self):
        r = ModelCallResult(output="text", model_used="gpt-4o",
                            input_tokens=100, output_tokens=50,
                            cost_usd=0.005, latency_ms=1200, cached=False)
        assert r.input_tokens == 100

class TestGenerationInput:
    def test_defaults(self):
        inp = GenerationInput(messages=[{"role": "user", "content": "hello"}])
        assert inp.temperature == 0.7
        assert inp.max_tokens == 4096
        assert inp.response_model is None

class TestGenerationOutput:
    def test_defaults(self):
        out = GenerationOutput(text="Hello world")
        assert out.finish_reason == "stop"

class TestEmbeddingInput:
    def test_basic(self):
        inp = EmbeddingInput(texts=["hello", "world"])
        assert len(inp.texts) == 2

class TestEmbeddingOutput:
    def test_basic(self):
        out = EmbeddingOutput(embeddings=[[0.1, 0.2], [0.3, 0.4]], dimensions=2)
        assert out.dimensions == 2
        assert len(out.embeddings) == 2
