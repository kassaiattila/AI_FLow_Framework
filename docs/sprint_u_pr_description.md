# Sprint U — Operational hardening + carry-forward catch-up (v1.5.4)

> **Already-merged sub-PRs:** #44 (S152 kickoff) · #45 (S153 + audit doc) · #46 (S154 cost consolidation) · #47 (S155 persona descriptors) · #48 (S156 Sprint Q polish)
> **This PR:** #?? (S157 close — retro + Sprint V kickoff plan publish + tag `v1.5.4` prep)
> **Cumulative diff vs Sprint T tip (`fd2a8bc`):** +5400 / −16500 LOC (16400 lines of `docs/api/openapi.json` re-serialization in S153)
> **Tag (post-merge):** `v1.5.4`

## Summary

Sprint U is the **carry-forward catch-up sprint** the project owed itself after eight feature sprints (M / N / O / P / Q / R / S / T). Each retro left a tail of operability follow-ups that individually didn't justify a sprint slot but collectively formed real debt. **Zero new functional capability, zero customer-visible feature.** The win is operability: faster CI signal, fewer footguns in the cost/settings surface, parity across PromptWorkflow personas, cleaner operator ergonomics, and the first `issue_date` accuracy fix the Sprint Q corpus has carried since 2026-04-04.

5 PRs merged in 2 calendar days; this PR (S157) ships the close docs + the Sprint V kickoff plan that Sprint V will execute against.

## What ships in S157 (this PR)

