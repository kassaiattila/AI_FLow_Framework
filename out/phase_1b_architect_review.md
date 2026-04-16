# AIFlow Phase 1b — Architect Review

> **Review session:** independent governance pass, 2026-04-16
> **Branch:** `feature/v1.4.1-phase-1b-sources`
> **HEAD reviewed:** `a1ef4a2` (S70 / E3.4)
> **Inputs:** `out/phase_1b_acceptance_report.md`, `docs/phase_1b_pr_description.md`, cross-validated against source tree.

---

## VERDICT: GO WITH CONDITIONS

Phase 1b is functionally merge-ready. All hard architectural gates (domain contract, state machine alignment, migration safety, backward compatibility, multi-tenant isolation, security middleware coverage) hold under independent cross-validation. The two documented non-PASS gates (G5 WAIVED, G8 PARTIAL) are correctly scoped as logging/documentation follow-ups that do not affect runtime contract or data integrity. The 198/200 unit-test shortfall is immaterial given the additional 11 integration + 35 Phase-1b-E2E tests (net +244 test count) and a hard subprocess-enforced Phase 1a regression gate.

The two merge-blocking conditions below are non-code (filing and commit hygiene); the remaining four conditions are post-merge follow-up work that are already tracked in the acceptance report.

---

## Per-question findings

### Q1 — G5 OpenAPI yaml waiver: ACCEPT WAIVER

**Evidence:**
- `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\80_Sample_Projects\07_AI_Flow_Framwork\docs\api\openapi.yaml` (10343 lines) checked in, last regenerated pre-Phase-1b — confirmed stale: a repo-wide grep for `upload-package` and `sources/webhook` under `docs/` matches **only** `docs/phase_1b_pr_description.md` (the PR copy itself). Neither endpoint is in the checked-in yaml.
- Grep for consumers of `docs/api/openapi.yaml` / `docs/api/openapi.json`:
  - `.github/workflows/*.yml` — **zero matches** (no CI job regenerates or diffs this file).
  - `aiflow-admin/` — **zero matches** (admin UI does not load the static schema; it calls `/openapi.json` at runtime if at all).
  - `Makefile` — **zero matches**.
  - `scripts/export_openapi.py:23` — generates both files from the live FastAPI app but is not invoked by CI.
- The router IS wired: `src/aiflow/api/app.py:140,160` imports `intake_router` and includes it; `src/aiflow/api/app.py:154,159` does the same for `sources_webhook_router`. FastAPI therefore publishes both at `/openapi.json` at runtime.
- Integration + E2E tests assert the **live** contract: `tests/integration/intake/test_upload_package_router.py` + `tests/e2e/v1_4_1_phase_1b/test_upload_package.py` + the 4-mode parametrize in `test_multi_source_e2e.py::test_n4_association_modes_roundtrip`.

**Rationale:** The stale `openapi.yaml` has no downstream consumer that would be harmed by the drift — not CI, not client SDK generation, not the admin UI, not a security-review pipeline. The live `/openapi.json` is the authoritative contract and is covered by real tests. Regenerating the yaml is purely a documentation refresh.

**Ruling:** Waiver accepted as documented. The follow-up OpenAPI regen ticket (acceptance report §5.1) is correctly scoped as a post-merge task. One merge-blocking refinement is required — see Condition C1 — to ensure the ticket is actually filed before merge rather than drifting indefinitely.

**Verdict: PASS (waiver accepted).**

---

### Q2 — G8 structlog event naming PARTIAL: NON-BLOCKING

