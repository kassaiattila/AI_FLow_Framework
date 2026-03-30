# AIFlow - Frontend Architektura

> **STATUS (2026-03-30): DONTES MEGTORTENT — Next.js 16 + shadcn/ui**
>
> Az alabbi dokumentum az eredeti ertekelest tartalmazza. A vegso dontes:
> **Next.js 16 + React 19 + TypeScript + shadcn/ui** (lasd `aiflow-ui/`).
> A Reflex opcio nem valasztatott. Az implementacio allapota:
> - Dashboard, /costs, /runs oldalak — KESZ
> - 4 skill viewer (invoice, email, rag-chat, diagram) — KESZ (mock data)
> - FastAPI backend endpoints (runs, costs, skills) — KESZ
> - Lasd: `33_PRODUCTION_UI_PLAN.md` a reszletekert.

## Technologiai Opciok Ertekelese (torteneti referencia)

### A Claude Code-bol Iranyitott Fejlesztes Szempontja

A frontend technologiavaasztasnal **kiemelt szempont** hogy Claude Code hatekonyan
tudja-e fejleszteni es karbantartani. Ez azt jelenti:
- **Tiszta, tipusos kodstruktura** (Claude jol ert hozza)
- **Konzisztens mintak** (ne kelljen kontextust valtani nyelvek kozott)
- **Jol dokumentalt API** (Claude tudjon valid kodot generalni)
- **Tesztelheto** (Claude irhat teszteket is)

---

## Opcio A: Reflex (Python Full-Stack) - **AJANLOTT**

**GitHub:** 25.7k+ stars, YC-backed, pre-v1.0 (v0.8), heti release-ek
**Hasznalat:** World Bank, Credit Agricole, Man Group (Fortune 500)

### Miert Reflex az elso ajanlott?

| Szempont | Ertekeles |
|----------|-----------|
| **Claude Code fejlesztheto** | **Kivaló** - teljes egeszeben Python, tipusos, deklarativ |
| **Professzionalis UI** | **Kivaló** - Radix UI komponensek, React minoseget ad Python-bol |
| **Komponensek** | 60+ beepitett (tablak, chartok, form-ok, modals) |
| **FastAPI integracio** | Nativ - maga Reflex FastAPI-t hasznal backend-kent |
| **Real-time** | Beepitett WebSocket, automatikus state sync |
| **Auth** | Ecosystem: reflex-local-auth, Azure AD, Google, Okta |
| **Deployment** | Docker, K8s, Reflex Cloud |
| **Team fit** | Python-only team -> nincs JS/TS learning curve |

### Architektura

```
Reflex App (Python)
    |
    +-- Frontend: React/Next.js (automatikusan kompilalt Python-bol!)
    +-- Backend: FastAPI + Uvicorn (beepitett)
    +-- Kommunikacio: WebSocket (automatikus state sync)
    +-- AIFlow API: ugyanabban a processz-ben VAGY kulon service
```

### Pelda Kod (Claude Code altal irhato)

```python
import reflex as rx

class DashboardState(rx.State):
    """Operator Dashboard state."""
    workflows: list[dict] = []
    total_runs: int = 0
    success_rate: float = 0.0

    async def load_metrics(self):
        # AIFlow API hivas
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/v1/admin/metrics/overview")
            data = resp.json()
            self.total_runs = data["total_runs"]
            self.success_rate = data["success_rate"]

def dashboard_page() -> rx.Component:
    return rx.box(
        rx.heading("AIFlow Dashboard", size="6"),
        rx.hstack(
            kpi_card("Osszes futtatas", DashboardState.total_runs),
            kpi_card("Sikeresseg", DashboardState.success_rate, suffix="%"),
            spacing="4",
        ),
        rx.data_table(
            data=DashboardState.workflows,
            columns=["name", "status", "duration_ms", "cost_usd"],
            sort=True, search=True, pagination=True,
        ),
        on_mount=DashboardState.load_metrics,
    )

def kpi_card(title: str, value: rx.Var, suffix: str = "") -> rx.Component:
    return rx.card(
        rx.text(title, size="2", color="gray"),
        rx.heading(rx.text(value, suffix), size="7"),
    )
```

### Korlatozasok
- Pre-v1.0 (v0.8) - breaking change lehetseges (de stabilizalodik)
- Kisebb ecosystem mint React
- NPM fuggoseg a build-hez (de csak build time, nem fejleszteskor)

---

## Opcio B: NiceGUI (Python Lightweight)

**GitHub:** ~10k stars, stabil, Quasar/Vue alap

### Miert NiceGUI alternativa?

