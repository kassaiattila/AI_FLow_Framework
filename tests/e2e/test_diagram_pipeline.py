"""
@test_registry:
    suite: e2e
    component: aiflow.pipeline.runner + services.diagram_generator
    covers: [src/aiflow/services/diagram_generator/service.py,
             src/aiflow/services/diagram_generator/prompts/diagram_planner.yaml,
             src/aiflow/services/diagram_generator/prompts/mermaid_generator.yaml,
             src/aiflow/services/diagram_generator/prompts/diagram_reviewer.yaml,
             src/aiflow/pipeline/adapters/diagram_adapter.py,
             src/aiflow/pipeline/builtin_templates/diagram_generator_v1.yaml]
    phase: B5.1.E2E
    priority: high
    estimated_duration_ms: 90000
    requires_services: [postgresql, kroki, openai]
    tags: [pipeline, diagram-generator, e2e, b5, real-llm]

B5.1 E2E — DiagramGeneratorService end-to-end through PipelineRunner.

Validates all three diagram semantics against the real LLM + real DB:
  1. flowchart      — legacy process_documentation skill path
  2. sequence       — new planner + mermaid + reviewer prompts
  3. bpmn_swimlane  — new planner + mermaid + reviewer prompts (swimlane layout)

Single comprehensive async test with 3 inline scenarios. Splitting into
multiple test methods triggers asyncpg "another operation is in progress"
errors because the cached session_factory is reused across the per-function
event loops — same workaround as tests/e2e/test_invoice_finder_pipeline_runner.py.

Needs: docker compose up db kroki -d + alembic upgrade head + OPENAI_API_KEY set.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import text

from aiflow.api.deps import get_session_factory
from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import adapter_registry
from aiflow.pipeline.adapters import discover_adapters
from aiflow.pipeline.runner import PipelineRunner

pytestmark = pytest.mark.asyncio

TEST_USER_ID = "a377062a-ec7f-4244-9a1e-17d7c5865b3c"  # admin@bestix.hu

PIPELINE_YAML = Path("src/aiflow/pipeline/builtin_templates/diagram_generator_v1.yaml").read_text(
    encoding="utf-8"
)


@pytest.fixture(scope="module", autouse=True)
def _require_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — real LLM E2E test cannot run.")


@pytest.fixture(scope="module", autouse=True)
def _ensure_adapters_discovered() -> None:
    """Auto-discover all pipeline adapters once per module."""
    discover_adapters()


async def _run_diagram_pipeline(
    runner: PipelineRunner,
    session_factory,
    description: str,
    diagram_type: str,
) -> tuple[str, str]:
    """Execute the diagram_generator_v1 pipeline end-to-end.

    Returns (mermaid_code, run_id) for downstream assertions.
    """
    ctx = ExecutionContext(
        prompt_label="b5.e2e",
        budget_remaining_usd=2.0,
        user_id=TEST_USER_ID,
    )

    result = await runner.run_from_yaml(
        yaml_str=PIPELINE_YAML,
        input_data={
            "description": description,
            "diagram_type": diagram_type,
        },
        ctx=ctx,
    )

    assert result.success, f"Pipeline failed for {diagram_type}: {result.error}"
    assert result.status == "completed"
    assert result.pipeline_name == "diagram_generator_v1"
    assert "generate_diagram" in result.step_outputs

    step_out = result.step_outputs["generate_diagram"]
    mermaid_code = step_out.get("mermaid_code") or ""
    assert mermaid_code, f"Empty mermaid_code for {diagram_type}"

    # Verify DB persistence of the generated_diagrams row.
    diagram_id = step_out.get("diagram_id")
    assert diagram_id, "Missing diagram_id in step output"

    async with session_factory() as session:
        row = (
            await session.execute(
                text("SELECT id, user_input, mermaid_code FROM generated_diagrams WHERE id = :id"),
                {"id": diagram_id},
            )
        ).fetchone()

    assert row is not None, f"generated_diagrams row not persisted for {diagram_id}"
    assert row.mermaid_code == mermaid_code

    return mermaid_code, result.run_id


class TestDiagramPipelineE2E:
    """B5.1 E2E gate — real LLM + real DB + real Kroki."""

    async def test_run_and_verify_all_three_diagram_types(self) -> None:
        """Single comprehensive test covering flowchart + sequence + swimlane.

        Each scenario exercises a full PipelineRunner → DiagramGeneratorService
        round-trip including DB persistence and mermaid syntax assertions.
        """
        session_factory = await get_session_factory()
        runner = PipelineRunner(
            registry=adapter_registry,
            session_factory=session_factory,
        )

        # ---- Scenario 1: flowchart (legacy process_documentation path) ----
        flowchart_desc = (
            "Customer submits an order on the webshop. The system validates "
            "stock availability. If stock is available, the payment is "
            "processed and the order is shipped. Otherwise the customer is "
            "notified that the product is out of stock."
        )
        flowchart_mermaid, flowchart_run = await _run_diagram_pipeline(
            runner, session_factory, flowchart_desc, "flowchart"
        )
        header_ok = flowchart_mermaid.strip().startswith(
            "flowchart"
        ) or flowchart_mermaid.strip().startswith("graph")
        assert header_ok, f"Unexpected flowchart header: {flowchart_mermaid[:80]!r}"
        print(f"\n[B5.1.E2E] flowchart OK run={flowchart_run} len={len(flowchart_mermaid)}")

        # ---- Scenario 2: sequence (new prompt path) ----
        sequence_desc = (
            "Authentication flow: user submits login credentials to the "
            "frontend. The frontend calls the backend /auth endpoint. The "
            "backend queries the database for the user, receives the user "
            "row, and returns a JWT token to the frontend. Finally the "
            "frontend redirects the user to the dashboard."
        )
        sequence_mermaid, sequence_run = await _run_diagram_pipeline(
            runner, session_factory, sequence_desc, "sequence"
        )
        assert sequence_mermaid.strip().startswith("sequenceDiagram"), (
            f"Expected sequenceDiagram header, got: {sequence_mermaid[:80]!r}"
        )
        assert "participant" in sequence_mermaid, "Sequence diagram must declare participants"
        assert "->>" in sequence_mermaid, "Sequence diagram must use sync arrows"
        print(f"\n[B5.1.E2E] sequence OK run={sequence_run} len={len(sequence_mermaid)}")

        # ---- Scenario 3: bpmn_swimlane (new prompt path) ----
        swimlane_desc = (
            "Employee onboarding: HR creates the employment contract and "
            "sends a welcome email. In parallel, IT creates the user "
            "account in Active Directory and provisions a laptop for the "
            "new hire. Once both HR and IT tasks are complete, the new "
            "hire joins the orientation session."
        )
        swimlane_mermaid, swimlane_run = await _run_diagram_pipeline(
            runner, session_factory, swimlane_desc, "bpmn_swimlane"
        )
        assert swimlane_mermaid.strip().startswith("flowchart LR"), (
            f"Expected 'flowchart LR' header, got: {swimlane_mermaid[:80]!r}"
        )
        assert "subgraph" in swimlane_mermaid, "Swimlane diagram must use subgraph lanes"
        print(f"\n[B5.1.E2E] bpmn_swimlane OK run={swimlane_run} len={len(swimlane_mermaid)}")

        # ---- Final gate: 3 runs created, 3 generated_diagrams rows persisted ----
        assert flowchart_run != sequence_run != swimlane_run
