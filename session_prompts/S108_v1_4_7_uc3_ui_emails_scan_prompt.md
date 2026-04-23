# AIFlow v1.4.7 Sprint K — Session 108 Prompt (UC3 — Emails.tsx scan + intent/routing UI)

> **Datum:** 2026-04-23 (tervezett folytatas)
> **Branch:** `feature/v1.4.7-email-intent`
> **HEAD:** `f557366` — `feat(sprint-k): S107 — IntentRoutingPolicy + scan_and_classify routing wiring`
> **Alembic head:** `042` (nincs uj migration szukseges)
> **Port:** API 8102 | Frontend Vite 5174
> **Elozo session:** S107 — `IntentRoutingPolicy` + `scan_and_classify` routing wiring + `POST /emails/scan/{config_id}` `routing_policy_id` + 4-way integration test GREEN.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K — S108 row (UI `Emails.tsx`).
> **Session tipus:** UI IMPLEMENTATION — 7 HARD GATE pipeline (Journey → Figma → Component → Page → API → E2E).

---

## KONTEXTUS

### Honnan jottunk (S107 output)

- `src/aiflow/policy/intent_routing.py` — `IntentAction`, `IntentRoutingRule`, `IntentRoutingPolicy` + `from_yaml` / `load_for_tenant`.
- `scan_and_classify(routing_policy=..., prompt_manager=..., prompt_name=...)` — persists `output_data.routing_action` + `routing_target`, emits `email_connector.scan_and_classify.routed` + optional `.prompt_fetched` structlog events.
- `POST /api/v1/emails/scan/{config_id}` — `ScanRequest.routing_policy_id` optional body field → betolti `$AIFLOW_POLICY_DIR/intent_routing/{id}.yaml`.
- 2 integration test GREEN (S106 `scan_and_classify` + S107 `intent_routing`) real Docker PG-n.
- `tests/integration/services/email_connector/conftest.py` — `deps.close_all()` autouse fixture (asyncpg pool + event loop trap fix).

### Hova tartunk (S108 scope)

UI `Emails.tsx` v2 az `aiflow-admin/`-ben:
- **Scan mailbox** gomb a connector kartyan → `POST /api/v1/emails/scan/{config_id}` hivas, `routing_policy_id` optional dropdown-bol.
- Email listaban **intent badge** (display_name + confidence szin-kodolva) + **routing action chip** (EXTRACT / NOTIFY_DEPT / ARCHIVE / MANUAL_REVIEW).
- **Langfuse trace link** per email (ha `output_data.prompt_version` is set → link a Langfuse trace-re).
- Playwright E2E: click Scan → 3 mock email → lista frissul intent + routing chip-ekkel.

### Jelenlegi allapot

```
27 service | 181 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1995 unit PASS | 413 E2E collected | 57 integration (incl. S106 + S107 UC3)
8 skills | Branch: feature/v1.4.7-email-intent @ f557366
Sprint J MERGED | UC2 DONE | UC3 S107 DELIVERED | UC3 S108 START
```

---

## ELOFELTELEK

```bash
git branch --show-current                              # feature/v1.4.7-email-intent
git log --oneline -1                                   # f557366
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet   # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/email_connector/ -q --no-cov
# Expected: 2 passed (S106 + S107)
cd aiflow-admin && npx tsc --noEmit                    # 0 hiba
```

**Docker dependencies:** PG (5433), Redis (6379). `docker compose up -d db redis` ha nem futnak.
**Frontend dev:** `cd aiflow-admin && npm run dev` → http://localhost:5174

---

## FELADATOK (7 HARD GATE pipeline — aiflow-ui-pipeline skill)

### GATE 0 — Journey (~10 min)

**File:** `aiflow-admin/journeys/uc3_scan_mailbox.md` (UJ).

```
USER: admin kattint Emails oldalon -> Scan mailbox gomb
  -> (opcionalisan) routing policy dropdown valaszt
  -> POST /emails/scan/{config_id} body: {tenant_id, max_items, routing_policy_id}
  -> ScanResponse.items renderelodnek az email listaban
  -> minden sor: intent badge + routing action chip + (ha van) Langfuse trace link
```

Required API endpoints — hasznald a letezoket:
- `GET /api/v1/emails/connectors` — connector lista
- `POST /api/v1/emails/scan/{config_id}` — scan-classify-route
- `GET /api/v1/emails?intent={label}` — lista (letezik)

