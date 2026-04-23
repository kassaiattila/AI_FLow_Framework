# Journey — Budget Management (Sprint N / S123)

Admin dashboard page surfacing the per-tenant LLM cost budget shipped by Sprint N
S121 (`tenant_budgets` table, `TenantBudgetService`) and read live by the S122
pre-flight guardrail.

## Actor

- Ops/admin user authenticated via the existing `AuthMiddleware` JWT flow.
  The page is reachable from the `Monitoring` sidebar group alongside `/costs`.

## Goal

Let the operator:

1. Pick a tenant (free-text input, same `[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}` pattern
   as `/emails/intent-rules`) or navigate via deep link `?tenant=acme`.
2. Read the live projection (`limit_usd`, `used_usd`, `remaining_usd`,
   `usage_pct`, `over_thresholds`) for both `daily` and `monthly` periods in one
   shot — no period toggle needed because the backend `GET .../budget` endpoint
   returns both rows.
3. Edit `limit_usd`, `alert_threshold_pct`, `enabled` per period and persist via
   `PUT`.

Out of scope for S123: creating a new tenant from the UI (no tenant registry
endpoint exists), deleting budgets (backend supports DELETE but not exposed
here until a destructive-action pattern exists).

## API contract (S121 endpoints — no new surface)

| Verb   | Path                                              | Request body                                           | Response                                                  |
|--------|---------------------------------------------------|--------------------------------------------------------|-----------------------------------------------------------|
| GET    | `/api/v1/tenants/{tenant_id}/budget`              | —                                                      | `TenantBudgetGetResponse[]` (one entry per period)        |
| GET    | `/api/v1/tenants/{tenant_id}/budget/{period}`     | —                                                      | `TenantBudgetGetResponse` or 404                          |
| PUT    | `/api/v1/tenants/{tenant_id}/budget/{period}`     | `{ limit_usd, alert_threshold_pct, enabled }`          | `TenantBudgetGetResponse` (persisted + live view refetch) |
| DELETE | `/api/v1/tenants/{tenant_id}/budget/{period}`     | —                                                      | `{ deleted: true }` or 404 (not used by S123 UI)          |

`TenantBudgetGetResponse`:

```ts
{
  budget: {
    id?: string;
    tenant_id: string;
    period: "daily" | "monthly";
    limit_usd: number;
    alert_threshold_pct: number[];
    enabled: boolean;
    created_at?: string;
    updated_at?: string;
  };
  view: {
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
}
```

- `period` and `tenant_id` are immutable after the first upsert (baked into the
  URL path) — the UI never PUTs a different period.
- `alert_threshold_pct` ints must be in `[1, 100]`. Backend validator dedupes
  and sorts; UI mirrors that contract to avoid pointless diff toasts.

## UX

- **Tenant input** — free-text + pattern validator; Enter or "Load" button
  re-routes to `/budget-management?tenant=<id>`. 404 on GET is an empty state
  with "No budgets for this tenant yet — upsert one below."
- **Budget card** (rendered per period, daily + monthly side by side):
  - Header: `Daily` / `Monthly` + `enabled` switch + last `updated_at`.
  - KPI row: `used_usd / limit_usd`, `remaining_usd`, `usage_pct` with a
    `ProgressBar` colored by the highest crossed threshold
    (ok < 50% / warning >= 50% / critical >= 80% / exceeded >= 100%).
  - Thresholds: `over_thresholds` chips rendered as red pills, other
    thresholds as gray.
  - Form:
    - `limit_usd` number input (step 0.01, min 0).
    - `alert_threshold_pct` `ThresholdEditor` (chip input, 1..100, dedup).
    - Save button disabled until the form diverges from the server payload.
- **Persistence** — Save calls `PUT`, then swaps the card with the returned
  projection. Inline error banner on non-2xx (same pattern as IntentRules).

## Source tagging

The admin UI lives behind `fetchApi` which forwards the JWT; backend tags its
own `source` field in the response — but `TenantBudgetGetResponse` does not
include one. S123 follows the Costs page pattern and passes `source="live"`
explicitly to `PageLayout` so the DB-direct live/demo toggle stays on.

## STOP conditions respected (plan §5.2)

- No Redis reads — `TenantBudgetService.get_remaining` runs a single SQL query
  against the live `cost_records` aggregator; the page never depends on the
  notification Redis/Valkey instance.
- No new Alembic migration (Sprint N is one-migration-per-sprint; S121 already
  shipped 045).
