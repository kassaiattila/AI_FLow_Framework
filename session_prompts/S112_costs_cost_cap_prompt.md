# AIFlow v1.4.8 Sprint L — Session 112 Prompt (S112 — Costs.tsx + PolicyEngine cost_cap)

> **Datum:** 2026-04-24 (tervezett folytatas)
> **Branch:** `feature/v1.4.8-monitoring-cost` — folytatas S111 commit `0351e6f` utan.
> **HEAD prereq:** `0351e6f feat(observability): S111 — Langfuse trace drill-down + span-metrics`. Fallback: ha a branch nincs checkout-olva, `git checkout feature/v1.4.8-monitoring-cost`.
> **Port:** API 8102 | Frontend Vite 5173
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint L (S112 row — `Costs.tsx` + `CostAttribution` contract + `PolicyEngine.cost_cap`).
> **Session tipus:** IMPLEMENTATION — backend policy enforcement + UI. Code risk: MEDIUM (uj 429 return path az Extractor + Embedder providernel), process risk: LOW.

---

## KONTEXTUS

### Honnan jottunk (S111 DONE)

- S111 (Sprint L opener) DONE `0351e6f` — Langfuse trace drill-down + span-metrics 5/5 integration PASS.
- `GET /api/v1/runs/{run_id}/trace` + `GET /api/v1/monitoring/span-metrics` uj endpointok.
- `TraceTree.tsx` + Runs/RunDetail/Monitoring oldalak kibovitve.
- `workflow_runs.trace_id/trace_url` mar schema-ban (nincs uj Alembic).

### Hova tartunk — S112 scope

Cel: **cost-cap enforcement** — `PolicyEngine.cost_cap` a ProviderRegistry Extractor + Embedder hivasoknal megszakitja a futast HTTP 429-cel ha a running cost > cap. Plusz `Costs.tsx` UI hogy a user lassa tenant szintu aggregatumot.

**Terv (replan §4 Sprint L):**

| Session | Scope | Acceptance |
|---|---|---|
| **S112 (this)** | `Costs.tsx` + `CostAttribution` Pydantic contract + `PolicyEngine.cost_cap`. | Cost cap integration test: 2 call, masodik 429-cel rebbenti be. |
| **S113** | Cross-UC regression pack: UC1 + UC2 + UC3 CI profilban ≤10 min. PR + tag `v1.4.8`. | CI profil <10 min GREEN. |

### Jelenlegi allapot (feature/v1.4.8-monitoring-cost @ 0351e6f)

```
27 service | 188 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1995 unit | 72+ integration | 420 E2E (413 + 4 UC3 + 3 S111 Monitoring)
8 skill | 24+ UI oldal (Runs + Monitoring S111-ben trace-UI-vel kibovitve)
Sprint L S111 DONE | S112 START
```

---

## ELOFELTELEK

```bash
git branch --show-current            # feature/v1.4.8-monitoring-cost
git log --oneline -3                  # 0351e6f S111 elso sor
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
cd aiflow-admin && npx tsc --noEmit && cd ..
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov   # 1995 pass
```

---

## FELADATOK

### LEPES 1 — Discovery (readonly ~15 min)

```bash
grep -rn "class PolicyEngine" src/aiflow/policy/ 2>&1 | head -5
grep -rn "cost_cap\|max_cost\|cost_limit" src/aiflow/ 2>&1 | head -20
grep -rn "CostAttribution" src/aiflow/ 2>&1 | head -10
ls aiflow-admin/src/pages-new/Costs.tsx 2>&1
```

Kerdesek:
- `PolicyEngine` jelenleg hol dol el cost-cap-et? (engine.py)
- Van-e mar `CostAttribution` contract? Ha igen: bovitsd. Ha nincs: add a `src/aiflow/contracts/` ala Pydantic v2-vel.
- `Costs.tsx` letezik-e? Mi a mostani tartalma?
- A ProviderRegistry Extractor/Embedder hivasok hol futnak? (`aiflow/providers/extractor/*`, `aiflow/providers/embedder/*`)

### LEPES 2 — Backend: `CostAttribution` contract + cost ledger

**Uj Pydantic contract** (`src/aiflow/contracts/cost_attribution.py`):

```python
class CostAttribution(BaseModel):
    tenant_id: str
    run_id: str | None = None
    skill: str
    provider: str        # extractor | embedder | llm
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    recorded_at: datetime
```

**Alembic 043** (ha meg nincs `cost_attributions` tabla): tenant_id + skill + provider + model + cost_usd + timestamp + indexek (tenant_id, recorded_at DESC).

**Cost ledger repository** (`src/aiflow/state/repository.py` vagy uj `cost_repository.py`): `insert_attribution()` + `aggregate_by_tenant(window_h)`.

### LEPES 3 — `PolicyEngine.cost_cap` enforcement

A `PolicyEngine.pick_extractor()` + `pick_embedder()` elott: olvasd a tenant running cost-jat (last window_h). Ha cap-en tul → `raise CostCapBreached(tenant_id, cap, current)`.

Az API layer (`api/v1/intake.py`, `api/v1/rag_engine.py`) `CostCapBreached`-et `HTTPException(status_code=429, detail=...)`-ra alakitja.

**Integration test** (`tests/integration/test_cost_cap_enforcement.py`):
1. Seed tenant cap = $0.001.
2. Provokalj egy "extract" hivast ami $0.002-be kerult (mockolt cost attribution).
3. Kovetkezo extract hivas → 429 response, detail magyarazza a cap-et.

### LEPES 4 — Frontend: `Costs.tsx`

**Uj/bovitett oldal** `aiflow-admin/src/pages-new/Costs.tsx`:
- KPI cardok: ma / 7 nap / 30 nap cost (per tenant).
- Tabla: provider / model / span_count / cost (az uj `GET /api/v1/costs/by-model?window_h=168` endpoint).
- Cap banner: piros ha running > 80% cap, sarga ha 50-80%.

**Backend** `GET /api/v1/costs/by-model` — a `cost_attributions` tablan osszesiti a running cost-ot. (A `costs_router` mar regisztralva van app.py-ban — bovitsd ki.)

### LEPES 5 — E2E + live-test bovites

- `tests/e2e/test_uc_cost_cap_golden_path.py` — 2 smoke (Costs oldal renderel, 429 path e2e hibauzenet).
- `tests/ui-live/costs.md` — uj journey (Login → /costs → cap banner → breach scenario).

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
cd aiflow-admin && npx tsc --noEmit && cd ..
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/test_cost_cap_enforcement.py -q --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe scripts/export_openapi.py
# CLAUDE.md: 188 → 190 endpoint (costs-by-model + cap-status), 72 → 75 integration, 50 → 51 DB tabla (cost_attributions), 42 → 43 Alembic.
/session-close S112
```

---

## STOP FELTETELEK

**HARD:**
1. `CostAttribution` schema konfliktus mar letezo contract-tal → architect agent.
2. Alembic 043 migration `cost_attributions` tablara — ellenorizd ha van mar hasonlo (costs tabla?), ne duplaszd.
3. `PolicyEngine` thread-safety — ha cost query per-request N+1 DB call, cache-reteg kell.

**SOFT:**
1. Cap breach banner Untitled UI variant hianyzik → minimal Tailwind acceptable.
2. 7 napos aggregatum lassu nagyobb datra → index + partial aggregation, defer S113-ra.

---

## SESSION VEGEN

```
/session-close S112
```

Utana `/clear` es S113 (cross-UC regression pack + tag `v1.4.8`).
