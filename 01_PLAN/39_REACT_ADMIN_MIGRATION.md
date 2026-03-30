# AIFlow UI — React Admin Migration Plan

> **Datum:** 2026-03-30
> **Dontes:** A jelenlegi Next.js 16 + shadcn/ui custom frontend (116 fajl) helyett React Admin keretrendszerre valtunk.

---

## 1. MIERT VALTUNK

### A jelenlegi felulet problemai
1. **Fejlesztesi ido arany:** A UI fejlesztes tobb idot igenyel mint a backend AI skillek
2. **116 custom fajl:** Minden UI elemet kézzel irtunk (tablak, formok, RBAC, i18n)
3. **Inkonzisztencia:** 6 kulonbozo viewer layout, elterö stilusok, heterogen UX
4. **Karbantartas:** Minden uj feature-hoz UI boilerplate (tabla, filter, pagination, i18n)

### Miert React Admin?
- **74/100 pont** a 10 kriterium alapu ertekelesen (legjobb az 11 vizsgalt framework kozul)
- **Beepitett:** RBAC, i18n (polyglot.js, 40+ nyelv), tablak, formok, real-time, dark mode
- **DataProvider minta:** Egy helyen definialjuk az API integraciot, minden Resource hasznalja
- **AuthProvider:** Login/logout/identity/permissions keretrendszer
- **Kiterjedt kozosseg:** 24k+ GitHub star, 300+ contributor, aktiv fejlesztes

### Alternativak ertekelese
| Framework | Pont | Elutasitas oka |
|-----------|------|---------------|
| React Admin | **74** | Valasztott |
| Refine | 72 | Hasonlo, de kevesbe erett i18n |
| Reflex | 67 | Nincs beepitett i18n |
| NiceGUI | 66 | Tul korai fazisban |
| Open WebUI | 63 | Alkalmazas, nem framework |

---

## 2. ROLL-BACK STRATEGIA

### Git tag
```bash
git tag v0.9-nextjs-ui    # jelenlegi allapot
```

### Visszaallitas
```bash
# Teljes visszaallas a Next.js UI-ra:
git checkout v0.9-nextjs-ui -- aiflow-ui/
cd aiflow-ui && npm run dev
```

### Mi marad meg
- `aiflow-ui/` konyvtar **NEM TORLODIK** — mellette el az `aiflow-admin/`
- A Next.js API route-ok tovabb futhatnak mint onallo API szerver
- Minden backend kod (skills/, src/aiflow/) **VALTOZATLAN**

---

## 3. MIT VISZUNK AT

### Valtozatlanul atveheto
| Fajl | Tartalom |
|------|----------|
| `aiflow-ui/src/lib/types.ts` | TypeScript tipusok (WorkflowRun, Invoice, Email, etc.) |
| `aiflow-ui/src/lib/i18n.ts` kulcsok | ~300 HU/EN forditas → polyglot formatumba |
| `aiflow-ui/src/components/skill-viewer/pipeline-bar.tsx` | Kompakt pipeline jelzo |
| `aiflow-ui/src/components/skill-viewer/source-badge.tsx` | Demo/Live badge |
| `aiflow-ui/src/components/process-docs/diagram-preview.tsx` | Mermaid render |
| `aiflow-ui/src/components/rag-chat/chat-messages.tsx` | Chat megjelenitoelenitoelenitoelenitol |

### Ujra kell irni
| Funkcio | React Admin megoldas |
|---------|---------------------|
| Sidebar navigacio | `<Menu>` + `<MenuItemLink>` |
| Oldal routing | `<Resource>` + `<CustomRoutes>` |
| Tablazatok | `<Datagrid>` + `<TextField>` stb. |
| Auth middleware | `<AuthProvider>` |
| Formok | `<SimpleForm>` + `<TextInput>` |
| i18n | `polyglotI18nProvider` |

---

## 4. API STRATEGIA

A React Admin a jelenlegi Next.js API route-okat hasznalja mint backend:
```
React Admin (localhost:5173)
    ↓ fetch
Next.js API (localhost:3000/api/*)
    ↓ fetchBackend / execFileAsync
FastAPI (localhost:8000) / Subprocess (.venv/Scripts/python.exe)
```

Alternativa: Kozvetlenul a FastAPI-t hasznaljuk (ha fut).

---

## 5. FAZISOK

| # | Fazis | Becsles | Kimenet |
|---|-------|---------|---------|
| 0 | Elokeszites | Jelen session | Tag + dokumentacio |
| 1 | Projekt setup | 1 session | Login + layout + i18n + DataProvider |
| 2 | CRUD Resources | 1 session | Runs + Invoices + Emails tablak |
| 3 | Skill Viewers | 2 session | ProcessDoc + RAG Chat + Cubix + Upload |
| 4 | Dashboard + Costs | 1 session | Teljes app |

---

## 6. JELENLEGI UI ALLAPOT (archiv referencia)

### Commitok a mai session-ben (2026-03-30)
| Commit | Tartalom |
|--------|---------|
| `b762d5c` | Mock-to-Real Phase 2-7 (subprocess bekotes) |
| `29c05c7` | Architektura audit |
| `caed8d2` | i18n cleanup (0 hardcoded string) |
| `8e7674d` | SkillViewerLayout + SourceBadge + KpiCard |
| `72db2d9` | Oszinte skill statuszok |
| `8097870` | Egyseges viewer layout + PipelineBar |
| `77be8c4` | Valos funkcionalitas dokumentacio |
| `545814a` | **Kritikus fix: SkillRunner.run_steps data merge** |

### Valos backend statusz
- `process_documentation`: **MUKODIK** subprocess-en at (CLI + UI is)
- `aszf_rag_chat`: Mukodik CLI-bol, UI-bol FastAPI + pgvector kell
- `email_intent_processor`: Mukodik CLI-bol, UI subprocess API kulccsal
- `invoice_processor`: Csak parse step, tobbi stub
- `cubix_course_capture`: Csak CLI, UI read-only viewer
