# Sprint T (v1.5.3) — PromptWorkflow consumer migration

> **Status:** ACTIVE — kickoff S147 on 2026-04-25.
> **Branch:** `feature/t-s{N}-*` (one branch per session → squash-merge to `main`).
> **Full plan:** `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md`.
> **Predecessor:** v1.5.2 Sprint S MERGED 2026-04-26 (functional vector DB, tag `v1.5.2`).
> **Target tag (post-merge):** `v1.5.3`.

## TL;DR

Sprint R (v1.5.1) **scaffolded** the `PromptWorkflow` contract — descriptors on disk, admin UI to list / inspect / dry-run, executor module ready — but explicitly deferred per-skill code migration to keep Sprint K UC3 / Sprint Q UC1 / Sprint J UC2 golden paths untouched. **Today, 0 skill consumes the executor at runtime.**

Sprint T closes that consumption loop — one skill per session, every session gated by its use-case golden-path test:

- **S148** wires `email_intent_chain` into `email_intent_processor`.
- **S149** wires `invoice_extraction_chain` into `invoice_processor.workflows.process`.
- **S150** wires `aszf_rag_chain` into `aszf_rag_chat.workflows.query` (baseline persona only — expert / mentor stay on legacy).
- **S151** retro + PR + tag `v1.5.3`.

Feature flags stay default-OFF: `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false`, `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""`. **Zero tenant impact** unless the operator explicitly opts each skill in.

## 3 deliveries in 3 sessions

| ID   | Skill / migration target                                  | Workflow descriptor          | Gate threshold |
|------|-----------------------------------------------------------|------------------------------|----------------|
| S148 | `email_intent_processor` LLM branch                       | `email_intent_chain`         | Sprint K UC3 4/4 golden-path E2E + 25-fixture flag-on label parity within ±1 fixture |
| S149 | `invoice_processor.workflows.process`                     | `invoice_extraction_chain`   | Sprint Q UC1 golden-path slice (≥ 75% / invoice_number ≥ 90%) + 10-fixture operator measurement ≥ 80% accuracy within ±5pp of Sprint Q 85.7% baseline |
| S150 | `aszf_rag_chat.workflows.query` (**baseline persona only**) | `aszf_rag_chain`             | Sprint J UC2 MRR@5 ≥ 0.55 Profile A; flag-on parity within ±0.02 absolute on 20-item HU UC2 corpus |

Each session ships with both **flag-off** (legacy path byte-stable) and **flag-on** (executor parity) smokes.

## What stays unchanged

- `AIFLOW_PROMPT_WORKFLOWS__ENABLED` default **`false`**.
- `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` default **`""`** (empty).
- 0 Alembic migrations (head stays at 047).
- 0 new endpoints (196).
- 0 new admin UI pages (26).
- `EmailDetailResponse.extracted_fields` Pydantic schema byte-identical (Sprint Q S136 contract preserved).
- Sprint J Profile A NULL-fallback gate unchanged.
- Sprint P strategy switch + attachment-signal early-return on the sklearn path unchanged.
- `aszf_rag_chat` expert + mentor persona variants stay on the legacy direct-prompt path (`ST-FU-2`).

## Carry-forward (not Sprint T scope)

- **`SS-FU-1` / `SS-FU-5`** — `customer` → `tenant_id` model rename. Wide cross-call surface; bundling with multi-tenancy rollout would have made the Sprint S diff opaque. Separate refactor sprint.
- **`SS-SKIP-2`** — Profile B (Azure OpenAI) live MRR@5. Azure billable credit pending.
- **`SR-FU-4` / `SR-FU-5` / `SR-FU-6`** — admin-page live-stack Playwright, `vite build` pre-commit hook, Langfuse workflow listing. Side-deliveries if bandwidth allows; otherwise post-Sprint-T.
- **`ST-FU-1`** (NEW) — JWT singleton CI-only failure in `tests/unit/api/test_rag_collections_router.py` (3 tests). Linux CI's `secret_cache_hit negative=True` causes ephemeral key swap between token-sign and verify. Local Windows runs PASS. Recommended fix in S148 side delivery: pin a per-test fresh `AuthProvider` + clear secret cache fixture.
- **`ST-FU-2`** (NEW) — Expert / mentor persona PromptWorkflow descriptors. Each variant's `system_prompt_<role>.yaml` would need its own descriptor. Post-Sprint-T scope.

## Operator activation (post-merge)

Once `v1.5.3` ships, each tenant can be migrated independently:

```bash
# Step 1 — enable the executor globally for the tenant's deployment
export AIFLOW_PROMPT_WORKFLOWS__ENABLED=true

# Step 2 — opt each skill in one at a time, observing the per-skill golden path
export AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV="email_intent_processor"
# (verify Sprint K UC3 4/4 + 25-fixture parity)

export AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV="email_intent_processor,invoice_processor"
# (verify Sprint Q UC1 ≥ 80% accuracy)

export AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV="email_intent_processor,invoice_processor,aszf_rag_chat"
# (verify Sprint J UC2 MRR@5 ≥ 0.55 — baseline persona only)
```

**Hot rollback** is a single env-var change — drop the skill name from the CSV; the legacy direct-prompt path runs immediately. No code rollback or DB rollback required.

## STOP conditions (summary)

- Any per-session golden-path threshold fails → halt + escalate.
- Flag-off smoke regression (legacy path byte-instability) → halt; revert the session's diff.
- `EmailDetailResponse.extracted_fields` schema drift in S149 → halt (Sprint Q UI consumer would break).
- `alembic upgrade head` ≠ 047 at any session start → drift outside Sprint T scope; investigate.
- Operator wants different skill ordering (e.g. start with `aszf_rag_chat`) → halt + revisit `01_PLAN/117_*.md` §2 sessions.

See the full plan doc for risk register, rollback details, expected diff sizes, and session-by-session test-count expectations.
