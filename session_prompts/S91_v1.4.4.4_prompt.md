# AIFlow Sprint H — Session 91 Prompt (v1.4.4.4: coverage uplift → close issue #7)

> **Datum:** 2026-04-27
> **Branch:** `feature/v1.4.4-consolidation` (S90 committed as `ea72c6b`)
> **HEAD:** `ea72c6b` fix(aiflow-admin): S90 — journey E2E triage + contract regressions
> **Port:** API 8102 | Frontend Vite :5174 (per `tests/e2e/conftest.py`)
> **Session tipus:** Coverage uplift + gate flip. Code risk: low (tests only). Process risk: low.
> **Master terv:** `01_PLAN/session_S88_v1_4_4_consolidation_kickoff.md` §"Session breakdown — S91" (originally scoped as S90; shifted one session because S89 triggered the HARD stop on journey red).

---

## KONTEXTUS

S90 restored the six journey E2E suites to 58/58 green by fixing four real UI contract regressions (sidebar settings group + archive discoverability, journey-card 1-to-1 wiring, Demo/Live badge fallback, RAG delete-dialog copy) and tightening a handful of Playwright locators that had drifted since the last UI refresh. Evidence: `out/s90_triage.md`, commit `ea72c6b`.

Issue #7 has been deferred since v1.4.3: global test coverage has been hovering under the 80% gate, so `fail_under=80` was not flipped on at Phase 1d merge. S91 picks that up — raise coverage on the 3-5 worst-covered modules, then flip the gate.

Open follow-up from earlier sprints: the stale `test_alembic_034` assertion (queued in v1.4.4 CLAUDE.md notes) is still unresolved; S91 should either complete or re-queue it.

---

## ELOFELTETELEK

```bash
git branch --show-current                                     # feature/v1.4.4-consolidation
git log --oneline -3                                          # top: ea72c6b fix(aiflow-admin): S90 …
.venv/Scripts/python.exe -c "from aiflow._version import __version__; print(__version__)"   # 1.4.3
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '07_ai_flow_framwork-(db|redis)'
curl -s http://localhost:8102/health | python -m json.tool | head -5                        # status "ready"
```

If postgres/redis are down: `docker compose up -d db redis`. If API isn't up: `make api`.

---

## FELADATOK

### LEPES 1 — Baseline coverage

```bash
.venv/Scripts/python.exe -m pytest tests/ --cov=aiflow \
  --cov-report=term-missing --cov-report=html:out/coverage_s91 \
  2>&1 | tee out/s91_coverage_baseline.log
```

Capture the current global percentage, identify the 3–5 worst-covered modules, and write their names + current coverage into `out/s91_coverage_plan.md` (one row per module: `module | current % | target % | test file to grow`).

### LEPES 2 — Targeted unit tests

Pick the worst-covered modules. Good candidates based on prior sessions (verify before writing):

- `aiflow.pipeline.adapters.*` (any adapter still under 70%)
- `aiflow.providers.*` (provider abstractions)
- `aiflow.services.intake.sink.IntakePackageSink`
- `aiflow.services.observability.*` (metrics / log wiring)
- `aiflow.engine.policy.*` (policy engine branches)

For each module:
1. Read the source + existing test coverage gaps (HTML report is easiest).
2. Write targeted unit tests in the matching `tests/unit/` file — **real** Postgres/Redis/LLM where the module hits them (per `tests/CLAUDE.md`).
3. Re-run the targeted tests and confirm coverage gain.

### LEPES 3 — Flip the global gate

Once `pytest tests/ --cov=aiflow` reports ≥ 80% line coverage:

```bash
# pyproject.toml
[tool.coverage.report]
fail_under = 80      # ← previously commented or 0
```

Run the regression suite once more with the gate on:

```bash
.venv/Scripts/python.exe -m pytest tests/ --cov=aiflow --cov-fail-under=80
```

Confirm it passes.

### LEPES 4 — Close issue #7

```bash
gh issue view 7 --comment-limit 3
# Reference the final coverage number and the commit that flipped the gate
gh issue close 7 --comment "Closed by S91: global coverage ≥ 80%, fail_under flipped on in <commit-sha>."
```

### LEPES 5 — Optional: stale `test_alembic_034` assertion

If time remains, fix the stale assertion (see `01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md` open follow-ups). Otherwise, keep it queued for a future v1.4.4 session.

### LEPES 6 — Commit

```bash
git add tests/unit/** pyproject.toml out/s91_coverage_baseline.log out/s91_coverage_plan.md
git commit -m "$(cat <<'EOF'
test(aiflow): S91 — raise coverage to ≥80% + flip fail_under gate

- Targeted unit tests for <modules>; each was < 70% before S91.
- Flipped `fail_under=80` in pyproject.toml; regression suite still green.
- Closes #7.

Part of Sprint H v1.4.4 Consolidation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### LEPES 7 — Close session

```
/session-close S91
```

---

## STOP FELTETELEK

- **HARD:** Global coverage gap is too large to close in one session (> 10 p.p. below 80%) — halt, plan a multi-session coverage roadmap instead of mechanically chasing numbers.
- **HARD:** Adding tests requires non-trivial production-code refactors to make modules testable — stop, surface the refactor scope, split into its own session.
- **HARD:** Any coverage tactic that relies on mocking Postgres/Redis/LLM — reject per `tests/CLAUDE.md`. Write an integration test against real services or skip the module.
- **SOFT:** Docker postgres/redis down → `docker compose up -d db redis`.
- **SOFT:** Langfuse down (env) — unrelated, continue without it.

---

## SESSION VEGEN

```
/session-close S91
```

S92 = retro for Sprint H + merge PR for v1.4.4 (once coverage gate + any stale follow-ups are resolved).

---

*Sprint H session: S91 = v1.4.4.4 (Consolidation Day 4 — coverage uplift, punted from S90). Sprint H total projected: 5 sessions.*