| Szempont | Ertekeles |
|----------|-----------|
| **Claude Code fejlesztheto** | **Jo** - Python, de kevesbe strukturalt mint Reflex |
| **Professzionalis UI** | **Kozepes** - Quasar komponensek, de kevesbe modern mint Radix |
| **Komponensek** | Kevesebb mint Reflex, de megfelelo |
| **FastAPI integracio** | **Kivaló** - kozvetlenul mountolhato |
| **Real-time** | Beepitett WebSocket |
| **Auth** | Nincs beepitett, custom kell |
| **Deployment** | Egyetlen container az API-val |
| **Team fit** | Python-only, nagyon egyszeru |

### Mikor NiceGUI-t valasszuk?
- Ha a UI nem kritikus (belso admin tool)
- Ha a legegyszerubb megoldas kell
- Ha az egyseg (egy process, egy port) fontosabb mint a UI minoseg

### Korlatozasok
- Kevesbe professzionalis UI mint Reflex vagy JS framework-ok
- Kisebb community
- Limitalt komponens keszlet osszetett UI-okhoz

---

## Opcio C: Next.js + TypeScript (Professzionalis JS)

**A klasszikus vallalati valasztas - maximalis UI minoseg**

### Miert JS/TS alternativa?

| Szempont | Ertekeles |
|----------|-----------|
| **Claude Code fejlesztheto** | **Kivaló** - Claude kiválóan ert a React/Next.js/TS-hez |
| **Professzionalis UI** | **Kivaló** - shadcn/ui, Tailwind, vegtelen komponens ecosystem |
| **Komponensek** | **Vegtelen** - npm ecosystem, TanStack Table, Recharts, etc. |
| **FastAPI integracio** | REST API kliens (kulon service) |
| **Real-time** | WebSocket/SSE kliens |
| **Auth** | NextAuth.js - komplett auth megoldas |
| **Deployment** | Kulon container (Vercel, Docker) |
| **Team fit** | TS/JS tudasra van szukseg |

### Architektura

```
Next.js Frontend (TypeScript)         FastAPI Backend (Python)
    |                                      |
    +-- shadcn/ui komponensek              +-- AIFlow API v1
    +-- TanStack Table/Query               +-- WebSocket endpoint
    +-- Recharts/Tremor                    +-- JWT auth
    +-- NextAuth.js                        |
    |                                      |
    +------------- REST + WS -------------+
```

### Pelda Kod (Claude Code altal irhato)

```tsx
// components/workflow-dashboard.tsx
"use client"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DataTable } from "@/components/ui/data-table"

export function WorkflowDashboard() {
  const { data: metrics } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetch("/api/v1/admin/metrics/overview").then(r => r.json()),
    refetchInterval: 5000,
  })

  return (
    <div className="grid gap-4 md:grid-cols-4">
      <KPICard title="Osszes futtatas" value={metrics?.total_runs ?? 0} />
      <KPICard title="Sikeresseg" value={`${metrics?.success_rate ?? 0}%`} />
      <DataTable columns={columns} data={metrics?.recent_runs ?? []} />
    </div>
  )
}
```

### Claude Code Kompatibilitas
- Claude **kivaloan** ert a Next.js + TypeScript + React fejleszteshez
- Generalni tud: komponenseket, API klienst, teszteket, Tailwind stilusokat
- shadcn/ui kodgeneralasa jol dokumentalt es Claude-barát
- **Kihivas:** Ket nyelv (Python backend + TS frontend) -> kontextus valtas

### Mikor Next.js-t valasszuk?
- Ha a UI minoseg **uzleti kritikus** (ugyfelekenk megjeleno felulet)
- Ha van vagy lesz JS/TS kepesseg a teamben
- Ha a leggazdagabb komponens ecosystem kell
- Ha hosszu tavon **SaaS** produktumot tervez a ceg

### Korlatozasok
- Kulon build pipeline (npm, node_modules)
- Kulon deployment (2 container: frontend + backend)
- Ket technologiai stack karbantartasa
- De: Claude Code **mindkettot** tudja kezelni

---

## Osszehasonlito Tablazat

| Szempont | Reflex | NiceGUI | Next.js+TS |
|----------|--------|---------|------------|
| **Nyelv** | Python only | Python only | TypeScript + Python |
| **UI Minoseg** | Profi (Radix UI) | Kozepes (Quasar) | Legjobb (vegtelen) |
| **Claude Code DX** | Kivaló | Jo | Kivaló (2 nyelven) |
| **Komponensek** | 60+ | 30+ | Vegtelen (npm) |
| **FastAPI integracio** | Nativ | Nativ mount | REST kliens (kulon) |
| **Real-time** | Auto WS | Auto WS | Manual WS/SSE |
| **Auth** | Ecosystem | Custom | NextAuth.js |
| **Deployment** | 1 container | 1 container | 2 container |
| **Team Learning** | Minimalis | Minimalis | JS/TS sukseg |
| **Production proof** | Fortune 500 | Kisebb | Iparagi standard |
| **Stars** | 25.7k | ~10k | 130k+ (Next.js) |
| **Eretts** | Pre-v1.0 | Stabil | Stabil (v15+) |

