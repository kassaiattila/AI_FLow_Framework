Design UI/UX in Figma for an AIFlow page or component based on a user journey.

Arguments: $ARGUMENTS
(e.g., "service config page", "RAG collection manager", "human review panel")

> **GATE 4 a 7 HARD GATE pipeline-bol.**
> Ez a command KIZAROLAG a `/ui-journey` (Gate 1) es API teszt (Gate 2-3) UTAN futtatható.
> **OUTPUT ARTEFAKTUM:** PAGE_SPECS.md frissites + Figma frame. Enelkul /ui-page FAIL.

## HARD GATE ELLENORZES (AUTOMATIKUS — ha FAIL → STOP):
> **GATE VIOLATION TORTENELEM:** F1+F2 fazisban a Figma design KIHAGYASRA kerult,
> PAGE_SPECS.md manuálisan lett írva. Emiatt FIZIKAI FAJL CHECK szukseges.

```bash
# GATE CHECK 1: Journey fajl FIZIKAILAG LETEZIK? (ONALLO FAJL, NEM grep a tervben!)
ls 01_PLAN/F*_*JOURNEY*.md 2>/dev/null || echo "GATE 1 FAIL: Journey fajl HIANYZIK!"
# Ha NINCS FAJL → **STOP** — futtasd `/ui-journey` ELOSZOR!

# GATE CHECK 2: API endpoint valos adatot ad?
curl -sf http://localhost:8100/api/v1/{endpoint} | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend', 'NO BACKEND DATA'" || echo "GATE 2-3 FAIL!"
# Ha FAIL → **STOP** — implementald az API-t ELOSZOR!

# GATE CHECK 3: Figma MCP elerheto?
# join_channel → aktualis channel (user adja meg) — ha FAIL → **STOP**
```
**Ha BARMELYIK gate FAIL → NEM DESIGNOLUNK! Eloszor az elofeltetel.**
**NEM kerhetsz engedelyt a gate kihagyasara — NINCS kiveteles.**

## Pre-requisites (HARD — nem advisory!):
1. **User Journey FAJL LETEZIK** — `ls 01_PLAN/F*_*JOURNEY*.md` FAJLT MUTAT (nem ures)
2. **API endpoint LETEZIK** — `curl` VALOS adatot ad, `source: "backend"`
3. **Figma MCP csatlakozva** — `join_channel` channel ID (user adja meg session elejen)

## Design Workflow:

### 1. FIGMA KONTEXTUS BEOLVASAS
```
# Csatlakozas a Figma dokumentumhoz
mcp__ClaudeTalkToFigma__join_channel → "e71e0crh"

# Aktualis design rendszer beolvasas
mcp__ClaudeTalkToFigma__get_document_info
mcp__ClaudeTalkToFigma__get_pages

# Letezo design system olvasas (szinek, tipografia, spacing)
mcp__ClaudeTalkToFigma__get_node_info → Design System page (0:1)

# Letezo komponensek
mcp__ClaudeTalkToFigma__get_local_components
```

### 2. PAGE SPECS OLVASAS
Olvasd el a megfelelo szekciokat:
- `aiflow-admin/figma-sync/PAGE_SPECS.md` — letezo oldalak specifikacioi
- `aiflow-admin/figma-sync/REDESIGN_PLAN.md` — design elvek
- `aiflow-admin/figma-sync/config.ts` — component/page mapping

### 3. FIGMA DESIGN LETREHOZAS
Az uj oldal/komponens designolasa a Figma-ban:

```
# Uj frame letrehozasa a megfelelo oldalon
mcp__ClaudeTalkToFigma__create_frame → {page_id, name, width, height}

# Layout: Auto Layout (flexbox-szeru)
mcp__ClaudeTalkToFigma__set_auto_layout → {direction, spacing, padding}

# Szinek: Design System-bol
mcp__ClaudeTalkToFigma__set_fill_color → {semantic color from design system}

# Szoveg: useTranslate() kulcsokkal
mcp__ClaudeTalkToFigma__create_text → {i18n key placeholder}

# Komponensek: Letezo component instance-ok
mcp__ClaudeTalkToFigma__create_component_instance → {component_key}
```

