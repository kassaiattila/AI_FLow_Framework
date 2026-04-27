# AIFlow [Sprint X] — Session SX-4 Prompt (Professional RAG chat — Alembic 051 + 4-route API + `/aszf/chat` UI upgrade)

> **Template version:** 1.0 (mandatory Quality target header).
> **Source template:** `session_prompts/_TEMPLATE.md`.
> **Closes:** Sprint W pipeline gap §3 — UC2 RAG chat is a stateless API. SX-4 promotes it from "demo" to "professional" with conversation persistence + persona switcher + collection picker + citation card + cost meter + transcript export.

---

## Quality target (MANDATORY)

- **Use-case:** UC2 (RAG chat) — additive conversation-persistence layer **above** the existing `/aszf/chat` retrieval API; retrieval API stays byte-stable so UC2 MRR@5 ≥ 0.55 is unchanged.
- **Metric:** composite gate — (a) UC2 MRR@5 ≥ 0.55 on existing `/aszf/chat` retrieval (byte-stable); (b) every conversation turn writes one `aszf_conversation_turns` row; (c) page reload preserves conversation history (sidebar list + center turn stream); (d) persona switcher mid-conversation produces a visible "persona changed" marker in the turn stream.
- **Baseline (now):** UC2 MRR@5 = 0.55 (Profile A BGE-M3, since Sprint J); `/aszf/chat` is **stateless** — every turn is a fresh request, no DB row, no UI history; persona only via API param, not UI.
- **Target (after this session):** all four sub-gates green. Alembic head 050 → 051. Every UI-driven turn lands in `aszf_conversation_turns` with citations + cost + latency. Sidebar history persists across page reload. Live Playwright `aszf-chat.md` 4/4 PASS.
- **Measurement command:** `pytest tests/integration/skills/test_uc2_rag_baseline_workflow.py tests/integration/services/test_conversation_repository_real.py tests/integration/api/test_conversations_router_real.py -v`

> Note: SX-4 is **additive** — the existing `/aszf/chat` retrieval API is NOT modified (UC2 byte-stable gate). Conversation persistence is a layer above retrieval: the UI calls `POST /api/v1/conversations` to start a session, then for each turn calls BOTH `POST /api/v1/aszf/chat` (byte-stable retrieval) AND `POST /api/v1/conversations/{id}/turns` (new — persistence).

---

## Goal

Replace the stateless `/aszf/chat` minimalist page with a professional management surface. Add an Alembic 051 `aszf_conversations` + `aszf_conversation_turns` schema, a `ConversationService`, a 4-route `/api/v1/conversations` API, and an upgraded `/aszf/chat` admin UI page with sidebar history + persona switcher + per-tenant collection picker + cumulative cost meter + transcript export. The upgrade is the customer-facing finish on the RAG chat surface.

---

## Predecessor context

