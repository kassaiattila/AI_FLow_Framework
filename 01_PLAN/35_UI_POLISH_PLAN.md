# UI Polish Plan — Melyseg javitas (2026-03-31+)

## Problema osszefoglalo

A P0-P7 session soran 92 fajlbol allo UI-t epitettunk 1 nap alatt.
Az eredmeny: szelessegben kesz (5 viewer, auth, dark mode, i18n infra, CSV, SSE, CI/CD),
de **melysegben hianyos**:
- i18n: 92 kulcs definiálva, de 0% hasznalat a komponensekben
- Viewerek: adat megjelenites van, de nincs workflow erzet
- Diagram: Kroki nem mukodik → semmit nem lat a felhasznalo
- Hardcoded stringek: 88 db szetszorodva 30+ fajlban

## 1. fazis: i18n bekotes (PRIORITAS 1)

**Cel:** Mind a 88 hardcoded string → `t()` hivas

### Erintett fajlok:
```
# Oldalak (8 fajl)
src/app/page.tsx                              — 6 string
src/app/costs/page.tsx                        — 4 string
src/app/runs/page.tsx                         — 12 string
src/app/skills/email_intent_processor/page.tsx — 10 string
src/app/skills/process_documentation/page.tsx — 8 string
src/app/skills/cubix_course_capture/page.tsx  — 8 string
src/app/skills/aszf_rag_chat/page.tsx         — 6 string
src/app/login/page.tsx                        — 4 string

# Komponensek (12+ fajl)
src/components/email/shared.tsx               — label stringek
src/components/email/email-table.tsx           — fejlec stringek
src/components/email/routing-card.tsx          — label stringek
src/components/process-docs/text-input-form.tsx — placeholder, gomb
src/components/process-docs/diagram-preview.tsx — hiba, tab labelek
src/components/process-docs/review-scores.tsx  — score labelek
src/components/process-docs/generation-gallery.tsx — ures allapot
src/components/cubix/pipeline-progress.tsx     — stage labelek
src/components/cubix/lesson-results.tsx        — fejlec stringek
src/components/rag-chat/chat-input.tsx         — role labelek, placeholder
src/components/rag-chat/hallucination-indicator.tsx — szint labelek
src/components/verification/audit-history.tsx  — action labelek
```

### i18n.ts bovites:
Uj kulcsok szuksegesek (becsles: +40 kulcs hu/en):
- email.* (table fejlecek, KPI labelek, ures allapotok)
- processdoc.* (form placeholder, score labelek, hiba uzenetek)
- cubix.* (stage labelek, table fejlecek)
- rag.* (role labelek, hiba uzenetek)
- runs.* (table fejlecek, statusz labelek)
- costs.* (KPI labelek)

### Minta:
```tsx
// ELOTTE (hardcoded):
<p>Betoltes...</p>

// UTANA (i18n):
const { t } = useI18n();
<p>{t("common.loading")}</p>
```

## 2. fazis: Email Viewer UX

### Jelenlegi allapot:
- Email lista tabla (sortable)
- Intent/entity/routing detail panelek
- KPI kartya (szamok)

### Hianyzo:
1. **Szures UI** — intent dropdown, priority dropdown, datum range
2. **Statusz jelzes** — uj/feldolgozott/hiba badge
3. **KPI javitas** — szazalekok, baseline context
4. **Ures allapot** — "Nincs feldolgozott email. Toltsön fel egy .eml fajlt..." szoveg

### Fajlok:
- `email_intent_processor/page.tsx` — szures state + UI
- `email/email-table.tsx` — szures prop fogadas
- `email/shared.tsx` — uj badge-ek

## 3. fazis: Process Docs UX

### Fo problema:
Kroki szerver nincs futva → diagram nem latszik → oldal ertelmetlen

### Megoldas:
1. **npm install mermaid** → client-side rendereles
2. `diagram-preview.tsx` → `mermaid.render()` hasznalata Kroki helyett
3. Kroki marad opcionalisan (ha elerheto, azt hasznalja)

### Tovabbi javitasok:
1. **Review scores** — legend/tooltip: "7+ = jo, 4-6 = elfogadhato, 1-3 = gyenge"
2. **Form pozicio** — elso elem az oldalon (KPI-k alatta)
3. **Galeria** — mindig latszodik (nem csak general utan)

## 4. fazis: Cubix + RAG polish

### Cubix:
1. Pipeline stage labelek: "Probe → Audio → Chunk → STT → Merge → Struktura" (szoveg, nem szimbolum)
2. Szinezett progress bar (zold=kesz, kek=fut, piros=hiba, szurke=varakozik)
3. Osszefoglalo KPI javitas

### RAG Chat:
1. Role selector: tooltip magyarazat
2. Streaming: "Gondolkodik..." jelzes a placeholder uzenetben
3. Conversation nevez/torol

## 5. fazis: Tesztek + validalas

### Uj tesztek:
- i18n-coverage.test.ts: minden oldalban van useI18n() import
- component-render.test.tsx: React Testing Library rendereles (nem crashel)

### Manualis checklist:
- [ ] Minden oldal betolt hiba nelkul
- [ ] HU/EN toggle megvaltoztatja MINDEN szoveget
- [ ] Diagram megjelenik (legalabb raw kod)
- [ ] Email tabla filterelheto
- [ ] Cubix pipeline lepesek olvashatoak

## Verifikacio

```bash
npx vitest run          # 58+ teszt pass
npx next build          # 0 hiba
npm run dev             # manualis ellenorzes
```
