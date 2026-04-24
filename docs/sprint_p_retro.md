# Sprint P — Retrospective (v1.4.12 LLM-fallback + body/mixed cohort coverage)

> **Sprint window:** 2026-05-05 → 2026-05-06 (3 sessions: S131, S132, S134; S133 skipped — see below)
> **Branch:** `feature/p-s134-sprint-close` (cut from `main` @ `b061d71`, S132 squash-merge)
> **Tag:** `v1.4.12` — queued for post-merge on `main`
> **PR:** opened at S134 against `main` — see `docs/sprint_p_pr_description.md`
> **Predecessor:** `v1.4.11` (Sprint O UC3 attachment-aware intent + follow-ups FU-2 / FU-4 / FU-7, all merged on `main`)
> **Plan reference:** `01_PLAN/113_SPRINT_P_LLM_CONTEXT_BODY_MIXED_PLAN.md` + `docs/uc3_llm_context_baseline.md`

## Headline

Sprint P closes Sprint O retro **FU-3** (body-only/mixed cohort coverage)
and **FU-6** (LLM-context fixture measurement) by changing the classifier
strategy on the attachment-intent flag-on path from `SKLEARN_ONLY` to
`SKLEARN_FIRST` and adding a pre-LLM attachment-signal early-return that
preserves Sprint O behaviour on NDA/SLA/MSA contracts.

```
Sprint K body-only baseline:        56% misclass (14/25)
Sprint O flag-on (rule boost only): 32% misclass  (8/25)  — 42.9% relative drop
Sprint P flag-on (strategy+rule):    4% misclass  (1/25)  — 87.5% relative drop

Cohort deltas (Sprint K → Sprint O → Sprint P):
  invoice_attachment: 3/6 → 6/6 → 6/6   (100%)
  contract_docx:      2/6 → 5/6 → 6/6   (100%)
  body_only:          3/6 → 3/6 → 6/6   (100%) ← Sprint P unlock
  mixed:              3/7 → 3/7 → 6/7   ( 86%) ← Sprint P unlock
```

The remaining miss is `024_complaint_about_invoice` — a legitimate
body-vs-attachment conflict (body says "complaint", PDF attachment is an
invoice). The rule boost fires because the attachment carries an
invoice-number signal; the body-label gate cannot protect `complaint`
here because the keyword classifier gives it a low-confidence score
that the early-return force-relabels to `unknown`. Resolving this
specific case would require a "complaint-over-attachment" precedence
rule — scope creep for a single-fixture win. Documented as SOFT carry.

## Scope by session

| Session | Commit | Deliverable |
|---|---|---|
| **S131** | `180f05d` | `01_PLAN/113_SPRINT_P_*`+ `scripts/measure_uc3_llm_context.py` + `docs/uc3_llm_context_baseline.md`. 4-combo matrix (strategy × LLM-context). Confirmed **combo 3 (SKLEARN_FIRST, no context) = 12% misclass, $0.0045/run** — crossing plan §7 target. No code changes under `src/`. |
| **S132** | `b061d71` | `UC3AttachmentIntentSettings.classifier_strategy` (default `"sklearn_first"`). Orchestrator threads it into `classify(...)`. `ClassifierService._keywords_first` pre-LLM early-return when attachment signals are strong — restores Sprint O behaviour on contracts where the LLM otherwise picks `internal`. 10 unit + 2 integration (real OpenAI + real Postgres) + 1 Playwright E2E (live stack). **Final measurement: 4% misclass (1/25).** |
| ~~S133~~ | _(skipped)_ | Plan §3 had S133 reserved for mixed-cohort refinement. S132's 4% result already exceeded plan §7 targets 4x over — the one remaining miss is an intractable body-vs-attachment conflict, not a cohort-level defect. Skipped to respect scope. |
| **S134** | _(this commit)_ | Sprint close — `docs/sprint_p_retro.md`, `docs/sprint_p_pr_description.md`, CLAUDE.md numbers + Sprint P DONE banner, PR cut against `main`. Tag `v1.4.12` queued (post-merge). |

## Test deltas

