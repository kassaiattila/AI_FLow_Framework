# Live UI journey — `/aszf/chat` (Sprint X / SX-4)

```yaml
@test_registry:
  suite: ui-live
  component: aiflow-admin/AszfChat
  covers:
    - aiflow-admin/src/pages-new/AszfChat.tsx
    - src/aiflow/api/v1/conversations.py
    - src/aiflow/api/v1/aszf_chat.py
  phase: v1.8.0
  priority: high
  estimated_duration_ms: 240000
  requires_services: [api, ui, postgres]
  tags: [ui-live, aszf-chat, sprint_x, sx_4]
```

## Utolso futtatas

> Status: PENDING — first SX-4 live execution.

---

## Pre-conditions

- API up on `http://127.0.0.1:8102` (`/health/ready` returns 200).
- Vite UI up on `http://127.0.0.1:5173`.
- PostgreSQL container `07_ai_flow_framwork-db-1` healthy on port 5433.
- Alembic head = `051` (`PYTHONPATH=src .venv/Scripts/python.exe -m alembic current` → `051 (head)`).
- At least one rag collection visible from `GET /api/v1/rag-collections?tenant_id=default` (e.g. `azhu-test`).
- LLM credentials available (`OPENAI_API_KEY` or LiteLLM equivalent) — the
  `/api/v1/aszf/chat` endpoint runs the live RAG workflow; without LLM creds
  T1/T3 will fail at the "Send" step with a 500.

## Authentication

```js
await page.evaluate(async () => {
  const r = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "admin@bestix.hu", password: "admin123" }),
  });
  const json = await r.json();
  localStorage.setItem("aiflow_token", json.access_token);
});
```

Then reload `http://localhost:5173/#/aszf/chat`.

## Test corpus assumptions

The page lists conversations by tenant. Tests start fresh — every test
creates its own conversation rows via the UI, so no seed script is
required. The `azhu-test` collection (or the first one returned by
`GET /api/v1/rag-collections`) must contain ingested ASZF chunks so the
RAG retrieval returns at least one citation.

If the active tenant has no collections, the composer "Send" button is
disabled and the page renders the empty-state copy — both T-empty-state
and the cross-tenant guard test cover that branch.

---

## Test 1 — Golden path: create conversation + ask question + citation card

Steps:

1. Navigate to `http://localhost:5173/#/aszf/chat`.
2. Wait for the page heading: `getByRole('heading', { name: /aszf chat/i })`.
3. Assert the persona switcher is visible with `baseline` selected
   (`getByTestId('aszf-persona-baseline')` has `aria-pressed="true"`).
4. Pick the first available collection from
   `getByTestId('aszf-collection-picker')`.
5. Type into `getByTestId('aszf-composer-input')`:
   `Mi a panaszkezelési hatarido?`.
6. Click `getByTestId('aszf-composer-send')`.
7. Wait until `getByTestId('aszf-busy')` disappears (max 60 s — workflow
   includes 6 LLM calls).
8. Assert exactly two turn bubbles appear:
   - `getByTestId('aszf-turn-user')` with the question text
   - `getByTestId('aszf-turn-assistant')` with non-empty answer
9. Assert at least one `getByTestId('aszf-citation-card')` block renders
   under the assistant turn.
10. Assert the `getByTestId('aszf-cost-meter')` shows a non-zero USD value
    (`> $0`).
11. Assert the sidebar list now contains a row for the new conversation
    (`getByTestId(/^aszf-conv-item-/)`) with the `baseline` persona badge.

**PASS criteria:** answer + citation card rendered, sidebar shows the
new conversation, cumulative cost > $0.

## Test 2 — Persistence: page reload preserves history + turn replay

Steps:

1. Note the conversation row's `data-testid` from T1 (`aszf-conv-item-{uuid}`).
2. Reload the page (`page.reload()`).
3. Wait for the sidebar to render.
4. Assert the conversation row from T1 is still visible.
5. Click that row.
6. Assert both turns from T1 reappear in the center stream (user +
   assistant) AND the citation card on the assistant turn is rendered
   from the persisted citations JSONB.
7. Assert the persona switcher reflects `baseline` and the collection
   picker locks to the conversation's collection.

**PASS criteria:** Sidebar persists across reload; clicking a historical
conversation replays its turns + citations; persona/collection re-bind.

## Test 3 — Mid-conversation persona switch produces visible marker

Steps:

1. With the conversation from T1/T2 active, click
   `getByTestId('aszf-persona-expert')`.
2. Assert a marker row appears in the stream:
   `getByTestId('aszf-persona-change-marker')` with text matching
   `/Persona changed:?\s*baseline\s*[→>]\s*expert/i`.
3. Type a follow-up question (e.g. `Es ha a bank elutasitja?`).
4. Click Send; wait for busy to clear.
5. Assert a new assistant turn appears, with citations + cost.
6. Inspect the network log for the `POST /api/v1/aszf/chat` call: the
   request body's `persona` field reads `expert`.

**PASS criteria:** Marker visible BEFORE the next assistant turn; the
chat request carries `persona=expert`.

## Test 4 — Transcript export downloads JSON

Steps:

1. With a non-empty conversation active, click
   `getByTestId('aszf-transcript-export')`.
2. Capture the download via Playwright's download API.
3. Assert the download filename matches `aszf-chat-*.json`.
4. Parse the downloaded JSON; assert:
   - It carries a top-level `conversation` object with the expected
     `persona` and `collection_name`.
   - `turns` is an array of length ≥ 2 (T1 user + assistant turns).
   - The assistant turn's `citations` array length matches what the UI
     showed in T1.

**PASS criteria:** Download fires; JSON structure matches the
ConversationDetail schema; citations preserved.

---

## Edge case 1 — Cross-tenant URL guard

Steps:

1. Navigate to `http://localhost:5173/#/aszf/chat` while authenticated
   as `admin` (tenant `default`).
2. From devtools, manually call:
   ```js
   await fetch(`/api/v1/conversations/${otherTenantConvId}?tenant_id=other-tenant`,
     { headers: { Authorization: `Bearer ${token}` } });
   ```
3. Assert the response is `404` (no leakage).
4. Repeat with the correct tenant; assert `200`.

**PASS criteria:** Cross-tenant detail GET returns 404; same-tenant
returns 200.

## Edge case 2 — Empty state for new tenant

Steps:

1. Switch `localStorage.aiflow_tenant` to `tenant-with-no-conversations`.
2. Reload the page.
3. Assert `getByTestId('aszf-empty-state')` renders with the empty-state
   copy ("No conversations yet …" / "Még nincs beszélgetés …").
4. Assert no conversation rows are visible in the sidebar.

**PASS criteria:** Empty-state copy renders; sidebar list is empty.

## Edge case 3 — Composer send disabled when no collection

Steps:

1. Stub `GET /api/v1/rag-collections` to return `{ items: [], total: 0 }`.
2. Reload `/aszf/chat`.
3. Type a question.
4. Assert `getByTestId('aszf-composer-send')` has `disabled` attribute.
5. Click it; assert no `POST /api/v1/conversations` request fires.

**PASS criteria:** Send button disabled; no chat / conversation API
calls fire when no collection is available.

---

## Capture artifacts

Each successful run should append a row to "Utolso futtatas" with:

- Date / time
- Result (PASS / FAIL counts)
- Number of conversations + turns persisted
- Total LLM cost burned (sum of assistant `cost_usd`)
- Any UI bugs found + fix landing PR link
- Console error audit (expected: 0 unexpected errors)
- Network request audit (`/api/v1/conversations/*` + `/api/v1/aszf/chat`)
