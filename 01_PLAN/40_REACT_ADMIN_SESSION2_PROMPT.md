# React Admin Migration — Session 2 Prompt

> Masold be ezt a promptot az uj session elejen.

---

## Feladat

Folytassuk az AIFlow React Admin migracios pilot projektet. A Phase 1 (setup) KESZ, a Phase 2-4 kovetkezik.

## Kontextus

### Mi ez a projekt?
AIFlow — Enterprise AI Automation Framework. Python backend (FastAPI, 6 skill, LLM hivasok), Next.js frontend (aiflow-ui/, 116 fajl), es egy uj React Admin frontend (aiflow-admin/) ami az aiflow-ui-t valtja le.

### Miert valtunk React Admin-ra?
A custom Next.js UI tul sok fejlesztesi idot igenyelt (tablak, formok, RBAC, i18n mind kezzel irva). A React Admin keretrendszer (5.14, MUI 7) ezeket out-of-box adja.

### Mi kesz mar (Phase 1)?
Az `aiflow-admin/` projekt mukodik:
- **Vite 7** dev server a `localhost:5173`-on
- **Vite proxy:** `/api/*` → `localhost:3000` (Next.js API szerver)
- **authProvider.ts** — login/logout/identity via `/api/auth/*`
- **dataProvider.ts** — REST abstraction: runs, invoices, emails, process-docs, cubix
- **i18nProvider.ts** — polyglot HU/EN (teljes React Admin forditas + AIFlow kulcsok)
- **Dashboard.tsx** — KPI cards + skill grid oszinte statuszokkal
- **RunList.tsx** — Datagrid (skill, status chip, duration, cost)
- **RunShow.tsx** — Run detail step-by-step ArrayField tablaval
- **App.tsx** — Admin wrapper: authProvider + dataProvider + i18nProvider + Layout + Runs resource
- Build: `tsc --noEmit` clean, `vite build` sikeres

### Mi a Next.js API szerver?
Az `aiflow-ui/` projekt tovabbra is futtatja az API route-okat (`localhost:3000`):
- `GET /api/runs` — workflow futasok (mock JSON)
- `GET /api/documents` — szamlak (valos kinyert adatok)
- `GET /api/emails` — email klasszifikaciok (mock)
- `GET /api/process-docs` — generalt diagramok (valos)
- `POST /api/process-docs/generate` — valos AI diagram generalas (subprocess!)
- `POST /api/rag/stream` — SSE streaming chat (mock/backend)
- `GET /api/cubix` — kurzus adatok (mock)
- Auth: `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`

**FONTOS:** A Next.js API szerver KELL a React Admin mukodesehez (Vite proxy-n at hasznalja).

### Inditasi sorrend:
```bash
# Terminal 1: Next.js API szerver
cd aiflow-ui && npm run dev          # localhost:3000

# Terminal 2: React Admin
cd aiflow-admin && npm run dev       # localhost:5173
```

### Login adatok (dev):
- admin / admin123
- operator / operator123
- viewer / viewer123

---

## Mi a kovetkezo? (Phase 2-4)

### Phase 2: CRUD Resources
Uj React Admin resource-ok a meglevo API endpointokra:
1. **invoices** Resource — `GET /api/documents` → List (Datagrid: fajl, szallito, szamlaszam, datum, brutto, statusz) + Show (DocumentDetail)
2. **emails** Resource — `GET /api/emails` → List (Datagrid: sender, subject, intent, confidence, priority) + Show (EmailPreview + IntentDetail + EntityList + RoutingCard)

Mindketto a `dataProvider.ts`-ben mar definialt endpoint-ot hasznalja.

