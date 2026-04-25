# AIFlow [Sprint T] — Session 147 Prompt (Sprint T kickoff — carry-forward triage + plan doc)

> **Datum:** 2026-04-27 (snapshot date — adjust if session runs later)
> **Branch:** `feature/t-s147-sprint-t-kickoff` (cut from `main` after PR #38 squash-merges → new tip).
> **HEAD (expected):** Sprint S close PR #38 squash on top of `d6ee813` (Sprint S S145).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S146 — Sprint S close. `docs/sprint_s_retro.md` + `docs/sprint_s_pr_description.md` + CLAUDE.md banner flip (Sprint S MERGED 2026-04-26, tag `v1.5.2` queued). PR #38 opened against `main`.
> **Terv:** to be authored — `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` is this session's deliverable.
> **Session tipus:** KICKOFF (plan + carry-forward triage, no feature code change).

---

## 1. MISSION

Open Sprint T with the same kickoff discipline that Sprint J / M / N / O / P / Q / R / S used: a single `01_PLAN/117_*` plan doc, the carry-forward queue triaged, and a clear scope for sessions S148+. Three SDLC outputs:

1. **Carry-forward reconcile** — Sprint J `Clock` seam deadline (2026-04-30) was flagged as overdue in S146's retro, but `docs/quarantine.md` says Sprint O FU-5 already resolved it. Pick one source of truth and update the other (most likely: drop the carry-forward from CLAUDE.md, since the test is no longer xfail-quarantined). Plus a quick audit of what the "1 skipped" test in `tests/unit/` actually is.
2. **`01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md`** — the Sprint T plan doc. Scope: per-skill `PromptWorkflow` migrations (S141-FU-1 / S141-FU-2 / S141-FU-3), each session gated by its UC golden-path. Include a Sprint T capability headline, session split (S148 / S149 / S150 / S151 close), gate matrix (which UC / which test / which threshold), risk register, follow-up table.
3. **`docs/sprint_t_plan.md`** (operator-facing companion) — narrative summary of §1 and §2 above for stakeholder review. Lighter than the plan doc; mirrors `docs/sprint_n_plan.md` style.

S147 **does not** touch:
- Skill code (no `email_intent_processor` / `invoice_processor` / `aszf_rag_chat` change).
- New tests (the migrations land in S148+).
- Migrations (no Alembic — Sprint T is a code-only sprint, expected to ship 0 migrations).
- The `customer` column rename (SS-FU-1, SS-FU-5; deferred to a separate refactor sprint, not Sprint T).
- Profile B Azure live MRR@5 (SS-SKIP-2; credit pending).

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint S closed 2026-04-26 on `chore/sprint-s-close` (PR #38). Three squash-merged feature PRs:

| PR | Squash | Headline |
|---|---|---|
| #34 | `95ec89e` | S143 — `RAGEngineService.query()` ProviderRegistry refactor + Alembic 046 |
| #35 | `bc59a8f` | S144 — `/rag/collections` admin UI + `set_embedder_profile()` mutation |
| #37 | `d6ee813` | S145 — `RagMetricsHarness` + Alembic 047 + BGE-M3 weight CI cache |

Plus `chore/consolidate-dev-env` (PR #36) cut between S144 and S145.

### Hova tartunk

Sprint T closes the **PromptWorkflow consumption loop** that Sprint R left scaffolded but unconsumed. Sprint R shipped the contract + admin UI + executor scaffold but explicitly deferred per-skill migration to keep golden paths untouched. S148+ migrate one skill per session, gated by its UC test:

- **S148** — `email_intent_processor` consumes `email_intent_chain`. Gate: Sprint K UC3 4/4 golden-path E2E.
- **S149** — `invoice_processor.workflows.process` consumes `invoice_extraction_chain`. Gate: Sprint Q UC1 golden-path slice (≥ 75% accuracy / invoice_number ≥ 90%).
- **S150** — `aszf_rag_chat.workflows.query` baseline persona consumes `aszf_rag_chain`. Gate: Sprint J UC2 MRR@5 ≥ 0.55.
- **S151** — Sprint T close (retro + PR description + CLAUDE.md banner + tag `v1.5.3`).

### Jelenlegi állapot (post-Sprint-S)

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2380 unit collected (2379 PASS / 1 skipped — identity TBD in §4 LEPES 1)
~113 integration | 432 E2E collected (~430 active, ~2 may be parametrize splits)
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors ready for consumption (email_intent_chain,
                                                     invoice_extraction_chain,
                                                     aszf_rag_chain)
0 skill consumes the executor today (Sprint R left scaffold-only)
```

---

## 3. ELOFELTETELEK

```bash
git switch main                                                    # presumes PR #38 merged
git pull --ff-only origin main
git checkout -b feature/t-s147-sprint-t-kickoff
git log --oneline -5                                                # confirm S146 squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current     # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1
```

Stop, ha:
- PR #38 not yet merged → wait or escalate (the kickoff branch needs the docs on `main` so it doesn't conflict).
- Alembic head ≠ 047 → S145 squash drift; investigate before opening Sprint T.
- `git status` dirty → finish or stash first.
- Operator wants to defer Sprint T or reorder the per-skill queue (e.g. start with `aszf_rag_chat` instead of `email_intent_processor`) → halt + revisit `01_PLAN/114_*` §3 + the S141-FU-1/2/3 ordering call.

---

## 4. FELADATOK

### LEPES 1 — Carry-forward reconcile (`Clock` seam + 1-skipped audit)

Two cleanup tasks before any plan-doc authoring; both are pure investigative + doc fixes.

**LEPES 1a — `Clock` seam reconcile.**

CLAUDE.md banner says `1 xfail-quarantined: resilience 50ms timing flake` with deadline 2026-04-30. Sprint J retro flagged it as the open Sprint J carry. S146's retro (`docs/sprint_s_retro.md` §"Carried" + §"Open follow-ups") repeats the deadline-overdue framing. **But `docs/quarantine.md` already lists this under "Resolved quarantine"** with Sprint O FU-5 as the fix.

```bash
# 1. Re-read the resolution
grep -nE "resilience|Clock|xfail" docs/quarantine.md

# 2. Confirm the test no longer carries an xfail decorator
grep -nE "@pytest.mark.xfail|@pytest.mark.skip" tests/unit/services/test_resilience_service.py

# 3. Run the resilience suite to verify deterministic green
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/services/test_resilience_service.py -q
```

If steps 2 + 3 confirm "no xfail, all green" → drop the carry-forward from:
- `CLAUDE.md` Key Numbers section: remove `1 xfail-quarantined: resilience 50ms timing flake` from the unit-tests bullet.
- `docs/sprint_s_retro.md` "Carried" section: remove the Clock-seam line from §"Carried".
- (The Sprint S retro docs are docs — editing them is fine in S147; flag the change in the commit message so the audit trail is clear.)

If steps 2 or 3 fail → the carry is real, file a GH issue, escalate to operator. Do NOT silently leave it.

**LEPES 1b — "1 skipped" audit.**

The unit-test collect prints `2380 collected` but CLAUDE.md says `2379 PASS / 1 skipped`. Identify which test, why it's skipped, whether it should be unskipped or remain skipped with a documented reason.

```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q -rs 2>&1 | grep -E "^SKIPPED" | head -5
```

If the skipped test has a clear conditional reason (e.g. "skip on Windows", "skip without docling weights"), document in `docs/quarantine.md` under "Resolved quarantine" or in a new "Conditional skips" section. If the skip looks accidental, file a fix-up follow-up under SS-FU-X for Sprint T retro.

### LEPES 2 — `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md`

Mirror the structure used by `01_PLAN/116_SPRINT_S_FUNCTIONAL_VECTOR_DB_PLAN.md` (Sprint S's plan doc). Sections:

1. **Headline + capability cohort delta.** Table showing PromptWorkflow consumers go from 0 (Sprint R) to 3 (Sprint T close). Reuse the Sprint R retro's "Cohort delta" diagram style.
2. **Scope per session** — table with session ID, target skill, gate test, expected diff size, risk level.
3. **Plan, gate matrix.** Each row is a session; columns are: skill / workflow descriptor / golden-path test / threshold / rollback path. The threshold column is the most important — it's what blocks merge.
4. **Risk register.**
   - R1: `email_intent_processor` has *both* a sklearn classifier path *and* an LLM path; the workflow only abstracts the LLM path. Migration must preserve the sklearn-first / sklearn-only / sklearn-then-llm strategy logic from Sprint P.
   - R2: `invoice_processor.workflows.process` is the freshest Sprint Q golden path. Migration changes only the prompt-loading surface; the extraction-result schema must stay byte-identical (S136's `EmailDetailResponse.extracted_fields` field must keep working).
   - R3: `aszf_rag_chat` has 3 role variants (baseline / expert / mentor). S150 migrates only baseline; expert / mentor remain on the legacy per-prompt path. This is the same pattern Sprint R used for the S141 scaffold.
   - R4: All three migrations land behind `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + per-skill `SKILLS_CSV` opt-in. Default-off → zero rollback risk for any tenant that hasn't explicitly enabled the flag.
5. **Follow-up table.** Carry from Sprint S (SS-FU-1 / SS-FU-5 / SS-SKIP-2) + Sprint R (SR-FU-4 / SR-FU-5 / SR-FU-6). Add Sprint T's own ST-FU-X entries if the plan reveals new ones.
6. **Test count expectations.** Each skill migration adds ~5-10 unit tests + 1 integration on real PG. Total expected delta: **+15-30 unit / +3 integration**. E2E unchanged (no UI surface change). Alembic head unchanged (047).
7. **Definition of done.** Each session: green golden-path test + flag-on smoke + flag-off smoke (no behaviour change) + ruff / TSC clean.

### LEPES 3 — `docs/sprint_t_plan.md`

Lighter operator-facing summary, mirrors `docs/sprint_n_plan.md` / `docs/sprint_m_plan.md` style. Sections:

1. **Headline** — "Sprint T closes the PromptWorkflow consumption loop that Sprint R scaffolded."
2. **3 deliveries in 3 sessions** — bullet list per S148/S149/S150 with the gate threshold.
3. **What stays unchanged** — flag defaults (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` default; per-skill `SKILLS_CSV` empty by default), 0 Alembic, 0 UI page added, 0 endpoint added.
4. **Carry-forward** — `customer` rename + Profile B Azure + SR-FU-4/5/6 stay on the queue.
5. **Operator activation** — what flags to flip per skill once Sprint T merges (per-tenant rollout plan).

### LEPES 4 — Commit + PR + close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/                   # docs+CLAUDE.md only — should still pass
git add 01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md \
        docs/sprint_t_plan.md \
        docs/quarantine.md \
        CLAUDE.md \
        docs/sprint_s_retro.md  # only if LEPES 1a removed the Clock-seam carry
git commit -m "feat(sprint-t): S147 — Sprint T kickoff plan + carry-forward triage"
git push -u origin feature/t-s147-sprint-t-kickoff
gh pr create --base main --head feature/t-s147-sprint-t-kickoff \
  --title "Sprint T S147 — kickoff plan + carry-forward triage"
```

Then `/session-close S147` — which queues S148 (`email_intent_processor` PromptWorkflow migration).

---

## 5. STOP FELTETELEK

**HARD:**
1. PR #38 (Sprint S close) not yet merged — wait until `main` has the Sprint S retro + PR description + banner; otherwise the kickoff branch starts from a stale tip.
2. LEPES 1a discovers the Clock-seam test is *still* xfail or flaking → halt; this is the deadline-overdue carry from Sprint J and needs operator triage before Sprint T can claim a clean kickoff.
3. Operator dispute on Sprint T scope (e.g. wants to start with `aszf_rag_chat` baseline instead of `email_intent_processor`) → halt + revisit ordering decision.
4. Sprint S close PR #38 has unresolved review comments → halt; reconcile before cutting Sprint T branch off `main`.

**SOFT:**
- LEPES 1b "1 skipped" turns out to be a Windows-only docling skip → document, proceed.
- The 432-vs-430 E2E count discrepancy turns out to be parametrize splits → document in §"Test count expectations", proceed.
- Operator hasn't pushed tag `v1.5.2` yet → Sprint T can still kick off, but the retro PR description should mention the tag is outstanding.

---

## 6. SESSION VEGEN

```
/session-close S147
```

The `/session-close` will:
- Validate lint + e2e collect (no test code change → unit re-run optional).
- Stage + commit the plan doc + companion + any LEPES 1 cleanup.
- Push the kickoff branch.
- Generate `session_prompts/NEXT.md` for S148 — `email_intent_processor` PromptWorkflow migration (the smallest-blast-radius migration first per Sprint R retro decision SR-6).

---

## 7. SKIPPED-ITEMS TRACKER (folytatas Sprint S close-ból)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SS-FU-1 | Sprint S retro | `create_collection` tenant-aware arg + `customer` deprecation | Kulon refactor sprint (NEM Sprint T) |
| SS-FU-5 | Sprint S retro | `rag_collections.customer` column drop | Kulon refactor (after SS-FU-1) |
| SS-SKIP-2 | Sprint S retro | Profile B (Azure OpenAI) live MRR@5 | Azure credit |
| S141-FU-1 | Sprint R retro | `email_intent_processor` PromptWorkflow migration | **Sprint T S148** |
| S141-FU-2 | Sprint R retro | `invoice_processor.workflows.process` PromptWorkflow migration | **Sprint T S149** |
| S141-FU-3 | Sprint R retro | `aszf_rag_chat.workflows.query` baseline migration | **Sprint T S150** |
| SR-FU-4 | Sprint R retro | Live-stack Playwright for `/prompts/workflows` | Sprint T (S148+ side delivery) |
| SR-FU-5 | Sprint R retro | `vite build` pre-commit hook | Sprint T (S148+ side delivery) |
| SR-FU-6 | Sprint R retro | Langfuse workflow listing | Sprint T or later |
| Sprint J Clock seam | CLAUDE.md key-numbers + Sprint S retro | Resilience 50ms timing flake | **TRIAGE in S147 LEPES 1a** — likely already resolved per `docs/quarantine.md`; reconcile both docs |
| 1-skipped unit test | CLAUDE.md key-numbers | Identify the skipped test + reason | **TRIAGE in S147 LEPES 1b** |

S147 closes the kickoff envelope — the per-skill migrations themselves land in S148/S149/S150.