| Suite | Before (Sprint O tip) | After (S132 tip) | Delta |
|---|---|---|---|
| Unit | 2268 | **2278** | **+10** (S132 classifier-unit bundle) |
| Integration | ~99 | **~101** | **+2** (S132 `test_strategy_switch_contract`: 009 contract + 013 body-only) |
| E2E collected | 427 | **428** | **+1** (S132 live-stack badge render) |
| Alembic head | 045 | **045** | **0** (no migration — Sprint P is code + settings only) |
| API endpoints | 190 (29 routers) | **190 (29 routers)** | **0** |
| UI pages | 24 | **24** | **0** (component updates only, no new route) |
| Ruff / TSC | clean | clean | 0 new errors on changed files |

## Contracts + architecture delivered

- **`UC3AttachmentIntentSettings.classifier_strategy` (S132, on `AIFlowSettings`)**
  — new string field (env prefix `AIFLOW_UC3_ATTACHMENT_INTENT__`), default
  `"sklearn_first"`. Operator may revert to `"sklearn_only"` to keep the
  Sprint K/O latency + cost profile. Additive; ignored when `enabled=false`.
- **`scan_and_classify` strategy override (S132)** — when flag-on, the
  orchestrator passes `strategy=settings.classifier_strategy` into
  `classifier.classify(...)`. Flag-off callers see no change.
- **`ClassifierService._keywords_first` early-return (S132)** — pre-LLM
  short-circuit when keyword confidence is below threshold **and**
  `_attachment_signal_is_strong(context)` is True. Base label is set to
  `unknown` so the post-process rule boost (Sprint O
  `_apply_attachment_rule_boost`) can apply without the body-label gate
  blocking it.
- **`_attachment_signal_is_strong` helper (S132)** — pure-function:
  True iff `invoice_number_detected` OR `total_value_detected` OR
  `keyword_buckets["contract"] > 0`. Symmetric with the rule-boost
  trigger list.

## Key numbers (Sprint P tip)

```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2278 unit PASS / 1 skip (no xpass — Sprint O FU-5 already resolved the
  resilience Clock seam quarantine)
~101 integration PASS (Sprint P +2: real OpenAI LLM fallback on NDA/inquiry)
428 E2E collected (Sprint P +1: strategy-switch badge render)
0 ruff error on changed files | 0 TSC error | OpenAPI snapshot refreshed
Branch: feature/p-s134-sprint-close (HEAD prepared, 3 commits ahead of main)
Flag defaults on merge: AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false
                        AIFLOW_UC3_ATTACHMENT_INTENT__CLASSIFIER_STRATEGY=sklearn_first
                        AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=false
```

## Decisions log

- **SP-1 — Measurement first, code second.** S131 landed the 4-combo
  measurement matrix WITHOUT a single source-code change, so S132 could
  make a grounded, bounded edit. The Sprint P plan §2 hard-gate
  framework (≥ 20% relative improvement on body_only/mixed) was
  exceeded before any business code moved.
- **SP-2 — LLM-context (FU-6) shipped as unit-tested infrastructure,
  not as default-on feature.** The matrix showed LLM-context actually
  hurt by 1 fixture on this corpus (mixed 7/7 → 6/7 on combo 3 → 4).
  Stays as an opt-in flag (`AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT`);
  a per-tenant Langfuse prompt variant is the right next step if the
  feature becomes customer-critical.
- **SP-3 — Pre-LLM early-return over body-label gate relaxation.**
  The NDA regression (keyword → `feedback`, LLM → `internal`) had two
  possible fixes: (a) expand the rule-boost body-label gate to include
  more labels, or (b) force the base label to `unknown` before the
  post-process boost. (b) is surgical — it only affects the low-
  confidence-keyword + strong-attachment-signal combo and doesn't
  broaden gate semantics for other callers.
- **SP-4 — Skip S133.** Plan §3 reserved S133 for mixed-cohort
  refinement. After S132's 4% result the only remaining miss is the
  024 body-vs-attachment conflict, which rule-boost work cannot resolve
  (the attachment signal is correct; the body signal is also correct;
  they disagree on intent). Pursuing a "complaint-over-attachment"
  precedence rule would either require per-cohort gates (scope creep)
  or an LLM re-read with both signals (already wired via
  `llm_context=true` but matrix shows no win on this fixture). Skip and
  document the ceiling.