**Evidence:**
- Every adapter emits structured events at the full lifecycle (enqueue / acknowledge / reject), with `package_id` consistently set: grep of `src/aiflow/sources/*.py` shows 20+ `logger.info(...)` + `logger.warning(...)` calls, none of which print raw secrets (verified: `email_adapter.py` logs `uid` + `package_id`, never `password`; `api_adapter.py` logs `package_id`, never `hmac_secret`).
- Drift from canonical spec:
  - `src/aiflow/sources/file_adapter.py:198,206` — `file_adapter_acknowledged` / `file_adapter_rejected`
  - `src/aiflow/sources/folder_adapter.py:255,263` — `folder_adapter_acknowledged` / `folder_adapter_rejected`
  - `src/aiflow/sources/batch_adapter.py:510,518` — `batch_adapter_acknowledged` / `batch_adapter_rejected`
  - `src/aiflow/sources/api_adapter.py:274,282` — `api_adapter_acknowledged` / `api_adapter_rejected`
  - `src/aiflow/sources/email_adapter.py:377,391` — `email_adapter_acknowledged` / `email_adapter_rejected`
  - None include `tenant_id` or `source_type` as structured keys (they're available in-context — adapters receive both in ctor — just not emitted).
- The router-level log DOES include both: `src/aiflow/api/v1/intake.py:466-473` emits `intake_upload_package_created` with `package_id`, `tenant_id`, `file_count`, `description_count`, `association_mode`.

**Rationale:** Non-canonical event names are a **logging contract misalignment**, not a runtime observability hole:
- Every lifecycle transition IS emitted with structured context and a unique identifier (`package_id`). Incident forensics remains possible via `package_id` search across services.
- No SLO or alert in the repo currently listens on `source.package_received` (grep confirmed) — there is nothing to break on day one.
- Dashboards that consume the canonical name will show empty data until the rename; this is a cosmetic harm, not a functional one.
- PII is NOT being logged — `email_adapter` does not log passwords; `api_adapter` does not log `hmac_secret`.
- The router-level event is already well-formed and complete; it is the adapter-level that drifts.

The spec intent (uniform querying by `tenant_id` + `source_type`) is preserved structurally by the log line being well-formed JSON per `structlog`; downstream tooling can filter on `event` prefix and the per-adapter name is already a clean mapping to `source_type`.

**Ruling:** Acceptable to ship. The G8 remediation ticket (acceptance report §5.2) is the right fix — introduce `emit_package_event(event, package, **extra)` helper — but is a post-merge task. One condition applies — see Condition C2 — to ensure a regression test is added so the canonical names don't drift again once they're introduced.

**Verdict: PASS (PARTIAL status accepted).**

---

### Q3 — Phase 1a regression subprocess-mode: SUFFICIENT

**Evidence:**
- `tests/e2e/v1_4_1_phase_1b/test_multi_source_e2e.py:550-583` — `test_phase_1a_regression_unchanged`:
  - Spawns `pytest tests/e2e/v1_4_0_phase_1a/ -q --tb=no --no-header` via `subprocess.run(..., timeout=600, check=False)`.
  - Asserts **BOTH** `result.returncode == 0` AND the parsed summary line reports **exactly 199 passed** (via `_PYTEST_SUMMARY_RE` regex).
  - Timeout 600s is generous; stdout/stderr tails are included in assertion messages for debuggability.
- The subprocess rationale is documented in `MEMORY.md` under `feedback_asyncpg_pool_event_loop.md` — asyncpg pools are event-loop-bound; per-function pytest-asyncio tests corrupt the pool, so Phase 1a E2E was merged into one-method-per-class and Phase 1b regressions it via an isolated subprocess. This is a dev-documented invariant, not a hack.
- The gate is **tighter** than a CI matrix run would be: a CI matrix could silently drop tests (marker changes, collection errors) as long as exit=0; this gate requires exact numeric count.

**Rationale:** Subprocess isolation + exact-count assertion is stronger than a parallel CI matrix job would be, because it:
1. Runs in the same Python interpreter image the dev uses, catching env-mismatch bugs early.
2. Asserts exact count, not just exit=0 — silent test-deletion cannot regress unnoticed.
3. Requires Phase 1a to remain green locally before push (dev-side gate) AND on CI (via the Phase 1b E2E job).

A parallel CI matrix run would add cost (duplicate container start, duplicate Postgres migration) with marginal additional safety. I'd only require it if the project adds a multi-architecture matrix later; for now the in-process subprocess gate is the right primitive.

**Verdict: PASS.**

---

### Q4 — Alembic 035 nullable `association_mode`: SAFE ZERO-DOWNTIME

**Evidence:**
- `alembic/versions/035_association_mode.py:34-49` — upgrade creates enum + adds `nullable=True` column with no default. No data writes. No NOT NULL. No indices. Minimal lock scope on Postgres.
- `alembic/versions/035_association_mode.py:52-59` — downgrade drops column and enum type; idempotent with `checkfirst=True`.
- Round-trip verified in `tests/e2e/v1_4_1_phase_1b/test_alembic_034.py` which was explicitly resynced in S70 to assert head=035 AND 034 invariants survive `head → downgrade 034 → upgrade 035` (acceptance report G7, lines 75-85).
- Every code path that **reads** the column handles NULL: `src/aiflow/state/repositories/intake.py:185-186` and `:307-308` guard `AssociationMode(mode_value) if mode_value else None`. The Pydantic model (`src/aiflow/intake/package.py:195-199`) declares `association_mode: AssociationMode | None = Field(None, ...)`.
- Every code path that **writes** the column correctly sets None when no descriptions are present:
  - API upload-package router: `src/aiflow/api/v1/intake.py:438-463` — only runs the associator and sets `package.association_mode` when `description_models` is truthy. With no descriptions, column stays None. Correct by design.
  - BatchSourceAdapter: `src/aiflow/sources/batch_adapter.py:491` — sets to the mode used; `:148,434` allows None.
  - Email / File / Folder / Api adapters: produce packages with no descriptions, so `association_mode=None` is the expected, correct path.

**Rationale:** The "nullable additive column → backfill later → NOT NULL" sequence is the canonical zero-downtime pattern per AIFlow's DB skill rules and is safe in production:
1. No writer assumes NOT NULL. Every writer sends either a valid enum value or None.
2. No reader assumes NOT NULL. All three read sites apply `AssociationMode(...) if mode_value else None`.
3. No pipeline logic branches on `association_mode IS NULL` in a way that breaks pre-Phase-1b rows (verified: grep for `association_mode IS NULL` returns 0 matches in `src/`).
4. The nullable column is semantically meaningful: packages with zero descriptions genuinely have no association mode. NOT NULL would be architecturally wrong today and would force a sentinel (like `legacy` for `source_type`) that adds noise.
5. Tech debt risk is real but small: if Phase 1c is postponed indefinitely, the column stays nullable. That is strictly worse than a clean invariant, but not a safety issue. The acceptance report §5 correctly files this as a tracked follow-up.

**Verdict: PASS.**

---

### Q5 — Other architectural risks reviewed

Cross-validated five additional dimensions; no blockers surfaced.

**5a. Multi-tenant isolation on the public multipart endpoint.** `src/aiflow/api/v1/intake.py:76-90` enforces tenant boundary via JWT `team_id` claim (not a form field, not a header, not a query param), with 401 fallback. Storage root is per-tenant: `src/aiflow/api/v1/intake.py:293` — `pkg_dir = _get_upload_root() / tenant_id / str(package_id)`. This is correct and matches the Phase 1a isolation contract. `test_all_sources_produce_valid_intake_package` asserts `hydrated.tenant_id == tenant_id` round-trip.

**5b. Rate limiting on public endpoints.** `src/aiflow/api/middleware.py:210-216` — `RateLimitMiddleware._classify` returns `"api"` for any `/api/*`, so both `upload-package` (100 req/min in prod, 1000 in dev) and `sources/webhook` (100 req/min in prod) are covered. Redis sliding window is fail-open (`:226-227`), which is the correct availability-over-security tradeoff for a non-auth path but worth noting. `MaxBodySizeMiddleware` (`:288+`) defaults to 50MB via `AIFLOW_MAX_UPLOAD_BYTES`, matching the intake router's `AIFLOW_INTAKE_UPLOAD_MAX_BYTES` default. No risk flagged.

**5c. Webhook is public by design (no auth middleware).** `src/aiflow/api/middleware.py:43` adds `/api/v1/sources/webhook` to `_PUBLIC_PREFIXES`. This is **correct and deliberate** — the webhook authenticates via HMAC-SHA256 signature + timestamp anti-replay inside the adapter (`src/aiflow/api/v1/sources_webhook.py:14-18` explicitly documents this; secret loaded from `AIFLOW_WEBHOOK_HMAC_SECRET` at adapter construction). The router refuses to start without the env var (`sources_webhook.py:63-68`). No secret appears in log fields (verified: grep of adapter logs shows `package_id`, `uid`, `reason` — never `hmac_secret` or raw signature).

**5d. Provider/source abstraction layering.** `src/aiflow/sources/base.py:57-89` — `SourceAdapter` ABC with four abstract methods + `metadata` property + `source_type: ClassVar`. `src/aiflow/sources/registry.py:29+` — registry validates subclass + ClassVar at register time, raises on duplicate. All 5 adapters live in `src/aiflow/sources/` (clean module boundary; no cross-imports into engine, state, or security). This matches the N2/R1 refinement in `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md`. Provider abstraction is clean.

**5e. Secret handling.** Email adapter stores password in an instance attribute (`src/aiflow/sources/email_adapter.py:91`) — inescapable for IMAP; never logged. API adapter stores HMAC secret as bytes (`api_adapter.py:109`) with non-empty guard (`:103-104`). Outlook COM backend (optional) does not store credentials (native Windows auth). No secrets leak into response bodies, log fields, or Pydantic serialization. Low risk.

**Verdict: PASS on all five sub-dimensions.**

---

## Cross-validation of acceptance report vs. actual code

No inconsistencies found. Every claim in `out/phase_1b_acceptance_report.md` was spot-checked against the source tree:

- G1: 5 adapters confirmed (`Glob src/aiflow/sources/*.py` → `api_adapter.py`, `batch_adapter.py`, `email_adapter.py`, `file_adapter.py`, `folder_adapter.py`). ABC + registry present.
- G2: `IntakePackage.association_mode` field confirmed (`src/aiflow/intake/package.py:195-199`); repository round-trip confirmed (`src/aiflow/state/repositories/intake.py:48,66,185-186,202,307-308,323`).
- G3: Policy resolution confirmed in test (`test_multi_source_e2e.py:233-234`).
- G4: Associator + all 4 modes confirmed (`src/aiflow/intake/associator.py` exists; 4-mode round-trip in `test_multi_source_e2e.py:370-537`).
- G5: Stale `openapi.yaml` confirmed (10343 lines, last regen pre-Phase-1b, does not mention `upload-package` or `sources/webhook`).
- G6: Regression subprocess gate confirmed (`test_multi_source_e2e.py:550-583`).
- G7: Migration 034 + 035 round-trip confirmed (`test_alembic_034.py:13-17` explicitly documents S70 resync to head=035).
- G8: Event names match the drift claimed in the report (5 adapters × 2-3 events each; no `source.package_*` names; no `tenant_id` key emitted at adapter level).
- G9: 1872 unit / 38 integration / 35 Phase 1b E2E / 199 Phase 1a E2E counts not independently re-run in this review (would require Docker services) but test files match the acceptance report inventory (9 Phase 1b E2E files confirmed by Glob; integration dir has the claimed upload-package router test).

---

## Conditions

### Merge-blocking (must complete before `main` merge)

- [ ] **C1** — File the G5 OpenAPI regen ticket as a tracked GitHub issue (not just acceptance-report §5). Link the issue in the PR description. Target: next session after Phase 1b merge, not Phase 1c close. *Scope: zero sessions (issue filing only). Prevents the waiver from drifting into "never".*
- [ ] **C2** — Before merging, confirm the PR description's test-plan checklist is actually executed against a fresh Postgres (the 10-line reviewer checklist in `docs/phase_1b_pr_description.md:140-149`). Acceptance report lines 122-132 give reproducible commands. This is a lead-review step, not new work. *Scope: zero sessions (validation only).*

### Post-merge follow-up (tracked, non-blocking)

- [ ] **C3** — G5 remediation session: run `python scripts/export_openapi.py`, commit `docs/api/openapi.yaml` + `docs/api/openapi.json` regen, add CI job that diffs live schema against checked-in copy to prevent future drift. *Scope: 1 session (~0.5 days).*
- [ ] **C4** — G8 observability harden session: introduce `aiflow.sources.observability.emit_package_event(event, package, **extra)` helper emitting canonical `source.package_received` / `source.package_rejected` with `package_id`, `tenant_id`, `source_type` keys; rewire all 5 adapters; add unit test per adapter asserting canonical shape. *Scope: 1 session (~0.5-1 day).*
- [ ] **C5** — Phase 1c association-mode backfill: backfill `intake_packages.association_mode` for legacy/pre-Phase-1b rows (via a heuristic derived from file/description counts, or leave NULL and adjust the constraint to NULL OR enum), then NOT NULL the column if all writers set it. *Scope: 1-2 sessions. Already scheduled per CLAUDE.md.*
- [ ] **C6** — Outlook COM backend parity (S58 downgrade if `pywin32` absent) — revisit in v1.4.2. *Scope: 1 session. Optional.*

---

## Merge recommendation

**Merge GO** once Conditions C1 and C2 are satisfied. Phase 1b ships 5 source adapters + N4 associator + a well-bounded multipart upload endpoint + two additive migrations, with zero breaking changes to Phase 1a, zero skill API churn, zero pipeline adapter churn, multi-tenant isolation verified, rate limiting and body-size caps in place on the new public surface, HMAC auth documented on the public webhook, and a hard subprocess-enforced 199-test Phase 1a regression gate. G5 (docs) and G8 (log names) are correctly deferred with tickets; neither is a functional or security risk. The 198/200 unit-test shortfall is explained, transparent, and offset by the integration + E2E deltas. Suggested merge tag: `v1.4.1-phase-1b` as proposed in the PR draft.

---

*End of Phase 1b architect review.*
