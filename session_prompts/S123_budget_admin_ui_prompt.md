# AIFlow v1.4.10 Sprint N — Session 123 Prompt (admin UI budget dashboard + alert threshold editor)

> **Datum:** 2026-04-27
> **Branch:** `feature/v1.4.10-cost-guardrail-budget`
> **HEAD (parent):** `8541857` (feat(sprint-n): S122 — pre-flight cost guardrail + structured refusal)
> **Port:** API 8102 | UI 5173
> **Elozo session:** S122 — `CostPreflightGuardrail` + `CostEstimator` + `CostGuardrailRefused` + settings + 3 enforcement points (pipeline runner / rag_engine / models/client) + `/api/v1/costs` 429 handler. +24 unit / +3 integration tests (2089 -> 2113 unit baseline). Feature-flag gated, DRY_RUN default; Alembic head unchanged (045).
> **Terv:** `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` S3 S123; STOP §5.2; rollback §7.
> **Session tipus:** UI — React 19 + Tailwind v4 + Vite admin page + 2 Playwright E2E. Untitled UI components + real API.

---

## KONTEXTUS

### Honnan jottunk (S122)
- Pre-flight guardrail shipped behind `AIFLOW_COST_GUARDRAIL__ENABLED=false` / `...__DRY_RUN=true`. Three wiring points (`pipeline/runner.py`, `services/rag_engine/service.py`, `models/client.py`) short-circuit when the flag is off — zero DB load for existing tenants until explicitly flipped on.
- `CostGuardrailRefused` mapped to HTTP 429 in `api/app.py` with the full `{refused, tenant_id, projected_usd, remaining_usd, period, reason, dry_run}` payload.
- `TenantBudgetService.get_remaining` (S121) is the single read surface; the admin UI consumes its live projection via `/api/v1/tenants/{id}/budget`.

### Hova tartunk (S123 — admin UI budget dashboard)
Surface the tenant-budget domain in the admin UI. Policy: **CLAUDE.md UI rule — 7 HARD GATES**. Use Untitled UI components + Tailwind v4 + React Aria. Real API, no silent mock.

1. **New page** `aiflow-admin/src/pages-new/BudgetManagement/` (or next to existing cost dashboards — inspect first). Routes into the admin dashboard nav.
2. **Dashboard widgets**:
   - Per-tenant card: `limit_usd`, `used_usd`, `remaining_usd`, `usage_pct` progress bar, `over_thresholds` badge row.
   - Alert threshold editor (chip input, integers 1-100, dedup + sort on blur).
   - Period toggle (daily / monthly) — swaps the GET query param.
   - Enabled toggle + last `updated_at` timestamp.
3. **API wiring** — consume the existing S121 `/api/v1/tenants/{id}/budget` GET/PUT/DELETE. No new endpoints expected.
4. **Journey coverage** — must follow `/ui-journey` → `/ui-api-endpoint` → `/ui-design` → `/ui-page` gates. Tiny page, but the journey doc keeps the contract honest.
5. **Tests**:
   - Component smoke (React Testing Library) — +~5 unit.
   - 2 Playwright E2E: (a) load page, assert badges render real budget; (b) edit thresholds + Save, assert round-trip persisted after reload.
6. **KOTELEZO `/live-test budget-management`** after the page lands — real browser journey via Playwright MCP, report saved under `tests/ui-live/`.

### Jelenlegi allapot
```
27 service | 190 endpoint | 50 DB table | 45 Alembic (head: 045)
2113 unit | 425 e2e (after +2) | ~93 integration | 8 skill | 24 UI page (after S123)
Branch: feature/v1.4.10-cost-guardrail-budget (S122 shipped @ 8541857)
```

---

## ELOFELTETELEK

```bash
git branch --show-current                         # feature/v1.4.10-cost-guardrail-budget
git log --oneline -3                              # HEAD 8541857
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current  # 045 (head)
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2113 pass
cd aiflow-admin && npx tsc --noEmit                # 0 error baseline
docker ps | grep -E 'postgres|redis'               # real services required
```

S121 API reachable:
```bash
curl -s -o NUL -w "%{http_code}\n" http://localhost:8102/api/v1/tenants/acme/budget  # expected 200/404
```

---

## FELADATOK

### LEPES 1 — Journey + API contract (~30 min)

```
Cel:    /ui-journey budget-management → /ui-api-endpoint GET/PUT flow
Fajlok: aiflow-admin/src/journeys/budget_management.md
        (no new backend; S121 endpoint is the whole surface)
```

Document: which tenant list the page pulls from (inspect existing tenant selector — maybe `/api/v1/tenants` or a settings provider), which period is default (daily), which fields are editable (limit_usd, alert_threshold_pct, enabled — NOT tenant_id or period after creation).

### LEPES 2 — Figma design (`/ui-design budget-management`) (~30 min)

