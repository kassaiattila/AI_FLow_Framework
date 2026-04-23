# AIFlow v1.4.10 Sprint N — Session 124 Prompt (Sprint N close — PR cut, retro, tag `v1.4.10`)

> **Datum:** 2026-04-28
> **Branch:** `feature/v1.4.10-cost-guardrail-budget`
> **HEAD (parent):** `f39309d` (feat(sprint-n): S123 — admin UI budget dashboard + alert threshold editor + 2 Playwright E2E)
> **Port:** API 8102 | UI 5173
> **Elozo session:** S123 — `/budget-management` admin page (BudgetCard + ThresholdEditor + types) behind `aiflow.menu.budgets` nav item; 2 Python Playwright E2E in `tests/e2e/test_budget_management.py` (render + edit round-trip); `/live-test` report at `tests/ui-live/budget-management.md`. TSC + ruff + 2113 unit baseline green.
> **Terv:** `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` S4 (Sprint N close) + §8 success metrics + §7 rollback note for flag-gated ship.
> **Session tipus:** CLOSE — retro + PR description + CLAUDE.md numbers + tag `v1.4.10` queue (no code changes expected).

---

## KONTEXTUS

### Honnan jottunk (S123)
- UI-only session: `aiflow-admin/src/pages-new/BudgetManagement/` (index + BudgetCard + ThresholdEditor + types) consumes the S121 endpoints (`GET/PUT/DELETE /api/v1/tenants/{id}/budget[/{period}]`). React Aria chip editor, per-period card grid, live projection (`used / limit / remaining / over_thresholds`), no silent mock (`source="live"`).
- No new backend surface, no new Alembic migration. The S122 pre-flight guardrail remains flag-gated (`AIFLOW_COST_GUARDRAIL__ENABLED=false` + `__DRY_RUN=true` defaults).
- `/live-test` uncovered a stale uvicorn process on 8102 (v1.4.4 openapi). The report documents the restart (`python -m uvicorn aiflow.api.app:create_app --factory --port 8102`); operators should mirror this for anything that has to hit the S121 routes.

### Hova tartunk (S124 — Sprint N close)
Per plan §3 and §7:
1. **Retro** — `docs/sprint_n_retro.md` modelled on `docs/sprint_m_retro.md`. Capture: feature flag ship (S122 default OFF), CostEstimator tokenizer heuristic trade-offs, S123 UI scope held to one page + chip editor, stale API-process gotcha from `/live-test`.
2. **PR description** — `docs/sprint_n_pr_description.md` modelled on `docs/sprint_m_pr_description.md`. Summary, migration story (one: 045), rollout toggle path, test deltas, follow-ups inherited + discovered.
3. **CLAUDE.md numbers** — bump sprint banner to "Sprint N **DONE** 2026-04-28, tag `v1.4.10` queued post-merge"; update counts (189 → 190 endpoints after S121, 44 → 45 Alembic, 2073 → 2113 unit, 422 → 424 E2E, 23 → 24 UI pages). Preserve Sprint M DONE block per convention.
4. **PR open against `main`** — single squash-merge PR per sprint. Tag `v1.4.10` queued post-merge.
5. **Session close** — `/session-close S124` generates an S125 NEXT.md. S125 is either the next sprint kickoff (v1.4.11 TBD) or a follow-up bucket (live rotation E2E, Clock seam, BGE-M3 weight cache) — leave the choice to the user.

### Jelenlegi allapot (pre-close counts)
```
27 service | 190 endpoint | 50 DB table | 45 Alembic (head: 045)
2113 unit | 424 e2e | ~93 integration | 8 skill | 24 UI page
Branch: feature/v1.4.10-cost-guardrail-budget (HEAD f39309d, S123 shipped)
```

---

## ELOFELTETELEK

```bash
git branch --show-current                         # feature/v1.4.10-cost-guardrail-budget
git log --oneline -3                              # HEAD f39309d + 5526bbf + 8541857
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current  # 045 (head)
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2113 pass baseline
cd aiflow-admin && npx tsc --noEmit                # 0 error
```

Reference artifacts (read, do not reinvent):
```bash
ls docs/sprint_m_retro.md docs/sprint_m_pr_description.md
cat 01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md | sed -n '1,80p'
```

---

## FELADATOK

### LEPES 1 — Sprint N retro (~45 min)

```
Cel:    docs/sprint_n_retro.md osszefoglalo
Fajl:   docs/sprint_n_retro.md (uj)
Minta:  docs/sprint_m_retro.md
```

Sections:
- **Scope delivered** — S120 inventory, S121 `tenant_budgets` (Alembic 045 + TenantBudgetService + CRUD), S122 pre-flight guardrail (`CostPreflightGuardrail` + `CostEstimator` + `CostGuardrailRefused` + 3 wiring points + 429 handler), S123 admin UI.
- **Metric deltas** — unit 2073 → 2113 (+40 in S121/S122/S123), E2E 422 → 424 (+2 from S123), endpoints 189 → 190 (+1 from S121 PUT), Alembic 44 → 45.
- **What went well** — flag-gated default-off ship, DRY_RUN policy for S122, UI held to one page, React Aria chip editor pattern transplantable to future threshold UIs.
- **What surprised us** — stale API process gotcha on `/live-test` (fix: always restart uvicorn with `--factory` at session start); `litellm` pricing coverage audit pushed to Sprint N retro (now this doc).
- **Follow-ups carried** — Sprint M list + S122 soft items (eval/promptfoo blanket bypass flag still NOT added by design; litellm pricing coverage audit, which this retro is the forum for).
- **Follow-ups discovered this sprint** — document what lives in the retro.

