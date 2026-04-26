# AIFlow v1.5.4 Sprint U — Operational hardening

> **Status:** KICKOFF on 2026-04-25 (S152).
> **Branch:** `feature/u-s{N}-*` (each session its own branch → PR → squash-merge).
> **Parent plan:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §6 (Sprint U operational hardening cohort).
> **Predecessor:** v1.5.3 Sprint T (PromptWorkflow consumer migration MERGED `fd2a8bc`, tag `v1.5.3` queued).
> **Target tag (post-merge):** `v1.5.4`.

---

## 1. Goal

Sprint U is the **carry-forward catch-up sprint**. After eight feature sprints (M / N / O / P / Q / R / S / T), each retro left a tail of operability follow-ups that individually didn't justify a sprint slot but collectively form real debt: CI gates that would have caught regressions earlier, settings classes ripe for consolidation, prompt-workflow descriptors that only cover one of three personas, operator scripts with inconsistent flags, Sprint Q golden-path papercuts. **Zero new functional capability, zero customer-visible feature.** The win is operability: faster CI signal, fewer footguns in the cost/settings surface, parity across PromptWorkflow personas, cleaner operator ergonomics.

**No skill code change** in the strict sense — `email_intent_processor`, `invoice_processor`, `aszf_rag_chat` baseline persona stay byte-stable on flag-off (Sprint T's golden paths must remain green throughout). Sprint U adds two new persona descriptors (`aszf_rag_chain_expert`, `aszf_rag_chain_mentor`) and wires them through the existing `_resolve_workflow_for_persona` carve-out from S150 — additive, default-off.

### Capability cohort delta

| Cohort | Sprint T close | Sprint U close (target) |
|---|---|---|
| CI gates (lint + unit + e2e) | 3 (lint, unit, e2e collect-only) | **5** (+ OpenAPI drift, + weekly 4-combo matrix as GHA) |
| Pre-commit hooks | ruff + pytest collect | **+ vite-build** (catches React-Aria/i18n breakage before push) |
| `*Settings` umbrella classes | 2 (`BudgetSettings`, `CostGuardrailSettings`) separate | **1** (`CostSettings` umbrella) |
| `CostPreflightGuardrail` reach | per-call + per-tenant period | **+ per-step ceiling consolidated** (ST-FU-3) |
| Cost recorder consolidation | `record_cost` + `CostAttributionRepository` parallel paths | **single attribution path** (SN-FU) |
| PromptWorkflow descriptors live | 3 (email_intent, invoice_extraction, aszf_rag baseline) | **5** (+ aszf_rag expert + mentor) |
| Live-stack Playwright coverage | `/budget-management`, `/extracted-fields`, `/rag/collections` | unchanged (SR-FU-4 deferred to Sprint V) |
| Operator script `--output` parity | inconsistent across `measure_uc1_*`, `run_nightly_rag_metrics`, `bootstrap_*` | **uniform `--output` JSON/text flag** |
| Sprint Q `issue_date` extraction | systematically misses (Sprint Q corpus) | **fixed** (SQ-FU-1) — accuracy lift target ≥ 90% on `issue_date` |
| Alembic head | 047 | 047 (no migration in Sprint U) |
| New endpoints / UI pages | — | 0 / 0 |

---

## 2. Sessions

### S152 — Kickoff (THIS SESSION)
**Scope.** Plan doc + carry-forward triage. Two deliverables: this plan doc and the optional `docs/sprint_u_plan.md` companion. 0 skill code change, 0 new tests, 0 Alembic. Carry-forward inventory mapped to S153–S156 (or deferred to Sprint V with rationale).

### S153 — CI hookups + tooling fixes
**Scope.** The lowest-risk batch first. Five small wins, each independently revertable:

1. **OpenAPI drift CI step.** `scripts/check_openapi_drift.py` already exists (Sprint O FU-1 era); wire it into `.github/workflows/ci.yml` as a `make api` boot + diff step. Catches a stale-uvicorn drift like the one that leaked through Sprint S S144.
2. **Weekly 4-combo matrix as GitHub Action.** Sprint P FU-2. The 4-combo (strategy × LLM-context) measurement script `scripts/measure_uc3_4combo_matrix.py` runs locally; promote to a `nightly-regression.yml` weekly job behind `secrets.OPENAI_API_KEY` (skip-by-default on PR runs).
3. **`vite build` pre-commit hook.** SR-FU-5. The Sprint R S140 mid-PR `react-i18next`→`useTranslate` fix was caught by CI; a pre-commit `cd aiflow-admin && npx vite build --mode development` would have caught it locally. Hook lives in `.husky/pre-commit` or `.git/hooks/pre-commit` template.
4. **ruff-strips-imports tooling fix.** ST-FU-5. The Sprint T retro decision log entry ST-4 documents the workaround (bundle imports + first usage in single Edit). Sprint U finds the underlying ruff config gap (`select` rule that's stripping unused-but-needed imports inside `if TYPE_CHECKING` or guard blocks) and either pins a config tweak or files a tracked exception list.
5. **BGE-M3 weight cache as CI artifact.** Carried Sprint J (and Sprint S touched it via `actions/cache@v4` step in `nightly-regression.yml`). Sprint U promotes the cache step from `nightly-regression.yml` to the standard `ci.yml` integration job so 1024-dim integration tests un-skip on every PR (today they only un-skip nightly).

**Gate.** All 5 wins land on `main` via 5 sub-PRs (or one bundled PR — operator's call at session-time). CI must stay green throughout. **No skill code change.**

**Expected diff.** ~80 lines across `.github/workflows/`, `.husky/`, `pyproject.toml` (ruff config), `Makefile`. **0 new tests** (these *are* tests / gates). 0 unit / 0 integration delta.

**Risk.** R1 — CI flake amplification (see §4 R1).

### S154 — Cost / Settings consolidation
**Scope.** Pay down accumulated Sprint N + Sprint T cost-surface debt. Four consolidations, all behind feature-stable refactors (no behaviour change):

1. **`CostSettings` umbrella class.** SN-FU. Today `BudgetSettings` (env prefix `AIFLOW_BUDGET__`) and `CostGuardrailSettings` (env prefix `AIFLOW_COST_GUARDRAIL__`) live as siblings on `Settings`. Roll them into a single `CostSettings` (env prefix `AIFLOW_COST__`) with sub-fields `cost.budget.*` and `cost.guardrail.*`. **Backward-compat shim** — old env names continue to read via Pydantic `validation_alias` for one minor version, deprecation logged on first access.
2. **`CostAttributionRepository` ↔ `record_cost` consolidation.** SN-FU. Two parallel cost-recording paths exist: (a) `CostAttributionRepository.record(...)` writes to `cost_records` table directly; (b) `record_cost(...)` helper in `aiflow.observability.cost` does its own writes via SQLAlchemy session. Pick one (recommend the repository path since `aggregate_running_cost` already uses it), migrate the other call sites, and delete the redundant helper. **Audit script** `scripts/audit_cost_recording.py` greps for both call surfaces to confirm zero stragglers.
3. **Per-step cost ceiling consolidation.** ST-FU-3. Sprint T S149 introduced a local `CostEstimator` + `CostGuardrailRefused` raise inside `invoice_processor.workflows.process` to enforce `metadata.cost_ceiling_usd` from the workflow descriptor. Lift this into `CostPreflightGuardrail.check_step(step_name, projected_usd)` so any `PromptWorkflowExecutor` consumer can reuse it (not just the invoice processor). The two existing call sites refactor to use the new `check_step` API; the local helper deletes.
4. **Model-tier fallback ceilings.** SN-FU-2. Today `CostEstimator` falls back to a hard-coded $0.05/$0.15 per-tier ceiling when `litellm.cost_per_token` returns no match (unknown model). Move the ceiling table into `CostGuardrailSettings.tier_fallback_usd: dict[str, float]` so operators tune it via env without a code change. Default values match today's hard-codes.

**Gate.** Sprint T golden paths (UC3 4/4 + UC1 ≥ 75% / `invoice_number` ≥ 90% + UC2 MRR@5 ≥ 0.55) all green flag-off and flag-on. Sprint N integration tests (`tests/integration/api/test_tenant_budgets_api.py` + `tests/integration/guardrails/test_cost_preflight_guardrail.py`) all green. Plus a new contract test asserting the env-alias shim resolves both old and new env names to the same value.

**Expected diff.** ~250 lines across `aiflow/config/cost.py` (new umbrella), `aiflow/services/tenant_budgets/`, `aiflow/guardrails/cost_preflight.py`, `aiflow/observability/cost.py`, plus migration of ~6–8 call sites. **+8–14 unit tests** (umbrella round-trip + alias resolution + `check_step` API + tier-fallback env override + `record_cost` deletion contract test). **0 integration test delta** (existing integration tests must keep passing under the consolidated path). 0 endpoint / UI change.

**Risk.** R2 — env-alias shim drift (see §4 R2).

### S155 — Persona descriptors (RESCOPED 2026-04-26)
**Scope.** **NARROWED** in audit `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` to ship only the additive ST-FU-2 expert/mentor PromptWorkflow descriptors. SR-FU-4 (live Playwright `/prompts/workflows`) and SR-FU-6 (Langfuse workflow listing) **deferred to Sprint V/W** — they sit more naturally next to the doc-recognizer admin page work; pulling them into Sprint U bloated session risk without unblocking Sprint V scope.

1. **Expert/mentor persona descriptors.** ST-FU-2. Author `prompts/workflows/aszf_rag_chain_expert.yaml` + `aszf_rag_chain_mentor.yaml` mirroring the baseline 4-step DAG (rewrite_query + system_<role> + answer + extract_citations) but pointing the `system_*` step at `system_prompt_expert.yaml` / `system_prompt_mentor.yaml` respectively. Update `_resolve_workflow_for_persona(role)` from S150 to return the new descriptors when `role in ("expert","mentor")` and flag-on. Default-off preserved — flag-off keeps the legacy direct-prompt path for both personas, byte-stable.
2. ~~**Live-stack Playwright for `/prompts/workflows`.** SR-FU-4.~~ **DEFERRED to Sprint V/W** — folded into Sprint V SV-4 admin UI scope or a follow-up post-Sprint-V.
3. **`vite build` pre-commit hook.** *Already in S153 batch 3.* Cross-reference only.
4. ~~**Langfuse workflow listing surface.** SR-FU-6.~~ **DEFERRED to Sprint V/W** — re-evaluate after Langfuse v3→v4 server migration decision; operator may choose to handle both at once.

**Gate.** Sprint J UC2 MRR@5 ≥ 0.55 on Profile A baseline persona (regression check — the new persona descriptors must not bleed onto the baseline path). Plus a flag-on parity check for expert/mentor: same answer text on a 5-question fixture set (`data/fixtures/rag_metrics/uc2_persona_smoke.json`) within ±0 token-difference (deterministic prompt-resolution test, no LLM call).

**Expected diff.** ~80 lines (2 new YAML descriptors + persona resolver update). **+4–6 unit tests** (persona resolver returns descriptor for expert/mentor, descriptor loader DAG-validates the new YAMLs). **0 integration** (the deferred Langfuse listing test goes with SR-FU-6 to Sprint V). **0 live Playwright** (the deferred SR-FU-4 spec also goes to Sprint V).

**Risk.** R3 — persona variant LLM nondeterminism (see §4 R3). Rescope **lowers** session risk to "low" since SR-FU-4/6 are out of scope.

### S156 — Sprint Q polish + operator script parity
**Scope.** Close the four SQ-FU-* items + ST-FU-4:

1. **`issue_date` prompt/schema fix.** SQ-FU-1. Sprint Q's 10-fixture corpus run hit 100% on every field except `issue_date` (systematically missed — extraction returns the email send-date, not the invoice's stamped issue date). Two-part fix: (a) prompt clarification — explicit "ignore email metadata, read the date stamped on the invoice document body"; (b) post-extraction validator — if `issue_date` equals the email envelope date and the body has a parseable date pattern, prefer the body match. Re-measure on the 10-fixture corpus; target `issue_date` accuracy ≥ 90%.
2. **Pre-boot docling warmup in `make api`.** SQ-FU-2. Sprint O FU-4 added a warmup hook on first request, but the first-request latency is ~6s. Promote to a `make api`-time warmup so dev sessions don't pay it. Lazy-import guard so test runs don't trigger docling load.
3. **`_parse_date` ISO roundtrip.** SQ-FU-4. The parser today returns `datetime.date` for some formats and ISO `str` for others depending on regex match. Normalize to always-ISO `str` (`YYYY-MM-DD`) at the boundary so downstream consumers (`ExtractedFieldsCard.tsx` + `EmailDetailResponse.extracted_fields`) get one shape.
4. **Operator parity scripts uniform `--output` flag.** ST-FU-4. Today `scripts/measure_uc1_golden_path.py` writes to stdout, `scripts/run_nightly_rag_metrics.py` writes to a hard-coded `data/metrics/...jsonl`, `scripts/bootstrap_bge_m3.py` and friends each have their own conventions. Add a uniform `--output {text|json|jsonl,path}` argspec via a shared `aiflow.scripts.common.argparse_output()` helper; migrate the 5 operator scripts to use it. Backward-compat: default behaviour unchanged when flag absent.
5. **Corpus extension to 25 (SQ-FU-3).** *Optional* if bandwidth allows. The Sprint Q 10-fixture corpus would benefit from doubling — but each new fixture is operator-curation work (anonymized real invoices). **Defer to Sprint V** if the session is full.

**Gate.** Sprint Q UC1 golden-path slice (3-fixture CI) overall ≥ 75% / `invoice_number` ≥ 90% **and** `issue_date` ≥ 90% on the full 10-fixture operator measurement run. Mirrors Sprint Q gate plus the new `issue_date` line.

**Expected diff.** ~180 lines (prompt edit + post-extract validator + `make api` warmup hook + `_parse_date` normalizer + `argparse_output` helper + 5 script migrations). **+8–12 unit tests** (issue_date validator decisions, `_parse_date` shape stability, `argparse_output` flag parsing). **0 new integration** (Sprint Q's existing integration test re-runs with the fix in place; the operator measurement script is the validation vehicle). 0 endpoint / UI change beyond `extracted_fields.issue_date` becoming reliably populated.

**Risk.** R4 — `issue_date` regression on already-correct fixtures (see §4 R4).

### S157 — Sprint U close + Sprint V kickoff plan publish
**Scope.** `docs/sprint_u_retro.md`, `docs/sprint_u_pr_description.md`, CLAUDE.md banner flip + key-numbers update, PR opened against `main`, tag `v1.5.4` queued. Explicit skipped-items enumeration. **Plus** the Sprint V kickoff plan dokumentum: `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` (per the audit decision in `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`).

Closes carry-forward IDs ST-FU-2/3/4/5, SR-FU-5, SQ-FU-1/2/4, SN-FU subset (cost-settings consolidation).

Carries forward **to Sprint V** (headline scope):
- **NEW** Generic document recognizer skill (refactor `invoice_finder` → `document_recognizer`; pluggable doc-type registry; 5 initial doc-types: hu_invoice, hu_id_card, hu_address_card, eu_passport, pdf_contract)
- SR-FU-4 live Playwright `/prompts/workflows` (rescoped from S155)
- SR-FU-6 Langfuse workflow listing (rescoped from S155)

Carries forward **to post-Sprint-V audit**:
- SS-FU-1/5 customer→tenant_id rename
- SM-FU-1/2/4/5 Vault prod hardening + Langfuse v3→v4
- SS-SKIP-2 Profile B Azure live MRR@5 (still credit-blocked)
- SJ-FU-7 coverage uplift 70%→80%
- SN-FU-3 Grafana panel
- SQ-FU-3 corpus extension to 25
- SP-FU-1 UC3 `024_complaint` body-vs-attachment intractable conflict

---

## 3. Plan, gate matrix

| Session | Theme | Golden-path test | Threshold | Rollback path |
|---|---|---|---|---|
| S153 | CI hookups + tooling | All existing CI green (lint + unit + e2e collect-only + `nightly-regression.yml`) | 0 new red, no flake injection | Revert per-batch (each of the 5 wins lands as its own commit so any can revert independently) |
| S154 | Cost/Settings consolidation | UC3 4/4 + UC1 ≥ 75% / invoice_number ≥ 90% + UC2 MRR@5 ≥ 0.55 + Sprint N integration tests | Identical numbers to Sprint T close (zero behaviour change refactor) | Revert squash; env-alias shim ensures old `AIFLOW_BUDGET__*` / `AIFLOW_COST_GUARDRAIL__*` env names keep working during transition |
| S155 | PromptWorkflow ergonomics + persona descriptors | UC2 baseline MRR@5 ≥ 0.55 (regression) + persona-smoke ±0 token-diff on 5-question expert/mentor fixture | Baseline unchanged; expert/mentor flag-on parity within ±0 tokens (deterministic prompt-resolution test, no LLM call) | Drop expert/mentor from `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` (instant runtime disable, baseline unaffected) |
| S156 | Sprint Q polish + operator script parity | UC1 ≥ 75% / invoice_number ≥ 90% (CI 3-fixture); operator full corpus `issue_date` ≥ 90% | issue_date lift the headline; other fields keep their Sprint Q numbers within ±5pp | Prompt + validator changes are isolated to `invoice_processor` extraction; `make api` warmup gated by `AIFLOW_DOCLING_WARMUP=true` (default false) |

**Threshold column blocks merge.** Any session that fails its gate halts; the operator either rolls forward (debug) or reverts the session and reschedules.

---

## 4. Risk register

### R1 — CI flake amplification in S153
Adding two new CI gates (OpenAPI drift + weekly 4-combo matrix) increases the surface where a flaky network call or a stale-uvicorn cache can red the pipeline. The 4-combo matrix in particular hits real OpenAI; if rate-limited, the weekly job falsely reds.

**Mitigation.** OpenAPI drift step is hermetic (no network — diff against committed `openapi.json` snapshot; refresh-on-commit pre-commit hook keeps it current). 4-combo matrix runs only as a **scheduled weekly job**, not on PR runs, so a transient OpenAI hiccup doesn't block merges. Skip-by-default behind `AIFLOW_RUN_4COMBO_MATRIX=1` + `secrets.OPENAI_API_KEY` so forks don't try to run it.

**Detection.** Two consecutive weekly red runs without an obvious code cause → flake; quarantine that job and triage in S157 retro.

### R2 — Env-alias shim drift in S154
Pydantic `validation_alias` lets us read `AIFLOW_BUDGET__LIMIT_USD` and `AIFLOW_COST__BUDGET__LIMIT_USD` to the same field, but both must point at the same source-of-truth value. If a deployment sets *both* env names with different values (transition state), Pydantic resolves whichever the alias graph picks first — silent surprise.

**Mitigation.** Validator on the umbrella `CostSettings` raises `AmbiguousEnvAlias` if both old and new env names are set with non-equal values for the same field. Deprecation warning logged on **first read** of the old name (not on every read — once-per-process). Document the deprecation timeline in `docs/cost_settings_migration.md` (target: drop old aliases in Sprint X / v1.6.0).

**Detection.** New unit test asserts the validator raises on conflicting both-set; CI runs the validator on a synthetic `os.environ`.

### R3 — Persona variant LLM nondeterminism in S155
The expert/mentor persona descriptors point the `system_*` step at different system prompts, so flag-on / flag-off byte-parity is *not* a meaningful gate (the LLM call genuinely produces different output by design — we want a different persona). The gate has to be **prompt-resolution byte-parity** (does the executor build the same prompt the legacy path would have built?), not output-text byte-parity.

**Mitigation.** The persona-smoke fixture is **resolution-only** — assert that the resolved prompt fed to `LLMClient.complete()` is byte-identical between flag-on and flag-off. Skip the actual LLM call (mock the client) so the test is deterministic and CI-fast. Flag-on parity check is therefore a contract test, not an end-to-end LLM round-trip.

**Detection.** Snapshot-test the resolved prompt under flag-off, replay under flag-on, diff. Any non-zero diff = real bug, halts S155.

### R4 — `issue_date` regression on already-correct fixtures in S156
Sprint Q's 10-fixture corpus has 100% accuracy on most fields. The `issue_date` fix shifts the prompt + adds a body-match validator; could regress an already-correct fixture if the body has multiple date patterns.

**Mitigation.** Re-measure on the **full 10-fixture corpus**, not just the 3-fixture CI slice. Gate threshold: every previously-correct field stays correct (no regression on `vendor` / `buyer` / `invoice_number` / `currency` / `due_date` / `gross_total`); `issue_date` lifts to ≥ 90%. If any other field regresses, halt and triage.

**Detection.** Side-by-side run report `docs/sprint_u_uc1_remeasure.md` shows the per-field accuracy delta vs Sprint Q baseline (85.7%).

### R5 — Default-off rollout (no per-tenant blast radius)
S155 expert/mentor persona descriptors land behind the same `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + per-skill `SKILLS_CSV` opt-in that S150 used. Default-off → zero rollback risk. S153–S156 are otherwise pure refactors / hooks; no per-tenant flag needed.

**Mitigation.** This is by design. Document the enablement sequence in `docs/sprint_u_plan.md`.

**Detection.** Flag-off CI run on every PR proves the legacy path is byte-stable.

---

## 5. Follow-up table

Carry-forwards (Sprint M / N / O / P / Q / R / S / T → Sprint U) + Sprint U's own SU-FU-X entries.

| ID | Description | Source | Target |
|---|---|---|---|
| ST-FU-2 | Expert/mentor persona PromptWorkflow descriptors | Sprint T retro | **Sprint U S155** |
| ST-FU-3 | Per-step cost ceiling consolidation into `CostPreflightGuardrail.check_step()` | Sprint T retro | **Sprint U S154** |
| ST-FU-4 | Operator parity scripts uniform `--output` flag | Sprint T retro | **Sprint U S156** |
| ST-FU-5 | ruff-strips-imports tooling fix | Sprint T retro | **Sprint U S153** |
| SR-FU-4 | Live-stack Playwright for `/prompts/workflows` admin page | Sprint R retro | **Sprint U S155** |
| SR-FU-5 | `vite build` pre-commit hook | Sprint R retro | **Sprint U S153** |
| SR-FU-6 | Langfuse workflow listing surface | Sprint R retro | **Sprint U S155** (deferable to Sprint V if Langfuse v4 migration arrives first) |
| SQ-FU-1 | `issue_date` prompt/schema fix | Sprint Q retro | **Sprint U S156** |
| SQ-FU-2 | Pre-boot docling warmup in `make api` | Sprint Q retro | **Sprint U S156** |
| SQ-FU-3 | UC1 corpus extension to 25 fixtures | Sprint Q retro | **Sprint V** (operator curation work; defer if S156 full) |
| SQ-FU-4 | `_parse_date` ISO roundtrip | Sprint Q retro | **Sprint U S156** |
| SP-FU-1 | LLM-context fixture measurement | Sprint P retro | **Sprint V** (covered by weekly 4-combo matrix once S153 GHA lands) |
| SP-FU-2 | Weekly 4-combo matrix as GitHub Action | Sprint P retro | **Sprint U S153** |
| SP-FU-3 | UC3 misclass `024_complaint_about_invoice` body-vs-attachment conflict | Sprint P retro | **Sprint V** (legitimate ambiguity; needs UI escalation, not classifier fix) |
| SN-FU-* | `CostSettings` umbrella + `record_cost` consolidation + model-tier fallback ceilings | Sprint N retro | **Sprint U S154** |
| SN-FU-Grafana | `cost_guardrail_refused` vs `cost_cap_breached` Grafana panel | Sprint N retro | **Sprint V** (Grafana panel work is monitoring-tier, batch with Langfuse v4) |
| SM-FU-rotation | Live Vault rotation E2E | Sprint M retro | **Sprint V** (infrastructure-tier; needs staging Vault) |
| SM-FU-prod | `AIFLOW_ENV=prod` root-token guard + AppRole prod IaC | Sprint M retro | **Sprint V** (infrastructure-tier) |
| SM-FU-langfuse | Langfuse v3→v4 server migration | Sprint M retro | **Sprint V** (server migration; needs runbook + staging) |
| SM-FU-bge | BGE-M3 weight cache as standard CI artifact (not just nightly) | Sprint M / J retro | **Sprint U S153** |
| SS-FU-1 / SS-FU-5 | `customer` → `tenant_id` rename | Sprint S retro | **Out of Sprint U** — separate refactor sprint |
| SS-SKIP-2 | Profile B Azure OpenAI live MRR@5 | Sprint S retro | Azure credit landing — **Out of Sprint U** |
| ST-SKIP-1 | Conditional Azure Profile B live test | Sprint T retro | **Same as SS-SKIP-2** |

---

## 6. Test count expectations

| Bucket | Sprint T close | Sprint U close (target) | Delta |
|---|---|---|---|
| Unit tests | 2424 | **2446–2460** | **+22 to +36** |
| Integration tests | ~116 | **~117** | **+1** (S155 Langfuse listing — skip-by-default) |
| E2E tests | 430 | 430 (unchanged) | 0 |
| Live Playwright (`tests/ui-live/`) | 4 (`/budget-management`, `/extracted-fields`, `/rag/collections`, `/runs`) | **5** (+ `/prompts/workflows`) | **+1** |
| Alembic head | 047 | 047 (unchanged) | 0 |
| New endpoints | 196 | **196 or 197** (S155 Langfuse listing may add 0 endpoint if extending an existing route, or +1 if standalone) | 0 or +1 |
| New UI pages | 26 | 26 | 0 |
| New CI jobs | 0 | **+2** (OpenAPI drift, weekly 4-combo matrix as GHA) | +2 |
| New pre-commit hooks | 0 | **+1** (`vite build`) | +1 |

The 2424→2446–2460 unit count is the cumulative S153 (~0) + S154 (+8 to +14) + S155 (+6 to +10) + S156 (+8 to +12) range. S153 doesn't add unit tests because its deliverables *are* CI gates / hooks. S157 close adds 0 (docs only).

---

## 7. Definition of done — per session

1. **Green gate test** at the threshold listed in §3 gate matrix.
2. **Flag-off smoke** confirms zero behaviour change on the affected golden path (Sprint T baselines: UC3 4/4 + UC1 ≥ 75% / invoice_number ≥ 90% + UC2 MRR@5 ≥ 0.55).
3. **`ruff check src/ tests/`** + **`cd aiflow-admin && npx tsc --noEmit`** clean.
4. **Live Playwright smoke** where applicable (S155 only — adds the `/prompts/workflows` live spec).
5. Session-close generates `docs/sprint_u_session_<N>_retro.md` (lightweight per-session note) + queues NEXT.md for the next session.
6. Skipped-items tracker (§8 below) updated with any new pytest.skip / deferred follow-up.

## 8. Skipped items tracker (S152 → S157)

Session-close per session must enumerate + explicit unskip-condition:

| ID | Session | Item | Unskip condition |
|---|---|---|---|
| ST-SKIP-1 | S152 (carry) | `tests/unit/providers/embedder/test_azure_openai.py::test_azure_openai_embed_real_api` — conditional Azure Profile B live | Azure credit (`AIFLOW_AZURE_OPENAI__ENDPOINT` + `__API_KEY` env) |
| SU-SKIP-1 | S153 | Weekly 4-combo matrix GHA — skip-by-default on PR runs (only nightly/weekly) | `secrets.OPENAI_API_KEY` available + scheduled trigger |
| SU-SKIP-2 | S155 | Langfuse listing real-server integration — skip-by-default behind `AIFLOW_RUN_LIVE_LANGFUSE=1` | Live Langfuse instance reachable from CI runner |
| *TBD* | S153+ | *(append during execution)* | — |

---

## 9. STOP conditions (HARD)

1. **Any per-session golden-path threshold failed** → halt + escalate. Either fix forward in the same session or revert and reschedule.
2. **Flag-off smoke regression** on UC3 4/4 / UC1 / UC2 baselines → halt; the consolidation has leaked behaviour change. Roll back the session's diff entirely.
3. **`alembic upgrade head` ≠ 047** at any session start → drift outside Sprint U scope; investigate before opening the session.
4. **Env-alias shim raises `AmbiguousEnvAlias` on a real deployment env** during S154 → halt; either operator fixes the env or the rollout sequence needs sequencing.
5. **`issue_date` fix regresses an already-correct field** during S156 → halt; the post-extraction validator is too aggressive.
6. **Operator declines the Sprint U scope mid-stream** (e.g., a higher-priority customer escalation lands) → halt; reschedule to Sprint V.

## 10. Rollback

- Per-session: each session is a single squash-merge — `git revert <squash>` reverts cleanly.
- S153 sub-batches: each of the 5 wins lands as its own commit so any can revert independently.
- S154 env-alias shim: keeps old `AIFLOW_BUDGET__*` / `AIFLOW_COST_GUARDRAIL__*` env names working during transition; revert is just dropping the new umbrella class.
- S155 persona descriptors: drop expert/mentor from `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` (instant runtime disable, baseline unaffected).
- S156 `issue_date` fix: prompt + validator changes isolated to `invoice_processor` extraction; revert restores the systematic-miss baseline.
- Schema: 0 Alembic in Sprint U → no DB rollback required.

## 11. Out of scope (Sprint U)

- **Server migrations.** Langfuse v3→v4 (SM-FU-langfuse) and live Vault rotation E2E (SM-FU-rotation) need their own runbook + staging + staged rollout — too heavy for shared sprint, deferred to Sprint V.
- **Infrastructure changes.** AppRole prod IaC (SM-FU-prod), `AIFLOW_ENV=prod` root-token guard — Sprint V.
- **`customer` → `tenant_id` model rename.** SS-FU-1 / SS-FU-5 — separate refactor sprint per Sprint S close.
- **Profile B Azure OpenAI live MRR@5.** SS-SKIP-2 — Azure credit pending.
- **UC1 corpus extension to 25 fixtures.** SQ-FU-3 — operator-curation work; defer to Sprint V if S156 full.
- **Grafana panels** for `cost_guardrail_refused` vs `cost_cap_breached`. SN-FU-Grafana — batch with Langfuse v4 server migration in Sprint V.
- **New skills consuming `PromptWorkflowExecutor`** beyond the existing 3 + the new expert/mentor variants. Additional descriptors land in their own sprints.
- **UC3 `024_complaint_about_invoice` body-vs-attachment conflict.** SP-FU-3 — needs UI escalation surface, not classifier fix; Sprint V.
- **Cost-aware routing escalation** (Candidate A from S152 triage — `PolicyEngine.pick_model_tier()`, pipeline-level cumulative budget tracker). Sprint V or later.
