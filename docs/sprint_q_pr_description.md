# Sprint Q (v1.5.0) — intent + extraction unification

> **Cut from:** `main` @ `5f850b5` (Sprint Q S137 squash-merge). No external rebase dependency.

## Summary

- **UC3 intent → UC1 invoice extraction chained end-to-end.** An email
  that the classifier labels `invoice_received` / `invoice_to_send` now
  runs `skills.invoice_processor` on its attachments, and the admin UI
  surfaces the structured fields (vendor / buyer / header / line
  items / totals). Flag-gated (`AIFLOW_UC3_EXTRACTION__ENABLED=false`
  default) so Sprint P callers are unaffected.
- **First UC1 end-to-end validation since Phase 1d — 85.7% accuracy** on
  a 10-fixture reportlab corpus (HU/EN/mixed; simple/tabular/multi-section
  layouts). Target was ≥ 80%. `invoice_number`, `vendor_name`,
  `buyer_name`, `currency`, `due_date`, `gross_total` all at 100%; only
  `issue_date` misses systematically (`_parse_date` ↔ manifest format
  mismatch — filed as SQ-FU-1).
- **No migration, no new endpoint, no new UI page.** One additive JSONB
  key on `workflow_runs.output_data`, one additive response field on
  `EmailDetailResponse`, one new settings class, one new React component.
  Flag-off path is a true no-op — import cost is zero via lazy import.

## Cohort delta (capability-first roadmap)

```
                        Sprint K    Sprint O    Sprint P    Sprint Q
UC3 intent misclass:    56%         32%         4%          4%        (unchanged)
UC3 → extraction:       –           –           –           wired     ← new
Admin UI card:          –           –           –           shipped   ← new
UC1 accuracy gate:      –           –           –           85.7%     ← new (target ≥ 80%)
```

## Acceptance criteria (per `01_PLAN/115_SPRINT_Q_*` §5)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `UC3ExtractionSettings` flag-gated settings class, default `enabled=false` | ✅ | `src/aiflow/core/config.py`; 3 unit tests |
| 2 | Orchestrator helper `_maybe_extract_invoice_fields` + `_intent_class_is_extract` gate | ✅ | `src/aiflow/services/email_connector/orchestrator.py` (14 unit + 1 real-stack integration) |
| 3 | Flag-off is a true no-op (Sprint O/P behaviour byte-identical) | ✅ | Unit tests assert sentinel; lazy import of `skills.invoice_processor` |
| 4 | `EmailDetailResponse.extracted_fields` additive field | ✅ | `src/aiflow/api/v1/emails.py`; OpenAPI snapshot refreshed |
| 5 | Admin UI `ExtractedFieldsCard` renders vendor/buyer/header/items/totals | ✅ | `aiflow-admin/src/components-new/ExtractedFieldsCard.tsx` + EN/HU locale |
| 6 | Playwright E2E against **live dev stack** (no route mock) | ✅ | `tests/e2e/v1_5_0_q_s136_extracted_fields/test_extracted_fields_card.py` — real DB seed, real API, visual assertions |
| 7 | 10-fixture UC1 golden-path corpus + manifest + regeneration script | ✅ | `data/fixtures/invoices_sprint_q/` (10 PDFs, `manifest.yaml`, `generate_invoices.py`) |
| 8 | Overall field accuracy ≥ 80% on 10-fixture corpus | ✅ | 85.7% — target exceeded |
| 9 | `invoice_number` accuracy ≥ 90% | ✅ | 100% |
| 10 | Cost per extraction < $0.02 | ✅ | $0.0004 mean (50x under budget) |
| 11 | CI slice integration test gates on the corpus accuracy | ✅ | `tests/integration/skills/test_uc1_golden_path.py` — 3 fixtures, overall ≥ 75% / invoice_number ≥ 90% |
| 12 | ≥ 15 new unit tests, ≥ 1 new integration, ≥ 1 new E2E | ✅ | +18 unit / +2 integration / +1 E2E |

Sprint Q closes green on all 12 criteria.

## What changed

### Source code

| File | Change | Session |
|---|---|---|
| `src/aiflow/core/config.py` | `UC3ExtractionSettings` class (enabled, max_attachments_per_email, total_budget_seconds, extraction_budget_usd) + `AIFlowSettings.uc3_extraction` mount | S135 |
| `src/aiflow/services/email_connector/orchestrator.py` | `_intent_class_is_extract()` gate + `_maybe_extract_invoice_fields()` helper with lazy import, per-file error isolation, `asyncio.wait_for` wrap, per-invoice USD budget ceiling | S135 |
| `src/aiflow/api/v1/emails.py` | `EmailDetailResponse.extracted_fields: dict[str, Any] \| None = None` + GET handler propagates `output_data.extracted_fields` | S136 |
| `aiflow-admin/src/components-new/ExtractedFieldsCard.tsx` | New React component (Tailwind v4, dark-mode, confidence + cost chips, Tailwind-native `<details>` line-items expand, data-testid hooks) | S136 |
| `aiflow-admin/src/pages-new/EmailDetail.tsx` | Mounts `<ExtractedFieldsCard>` under the existing `<AttachmentSignalsCard>` | S136 |
| `aiflow-admin/src/locales/{en,hu}.json` | `aiflow.emails.extractedFields.*` bundle | S136 |

