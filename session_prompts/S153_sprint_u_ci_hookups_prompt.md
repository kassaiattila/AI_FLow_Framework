# AIFlow [Sprint U] — Session 153 Prompt (CI hookups + tooling fixes)

> **Datum:** 2026-04-25 (snapshot date — adjust if session runs later)
> **Branch:** `feature/u-s153-ci-hookups` (cut from `main` after the Sprint U S152 kickoff PR squash-merges → new tip).
> **HEAD (expected):** Sprint U S152 kickoff PR squash on top of `fd2a8bc` (Sprint T close squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S152 — Sprint U kickoff. `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` + `docs/sprint_u_plan.md` + carry-forward triage. Operator picked Candidate B (operational hardening). Plan slates 4 execution sessions + close.
> **Terv:** `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` §2 Sessions / S153 row.
> **Session tipus:** IMPLEMENTATION (CI gates + pre-commit hook + tooling config).

---

## 1. MISSION

Sprint U's lowest-blast-radius batch. Five small wins, each independently revertable; collectively they shorten CI signal latency and close tooling papercuts that bit prior sprints. **No skill code change. No new unit/integration tests** — the deliverables *are* gates.

### Five wins

1. **OpenAPI drift CI step.** `scripts/check_openapi_drift.py` already exists; wire into `.github/workflows/ci.yml` as a `make api` boot + diff step against the committed `openapi.json` snapshot. Catches stale-uvicorn drift like the one that leaked through Sprint S S144.
2. **Weekly 4-combo matrix as GitHub Action.** Sprint P FU-2. Promote `scripts/measure_uc3_4combo_matrix.py` to a `nightly-regression.yml` weekly job. Skip-by-default behind `secrets.OPENAI_API_KEY` + scheduled trigger so forks don't try to run it.
3. **`vite build` pre-commit hook.** SR-FU-5. Hook in `.husky/pre-commit` (or `.git/hooks/pre-commit` template via `make install-hooks`) runs `cd aiflow-admin && npx vite build --mode development` when `aiflow-admin/` files staged. Catches the kind of `react-i18next`→`useTranslate` breakage that surfaced mid-PR in Sprint R S140.
4. **ruff-strips-imports tooling fix.** ST-FU-5. Find the underlying ruff config gap that strips imports inside `if TYPE_CHECKING` / guard blocks (Sprint T S148-S150 mitigation pattern: bundle imports + first usage in single Edit). Either pin a `pyproject.toml` config tweak or add a tracked exception list.
5. **BGE-M3 weight cache as standard CI artifact.** Carried Sprint J / Sprint S. Sprint S already added the `actions/cache@v4` step to `nightly-regression.yml`; promote to the standard `ci.yml` integration job so 1024-dim integration tests un-skip on every PR (today they only un-skip nightly).

### Out of scope for S153

- New unit / integration tests (S153 ships gates, not feature code).
- Skill code changes (`email_intent_processor`, `invoice_processor`, `aszf_rag_chat` untouched).
- Alembic migrations (head stays at 047).
- Endpoint / UI surface changes.
- The other Sprint U batches (S154 cost consolidation, S155 persona descriptors, S156 Sprint Q polish — separate sessions).

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint T closed 2026-04-25. PromptWorkflow consumer migration shipped: 3 skills × 3 descriptors wired (email_intent / invoice_extraction / aszf_rag baseline). Sprint U is the carry-forward catch-up sprint — operator picked Candidate B (operational hardening) at the S152 triage.

### Hova tartunk

S153–S156 execute Sprint U in 4 batches, S157 closes. S153 is the first batch — CI gates + tooling.

### Jelenlegi állapot

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2424 unit collected / 1 skipped (ST-SKIP-1 conditional Azure Profile B)
~116 integration | 432 e2e collected
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors live (email_intent_chain, invoice_extraction_chain, aszf_rag_chain baseline)
Default-off rollout preserved.
```

### Key files for S153

| Role | Path |
|---|---|
| Sprint U plan | `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` (§2 / S153 row, §3 gate matrix, §4 R1) |
| Sprint U companion | `docs/sprint_u_plan.md` |
| OpenAPI drift script | `scripts/check_openapi_drift.py` (exists; needs CI wiring) |
| 4-combo matrix script | `scripts/measure_uc3_4combo_matrix.py` (exists; needs GHA wiring) |
| Existing CI pipelines | `.github/workflows/ci.yml`, `.github/workflows/nightly-regression.yml` |
| Existing pre-commit | `.husky/` or `.git/hooks/` (verify present at session start) |
| ruff config | `pyproject.toml` |
| Sprint T retro reference | `docs/sprint_t_retro.md` (decision log ST-4 — ruff-strips-imports workaround) |

---

## 3. ELOFELTETELEK

```bash
git switch main
git pull --ff-only origin main
git checkout -b feature/u-s153-ci-hookups
git log --oneline -5                                                # confirm S152 kickoff squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current     # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1  # 2424 collected
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
ls scripts/check_openapi_drift.py scripts/measure_uc3_4combo_matrix.py     # confirm scripts exist
```

Stop, ha:
- Sprint U S152 kickoff PR not yet merged → wait or escalate.
- Alembic head ≠ 047 → drift; investigate before opening S153.
- Either of the two referenced scripts missing → triage before authoring CI wiring (script may have been renamed since the source retro).
- `git status` dirty → finish or stash first.

---

## 4. FELADATOK

### LEPES 1 — OpenAPI drift CI step

Read `scripts/check_openapi_drift.py` to understand its current invocation contract. Wire into `.github/workflows/ci.yml` as a job that:
1. Boots `make api` on a free port.
2. Curls `/openapi.json`.
3. Diffs against the committed snapshot at the well-known path (likely `aiflow-admin/openapi.json` or `docs/openapi.json` — confirm by reading the script).
4. Fails the CI run on any non-zero diff with a clear message ("OpenAPI drift detected — run `make openapi-snapshot` and commit").

Include a companion pre-commit hook stub (or `make openapi-snapshot` target) so contributors can refresh the snapshot locally. Keep the step **hermetic** — no network, no LLM.

### LEPES 2 — Weekly 4-combo matrix as GHA

Read `scripts/measure_uc3_4combo_matrix.py` to understand its argspec + output shape. Add a job to `.github/workflows/nightly-regression.yml` (or a new `weekly-regression.yml` if scheduling differs) that:
1. Triggers on `schedule: cron: '0 7 * * 1'` (Monday 07:00 UTC) **and** `workflow_dispatch` for manual runs.
2. Runs only when `secrets.OPENAI_API_KEY` is set (skip-by-default on forks).
3. Uploads the matrix output as a workflow artifact.
4. Posts a summary to GitHub Actions step summary.

Document the schedule + opt-in env in `docs/sprint_u_plan.md` §"Operator activation" (or a new `docs/ci_schedules.md` if the section grows).

### LEPES 3 — `vite build` pre-commit hook

Confirm whether the repo uses `husky` (look for `.husky/`) or a manual `.git/hooks/` template (look for `Makefile` `install-hooks` target). Whichever it is:
1. Add a hook step that, when staged files include `aiflow-admin/`, runs `cd aiflow-admin && npx vite build --mode development`.
2. Skip the build when no `aiflow-admin/` files staged (fast path for backend-only commits).
3. Document the hook installation in `README.md` or `CONTRIBUTING.md` if not already covered.

### LEPES 4 — ruff-strips-imports tooling fix

Read Sprint T retro decision log entry ST-4 (in `docs/sprint_t_retro.md`) and reproduce the failure case. Likely root causes:
- A `select = [...]` rule like `F401` (unused-import) that ignores `if TYPE_CHECKING:` guards.
- A `fix = true` interaction with conditional imports.

Either pin a `pyproject.toml` `[tool.ruff.lint]` config tweak (e.g., `extend-ignore-init-module-imports = true` or per-file ignore for guard-block files), or add a tracked exception list with a `# noqa` comment + a comment pointing back to ST-4 for context. Document the chosen mitigation in the commit message.

### LEPES 5 — BGE-M3 weight cache as standard CI artifact

Read the existing cache step in `.github/workflows/nightly-regression.yml` (Sprint S S145 wiring). Promote to `.github/workflows/ci.yml` integration job so 1024-dim integration tests run on every PR:
1. Add the `actions/cache@v4` step at the integration job's start, keyed on `${{ runner.os }}-bge-m3-${{ hashFiles('scripts/bootstrap_bge_m3.py') }}`.
2. Run `scripts/bootstrap_bge_m3.py` if cache miss.
3. Confirm the `RAGEngineService` integration tests (`tests/integration/skills/test_uc2_rag.py`) un-skip when the weights are present.

If the cache size hits GitHub Actions limits, fall back to a docker-image baked cache or a network-cached HF mirror — document the choice.

### LEPES 6 — Validate + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # still 2424 collected (no test changes)

git add .github/workflows/ \
        scripts/ \
        pyproject.toml \
        .husky/ \
        Makefile \
        docs/ \
        README.md
git commit -m "ci(sprint-u): S153 — CI hookups + tooling fixes"
git push -u origin feature/u-s153-ci-hookups
gh pr create --base main --head feature/u-s153-ci-hookups \
  --title "Sprint U S153 — CI hookups + tooling fixes"
```

Then `/session-close S153` — which queues S154 (cost-settings consolidation).

---

## 5. STOP FELTETELEK

**HARD:**
1. Sprint U S152 kickoff PR not yet merged on `main` — wait until `main` carries the Sprint U S152 squash.
2. Alembic head ≠ 047 → drift; investigate before opening S153.
3. CI flake injection — adding the OpenAPI drift step or 4-combo GHA causes ≥ 2 consecutive false reds → halt; rollback the offending step and triage in S157 retro.
4. The 4-combo matrix script doesn't exist or has been renamed → halt; triage before authoring GHA.
5. ruff-strips-imports root cause turns out to be a ruff bug (not a config issue) → halt; file upstream issue + add tracked exception list as interim mitigation.

**SOFT:**
- BGE-M3 cache size exceeds GitHub Actions cache quota → fall back to docker-baked cache or HF mirror; document in the commit.
- `vite build` pre-commit hook adds > 30s to commit time → fall back to `vite build` only on `aiflow-admin/src/**` changes (more selective filter); document in CONTRIBUTING.md.

---

## 6. SESSION VEGEN

```
/session-close S153
```

The `/session-close` will:
- Validate lint + unit collect.
- Stage + commit the CI/tooling diff (`.github/workflows/`, `pyproject.toml`, `.husky/`, `scripts/`, `Makefile`, docs).
- Push the branch.
- Open the kickoff PR.
- Generate `session_prompts/NEXT.md` for S154 — the cost / settings consolidation session.

---

## 7. SKIPPED-ITEMS TRACKER (carry from Sprint U S152)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SU-SKIP-1 | `.github/workflows/nightly-regression.yml` (S153 new) | Weekly 4-combo matrix GHA — skip on PR runs | `secrets.OPENAI_API_KEY` + scheduled trigger |
| SU-SKIP-2 | (S155 future) | Langfuse listing real-server integration | Live Langfuse instance reachable from CI |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-2 | Sprint T retro | Expert/mentor persona descriptors | **Sprint U S155** |
| ST-FU-3 | Sprint T retro | Per-step cost ceiling consolidation | **Sprint U S154** |
| ST-FU-4 | Sprint T retro | Operator parity scripts `--output` flag | **Sprint U S156** |
| SR-FU-4 / SR-FU-6 | Sprint R retro | Live Playwright `/prompts/workflows` + Langfuse listing | **Sprint U S155** |

S153 hits `.github/workflows/`, pre-commit, ruff config, and the BGE-M3 cache promotion. S154+ continues per the Sprint U plan.
