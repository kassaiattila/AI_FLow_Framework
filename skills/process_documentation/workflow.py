"""Process Documentation workflow - BPMN extraction pipeline.

TODO: Implement full workflow steps:
  1. classify_intent - Determine if input describes a process
  2. elaborate - Expand natural language into structured form
  3. extract - Extract BPMN elements (tasks, gateways, events)
  4. review - Quality gate for completeness and correctness
  5. generate_diagram - Produce Mermaid flowchart output
"""
from aiflow.engine.workflow import workflow, WorkflowBuilder


@workflow(name="process-documentation", version="2.0.0", skill="process_documentation")
def process_documentation(wf: WorkflowBuilder) -> None:
    """Natural language -> structured BPMN documentation + diagrams."""
    # TODO: Register steps
    # wf.step(classify_intent)
    # wf.branch(on="classify_intent", when={
    #     "output.category == 'process'": ["elaborate"],
    # }, otherwise="reject")
    # wf.step(elaborate, depends_on=["classify_intent"])
    # wf.step(extract, depends_on=["elaborate"])
    # wf.step(review, depends_on=["extract"])
    # wf.step(generate_diagram, depends_on=["review"])
    # wf.join(["generate_diagram"], into="assemble_output")
    pass
