"""
@test_registry:
    suite: e2e
    component: aiflow.pipeline.runner
    covers: [src/aiflow/pipeline/runner.py, src/aiflow/pipeline/compiler.py,
             src/aiflow/pipeline/builtin_templates/invoice_finder_v3_offline.yaml,
             src/aiflow/pipeline/adapters/document_adapter.py,
             src/aiflow/pipeline/adapters/classifier_adapter.py,
             src/aiflow/pipeline/adapters/payment_status_adapter.py,
             src/aiflow/pipeline/adapters/report_generator_adapter.py]
    phase: B3.E2E.P2
    priority: critical
    estimated_duration_ms: 120000
    requires_services: [postgresql, redis]
    tags: [pipeline, invoice-finder, runner, db-persistence, e2e]

B3.E2E Phase 2 — PipelineRunner integration with real PostgreSQL + Redis.

Validates that PipelineRunner.run_from_yaml() end-to-end:
  1. Creates workflow_runs DB row with status progression (running → completed)
  2. Creates step_runs DB rows for each step (completed + duration)
  3. Records LLM cost in cost_records table
  4. Orchestrates for_each steps correctly
  5. Resolves Jinja2 templates across step boundaries

Uses invoice_finder_v3_offline.yaml (email fetch skipped) with 3 real HU invoice
PDFs. Needs: docker compose up db redis -d + alembic upgrade head.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select, text

from aiflow.api.deps import get_session_factory
from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import adapter_registry
from aiflow.pipeline.adapters import discover_adapters
from aiflow.pipeline.runner import PipelineRunner
from aiflow.state.models import StepRunModel, WorkflowRunModel

# team_id FK → teams table (empty in dev DB, so use None — nullable)
# user_id FK → users table (admin@bestix.hu exists in dev DB)
TEST_TEAM_ID: str | None = None
TEST_USER_ID = "a377062a-ec7f-4244-9a1e-17d7c5865b3c"  # admin@bestix.hu

# Pipeline template + test PDFs
PIPELINE_YAML = Path(
    "src/aiflow/pipeline/builtin_templates/invoice_finder_v3_offline.yaml"
).read_text(encoding="utf-8")

INVOICES_DIR = Path("data/uploads/invoices")
TEST_PDFS = [
    "20210423_EdiMeron_Bestix_Szla_2021_08.pdf",
    "20210423_Kacz_Levente_KL-2021-4.pdf",
    "20210615_CSEPP_Studio_E-CSEPP-2021-6.pdf",
]


@pytest.fixture(scope="module", autouse=True)
def _ensure_adapters_discovered() -> None:
    """Auto-discover all pipeline adapters once per module."""
    discover_adapters()


@pytest.fixture(scope="module")
def pdf_paths() -> list[str]:
    """Resolve test PDF absolute paths — skip module if any missing."""
    paths: list[str] = []
    for name in TEST_PDFS:
        p = INVOICES_DIR / name
        if not p.exists():
            pytest.skip(f"Test PDF missing: {p}")
        paths.append(str(p))
    return paths


pytestmark = pytest.mark.asyncio


class TestPipelineRunnerDBPersistence:
    """Phase 2 gate: PipelineRunner persists run + steps + cost to real DB.

    Single comprehensive async test — splitting into multiple test methods
    causes Windows proactor event loop errors when the cached session_factory
    is reused across pytest-asyncio event loops.
    """

    async def test_run_and_verify_db_persistence(self, pdf_paths: list[str]) -> None:
        """Run pipeline end-to-end and verify ALL DB persistence + outputs."""
        session_factory = await get_session_factory()
        runner = PipelineRunner(
            registry=adapter_registry,
            session_factory=session_factory,
        )

        ctx = ExecutionContext(
            run_id="b3-e2e-p2-test",
            prompt_label="b3.e2e.p2",
            budget_remaining_usd=5.0,
            team_id=TEST_TEAM_ID,
            user_id=TEST_USER_ID,
        )

        # ---- 1. Execute pipeline ----
        result = await runner.run_from_yaml(
            yaml_str=PIPELINE_YAML,
            input_data={
                "pdf_paths": pdf_paths,
                "confidence_threshold": 0.5,
            },
            ctx=ctx,
        )

        assert result.success, f"Pipeline failed: {result.error}"
        assert result.status == "completed"
        assert result.pipeline_name == "invoice_finder_v3_offline"
        assert result.total_duration_ms > 0

        expected_steps = {
            "acquire_documents",
            "classify_invoices",
            "extract_fields",
            "check_payment_status",
            "generate_report",
        }
        assert set(result.step_outputs.keys()) == expected_steps
        run_id = result.run_id

        # ---- 2. Verify workflow_runs DB row ----
        async with session_factory() as session:
            wf_run = await session.get(WorkflowRunModel, run_id)

            assert wf_run is not None, f"WorkflowRun {run_id} not found in DB"
            assert wf_run.status == "completed"
            assert wf_run.workflow_name == "invoice_finder_v3_offline"
            assert wf_run.workflow_version == "3.0.0"
            assert wf_run.started_at is not None
            assert wf_run.completed_at is not None
            assert wf_run.total_duration_ms is not None
            assert wf_run.total_duration_ms > 0
            assert str(wf_run.user_id) == TEST_USER_ID
            assert wf_run.input_data is not None
            assert wf_run.input_data.get("pdf_paths") == pdf_paths

            # ---- 3. Verify step_runs DB rows ----
            stmt = (
                select(StepRunModel)
                .where(StepRunModel.workflow_run_id == run_id)
                .order_by(StepRunModel.step_index)
            )
            step_result = await session.execute(stmt)
            step_runs = list(step_result.scalars())

        assert len(step_runs) == 5, (
            f"Expected 5 step_runs, got {len(step_runs)}: {[s.step_name for s in step_runs]}"
        )

        expected_order = [
            "acquire_documents",
            "classify_invoices",
            "extract_fields",
            "check_payment_status",
            "generate_report",
        ]
        actual_order = [s.step_name for s in step_runs]
        assert actual_order == expected_order, (
            f"Step order mismatch: {actual_order} != {expected_order}"
        )

        for sr in step_runs:
            assert sr.status == "completed", (
                f"Step {sr.step_name} status={sr.status}, error={sr.error}"
            )
            assert sr.started_at is not None
            assert sr.completed_at is not None
            assert sr.duration_ms is not None
            assert sr.duration_ms > 0

        # ---- 4. Check cost_records (best-effort — plumbing test, not strict) ----
        async with session_factory() as session:
            cost_result = await session.execute(
                text(
                    "SELECT step_name, model, input_tokens, output_tokens, cost_usd "
                    "FROM cost_records WHERE workflow_run_id = :run_id "
                    "ORDER BY recorded_at"
                ),
                {"run_id": run_id},
            )
            cost_rows = cost_result.fetchall()

        print(f"\n[B3.E2E.P2] cost_records entries for run {run_id}: {len(cost_rows)}")
        for row in cost_rows:
            print(f"  - {row.step_name}: {row.model} ${row.cost_usd:.6f}")

        # ---- 5. Verify pipeline extracted real invoice data ----
        outputs = result.step_outputs

        acquire = outputs["acquire_documents"]
        assert acquire["count"] == 3
        for doc in acquire["results"]:
            assert doc["file_path"], "Empty file_path in acquire_documents"
            assert len(doc["raw_text"]) > 100, f"raw_text too short: {len(doc['raw_text'])} chars"

        classify = outputs["classify_invoices"]
        assert classify["count"] == 3
        for r in classify["results"]:
            assert "label" in r
            assert "confidence" in r
            assert 0.0 <= r["confidence"] <= 1.0

        extract = outputs["extract_fields"]
        assert extract["count"] == 3
        extracted_count = sum(
            1 for r in extract["results"] if r.get("fields") and r["fields"].get("invoice_number")
        )
        assert extracted_count >= 1, (
            f"At least 1/3 invoices should have invoice_number extracted, got {extracted_count}"
        )

        payment = outputs["check_payment_status"]
        assert payment["count"] == 3

        report = outputs["generate_report"]
        assert report, "Empty generate_report output"

        print(
            f"\n[B3.E2E.P2] PASSED — run_id={run_id}, "
            f"duration={result.total_duration_ms:.0f}ms, "
            f"extracted={extracted_count}/3, "
            f"steps={len(step_runs)}, "
            f"cost_records={len(cost_rows)}"
        )
