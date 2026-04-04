"""
@test_registry:
    suite: engine-unit
    component: engine.serialization
    covers: [src/aiflow/engine/serialization.py]
    phase: 2
    priority: medium
    estimated_duration_ms: 200
    requires_services: []
    tags: [engine, serialization, yaml, export, import]
"""
import pytest
import yaml

from aiflow.engine.dag import DAG
from aiflow.engine.serialization import deserialize_dag_structure, serialize_workflow


class TestSerializeWorkflow:
    def test_basic_serialization(self):
        dag = DAG()
        dag.add_node("step_a")
        dag.add_node("step_b")
        dag.add_edge("step_a", "step_b")
        result = serialize_workflow("test-wf", "1.0.0", dag)
        assert "test-wf" in result
        assert "1.0.0" in result
        data = yaml.safe_load(result)
        assert len(data["steps"]) == 2
        assert len(data["edges"]) == 1

    def test_serialization_with_skill(self):
        dag = DAG()
        dag.add_node("a")
        result = serialize_workflow("wf", "1.0", dag, skill="my_skill")
        data = yaml.safe_load(result)
        assert data["workflow"]["skill"] == "my_skill"

    def test_terminal_node_serialized(self):
        dag = DAG()
        dag.add_node("end", is_terminal=True)
        result = serialize_workflow("wf", "1.0", dag)
        data = yaml.safe_load(result)
        assert data["steps"][0]["terminal"] is True

    def test_max_iterations_serialized(self):
        dag = DAG()
        dag.add_node("review", max_iterations=3)
        result = serialize_workflow("wf", "1.0", dag)
        data = yaml.safe_load(result)
        assert data["steps"][0]["max_iterations"] == 3

    def test_conditional_edge_serialized(self):
        from aiflow.engine.conditions import Condition
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b", condition=Condition(expression="output.x == 1"))
        result = serialize_workflow("wf", "1.0", dag)
        data = yaml.safe_load(result)
        assert data["edges"][0]["condition"] == "output.x == 1"


class TestDeserializeDagStructure:
    def test_basic_deserialization(self):
        yaml_str = """
workflow:
  name: test-wf
  version: "1.0.0"
steps:
  - name: step_a
  - name: step_b
edges:
  - from: step_a
    to: step_b
"""
        result = deserialize_dag_structure(yaml_str)
        assert result["workflow"]["name"] == "test-wf"
        assert len(result["steps"]) == 2
        assert len(result["edges"]) == 1

    def test_invalid_yaml_missing_workflow(self):
        with pytest.raises(ValueError, match="missing 'workflow'"):
            deserialize_dag_structure("steps: []")

    def test_invalid_yaml_missing_steps(self):
        with pytest.raises(ValueError, match="missing 'steps'"):
            deserialize_dag_structure("workflow: {name: x}")

    def test_roundtrip(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        yaml_str = serialize_workflow("roundtrip", "1.0", dag)
        structure = deserialize_dag_structure(yaml_str)
        assert structure["workflow"]["name"] == "roundtrip"
        assert len(structure["steps"]) == 2
