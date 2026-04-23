# /live-test — budget-management (Sprint N / S123)

- **Run date:** 2026-04-27 (session 123, HEAD `5526bbf` + S123 working tree)
- **Runner:** Playwright MCP (browser_navigate / browser_click / browser_type /
  browser_evaluate / browser_snapshot)
- **Target:** `http://localhost:5173/#/budget-management?tenant=live-s123`
- **API:** `http://localhost:8102` (uvicorn, factory mode, openapi exposes
  `/api/v1/tenants/{tenant_id}/budget[/{period}]`)
- **Services:** PostgreSQL (5433, Docker), Redis (6379, Docker), Langfuse Cloud
  (SaaS — not the S118 self-hosted overlay, sufficient for this journey)

## Journey

1. **Login** — `/#/login` → filled `admin@aiflow.local` / `AiFlowDev2026` → Bejelentkezes.
   Sidebar nav rendered, confirming auth + `aiflow_token` in localStorage.
2. **Seed** — `PUT /api/v1/tenants/live-s123/budget/daily` with
   `{ limit_usd: 15.5, alert_threshold_pct: [50, 80, 95], enabled: true }` →
   200 with full `TenantBudgetGetResponse` (persisted row + live projection,
   `used_usd: 0`, `remaining_usd: 15.5`, `usage_pct: 0`).
3. **Navigate** — `/#/budget-management?tenant=live-s123`. Sidebar group
   **Monitoring → Tenant koltsegvetesek** visible + active. Page header
   "Tenant koltsegvetesek" rendered with `Live` status badge (source='live').
4. **Render assertions** — Daily card populated:
   - Felhasznalt `$0.0000 / $15.5000`
   - Hatralevo `$15.5000`
   - Usage `0.0%`
   - Chip row `[50%, 80%, 95%]`
   - Limit input prefilled `15.5`
   - Save button disabled (no diff).
   Monthly card rendered empty state
   ("Meg nincs monthly kuszob ennek a tenant-nek.") + default thresholds in the
   editor, correctly hidden from the live projection until first save.
5. **Edit thresholds** — clicked the `×` on the `95` chip, typed `75` in the
   ThresholdEditor input + Enter. Live DOM verified via page.evaluate:
   `chips = [50, 75, 80]`, Save now enabled.
6. **Persist** — clicked `Mentes`. PUT round-trip OK; "Elmentve." confirmation
   appeared.
7. **Hard reload** — `page.goto` the same URL. Chips re-render as `[50, 75, 80]`
   from the fresh GET; the live threshold-bar widget (`data-testid="budget-over-daily"`)
   shows the same three percentages. Regression guard passed (no
   optimistic-only state).
8. **Cleanup** — `DELETE /api/v1/tenants/live-s123/budget/daily` → 200.

## Observations

- No new console errors attributable to S123. Four JS errors surfaced in the
  session console:
  - 1× 404 on the initial seed, pre-dates the API restart in this session
    (the Sprint N `tenant_budgets` router was not yet registered in the stale
    v1.4.4 API process — restarting uvicorn with `--factory` picked up the
    S121 router at commit `483bd86`).
  - 3× 500 on `/api/v1/notifications/in-app/unread-count` — pre-existing,
    unrelated to S123 (notification subsystem is Sprint M territory). Flagged
    as a follow-up, but does not block this report.
- All S123 `data-testid` hooks observed live — matching the Python Playwright
  spec in `tests/e2e/test_budget_management.py`.
- Untitled UI + Tailwind tokens render correctly (brand color progress bar,
  chip pills with ring-brand-200 borders, ring-inset badges). No raw hex seen
  in the rendered DOM outside the standard Tailwind utility classes.

## Result

`PASS` — golden path + edit round-trip + reload persistence all green in a
real browser against a real FastAPI + PostgreSQL stack. Journey mirrors the
spec in `aiflow-admin/src/journeys/budget_management.md`.
