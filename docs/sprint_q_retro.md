# Sprint Q — Retrospective (v1.5.0 intent + extraction unification)

> **Sprint window:** 2026-05-07 → 2026-05-10 (4 sessions: S135, S136, S137, S138)
> **Branch:** `feature/q-s138-sprint-close` (cut from `main` @ `5f850b5`, S137 squash-merge)
> **Tag:** `v1.5.0` — queued for post-merge on `main`
> **PR:** opened at S138 against `main` — see `docs/sprint_q_pr_description.md`
> **Predecessor:** `v1.4.12` (Sprint P — UC3 intent at 4% misclass, MERGED `390d4d5`)
> **Plan reference:** `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md` + master roadmap `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md`

## Headline

Sprint Q bridged Sprint P's intent classifier with the `invoice_processor`
skill's extraction pipeline, then validated the UC1 end-to-end path on a
curated 10-fixture corpus that had been open since Sprint I (Phase 1d
rescope). Together these close the "intent + extraction" capability
gap — an email with an invoice attachment now yields both the intent and
the structured fields, surfaced on the admin UI.

```
UC3 intent (Sprint P):        4% misclass on 25-fixture corpus  ← unchanged
UC3 → invoice_processor wiring (S135):   output_data.extracted_fields  ← new
Admin UI ExtractedFieldsCard (S136):     vendor / buyer / header / items / totals  ← new
UC1 golden-path accuracy (S137):         85.7% on 10-fixture corpus  ← new first validation
  invoice_number: 100%, vendor_name: 100%, buyer_name: 100%,
  currency: 100%, due_date: 100%, gross_total: 100%,
  issue_date:   0%   ← SQ-FU-1 (prompt/schema mismatch)
```

The `issue_date` systematic failure is the one visible gap — the
extractor's `_parse_date` helper returns a Python `date` object that
doesn't round-trip to the manifest's ISO-8601 string in all cases.
Filed as SQ-FU-1 for Sprint R prompt-tune work.

## Scope by session

