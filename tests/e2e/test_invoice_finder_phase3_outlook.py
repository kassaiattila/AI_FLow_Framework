"""
@test_registry:
    suite: e2e
    component: aiflow.pipeline.runner
    covers: [src/aiflow/pipeline/runner.py,
             src/aiflow/pipeline/compiler.py,
             src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml,
             src/aiflow/pipeline/adapters/email_adapter.py,
             src/aiflow/pipeline/adapters/document_adapter.py,
             src/aiflow/pipeline/adapters/classifier_adapter.py,
             src/aiflow/pipeline/adapters/payment_status_adapter.py,
             src/aiflow/pipeline/adapters/data_router_adapter.py,
             src/aiflow/pipeline/adapters/report_generator_adapter.py,
             src/aiflow/pipeline/adapters/notification_adapter.py,
             src/aiflow/services/email_connector/service.py]
    phase: B3.E2E.P3
    priority: critical
    estimated_duration_ms: 300000
    requires_services: [postgresql, redis, outlook_com]
    tags: [pipeline, invoice-finder, outlook, full-e2e, e2e]

B3.E2E Phase 3 — Full 8-step Invoice Finder pipeline on real Outlook COM mailboxes.

Runs invoice_finder_v3.yaml end-to-end for 3 accounts (bestix, kodosok, gmail)
via PipelineRunner.run_from_yaml() with real:
  - Outlook COM MAPI fetch (search_emails)
  - Docling PDF parse (acquire_documents)
  - GPT-4o-mini classifier (classify_invoices)
  - GPT-4o field extractor (extract_fields)
  - PaymentStatusAdapter (check_payment_status)
  - DataRouter tag rule (organize_files)
  - ReportGenerator markdown+CSV (generate_report)
  - NotificationService in_app channel (notify_team)

Gate: at least 1 account successfully runs the 8-step pipeline end-to-end
and persists workflow_runs + step_runs in DB. Each account run independent.

Needs: docker compose up db redis -d + alembic head + Outlook running +
       OpenAI API key + 3 email_connector_configs rows (bestix/kodosok/gmail).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from aiflow.api.deps import get_session_factory
from aiflow.core.context import ExecutionContext
from aiflow.pipeline.adapter_base import adapter_registry
from aiflow.pipeline.adapters import discover_adapters
from aiflow.pipeline.runner import PipelineRunner
from aiflow.state.models import StepRunModel, WorkflowRunModel

PIPELINE_YAML = Path("src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml").read_text(
    encoding="utf-8"
)

# admin@bestix.hu — FK for workflow_runs.user_id + in_app notification recipient
TEST_USER_ID = "a377062a-ec7f-4244-9a1e-17d7c5865b3c"

# Outlook COM connector configs (pre-created by B3.E2E Phase 0)
ACCOUNTS = [
    {
        "name": "bestix",
        "connector_id": "f522575b-ff3b-44a6-9a70-b68592a01b7c",
        "mailbox": "attila.kassai@bestix.hu",
        "label": "BestIx (business)",
    },
    {
        "name": "kodosok",
        "connector_id": "10afc761-abf4-4796-9d38-cd6931570738",
        "mailbox": "kassaia@kodosok.hu",
        "label": "Kodosok (dev)",
    },
    {
        "name": "gmail",
        "connector_id": "2134ff39-1313-4929-b626-3381d4d62e8f",
        "mailbox": "jegesparos@gmail.com",
        "label": "Gmail (personal)",
    },
]


@pytest.fixture(scope="module", autouse=True)
def _ensure_adapters_discovered() -> None:
    discover_adapters()


@pytest.fixture(scope="module", autouse=True)
def _ensure_outlook_running() -> None:
    """Skip the whole module if Outlook COM is not accessible."""
    try:
        import win32com.client

        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        _ = outlook.Stores.Count
    except Exception as exc:
        pytest.skip(f"Outlook COM not accessible: {exc}")


class TestInvoiceFinderPhase3:
    """Full 8-step pipeline on real Outlook COM — 3 accounts, 1 comprehensive test.

    Single async test to share event loop + cached session_factory (Windows
    proactor event loop limitation — see B3.E2E.P2 test for background).
    """

    async def test_full_pipeline_on_3_outlook_accounts(self) -> None:
        session_factory = await get_session_factory()
        runner = PipelineRunner(
            registry=adapter_registry,
            session_factory=session_factory,
        )

        account_results: list[dict] = []

        for account in ACCOUNTS:
            ctx = ExecutionContext(
                run_id=f"b3-e2e-p3-{account['name']}",
                prompt_label="b3.e2e.p3",
                budget_remaining_usd=2.0,
                team_id=None,
                user_id=TEST_USER_ID,
            )

            print(
                f"\n[B3.E2E.P3] === Running pipeline for {account['label']} "
                f"({account['mailbox']}) ==="
            )

            result = await runner.run_from_yaml(
                yaml_str=PIPELINE_YAML,
                input_data={
                    "connector_id": account["connector_id"],
                    "days": 30,
                    "limit": 10,
                    "confidence_threshold": 0.5,
                    "notify_channel": "in_app",
                    "notify_recipients": TEST_USER_ID,
                    "output_dir": f"./data/phase3/{account['name']}",
                },
                ctx=ctx,
            )

            account_results.append(
                {
                    "account": account["name"],
                    "result": result,
                }
            )

            # Per-account summary (don't fail hard — collect results then assert)
            steps_ok = sum(
                1
                for v in result.step_outputs.values()
                if not (isinstance(v, dict) and v.get("error"))
            )
            print(
                f"  run_id={result.run_id} status={result.status} "
                f"duration={result.total_duration_ms:.0f}ms "
                f"steps_executed={len(result.step_outputs)}/{steps_ok} "
                f"error={result.error}"
            )

            if result.success:
                search = result.step_outputs.get("search_emails", {})
                acquire = result.step_outputs.get("acquire_documents", {})
                classify = result.step_outputs.get("classify_invoices", {})
                extract = result.step_outputs.get("extract_fields", {})
                print(
                    f"  emails_found={search.get('total_matched', 0)} "
                    f"docs_acquired={acquire.get('count', 0)} "
                    f"classified={classify.get('count', 0)} "
                    f"extracted={extract.get('count', 0)}"
                )

        # ---- Gate: at least 1 account must succeed ----
        successes = [r for r in account_results if r["result"].success]
        assert len(successes) >= 1, "All 3 accounts failed. Errors:\n" + "\n".join(
            f"  {r['account']}: {r['result'].error}" for r in account_results
        )

        # ---- Verify DB persistence for at least the first success ----
        first_success = successes[0]
        run_id = first_success["result"].run_id

        async with session_factory() as session:
            wf_run = await session.get(WorkflowRunModel, run_id)
            assert wf_run is not None, f"WorkflowRun {run_id} not in DB"
            assert wf_run.workflow_name == "invoice_finder_v3"
            assert wf_run.status == "completed"
            assert wf_run.total_duration_ms is not None
            assert wf_run.total_duration_ms > 0

            stmt = (
                select(StepRunModel)
                .where(StepRunModel.workflow_run_id == run_id)
                .order_by(StepRunModel.step_index)
            )
            step_rows = list((await session.execute(stmt)).scalars())

        # Full 8-step pipeline
        expected_steps = [
            "search_emails",
            "acquire_documents",
            "classify_invoices",
            "extract_fields",
            "check_payment_status",
            "organize_files",
            "generate_report",
            "notify_team",
        ]
        actual_steps = [s.step_name for s in step_rows]
        assert actual_steps == expected_steps, (
            f"Step order mismatch: {actual_steps} != {expected_steps}"
        )

        for sr in step_rows:
            assert sr.status == "completed", (
                f"Step {sr.step_name} status={sr.status}, error={sr.error}"
            )

        # ---- Cross-account summary print ----
        print("\n[B3.E2E.P3] === CROSS-ACCOUNT SUMMARY ===")
        for r in account_results:
            result = r["result"]
            if result.success:
                search = result.step_outputs.get("search_emails", {})
                extract = result.step_outputs.get("extract_fields", {})
                print(
                    f"  {r['account']:10s}: OK  run={result.run_id} "
                    f"found={search.get('total_matched', 0)} "
                    f"extracted={extract.get('count', 0)}"
                )
            else:
                print(f"  {r['account']:10s}: FAIL {result.error}")
        print(f"[B3.E2E.P3] GATE: {len(successes)}/{len(ACCOUNTS)} accounts succeeded")
