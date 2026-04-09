# AIFlow UI Roadmap — 2026-03-30

## Elkeszult (P0 — P6)

### P0: Audit + cleanup (KESZ — 2026-03-29)
- src/aiflow/ui/ torolve, aiflow_ui/ Reflex archivalva
- CLAUDE.md pontositva, turt sidebar linkek javitva

### P1: Skill viewers + FastAPI (KESZ — 2026-03-30)
- 3 skill viewer: email (6 komp), rag-chat (6 komp), process-docs (5 komp)
- FastAPI: runs, costs, skills, emails endpoints
- 39 TypeScript interface, 6 mock data seed fajl

### P2: Backend integracio + Cubix (KESZ — 2026-03-30)
- Backend proxy (`backend.ts`): FastAPI first, JSON fallback
- Cubix Course Capture viewer (3 komp + pipeline progress)
- Loading/error states mind 5 viewerben

### P3: Streaming + Auth + Audit (KESZ — 2026-03-30)
- SSE streaming: RAG chat token-by-token (`/api/rag/stream`)
- JWT auth: login oldal, `proxy.ts`, cookie token, 3 role
- Verification audit log (`audit-history.tsx`)

### P4: RBAC + CI/CD + E2E (KESZ — 2026-03-30)
- RBAC: `proxy.ts` role hierarchy, route vedelem
- `use-auth.ts` hook + `sidebar-user.tsx` (role badge)
- GitHub Actions CI/CD, Playwright E2E setup (8 test)

### P5: Dark mode + CSV export (KESZ — 2026-03-30)
- Dark mode: `theme-toggle.tsx`, CSS `.dark` class, localStorage
- CSV export: `csv-export.ts` + `export-button.tsx` (4 oldal)

### P6: i18n + PDF export + bugfix (KESZ — 2026-03-30)
- i18n: `i18n.ts` (80+ kulcs hu/en) + `use-i18n.ts` hook + HU/EN toggle
- PDF export: `print-button.tsx` + `@media print` CSS (sidebar elrejtes)
- Bugfix: Script tag hiba (eltavolitva), BatchBanner hydration (useEffect-be mozgatva), i18n hydration (server/client sync)

## Kovetkezo feladatok

### P7: Production hardening (2-3 het)
1. **Invoice batch teszt** — 20+ valos szamla OCR pontositas
2. **Verification panel valos adat** — sub-komponensek bekotese
3. **Real-time dashboard** — WebSocket run tracking
4. **UI unit tesztek** — Vitest + React Testing Library

### P8: Enterprise (1-2 honap)
1. **Kubernetes deployment** — Helm chart
2. **Multi-tenant** — per-customer instance deployment
3. **Production monitoring** — SLA, alerting, Grafana

## Fajl osszefoglalo (jelenlegi allapot)

```
aiflow-ui/src/ — 92 fajl
  app/                    — 11 oldal (/, /login, /costs, /runs, /runs/[id], 6 skill viewer)
  app/api/                — 18 API route (auth, documents, emails, rag, process-docs, cubix, runs)
  components/             — 48 komponens (6 ui, 7 invoice, 7 verification, 3 workflow, 6 email, 6 rag-chat, 5 process-docs, 3 cubix + standalone: sidebar, sidebar-user, theme-toggle, export-button, print-button)
  lib/                    — 9 utility fajl (types, data-store, backend, csv-export, i18n, api, utils, verification-types, document-layout)
  hooks/                  — 4 hook (use-auth, use-i18n, use-verification-state, use-workflow-simulation)
  proxy.ts                — Auth proxy + RBAC (cookie JWT, login redirect, role check)

src/aiflow/api/v1/ — 9 route fajl
  health.py, workflows.py, chat_completions.py, feedback.py,
  runs.py, costs.py, skills_api.py, emails.py, auth.py

.github/workflows/ci.yml — Python lint+test, Next.js build
aiflow-ui/e2e/            — Playwright smoke tests (8 test)
```

## Technologia
- Next.js 16.2.1 + React 19.2.4 + TypeScript 5
- shadcn/ui (button, card, badge, table, tabs, progress)
- TailwindCSS 4 + dark mode (class-based, localStorage)
- FastAPI + asyncpg (real DB queries)
- SSE streaming (ReadableStream + text/event-stream)
- JWT auth (cookie-based, proxy.ts RBAC)
- i18n (lightweight, 80+ kulcs hu/en, localStorage)
- CSV export (client-side, UTF-8 BOM) + PDF (window.print)
- Backend proxy: backend.ts (FastAPI first, JSON fallback)
- CI/CD: GitHub Actions | E2E: Playwright
