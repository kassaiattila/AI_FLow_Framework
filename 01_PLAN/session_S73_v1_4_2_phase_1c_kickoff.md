# AIFlow Phase 1c — Sprint Plan (v1.4.2: Association Backfill + Observability Harden + CI Hygiene)

> **Status:** **KICKOFF** 2026-05-11 in S73 / F0.1 (THIS session).
> **Datum (planned start):** 2026-05-11 (Monday after Phase 1b merge).
> **Branch:** `feature/v1.4.2-phase-1c-association-backfill` (created from `main` at tag `v1.4.1-phase-1b`).
> **Phase 1b close:** commit `b4b1aae` on `main` (squash-merged PR #4, tag `v1.4.1-phase-1b`, 2026-05-08).
> **Plan sources:** `out/phase_1b_architect_review.md` §Conditions C3-C5, GitHub issues #3 + #5, `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md`.
> **Predecessor:** S72 / E3.6 — Phase 1b merge + tag push.

---

## KONTEXTUS

### Phase 1b (v1.4.1) — CLOSED

- Source Adapters merged to `main` 2026-05-08 (squash commit `b4b1aae`, tag `v1.4.1-phase-1b`, PR #4).
- 5 adapters (Email / File / Folder / Batch / API) + N4 associator + `POST /api/v1/intake/upload-package` + Alembic 034 (source_type) + 035 (association_mode nullable).
- Test deltas: +198 unit, +11 integration, +35 Phase 1b E2E (2144 tests GREEN against live Postgres in merge-gate validation).
- Architect verdict: **GO WITH CONDITIONS** (C1+C2 closed at merge; C3-C5 filed as Phase 1c follow-ups: issues #3, #5).

### Phase 1c (v1.4.2) — THIS SPRINT

Phase 1c closes the three non-blocking Phase 1b conditions plus CI hygiene that has been red since pre-Phase-1b. The sprint is scoped as **small, independent, low-risk deliverables** (no new user-facing surface, no new services, no new skill API changes). Each deliverable ships behind a dedicated session with its own PR so that main stays green throughout.

1. **CI hygiene first** (issue #5) — pin `python-multipart`, triage ≥10 pre-existing mypy errors. Unblocks CI-green signal for all subsequent Phase 1c PRs.
2. **OpenAPI regen + CI diff gate** (issue #3 / C3) — refresh `docs/api/openapi.{yaml,json}` for `upload-package` + `sources/webhook`, add a CI job that fails on future drift.
3. **Observability canonical event names** (C4) — introduce `aiflow.sources.observability.emit_package_event` helper emitting canonical `source.package_received` / `source.package_rejected` with `package_id` + `tenant_id` + `source_type`; rewire all 5 adapters; per-adapter unit test asserting canonical shape.
4. **Association-mode backfill** (C5) — Alembic 036 backfill pre-Phase-1b rows via heuristic (`single_description` when exactly 1 description, `order` when N files + N descriptions, `NULL` otherwise); Alembic 037 tighten to `NOT NULL` once every writer path verified.

---

## SPRINT OVERVIEW

```
Phase 1c (v1.4.2) — 4-5 sessions / 3-4 working days / 4 deliverables + acceptance gate
  Week 0 Day 0       : Sprint kickoff (THIS session — F0.1)
  Week 1 Day 1       : CI hygiene (issue #5)                         — F0.2 / S74
  Week 1 Day 2       : OpenAPI regen + CI diff gate (issue #3 / C3)  — F0.3 / S75
  Week 1 Day 3       : Observability canonical events (C4)           — F0.4 / S76
  Week 1 Day 4       : Association-mode backfill (C5a: Alembic 036)  — F0.5 / S77
  Week 1 Day 5       : NOT NULL tightening + gate + PR (C5b: Alembic 037) — F0.6 / S78
```

---

## WEEK 0 — Kickoff (Day 0, session F0.1 — THIS session)

**Goal:** lay the Phase 1c governance scaffolding — plan doc, branch, CLAUDE.md refresh — so Day 1 can start on CI hygiene without rework.

- [x] Create `feature/v1.4.2-phase-1c-association-backfill` from `main` (post Phase 1b merge).
- [x] Write this plan document.
- [x] Update `CLAUDE.md` (3 sites: overview header, git workflow branch pointer, current plan reference).
- [x] Verify preconditions: `ruff check` clean, alembic head = 035, issues #3 + #5 visible with `phase-1c` label.

**Day 0 exit:** branch pushed to origin, plan doc + CLAUDE.md committed, `ruff check src/ tests/` still `All checks passed!`, `pytest --collect-only` unchanged.

---

## WEEK 1 — Execution

### Day 1 — CI hygiene (F0.2 / S74)

**Issue:** #5.

- Add `python-multipart>=0.0.9` to `pyproject.toml` `[project.dependencies]` (alongside `fastapi>=0.115`).
- Run `uv sync` + `uv lock --check`; confirm `tests/unit/api/test_verification_api.py` collects + passes.
- Triage the ≥10 pre-existing mypy errors (fix where trivial, justify + suppress where unavoidable):
  - `src/aiflow/core/errors.py:34,103` — `Missing type arguments for generic type "dict"`
  - `src/aiflow/guardrails/base.py:55,67` — same
  - `src/aiflow/intake/state_machine.py:193` — `dict[Enum, set[Enum]]` variance
  - `src/aiflow/policy/__init__.py:97` — unused `# type: ignore`
  - `skills/process_documentation/drawio/bpmn.py:379,424` — `dict` generic arg
  - `skills/process_documentation/models/__init__.py:65` — `dict` generic arg
- Confirm CI-green on `main` via an open draft PR (`Framework CI` + `Python Lint + Test` all green).

**Day 1 exit:** `unit-tests`, `lint`, `Python Lint + Test` all green locally + in CI preview. PR merged → `main` CI green.

### Day 2 — OpenAPI regen + CI diff gate (F0.3 / S75)

**Issue:** #3. **Architect condition:** C3.

- Run `python scripts/export_openapi.py` against a live FastAPI app; commit `docs/api/openapi.yaml` + `docs/api/openapi.json` regen.
- Verify both `POST /api/v1/intake/upload-package` and `POST /api/v1/sources/webhook` appear in the regenerated schema.
- Add a CI job (`.github/workflows/openapi-drift.yml`) that:
  1. boots the FastAPI app (testcontainers or direct `uvicorn` spawn),
  2. dumps `/openapi.json` to a temp file,
  3. diffs it against the checked-in `docs/api/openapi.json` (normalize non-stable fields: `description`, `summary` rewrites when unchanged semantically),
  4. fails the build on drift.
- Prove the drift gate triggers: temporarily flip a route summary, confirm the CI job fails, revert.
- Add a one-liner to `docs/api/README.md` (or create it) documenting the regen workflow: `python scripts/export_openapi.py`.

**Day 2 exit:** `docs/api/openapi.yaml` + `docs/api/openapi.json` contain both new endpoints; drift job green on PR, red on induced drift.

### Day 3 — Observability canonical event names (F0.4 / S76)

**Architect condition:** C4.

- New module `src/aiflow/sources/observability.py` exposing a single helper:
  ```python
  def emit_package_event(
      event: Literal["source.package_received", "source.package_rejected"],
      package: IntakePackage,
      source_type: str,
      **extra: Any,
  ) -> None:
      logger.info(
          event,
          package_id=str(package.package_id),
          tenant_id=package.tenant_id,
          source_type=source_type,
          **extra,
      )
  ```
- Rewire all 5 adapters to call the helper at enqueue / acknowledge / reject transitions:
  - `file_adapter.py:198,206` (acknowledged / rejected)
  - `folder_adapter.py:255,263`
  - `batch_adapter.py:510,518`
  - `api_adapter.py:274,282`
  - `email_adapter.py:377,391`
- Keep the existing per-adapter-specific event names (e.g. `file_adapter_acknowledged`) as **secondary** events for backward-compatibility with any ad-hoc log tailing; primary event is the canonical name. Document this in the module docstring.
- Per-adapter unit test asserting the canonical event emission shape (`event` name, `tenant_id`, `package_id`, `source_type` all present; no PII — e.g. no `password`, `hmac_secret`).
- One cross-adapter parametrized test: `test_all_source_adapters_emit_canonical_events` (ABC-style assertion over the registry).

**Day 3 exit:** `grep -rE 'source\.package_(received|rejected)' src/aiflow/sources/ | wc -l` returns ≥ 10 (5 adapters × 2 events each at minimum). Unit tests GREEN. No drift of non-canonical names introduced.

### Day 4 — Association-mode backfill (F0.5 / S77)

**Architect condition:** C5 (part a).

- Alembic migration `036_association_mode_backfill.py`:
  - **Upgrade:** for each `intake_packages` row where `association_mode IS NULL`:
    - If `description_count` == 0 → leave NULL (valid: package with no descriptions).
    - If `description_count` == 1 → set `single_description`.
    - If `description_count` == `file_count` AND both > 0 → set `order`.
    - Otherwise → leave NULL and emit a structured WARNING log line for ops review (no data loss).
  - **Downgrade:** no-op (backfill is data; no schema change to reverse). Document this in the migration docstring.
- **Safety:** purely data-mutating migration; read-then-write under advisory lock to prevent racing with live ingestion. Chunked batch of 1000 rows to avoid long-running single transaction on large tables.
- Unit test (migration integration test against fresh Postgres):
  - Seed 4 representative packages (0 desc, 1 desc, N/N, N/M mismatch).
  - Run upgrade.
  - Assert backfilled modes match expected.
  - Run downgrade → assert data unchanged (no-op).
- Count the rows affected in a one-shot SQL query run against the dev DB (document in PR description).
- **No NOT NULL yet** — that is Day 5.

**Day 4 exit:** migration 036 head; chunked backfill tested against live Postgres with representative seed data; ops warning log surfaced for the ambiguous `N/M` case.

**STOP feltetel:** if ambiguous `N/M mismatch` rows are > 5% of production volume, escalate to user before deciding whether to extend heuristics or leave NULL permanently.

### Day 5 — NOT NULL tightening + acceptance gate + PR (F0.6 / S78)

**Architect condition:** C5 (part b). **Phase 1c acceptance gate.**

- **Pre-flight audit:** grep all writer paths in `src/aiflow/` to confirm every INSERT of `intake_packages` now sets `association_mode` (either enum value or explicit `None` when genuinely inapplicable). Required paths:
  - `src/aiflow/api/v1/intake.py:438-463` (upload-package router)
  - `src/aiflow/sources/batch_adapter.py:491`
  - `src/aiflow/state/repositories/intake.py:insert_package` (all call-sites)
  - 4 remaining adapters (email / file / folder / api) — produce packages with zero descriptions → `None`.
- Alembic migration `037_association_mode_check_constraint.py`:
  - **Upgrade:** add `CHECK (description_count = 0 OR association_mode IS NOT NULL)` (conditional NOT NULL — only enforces when descriptions exist). This is stricter than unconditional NOT NULL because packages with zero descriptions genuinely have no mode.
  - **Downgrade:** drop the CHECK constraint.
- Validate with a negative test: insert a package with `description_count > 0` and `association_mode IS NULL` → expect constraint violation.
- Acceptance gate walkthrough (see checklist below), run `/regression` + `/lint-check` + `/smoke-test`.
- Draft `docs/phase_1c_acceptance_report.md` + `docs/phase_1c_pr_description.md`.
- Refresh CLAUDE.md key numbers (Alembic migration count 35 → 37, add Phase 1c to progress table).
- Open PR `v1.4.2 Phase 1c — Association Backfill + Observability Harden + CI Hygiene`.

**Day 5 exit:** all Phase 1c gates PASS, PR opened, `v1.4.2-phase-1c` tag ready to push on merge.

---

## PHASE 1c ACCEPTANCE GATE CHECKLIST

Analog to Phase 1b gates G1-G9. Each item MUST be checked before merge to `main`.

- [ ] **G1 — CI hygiene:** `python-multipart>=0.0.9` pinned; `Framework CI` + `Python Lint + Test` green on `main` and on the Phase 1c PR. Mypy errors triaged to 0 new + ≤ 0 legacy (or explicitly suppressed with reason).
- [ ] **G2 — OpenAPI regen:** `docs/api/openapi.{yaml,json}` regenerated; both new endpoints (`upload-package`, `sources/webhook`) present; drift CI job green.
- [ ] **G3 — OpenAPI drift gate:** induced drift triggers CI failure (tested once in the PR body).
- [ ] **G4 — Canonical events:** All 5 adapters emit `source.package_received` + `source.package_rejected` via `emit_package_event` helper, with `package_id` + `tenant_id` + `source_type` keys.
- [ ] **G5 — No PII leak:** canonical events unit-test asserts no `password`, `hmac_secret`, raw `signature`, or email body content leaks into log fields.
- [ ] **G6 — Backfill correctness:** Alembic 036 backfill heuristic applied; no row with `description_count > 0` left with NULL `association_mode` unless explicitly flagged in ops warnings.
- [ ] **G7 — NOT NULL constraint:** Alembic 037 CHECK constraint enforced; negative test proves rejection of invalid INSERT.
- [ ] **G8 — Backward compat:** 199 Phase 1a E2E + 35 Phase 1b E2E regression run — same exact-count subprocess gate as Phase 1b — PASS.
- [ ] **G9 — Test counts:** unit tests ≥ +15 (5 adapters × observability + 4 migration tests + edge-case CHECK tests), E2E count unchanged (no new user-facing surface), ruff 0 error.

---

## ALEMBIC MIGRACIO — Overview

| Revision | Purpose                                         | Reversible? | Data change? |
|----------|-------------------------------------------------|-------------|--------------|
| 036      | Backfill `association_mode` via heuristic       | downgrade = no-op | YES (data) |
| 037      | CHECK `description_count = 0 OR association_mode IS NOT NULL` | YES (drop constraint) | NO (schema) |

Both migrations are chunked, idempotent, and safe for zero-downtime deployment per `aiflow-database` skill rules. No index changes. No column type changes. No renames.

---

## RISK REGISTER

| Risk | Mitigation | Residual |
|------|------------|----------|
| Backfill heuristic ambiguous on `N/M mismatch` rows | Leave NULL + emit ops warning log; escalate at STOP feltetel > 5% | LOW (safe default) |
| `python-multipart` pin breaks downstream deps | Run `uv lock --check` + full unit-test suite pre-PR | LOW |
| mypy fix introduces runtime type drift | Only fix type-annotations, never runtime behavior; unit tests catch regressions | LOW |
| OpenAPI drift gate too strict (false-positive on cosmetic wording) | Normalize `description`/`summary` fields in the diff; document the normalization in `docs/api/README.md` | MEDIUM (iterate) |
| Observability rewire breaks existing log consumers | Keep old per-adapter event names as secondary emissions; document deprecation timeline in module docstring | LOW |
| CHECK constraint 037 fires on concurrent writes during migration | Backfill 036 is chunked with advisory lock; 037 is add-constraint only (single scan, acceptable on tables < 10M rows) | LOW |

---

## ROLLBACK PLAN

Per migration:

- **036** — downgrade is no-op; to reverse data effect, run `UPDATE intake_packages SET association_mode = NULL` against the dev DB (production rollback would need ops intervention — document this in the 036 docstring).
- **037** — downgrade drops CHECK constraint cleanly.

Per PR:

- If any gate fails post-merge, `git revert` the squash commit and roll back `v1.4.2-phase-1c` tag. Phase 1b state is immediately restored (no irreversible data change in 037; 036 backfill data remains but is semantically harmless).

---

## STOP FELTETELEK

ALLJ MEG es kerj iranymutatast, ha:

- **HARD:** backfill heuristic ambiguous on > 5% of prod rows → escalate to user before choosing extension strategy.
- **HARD:** a writer path is discovered mid-sprint that does NOT set `association_mode` even when descriptions are present → revisit 037 design.
- **HARD:** OpenAPI drift gate produces > 5 false positives on unrelated PRs → revisit normalization strategy.
- **SOFT:** issue #5 mypy triage surface-area expands beyond the listed ≥10 errors (e.g. legacy files cascade into new errors) → split into dedicated session.
- **SOFT:** Observability rewire breaks an ad-hoc log consumer → decide whether to keep both event names permanently or deprecate with a timeline.

---

## REFERENCIAK

- `out/phase_1b_architect_review.md` — Conditions C3, C4, C5 with full rationale.
- `out/phase_1b_acceptance_report.md` — §5.1 (G5 remediation), §5.2 (G8 remediation).
- GitHub issue #3 — OpenAPI regen + drift gate.
- GitHub issue #5 — CI hygiene (`python-multipart` + mypy triage).
- `01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md` — Phase 1b plan (reference for sprint shape).
- `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` Section 4 — Phase ordering.
- `src/aiflow/intake/package.py:195-199` — `association_mode: AssociationMode | None` field.
- `alembic/versions/035_association_mode.py` — predecessor migration.
- `scripts/export_openapi.py` — OpenAPI regen entry point.
- `.claude/skills/aiflow-database.md` — zero-downtime migration rules.
- `.claude/skills/aiflow-observability.md` — structlog conventions.

---

## SESSION CHAINING

```
S73 / F0.1 (THIS) — kickoff + plan + branch + CLAUDE.md refresh
S74 / F0.2        — Day 1: CI hygiene (issue #5)
S75 / F0.3        — Day 2: OpenAPI regen + CI diff gate (issue #3 / C3)
S76 / F0.4        — Day 3: Observability canonical events (C4)
S77 / F0.5        — Day 4: Association-mode backfill (C5a, Alembic 036)
S78 / F0.6        — Day 5: NOT NULL tightening + acceptance gate + PR (C5b, Alembic 037)
```

At end of each session: `/session-close <id>` generates `session_prompts/NEXT.md` for the next Day N.

---

*Phase 1c session: S73 = F0.1 (Association backfill + observability + CI hygiene kickoff — finalized plan).*