| Session | Commit | Deliverable |
|---|---|---|
| **S135** | `c70c5eb` (PR #26) | `UC3ExtractionSettings` flag (`AIFLOW_UC3_EXTRACTION__ENABLED=false` default) + `_maybe_extract_invoice_fields` orchestrator helper + `_intent_class_is_extract` gate (reuses Sprint O FU-2 lookup). Lazy-imports `skills.invoice_processor.workflows.process` so flag-off is a true no-op. Wraps per-file extraction in `asyncio.wait_for(total_budget_seconds)` with per-invoice USD budget ceiling. 14 unit tests (flag-off sentinel, intent_class gate, happy path, per-file error isolation, timeout, budget breach, max_attachments honored, cross-sprint coexistence with Sprint O) + 1 real-stack integration (real PG + real docling + real OpenAI on fixture `001_invoice_march` → `INV-2026-0001` extracted + persisted). |
| **S136** | `a1cf989` (PR #27) | `EmailDetailResponse.extracted_fields: dict[str, Any] \| None` (additive). New `ExtractedFieldsCard.tsx` React component (Tailwind v4, dark-mode, Tailwind-native `<details>` line-items expand, confidence/cost chips). EN + HU locale (`aiflow.emails.extractedFields.*`). 1 Playwright E2E against the **real live dev stack** (no route mock) — seeds DB, hits live API with signed JWT, visually asserts card + invoice number + gross total render. |
| **S137** | `5f850b5` (PR #28) | 10 reportlab-generated invoice PDFs under `data/fixtures/invoices_sprint_q/` (4 HU / 4 EN / 2 mixed; 5 simple / 3 tabular / 2 multi-section) + `manifest.yaml` ground-truth. `scripts/measure_uc1_golden_path.py` — writes `docs/uc1_golden_path_report.md` with per-field accuracy, p50/p95, cost. HARD STOP conditions (wall > 600 s, mean cost > $0.10, accuracy < 60%). `tests/integration/skills/test_uc1_golden_path.py` — CI slice (3 fixtures) asserting overall ≥ 75% / invoice_number ≥ 90%. Full corpus measurement: 85.7% accuracy, $0.0004 mean cost, 96 s wall. |
| **S138** | _(this commit)_ | Sprint close — `docs/sprint_q_retro.md`, `docs/sprint_q_pr_description.md`, CLAUDE.md numbers + Sprint Q DONE banner, PR cut against `main`. Tag `v1.5.0` queued. |

## Test deltas

| Suite | Before (Sprint P tip) | After (S137 tip) | Delta |
|---|---|---|---|
| Unit | 2278 | **2296** | **+18** (14 orchestrator + 3 settings + 1 intent_class gate) |
| Integration | ~101 | **~103** | **+2** (S135 extraction_real + S137 golden-path slice) |
| E2E collected | 428 | **429** | **+1** (S136 extracted-fields-card live-stack) |
| Alembic head | 045 | **045** | **0** (JSONB field + settings only) |
| API endpoints | 190 (29 routers) | **190 (29 routers)** | **0** (one additive field on `EmailDetailResponse`) |
| UI pages | 24 | **24** | **0** (new component only) |
| Ruff / TSC | clean | clean | 0 new errors |

## Contracts + architecture delivered

- **`UC3ExtractionSettings` (S135)** — env prefix `AIFLOW_UC3_EXTRACTION__`,
  fields: `enabled=false` default, `max_attachments_per_email=5`,
  `total_budget_seconds=60.0`, `extraction_budget_usd=0.05` per-invoice
  ceiling. Additive on `AIFlowSettings`. Operators can flip per-tenant.
- **`_intent_class_is_extract` (S135)** — module-level gate on the
  classifier result. Reuses Sprint O FU-2 `_resolve_intent_class` —
  no new intent_class list. Future-proof: new EXTRACT intents land here
  automatically once added to the schema.
- **`_maybe_extract_invoice_fields` (S135)** — orchestrator helper, lazy
  imports `skills.invoice_processor.workflows.process.parse_invoice` +
  `extract_invoice_data`. Per-file budget USD estimate based on token
  counts. Per-filename error capture — one bad attachment never aborts
  the others. `asyncio.wait_for(total_budget_seconds)` wraps the whole
  loop.
- **`EmailDetailResponse.extracted_fields` (S136)** — optional
  `dict[str, Any]`, additive — Sprint P callers unaffected. OpenAPI
  snapshot refreshed.
- **`ExtractedFieldsCard.tsx` (S136)** — composable React component,
  reusable if a future UC (contracts, purchase orders) ships its own
  extraction path. `data-testid` hooks for stable E2E.
- **UC1 golden-path corpus (S137)** — the project's first
  regeneratable anonymised invoice corpus. 10 reportlab PDFs with
  ground-truth manifest. `scripts/measure_uc1_golden_path.py` runs the
  full pipeline and writes a report comparable to Sprint O's
  baseline/intent reports.

## Key numbers (Sprint Q tip)

```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2296 unit PASS / 1 skipped
~103 integration PASS (Sprint Q +2)
429 E2E collected (Sprint Q +1)
0 ruff error on changed files | 0 TSC error | OpenAPI snapshot refreshed
Branch: feature/q-s138-sprint-close (HEAD prepared, 3 commits on main ahead
        of Sprint P tip 390d4d5)
Flag defaults on merge: AIFLOW_UC3_EXTRACTION__ENABLED=false
                        AIFLOW_UC3_ATTACHMENT_INTENT__* (Sprint O/P defaults unchanged)
UC1 accuracy target: ≥ 80% → 85.7% (target exceeded, 1 field missing)
```

## Decisions log

- **SQ-1 — Additive JSONB field over schema migration.** Sprint O's
  pattern (`output_data.attachment_features`) already proved JSONB
  keys work for cross-feature payloads; Sprint Q did the same for
  `extracted_fields`. Zero Alembic cost, zero-downtime rollback via
  flag flip.
- **SQ-2 — Lazy-imported `skills.invoice_processor` from orchestrator.**
  The orchestrator lives in `src/aiflow/services/email_connector/`; the
  extractor lives in `skills/invoice_processor/`. Cross-namespace import
  is fine at runtime but a module-level `from skills.invoice_processor…`
  would pull the docling dependency chain at module load — expensive
  when the flag is off. Lazy pattern (import inside `_maybe_extract_…`)
  preserves the Sprint O flag-off contract.
- **SQ-3 — Per-file error isolation.** Multi-attachment emails are a
  real pattern (invoice + supporting docs). One bad file mustn't kill
  the others. Each file's error lands under `extracted_fields[<filename>]
  = {"error": "..."}`, and the rest proceed.
- **SQ-4 — Reportlab-generated fixture corpus.** `generate_invoices.py`
  is idempotent + deterministic, so the 10 PDFs can be regenerated
  instead of tracked as binary blobs — keeps the repo diff clean.
  Same pattern Sprint O used for emails.
- **SQ-5 — CI slice vs. operator measurement.** The full 10-fixture
  `measure_uc1_golden_path.py` run takes ~96 s (docling cold start is
  the tail). Too slow for every PR's CI; too valuable not to run. Split:
  CI runs a 3-fixture slice (< 1 min, same accuracy gate scaled), the
  full script is operator-facing and writes the report that ships with
  the release.

## What worked

- **Capability-first replan (01_PLAN/114) identified the right bridge
  immediately.** UC3 intent was already at 4%; the customer-visible
  win was chaining `invoice_processor` after the classifier, not
  improving the classifier further. Three mergeable PRs, each with real
  E2E, each < 1 day of work.
- **Sprint O's modular pieces composed cleanly.** `_resolve_intent_class`
  (FU-2) plugged straight into `_intent_class_is_extract`. The JSONB
  pattern from `attachment_features` extended to `extracted_fields`
  without friction. Sprint O's orchestrator-helper style became the
  template for Sprint Q's helper.
- **Real-stack tests caught a real issue early.** S135's integration
  test on `001_invoice_march.eml` caught a docling-on-Linux
  incompatibility flag (same as the Sprint O discovery) — reused the
  `_docling_can_read_fixture` skip guard pattern. Kept CI green on
  Linux without compromising Windows dev-box coverage.
- **S137 corpus generator is reusable.** Same reportlab pattern as the
  Sprint O email fixtures; the `generate_invoices.py` script ships in
  the repo and can expand from 10 → 25 fixtures in an afternoon if a
  customer asks.

## What hurt

- **`issue_date` systematic miss (SQ-FU-1).** All 10 fixtures extracted
  every field except `issue_date`. Likely cause: the `_parse_date`
  helper in `skills/invoice_processor/workflows/process.py` returns a
  Python `date` or `None` depending on the LLM output format — when
  `None`, the manifest's `"2026-03-15"` string can't match. Options
  (deferred to Sprint R):
  (a) Tune the `invoice/header_extractor` prompt to explicitly return
      ISO-8601 strings.
  (b) Post-process the parsed date back to ISO in the `header` dict.
  (c) Add a manifest-side tolerance: accept `date(2026, 3, 15)` and
      `"2026-03-15"` as equivalent.
  Pick one and close in Sprint R's PromptWorkflow work.
- **p95 latency 34.9 s on the 10-fixture run.** The first invoice pays
  the docling cold start; subsequent invoices land at ~5-8 s each.
  Sprint O's FU-4 warmup script already addresses this but isn't wired
  into `make api` boot — small operational follow-up (SQ-FU-2).
- **Formatter stripped imports twice during S135/S137.** Same pattern
  as Sprint O — `_RUNTIME_HOOKS` tuple workaround documented in the
  shared memory. One more data point that a project-level ruff rule
  to honor `if TYPE_CHECKING` imports would save time.

## Open follow-ups

- **SQ-FU-1** `issue_date` extraction — pick option (a/b/c) above
  during Sprint R's PromptWorkflow migration (S141 migrates the
  `invoice_processor` prompts anyway; good place to add the ISO format
  instruction).
- **SQ-FU-2** Pre-boot docling warmup — wire `scripts/warmup_docling.py
  --strict` into `make api` start sequence so the first real invoice
  doesn't pay the model load. Zero code change, Makefile only.
- **SQ-FU-3** UC1 corpus extension — if a customer needs > 10 fixture
  coverage, extend the generator to 25 (add multilingual,
  image-only-PDF, large-page-count cohorts).
- **SQ-FU-4** `_parse_date` ↔ ISO roundtrip helper in Pydantic
  `_header_extractor` output schema. Defensive fix that pairs with
  SQ-FU-1.

## Carried (Sprint N / M / J / P — unchanged)

Sprint P retro SP-FU-1..3 unchanged (complaint-over-attachment
precedence, matrix CI artifact, Langfuse prompt variant). Sprint N/M/J
residuals unchanged (cost consolidation, Grafana panels, Langfuse v4,
BGE-M3 cache). These are Sprint R-and-later scope.
