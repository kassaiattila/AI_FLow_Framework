# UI Polish Plan — Melyseg javitas (2026-03-31+)

## Elkeszult

### 1. fazis: i18n bekotes — KESZ (8bc89fa)
- 170+ kulcs (hu + en) az i18n.ts-ben
- 26 fajl modositva: mind a 8 oldal + 20+ komponens hasznalja `t()`-t
- HU/EN toggle valoban leforditja a teljes feluletet
- 58 Vitest teszt pass

### Fejlesztesi szabalyok rogzitve — KESZ (0582b49)
- CLAUDE.md: "MANDATORY Next.js UI Development Rules" szekcio
- 4 command fajl frissitve (/ui-component, /ui-page, /ui-viewer, /dev-step)
- Memory: feedback_ui_depth.md (6 szabaly)

## Kovetkezo feladatok

### 2. fazis: Process Docs UX — diagram megjelenites (PRIORITAS 1)
**Fo problema:** Kroki szerver nincs futva → diagram nem latszik → oldal ertelmetlen

**Megoldas:**
1. `npm install mermaid` → client-side rendereles (nem fugg kulso szervertol)
2. `diagram-preview.tsx` → `mermaid.render()` hasznalata, Kroki marad fallback
3. Review scores — tooltip/legend: "7+ = jo, 4-6 = elfogadhato, 1-3 = gyenge"
4. Form pozicio — elso elem az oldalon
5. Galeria — mindig latszodik

**Erintett fajlok:**
- `components/process-docs/diagram-preview.tsx`
- `components/process-docs/review-scores.tsx`
- `skills/process_documentation/page.tsx`

### 3. fazis: Email Viewer UX
1. **Szures UI** — intent dropdown, priority dropdown
2. **Statusz badge** — uj/feldolgozott/hiba
3. **KPI javitas** — szazalekok, context
4. **Ures allapot** — ertelmesebb szoveg

### 4. fazis: Cubix + RAG polish
**Cubix:**
- Pipeline stage: szoveges labelek (mar bekotve i18n-nel)
- Progress bar szinezese (zold/kek/piros/szurke — mar mukodik)

**RAG Chat:**
- Streaming: "Gondolkodik..." jelzes
- Role tooltip
- Conversation nevez

### 5. fazis: Tesztek + validalas
- i18n coverage test: grep minden oldalban van-e `useI18n` import
- Component render test: minden komponens renderelheto hiba nelkul
- Manualis checklist (lasd lent)

## Manualis teszt checklist
- [ ] Dashboard betolt, KPI-k valos adatokat mutatnak
- [ ] HU/EN toggle MINDEN szoveget valtoztat minden oldalon
- [ ] Process docs: diagram latszik (Mermaid client-side VAGY raw kod)
- [ ] Email tabla betolt, detail panelek mukodnek
- [ ] RAG Chat: kerdes kuldheto, streaming valasz erkezik
- [ ] Cubix pipeline: fajlok kivalaszthatok, stage-ek lathatok
- [ ] Costs/Runs: adatok betoltodnek /api/-bol
- [ ] Login/logout/re-login mukodik
- [ ] Dark mode: minden oldal jol nez ki
- [ ] CSV Export mukodik (invoice, runs, costs, email)

## Verifikacio
```bash
npx vitest run          # 58+ teszt pass
npx next build          # 0 hiba
npm run dev             # manualis ellenorzes a checklist alapjan
```