---

## Ajanlott Strategia: Fazisolt Megkozelites

### Fazis 1-4 (0-12 het): **Reflex**
- Gyors fejlesztes Python-only team-mel
- Claude Code hatékonyan fejleszti (tiszta Python)
- Operator Dashboard + Chat + Developer Portal
- Ha kozben v1.0 megjelenik -> stabilabb alap

### Fazis 5-7 (13-22 het): Dontes a tapasztalatok alapjan

**Ha Reflex megfelel** (valoszinuleg igen belso tool-okhoz):
- Folytatjuk Reflex-szel
- Admin Panel + Reports + production polish

**Ha professzionalisabb UI kell** (ugyfelelnek megjeleno):
- Next.js + TS migracio a kulso feluletre
- Reflex marad belso admin/developer tool-nak
- Ket frontend: Reflex (belso) + Next.js (kulso)

**Ha NiceGUI is eleg** (minimum viable):
- Egyszerubb, kevesebb fejlesztes
- Kozepes UI minoseg, de gyorsabb delivery

---

## 5 UI Modul (Framework-Fuggetlen)

Ezek az UI modulok **barmelyik framework-kel** megvalosithatok:

### 1. Operator Dashboard (`/operator/`)
- **KPI kartyak:** aktiv workflow-k, success rate, queue depth, avg cost
- **Job management:** Active/Completed/Failed/DLQ tabok, retry, cancel
- **Skill catalog:** kartya nezet, manifest details
- **Budget overview:** team koltseg progressbar, drill-down
- **Alert management:** P1-P4 alertek, acknowledge, Langfuse link
- Real-time: WebSocket push Event Bus-on keresztul

### 2. Chat Interface (`/chat/`) - RAG skill-ekhez
- **Multi-turn chat:** Markdown rendereles, streaming valasz
- **Forras citacio:** expandable kartyak (dokumentum, oldal, paragrafus, score)
- **Dokumentum feltoltes:** drag-and-drop, ingestion pipeline triggereles
- **Feedback widget:** thumbs up/down + correction -> Langfuse score
- **Streaming:** Token-by-token LLM output WebSocket-en

### 3. Developer Portal (`/developer/`)
- **Workflow DAG vizualizacio:** interaktiv Mermaid diagram
- **Prompt editor:** YAML szerkeszto + "Test Prompt" dialog
- **Prompt promocioo:** dev -> test -> staging -> prod label valtas
- **Evaluation viewer:** teszt eredmenyek tabla + trend chart
- **Langfuse trace explorer:** step timeline + link Langfuse-ba

### 4. Admin Panel (`/admin/`)
- **User/Team CRUD:** tabla + dialog form-ok
- **RBAC matrix:** role vs permission grid
- **Audit log viewer:** szurheto, lapozhato, CSV export
- **System health:** service statusz kartyak

### 5. Business Reports (`/reports/`)
- **Usage stats:** napi futtatasok chart, per-workflow tabla
- **Cost reports:** embedded Grafana VAGY nativ chart
- **SLA compliance:** p50/p95/p99 + target vs actual
- **Auto-gen docs viewer:** workflow dokumentacio rendereles

---

## Authentikacio (Kozos)

```
Browser -> /login -> POST /api/v1/auth/login
  -> JWT token -> HttpOnly cookie (Reflex/NiceGUI) VAGY NextAuth session (Next.js)
  -> Minden page: middleware RBAC check role alapjan
  -> admin: /admin/* | developer: /developer/* | operator: /operator/*
  -> reports + chat: minden bejelentkezett user
```

---

## Konyvtar Struktura

### Reflex Verzio
```
src/aiflow/ui/                    # VAGY kulon repo: aiflow-ui/
    rxconfig.py                   # Reflex konfiguracio
    aiflow_ui/
        __init__.py
        state/
            auth.py               # AuthState (login, session)
            dashboard.py          # DashboardState (metriak)
            jobs.py               # JobState (lista, szures)
            chat.py               # ChatState (uzenet, history)
        pages/
            operator/dashboard.py, jobs.py, alerts.py
            chat/chat.py, history.py
            developer/workflows.py, prompts.py, evaluations.py
            admin/users.py, teams.py, audit.py
            reports/usage.py, costs.py, sla.py
        components/
            dag_viewer.py
            kpi_card.py
            job_table.py
            citation_card.py
            feedback_widget.py
        i18n.py                   # Magyar/Angol
```