### Fixtures + scripts + docs

| File | Purpose | Session |
|---|---|---|
| `data/fixtures/invoices_sprint_q/*.pdf` + `manifest.yaml` | 10-fixture UC1 golden-path corpus (HU/EN/mixed, simple/tabular/multi-section) | S137 |
| `data/fixtures/invoices_sprint_q/generate_invoices.py` | Idempotent + deterministic reportlab generator (same pattern as Sprint O email fixtures) | S137 |
| `scripts/measure_uc1_golden_path.py` | Operator-facing full-corpus measurement script — writes report | S137 |
| `docs/uc1_golden_path_report.md` | 85.7% accuracy / $0.0004 cost / p50 5.8s / p95 34.9s | S137 |
| `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` | Master capability roadmap Q-R-S-T-U | S135 kickoff |
| `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md` | Sprint Q detailed plan | S135 kickoff |
| `docs/sprint_q_retro.md` | Sprint retrospective | S138 |
| `docs/sprint_q_pr_description.md` | This file | S138 |

### Tests

| File | Added | Session |
|---|---|---|
| `tests/unit/services/email_connector/test_orchestrator_extraction_wiring.py` | 14 unit tests (flag-off sentinel, intent_class gate, happy path, per-file error isolation, timeout, budget breach, max_attachments honored, Sprint O coexistence) | S135 |
| `tests/unit/core/test_uc3_extraction_settings.py` | 3 settings tests (defaults, env override, bounds) | S135 |
| `tests/unit/services/email_connector/test_intent_class_gate.py` | 1 gate test reusing Sprint O FU-2 `_resolve_intent_class` | S135 |
| `tests/integration/services/email_connector/test_extraction_real.py` | 1 real-stack integration (real PG + real docling + real OpenAI → `001_invoice_march.eml` → `INV-2026-0001` persisted) | S135 |
| `tests/e2e/v1_5_0_q_s136_extracted_fields/test_extracted_fields_card.py` | 1 Playwright E2E on **live dev stack** (no route mock) | S136 |
| `tests/integration/skills/test_uc1_golden_path.py` | 1 CI slice (3 fixtures) — overall ≥ 75% / invoice_number ≥ 90% | S137 |

## Test plan (post-merge)

- [ ] Per-tenant flag-on rollout: enable
      `AIFLOW_UC3_EXTRACTION__ENABLED=true` for one tenant, observe
      `workflow_runs.output_data.extracted_fields[<filename>]` rows for
      EXTRACT-labelled emails. Expect vendor / buyer / gross_total
      populated within the configured USD budget.
- [ ] Admin UI smoke: open an affected email detail page — confirm
      `<ExtractedFieldsCard>` renders below the attachment-signals card,
      invoice number + gross total visible, line-items expand on click.
- [ ] Cost dashboard check: `cost_records` should show one
      `invoice_processor` row per extracted attachment (leveraging FU-7
      per-attachment cost accounting). Per 10-fixture corpus run:
      ~$0.004 OpenAI spend.
- [ ] Operator measurement: run `scripts/measure_uc1_golden_path.py`
      locally against `data/fixtures/invoices_sprint_q/` — expect the
      same 85.7% accuracy / $0.0004 mean cost / 96s wall produced in
      S137.
- [ ] Regression: Sprint K UC3 golden-path E2E unchanged (4/4 green);
      Sprint P strategy-switch E2E unchanged.

## Rollback

1. **Flag-off rollback (primary).**
   `AIFLOW_UC3_EXTRACTION__ENABLED=false` = Sprint P tip behaviour, the
   extraction helper is never called, lazy import never fires, no
   `extracted_fields` key lands on `output_data`.
2. **Revert rollback.** 3 squash commits (#26 S135, #27 S136, #28 S137,
   plus this close PR) are isolated; `git revert` on any combination
   restores the prior state. The UI component is additive — reverting
   only the frontend PR leaves the backend harmless.
3. **Data rollback.** None — Sprint Q ships zero migrations. JSONB keys
   can be dropped via a one-off update if needed
   (`output_data = output_data - 'extracted_fields'`).

## Open follow-ups (Sprint R candidates)

- **SQ-FU-1** `issue_date` extraction fix — tune
  `invoice/header_extractor` prompt for ISO-8601 strings OR add
  manifest-side date-tolerance. Natural fit for Sprint R's
  PromptWorkflow migration.
- **SQ-FU-2** Pre-boot docling warmup wired into `make api` so the
  first real invoice doesn't pay the model cold start (p95 34.9 s on
  first fixture today, ~5-8 s thereafter).
- **SQ-FU-3** UC1 corpus extension to 25 fixtures (multilingual,
  image-only, large-page-count cohorts) — on demand.
- **SQ-FU-4** `_parse_date` ↔ ISO roundtrip helper in
  `invoice_processor` Pydantic output schema. Defensive fix that pairs
  with SQ-FU-1.

Plus carried Sprint P (SP-FU-1..3), Sprint N/M/J residuals unchanged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
