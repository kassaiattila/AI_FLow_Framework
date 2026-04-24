# AIFlow — Session 125 Prompt (triage — post-Sprint-N direction)

> **Datum:** 2026-04-29
> **Branch:** `feature/v1.4.10-cost-guardrail-budget` (Sprint N DONE, PR #18 OPEN, queued behind Sprint M PR #17)
> **HEAD (parent):** `70312cc` (chore(sprint-n): S124 close — retro + PR description + CLAUDE.md v1.4.10 numbers)
> **Port:** API 8102 | UI 5173
> **Elozo session:** S124 — Sprint N close. `docs/sprint_n_retro.md` + `docs/sprint_n_pr_description.md` + CLAUDE.md bumped (Sprint N DONE, v1.4.10 queued, 189→190 endpoints / 44→45 Alembic / 2073→2113 unit / 422→424 E2E / 23→24 UI pages). PR #18 opened against `main` with Sprint M PR #17 rebase dependency noted.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` + the three open "next step" tracks (see §1 below).
> **Session tipus:** TRIAGE — pick one of three lanes at session start, then execute the chosen lane's LEPES list.

---

## 1. DONTES A SESSION ELEJEN

Three mutually-exclusive lanes. Pick one out loud at the start of the session; do not start work until the user has acknowledged the choice.

### Lane A — **Merge coordination + post-merge tag**
Goal: land Sprint M PR #17, rebase Sprint N PR #18 onto fresh `main`, squash-merge #18, tag `v1.4.9` + `v1.4.10`.

- Scope: git operations + CI watch. No new code.
- Prerequisite: user confirms both PRs are green in review.
- Artifacts: updated branch tips, two git tags, GitHub releases (optional).
- Estimated duration: 30–60 min (plus CI wait).

### Lane B — **Sprint N+1 kickoff (v1.4.11 — TBD scope)**
Goal: open a new `feature/v1.4.11-*` branch and write the Sprint N+1 plan + kickoff docs.

- Candidate themes (pick one with the user before writing the plan):
  - **UC3 Sprint K — email_intent_processor UC3 golden path** (was queued in `110_USE_CASE_FIRST_REPLAN.md` §6; deferred by Sprint L/M/N cross-cutting work). High customer value, clean scope.
  - **Sprint L reactive-cap ↔ Sprint N pre-flight consolidation** — unify `BudgetSettings` + `CostGuardrailSettings` into a `CostSettings` umbrella, consolidate `CostAttributionRepository.insert_attribution` with `cost_recorder.record_cost`. Single-sprint hardening.
  - **User-flagged theme** — something not in the backlog.
- Artifacts: `feature/v1.4.11-*` branch cut from `main` (after #18 merges) OR from `feature/v1.4.10-cost-guardrail-budget` (if PRs still queued); `01_PLAN/112_SPRINT_{N+1}_*_PLAN.md`; `docs/sprint_{n+1}_plan.md`; CLAUDE.md banner flip.
- Estimated duration: 60–90 min.

### Lane C — **Hardening bucket — carry-over cleanup**
Goal: knock out 1–2 small follow-ups from the combined Sprint J/M/N carry-over list (see `docs/sprint_n_retro.md` §"Follow-up issues"). Stays on `feature/v1.4.10-cost-guardrail-budget` (piggyback-commit before the PR merges) OR cuts a tiny `chore/*` branch.

Top candidates (small, independent, high-signal):
  1. **`AIFLOW_ENV=prod` boot guard refuses Vault root tokens.** ~20 lines in `src/aiflow/security/resolver.py` + 2 unit tests. Closes Sprint M retro follow-up #2.
  2. **`make langfuse-bootstrap` target.** Sequences the 3 bootstrap commands. ~15 lines in `Makefile` + a runbook tweak. Closes Sprint M retro follow-up #3.
  3. **`scripts/seed_tenant_budgets_dev.py` demo seeder.** Mirrors `scripts/seed_vault_dev.py` pattern. Closes Sprint N retro follow-up #8.
  4. **litellm pricing coverage audit as CI step.** ~30 lines in a new `scripts/audit_litellm_pricing.py` + a CI hook. Closes Sprint N retro follow-up #4.
  5. **Resilience `Clock` seam — xfail fix** (deadline 2026-04-30, last chance). Unquarantine `test_circuit_opens_on_failures`. Sprint J carry-over.

Pick 1 or 2 (not 3+). Artifacts: focused code change + test delta + small doc entry.
Estimated duration: 45–90 min depending on pick.

---

## 2. KONTEXTUS

### Honnan jottunk (S124)
Sprint N closed green. `docs/sprint_n_retro.md` + `docs/sprint_n_pr_description.md` landed. CLAUDE.md bumped. PR #18 opened against `main`, queued behind Sprint M PR #17. Tag `v1.4.10` is queued for post-merge.

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2113 unit PASS / 1 skip / 1 xpass (resilience quarantine)
~96 integration | 424 E2E collected | 8 skill | 24 UI page
Branch: feature/v1.4.10-cost-guardrail-budget (HEAD 70312cc)
Open PRs: #17 (Sprint M v1.4.9, MERGEABLE), #18 (Sprint N v1.4.10, depends on #17)
Flag defaults on v1.4.10: AIFLOW_COST_GUARDRAIL__ENABLED=false / __DRY_RUN=true
```

### Hova tartunk
User decision at S125 start. Lanes A / B / C above are the mutually-exclusive options.

---

## 3. ELOFELTETELEK (all lanes)

```bash
git branch --show-current                         # feature/v1.4.10-cost-guardrail-budget
git log --oneline -3                              # HEAD 70312cc + 751107d + f39309d
gh pr list --state open --json number,headRefName,mergeable  # #17, #18
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2113 passed
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet    # 0 error
```

### Lane A extras
```bash
gh pr view 17 --json state,mergeable,reviewDecision,statusCheckRollup
gh pr view 18 --json state,mergeable,reviewDecision,statusCheckRollup
git fetch origin
```

### Lane B extras
```bash
ls 01_PLAN/110_USE_CASE_FIRST_REPLAN.md 01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md
cat docs/sprint_m_plan.md docs/sprint_n_plan.md   # structural templates
```

### Lane C extras
```bash
cat docs/sprint_n_retro.md | sed -n '/Follow-up issues/,/Process notes/p'
cat docs/sprint_m_retro.md | sed -n '/Follow-up issues/,/Process notes/p'
```

---

## 4. FELADATOK (lane-specific)

### Lane A — Merge coordination + tag

1. **Verify #17 is green** — `gh pr checks 17` green, at least one approval, no requested changes.
2. **Merge #17 (squash)** — `gh pr merge 17 --squash --delete-branch` (confirm deletion after).
3. **Rebase #18 onto fresh main**:
   ```bash
   git fetch origin
   git checkout feature/v1.4.10-cost-guardrail-budget
   git rebase origin/main
   # resolve any conflicts (Sprint M and Sprint N are largely non-overlapping;
   # expect CLAUDE.md conflict only — keep Sprint M block from main + Sprint N
   # block from this branch).
   git push --force-with-lease
   ```
4. **Verify #18 goes green on CI after rebase.** Update `docs/sprint_n_pr_description.md` if the "Depends on" block needs adjustment after #17 lands.
5. **Merge #18 (squash)** — `gh pr merge 18 --squash --delete-branch`.
6. **Tag both versions**:
   ```bash
   git checkout main && git pull
   git tag v1.4.9  -a -m "Sprint M: Vault hvac + self-hosted Langfuse + air-gap Profile A"
   git tag v1.4.10 -a -m "Sprint N: LLM cost guardrail + per-tenant budget"
   git push origin v1.4.9 v1.4.10
   ```
7. **Close with CLAUDE.md update** flipping both Sprint M and Sprint N banners to MERGED with their squash SHAs.

### Lane B — Sprint N+1 kickoff

1. **Confirm theme with user.** Do not start writing the plan until the theme is picked.
2. **Base branch decision:**
   - If PRs #17 / #18 are merged → cut from fresh `main` as `feature/v1.4.11-<theme>`.
   - If PRs are still open → either stay on `feature/v1.4.10-cost-guardrail-budget` (piggyback) or cut from its tip (fork pattern Sprint N used with Sprint M).
3. **Write plan doc** — follow `docs/sprint_m_plan.md` / `docs/sprint_n_plan.md` structure + full `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` structure:
   - Why this sprint (1-paragraph motivation).
   - Discovery (1–2 sessions) → implementation (2–3) → close (1).
   - STOP conditions (hard + soft).
   - Out of scope list.
   - Rollback plan.
   - Success metrics with numeric targets.
4. **Kickoff session prompt** — write `session_prompts/S126_<theme>_kickoff_prompt.md` + overwrite `NEXT.md`.
5. **CLAUDE.md banner flip** to new Sprint kickoff.
6. **Commit** `chore(sprint-<X>): S{N}26 kickoff — ...` and push.

### Lane C — Hardening bucket

1. **Pick 1–2 follow-ups with the user.** Acknowledge explicitly which follow-up IDs from the retros (e.g., "Sprint M FU #2 + Sprint N FU #8").
2. **Branch decision:**
   - Small + self-contained → piggyback commit on `feature/v1.4.10-cost-guardrail-budget` (same PR #18) if the PR has not merged.
   - Cross-cutting → cut `chore/<scope>` off `main` after #17/#18 merge.
3. **Implement + test each follow-up** with unit/integration as appropriate. Mirror the existing patterns in the codebase (skill rules still apply — no mocks, real services, etc.).
4. **Update the retro notes** — mark the picked follow-ups as landed in `docs/sprint_n_retro.md` (or `docs/sprint_m_retro.md` for carry-overs).
5. **Close** — `/session-close S125` generates S126 NEXT.md.

---

## 5. STOP FELTETELEK

**HARD (hand back to user):**
1. **#17 review-blocked** — if a blocking review lands on #17, halt Lane A and ask whether to address the review or pivot to Lane C.
2. **Lane A rebase conflicts outside CLAUDE.md** — if merging `main` introduces unexpected conflicts (e.g., in `src/aiflow/core/config.py` because another PR touched it), halt and surface the conflict set.
3. **Lane B plan scope > 1 Alembic migration OR > 2 new services** — that is sprint-kickoff territory, not a session decision. Halt and escalate to a plan-validator review (`architect` agent) before writing the full plan.
4. **Lane C — picked follow-up turns out to be > 90 min** — halt after the first 90 min and either ship what landed or hand back.

**SOFT (proceed with note):**
1. If `gh pr merge --squash --delete-branch` prompts interactively, document the exact command that ran and move on.
2. If CI flakes on rebase, re-run once; if it flakes again, note it in the session summary and hand back rather than retrying indefinitely.

---

## 6. NYITOTT (carried)

From Sprint N retro §"Follow-up issues", unchanged unless Lane C picked one up:

1. `CostAttributionRepository` ↔ `record_cost` consolidation.
2. Model-tier fallback ceilings → `CostGuardrailSettings`.
3. Grafana panel for `cost_guardrail_refused` vs `cost_cap_breached`.
4. litellm pricing coverage audit as CI step.
5. `/status` fetches `/openapi.json` + diffs tags (catches stale-uvicorn).
6. `CostSettings` umbrella (consolidate `BudgetSettings` + `CostGuardrailSettings`).
7. Soft-quota / over-draft semantics (customer ask).
8. `scripts/seed_tenant_budgets_dev.py` demo seeder.

Sprint M carry: live Vault rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC, Langfuse v3→v4, `SecretProvider` registry slot.

Sprint J carry: BGE-M3 weight cache CI artifact, Azure OpenAI Profile B live, resilience `Clock` seam (deadline 2026-04-30 — last chance), coverage uplift (issue #7).

---

## 7. SESSION VEGEN

```
/session-close S125
```

Utana: `/clear` -> `/next` -> S126.