- **SP-5 — Sprint P is additive on Sprint O.** No new DB migration,
  no new API endpoint, no new UI page. The `classifier_strategy`
  setting and the early-return logic both degrade gracefully when the
  flag is off. Rollback is a single env-var flip.

## What worked

- **The S131 measurement script caught the LLM regression on contracts
  before it shipped.** Without the 4-combo matrix we would have shipped
  `SKLEARN_FIRST` as Sprint P and regressed contract accuracy by 2
  fixtures. The matrix report made the regression visible in one table
  row, and the early-return fix followed naturally.
- **Sprint O's pure-function modularity paid off.** `extract_attachment_features`,
  `_attachment_signal_is_strong`, and `_apply_attachment_rule_boost`
  all compose cleanly. The S132 fix is three lines of orchestrator
  wiring + one new helper + one edit to `_keywords_first`. No
  structural refactor.
- **Real-stack integration tests caught a real bug.** The first draft
  of S132 relied on the `_apply_attachment_rule_boost` gate admitting
  `feedback` as a base label. Integration test flagged it immediately —
  `feedback` is not in `{unknown} ∪ EXTRACT_INTENT_IDS`, so the boost
  was a no-op. Fixed by force-relabelling to `unknown` in the
  early-return.

## What hurt

- **Matrix runs cost ~7 minutes each on the dev box.** Docling cold
  start + LLM latency + per-fixture PG round-trip adds up. The FU-4
  warmup script helps (~11x speedup on docling), but 25 fixtures × 4
  combos × ~1.5 s/fixture ≈ 2.5 min/matrix is the floor. Fine for
  S131/S132 but wouldn't scale to a per-PR matrix run in CI.
- **The PostToolUse ruff formatter stripped imports twice during S131
  script authoring.** Workaround was the same `_RUNTIME_HOOKS` pin
  pattern used in Sprint O. Added to a shared memory note for future
  sessions.

## Open follow-ups

- **SP-FU-1 — 024_complaint_about_invoice body-vs-attachment conflict
  precedence.** Sprint P ceiling on a single fixture. Options: (a) add
  a `"complaint"` keyword bucket to the extractor and block boost when
  it fires, (b) swap to `llm_first` strategy on this flag variant, (c)
  leave as known-miss. No target deadline — customer impact unknown.
- **SP-FU-2 — Matrix runs as CI artifact.** S131 script is operator-
  only today. A nightly / weekly GitHub Action that runs all 4 combos
  and posts the result as a dashboard snapshot would catch regressions
  on schema/classifier changes. Out of scope for v1.4.12.
- **SP-FU-3 — LLM-context per-prompt variant.** The `LLM_CONTEXT=true`
  combo is unit-tested but hurts 1 fixture. A dedicated Langfuse
  prompt variant (not just an appended system message) may close that
  gap. Sprint O out-of-scope list has this too.

## Carried (Sprint N / M / J, Sprint O retro residual)

Sprint O retro's "Resolved" list (FU-1, FU-2, FU-4, FU-5, FU-7,
OpenAPI drift detector) all merged before Sprint P. Sprint P closes
FU-3 + FU-6. Remaining cross-sprint carry (unchanged from Sprint O
retro):

- Sprint N: `CostAttributionRepository` ↔ `record_cost` consolidation,
  model-tier fallback ceilings → `CostGuardrailSettings`, Grafana panel
  for cost refusals, litellm pricing coverage as CI step,
  `CostSettings` umbrella, soft-quota / over-draft, dev-seed script.
- Sprint M: live Vault rotation E2E, `AIFLOW_ENV=prod` root-token
  guard, `make langfuse-bootstrap`, AppRole prod IaC, Langfuse v3→v4,
  `SecretProvider` registry slot.
- Sprint J: BGE-M3 weight cache CI artifact, Azure OpenAI Profile B
  live, coverage uplift (issue #7).