### Phase 3: Custom Skill Viewers
Ezek NEM CRUD resource-ok, hanem custom oldalak:
1. **ProcessDocViewer** — TextInput form → `POST /api/process-docs/generate` → Mermaid diagram megjelenites. Ez a skill VALOS AI diagramot general (subprocess: `python -m skills.process_documentation`). Kell: Mermaid client-side render (`npm install mermaid`).
2. **RagChat** — SSE streaming chat. `POST /api/rag/stream` → token-by-token megjelenites. A legkomplexebb custom page.
3. **CubixViewer** — Read-only pipeline viewer. `GET /api/cubix` → kurzus struktura + pipeline files.
4. **InvoiceUpload** — File upload (`POST /api/documents/upload`) + batch processing (`POST /api/documents/process`).
5. **EmailUpload** — Email upload (`POST /api/emails/upload`) + processing (`POST /api/emails/process`).

Custom oldalak React Admin-ban: `<CustomRoutes>` az `App.tsx`-ben.

### Phase 4: Dashboard finomhangolas + Costs oldal
1. Costs oldal: per-skill/per-step koltseg breakdown (aggregalt a runs adatbol)
2. Dashboard finomhangolas: connection status, source badge-ek

---

## Fontos fajlok

### React Admin projekt (aiflow-admin/)
```
src/
  App.tsx                    # Admin wrapper — IDE KERUL minden uj resource/route
  authProvider.ts            # Auth — KESZ
  dataProvider.ts            # REST calls — BOVITHETO uj resource-okkal
  i18nProvider.ts            # HU/EN — BOVITHETO uj kulcsokkal
  Dashboard.tsx              # Fo oldal — KESZ
  Layout.tsx                 # Sidebar layout — KESZ (default)
  resources/
    RunList.tsx              # KESZ
    RunShow.tsx              # KESZ
```

### Next.js API (aiflow-ui/src/app/api/)
```
api/auth/login/route.ts      # POST — login
api/auth/me/route.ts         # GET — identity
api/documents/route.ts       # GET — invoice lista
api/documents/upload/route.ts # POST — PDF upload
api/documents/process/route.ts # POST — batch processing
api/emails/route.ts          # GET — email lista
api/emails/[id]/route.ts     # GET — email detail
api/emails/upload/route.ts   # POST — .eml upload
api/emails/process/route.ts  # POST — email processing
api/process-docs/route.ts    # GET — diagram lista
api/process-docs/generate/route.ts # POST — valos AI generalas!
api/rag/stream/route.ts      # POST — SSE streaming
api/cubix/route.ts           # GET — kurzus adatok
api/runs/route.ts            # GET — futasok
api/health/route.ts          # GET — backend status
```

### Backend (Python)
```
.env                         # OPENAI_API_KEY — megvan, mukodik
.venv/Scripts/python.exe     # Python 3.12 venv
skills/process_documentation/ # PRODUCTION — valos AI diagram generalas
skills/aszf_rag_chat/        # PRODUCTION — RAG chat (DB kell)
skills/email_intent_processor/ # IN-DEVELOPMENT
skills/invoice_processor/    # 10% KESZ (csak parse)
```

### Tervek es dokumentacio
```
01_PLAN/37_UI_AUDIT_AND_REDESIGN.md   # UI audit eredmenyek
01_PLAN/38_UI_REALITY_STATUS.md       # Valos backend statusz
01_PLAN/39_REACT_ADMIN_MIGRATION.md   # Migracios terv + rollback
```

---

## Szabalyok
- **CLAUDE.md** a projekt gyokereben — kotelezoen kovetendo fejlesztesi szabalyok
- Minden string i18n-nel (`useTranslate` hook React Admin-ban)
- Source badge-ek: mindig mutassuk honnan jon az adat (backend/subprocess/demo)
- `npx tsc --noEmit` KELL hogy clean legyen commit elott
- Commitok: conventional commits (`feat`, `fix`, `refactor`)
- A `aiflow-ui/` NEM TORLENDO — rollback celra megmarad (`git tag v0.9-nextjs-ui`)

---

## Elso lepes
Inditsd el a Next.js API servert (`cd aiflow-ui && npm run dev`), majd a React Admin-t (`cd aiflow-admin && npm run dev`), es kezdjuk a Phase 2-vel: **invoices** es **emails** CRUD resources.
