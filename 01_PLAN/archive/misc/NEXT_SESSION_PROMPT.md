# AIFlow — Kovetkezo Session Prompt (2026-04-02 utan)

> **Masold be ezt a promptot a kovetkezo Claude Code session elejen!**

---

## Kontextus

Az elozo session-ben (2026-04-02) elvegzetuk az **F6.0-F6.6 UI migraciot**:
- React Admin + MUI → Untitled UI + Tailwind v4 + TanStack Table
- 15 Tailwind oldal elkeszult, mind mukodik valos backend adattal
- 28 regi MUI fajl torolve (6,987 sor)
- 21/21 API endpoint OK
- Bundle: 325KB gzip
- 13 commit a main branch-en

**Allapot:** `01_PLAN/STATUS_v1.1.0_SESSION.md` — reszletes audit eredmenyek.

---

## 3 Feladat a mai session-re

### 1. Verification oldal Tailwind migracio (KRITIKUS)

A `/documents/:id/verify` oldal az **egyetlen TOROTT** oldal a rendszerben.

**Jelenlegi allapot:**
- `router.tsx`: `{ path: "documents/:id/verify", element: <LegacyPage><VerificationPanel /></LegacyPage> }`
- A regi `verification/VerificationPanel.tsx` MUI + React Admin alapu
- React Admin provider mar NINCS → i18n kulcsok nyers szovegkent, adatlekerdezes nem mukodik
- A Documents oldalon a "Verify" gomb ide navigal → TOROTT oldal

**Figma design (15. frame, ID: `11662:113185`):**
- Split-screen: PDF canvas (bal 55%) + Data Editor (jobb 45%)
- **Dinamikus schema**: mezo nevek/szamok a `document_type_configs` tabla alapjan
- **Collapsible szekciok**: DOCUMENT HEADER (4 fields), VENDOR (3 fields), TOTALS (3 fields), LINE ITEMS
- **Governor Pattern**: 70% opacity = nem verifikalt, 100% = verifikalt
- **Confidence badge**: minden mezonel %-os ertek + ✓/⚠ jeloles
- **Prev/Next navigacio**: ← Prev / Next → gombok (oldal elhagyasa nelkul)
- **"3 of 24 pending"** szamlalo
- **Progress bar**: 5/12 verified (42%)
- **Save & Next →** / **Skip Document** kettős gomb

**API endpointok (mar leteznek):**
- `GET /api/v1/documents/{id}` — dokumentum detail + kinyert mezok
- `POST /api/v1/documents/{id}/verify` — verifikacio mentes
- `GET /api/v1/documents/images/{file}/page_{n}.png` — PDF oldal kep
- `GET /api/v1/documents/extractor/configs` — schema definicio

**Implementacios terv:**
1. Uj `src/pages-new/Verification.tsx` Tailwind-del
2. Router frissites: `LegacyPage<VerificationPanel>` → `<VerificationNew />`
3. Regi `verification/` mappa torlese (5 fajl)
4. Playwright E2E: navigal Document listabol → Verify → mezo szerkesztes → Save
5. Ha kesz: React Admin + MUI dependency eltavolitasa a package.json-bol

### 2. E2E teszt valos adatokkal (Playwright)

**Teszt adatforrasok (ellenorizve, mind elerheto):**

| Forras | Hely | Mennyiseg | Teszt |
|--------|------|-----------|-------|
| PDF szamlak | `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\02_Számlák\Bejövő\2021\` | 29 PDF | Upload 3-5 → process → verify |
| RAG dokumentumok | `C:\Users\kassaiattila\OneDrive - BestIxCom Kft\00_BESTIX_KFT\11_DEV\94_Cubix_RAG_AI\allianz-rag-unified\documents\` | 6 tema mappa | Uj kollekcio → ingest → chat query |
| Video fajlok | `C:\Users\kassaiattila\Videos\ml_w7_8\` | 23 MKV | Upload 1 → STT transcript |
| Email OST | `C:\Users\kassaiattila\AppData\Local\Microsoft\Outlook\attila.kassai@aam.hu.ost` | 319 MB | Lokalis Outlook olvasas |
| Cubix weboldal | https://cubixedu.com/ | HTTP 200 | RPA scraping teszt |

**E2E teszt szcenariok:**
1. **Documents flow**: Upload PDF → SSE process → lista megjelenik → Verify gomb → verifikacio
2. **RAG flow**: Uj kollekcio → ingest dokumentumok → chat query → valasz + citations
3. **Media flow**: Upload video → STT processing → transcript megjelenes
4. **Process Docs flow**: NL leiras → Generate → Mermaid diagram → export
5. **Monitoring check**: 9 service mind healthy
6. **Admin check**: 2 user, role badge-ek

### 3. Vegso polish + v1.1.0 tag

- React Admin + MUI dependency eltavolitasa (ha Verification Tailwind-re migralva)
- Bundle size optimalizacio (code splitting)
- Vegso Playwright regresszio minden oldalon
- `git tag v1.1.0-rc1`
- STATUS frissites

---

## Inditas

```bash
# Backend
make dev    # Docker services
make api    # FastAPI @ localhost:8101

# Frontend
cd aiflow-admin && npm run dev   # Vite @ localhost:5173

# Login
# http://localhost:5173/#/login
# admin@bestix.hu / Admin1234
```

## Kulcs fajlok

- `aiflow-admin/src/router.tsx` — route konfiguracio
- `aiflow-admin/src/pages-new/` — 15 uj Tailwind oldal
- `aiflow-admin/src/components-new/DataTable.tsx` — TanStack Table
- `aiflow-admin/src/lib/` — api-client, auth, i18n, hooks
- `aiflow-admin/src/layout/` — AppShell, Sidebar, TopBar
- `01_PLAN/43_UI_RATIONALIZATION_PLAN.md` — teljes F6 terv
- `01_PLAN/F6_CONSOLIDATION_EVIDENCE.md` — journey/figma/API audit
