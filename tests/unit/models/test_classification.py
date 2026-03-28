"""
@test_registry:
    suite: models-unit
    component: models.protocols.classification
    covers: [src/aiflow/models/protocols/classification.py]
    phase: 2
    priority: medium
    estimated_duration_ms: 50
    requires_services: []
    tags: [models, protocols, classification]
"""
from aiflow.models.protocols.classification import ClassificationInput, ClassificationOutput, ClassificationResult

class TestClassificationModels:
    def test_input(self):
        inp = ClassificationInput(text="Hello world")
        assert inp.multi_label is False
        assert inp.labels is None

    def test_input_zero_shot(self):
        inp = ClassificationInput(text="test", labels=["pos", "neg"])
        assert len(inp.labels) == 2

    def test_result(self):
        r = ClassificationResult(label="positive", confidence=0.95)
        assert r.all_scores == {}

    def test_output(self):
        out = ClassificationOutput(results=[
            ClassificationResult(label="pos", confidence=0.9),
            ClassificationResult(label="neg", confidence=0.1),
        ])
        assert len(out.results) == 2
