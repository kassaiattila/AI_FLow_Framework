# AIFlow Phase 1b — Session 55 Kickoff Prompt (S55 / E0.1: Source Adapters)

> **Status:** DRAFT skeleton (generated in S54). Flesh out in the sprint-planning session that follows Phase 1a merge + architect sign-off.
> **Datum (planned):** 2026-04-21 (Monday after Phase 1a merge)
> **Branch:** `feature/v1.4.1-phase-1b-sources` (create from `main` only after Phase 1a merges)
> **Previous:** S54 / D0.11 — Phase 1a demo + PR draft (HEAD `8457eff` + D0.11 docs commit)
> **Plan:** `01_PLAN/106_*` + `01_PLAN/101_*` (N2 email, R1 file, N4 association)
> **Session type:** SPRINT KICKOFF — Phase 1b (v1.4.1, ~3 weeks, 5 source adapters + upload-package endpoint)

---

## KONTEXTUS

### Phase 1a (v1.4.0) — CLOSED

- Foundation layer merged to `main`, tag `v1.4.0-phase-1a`
- IntakePackage + PolicyEngine + ProviderRegistry + SkillInstance.policy_override + backward compat shim
- 199 Phase 1a E2E tests, 1674 unit tests

### Phase 1b (v1.4.1) — THIS SPRINT

Source adapters take raw inputs (email, file, folder, batch, webhook) and produce `IntakePackage` objects ready for the policy/provider pipeline built in Phase 1a.

---

## SPRINT OVERVIEW

```
Phase 1b (v1.4.1): Source Adapters + N4 Association + upload-package endpoint
  Week 1: EmailSourceAdapter + FileSourceAdapter
  Week 2: FolderSourceAdapter + BatchSourceAdapter + ApiSourceAdapter
  Week 3: N4 File<->Description association (4 modes) + upload-package endpoint + E2E
```

---

## WEEK 1 — Email + File source adapters

### E1.1 — EmailSourceAdapter (Outlook COM + IMAP)

- `src/aiflow/sources/email_adapter.py` — ABC `SourceAdapter` + `EmailSourceAdapter` impl
- Two backends: Outlook COM (Windows only, via pywin32) + IMAP (cross-platform)
- Produces `IntakePackage` from email metadata + attachments
- Alembic: extend `intake_packages` with `source_type` (`email` | `file` | ...) — already nullable from Phase 1a
- Unit tests: >=20 (backend abstraction, MIME parsing, attachment extraction)

### E1.2 — FileSourceAdapter

- `src/aiflow/sources/file_adapter.py` — single-file upload entry point
- Produces `IntakePackage` with exactly 1 `IntakeFile`
- Routes via existing PolicyEngine for parser/classifier selection
- Unit tests: >=15

**Week 1 exit:** 2 adapters + ~35 unit tests + 1 E2E test per adapter

---

## WEEK 2 — Folder + Batch + API adapters

### E2.1 — FolderSourceAdapter (watch dir)

- `src/aiflow/sources/folder_adapter.py` — filesystem watch (watchdog lib)
- Emits `IntakePackage` per new file appearing in configured directory
- Graceful handling of mid-write detection, file locking

### E2.2 — BatchSourceAdapter (ZIP/tarball)

- `src/aiflow/sources/batch_adapter.py` — unpack archive → 1 package with N files
- Max-size guardrail (configurable, default 500 MB)
- Shared extraction tmp dir under per-tenant storage prefix

### E2.3 — ApiSourceAdapter (webhook)

- `src/aiflow/sources/api_adapter.py` + FastAPI router `POST /api/v1/sources/webhook`
- Signed payload verification (HMAC or JWT per customer config)
- Returns `intake_package_id` for async tracking

**Week 2 exit:** 5 total adapters, contract tests against shared `SourceAdapter` ABC

---

## WEEK 3 — N4 Association + upload-package endpoint + E2E

### E3.1 — N4 File <-> Description association (4 modes)

- Per `101_*` N4: explicit, filename_match, order, single_description
- Implementation in `src/aiflow/intake/associator.py` + new `association_mode` column on `intake_packages`

### E3.2 — POST /api/v1/intake/upload-package endpoint

- `src/aiflow/api/v1/intake.py` — multipart upload: N files + M descriptions + association_mode
- Returns 201 with `IntakePackage` summary
- Uses `FileSourceAdapter` internally for single files; `BatchSourceAdapter` for multi

### E3.3 — Multi-source E2E acceptance

- `tests/e2e/v1_4_1_phase_1b/` — 1 test per source × 2 paths (success + rejection) = ~10 tests
- End-to-end: source → IntakePackage → PolicyEngine routing → provider selection → extract

**Week 3 exit:** Phase 1b acceptance checklist (to be authored in sprint-planning session)

---

## EXIT CRITERIA (gate to Phase 1c)

- [ ] All 5 source adapters implement the shared `SourceAdapter` ABC (contract tests PASS)
- [ ] `101_*` N2 (email) + R1 (file) + N4 (association) acceptance items checked
- [ ] Multi-source E2E suite PASS
- [ ] `POST /api/v1/intake/upload-package` documented in OpenAPI
- [ ] Backward compat shim unchanged (legacy pipelines still pass 114-test regression suite from Phase 1a)
- [ ] CLAUDE.md key numbers refreshed

---

## STOP FELTETELEK

- Phase 1a PR not yet merged → do NOT start Phase 1b
- Architect sign-off missing → do NOT cut `feature/v1.4.1-phase-1b-sources` branch
- Outlook COM backend blocked by missing pywin32 → downgrade E1.1 to IMAP-only for v1.4.1, revisit in v1.4.2

---

## REFERENCIAK

- `01_PLAN/101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` — N2, R1, N4 full spec
- `01_PLAN/100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` — IntakePackage / IntakeFile / IntakeDescription
- `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` Section 4 — Phase ordering
- `docs/phase_1a_pr_description.md` — Phase 1a close-out
- `docs/phase_1a_acceptance_report.md` — Phase 1a gate walkthrough

---

## SESSION VEGEN

```
/session-close E0.1
```

*Phase 1b session: S55 = E0.1 (Source Adapters kickoff — DRAFT, finalize in planning session)*