### Next.js Verzio
```
frontend/                         # Kulon repo: aiflow-frontend/
    package.json
    next.config.ts
    src/
        app/                      # Next.js App Router
            layout.tsx
            (auth)/login/page.tsx
            operator/dashboard/page.tsx, jobs/page.tsx
            chat/page.tsx
            developer/workflows/page.tsx, prompts/page.tsx
            admin/users/page.tsx, teams/page.tsx
            reports/usage/page.tsx, costs/page.tsx
        components/
            ui/                   # shadcn/ui (auto-generated)
            dag-viewer.tsx
            kpi-card.tsx
            citation-card.tsx
        lib/
            api-client.ts         # AIFlow API TypeScript kliens
            auth.ts               # NextAuth konfig
        hooks/
            use-workflows.ts      # TanStack Query hooks
            use-websocket.ts      # Real-time hook
    Dockerfile
```

---

## Uj API Endpoint-ok (UI-nak)

| Endpoint | Cel | Fazis |
|----------|-----|-------|
| POST /api/v1/auth/login | JWT auth | 5 |
| GET /api/v1/auth/me | Aktualis user info | 5 |
| GET /api/v1/conversations | Chat history | 4 |
| POST /api/v1/feedback | User feedback | 4 |
| POST /api/v1/prompts/{name}/promote | Label promo | 3 |
| POST /api/v1/prompts/{name}/test | Prompt teszt | 3 |
| GET /api/v1/workflows/{name}/docs | Auto-gen docs | 6 |
| POST /api/v1/skills/{skill}/ingest | RAG ingestion | 4 |
| GET /api/v1/admin/metrics/overview | Dashboard KPI-k | 6 |
| GET /api/v1/admin/metrics/sla | SLA riport | 6 |
| WS /ws/events | Real-time event stream | 5 |

---

## Claude Code Frontend Fejlesztes Mintak

### Reflex-szel

```
User: "Keszits egy uj KPI kartya komponenst ami a workflow success rate-et mutatja"

Claude Code:
1. Letrehozza src/aiflow/ui/aiflow_ui/components/success_rate_card.py
2. Definiálja a Reflex komponenst (Python)
3. Bekotos a DashboardState-be
4. Ir tesztet
5. Frissiti a dashboard page-et
```

### Next.js-szel

```
User: "Keszits egy uj KPI kartya komponenst ami a workflow success rate-et mutatja"

Claude Code:
1. Letrehozza frontend/src/components/success-rate-card.tsx
2. Definiálja a React komponenst (TypeScript)
3. shadcn/ui Card + Recharts
4. TanStack Query hook az API hivashoz
5. Ir tesztet (Vitest)
6. Frissiti a dashboard page-et
```

**Mindket esetben Claude Code hatekonyan dolgozik** - a kulonbseg a generalt kod nyelve.

---

## Implementacios Fazisok (Ajanlott: Reflex Start)

| Backend Fazis | UI Munka |
|--------------|----------|
| Phase 1 (1-3 het) | Reflex scaffold, login, health page |
| Phase 2 (4-6 het) | DAG viewer, workflow lista |
| Phase 3 (7-9 het) | Prompt editor, chat skeleton |
| Phase 4 (10-13 het) | Chat interface, feedback widget, streaming |
| Phase 5 (14-16 het) | Operator dashboard, job mgmt, admin panel |
| Phase 6 (17-19 het) | Cost/SLA chartok, trace viewer, reports |
| Phase 7 (20-22 het) | Alert mgmt, i18n, polish, **dontes Next.js migraciora** |

---

## Browser Tamogatas
| Browser | Minimum verzio | Megjegyzes |
|---------|---------------|------------|
| Chrome/Edge | Utolso 2 major | Fo fejlesztesi celplatform |
| Firefox | Utolso 2 major | Teljes tamogatas |
| Safari | Utolso 2 major | WebSocket korlatok figyelendo |
| IE 11 | NEM TAMOGATOTT | - |

---

## Mobile Strategia
**Dontes:** A Phase 1-6 kizarolag desktop felulet. A responsive design **Phase 7 opcionalis feladata**.
- Operator Dashboard: responsive layout tervezve (KPI kartyak, job lista)
- Chat Interface: mobilon is hasznalhato (egyszeru layout)
- Developer Portal: desktop-only (DAG viewer, prompt editor)
- Admin Panel: desktop-only

---

## Akadalymentes (WCAG 2.1 AA)
- Billentyuzet navigacio minden interaktiv elemen
- ARIA labelek gombokra es form elemekre
- Szin kontraszt minimum 4.5:1 (szoveg), 3:1 (nagy szoveg)
- Focus management dialog-okban es modal-okban
- Screen reader kompatibilitas (Reflex/Next.js ARIA tamogatas)
- Teszteles: axe-core integracio Playwright-tal (tests/ui/test_accessibility.py)