Use Untitled UI + Tailwind v4 tokens — no raw hex, no placeholder wireframes. Components to reuse: `Card`, `ProgressBar`, `Badge`, `Chip`, `Switch`, `Input`, `Button`. Verify actually rendered in the target project (check `aiflow-admin/src/components-new/` for existing atoms).

### LEPES 3 — Page scaffold + routing (~60 min)

```
Cel:    render the S121 BudgetView live
Fajlok: aiflow-admin/src/pages-new/BudgetManagement/index.tsx
        aiflow-admin/src/pages-new/BudgetManagement/BudgetCard.tsx
        aiflow-admin/src/pages-new/BudgetManagement/ThresholdEditor.tsx
        aiflow-admin/src/routes.tsx (or App.tsx — whichever defines routes)
```

State shape (mirrors `BudgetView` from `src/aiflow/services/tenant_budgets/contracts.py`):
```ts
type BudgetView = {
  tenant_id: string;
  period: "daily" | "monthly";
  limit_usd: number;
  used_usd: number;
  remaining_usd: number;
  usage_pct: number;
  alert_threshold_pct: number[];
  over_thresholds: number[];
  enabled: boolean;
  as_of: string;
};
```

### LEPES 4 — ThresholdEditor component (~45 min)

- Chip input: type integer 1..100, Enter adds, click X removes.
- Validation: reject duplicates, reject out-of-range, show inline error via React Aria `aria-describedby`.
- Save button disabled when no changes vs. server payload.
- On Save → PUT `/api/v1/tenants/{id}/budget` with `{period, limit_usd, alert_threshold_pct, enabled}` → refetch BudgetView.

### LEPES 5 — Playwright E2E x2 (~45 min)

```
Fajlok: aiflow-admin/tests/e2e/budget-management.spec.ts
```

**E2E 1 — Load + render**
- Seed a `tenant_budgets` row via API (test fixture using the same auth path as existing e2e specs — check `aiflow-admin/tests/e2e/*cost*` specs for precedent).
- Navigate to /budget-management?tenant=... → assert `limit_usd` + `used_usd` + `remaining_usd` + at least one threshold chip render with real values.

**E2E 2 — Edit + persist**
- From loaded state add threshold `75`, remove `95`, click Save.
- Assert PUT returned 200 and refetched view matches the new `[50, 75, 80]`.
- Reload the page; assert the changes persisted (regression guard against optimistic-UI-only updates).

### LEPES 6 — `/live-test budget-management` (~15 min)

Browser journey via Playwright MCP per `CLAUDE.md` rule. Save report at `tests/ui-live/budget-management.md`. KOTELEZO — nem skippable UI session-ben.

### LEPES 7 — Validacio + commit

```bash
cd aiflow-admin && npx tsc --noEmit && cd ..
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # still 2113+
cd aiflow-admin && npx playwright test budget-management --reporter=line && cd ..
git add aiflow-admin/src/pages-new/BudgetManagement \
        aiflow-admin/src/journeys/budget_management.md \
        aiflow-admin/src/routes.tsx \
        aiflow-admin/tests/e2e/budget-management.spec.ts \
        tests/ui-live/budget-management.md
git commit -m "feat(sprint-n): S123 — admin UI budget dashboard + alert threshold editor + 2 Playwright E2E"
/session-close S123
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. **UI cannot render real-time with Redis down** (plan §5.2) — dashboard must be DB-direct, never Redis-dependent. If the existing admin data layer hard-depends on Redis for tenant budget display, halt and refactor.
2. **Figma quality gate fails** — placeholder wireframes or raw hex in components. Re-design per `feedback_figma_quality.md`.
3. **Tenant selector missing** — if the admin UI has no tenant-picker surface, S123 must not invent one; pause and split out a selector session.
4. **New Alembic migration needed** — out of scope for S123 (S121 shipped the only migration this sprint).

**SOFT (proceed with note):**
1. 2073 pre-existing E2E already include a 'cost dashboard' page that partially overlaps — document the overlap in retro, do not retire the old page.
2. React 19 + Untitled UI + React Aria triple is still novel; if any component needs a workaround (e.g. Aria chip + Untitled UI input composition), ship it but flag in retro.

---

## NYITOTT (cross-sprint, carried)

- Sprint M follow-ups: live rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC example.
- Resilience `Clock` seam — deadline 2026-04-30 (still xfails).
- BGE-M3 weight cache as CI artifact.
- Azure OpenAI Profile B live (credits pending).
- Rebase Sprint N onto `main` once PR #17 (Sprint M) merges.
- S122 soft follow-ups: eval / promptfoo-safe blanket bypass flag still not added (by design); litellm pricing table coverage audit deferred to Sprint-N retro.

---

## SESSION VEGEN

```
/session-close S123
```

Utana: `/clear` -> `/next` -> S124 (Sprint N close — PR cut, retro, tag `v1.4.10`, CLAUDE.md numbers).