### 4. DESIGN ELLENORZES
- [ ] Kovetkezetes szin hasznalat (Design System palette)
- [ ] Tipografia hierarchia (H1 > H2 > Body > Caption)
- [ ] Spacing konzisztens (8px grid)
- [ ] Responsive: min 1024px szelesseg
- [ ] Dark mode: minden szin mukodik sotet temaban
- [ ] Loading state: Skeleton/Spinner design
- [ ] Error state: Alert + retry design
- [ ] Empty state: Illustration + CTA design
- [ ] i18n: Minden szoveg i18n key placeholder (NEM hardcoded string!)
- [ ] Governor Pattern: AI adat 70% opacity, verified 100% + checkmark (ha releváns)

### 5. PAGE SPECS FRISSITES
Az uj/modositott design specifikaciojat irasd be:
`aiflow-admin/figma-sync/PAGE_SPECS.md`

Formatum:
```markdown
### {Page Name} (/{route})

**Layout:** {description}
**Data Source:** {API endpoint}

**Sections:**
- {Section 1}: {description, components, data}
- {Section 2}: {description, components, data}

**States:**
- Loading: {skeleton/spinner leiras}
- Error: {alert + retry leiras}
- Empty: {illustration + CTA leiras}

**Interactions:**
- {Click/hover/keyboard akciok}

**i18n Keys:**
- {page.title}: "..."
- {page.description}: "..."
```

### 6. CONFIG FRISSITES
Ha uj oldal vagy komponens:
- `aiflow-admin/figma-sync/config.ts` — PAGE_MAP es/vagy COMPONENT_MAP bovites

### 7. SCREENSHOT MENTES
```
mcp__ClaudeTalkToFigma__export_node_as_image → {node_id, format: "png"}
```

## Design Elvek (ld. REDESIGN_PLAN.md + 43_UI_RATIONALIZATION_PLAN.md):
- **Progressive Disclosure** — Ne mutass mindent egyszerre, bovitheto sorok
- **Governor Pattern (Stanford HAI)** — AI adat 70% opacity amig nem verifikalt
- **Real-Time Status** — Favicon pipeline statusz, SSE/WebSocket live update
- **Honest Data** — Demo/Live badge MINDIG lathato, skeleton loading
- **Keyboard-First** — Cmd+K, Tab navigacio, single-key shortcuts

## Design System: Untitled UI
- **Komponens konyvtar:** Untitled UI Figma Kit (1,100+ ikon, 200+ komponens)
- **Szinek:** brand indigo (#4f46e5), surface (#f8fafc/#0f172a), status (success/warning/error/info)
- **Typography:** Inter font, 13px base, 8px spacing grid
- **Implementacio:** Tailwind v4 utility classes (NEM MUI sx prop)
- **Accessibility:** React Aria (WCAG AA)
- **Ld.:** `aiflow-admin/figma-sync/UNTITLED_UI_AGENT.md` komponens referencia

## VALOS teszteles (a design UTAN!):
- A design UTAN kovetkezik: `/ui-page` vagy `/ui-component` a megvalositas
- A megvalositas UTAN: Playwright E2E teszt valos backend-del
- **A design CSAK AKKOR "KESZ" ha a megvalositott UI Playwright teszten atment**

## FIGMA MCP TOOLS Quick Reference:
| Tool | Mire jo |
|------|---------|
| `join_channel` | Figma csatlakozas (channel: e71e0crh) |
| `get_document_info` | Teljes dokumentum struktura |
| `get_pages` / `set_current_page` | Oldal navigacio |
| `get_node_info` / `get_nodes_info` | Elem inspektalas |
| `create_frame` | Uj frame (oldal vagy szekció) |
| `set_auto_layout` | Flexbox layout |
| `create_text` / `set_text_content` | Szoveg |
| `set_fill_color` / `set_stroke_color` | Szinek |
| `create_component_instance` | Component hasznalat |
| `get_local_components` | Letezo komponensek |
| `export_node_as_image` | Screenshot exportalas |
| `scan_text_nodes` | Osszes szoveg kereses |
