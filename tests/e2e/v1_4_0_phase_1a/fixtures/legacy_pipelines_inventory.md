# Legacy Pipeline Inventory — Phase 1a Regression Suite (D0.9)

> Generated: 2026-04-16
> Source detector: `src/aiflow/pipeline/compatibility.py::detect_pipeline_version`
> Used by: `tests/e2e/v1_4_0_phase_1a/test_legacy_pipeline_regression.py`

Detection rules:
- Explicit `version: "2.*"` → v1.4
- Any step with `adapter: intake_normalize` → v1.4
- Otherwise → v1.3

## Repo-wide sweep

Scanned paths: `src/aiflow/pipeline/builtin_templates/`, `tests/e2e/v1_4_0_phase_1a/fixtures/`.

| File | Detected | Steps | Notes |
|---|---|---|---|
| `src/aiflow/pipeline/builtin_templates/advanced_rag_ingest.yaml` | v1.3 | 5 | `service:` key (no adapter mapping triggers) — version-bump only |
| `src/aiflow/pipeline/builtin_templates/contract_analysis.yaml` | v1.3 | 5 | service-style template |
| `src/aiflow/pipeline/builtin_templates/diagram_generator_v1.yaml` | v1.3 | 1 | service-style template |
| `src/aiflow/pipeline/builtin_templates/email_triage.yaml` | v1.3 | 4 | service-style template (`email_connector`) |
| `src/aiflow/pipeline/builtin_templates/invoice_automation_v1.yaml` | v1.3 | 3 | service-style template |
| `src/aiflow/pipeline/builtin_templates/invoice_automation_v2.yaml` | v1.4 | 5 | explicit `version: "2.0.0"` → detected v1.4 (semver marker) |
| `src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml` | v1.3 | 8 | service-style template |
| `src/aiflow/pipeline/builtin_templates/invoice_finder_v3_offline.yaml` | v1.3 | 5 | service-style template |
| `src/aiflow/pipeline/builtin_templates/knowledge_base_update.yaml` | v1.3 | 5 | service-style template |
| `src/aiflow/pipeline/builtin_templates/spec_writer_v1.yaml` | v1.3 | 1 | service-style template |
| `tests/e2e/v1_4_0_phase_1a/fixtures/sample_legacy_pipeline.yaml` | v1.3 | 3 | adapter-style fixture (`email_adapter` + `document_adapter.extract`) — exercises full rewrite branch |

## Upgrade coverage

- **Adapter-style rewrite** (email_adapter → intake_normalize, document_adapter.extract → extract_from_package): covered by the fixture `sample_legacy_pipeline.yaml`.
- **Service-style pass-through** (no `adapter` keys match): covered by all 9 builtin v1.3 templates — these exercise the "version bump only, steps passthrough" branch of `upgrade_pipeline_v1_3_to_v1_4`.
- **Already-v1.4 skip**: `invoice_automation_v2.yaml` validates that v1.4 detection prevents re-upgrade.

## Why parametrize the builtins

Running the full builtin template set through `upgrade_pipeline_v1_3_to_v1_4` guards against regressions where:
- A step key is accidentally dropped during `deepcopy`.
- `intake_added` flag logic mis-fires on templates without `email_adapter`.
- Future upgrade rules break idempotent `upgrade(upgrade(x)) == upgrade(x)`.
