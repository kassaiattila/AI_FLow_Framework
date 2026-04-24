# AIFlow v1.4.12 Sprint P — LLM-context + body-only + mixed cohort coverage

> **Status:** KICKOFF — S131 on 2026-05-05.
> **Branch:** `feature/p-s131-*` (cut from `main` @ `bdfe149`, Sprint O FU-7 squash-merge).
> **Predecessor:** v1.4.11 Sprint O (UC3 attachment-aware intent) + 3 retro follow-ups (FU-2 / FU-4 / FU-7) all merged.
> **Target tag (post-merge):** `v1.4.12`.
> **Parent plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 (UC3 hardening). Sprint P closes Sprint O's open `FU-3` (body-only/mixed coverage) and `FU-6` (LLM-context fixture measurement).

---

## 1. Why this sprint

Sprint O's 25-fixture corpus ends at **32% misclass** (56% baseline → 24 pts
absolute / 42.9% relative drop), but the win is concentrated in the
**attachment-carrying cohorts**:

| Cohort | Count | Sprint K baseline | Sprint O flag-on |
|---|---|---|---|
| invoice_attachment | 6 | 3/6 correct | **6/6 correct** |
| contract_docx | 6 | 2/6 correct | 5/6 correct |
| body_only | 6 | 3/6 correct | **3/6 correct** ← unchanged |
| mixed | 7 | 3/7 correct | **3/7 correct** ← unchanged |

The remaining **8 misclassifications** all live in cohorts where either no
attachment exists (body_only) or the attachment signal disagrees with the
body (mixed). Sprint O's attachment rule boost cannot help here — a
different lever is needed.

Two levers Sprint O already pre-wired but hasn't measured live:

1. **`AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT`** (S128 opt-in) — appends
   an attachment-summary system message to the LLM classification prompt.
   For body_only cohort this is a no-op (no attachment), but for mixed
   cohort it should help the LLM reconcile body-vs-attachment conflicts.
2. **Classifier strategy** — Sprint O measurement used `SKLEARN_ONLY` for
   speed + determinism. Switching to `SKLEARN_FIRST` (keyword → LLM
   fallback at < 0.6 confidence) lets the LLM rescue low-confidence
   body_only cases the keyword classifier mis-labels.

Sprint P measures both, then ships targeted improvements.

---

## 2. Discovery outcome (S131)

S131 produces `docs/uc3_llm_context_baseline.md` containing:

- **Misclass rate** on the 25-fixture corpus with four strategy combinations:
  1. `SKLEARN_ONLY` + `LLM_CONTEXT=false` ← Sprint O baseline (32%)
  2. `SKLEARN_ONLY` + `LLM_CONTEXT=true` ← FU-6 measurement (LLM-context-only effect; expected minimal because SKLEARN path skips _classify_llm)
  3. `SKLEARN_FIRST` + `LLM_CONTEXT=false` ← LLM-fallback without context
  4. `SKLEARN_FIRST` + `LLM_CONTEXT=true` ← full Sprint P target
- **Per-cohort breakdown** (invoice / contract / body_only / mixed).
- **Cost delta** — LLM call count × estimated cost per strategy.
- **Latency** — p50, p95 per strategy.

**Hard gate for S132 start:** combination (4) must show ≥ 20% relative
improvement over the Sprint O baseline on body_only + mixed cohorts
combined, OR the LLM path must reveal a specific failure mode that justifies
further work. Otherwise the sprint stops at S131 and documents the ceiling.

---

## 3. Session plan

### S131 — LLM-context baseline measurement
**Scope.**
- `scripts/measure_uc3_llm_context.py` — runs the 25-fixture corpus four
  times (one per strategy combo), persists results.
- `docs/uc3_llm_context_baseline.md` with the four-way comparison table +
  per-cohort + cost + latency.
- Sprint P plan + S132 NEXT.md + CLAUDE.md banner flip.

**Acceptance.**
- Script runs against real OpenAI + real Postgres; outputs report.
- Hard gate PASS (combo 4 shows meaningful improvement on body_only/mixed).
- If gate FAILS → document ceiling, skip S132/S133, jump to S134 close
  with "no-code sprint" note.

### S132 — Body-only cohort improvements
**Scope (conditional on S131 gate).** Identify specific failure modes
from S131's report:

- If LLM fallback rescues 2+ body_only fixtures → make `SKLEARN_FIRST` the
  orchestrator default for the attachment-intent flag-on path (currently
  hardcoded `SKLEARN_ONLY`).
- If LLM misclassifies too → improve keywords for the specific intents
  (marketing, notification) that fail; possibly adjust the rule-boost
  gate (e.g., let a high-confidence SKLEARN call through unmodified).
