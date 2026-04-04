"""
@test_registry:
    suite: engine-unit
    component: engine.dag
    covers: [src/aiflow/engine/dag.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 300
    requires_services: []
    tags: [engine, dag, topological-sort, validation, graph]
"""
import pytest

from aiflow.engine.conditions import Condition
from aiflow.engine.dag import DAG, DAGValidationError


class TestDAGNodeManagement:
    def test_add_node(self):
        dag = DAG()
        dag.add_node("step_a")
        assert "step_a" in dag.nodes
        assert dag.node_count == 1

    def test_add_duplicate_node_raises(self):
        dag = DAG()
        dag.add_node("step_a")
        with pytest.raises(ValueError, match="already exists"):
            dag.add_node("step_a")

    def test_get_node(self):
        dag = DAG()
        dag.add_node("step_a", is_terminal=True)
        node = dag.get_node("step_a")
        assert node.name == "step_a"
        assert node.is_terminal is True

    def test_get_missing_node_raises(self):
        dag = DAG()
        with pytest.raises(KeyError):
            dag.get_node("nonexistent")

    def test_node_with_max_iterations(self):
        dag = DAG()
        dag.add_node("review", max_iterations=3)
        assert dag.get_node("review").max_iterations == 3


class TestDAGEdgeManagement:
    def test_add_edge(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert dag.edge_count == 1
        assert dag.get_successors("a") == ["b"]
        assert dag.get_predecessors("b") == ["a"]

    def test_add_edge_missing_source_raises(self):
        dag = DAG()
        dag.add_node("b")
        with pytest.raises(ValueError, match="Source node"):
            dag.add_edge("a", "b")

    def test_add_edge_missing_target_raises(self):
        dag = DAG()
        dag.add_node("a")
        with pytest.raises(ValueError, match="Target node"):
            dag.add_edge("a", "b")

    def test_conditional_edge(self):
        dag = DAG()
        dag.add_node("classify")
        dag.add_node("process")
        cond = Condition(expression="output.category == 'process'")
        dag.add_edge("classify", "process", condition=cond)
        edges = dag.get_edges_from("classify")
        assert len(edges) == 1
        assert edges[0].condition is not None


class TestDAGTopologicalSort:
    def test_linear_sort(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_node("c")
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        assert dag.topological_sort() == ["a", "b", "c"]

    def test_branching_sort(self):
        dag = DAG()
        dag.add_node("start")
        dag.add_node("branch_a")
        dag.add_node("branch_b")
        dag.add_node("join")
        dag.add_edge("start", "branch_a")
        dag.add_edge("start", "branch_b")
        dag.add_edge("branch_a", "join")
        dag.add_edge("branch_b", "join")
        result = dag.topological_sort()
        assert result.index("start") < result.index("branch_a")
        assert result.index("start") < result.index("branch_b")
        assert result.index("branch_a") < result.index("join")

    def test_cycle_detection(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_node("c")
        dag.add_edge("a", "b")
        dag.add_edge("b", "c")
        dag.add_edge("c", "a")  # true cycle
        with pytest.raises(DAGValidationError, match="Cycle"):
            dag.topological_sort()

    def test_controlled_loop_allowed(self):
        dag = DAG()
        dag.add_node("extract")
        dag.add_node("review", max_iterations=3)
        dag.add_node("refine")
        dag.add_edge("extract", "review")
        dag.add_edge("review", "refine")
        dag.add_edge("refine", "review")  # loop back, allowed because review.max_iterations=3
        result = dag.topological_sort()
        assert "extract" in result
        assert "review" in result


class TestDAGRootAndTerminal:
    def test_root_nodes(self):
        dag = DAG()
        dag.add_node("start")
        dag.add_node("middle")
        dag.add_node("end")
        dag.add_edge("start", "middle")
        dag.add_edge("middle", "end")
        assert dag.get_root_nodes() == ["start"]

    def test_terminal_nodes(self):
        dag = DAG()
        dag.add_node("start")
        dag.add_node("end", is_terminal=True)
        dag.add_edge("start", "end")
        assert "end" in dag.get_terminal_nodes()

    def test_leaf_nodes_are_terminal(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert "b" in dag.get_terminal_nodes()


class TestDAGReadySteps:
    def test_root_is_ready(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert dag.get_ready_steps(set()) == ["a"]

    def test_step_ready_after_predecessor(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert dag.get_ready_steps({"a"}) == ["b"]

    def test_join_waits_for_all(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_node("join")
        dag.add_edge("a", "join")
        dag.add_edge("b", "join")
        assert dag.get_ready_steps({"a"}) == ["b"]  # join not ready yet
        assert "join" in dag.get_ready_steps({"a", "b"})  # now ready


class TestDAGValidation:
    def test_empty_dag(self):
        dag = DAG()
        errors = dag.validate()
        assert any("no nodes" in e for e in errors)

    def test_valid_linear_dag(self):
        dag = DAG()
        dag.add_node("a")
        dag.add_node("b")
        dag.add_edge("a", "b")
        assert dag.validate() == []

    def test_unreachable_node(self):
        # orphan_a <-> orphan_b form a cycle, so neither is a root.
        # They are unreachable from the only root ("root").
        dag = DAG()
        dag.add_node("root")
        dag.add_node("step1")
        dag.add_node("orphan_a")
        dag.add_node("orphan_b")
        dag.add_edge("root", "step1")
        dag.add_edge("orphan_a", "orphan_b")
        dag.add_edge("orphan_b", "orphan_a")
        errors = dag.validate()
        assert any("Unreachable" in e or "Cycle" in e for e in errors)

    def test_repr(self):
        dag = DAG()
        dag.add_node("a")
        assert "nodes=1" in repr(dag)
