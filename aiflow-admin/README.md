# AIFlow Admin — React Admin Dashboard

Admin felulet az AIFlow framework-hoz. React Admin 5 + MUI 7 + Vite 7 + TypeScript.

## Architektura

```
Vite :5174  ──proxy──>  FastAPI :8100  ──>  PostgreSQL :5433
                                       ──>  Redis :6379
```

**Ket process** — nincs Next.js:
- **Vite** (frontend dev server) — React Admin + hot reload
- **FastAPI** (backend API) — CRUD + skill futtatás + auth

## Inditas

### 1. Elofeltetelek

```bash
# Projekt gyokerbol:
cd /path/to/07_AI_Flow_Framwork

# Python venv (ha meg nincs):
uv venv && uv pip install -e ".[dev]"

# Node csomagok (ha meg nincs):
cd aiflow-admin && npm install && cd ..

# Docker szolgaltatasok (PostgreSQL, Redis, Kroki):
docker compose --env-file /dev/null up -d db
```

### 2. FastAPI backend (Terminal 1)

```bash
# Projekt gyokerbol:
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8100

# Vagy reload-dal (fejleszteshez):
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --reload --port 8100
```

Ellenorzes: http://localhost:8100/docs (Swagger UI)

### 3. Vite frontend (Terminal 2)

```bash
cd aiflow-admin
npx vite --port 5174
```

**Admin UI:** http://localhost:5174/

**Bejelentkezes:** admin / admin (vagy operator / operator, viewer / viewer)

### 4. Egy parancsban (gyors inditas)

```bash
# Terminal 1 — backend:
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8100

# Terminal 2 — frontend:
cd aiflow-admin && npx vite --port 5174
```

## Portok

| Port | Szolgaltatas | Megjegyzes |
|------|-------------|------------|
| 5174 | Vite (React Admin) | Frontend dev server |
| 8100 | FastAPI | Backend API |
| 8000 | Kroki (Docker) | Diagram rendering — NE hasznald FastAPI-hoz! |
| 5433 | PostgreSQL (Docker) | Adatbazis |
| 6379 | Redis (Docker) | Cache + queue |

## Oldalak

| Oldal | URL | Leiras |
|-------|-----|--------|
| Dashboard | `/` | KPI kartyak + skill kartyak |
| Workflow Runs | `/#/runs` | Futasok listaja + reszletek |
| Invoices | `/#/invoices` | Szamlak listaja + verifikacio |
| Emails | `/#/emails` | Email feldolgozas eredmenyei |
| Cost Analytics | `/#/costs` | Koltseg bontas skill/step szinten |
| Process Docs | `/#/process-docs` | BPMN diagram generalas |
| RAG Chat | `/#/rag-chat` | Jogi dokumentum chat |
| Cubix | `/#/cubix` | Kurzus atiratok |
| Invoice Upload | `/#/invoice-upload` | PDF szamla feltoltes + feldolgozas |
| Email Upload | `/#/email-upload` | Email feltoltes + feldolgozas |
| Verification | `/#/invoices/:id/verify` | Szamla verifikacio (overlay + szerkesztes) |

## API Proxy

A Vite minden `/api/*` es `/health` kerest a FastAPI-ra proxy-zza (port 8100).
Konfiguracio: `vite.config.ts`

Ha a DB ures, az API JSON fallback fajlokbol szolgalja ki az adatokat (`aiflow-ui/data/*.json`).

## Fejlesztes

```bash
# TypeScript ellenorzes:
cd aiflow-admin && npx tsc --noEmit

# Production build:
cd aiflow-admin && npx vite build

# Nyelv valtas: a feluleten jobb felso sarokban Magyar/English toggle
```

## Tech Stack

- React 19 + React Admin 5.14
- Material-UI 7 + Emotion 11
- Vite 7 + TypeScript 5.1
- Mermaid 11.13 (diagram rendereles)
- ra-i18n-polyglot (HU/EN ~165 forditas kulcs)
