# AIFlow Sprint C — Session 38 Prompt (C2.1–C2.3: RunDetail + Monitoring)

> **Datum:** 2026-04-10
> **Branch:** `feature/v1.4.0-ui-refinement` | **HEAD:** `e34d697`
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S37 — C0+C1 DONE (J4 archive, ConfirmDialog, i18n, J1 invoice flow)
> **Terv:** `01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md` (C2 szekcio)
> **Session tipus:** CODE + UI — RunDetail UJ OLDAL, Dashboard alert, Monitoring restart+auto-refresh
> **Workflow:** RunDetail → route → Dashboard alert → Monitoring restart → auto-refresh → tsc → Commit(ok)

---

## KONTEXTUS

### S37 Eredmenyek (C0+C1 — KESZ)

```
✅ C0.3: 5 J4 oldal archivalva (pages-archive/), sidebar 6 csoport, J4 kartya torolve
✅ C0.1: ConfirmDialog.tsx ujrahasznalhato komponens
✅ C0.2: 22 i18n kulcs (hu+en)
✅ C1.1: Email scan success banner → /documents link
✅ C1.2: Documents summary banner + confidence badge szinekkel
✅ tsc --noEmit 0 error
```

### Sprint C Allapot

```
18 aktiv UI oldal + 5 archiv | 0 uj oldal meg (RunDetail = C2.2)
J1 Invoice: Scan ✅ → Documents(badge) ✅ → Verify ✅ → Export ✅
J5 Pipeline: Runs ✅ → RunDetail ❌ (NEM LETEZIK) → Retry ✅
J2a Monitoring: restart ❌, auto-refresh ❌
```

### API Endpointok (mar leteznek — NINCS backend munka)

```
GET  /api/v1/runs                    — lista (RunItem[]: run_id, workflow_name, skill_name, status, started_at, total_duration_ms, total_cost_usd, steps[])
GET  /api/v1/runs/{run_id}           — reszletek (RunItem: steps[] tartalommal)
GET  /api/v1/runs/stats              — statisztikak
POST /api/v1/pipelines/{id}/execute  — pipeline ujrainditas
GET  /api/v1/admin/health            — service health lista
GET  /api/v1/admin/metrics           — service metrikak
POST /api/v1/admin/services/{name}/restart — service restart (mar letezik!)
```

---

## S38 FELADATOK: 5 lepes

### LEPES 1: C2.2 — RunDetail.tsx UJ OLDAL (40 perc)

```
Cel: Uj oldal /runs/:id — step-level naplo, retry, export.
Ez a Sprint C fo uj oldala.

Fajl: aiflow-admin/src/pages-new/RunDetail.tsx (UJ)

API: GET /api/v1/runs/{run_id}
Response: RunItem { run_id, workflow_name, skill_name, status, started_at, completed_at, total_duration_ms, total_cost_usd, steps: StepRunItem[] }
StepRunItem: { step_name, status, duration_ms, cost_usd, model_used, input_tokens, output_tokens, error }

Layout (Untitled UI style):

┌─────────────────────────────────────────────────────────────┐
│ ← Vissza    Run: {run_id.substr(0,8)}    {StatusBadge}      │
│                                                              │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│ │ Pipeline │  │ Duration │  │ Cost     │  │ Started  │     │
│ │ {name}   │  │ {dur}s   │  │ ${cost}  │  │ {date}   │     │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                              │
│ Step Log:                                        [Actions]   │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ # │ Step          │ Status │ Dur.  │ Model     │ Cost  │  │
│ │ 1 │ classify      │  ✅    │ 1.1s  │ gpt-4o-m. │ $0.01│  │
│ │ 2 │ extract       │  ✅    │ 0.8s  │ gpt-4o-m. │ $0.00│  │
│ │ 3 │ route         │  ❌    │ 1.3s  │ gpt-4o    │ $0.00│  │
│ │   │ Error: "Timeout connecting to..."                   │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                              │
│ [Retry Pipeline ▶]  [Export JSON 📥]                         │
└─────────────────────────────────────────────────────────────┘

Implementacio:

A) useParams + useApi:
  const { id } = useParams<{ id: string }>();
  const { data, loading, error, refetch } = useApi<RunItem>(`/api/v1/runs/${id}`);

B) KPI sav (4 kartya):
  - Pipeline/Skill nev
  - Duration (total_duration_ms / 1000).toFixed(1) + "s"
  - Cost ($total_cost_usd.toFixed(3))
  - Started (toLocaleString)

C) Step log tabla:
  data.steps.map((step, i) => ...)
  - # (index+1)
  - step_name
  - status badge (szin: completed=green, running=blue, failed=red)
  - duration_ms → sec
  - model_used ?? "—"
  - cost_usd → $
  - Ha step.error → extra sor piros hatterrel az error szoveggel

D) Action gombok:
  [← Vissza]: navigate("/runs")
  [Retry Pipeline]: ConfirmDialog → POST /api/v1/pipelines/{pipeline_id}/execute → refetch
    - pipeline_id-t a data.workflow_name-bol kell kiszedni (vagy fallback a run-bol)
    - Ha nincs pipeline_id, a gomb disabled
  [Export JSON]: JSON.stringify(data, null, 2) → Blob → download

E) i18n kulcsok (LEPES 4-ben hozzaadni):
  aiflow.runDetail.title:        "Run reszletek" / "Run Details"
  aiflow.runDetail.backToRuns:   "Vissza" / "Back"
  aiflow.runDetail.pipeline:     "Pipeline" / "Pipeline"
  aiflow.runDetail.retryPipeline: "Ujraindit" / "Retry"
  aiflow.runDetail.retryConfirm: "Biztosan ujrainditod ezt a pipeline-t?" / "Retry this pipeline?"
  aiflow.runDetail.exportJson:   "Export JSON" / "Export JSON"
  aiflow.runDetail.stepLog:      "Lepes naplo" / "Step Log"
  aiflow.runDetail.stepName:     "Lepes" / "Step"
  aiflow.runDetail.model:        "Modell" / "Model"
  aiflow.runDetail.tokens:       "Token" / "Tokens"
  aiflow.runDetail.error:        "Hiba" / "Error"

tsc ellenorzes
```