> **Datum:** 2026-04-27
> **Branch:** `feature/x-sx4-rag-chat-conversations` (cut from `main` after SX-3 close).
> **HEAD (expected):** `c259c7c` (SX-3 routing trace audit + admin UI, PR #67 squash-merged).
> **Predecessor session:** SX-3 — routing trace audit + admin UI (PR #67 merged with 12/12 live Playwright PASS + 1 UX bug fix).

---

## Pre-conditions

- [ ] SX-3 PR (#67) merged on `main` (verified — visible in `git log --oneline`)
- [ ] Branch cut: `feature/x-sx4-rag-chat-conversations`
- [ ] Stack runnable (`bash scripts/start_stack.sh --validate-only` GREEN)
- [ ] Alembic head = 050 (`PYTHONPATH=src .venv/Scripts/python.exe -m alembic current` reports `050`)
- [ ] PostgreSQL Docker container running (5433)
- [ ] Existing `aszf_rag_chat` skill: `POST /api/v1/aszf/chat` retrieval endpoint reachable + UC2 MRR@5 ≥ 0.55 baseline confirmed (`tests/integration/skills/test_uc2_rag_baseline_workflow.py`)
- [ ] Existing `aszf_rag_chain_{baseline,expert,mentor}` PromptWorkflow descriptors registered (Sprint T S150 + Sprint U S155)
- [ ] aiflow-admin dev server starts (`cd aiflow-admin && npm run dev` → 5173)

---

## Predecessor surfaces (existing, do not modify)

- Existing chat endpoint: `POST /api/v1/aszf/chat` in `src/aiflow/api/v1/rag_engine.py` (or equivalent — verify path). **Byte-stable.** SX-4 does NOT change request/response shape, retrieval logic, or descriptor selection.
- `aszf_rag_chain_{baseline,expert,mentor}` PromptWorkflow descriptors at `prompts/workflows/`. **Read-only** — persona switcher in UI selects which descriptor the chat endpoint uses.
- `rag_collections` table + tenant-scoped collection list (Sprint S S143–145). UI collection picker reads from `GET /api/v1/rag/collections/?tenant_id=...`.
- `Citation` shape (existing in chat response): `{"source_id": str, "title": str, "snippet": str, "score": float}` — preserved as-is in the new `aszf_conversation_turns.citations` JSONB.
- Alembic head: `050` (verify via `alembic current`).
- OpenAPI snapshot: `docs/api/openapi.json` (drift gate).

---

## Tasks

1. **Alembic 051 — `aszf_conversations` + `aszf_conversation_turns` tables.**
   - File: `alembic/versions/051_aszf_conversations.py`
   - `aszf_conversations`:
     - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
     - `tenant_id TEXT NOT NULL DEFAULT 'default'`
     - `created_by TEXT NOT NULL` (user_id from JWT)
     - `persona TEXT NOT NULL` (CHECK in `('baseline', 'expert', 'mentor')`)
     - `collection_name TEXT NOT NULL` (FK-style; not enforced because rag_collections has soft-delete patterns)
     - `title TEXT NULL` (operator-editable; default NULL → UI shows first-turn snippet as label)
     - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
     - `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` (trigger updates on turn append)
   - `aszf_conversation_turns`:
     - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
     - `conversation_id UUID NOT NULL REFERENCES aszf_conversations(id) ON DELETE CASCADE`
     - `turn_index INTEGER NOT NULL` (0-based; UNIQUE per conversation)
     - `role TEXT NOT NULL` (CHECK in `('user', 'assistant')`)
     - `content TEXT NOT NULL`
     - `citations JSONB NULL` (only populated on assistant turns)
     - `cost_usd FLOAT NULL` (only populated on assistant turns)
     - `latency_ms INTEGER NULL` (only populated on assistant turns)
     - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
   - Indexes: `aszf_conversations(tenant_id, updated_at DESC)`, `aszf_conversation_turns(conversation_id, turn_index)` UNIQUE.
   - Round-trip clean (`alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`).

2. **Service — `ConversationService`.**
   - Path: `src/aiflow/services/conversations/service.py` (+ `schemas.py`, `repository.py`, `__init__.py`)
   - Methods (async, real PG via existing session factory):
     - `create(tenant_id, created_by, persona, collection_name, title=None) → ConversationDetail`
     - `list(tenant_id, limit=50, offset=0) → list[ConversationSummary]` (sorted `updated_at DESC`)
     - `get(id, tenant_id) → ConversationDetail | None` (includes turns)
     - `append_turn(conversation_id, tenant_id, role, content, citations=None, cost_usd=None, latency_ms=None) → TurnDetail` (auto-increment `turn_index`; updates parent's `updated_at`; tenant-scope guard)
     - `delete(id, tenant_id) → None` (intentionally added even though DELETE route is deferred — service-level method ready for v1.8.1)
   - Pydantic v2 schemas: `ConversationCreate`, `ConversationSummary`, `ConversationDetail`, `TurnAppend`, `TurnDetail`, `Citation` (shared shape with `/aszf/chat` response).

3. **API — new router `/api/v1/conversations`.**
   - Path: `src/aiflow/api/v1/conversations.py` (mount in `src/aiflow/api/app.py`)
   - 4 routes:
     - `GET /` — list per tenant (query: `tenant_id`, `limit` default 50 max 200, `offset` default 0)
     - `POST /` — create (body: `ConversationCreate` = persona + collection_name + optional title)
     - `GET /{id}` — detail with turns (404 on miss; tenant-scoped)
     - `POST /{id}/turns` — append a turn (body: `TurnAppend` = role + content + optional citations/cost/latency)
   - Auth: existing tenant-scoped JWT pattern (mirror `/api/v1/emails` and `/api/v1/routing-runs` from SX-3).
   - Response schemas: `ConversationSummary`, `ConversationDetail`, `TurnDetail`.

4. **`/aszf/chat` retrieval API — UNCHANGED.**
   - **Hard constraint.** SX-4 must NOT modify `POST /api/v1/aszf/chat`'s request/response shape, retrieval logic, descriptor selection, or any test that exercises it. UC2 MRR@5 ≥ 0.55 byte-stable.
   - Persona is **per-conversation** in the data model. The UI passes `persona` from the conversation row to the chat endpoint as a query/body param (existing param if it exists; new query param if not — but the chat endpoint's response shape stays identical).

5. **Admin UI `/aszf/chat` upgrade.**
   - Path: `aiflow-admin/src/pages-new/AszfChat.tsx` (or `Chat.tsx` — match existing file). Replace the minimalist page entirely.
   - Layout (Untitled UI + Tailwind v4 + React Aria, 7 HARD GATES):
     - **Left sidebar** — conversation history list (per-tenant, sorted `updated_at DESC`); each row shows `title || first-user-turn-snippet`, persona badge, last-updated relative time. Click loads conversation detail. "New conversation" button at top.
     - **Top bar** — persona switcher (segmented control: `baseline` / `expert` / `mentor`; defaults to `baseline`); per-tenant collection picker (dropdown reading from `GET /api/v1/rag/collections/?tenant_id=...`); cost meter (cumulative USD for current conversation, summing assistant turn `cost_usd`).
     - **Center panel** — turn stream; user turns right-aligned, assistant turns left-aligned with **Citation card** below; assistant turn has cost chip (USD + latency ms). Transcript export button (JSON download containing all turns + citations).
     - **Citation card** — clickable; opens deep-link to source document in the live RAG collection (existing `/api/v1/rag/collections/{name}/documents/{id}` route — verify path before linking).
     - **Mid-conversation persona switch marker** — when the operator switches persona during an active conversation, a visible non-turn marker row appears (`"Persona changed to expert at 14:23:45"`) so the answer-style shift is operator-visible.
   - EN/HU locale entries in `aiflow-admin/src/locales/{en,hu}.json`.
   - Mounted in admin sidebar nav (existing nav config — likely under "Tudasbazis" / "Knowledge Base" group).

6. **OpenAPI snapshot refresh.**
   - `PYTHONPATH=$(pwd) .venv/Scripts/python.exe scripts/export_openapi.py`
   - Expected delta: **+4 paths** (`/api/v1/conversations/`, `/api/v1/conversations/{id}`, `/api/v1/conversations/{id}/turns`, plus the GET-list collision is single path with two methods) **+5–7 schemas** (`ConversationCreate`, `ConversationSummary`, `ConversationDetail`, `TurnAppend`, `TurnDetail`, possibly `Citation` if not already exported). No removals; no changes to existing paths/schemas.

---

## Tests (15 unit + 3 integration + 4 live Playwright)

**Service unit (9):**
- `test_create_returns_uuid_and_persists`
- `test_create_defaults_title_to_null`
- `test_list_filters_by_tenant_isolates_correctly`
- `test_list_orders_by_updated_at_desc`
- `test_get_includes_turns_in_index_order`
- `test_get_returns_none_for_other_tenant`
- `test_append_turn_increments_turn_index`
- `test_append_turn_updates_parent_updated_at`
- `test_append_turn_rejects_cross_tenant`

**Router unit (6):**
- `test_post_create_returns_201_with_detail`
- `test_get_list_returns_200_with_default_pagination`
- `test_get_list_rejects_limit_over_200_with_422`
- `test_get_detail_returns_404_for_missing_id`
- `test_post_turns_appends_with_citations`
- `test_post_turns_enforces_tenant_scope`

**Integration (3, real PG via Docker 5433):**
- `test_conversation_repository_real.py::test_create_then_append_then_list_real_pg`
- `test_conversation_repository_real.py::test_cascade_delete_drops_turns_real_pg`
- `test_conversations_router_real.py::test_full_round_trip_create_append_get_real_pg` — uses httpx.AsyncClient + ASGITransport (same pattern as SX-3 test) to avoid the asyncpg pool + event loop trap.

**Live Playwright (4, `tests/ui-live/aszf-chat.md`):**
- Test 1 — create conversation, ask question, persona switcher selected = `baseline`, citation card renders, cost chip non-zero
- Test 2 — refresh page → conversation persists in sidebar; click → turns reload
- Test 3 — switch persona to `expert` mid-conversation → next turn uses `aszf_rag_chain_expert` descriptor + persona-change marker visible
- Test 4 — transcript export downloads JSON with all turns + citations

**Plus 3 edge-case scenarios (live testing protocol from SX-3):**
- Cross-tenant URL guard (manipulate `tenant_id` query → 404)
- Empty state (no conversations yet → "Új beszélgetés" prompt)
- Drawer/panel ESC close + backdrop click + X button parity

---

## Acceptance criteria

- [ ] **Quality target met** — `pytest tests/integration/skills/test_uc2_rag_baseline_workflow.py tests/integration/services/test_conversation_repository_real.py tests/integration/api/test_conversations_router_real.py -v` PASS (composite gate)
- [ ] All 15 unit tests PASS (`make test`)
- [ ] All 3 integration tests PASS
- [ ] Alembic 051 round-trip clean (upgrade → downgrade → upgrade)
- [ ] Live Playwright `tests/ui-live/aszf-chat.md` 4/4 PASS on a clean dev stack (`/live-test aszf-chat`)
- [ ] No regression on byte-stable `/aszf/chat` retrieval API (UC2 MRR@5 ≥ 0.55 unchanged via `tests/integration/skills/test_uc2_rag_baseline_workflow.py`)
- [ ] Cumulative cost meter sums correctly across multiple assistant turns
- [ ] Persona switch mid-conversation produces visible marker AND next turn uses the new descriptor
- [ ] `make lint` clean
- [ ] `cd aiflow-admin && npx tsc --noEmit` clean
- [ ] OpenAPI snapshot refreshed (+4 paths +5–7 schemas; **zero removals; zero changes to existing paths**)
- [ ] PR opened against `main`, CI green
- [ ] `01_PLAN/ROADMAP.md` Sprint X table row SX-4 status → DONE
- [ ] `CLAUDE.md` Sprint X session lineup table row SX-4 status → DONE

---

## Constraints

- **Retrieval API byte-stable.** `/aszf/chat` request/response shape, retrieval logic, and descriptor selection unchanged. UC2 MRR@5 ≥ 0.55 unchanged.
- **Tenant scope.** Every read API route enforces `tenant_id` from the JWT (or query param mirroring existing emails/routing-runs pattern). No cross-tenant leakage in list/get/append.
- **Citation shape preservation.** The existing `Citation` shape from `/aszf/chat` is reused in `aszf_conversation_turns.citations` JSONB so the UI can render the citation card identically whether the turn is "live" (just answered) or "loaded" (from history).
- **No turn-deletion endpoint.** `DELETE /conversations/{id}` and `DELETE /conversations/{id}/turns/{turn_id}` are intentionally deferred to v1.8.1 per the plan (operators ask for it after seeing usage patterns).
- **No new endpoint paths beyond the 4 listed.** OpenAPI delta tightly bounded.
- **No DB schema change beyond Alembic 051.** SX-5 owns no migrations.
- **No UI page beyond `/aszf/chat` upgrade.** SX-5 owns the SW-FU-2 source-toggle on `/prompts/workflows`.

---

## STOP conditions

**HARD:**
- UC2 MRR@5 < 0.55. Halt; the conversation persistence layer is leaking into the retrieval path.
- `/aszf/chat` retrieval API request/response shape changed. Halt; revert.
- Alembic 051 round-trip not clean (downgrade fails). Halt; revert migration.
- OpenAPI drift on existing paths/schemas (only the +4/+5–7 additive delta is allowed). Halt.
- Tenant-scope leak in any of the 4 routes (cross-tenant row visible). Halt.
- Persona switch mid-conversation produces inconsistent style WITHOUT the marker. Halt; the marker is operator-visibility-critical.

**SOFT:**
- Citation deep-link 404 (collection or document missing) — render the citation card with a "source unavailable" badge; defer fix to follow-up.
- Cost meter rounding edge cases (0.0001 USD displayed as `<$0.01`) — accept; matches SX-3 routing-runs UI convention.
- Transcript export size > 5 MB on long conversations — chunk or warn; defer optimization.
- Operator-driven dependency missing (no Docker PG) → integration tests skip; unit gates still required.

---

## Output / handoff format

The session ends with:

1. PR opened against `main` titled `feat(sprint-x): SX-4 — professional RAG chat (Alembic 051 + 4-route API + /aszf/chat UI upgrade)`
2. PR body summarizes:
   - Alembic 051 round-trip
   - Service + router + UI page LOC
   - Composite Quality target outcome (UC2 MRR@5 byte-stable + conversation persistence verified)
   - Live Playwright 4/4 PASS evidence
3. `/session-close SX-4` invoked → archives this prompt to `session_prompts/archive/SX-4_aszf_conversations_prompt.md` and generates `session_prompts/NEXT.md` for SX-5 (close + SW-FU bundle + tag `v1.8.0`)
4. `01_PLAN/ROADMAP.md` Sprint X table row SX-4 status → DONE
5. `CLAUDE.md` Sprint X session lineup table row SX-4 status → DONE
6. (No `docs/SPRINT_HISTORY.md` entry — that lands at SX-5 sprint-close only)

---

## References

- Sprint X plan: `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md` §SX-4
- Forward queue: `01_PLAN/ROADMAP.md`
- Post-Sprint-W audit: `docs/post_sprint_w_audit.md` §"RAG chat is a stateless API"
- Honest alignment audit: `docs/honest_alignment_audit.md` §2.4 (UC2 RAG state)
- Predecessor session prompt (SX-3): `session_prompts/archive/SX-3_routing_runs_trace_prompt.md`
- SX-3 live test report (Playwright MCP pattern): `tests/ui-live/routing-runs.md` `## Utolso futtatas`
- `aszf_rag_chain_{baseline,expert,mentor}` descriptors: `prompts/workflows/`
- aiflow-admin UI pipeline (7 HARD GATES): `.claude/skills/aiflow-ui-pipeline/SKILL.md`
- Database conventions: `.claude/skills/aiflow-database/SKILL.md`
- Quality baseline script: `scripts/run_quality_baseline.sh`
- Session-prompt template: `session_prompts/_TEMPLATE.md`