### LEPES 2 — PR description (~30 min)

```
Cel:    docs/sprint_n_pr_description.md (template for PR against main)
Fajl:   docs/sprint_n_pr_description.md (uj)
Minta:  docs/sprint_m_pr_description.md
```

Outline:
- **Summary** — 3 bullets (per-tenant budget domain, pre-flight guardrail flag-gated, admin UI dashboard).
- **Migration story** — 1 Alembic (045). Zero-downtime: additive table + indexes, nullable columns per DB skill.
- **Rollout plan** — ship with `AIFLOW_COST_GUARDRAIL__ENABLED=false` + `__DRY_RUN=true` defaults; operator flip per tenant is the enablement gate. Rollback = flag off.
- **Test deltas** — see retro metric deltas.
- **Follow-ups** — paste from retro.

### LEPES 3 — CLAUDE.md numbers + sprint status (~15 min)

Update `CLAUDE.md` header paragraph:
- Sprint N status: `**DONE 2026-04-28, tag v1.4.10 queued post-merge**` (mirror Sprint M block format).
- Numbers row: endpoints 189 → **190**, Alembic 44 → **45 (head: 045)**, unit 2073 → **2113**, E2E 422 → **424**, UI pages 23 → **24**.
- Feature-flag note: `AIFLOW_COST_GUARDRAIL__ENABLED=false` + `__DRY_RUN=true` defaults (ship-off).
- Preserve the Sprint M DONE block unchanged (append-style history).

### LEPES 4 — Open PR against `main` (~10 min)

Pre-flight:
```bash
git fetch origin
git log --oneline origin/main..HEAD   # expect 4 feature commits (S121, S122, S123) + 3 session-close commits
gh pr list --head feature/v1.4.10-cost-guardrail-budget --state open --json number,url
```

If no PR open yet:
```bash
gh pr create --base main --head feature/v1.4.10-cost-guardrail-budget \
  --title "feat(v1.4.10): Sprint N — cost guardrail + per-tenant budget" \
  --body-file docs/sprint_n_pr_description.md
```

If Sprint M PR #17 still OPEN and NOT MERGED: note the dependency in the description ("rebase onto `main` after #17 merges"). Do not force-rebase blindly.

### LEPES 5 — Tag queue (no tag push yet)

Per Sprint M pattern: queue `v1.4.10` in the retro + PR description, but **do not** `git tag` until the PR merges. Tag creation is a post-merge action by the user.

### LEPES 6 — Commit docs + CLAUDE.md update

```bash
git add docs/sprint_n_retro.md docs/sprint_n_pr_description.md CLAUDE.md
git commit -m "chore(sprint-n): S124 close — retro + PR description + CLAUDE.md v1.4.10 numbers"
git push
```

### LEPES 7 — Validation

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2113
cd aiflow-admin && npx tsc --noEmit && cd ..
/session-close S124
```

The session-close skill will generate an S125 NEXT.md. If the user has not yet decided on the next sprint, ask at the end of S124 (not during) — let the close skill finish first.

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. **Sprint M PR #17 still open at session start and blocking this PR** — if GitHub shows #17 still OPEN and targeting `main`, halt, surface the situation, and ask whether to block or queue behind it.
2. **CLAUDE.md conflict** — if the user's working tree has CLAUDE.md edits not committed (and not yours), do not overwrite — ask.
3. **Tag `v1.4.10` already exists** — confirm with the user before any re-tagging.
4. **Regression unit baseline drops below 2113** — halt and diagnose.

**SOFT (proceed with note):**
1. `litellm` pricing coverage audit surfaces missing models — document in retro, schedule as a follow-up, do not block the PR.
2. `scripts/` bootstrap updates needed for budget seeding demos — write the shell stub in retro follow-ups; not required for close.

---

## NYITOTT (cross-sprint, carried)

- Sprint M follow-ups: live rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC example, Langfuse v4 self-host migration, `SecretProvider` slot on `ProviderRegistry`.
- Sprint J follow-ups: BGE-M3 weight cache as CI artifact, Azure OpenAI Profile B live (credits pending), resilience `Clock` seam (deadline 2026-04-30 — still xfails), coverage uplift (issue #7).
- S122 soft: eval/promptfoo blanket bypass flag NOT added by design; `litellm` pricing table coverage audit (this retro).
- S123 soft: stale-API-process guidance in operator runbook (the `/live-test` report has the note — promote to a runbook entry if it recurs).

---

## SESSION VEGEN

```
/session-close S124
```

Utana: `/clear` -> `/next` -> S125 (Sprint N+1 kickoff TBD OR follow-up bucket — user dontes).
