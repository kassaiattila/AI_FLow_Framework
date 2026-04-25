# AIFlow — Session 146 Prompt (Sprint S close — retro + PR description + tag v1.5.2)

> **Datum:** 2026-04-26 (snapshot date — adjust if session runs later)
> **Branch:** `chore/sprint-s-close` (cut from `main` after PR #37 squash-merged → `d6ee813`).
> **HEAD:** `d6ee813` — `feat(sprint-s): S145 — nightly MRR@5 + Alembic 047 (tenant_id, name) unique + BGE-M3 weight cache (#37)`
> **Port:** API 8102 | UI 5173
> **Elozo session:** S145 — Alembic 047 swap of legacy `UNIQUE (name)` for `UNIQUE (tenant_id, name)` on `rag_collections`, `RagMetricsHarness` service + 20-item HU UC2 corpus + CLI runner + 4-panel Grafana dashboard JSON + operator runbook, BGE-M3 weight `actions/cache@v4` step in `nightly-regression.yml`. 2373 → 2379 unit (+6), ~110 → ~113 integration (+3), Alembic head 046 → 047, 0 new endpoints, 0 UI pages, 0 skill code change. PR #37 squash-merged.
> **Terv:** `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` close-out + `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §4 follow-up consolidation.
> **Session tipus:** Retro + PR description authoring + tag prep. **NO code change.**

---

## 1. MISSION

Close Sprint S with the same retro + PR description discipline that Sprints J, M, N, O, P, Q, R used. Three SDLC outputs:

1. **`docs/sprint_s_retro.md`** — full retro covering S143 (query-path ProviderRegistry refactor), S144 (admin UI `/rag/collections`), S145 (operability close-out). Decisions log `SS-1 .. SS-N`, all open follow-ups, lessons learned, test deltas, cost.
2. **`docs/sprint_s_pr_description.md`** — consolidated PR-style summary across the three squash-merged PRs (#34, #35, #37). The doc is reference material — the actual PRs already shipped, this is a single rolled-up view for stakeholders + future archeology.
3. **CLAUDE.md** numbers + banner update — flip Sprint S S145 IN-PROGRESS → MERGED, queue tag `v1.5.2`, demote S145 to predecessor.

S146 **does not** touch:
- Code (no source / test / migration changes).
- Sprint T kickoff (separate session — S147).
- Per-skill PromptWorkflow migrations (S141-FU-*; Sprint T scope).
- `customer` column drop (SS-FU-1, SS-FU-5; separate refactor sprint).
- Azure Profile B live MRR (SS-SKIP-2; credit pending).

---

## 2. KONTEXTUS

### Sprint S delivered (S143 → S144 → S145)

| Session | Squash | Headline |
|---|---|---|
| S143 | `95ec89e` (PR #34) | `RAGEngineService.query()` ProviderRegistry refactor; Alembic 046 `tenant_id` + `embedder_profile_id`; 1024-dim BGE-M3 collections become queryable |
| S144 | `bc59a8f` (PR #35) | Admin UI `/rag/collections` (3-route router + tenant filter + side drawer + EN/HU + Playwright spec); `set_embedder_profile()` mutation with `DimensionMismatch` HTTP 409 guard |
| S145 | `d6ee813` (PR #37) | Alembic 047 `(tenant_id, name)` unique swap; `RagMetricsHarness` + CLI + corpus + Grafana panel + runbook; BGE-M3 weight CI cache |

Plus the `chore/consolidate-dev-env` PR #36 (`ec3e672`) — sourced from S145 prereq work but landed before to unblock the live-test on `/rag/collections`.

### Carry-forward at Sprint S close

| ID | Origin | Disposition |
|---|---|---|
| SS-FU-1 | S143 | `create_collection` tenant-aware arg + `customer` deprecation — separate refactor sprint |
| SS-FU-5 | S143 | `rag_collections.customer` column drop — separate refactor sprint (depends on SS-FU-1) |
| SS-SKIP-2 | S143 plan §8 | Profile B (Azure OpenAI) MRR@5 — Azure credit pending |
| S141-FU-1/2/3 | Sprint R retro | Per-skill PromptWorkflow migration — Sprint T |
| SR-FU-4 | Sprint R retro | Live-stack Playwright for `/prompts/workflows` — Sprint T |
| Sprint J Clock seam | Sprint J retro | Resilience timing flake fix — DEADLINE 2026-04-30 (now overdue, S147 must triage) |

### Live-test debt

- `/rag/collections` live-test: PASSED 2026-04-25 09:07 in S145 prereq run (`tests/ui-live/rag-collections.md`).
- `/prompts/workflows` live-test: still PENDING from Sprint R (`SR-FU-4`).

---

## 3. ELOFELTETELEK

```bash
git checkout main
git pull --ff-only origin main                                         # tip: d6ee813
git checkout -b chore/sprint-s-close
git log --oneline -5
docker compose ps                                                       # db (5433) + redis (6379) healthy (only needed if final regression runs)
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current          # head: 047
```

Stop, ha:
- Alembic current ≠ 047 — S145 squash not on local main.
- `git status` dirty — finish or stash first.
- PR #37 not merged — wait or escalate.

---

## 4. FELADATOK

### LEPES 1 — `docs/sprint_s_retro.md`

Mirror the structure used by `docs/sprint_r_retro.md`. Sections:

1. **Scope** — bullet list per session (S143/S144/S145), 2-3 lines each.
2. **Test deltas** —
   - Unit: `Sprint R close 2333 → S143 2347 (+14) → S144 2361 (+12+missing — verify) → S145 2379 (+6)` … verify exact numbers from CLAUDE.md.
   - Integration: `~107 → ~110 (S144 +3) → ~113 (S145 +3, including 1 skip-by-default)`.
   - E2E: `429 → 430 (S144 +1)`.
3. **Decisions log SS-1 .. SS-N** — at minimum:
   - SS-1: ProviderRegistry adapter on the query path keeps NULL-fallback byte-for-byte for legacy 1536-dim collections.
   - SS-2: Admin router mounted at `/api/v1/rag-collections` (hyphenated) to avoid colliding with the legacy `/api/v1/rag/collections` UC2 ingest/query routes.
   - SS-3: `set_embedder_profile()` short-circuits on empty collections (no `DimensionMismatch` raised when `chunk_count=0`) — matches operator expectation that profile is changeable on fresh collections.
   - SS-4: Alembic 047 drops the legacy `UNIQUE (name)` instead of preserving both — preserving both would block cross-tenant name reuse, defeating the multi-tenancy story.
   - SS-5: MRR@5 harness persists *externally* via runbook-driven psql ingest — keeps the AIFlow runtime air-gap-safe and lets operators choose retention policy.
   - SS-6: BGE-M3 weight cache lives in `nightly-regression.yml`, not `ci.yml` — main CI stays fast (~3 min); the 1024-dim integration tests un-skip only on the nightly run.
   - SS-7: `chore/consolidate-dev-env` (PR #36) cut as a side branch off `main` between S144 and S145 to unblock the operator live-test of `/rag/collections` — not strictly Sprint S scope, captured here for ops-history continuity.
4. **Open follow-ups** — table from §2 above.
5. **Lessons learned** — at minimum the trailing-space password issue in the `/live-test` flow and the env-file consolidation that came out of it.
6. **Cost** — per-session LLM cost (USD) if measurable.

### LEPES 2 — `docs/sprint_s_pr_description.md`

PR-description-style document covering all three Sprint S PRs. Sections:

1. **Headline** — "Sprint S — multi-tenant + multi-profile vector DB ships at parity with Sprints L (monitoring) + N (budgets)."
2. **What landed** — 3-row table (PR # / commit / scope).
3. **Schema changes** — Alembic 046 + 047 in one breath, with the legacy `UNIQUE (name)` swap called out.
4. **Test deltas** — same numbers as retro §2.
5. **Test plan** — checkboxes for each green PR (unit / integration / e2e / lint / TS).
6. **What's NOT in this sprint** — carry-forward table.
7. **Operator follow-up** — provision `rag_collection_metrics_jsonl` + import Grafana panel + run `bootstrap_bge_m3.py` locally if needed.

### LEPES 3 — CLAUDE.md numbers + banner

- Banner: `**v1.5.2 Sprint S S145** — **IN-PROGRESS 2026-04-26**` → `**v1.5.2 Sprint S** — **MERGED 2026-04-26**, tag `v1.5.2` (queued post-merge), squashes `95ec89e` (#34) + `bc59a8f` (#35) + `d6ee813` (#37).
- Demote S145 to predecessor sentence.
- Numbers stay at 2379 unit / ~113 integration / 47 Alembic / 196 endpoints / 31 routers / 26 UI pages — no further deltas.
- **Important:** the banner already mentions the chore PR #36; keep that.

### LEPES 4 — Tag prep (NOT push)

```bash
git tag -a v1.5.2 -m "Sprint S — multi-tenant vector DB + nightly MRR@5"
git tag --list 'v1.5.*'           # confirm v1.5.0 / v1.5.1 / v1.5.2 ordering
```

Do **not** `git push --tags` from this session — the operator pushes the tag once the retro PR merges, in line with the SDLC convention used for v1.5.1 (tag `v1.5.1` queued post-merge per `docs/sprint_r_retro.md`).

### LEPES 5 — Commit + PR + close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/                      # only docs+CLAUDE.md changed — should still pass
git add docs/sprint_s_retro.md docs/sprint_s_pr_description.md CLAUDE.md
git commit -m "chore(sprint-s): close — retro + PR description + CLAUDE.md banner (tag v1.5.2 queued)"
git push -u origin chore/sprint-s-close
gh pr create --base main --head chore/sprint-s-close --title "Sprint S close — retro + PR description + tag v1.5.2 prep"
```

Then `/session-close S146` — which will queue S147 (Sprint T kickoff or per-skill PromptWorkflow migration).

---

## 5. STOP FELTETELEK

**HARD:**
1. CLAUDE.md banner numbers don't add up (e.g. integration count diverges from `pytest --collect-only`) → halt + recount.
2. `gh pr create` credentials missing → halt; document in retro and surface to operator.
3. Operator dispute on Sprint S scope (e.g. wants SS-FU-1 included before tag) → halt + revisit `01_PLAN/116_*`.

**SOFT:**
- LLM cost numbers unavailable from Langfuse → leave a `TBD` placeholder + note in retro §6.
- E2E test count cross-check fails by 1 due to `xfail` quarantine — flag in retro lessons but proceed.
- Live-test debt for `/prompts/workflows` (SR-FU-4) — Sprint S close acknowledges it as carry-forward, does not resolve.

---

## 6. SESSION VEGEN

```
/session-close S146
```

The `/session-close` will:
- Validate lint + e2e collect (no test code change → unit re-run optional).
- Stage + commit (docs only).
- Push the chore branch.
- Generate `session_prompts/NEXT.md` for S147 — likely Sprint T kickoff (per-skill PromptWorkflow migration starting with `aszf_rag_chat`, gated by Sprint J UC2 baseline).

---

## 7. SKIPPED-ITEMS TRACKER (folytatas)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SS-FU-1 | PR #34 / #35 body | `create_collection` tenant-aware arg + `customer` deprecation | Külön refactor sprint |
| SS-FU-5 | PR #34 body | `rag_collections.customer` column drop | Külön refactor (after SS-FU-1) |
| SS-SKIP-2 | `01_PLAN/116_*` §8 | Profile B (Azure OpenAI) MRR@5 | Azure credit |
| SS-SKIP-1 | S145 (this session) | BGE-M3 weight CI cache | **CLOSED** in S145 — confirm with first nightly run |
| S141-FU-1/2/3 | Sprint R retro | Per-skill PromptWorkflow migration | Sprint T (S147+) |
| SR-FU-4 | Sprint R retro | Live-stack Playwright for `/prompts/workflows` | Sprint T |
| SR-FU-5 | Sprint R retro | vite-build pre-commit hook | Sprint T |
| SR-FU-6 | Sprint R retro | Langfuse workflow listing | Sprint T |
| Sprint J Clock seam | Sprint J retro | Resilience timing flake fix | **DEADLINE 2026-04-30 — overdue at S146 close** |
| SS-FU-3 | S143 PR | Nightly MRR@5 + Grafana | **CLOSED** in S145 — operator activation pending |
| SS-FU-4 | S143 PR | `(tenant_id, name)` unique | **CLOSED** in S145 |
| `/prompts/workflows` live-test | Sprint R retro | Operator live run | Sprint T (S147+) |

S146 closes the sprint envelope; nothing in this list resolves in S146 itself.