### GATE 1 — Figma design (~20 min)

Hasznald a `frontend-design` skillt: `Emails.tsx` page-hez adj hozza:
- `ScanMailboxButton` komponenst a page headerbe (Untitled UI primary button + Zap icon).
- `IntentBadge` chip (color map: invoice_question=blue, support_request=amber, spam=rose, unknown=slate).
- `RoutingActionChip` (EXTRACT=emerald, NOTIFY_DEPT=violet, ARCHIVE=zinc, MANUAL_REVIEW=amber, REPLY_AUTO=sky).
- `LangfuseTraceLink` (external link icon + hover tooltip, csak ha `output_data.prompt_version`).

Screenshot-olj az UNOUN UI component library-ba, FigJam frame-et mentsd.

### GATE 2 — Components (~30 min)

**Files:**
- `aiflow-admin/src/components/emails/IntentBadge.tsx` (UJ) — `label` + `confidence` → colored badge.
- `aiflow-admin/src/components/emails/RoutingActionChip.tsx` (UJ) — `action` → colored chip.
- `aiflow-admin/src/components/emails/LangfuseTraceLink.tsx` (UJ) — `traceUrl` → external link.
- `aiflow-admin/src/components/emails/ScanMailboxButton.tsx` (UJ) — `configId` + `policyId?` + onSuccess callback, loading state.

React Aria + Tailwind v4, no hardcoded colors (`var(--color-*)`).

### GATE 3 — Page wiring (~20 min)

**File:** `aiflow-admin/src/pages-new/Emails.tsx` (MODIFY).

- Header: add `ScanMailboxButton` (config selector dropdown from `GET /connectors`).
- Row: replace/extend intent cell with `IntentBadge`, add `RoutingActionChip` cell from `output_data.routing_action`, add `LangfuseTraceLink` if `prompt_version` present.
- After scan success → invalidate `useQuery(["emails"])`.

Respect `source` field (`demo` vs `backend`) — keep the Demo/Live indicator (feedback_no_silent_mock.md).

### GATE 4 — API contract verify (~10 min)

**File:** `aiflow-admin/src/api/emails.ts` — frissitsd a response tipusokat:
- `EmailResultItem` — opcionalis `routing_action`, `routing_target`, `prompt_name`, `prompt_version` mezokkel.
- `ScanRequest` tipus — `routing_policy_id?` mezovel.

Futtasd: `curl -s http://localhost:8102/openapi.json | jq '.paths."/api/v1/emails/scan/{config_id}"'` — ellenorizd a schema-t.

### GATE 5 — Playwright E2E (~30 min)

**File:** `aiflow-admin/tests/e2e/emails_scan.spec.ts` (UJ).

- Mock `/api/v1/emails/connectors` → 1 dev imap connector.
- Mock `/api/v1/emails/scan/{config_id}` → 4 `ScanResponse.items` (invoice / support / spam / unknown) routing_action-okkal.
- Click Scan Mailbox → assert 4 row with correct badge+chip color.
- Hover Langfuse link → assert tooltip.

### GATE 6 — Docs + regression (~10 min)

- `CLAUDE.md` Key Numbers: 413 → 414 E2E (1 uj Playwright).
- `110_USE_CASE_FIRST_REPLAN` §4 S108 row: **[DELIVERED]**.
- `cd aiflow-admin && npx tsc --noEmit` — 0 hiba.
- `.venv/Scripts/python.exe -m ruff check src/ tests/` — 0 error (csak fallback check, nem valoszinu py valtozas).

### GATE 7 — Session close

```bash
/session-close S108
```

---

## STOP FELTETELEK

**HARD:**
1. `ScanResponse.items` nem tartalmaz `routing_action`-t (backend schema drift) → architect.
2. Playwright mock nem imgaltja a real network flow-t → SOFT, quarantine-ba.
3. Tailwind v4 CSS var-ok nem mukodnek dev-ben → `@theme` config-ot elvenni.

**SOFT:**
1. Langfuse URL format nem deriveable client-side → omit link, S109-re defer (Prompts.tsx-ban generalja).
2. 4-way routing mock + Scan button gyorsabb mint a backend scan ~5-10s → adj loading spinner-t, ne blokkold a session-t.

---

## SESSION VEGEN

```
/session-close S108
```

Utana `/clear` es S109 (`Prompts.tsx` v2 — Langfuse-synced prompt editing with `PUT /api/v1/prompts/{id}`).
