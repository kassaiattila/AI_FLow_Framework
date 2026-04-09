"""
@test_registry:
    suite: pipeline-unit
    component: pipeline.parser
    covers: [src/aiflow/pipeline/parser.py]
    phase: C2
    priority: critical
    estimated_duration_ms: 200
    requires_services: []
    tags: [pipeline, parser, yaml]
"""

from __future__ import annotations

import pytest

from aiflow.pipeline.parser import PipelineParseError, PipelineParser

VALID_YAML = """
name: test_pipeline
version: "1.0.0"
trigger:
  type: manual
steps:
  - name: fetch
    service: email_connector
    method: fetch_emails
    config:
      connector_id: "{{ input.connector_id }}"
  - name: classify
    service: classifier
    method: classify
    depends_on: [fetch]
    for_each: "{{ fetch.output.emails }}"
    config:
      text: "{{ item.body }}"
"""

MINIMAL_YAML = """
name: minimal
steps:
  - name: step1
    service: svc
    method: meth
"""


@pytest.fixture
def parser():
    return PipelineParser()


class TestParseYaml:
    def test_valid_yaml(self, parser):
        p = parser.parse_yaml(VALID_YAML)
        assert p.name == "test_pipeline"
        assert len(p.steps) == 2
        assert p.steps[1].depends_on == ["fetch"]
        assert p.steps[1].for_each is not None

    def test_minimal_yaml(self, parser):
        p = parser.parse_yaml(MINIMAL_YAML)
        assert p.name == "minimal"
        assert len(p.steps) == 1

    def test_invalid_yaml_syntax(self, parser):
        with pytest.raises(PipelineParseError, match="Invalid YAML"):
            parser.parse_yaml("{{invalid: yaml: [[")

    def test_yaml_not_a_dict(self, parser):
        with pytest.raises(PipelineParseError, match="must be a mapping"):
            parser.parse_yaml("- just\n- a\n- list")

    def test_missing_name(self, parser):
        with pytest.raises(PipelineParseError):
            parser.parse_yaml("steps:\n  - name: s\n    service: a\n    method: b")

    def test_missing_steps(self, parser):
        with pytest.raises(PipelineParseError):
            parser.parse_yaml("name: p")

    def test_empty_steps(self, parser):
        with pytest.raises(PipelineParseError):
            parser.parse_yaml("name: p\nsteps: []")


class TestParseDict:
    def test_valid_dict(self, parser):
        p = parser.parse_dict(
            {
                "name": "dict_pipeline",
                "steps": [{"name": "s1", "service": "a", "method": "b"}],
            }
        )
        assert p.name == "dict_pipeline"

    def test_invalid_dict(self, parser):
        with pytest.raises(PipelineParseError):
            parser.parse_dict({"name": "p"})


class TestCrossValidation:
    def test_unknown_dependency(self, parser):
        with pytest.raises(PipelineParseError, match="unknown step"):
            parser.parse_yaml("""
name: bad
steps:
  - name: s1
    service: a
    method: b
    depends_on: [nonexistent]
""")

    def test_self_dependency(self, parser):
        with pytest.raises(PipelineParseError, match="depend on itself"):
            parser.parse_yaml("""
name: bad
steps:
  - name: s1
    service: a
    method: b
    depends_on: [s1]
""")


class TestParseFile:
    def test_file_not_found(self, parser):
        with pytest.raises(PipelineParseError, match="not found"):
            parser.parse_file("/nonexistent/pipeline.yaml")

    def test_wrong_extension(self, parser, tmp_path):
        f = tmp_path / "pipeline.txt"
        f.write_text("name: p\nsteps:\n  - name: s\n    service: a\n    method: b")
        with pytest.raises(PipelineParseError, match="Expected .yaml"):
            parser.parse_file(f)

    def test_valid_file(self, parser, tmp_path):
        f = tmp_path / "pipeline.yaml"
        f.write_text(VALID_YAML)
        p = parser.parse_file(f)
        assert p.name == "test_pipeline"
