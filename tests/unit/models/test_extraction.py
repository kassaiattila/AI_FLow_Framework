"""
@test_registry:
    suite: models-unit
    component: models.protocols.extraction
    covers: [src/aiflow/models/protocols/extraction.py]
    phase: 2
    priority: medium
    estimated_duration_ms: 50
    requires_services: []
    tags: [models, protocols, extraction, ner]
"""
from aiflow.models.protocols.extraction import ExtractionEntity, ExtractionInput, ExtractionOutput

class TestExtractionModels:
    def test_entity(self):
        e = ExtractionEntity(text="Budapest", label="LOCATION")
        assert e.confidence == 1.0
        assert e.start is None

    def test_entity_with_span(self):
        e = ExtractionEntity(text="John", label="PERSON", start=0, end=4, confidence=0.98)
        assert e.end == 4

    def test_input(self):
        inp = ExtractionInput(text="John lives in Budapest")
        assert inp.entity_types is None

    def test_output(self):
        out = ExtractionOutput(entities=[
            ExtractionEntity(text="John", label="PERSON"),
            ExtractionEntity(text="Budapest", label="LOCATION"),
        ])
        assert len(out.entities) == 2
