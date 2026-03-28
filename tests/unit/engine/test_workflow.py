"""
@test_registry:
    suite: engine-unit
    component: engine.workflow
    covers: [src/aiflow/engine/workflow.py]
    phase: 2
    priority: critical
    estimated_duration_ms: 500
    requires_services: []
    tags: [engine, workflow, builder, decorator]
"""
import pytest
from aiflow.engine.step import step
from aiflow.engine.workflow import workflow, WorkflowBuilder, WorkflowDefinition, Workflow
from aiflow.engine.dag import DAGValidationError


# Sample steps for testing
@step(name="step_a")
async def step_a(data):
    return {"result": "a"}

@step(name="step_b")
async def step_b(data):
    return {"result": "b"}

@step(name="step_c")
async def step_c(data):
    return {"result": "c"}

@step(name="step_d")
async def step_d(data):
    return {"result": "d"}


class TestWorkflowBuilder:
    def test_add_step(self):
        builder = WorkflowBuilder()
        name = builder.step(step_a)
        assert name == "step_a"
        assert "step_a" in builder.dag.nodes

    def test_add_step_with_dependency(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b, depends_on=["step_a"])
        assert builder.dag.get_successors("step_a") == ["step_b"]

    def test_add_edge(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b)
        builder.edge("step_a", "step_b")
        assert "step_b" in builder.dag.get_successors("step_a")

    def test_conditional_edge(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b)
        builder.edge("step_a", "step_b", condition="output.score >= 8")
        edges = builder.dag.get_edges_from("step_a")
        assert len(edges) == 1
        assert edges[0].condition is not None

    def test_branch(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b)
        builder.step(step_c)
        builder.branch(on="step_a", when={
            "output.category == 'yes'": ["step_b"],
        }, otherwise="step_c")
        successors = builder.dag.get_successors("step_a")
        assert "step_b" in successors
        assert "step_c" in successors

    def test_join(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b)
        builder.step(step_c)
        builder.step(step_d)
        builder.edge("step_a", "step_b")
        builder.edge("step_a", "step_c")
        builder.join(["step_b", "step_c"], into="step_d")
        preds = builder.dag.get_predecessors("step_d")
        assert "step_b" in preds
        assert "step_c" in preds

    def test_terminal_step(self):
        builder = WorkflowBuilder()
        builder.step(step_a, terminal=True)
        assert builder.dag.get_node("step_a").is_terminal is True

    def test_validate_valid_dag(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b, depends_on=["step_a"])
        assert builder.validate() == []

    def test_build_returns_dag(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b, depends_on=["step_a"])
        dag = builder.build()
        assert dag.node_count == 2

    def test_build_raises_on_invalid(self):
        builder = WorkflowBuilder()
        # Empty DAG
        with pytest.raises(DAGValidationError):
            builder.build()

    def test_step_funcs_map(self):
        builder = WorkflowBuilder()
        builder.step(step_a)
        builder.step(step_b, depends_on=["step_a"])
        assert "step_a" in builder.step_funcs
        assert "step_b" in builder.step_funcs


class TestWorkflowDecorator:
    def test_creates_workflow(self):
        @workflow(name="test-wf", version="1.0.0")
        def my_workflow(wf: WorkflowBuilder):
            wf.step(step_a)
            wf.step(step_b, depends_on=["step_a"])

        assert isinstance(my_workflow, Workflow)
        assert my_workflow.name == "test-wf"
        assert my_workflow.version == "1.0.0"
        assert my_workflow.dag.node_count == 2

    def test_workflow_with_skill(self):
        @workflow(name="skill-wf", version="2.0.0", skill="process_doc")
        def my_workflow(wf: WorkflowBuilder):
            wf.step(step_a)

        assert my_workflow.definition.skill == "process_doc"

    def test_workflow_repr(self):
        @workflow(name="repr-test", version="1.0.0")
        def my_workflow(wf: WorkflowBuilder):
            wf.step(step_a)

        assert "repr-test" in repr(my_workflow)
        assert "v1.0.0" in repr(my_workflow)

    def test_workflow_with_branching(self):
        @workflow(name="branch-wf", version="1.0.0")
        def my_workflow(wf: WorkflowBuilder):
            wf.step(step_a)
            wf.step(step_b)
            wf.step(step_c)
            wf.branch(on="step_a", when={
                "output.category == 'yes'": ["step_b"],
            }, otherwise="step_c")

        assert my_workflow.dag.node_count == 3


class TestWorkflowDefinition:
    def test_defaults(self):
        defn = WorkflowDefinition(name="test")
        assert defn.version == "1.0.0"
        assert defn.complexity == "medium"
        assert defn.tags == []

    def test_full(self):
        defn = WorkflowDefinition(
            name="full", version="2.0.0", skill="my_skill",
            complexity="large", tags=["production"],
        )
        assert defn.skill == "my_skill"