- `docs/sprint_u_retro.md` — retrospective covering all 5 sub-PRs (#44–#48) with decisions log SU-1..SU-7, what worked, what hurt, and 7 follow-ups (SU-FU-1..SU-FU-4 + SR-FU-4/6 deferred + ST-FU-4-followup).
- `docs/sprint_u_pr_description.md` — this document.
- `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` — **Sprint V kickoff plan** (formal sprint plan dokumentum derived from `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` "Sprint V vázlat" section). 5-session plan SV-1..SV-5, gate matrix, risk register R1–R5, skipped tracker.
- `CLAUDE.md` — Sprint U DONE banner flip + key numbers update (2424 → 2475 unit, 3 → 5 PromptWorkflow descriptors, 2 → 4 `ci.yml` gates).
- `session_prompts/NEXT.md` — points to SV-1 (Sprint V kickoff session — DocTypeDescriptor Pydantic + skill rename + safe-eval).

## Sub-PR digest (already merged)

### #44 S152 — Sprint U kickoff plan + carry-forward triage

- `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` (11-section plan mirroring Sprint T structure)
- `docs/sprint_u_plan.md` (operator-facing companion)
- 4 execution sessions + close planned (S153–S157)

### #45 S153 — CI hookups + tooling fixes (5 micro-wins)

1. OpenAPI drift CI step → new `openapi-drift` job in `ci.yml` (caught real Sprint S S144 drift on first run, snapshot refreshed)
2. Weekly UC3 4-combo matrix as GHA → `nightly-regression.yml` Mon 07:00 UTC + workflow_dispatch (skip-by-default on `OPENAI_API_KEY` missing)
3. `vite build` pre-commit hook → `scripts/hooks/pre-commit` + `make install-hooks`
4. `extend-unsafe-fixes = ["F401"]` ruff config (mid-Edit unused-import auto-removal mitigation; ST-FU-5)
5. BGE-M3 weight cache promoted from nightly to PR-time CI → new `integration-1024-dim` job

**Plus:** `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` (audit + Sprint U S155 rescope + Sprint V direction) published as part of the same PR.

### #46 S154 — Cost / Settings consolidation (4 wins)

1. `CostSettings` umbrella class (`AIFLOW_COST__*`; legacy `AIFLOW_BUDGET__*` + `AIFLOW_COST_GUARDRAIL__*` continue to work)
2. `record_cost(...)` rewritten as thin shim over `CostAttributionRepository.insert_attribution(...)` (single DB-write path; **inline DDL hack removed**)
3. `CostPreflightGuardrail.check_step()` per-step API + 4 new `PreflightReason` literals (ST-FU-3)
4. `tier_fallback_*_per_1k` env-tunable JSON via `CostGuardrailSettings` (SN-FU-2)

**+22 unit tests · 0 integration delta · 0 endpoint / UI / Alembic.**

### #47 S155 — Expert + mentor PromptWorkflow descriptors (ST-FU-2)

**Rescoped to ST-FU-2 only.** SR-FU-4 (live Playwright `/prompts/workflows`) and SR-FU-6 (Langfuse listing) deferred to Sprint V/W per the audit decision.

- 2 new YAML descriptors: `prompts/workflows/aszf_rag_chain_expert.yaml` + `aszf_rag_chain_mentor.yaml`
- `_PERSONA_WORKFLOW_MAP` + `_PERSONA_SYSTEM_STEP_MAP` in `query.py` (persona-aware step lookup; `generate_answer` no longer hard-codes `system_baseline`)
- 4 existing S150 "expert/mentor always falls through" tests UPDATED + 4 new flag-OFF parity tests
- Drive-by: `from typing import Any` import in `bpmn.py` (pre-existing F821 the S153 ruff change kept in scope)

**+4 net unit (+8 new − 4 obsolete) · 0 integration · 0 Alembic.**

### #48 S156 — Sprint Q polish + operator script parity (4 wins)

1. `issue_date` prompt + schema fix (SQ-FU-1; `Field(validation_alias=AliasChoices(...))`, no Alembic, dict normalization, SQL INSERT prefers `issue_date`, `inv.header.invoice_date` `@property` for byte-stable callers)
2. `_parse_date_iso` ISO normalizer at JSON-payload boundary (SQ-FU-4; regex char-class bug fix)
3. `make api` docling warmup gate (`AIFLOW_DOCLING_WARMUP=true`; default off)
4. `argparse_output()` helper + `audit_cost_recording.py` migration (ST-FU-4; 4 remaining scripts tracked as ST-FU-4-followup)

**+25 unit tests · 0 integration · 0 endpoint / UI / Alembic.**

## Cumulative metrics

| Metric | Sprint T tip | Sprint U tip | Delta |
|---|---|---|---|
| Unit tests | 2424 | **2475** | **+51** |
| Integration tests | ~116 | ~116 | 0 |
| API endpoints | 196 | 196 | 0 |
| API routers | 31 | 31 | 0 |
| UI pages | 26 | 26 | 0 |
| Alembic head | 047 | **047** | **0** (no DB change) |
| PromptWorkflow descriptors | 3 | **5** | **+2** |
| `ci.yml` jobs | 2 | **4** | **+2** (`openapi-drift`, `integration-1024-dim`) |
| `nightly-regression.yml` jobs | 4 | **5** | **+1** (`uc3-4combo-matrix` weekly) |
| Pre-commit hooks (project) | 0 | **1** | **+1** (vite-build, install via `make install-hooks`) |
| Settings classes | 2 separate | **+ 1 umbrella** | additive |
| Operator scripts on uniform `--output` | 1 (`run_nightly_rag_metrics`) | **2** (+ `audit_cost_recording`) | **+1** of 5 (4 ST-FU-4-followup) |

## Validation checklist

- [x] All 5 sub-PRs (#44–#48) merged on `main` with green CI
- [x] Pre-commit hook (lint + 2475 unit, ~1.5 min) green for every Sprint U commit
- [x] OpenAPI drift gate (`scripts/check_openapi_drift.py`) reports `[ok]` on `main` (snapshot up-to-date through S153)
- [x] Sprint T golden paths unchanged (UC1 ≥ 75% / `invoice_number` ≥ 90% on CI 3-fixture slice; UC2 MRR@5 ≥ 0.55 baseline; UC3 4/4 email intent)
- [x] Default-off rollout preserved — flag-off `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` + `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""` keeps all 3 skills + 2 new persona descriptors on the legacy direct-prompt path byte-stable
- [x] Backward-compat: `record_cost()`, `inv.header.invoice_date`, `AIFLOW_BUDGET__*` env, `AIFLOW_COST_GUARDRAIL__*` env all keep working
- [ ] **Sprint V SV-1 verification** (first action post-merge): operator runs `scripts/measure_uc1_golden_path.py` on the full 10-fixture corpus and confirms `issue_date` accuracy ≥ 90% (SU-FU-4)

## Test plan

- [ ] CI runs all jobs green (lint+unit, admin-build, openapi-drift, integration-1024-dim, e2e)
- [ ] Manual `gh workflow run nightly-regression.yml` to verify the new `uc3-4combo-matrix` job triggers cleanly
- [ ] Local: `make install-hooks` + edit something in `aiflow-admin/src/` + commit → vite build runs
- [ ] Local: `make openapi-snapshot` succeeds and exit code 0
- [ ] Local: `AIFLOW_DOCLING_WARMUP=true make api` triggers warmup phase before uvicorn
- [ ] Local: `python scripts/audit_cost_recording.py --output json` emits structured payload
- [ ] Tag `v1.5.4` queued for post-merge

## Carry-forward to Sprint V

Sprint V's headline scope is **the generic document recognizer skill** (UC1-General) — `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` (published in this PR) details:

- Refactor `invoice_finder` → `document_recognizer` skill
- Pluggable doc-type registry (5 initial types: `hu_invoice`, `hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`)
- 3-stage classification pipeline (parse → rule-scorer → LLM fallback)
- 5 document intents (`process` / `route_to_human` / `rag_ingest` / `respond` / `reject`)
- Multi-tenancy via `data/doctypes/_tenant/<tenant_id>/<name>.yaml` override
- 5 sessions (SV-1 contracts + skill rename, SV-2 classifier + 2 doctypes, SV-3 API + Alembic 048 doc_recognition_runs, SV-4 admin UI + 3 more doctypes, SV-5 close)
- Gate: 3 doctype accuracy ≥ 80%, classifier top-1 ≥ 90%, UC1/2/3 regression untouched
- Risk register R1–R5: LLM cost amplification, HU regex brittleness, OCR quality, PII leak, invalid tenant YAML

Plus the 7 Sprint U follow-ups (SU-FU-1..4 + SR-FU-4/6 deferred + ST-FU-4-followup) tracked in `docs/sprint_u_retro.md`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