---

### LEPES 2: C2.2 — Route regisztracio (5 perc)

```
Cel: /runs/:id route bekotes

Fajl: aiflow-admin/src/router.tsx

A) Import hozzaadas:
  import { RunDetail } from "./pages-new/RunDetail";

B) Route hozzaadas (az Operations szekcioban, { path: "runs", ... } utan):
  { path: "runs/:id", element: <RunDetail /> },

C) Runs.tsx: sor kattintas → navigate
  Fajl: aiflow-admin/src/pages-new/Runs.tsx
  - onRowClick hozzaadasa a DataTable-hez:
    onRowClick={(item) => navigate(`/runs/${item.run_id}`)}
  - useNavigate import hozzaadasa

tsc ellenorzes
```

---

### LEPES 3: C2.1 — Dashboard Alert Banner Finomitas (10 perc)

```
Cel: A Dashboard.tsx "Pipeline running" es "service DOWN" bannerek
     mar leteznek (S37-ben olvastam). Ellenorizni:

A) Pipeline running banner: ✅ mar mukodik (241-251. sor)
B) Service DOWN banner: ✅ mar mukodik (228-238. sor)

Teendo: NINCS valtozas, ha mindketto rendben.
Ha megis kell finomitas (pl. a running banner linkje Runs helyett RunDetail):
  - onClick: navigate(`/runs/${runningPipelines[0].run_id}`) a legfrissebb running run-ra

Valoszinuleg SKIP — ellenorizni es tovabblepni.
```

---

### LEPES 4: C2.3 — Monitoring Restart + Auto-refresh (25 perc)

```
Cel: Monitoring oldalon restart gomb + auto-refresh interval.

Fajl: aiflow-admin/src/pages-new/Monitoring.tsx

A) Restart gomb — minden service kartyara:
  - Import: ConfirmDialog from "../components-new/ConfirmDialog"
  - Import: fetchApi from "../lib/api-client"
  - State: restartTarget (string | null), restarting (boolean)
  
  Gomb (a service kartya aljara):
    <button onClick={() => setRestartTarget(svc.service_name)} ...>
      ↻ Restart
    </button>
  
  Dialog:
    <ConfirmDialog
      open={!!restartTarget}
      title={translate("aiflow.monitoring.restartConfirm").replace("{{service}}", restartTarget ?? "")}
      message={`Service: ${restartTarget}`}
      variant="danger"
      loading={restarting}
      confirmLabel="Restart"
      onConfirm={handleRestart}
      onCancel={() => setRestartTarget(null)}
    />
  
  handleRestart:
    await fetchApi("POST", `/api/v1/admin/services/${restartTarget}/restart`);
    setRestartTarget(null);
    refetch();

B) Auto-refresh — interval valaszto:
  State: autoRefresh (number | null) — 10000, 30000, 60000, null
  
  useEffect:
    if (!autoRefresh) return;
    const timer = setInterval(() => refetch(), autoRefresh);
    return () => clearInterval(timer);
  
  UI (a PageLayout actions-be, a Refresh gomb melle):
    <select
      value={autoRefresh ?? ""}
      onChange={(e) => setAutoRefresh(e.target.value ? Number(e.target.value) : null)}
      className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs ..."
    >
      <option value="">Off</option>
      <option value="10000">10s</option>
      <option value="30000">30s</option>
      <option value="60000">60s</option>
    </select>

tsc ellenorzes
```

