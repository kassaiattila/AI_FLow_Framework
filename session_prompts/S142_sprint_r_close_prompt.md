# AIFlow — Session 142 Prompt (Sprint R S142 — Sprint R close + tag v1.5.1)

> **Datum:** 2026-05-14
> **Branch:** `feature/r-s142-sprint-close` (cut from `main` after S141 squash-merge).
> **HEAD (parent):** S141 squash-merge on `main` (PR #32).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S141 — `PromptWorkflowExecutor` scaffold + 3 workflow descriptors (`email_intent_chain`, `invoice_extraction_chain`, `aszf_rag_chain`) + `skills_csv` settings. Skill code unchanged — per-skill migration deferred to S141-FU-1/2/3 to keep Sprint K/Q/J golden paths untouched.
> **Terv:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 Sprint R close.
> **Session tipus:** Sprint close — retro + PR description + CLAUDE.md numbers + tag `v1.5.1`.

---

## 1. MISSION

Close Sprint R. Write `docs/sprint_r_retro.md` (S139 → S141 walkthrough, decisions, follow-ups). Write `docs/sprint_r_pr_description.md` mirroring Sprint Q's format. Bump CLAUDE.md numbers. Cut final Sprint R-close PR. Tag `v1.5.1` queued post-merge.

---

## 2. KONTEXTUS

### Sprint R recap
| Session | PR | Scope |
|---|---|---|
| S139 | #30 (merged) | `PromptWorkflow` Pydantic model + `PromptWorkflowLoader` + `PromptManager.get_workflow()` 3-layer lookup + `PromptWorkflowSettings` (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` default) + `FeatureDisabled` exception + 24 unit tests. Example descriptor `prompts/workflows/uc3_intent_and_extract.yaml`. |
| S140 | #31 (merged) | Admin UI `/prompts/workflows` page (table + detail + DAG indentation + dry-run JSON output) + 3-route GET-only router (list / detail / dry-run) + EN/HU locale + sidebar nav + 10 router unit tests. OpenAPI snapshot refreshed. |
| S141 | #32 (this branch's parent) | `PromptWorkflowExecutor` scaffold (resolution-only, no LLM call) + 3 skill workflow descriptors (`email_intent_chain`, `invoice_extraction_chain`, `aszf_rag_chain`) + `PromptWorkflowSettings.skills_csv` per-skill opt-in + 17 unit tests. Skill code untouched — migration deferred to S141-FU-1/2/3. |
| S142 | (this commit) | Sprint close — retro + PR description + CLAUDE.md numbers + tag `v1.5.1` queued. |

### Success metrics status (capability roadmap §3)

| Metric | Target | Actual |
|---|---|---|
| `PromptWorkflow` Pydantic model | shipped | ✅ |
| YAML loader + Langfuse lookup | shipped | ✅ |
| Admin UI listing + detail + dry-run | shipped | ✅ |
| 3 skills migrated | 3 | **0** (deferred to S141-FU-1/2/3, scaffold ready) |
| Sprint K UC3 / Sprint Q UC1 / Sprint J UC2 golden paths | unchanged | ✅ |
| Unit tests added | ≥ 30 | **51** (24 + 10 + 17) |
| New routers / endpoints | 1 / 3 | **1 / 3** ✅ |
| Alembic migrations | 0 | **0** ✅ |

Sprint R closes with foundation 100% delivered + scaffold for skill migration ready. The actual per-skill migration is split into 3 small, focused follow-ups (each with its golden-path test as the gate) instead of a single 3-skill bundle that would risk regressing every UC.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                       # feature/r-s142-sprint-close
git log --oneline -5                            # S139 + S140 + S141 squash visible on main
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2347 pass
docker compose ps                               # postgres + redis healthy
```

---

## 4. FELADATOK

### LEPES 1 — `docs/sprint_r_retro.md`
- Headline: from `PromptManager.get(name)` per skill → reusable `PromptWorkflow` descriptor + executor + admin UI + 3 ready-to-consume YAMLs.
- Scope-by-session table (S139, S140, S141 — skip S142 which is this commit).
- Test deltas table (2330 → 2347 unit / 0 integration / 0 E2E live-stack — 1 deferred / 0 Alembic / 1 router / 3 endpoints / 1 admin page).
- Contracts delivered (S139 model + lookup; S140 router + UI + dry-run; S141 executor scaffold + 3 descriptors + per-skill opt-in).
- **Decisions log SR-1..SR-6**:
  - SR-1: 3-layer lookup mirroring `PromptManager.get()` (cache → Langfuse JSON-typed → local YAML) — kept the codebase's existing pattern instead of inventing a new one.
  - SR-2: Workflows live as `workflow:<name>` JSON-typed prompts in Langfuse — reused v4 SDK `get_prompt`, no new client code.
  - SR-3: Admin UI uses `useTranslate` from existing `lib/i18n` (not `react-i18next`) — first PR caught the missing dep at CI, fixed in same session.
  - SR-4: Workflow router mounted BEFORE prompts router on both backend (FastAPI) and frontend (React Router) — the existing `/prompts/{path}` catch-all otherwise shadows the `/workflows` route.
  - SR-5: `skills_csv: str` instead of `list[str]` for the per-skill opt-in env var — pydantic_settings JSON-decodes list fields from env, breaking CSV input.
  - SR-6: S141 ships scaffold-only, defers per-skill migration to follow-ups — bundling 3 skill migrations in one session would risk regressing every UC; each follow-up is a focused PR with its own golden-path gate.
- **What worked**: incremental scaffolding (model → router → executor); each session's PR independently mergeable; full reuse of Sprint M's PromptManager pattern.
- **What hurt**: the `react-i18next` slip (caught only at CI Vite build, not local TSC) — local check should have flagged it; consider adding a vite-build check to the local pre-commit.
- **Follow-ups (SR-FU-1..N)**:
  - **S141-FU-1** migrate `email_intent_processor` LLM classifier path to consume `email_intent_chain`. Gate: Sprint K UC3 golden-path E2E (4/4 green).
  - **S141-FU-2** migrate `invoice_processor.workflows.process` to consume `invoice_extraction_chain`. Gate: Sprint Q UC1 golden-path slice (≥ 75% accuracy / invoice_number ≥ 90%).
  - **S141-FU-3** migrate `aszf_rag_chat.workflows.query` baseline persona to consume `aszf_rag_chain`. Expert/mentor variants remain separate workflows. Gate: Sprint J UC2 MRR@5 ≥ 0.55.
  - SR-FU-4: live-stack Playwright E2E for `/prompts/workflows` page — deferred from S140 because it needs interactive shell to bring up dev server with the flag on.
  - SR-FU-5: vite-build local pre-commit (catch the `react-i18next`-style slip earlier).
  - SR-FU-6: workflow listing endpoint enumerates Langfuse workflows too (today only local YAML) — needs a Langfuse v4 list-by-prefix call.

### LEPES 2 — `docs/sprint_r_pr_description.md`
Mirror Sprint Q's format. Cohort-delta table (Sprint Q UC1 extraction 85.7% → Sprint R **PromptWorkflow foundation**). Per-session commit table. 8-criterion acceptance status table. Post-merge test plan. 3-level rollback (flag-off → revert → no-data).

### LEPES 3 — CLAUDE.md banner + numbers
- Flip banner to `v1.5.1 Sprint R CLOSE 2026-05-14`.
- Bump unit-test count: `2296 → 2347` (+51 over Sprint Q tip).
- API endpoints: `190 → 193` (+3, all under `/api/v1/prompts/workflows`).
- API routers: `29 → 30` (+1).
- New flag default: `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false`, `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""`.

### LEPES 4 — PR cut + tag
```bash
gh pr create \
  --title "Sprint R (v1.5.1): PromptWorkflow foundation — retro + close" \
  --body-file docs/sprint_r_pr_description.md \
  --base main
```
After merge: `git tag -a v1.5.1 <squash-sha> -m "..."` + push.

### LEPES 5 — Regression + commit + push
- `/regression` — unit 2347 green.
- `/lint-check` clean.
- Commit: `chore(sprint-r): S142 — Sprint R retro + PR description + CLAUDE.md numbers` + Co-Authored-By.

### LEPES 6 — NEXT.md for Sprint S
Master roadmap §4 identifies Sprint S = Functional vector DB teljes kör. Write S143 kickoff prompt (UC2 RAG `RagEngineService.query()` refactor + `rag_collections` Alembic + admin UI per-tenant collection list). Document the open S141-FU-1/2/3 follow-ups so Sprint R skill migrations can be scheduled inline with Sprint S or after it.

---

## 5. STOP FELTETELEK

**HARD:**
1. `gh pr create` requires credentials the autonomous loop doesn't have — halt + ask user.
2. Sprint Q UC1 / Sprint K UC3 / Sprint J UC2 golden-path regresses on final regression — halt.
3. CLAUDE.md merge conflict with another in-flight branch — halt.

**SOFT:**
- Sprint M/N PRs still open queued behind Sprint R — document as rebase note in PR body.

---

## 6. SESSION VEGEN

```
/session-close S142
```

Sprint R closes here. Auto-sprint may halt and await a Sprint S kickoff decision, OR queue S143 (Sprint S kickoff) if the user confirms.
