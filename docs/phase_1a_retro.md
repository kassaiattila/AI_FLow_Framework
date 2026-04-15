# Phase 1a — Sprint D Retrospective

> **Sprint:** D (v1.4.0 Phase 1a Foundation)
> **Duration:** 2026-04-10 (S44 / D0.1) → 2026-04-17 (S53 / D0.10) — 8 days, 10 sessions
> **Demo + PR prep:** 2026-04-18 (S54 / D0.11)
> **Outcome:** 30 PASS / 1 PARTIAL / 4 N/A / 2 PENDING / 0 FAIL on the acceptance matrix

---

## Session timeline

| Session | Date       | Deliverable                                          | Commit    |
|---------|------------|------------------------------------------------------|-----------|
| S44 D0.1| 2026-04-10 | IntakePackage contracts + state machines             | `ed7b8ab` |
| S45 D0.2| 2026-04-11 | Alembic 032 intake tables + IntakeRepository         | `e5ae658` |
| S46 D0.3| 2026-04-12 | PolicyEngine + profile A/B                           | `ff622d9` |
| S47 D0.4| 2026-04-13 | ProviderRegistry + 4 ABC + contract tests            | `c2678a5` |
| S48 D0.5| 2026-04-14 | Alembic 033 + PolicyEngine DB integration            | `d11eecd` |
| S49 D0.6| 2026-04-14 | SkillInstance policy_override + triple merge         | `bf8680c` |
| S50 D0.7| 2026-04-15 | Backward compat shim + pipeline auto-upgrade         | `fee3d56` |
| S51 D0.8| 2026-04-16 | Phase 1a E2E acceptance suite (85 tests)             | `0baed5e` |
| S52 D0.9| 2026-04-17 | Backward compat regression suite (+114 → 199 total)  | `f2c0cfc` |
| S53 D0.10| 2026-04-17| Documentation refresh                                | `8457eff` |
| S54 D0.11| 2026-04-18| Acceptance report + PR draft + Phase 1b kickoff      | *this session* |

---

## What went well

### Contract-first cadence

Starting with Pydantic v2 contracts (D0.1) before any persistence or engine code meant every downstream session could rely on stable schemas. Refactoring risk was confined to the first session; sessions D0.2–D0.10 never had to revisit the contract shape.

### E2E-second, regression-bolted-on

Writing the Phase 1a E2E suite (85 tests in D0.8) **before** the regression suite (114 tests in D0.9) surfaced the shim edge cases in a clean context. When regression tests went in, the shim was already exercised end-to-end, so the regression layer stayed focused on proving "legacy did not break" rather than discovering shim bugs.

### Additive-only Alembic

Both Phase 1a migrations (032 intake_tables, 033 policy_overrides) are pure `CREATE TABLE` operations with `nullable=True` for any columns that touch existing tables. This made rollback trivial (`DROP TABLE`) and meant the plan's "rollback rehearsal" item is genuinely low-risk.

### Shared asyncpg pool

Applying the `feedback_asyncpg_pool_event_loop` lesson upfront — using `aiflow.api.deps.get_pool()` in `IntakeRepository` rather than per-test pools — meant zero event-loop crashes in the 199-test E2E suite. Earlier phases learned this the hard way; Phase 1a didn't pay the tax.

---

## What was complicated

### SkillInstance policy-merge semantics

D0.6 (`bf8680c`) was the hardest session. The triple-merge (profile → tenant → instance) has several subtle rules:

- Instance override wins over tenant override on the same field
- Partial override (only some fields set) must NOT null out the other fields — they shine through from tenant/profile
- `policy_override: None` is semantically different from `policy_override: {}`

The 6 dedicated E2E tests in `test_skill_instance_policy_override.py` each codify one of these rules. Future reviewers should read those tests first, not the engine source.

### Pipeline auto-upgrade masking legacy step names

The `pipeline/compatibility.py` auto-upgrade layer rewrites legacy pipeline YAMLs at load time. Because the rewrite is transparent, test fixtures that *appear* to use v2 step names were actually legacy names getting rewritten. A small number of fixtures had to be made explicit (force-v2 or force-legacy) so the test intent was unambiguous.

### Migration numbering drift

The plan (`106_*`) references Alembic `030/031` for intake/policy. Implementation used `032/033` because 030 (generated_specs) and 031 (verification_edits) were already merged in Sprint B. Harmless, but it meant every Alembic reference in docs had to be cross-checked. Left the plan unchanged (historical fidelity) and noted the mapping in the PR description.

---

## What to carry into Phase 1b

1. **Keep contract-first.** The 5 source adapters should all conform to a single `SourceAdapter` ABC written in the first session of Phase 1b, before any adapter implementations.
2. **Start E2E setup earlier.** Phase 1a wrote E2E tests in week 4. For Phase 1b, stub the `test_e2e_source_adapters.py` file during week 1 with skipped placeholders so the shape is visible from day one.
3. **Check Alembic numbering on day 1.** Don't trust plan doc numbers — grep `alembic/versions/` first.
4. **One session per merge-worthy commit.** Sprint D's 10 commits map 1:1 to sessions. That's a sustainable rhythm; keep it.
5. **Legacy regression suite is a load-bearing artifact.** The 114 regression tests in Phase 1a must continue to pass through Phase 1b. Add them to any CI lane that runs in Phase 1b.

---

## Metrics delta (Sprint D)

| Metric            | Start (Sprint B close) | End (Phase 1a close) | Δ    |
|-------------------|-----------------------|---------------------|------|
| Unit tests        | 1443                  | 1674                | +231 |
| E2E tests         | 169                   | 368                 | +199 |
| DB tables         | 48                    | 49                  | +1 group |
| Alembic migrations| 31                    | 33                  | +2   |
| Top-level modules | —                     | +3 (`intake/`, `policy/`, `providers/`) | — |
| Ruff errors       | 0                     | 0                   | 0    |

Test-pass wall-clock: unit suite 121s, E2E Phase 1a suite 5.5s (well under the 10s SLA noted in the S54 prompt).

---

## Acknowledgements

This sprint was executed as an autonomous session chain (S44 → S54) with the DOHA-aligned `/next` + `/session-close` workflow. Every session closed with a clean git state, a generated next-session prompt, and an updated NEXT.md pointer — no manual bookkeeping between sessions.