---

### LEPES 5: i18n + tsc + Commit (10 perc)

```
5a) i18n kulcsok hozzaadasa (hu.json + en.json):
    - runDetail.* kulcsok (LEPES 1 E szekciojaban felsorolva)

5b) tsc:
    cd aiflow-admin && npx tsc --noEmit → 0 error

5c) Manualis check (ha app fut):
    - /runs: kattintas sor → /runs/:id → RunDetail megjelenik
    - RunDetail: step tabla, KPI kartyak, Retry gomb, Export JSON
    - ← Vissza gomb → /runs
    - Dashboard: J1 kartya → /emails (nem /documents)
    - Dashboard: 3 journey kartya (nem 4)
    - /monitoring: Restart gomb → ConfirmDialog → POST → refetch
    - /monitoring: Auto-refresh dropdown (10s/30s/60s/off)

5d) Commit:
    git add aiflow-admin/src/pages-new/RunDetail.tsx \
            aiflow-admin/src/pages-new/Runs.tsx \
            aiflow-admin/src/pages-new/Monitoring.tsx \
            aiflow-admin/src/router.tsx \
            aiflow-admin/src/locales/hu.json \
            aiflow-admin/src/locales/en.json
    
    Commit message:
    feat(ui): Sprint C S38 — C2.1-C2.3 RunDetail page + Monitoring restart + auto-refresh

Gate: tsc 0 error, RunDetail rendel, Monitoring restart mukodik
```

---

## KORNYEZET ELLENORZES

```bash
# Jelenlegi allapot
git branch --show-current     # → feature/v1.4.0-ui-refinement
git log --oneline -3           # → e34d697 (S37 commit)

# API endpoint letezik?
curl -s http://localhost:8102/api/v1/runs?limit=1 2>/dev/null | head -3
curl -s http://localhost:8102/api/v1/runs/test-id 2>/dev/null | head -3

# Modositando fajlok
wc -l aiflow-admin/src/pages-new/Runs.tsx           # → 59 sor
wc -l aiflow-admin/src/pages-new/Monitoring.tsx      # → 74 sor
wc -l aiflow-admin/src/router.tsx                    # → ~97 sor

# RunItem interface referencia (backend)
grep -n "class RunItem\|class StepRunItem" src/aiflow/api/v1/runs.py

# Restart endpoint letezik?
grep -rn "restart" src/aiflow/api/v1/admin.py | head -5
```

---

## MEGLEVO KOD REFERENCIAK

```
# Sprint C terv:
01_PLAN/65_SPRINT_C_UI_JOURNEY_FIRST_PLAN.md   — C2 szekcio: RunDetail + Monitoring

# API modell:
src/aiflow/api/v1/runs.py                       — RunItem, StepRunItem, GET /{run_id}
src/aiflow/api/v1/admin.py                      — restart endpoint

# Minta oldalak:
aiflow-admin/src/pages-new/PipelineDetail.tsx    — hasonlo detail oldal minta (← Back, KPI, tabla)
aiflow-admin/src/pages-new/DocumentDetail.tsx    — masik detail oldal minta
aiflow-admin/src/pages-new/Runs.tsx              — jelenlegi lista (DataTable)

# Ujrahasznalhato komponensek:
aiflow-admin/src/components-new/ConfirmDialog.tsx — S37-ben keszult, Monitoring restart-hoz
aiflow-admin/src/layout/PageLayout.tsx            — standard page wrapper

# Modositando fajlok:
aiflow-admin/src/pages-new/RunDetail.tsx  (UJ)
aiflow-admin/src/pages-new/Runs.tsx       (onRowClick navigate)
aiflow-admin/src/pages-new/Monitoring.tsx (restart + auto-refresh)
aiflow-admin/src/router.tsx               (runs/:id route)
aiflow-admin/src/locales/hu.json + en.json (runDetail.* kulcsok)
```

---

## SPRINT C UTEMTERV

```
S37: C0+C1 — J4 archive + infra + J1 Invoice flow       ✅ DONE
S38: C2.1-C2.3 — RunDetail UJ OLDAL + Monitoring         ← EZ A SESSION
S39: C2.4-C2.6 — Quality + Admin CRUD + Audit
S40: C4 — RAG chunk search
S41: C5 — Sidebar final + cleanup + polish
S42-S44: C6 — Journey E2E validacio (5 journey)
S45: C7 — Regresszio + v1.4.0 tag
```

---

*Sprint C masodik session: S38 = C2.1-C2.3 (RunDetail UJ OLDAL + Monitoring restart/auto-refresh)*