- 1 Playwright E2E on live stack: seed a body_only run, load detail page,
  assert the correct intent is shown.

**Acceptance.**
- Body_only cohort accuracy 3/6 → ≥ 5/6.
- Sprint K UC3 golden-path E2E still green.
- No regression on invoice/contract cohorts.

### S133 — Mixed cohort improvements
**Scope (conditional on S131 gate).**

- Mixed cohort is the hardest case: 024 (`complaint_about_invoice`) has
  a complaint body + invoice attachment; the correct answer is
  `complaint`, not `invoice_received`. Sprint O's body-label gate
  already protects this case, but the keyword classifier mis-labels it
  first.
- Enable LLM-context on this path — the LLM sees both the body and the
  attachment summary and should pick `complaint`.
- 1 Playwright E2E on live stack for the mixed conflict.

**Acceptance.**
- Mixed cohort accuracy 3/7 → ≥ 5/7.
- No regression on other cohorts.

### S134 — Sprint P close
**Scope.** Retro + PR description + CLAUDE.md numbers bump + tag
`v1.4.12` queued.

---

## 4. STOP conditions

**HARD (halt + escalate):**
1. S131 gate FAIL — combo 4 shows no meaningful improvement on
   body_only/mixed cohorts. Document ceiling, skip to S134 close.
2. Sprint K UC3 golden-path E2E regresses — halt until root-caused.
3. LLM cost per 25-fixture run > $0.20 — classification path is too
   expensive for default-on, rescope to per-tenant opt-in.
4. OpenAI rate-limit or outage persists > 30 min mid-sprint — halt and
   document, retry in next window.

**SOFT (proceed with note):**
- If LLM-context helps mixed cohort but hurts invoice_attachment by
  1-2 fixtures (net positive) — document and ship.
- If `SKLEARN_FIRST` pushes p95 latency from ~200 ms to > 2 s on body_only
  cohort (no LLM saved by keyword match) — document and gate behind a
  new `llm_fallback_for_body_only` flag.

---

## 5. Out of scope (explicit)

- Thread-aware classification (conversation history) — separate sprint.
- Per-tenant intent schema overrides — v2 architecture work.
- Non-English / non-Hungarian cohorts.
- OAuth-based live mailbox (Sprint O out-of-scope, still).
- Dedicated Langfuse prompt variant for attachment-aware classification
  (Sprint O out-of-scope, still).

---

## 6. Rollback plan

Sprint P is additive + flag-gated (same as Sprint O):

1. `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=false` (default) restores
   Sprint O FU-7 behaviour. Primary rollback lever.
2. If S132 flips the orchestrator default strategy (`SKLEARN_FIRST`), a
   second flag `AIFLOW_UC3_CLASSIFIER_STRATEGY_OVERRIDE` keeps the
   current `SKLEARN_ONLY` available for tenants that need speed.
3. Revert rollback: Sprint P PRs are 3 squash-merge commits, isolated.
4. Data rollback: none — no new tables, no Alembic migration.

---

## 7. Success metrics

| Metric | Source | Target |
|---|---|---|
| Body_only cohort accuracy | S132 measurement report | ≥ 5/6 (was 3/6) |
| Mixed cohort accuracy | S133 measurement report | ≥ 5/7 (was 3/7) |
| Overall misclass rate | 25-fixture corpus | ≤ 16% (was 32%) |
| LLM cost per 25-fixture run | measurement script | < $0.10 (operator-visible) |
| Sprint K UC3 golden-path E2E | existing 4 Playwright tests | green, 0 regressions |
| Unit test delta | pytest collect | +20 tests minimum |

---

## 8. Carry-over / NYITOTT

From Sprint O retro (post-FU merges):

- **Resolved:** FU-1 (live-API E2E), FU-2 (intent_class), FU-4 (docling
  warmup), FU-5 (resilience Clock seam), FU-7 (per-attachment cost),
  `/status` OpenAPI drift detector.
- **This sprint (P):** FU-3 + FU-6.
- **Remaining carry from Sprint N/M/J:** `CostAttributionRepository` ↔
  `record_cost` consolidation, model-tier fallback ceilings, Grafana
  panels, litellm pricing CI audit, `CostSettings` umbrella, soft-quota
  semantics, `scripts/seed_tenant_budgets_dev.py`. Sprint M: AppRole
  prod IaC, Langfuse v4, `SecretProvider` slot, live Vault rotation
  E2E. Sprint J: BGE-M3 weight cache CI artifact, Azure OpenAI Profile
  B live.
