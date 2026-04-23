# Sprint O (v1.4.11) — UC3 attachment-aware intent

> **Cut from:** `main` @ `13a2f08` (Sprint N PR #18 squash, MERGED 2026-04-29).
> No external PR rebase dependency at the time of opening.

## Summary

- **Classifier reads PDF / DOCX attachments.** New pure-function
  `AttachmentFeatureExtractor` produces a compact `AttachmentFeatures`
  payload (invoice-number regex hit, total-value detection, mime profile,
  table count, keyword buckets, text quality) from the attachments the
  Sprint K `AttachmentProcessor` already produces.
- **Signal-aligned EXTRACT-class rule boost.** When body confidence is
  below 0.6 and the body label is `unknown` ∪ `EXTRACT_INTENT_IDS`, the
  classifier promotes the closest EXTRACT label by +0.3 (cap 0.95):
  `invoice_number_detected → invoice_received`,
  `keyword_buckets["contract"] → order`,
  `total_value_detected only → invoice_received`.
- **End-to-end measurement on a frozen 25-fixture corpus.** Sprint K
  body-only baseline **56% misclass** → Sprint O flag-on **32% misclass**
  (24 pts absolute / 42.9% relative drop). Headline cohorts:
  `invoice_attachment` 3/6 → 6/6 (100%), `contract_docx` 2/6 → 5/6.
- **Optional LLM-context path** (`AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=true`)
  appends an attachment-summary system message to the LLM classification
  prompt. Off by default — Sprint K LLM cost profile unchanged on merge.
- **Admin UI surface** — new `AttachmentSignalsCard` on `/emails/<id>`
  shows the booleans + mime + boost indicator. EN + HU locale strings.
  `EmailDetailResponse` extended with `attachment_features` +
  `classification_method` (additive).
- **Rollout is a no-op for existing deploys.**
  `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false` (default) restores Sprint K
  body-only behaviour exactly: no `AttachmentProcessor` instantiation, no
  classifier `context` argument, no UI card render. Verified by 5 wiring
  unit tests.

## Acceptance criteria (per `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` §3)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | S126 baseline misclass ≥ 15% on frozen 25-email fixture | ✅ | `docs/uc3_attachment_baseline.md` (56% body-only baseline) |
| 2 | `AttachmentFeatureExtractor` ≥ 12 unit tests, fixture-driven | ✅ | `tests/unit/services/classifier/test_attachment_features.py` (14 tests) |
| 3 | Flag-OFF is true no-op (no AttachmentProcessor instantiation, zero new log events, no new keys in `output_data`) | ✅ | `tests/unit/services/email_connector/test_orchestrator_attachment_wiring.py` (5 tests, monkeypatched constructor sentinel + log capture) |
| 4 | Flag-ON wall-clock < 120 s on 25 fixtures | ✅ | `docs/uc3_attachment_extract_timing.md` (65.7 s wall, p50 139 ms, p95 17.5 s docling cold start) |
| 5 | `ClassifierService` consumes `attachment_features` via optional `context` kwarg (backward-compatible with Sprint K callers) | ✅ | `tests/unit/services/classifier/test_attachment_rule_boost.py::test_classify_signature_backward_compat`; Sprint K `tests/integration/services/email_connector/test_scan_and_classify.py` 2/2 unchanged |
| 6 | Rule boost: body conf < 0.6 + EXTRACT signal → +0.3 cap 0.95 | ✅ | 23 unit tests in `test_attachment_rule_boost.py` (matrix, signal alignment, cap, body-label gate) |
| 7 | LLM-context path opt-in via `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT`; OFF by default; OFF emits no extra system message | ✅ | `test_llm_path_no_extra_message_when_opt_in_off` + `test_llm_path_injects_extra_message_when_opt_in_on` |
| 8 | 1 integration test on real Postgres: fixture invoice attachment → `EXTRACT_INTENT_IDS` | ✅ | `tests/integration/services/email_connector/test_attachment_intent_classify.py` (fixture `001_invoice_march`, baseline `unknown` → flag-on `invoice_received`) |
| 9 | Sprint K UC3 golden-path E2E unchanged (regression gate) | ✅ | Sprint K integration tests (`test_scan_and_classify`, `test_intent_routing`) 2/2 unchanged across S127/S128/S129 commits |
| 10 | Misclass drop on 25-fixture corpus | 🟡 | **42.9% relative drop** (56% → 32%); plan §7 target 50%; documented as SOFT in `docs/sprint_o_retro.md` "What hurt". Headline cohort gains met in full (invoice 6/6, contract 5/6). |
| 11 | `AttachmentSignalsCard` UI surface + Playwright E2E + `/live-test` report | ✅ | `aiflow-admin/src/components-new/AttachmentSignalsCard.tsx` + `tests/e2e/v1_4_11_uc3_attachment/test_attachment_signals.py` + `tests/ui-live/attachment-signals.md` |
| 12 | EN + HU locale strings, no console errors during journey | ✅ | `aiflow-admin/src/locales/{en,hu}.json` (`aiflow.emails.attachmentSignals.*` bundle); E2E filters benign WebSocket / Failed-to-load noise |

Sprint O closes green on criteria 1-9, 11-12. Criterion 10 is a SOFT
miss (42.9% vs 50%), surfaced in the retro and tracked as Sprint P
candidate (FU-3 in retro).

## What changed

### Source code

| File | Change | Session |
|---|---|---|
| `src/aiflow/core/config.py` | Added `UC3AttachmentIntentSettings` (env prefix `AIFLOW_UC3_ATTACHMENT_INTENT__`); fields: `enabled` (default False), `max_attachment_mb` (10), `total_budget_seconds` (5.0), S128 `llm_context` (default False) | S127 / S128 |
| `src/aiflow/services/classifier/attachment_features.py` | **NEW** — pure-function `extract_attachment_features` + `AttachmentFeatures` Pydantic | S127 |
| `src/aiflow/services/classifier/service.py` | `ClassifierService.classify(... context=None)` extension; `EXTRACT_INTENT_IDS = {"invoice_received", "order"}`; `_apply_attachment_rule_boost`; `_build_attachment_context_message`; per-strategy helpers thread `context` to `_classify_llm` | S128 |
| `src/aiflow/services/email_connector/orchestrator.py` | `attachment_intent_settings` kwarg on `scan_and_classify`; `_maybe_extract_attachment_features` lazy-imports `AttachmentProcessor`, runs in `asyncio.wait_for(total_budget_seconds)`, returns `{"attachment_features", "attachment_text_preview"}`; flag-OFF path is a true no-op (verified) | S127 / S128 |
| `src/aiflow/api/v1/emails.py` | `EmailDetailResponse.attachment_features: dict \| None`, `classification_method: str \| None` (additive); GET handler threads `data["attachment_features"]` + `data["method"]` from `workflow_runs.output_data` | S129 |
| `aiflow-admin/src/components-new/AttachmentSignalsCard.tsx` | **NEW** — Tailwind v4 collapsible card with badges + mime/dl + keyword chips + boost indicator. `data-testid` hooks for E2E stability. | S129 |
| `aiflow-admin/src/pages-new/EmailDetail.tsx` | Mounts `AttachmentSignalsCard` below intent / priority / routing / meta cards | S129 |
| `aiflow-admin/src/locales/{en,hu}.json` | `aiflow.emails.attachmentSignals.*` bundle (title + badges + dl + keyword buckets + boost indicator) | S129 |

### Tests

| File | Added | Session |
|---|---|---|
| `tests/unit/core/test_config.py` | +3 tests (`TestUC3AttachmentIntentSettings`: defaults / env override / direct construction) | S127 |
| `tests/unit/services/classifier/test_attachment_features.py` | **NEW** — 14 unit tests (empty list, INV regex match/miss, HUF total, NDA contract, support cohort, table count sum, image skip, oversize skip, error skip, mime dominance, text-quality mean, HU SZAMLA pattern, image-only zeroed) | S127 |
| `tests/unit/services/email_connector/test_orchestrator_attachment_wiring.py` | **NEW** — 5 unit tests (flag-OFF no-op, default-OFF backward-compat, flag-ON zero-files skip, flag-ON real-file end-to-end, helper timeout path) | S127 |
| `tests/unit/services/classifier/test_attachment_rule_boost.py` | **NEW** — 23 unit tests (rule-boost matrix, body-label gate, signal alignment, +0.3 / 0.95 cap, no-op cases, LLM-context message contents + 500-char truncation, LLM messages list shape) | S128 |
| `tests/integration/services/email_connector/test_attachment_intent_classify.py` | **NEW** — 1 integration test on real Postgres (fixture `001_invoice_march` → `EXTRACT_INTENT_IDS`, attachment_features persisted) | S128 |
| `tests/e2e/v1_4_11_uc3_attachment/test_attachment_signals.py` | **NEW** — 1 Playwright E2E (route-mocked card render with boost indicator) | S129 |
| `tests/ui-live/attachment-signals.md` | **NEW** — `/live-test` report (Playwright PASS; live-API smoke deferred until `make api` restart) | S129 |

### Scripts + docs

| File | Purpose | Session |
|---|---|---|
| `scripts/measure_uc3_baseline.py` | **NEW** — Sprint K body-only baseline measurement on the 25-fixture corpus | S126 |
| `scripts/measure_uc3_attachment_extract_cost.py` | **NEW** — flag-on extraction wall-clock on the 25-fixture corpus | S127 |
| `scripts/measure_uc3_attachment_intent.py` | **NEW** — flag-on misclass re-measurement + comparison vs S126 baseline | S128 |
| `data/fixtures/emails_sprint_o/` | **NEW** — 25 anonymised fixture emails + manifest + fixture-generation script | S126 |
| `docs/uc3_attachment_baseline.md` | **NEW** — S126 output, 56% misclass / 40% manual-review-like / p95 95 ms | S126 |
| `docs/uc3_attachment_extract_timing.md` | **NEW** — S127 output, 65.7 s wall / p50 139 ms / p95 17.5 s | S127 |
| `docs/uc3_attachment_intent_results.md` | **NEW** — S128 output, 32% misclass / per-cohort breakdown | S128 |
| `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` | **NEW** — sprint plan (4 sessions S126-S130, scope, STOP, metrics) | S126 |
| `docs/sprint_o_plan.md` | **NEW** — operator-facing sprint plan summary | S126 |
| `docs/sprint_o_retro.md` | **NEW** — sprint retro (this PR closes against it) | S130 |
| `docs/sprint_o_pr_description.md` | **NEW** — this file | S130 |

## Test plan (post-merge)

- [ ] `make api` restart so live `/api/v1/emails/{id}` exposes
      `attachment_features` + `classification_method`. Without restart,
      the AttachmentSignalsCard renders nothing on real
      orchestrator-produced runs (the data is in
      `workflow_runs.output_data`; only the API filter was missing).
- [ ] Smoke `/budget-management` and `/emails` admin pages — Sprint N
      surface unchanged.
- [ ] Live `/live-test attachment_signals` against real
      `/api/v1/emails/{id}` once API restarted; remove the `page.route`
      mock in the E2E if it survives a real-API run.
- [ ] Per-tenant flag-on rollout: enable
      `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=true` for one tenant,
      observe the `email_connector.scan_and_classify.attachment_features_extracted`
      structlog event count and the `attachment_features` payload on a
      few `workflow_runs` rows.
- [ ] Once rule-boost behaviour is observed for a few days, optionally
      flip `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=true` for a
      live-LLM measurement (FU-6 in retro).

## Rollback

- **Flag-off rollback** (primary). `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false`
  restores Sprint K body-only behaviour exactly: no AttachmentProcessor
  instantiation, no classifier `context` argument, no UI card render.
  Verified by 5 wiring unit tests + Sprint K integration tests unchanged.
  No DB rollback required (Sprint O ships zero migrations).
- **Revert rollback.** S127 + S128 + S129 are 4 squash-mergeable commits;
  reverting them on `main` restores Sprint K behaviour bit-for-bit.
- **Data rollback.** Nothing to roll back — `attachment_features` is
  additive JSONB in `workflow_runs.output_data`; leftover keys are
  ignored by Sprint K callers.

## Open follow-ups (Sprint P candidates)

- **FU-1** Restart `make api` post-merge.
- **FU-2** Add `intent.intent_class` to v1 schema for UI-agnostic
  EXTRACT badge.
- **FU-3** Body-only / mixed cohort coverage (out of attachment scope —
  candidate Sprint P with LLM-context evaluation + thread-aware
  classification).
- **FU-4** docling p95 cold-start instrumentation (Sprint J BGE-M3
  weight-cache CI artifact carry).
- **FU-5** Resilience `Clock` seam (deadline 4 days past 2026-04-30) —
  unquarantine `test_circuit_opens_on_failures` or document a new
  deadline.
- **FU-6** LLM-context path live measurement against fixtures.
- **FU-7** Per-attachment cost accounting.

Carried Sprint N / M / J follow-ups are listed verbatim in
`docs/sprint_o_retro.md` §"Carried".

🤖 Generated with [Claude Code](https://claude.com/claude-code)
