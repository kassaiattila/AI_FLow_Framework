# AIFlow [Sprint T] — Session 151 Prompt (Sprint T close + tag v1.5.3)

> **Datum:** 2026-04-25 (snapshot — adjust if session runs later)
> **Branch:** `chore/sprint-t-close` (cut from `main` after PR #42 squash-merges → new tip).
> **HEAD (expected):** Sprint T S150 squash on top of `e936eb3` (S149 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S150 — `aszf_rag_chat` baseline persona consumes `aszf_rag_chain` (PR #42 opened, **+19 unit / +1 integration**, full unit suite 2423 PASS / 1 skipped, Sprint J UC2 retrieval baseline Profile A BGE-M3 PASS, real-OpenAI parity smoke on HU UC2 query #1 PASS in 82 s). Lessons learned: (a) the descriptor's `answer` step had no matching legacy `prompt_manager.get(...)` call (legacy generates the answer directly from `system_prompt_<role>` in one LLM hop) — per S149's lesson, no new call site introduced, the executor is resolution-only; (b) when the formatter (ruff) auto-strips type-only imports between Edit waves, bundle the imports + first usage in a single Edit OR keep a referencing helper around to anchor them — the import block survives the next pass.
> **Terv:** `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` §5 close + §3 gate matrix all rows green + §6 follow-up triage.
> **Session tipus:** SPRINT CLOSE (retro + PR description + CLAUDE.md banner + tag prep + carry-forward queue).

---

## 1. MISSION

Close Sprint T. Three per-skill PromptWorkflow consumer migrations have shipped (S148 email_intent_processor + S149 invoice_processor + S150 aszf_rag_chat baseline). The shim is now proven on three skills with very different LLM-call surfaces and persona-variant carve-out semantics.

S151 deliverables:
1. **`docs/sprint_t_retro.md`** — scope, test deltas, decisions log (ST-1..ST-N), follow-ups (carry to Sprint U).
2. **`docs/sprint_t_pr_description.md`** — single PR description for the umbrella Sprint T PR (squash sequence S148+S149+S150 onto the new `chore/sprint-t-close` branch).
3. **CLAUDE.md banner** — bump version to **v1.5.3**, refresh §Overview Sprint T entry, update Key Numbers (services, endpoints, routers, Alembic, unit counts, integration counts, E2E counts), include the 3 ready+wired PromptWorkflow descriptors mention.
4. **Tag prep** — `git tag -a v1.5.3 -m "Sprint T — PromptWorkflow per-skill migrations (3 skills)"` queued post-merge.
5. **`session_prompts/NEXT.md`** for **S152** (Sprint U kickoff) — read the next plan doc and queue the first Sprint U session.

ST-FU-1 (JWT singleton CI failure in `tests/unit/api/test_rag_collections_router.py`) lands here as a **must-clean** before tag — this is the last call before Sprint T tag.

S151 **does not** touch:
- Any per-skill workflow code (S148/S149/S150 already shipped).
- `prompts/workflows/` descriptors (frozen for Sprint T).
- `src/aiflow/prompts/workflow*.py` framework code (Sprint R foundation; only bug-fix territory if S151 surfaces one).
- Any Alembic migration (head stays at 047).

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint T sequence delivered 2026-04-25:
- **S147** (PR #39 `9c76239`): kickoff plan + carry-forward triage from Sprint S retro.
- **S148** (PR #40 `aa74e02`): `email_intent_processor` consumes `email_intent_chain` — 1 LLM call site, hybrid ML+LLM short-circuit preserved. +10 unit / +1 integration.
- **S149** (PR #41 `e936eb3`): `invoice_processor` consumes `invoice_extraction_chain` — 3 LLM call sites, per-step cost ceilings (`extract_header` 0.02 USD, `extract_lines` 0.03 USD), `CostGuardrailRefused` propagation. +15 unit / +1 integration.
- **S150** (PR #42 `d353603`): `aszf_rag_chat` baseline persona consumes `aszf_rag_chain` — 3 mappable call sites (`rewrite_query`, `system_baseline` baseline-only, `extract_citations`), persona carve-out keeps expert/mentor on legacy. +19 unit / +1 integration.

Total Sprint T unit deltas: +44 unit / +3 integration / 0 Alembic / 0 new endpoints / 0 new UI pages.

### Hova tartunk

**Sprint T close end-state (post-S151):**
- All three per-skill consumer migrations merged into `main`.
- v1.5.3 tag queued post-merge.
- Sprint U replan kicked off (next capability — TBD per `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §5 or follow-on doc).

### Jelenlegi állapot (post-S150)

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2423 unit PASS / 1 skipped (Azure Profile B conditional)
~115 integration | 432 E2E collected (no UI surface change in S148/S149/S150)
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors ready, 3/3 skill consumers wired
   (email_intent_chain ✓ | invoice_extraction_chain ✓ | aszf_rag_chain ✓ baseline only)
```

### Key files for S151

| Role | Path |
|---|---|
| Sprint plan | `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` |
| Capability roadmap | `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` (Sprint T = §3 R3; §4-5 forward) |
| S148 retro reference | `docs/sprint_r_retro.md`, `docs/sprint_r_pr_description.md` (template) |
| Session archive | `session_prompts/S148_*.md`, `S149_*.md`, `S150_*.md` |
| ST-FU-1 candidate | `tests/unit/api/test_rag_collections_router.py` (1 of 3 still failing on main) |

---

## 3. ELOFELTETELEK

```bash
git switch main                                              # presumes PR #42 merged
git pull --ff-only origin main
git checkout -b chore/sprint-t-close
git log --oneline -5                                          # confirm S150 squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current        # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # 2423 collected (or +new)
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
```

Stop, ha:
- PR #42 not yet merged → wait or escalate; the S151 branch must start from a clean S150 tip on `main`.
- Alembic head ≠ 047 → drift; investigate before opening S151.
- `git status` dirty → finish or stash first.

---

## 4. FELADATOK

### LEPES 1 — ST-FU-1 (JWT singleton) — must-clean before tag

```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/api/test_rag_collections_router.py -v
```

Currently 1/3 fails on main: `test_list_filters_by_tenant_id`. Root cause documented in S150 PR #42 + retro: middleware `AuthProvider` re-init outside the test's `patch.object(from_env)` block. Two clean fix paths:

**A. Lifecycle fix in `_client_and_headers()`** — extend the `patch.object(AuthProvider, "from_env", return_value=auth)` context to wrap the entire test (return a context manager from the helper, callers use `with`). Bound by ~20-30 LOC.

**B. DI-layer pinning** — bind the `AuthProvider` instance into the FastAPI app's dependency-injection container at `create_app()` time and have the middleware read from there instead of calling `from_env()` per-request. Bound by ~40-60 LOC.

Pick **A** for S151 close (smaller blast radius, no framework change). Defer **B** to a hardening sprint if the same pattern appears in other test files.

### LEPES 2 — `docs/sprint_t_retro.md`

Mirror `docs/sprint_r_retro.md` shape:
- Scope delivered (S147-S151 itemized).
- Test deltas (unit/integration/E2E counts; +44 unit / +3 integration).
- Per-skill summary (call sites migrated, lessons learned).
- Decisions log (ST-1: persona carve-out via resolver-returns-None; ST-2: `validate` step `required: false` mapping to pure-Python legacy code; ST-3: per-step cost ceilings via local `CostEstimator` + `CostGuardrailRefused` raise; ST-4: ruff-strips-imports mitigation pattern).
- Follow-ups (ST-FU-2 expert/mentor descriptors; carry-forwards from Sprint S/J/M/N).

### LEPES 3 — `docs/sprint_t_pr_description.md`

Single umbrella PR description for the (already-merged) Sprint T sequence. Reference each PR (#40/#41/#42), summarize squash deltas, list out-of-scope carries.

### LEPES 4 — CLAUDE.md banner

```
v1.5.3 Sprint T — MERGED 2026-04-25, tag v1.5.3 (queued post-merge),
squashes 8a84347 (#40, S148) + e936eb3 (#41, S149) + d353603 (#42, S150).
PromptWorkflow per-skill consumer migrations: 3 skills × 3 descriptors
wired (email_intent_chain ✓ | invoice_extraction_chain ✓ | aszf_rag_chain ✓
baseline only). 0 Alembic, 0 new endpoints, 0 new UI pages, 0 skill behaviour
change on flag-off (default). Per-skill flag-on opt-in via
AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV. ...
```

Update Key Numbers: 2423 unit (post-S150 baseline), ~115 integration, 432 E2E. Mention the 3 descriptors ready+wired.

### LEPES 5 — Tag prep

```bash
git tag -a v1.5.3 -m "Sprint T — PromptWorkflow per-skill migrations (3 skills)"
# Push the tag AFTER the umbrella PR merges into main.
```

### LEPES 6 — `session_prompts/NEXT.md` for S152 (Sprint U kickoff)

Read `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §5 or the next plan doc. Identify the first Sprint U session. Generate the standard kickoff template (mirror S147's shape).

If there's no Sprint U plan yet, create a placeholder NEXT.md asking the operator to point at the next plan doc.

### LEPES 7 — Lint + commit + push + PR + close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/api/test_rag_collections_router.py -q   # 3/3 PASS

git add docs/sprint_t_retro.md docs/sprint_t_pr_description.md CLAUDE.md \
        tests/unit/api/test_rag_collections_router.py \
        session_prompts/NEXT.md session_prompts/S152_*.md \
        session_prompts/S151_sprint_t_close_prompt.md
git commit -m "chore(sprint-t): close — retro + PR description + tag v1.5.3 prep + ST-FU-1 fix + S152 NEXT"
git push -u origin chore/sprint-t-close
gh pr create --base main --head chore/sprint-t-close \
  --title "Sprint T close — retro + PR description + tag v1.5.3 prep"
```

Then `/session-close S151` — which queues S152 (Sprint U kickoff).

---

## 5. STOP FELTETELEK

**HARD:**
1. PR #42 (Sprint T S150) not yet merged — wait until `main` has the aszf_rag_chat migration squash.
2. ST-FU-1 fix bigger than ~50 LOC after first attempt → fall back to DI-layer pinning (path B), or carry to a separate hardening PR (do NOT block tag v1.5.3 if the test was already failing pre-Sprint T).
3. CLAUDE.md banner refresh accidentally truncates Sprint S/Q/P/O/N/M/L history → halt; the Overview banner is append-only, never delete prior sprint entries.
4. Sprint U plan doc missing or ambiguous → stop at S152 NEXT generation; ask operator to point at the next plan doc before writing the kickoff prompt.

**SOFT:**
- ST-FU-1 fix path A (lifecycle) doesn't generalise → document path B in retro for a hardening sprint.
- Operator wants to ship v1.5.3 without ST-FU-1 fix → flag in retro as "carried-pre-existing-failure" and proceed.

---

## 6. SESSION VEGEN

```
/session-close S151
```

The `/session-close` will:
- Validate lint + unit + e2e collect.
- Re-run `tests/unit/api/test_rag_collections_router.py` as the final gate (3/3 PASS expected).
- Stage + commit the close diff (retro + PR description + CLAUDE.md banner + ST-FU-1 fix + S152 NEXT).
- Push the branch.
- Open the umbrella Sprint T close PR.
- Generate `session_prompts/NEXT.md` for S152 — Sprint U kickoff.

---

## 7. SKIPPED-ITEMS TRACKER (carry from S147 / S148 / S149 / S150)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-1 | Sprint T plan §5 | JWT singleton CI failure (1 of 3 still failing in `test_rag_collections_router.py`) | **MUST-CLEAN in S151 close** — pin lifecycle in `_client_and_headers` |
| ST-FU-2 | Sprint T plan §11 | Expert/mentor persona descriptors (`aszf_rag_chain_expert/_mentor`) | Post-Sprint-T (Sprint U candidate) |
| SR-FU-4/5/6 | Sprint R retro | Live-stack Playwright + vite-build hook + Langfuse listing | Sprint U side delivery if bandwidth |
| **NEW from S150** | session_prompts/S150 §3 step 5 | 20-item harness flag-on parity script needs `--output` flag (carried from S149) | S151 close (small refactor) |
| **NEW from S150** | session_prompts/S150 §6 SOFT | Per-test fresh `AuthProvider` + secret-cache fixture pattern (path A) | S151 close as ST-FU-1 fix |

S151 closes Sprint T + tags `v1.5.3`. S152 opens Sprint U (kickoff).
