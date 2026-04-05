# AIFlow v1.2.0 — Frontend Design System & Component Library

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
> **Cel:** Professzionalis, ujrahasznalhato UI komponens konyvtar — minden AIFlow oldal egysegesen ebbol epit.

---

## 0. Untitled UI Component Audit

### Elerheto INGYENES React komponensek (MIT, copy-paste CLI)

**Install:** `npx untitledui@latest add <component>` — komponensek a MI REPONKBA masolodnak (nincs vendor lock-in)

**Stack:** React 19 + Tailwind v4 + React Aria — **PONT A MI STACK-UNK, 100% kompatibilis!**

| Kategoria | Elerheto komponensek (FREE) | Hasznaljuk? |
|-----------|---------------------------|-------------|
| **Base** | Avatars, Badge Groups, Badges, Button Groups, Buttons, Checkboxes, Dropdowns, Featured Icons, Inputs, Radio Buttons, Radio Groups, Ratings, Select, Multi-select, Sliders, Tags, Textareas, Toggles, Tooltips | **IGEN — ezeket MIND hasznalni kell** |
| **App UI** | Activity Feeds, Alerts, Breadcrumbs, Calendars, Card Headers, Code Snippets, Color Pickers, Command Menus, Content Dividers, Date Pickers, Empty States, File Uploaders, Filter Bars, Header Navs, Charts (Line/Bar/Pie/Radar), Loading Indicators, Messaging, Metrics, Modals, Notifications, Page Headers, Paginations, Progress Steps, Section Headers, Sidebar Navs, Slideout Menus, Tables, Tabs, Tree Views | **IGEN — adminisztracios UI-hoz** |
| **Page Examples** | Login, Signup, Verification, 404, Dashboards, Settings | **IGEN — referencia** |
| **Marketing** | Banners, Hero, CTA, FAQ, Pricing, Team, Testimonials | NEM (admin app, nem marketing site) |

### Teendo: Untitled UI integracio

```bash
# 1. Init (ha meg nincs)
npx untitledui@latest init aiflow-admin --vite

# 2. Base komponensek hozzaadasa (az osszes free)
npx untitledui@latest add -a -t base

# 3. App UI komponensek hozzaadasa
npx untitledui@latest add modal tabs breadcrumbs alerts notifications metrics file-uploaders
```

### Ami NINCS az ingyenesben (es magunknak kell irni):

| Komponens | Miert nincs | Megoldas |
|-----------|-------------|----------|
| JsonViewer | Specifikus | Sajat impl (30 sor, rekurziv fa) |
| KeyValue list | Specifikus | Sajat impl (20 sor) |
| Split-screen layout | Specifikus | Sajat impl (CSS flex) |
| DocumentViewer | Nagyon specifikus | Sajat impl (PDF.js + canvas) |
| Pipeline YAML editor | Nagyon specifikus | Sajat impl (textarea + syntax) |

---

## 0.1 Chat UI Modernizacio

### Jelenlegi allapot vs. Professional szint

| Feature | Jelenlegi ChatPanel | claude.ai szint |
|---------|--------------------|--------------------|
| Streaming | SSE, alapveto | SSE + token-by-token render |
| Markdown | Nincs | react-markdown + remark-gfm |
| Code highlight | Nincs | Shiki (VS Code engine, WASM) |
| Copy message | Van (basic) | Copy + share link |
| History | Van (usePromptHistory) | Virtual scroll (TanStack Virtual) |
| Model selector | Van (dropdown) | Dropdown + model info tooltip |
| Keyboard shortcuts | Nincs | Cmd+Enter, Cmd+K palette |
| Mobile responsive | Reszleges | Drawer sidebar, bottom input |
| Artifacts/vizualizacio | Nincs | Inline code exec, charts |

### claude.ai tech stack (kutatott):
- **Next.js** + TypeScript + **Tailwind CSS** + SSE streaming
- Anthropic mobil app: **React Native**
- OpenAI ChatGPT mobil: **React Native**

### Chat UI bovitesi terv:

```bash
# Uj fuggosegek:
npm install react-markdown remark-gfm rehype-highlight shiki @tanstack/react-virtual
```

**Prioritas sorrend:**
1. Markdown rendering (react-markdown + remark-gfm)
2. Code syntax highlighting (Shiki — VS Code motor)
3. Virtual scrolling hosszu beszelgetesekhez (TanStack Virtual)
4. Keyboard shortcuts (Cmd+Enter = kuldes, Escape = cancel)
5. Mobile responsive layout (bottom-fixed input, drawer sidebar)

---

## 0.2 User Journey Tervezesi Metodologia

### Problema (tapasztalat F1-F2-bol):
> A korabbi journey-k NEM voltak eleg reszletesek → UI-n nem volt letesztelve → hasznalhatosagi problemak a fejlesztes vegen derultek ki.

### Uj Journey Template (KOTELEZO minden uj oldalra):

```markdown
# User Journey: [Feature Name]

## 1. Actor & Context
- **Ki:** [Szerepkor — admin, konyvelo, auditor]
- **Honnan jon:** [Elozo oldal/trigger]
- **Celja:** [Mit akar elereni]

## 2. Lepes-Szerepjáték (MINDEN kattintas!)
| # | User cselekves | Rendszer reakcio | UI elem | Hiba eset |
|---|----------------|-----------------|---------|-----------|
| 1 | Megnyitja a Pipelines oldalt | Lista betolt | DataTable | ErrorState ha backend down |
| 2 | Kattint "Create Pipeline" | Modal megnyilik | Modal + YAML editor | — |
| 3 | Beilleszt YAML-t | Live validation fut | Textarea + error list | Piros hiba uzenet |
| 4 | Kattint "Validate" | API hivas | Button → loading | ErrorState ha invalid |
| 5 | Kattint "Save" | Pipeline mentve, lista frissul | Toast: "Pipeline created" | Error toast |

## 3. Alternativ Utak
- Mi tortenik ha nincs backend? → Demo mode banner
- Mi tortenik ha a YAML szintaktikailag hibas? → Inline error, NEM ment
- Mi tortenik ha a user mobil eszkozon van? → Responsive layout

## 4. Acceptance Criteria (Playwright E2E)
- [ ] Oldal betolt < 2s
- [ ] Lista megjelenik valos adatokkal
- [ ] Create → modal → save → lista frissul
- [ ] HU/EN toggle MINDEN szovegen
- [ ] Dark/Light mode MINDEN elmen
- [ ] 0 console error
- [ ] Mobile nezetben hasznalhato (viewport 375px)

## 5. Figma Design Link
- Frame ID: [Figma frame hivatkozas]
- PAGE_SPECS.md szekció: [hivatkozas]
```

### Journey → UI → Teszt Pipeline (KOTELEO sorrend):
```
1. Journey doc iras → 01_PLAN/F{X}_{NAME}_JOURNEY.md
2. Figma design → /ui-design (MCP Figma integration)
3. UI implementacio → /ui-page
4. Playwright E2E → MINDEN journey lepes tesztelve
5. Ha barmelyik journey lepes FAIL → JAVITAS, NEM "kesobb"
```

---

## 0.3 Cross-Platform Strategia

### Jelenlegi: Web-only (React 19 + Vite)
### Rovid tav: PWA (Progressive Web App)
### Kozep tav: React Native (ha mobil kell)

**PWA bovites (minimalis koltseg, nagy hozam):**
```json
// vite.config.ts — PWA plugin
import { VitePWA } from 'vite-plugin-pwa'
// → Offline capability, home screen install, push notifications
```

**React Native (jovobeli):**
- Anthropic es OpenAI is React Native-ot hasznal a mobil apphoz
- Kozos TypeScript konyvtarak a web es mobil kozott: API client, i18n, types
- A jelenlegi Tailwind → NativeWind (Tailwind for React Native)

PWA setup a C20 ciklusban (Tier 4 Polish): vite-plugin-pwa + manifest.json + service worker. React Native kesobbi fazisban ha mobil kell.

---

## 1. Jelenlegi Allapot

### Meglevo komponensek

| Komponens | Ujrahasznalhato? | Hol hasznalt |
|-----------|-----------------|--------------|
| **DataTable** | Igen (TanStack v8) | 10+ oldal |
| **PageLayout** | Igen | Minden oldal |
| **StatusBadge** | Igen | Minden oldal |
| **LoadingState** | Igen | Minden oldal |
| **ErrorState** | Igen | Minden oldal |
| **EmptyState** | Igen | Tobb oldal |
| **FileProgress** | Reszben (pipeline-specifikus) | 6 pipeline oldal |
| **ChatPanel** | Reszben (RAG-specifikus) | RagDetail |
| **AppShell** | Igen | Layout |
| **Sidebar** | Igen | Layout |
| **TopBar** | Igen | Layout |

### Ami HIANYZIK:

| Kategoria | Hianyzó komponensek |
|-----------|-------------------|
| **Form** | Input, Select, Textarea, DatePicker, Checkbox, Radio, Toggle, FormField, FormGroup |
| **Feedback** | Toast/Snackbar, ConfirmDialog, ProgressBar, Skeleton |
| **Navigation** | Tabs, Breadcrumb, Stepper/Wizard, Pagination (kulon DataTable-tol) |
| **Overlay** | Modal/Dialog, Drawer/SlideOver, Popover, Tooltip |
| **Data Display** | Card, KpiCard, Badge (altalanos), Tag, Avatar, Timeline |
| **Layout** | Grid, Stack, Divider, Spacer |
| **Charting** | BarChart, LineChart, PieChart wrapper (recharts mar dep) |

---

## 2. Design Token Rendszer

### 2.1 Jelenlegi tokenek (index.css)

Mar leteznek: `--color-brand-*`, `--color-surface-*`, `--color-status-*`, `--font-sans`, `--text-base`.

### 2.2 Bovitett token hierarchia

```css
/* === Spacing Scale === */
--space-0: 0;
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;

/* === Border Radius === */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-xl: 12px;
--radius-full: 9999px;

/* === Shadow === */
--shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px rgb(0 0 0 / 0.07);
--shadow-lg: 0 10px 15px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px rgb(0 0 0 / 0.15);

/* === Typography Scale === */
--text-xs: 11px;
--text-sm: 12px;
--text-base: 13px;
--text-md: 14px;
--text-lg: 16px;
--text-xl: 18px;
--text-2xl: 20px;
--text-3xl: 24px;

/* === Animation === */
--duration-fast: 100ms;
--duration-normal: 200ms;
--duration-slow: 300ms;
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);
```

---

## 3. Komponens Konyvtar Terv

### 3.1 Konyvtar Struktura

```
aiflow-admin/src/components-new/
  ui/                          # Alapveto UI primitives
    Button.tsx                 # Primary, secondary, ghost, danger variants
    Input.tsx                  # Text input + label + error + icon
    Select.tsx                 # Dropdown select + search
    Textarea.tsx               # Multi-line input
    Checkbox.tsx               # + indeterminate state
    Toggle.tsx                 # On/off switch
    DatePicker.tsx             # Datum valaszto (native + custom)
    Badge.tsx                  # Altalanos badge (szin, meret, dot)
    Tag.tsx                    # Removable tag
    Avatar.tsx                 # User avatar (initials fallback)
    Tooltip.tsx                # Hover tooltip (React Aria)
    Divider.tsx                # Horizontal/vertical divider
    
  feedback/                    # Visszajelzes komponensek
    Toast.tsx                  # Toast notifications (success/error/info)
    ToastProvider.tsx          # Context provider for toasts
    ConfirmDialog.tsx          # "Biztos torlod?" modal
    ProgressBar.tsx            # Determinisztikus progress bar
    Skeleton.tsx               # Loading skeleton (tobb variacio)
    
  overlay/                     # Overlay komponensek
    Modal.tsx                  # Centered modal (React Aria useDialog)
    Drawer.tsx                 # Slide-over panel (jobbrol)
    Popover.tsx                # Positioned popup (React Aria)
    
  navigation/                  # Navigacio
    Tabs.tsx                   # Tab switcher (controlled)
    Breadcrumb.tsx             # Utvonal jelzo
    Stepper.tsx                # Wizard / multi-step form
    
  data/                        # Adat megjelentes
    Card.tsx                   # Content card (header, body, footer)
    KpiCard.tsx                # Szam + label + trend ikon (bovitett)
    Timeline.tsx               # Idobeli esemenyek listaja
    KeyValue.tsx               # Key-value pair list
    JsonViewer.tsx             # JSON fa megjelenito (review-hoz)
    
  charts/                      # Diagramok (recharts wrapper)
    BarChart.tsx               # Bar chart wrapper
    LineChart.tsx              # Line chart wrapper  
    PieChart.tsx               # Pie/donut chart wrapper
    ChartContainer.tsx         # Kozos container (title, legend, responsive)
    
  form/                        # Form building blocks
    FormField.tsx              # Label + input + error message wrapper
    FormGroup.tsx              # Csoport (fieldset)
    FormActions.tsx            # Submit/cancel gombok
    
  layout/                      # Layout helpers
    Stack.tsx                  # Vertical/horizontal stack (gap)
    Grid.tsx                   # CSS grid wrapper
    
  # Meglevo (mar letezik)
  DataTable.tsx
  StatusBadge.tsx
  LoadingState.tsx
  ErrorState.tsx
  EmptyState.tsx
  FileProgress.tsx
  ChatPanel/
```

### 3.2 Komponens API Konvenciok

Minden komponens kovetkezetes API-val:

```tsx
// 1. Alapertelmezett export
export function Button({ children, variant, size, disabled, loading, ...props }: ButtonProps) { ... }

// 2. Tipizalt props (MINDIG)
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;     // Ikon (bal oldal)
  iconRight?: React.ReactNode; // Ikon (jobb oldal)
}

// 3. Tailwind class-ok (NEM inline style)
// 4. Dark mode tamogatas (dark: prefix)
// 5. React Aria hook (accessibility)
// 6. forwardRef (ha DOM ref kell)
```

### 3.3 Accessibility (React Aria)

| Komponens | React Aria Hook |
|-----------|----------------|
| Button | `useButton` |
| Modal | `useDialog`, `useOverlay` |
| Popover | `usePopover` |
| Tooltip | `useTooltip` |
| Select | `useSelect`, `useListBox` |
| Tabs | `useTabList`, `useTab`, `useTabPanel` |
| Checkbox | `useCheckbox` |
| Toggle | `useSwitch` |
| Toast | `useToast` (aria-live) |

---

## 4. Oldal Pattern-ek

### 4.1 Lista Oldal Pattern

```tsx
function ListPage() {
  const t = useTranslate();
  const { data, loading, error, refetch } = useApi<ListResponse>("/api/v1/items");
  const [selection, setSelection] = useState<string[]>([]);
  
  return (
    <PageLayout titleKey="items.title" source={data?.source}>
      {/* Toolbar: search + filters + actions */}
      <div className="flex items-center justify-between mb-4">
        <Input placeholder={t("common.search")} icon={<SearchIcon />} />
        <div className="flex gap-2">
          {selection.length > 0 && (
            <Button variant="danger" onClick={handleBulkDelete}>
              {t("common.delete")} ({selection.length})
            </Button>
          )}
          <Button variant="primary" onClick={handleCreate}>
            {t("items.create")}
          </Button>
        </div>
      </div>
      
      {/* Content */}
      {error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={data?.items} columns={columns} loading={loading}
          selectable onSelectionChange={setSelection} onRowClick={navigateToDetail} />
      }
    </PageLayout>
  );
}
```

### 4.2 Detail Oldal Pattern

```tsx
function DetailPage() {
  const { id } = useParams();
  const t = useTranslate();
  const { data, loading, error } = useApi<DetailResponse>(`/api/v1/items/${id}`);
  
  return (
    <PageLayout titleKey="items.detail" source={data?.source}>
      <Breadcrumb items={[
        { label: t("items.title"), href: "/items" },
        { label: data?.name || "..." },
      ]} />
      
      <Tabs defaultTab="overview">
        <Tabs.Tab id="overview" label={t("common.overview")}>
          <Card>
            <KeyValue items={[
              { key: t("items.name"), value: data?.name },
              { key: t("items.status"), value: <Badge>{data?.status}</Badge> },
            ]} />
          </Card>
        </Tabs.Tab>
        <Tabs.Tab id="history" label={t("common.history")}>
          <Timeline events={data?.history} />
        </Tabs.Tab>
      </Tabs>
    </PageLayout>
  );
}
```

### 4.3 Form Oldal Pattern

```tsx
function CreatePage() {
  const t = useTranslate();
  const [formData, setFormData] = useState<CreateRequest>({});
  const [submitting, setSubmitting] = useState(false);
  
  return (
    <PageLayout titleKey="items.create">
      <Card>
        <form onSubmit={handleSubmit}>
          <FormGroup label={t("items.general")}>
            <FormField label={t("items.name")} required error={errors.name}>
              <Input value={formData.name} onChange={...} />
            </FormField>
            <FormField label={t("items.type")}>
              <Select options={typeOptions} value={formData.type} onChange={...} />
            </FormField>
          </FormGroup>
          
          <FormActions>
            <Button variant="ghost" onClick={goBack}>{t("common.cancel")}</Button>
            <Button variant="primary" type="submit" loading={submitting}>
              {t("common.save")}
            </Button>
          </FormActions>
        </form>
      </Card>
    </PageLayout>
  );
}
```

### 4.4 Review Oldal Pattern (split-screen)

```tsx
function ReviewPage() {
  return (
    <PageLayout titleKey="reviews.detail">
      <div className="flex gap-4 h-[calc(100vh-8rem)]">
        {/* Bal: Dokumentum */}
        <div className="w-3/5 overflow-auto border rounded-lg">
          <DocumentViewer documentId={review.entity_id} type={review.entity_type} />
        </div>
        
        {/* Jobb: Review panel */}
        <div className="w-2/5 overflow-auto">
          <Card>
            <KeyValue items={extractedFields} editable onEdit={handleFieldEdit} />
            <Divider />
            <FormField label={t("reviews.comment")}>
              <Textarea value={comment} onChange={setComment} />
            </FormField>
            <FormActions>
              <Button variant="danger" onClick={reject}>Reject</Button>
              <Button variant="primary" onClick={approve}>Approve</Button>
            </FormActions>
          </Card>
        </div>
      </div>
    </PageLayout>
  );
}
```

---

## 5. Fejlesztesi Sorrend

**Elv:** Eloszor az alapvetoe primitives-eket epitjuk, utana a kompozitokat.

| Fazis | Komponensek | Miert eloszor |
|-------|-------------|---------------|
| **1** | Button, Input, Select, Textarea, Checkbox, Toggle | Minden form-hoz kell |
| **2** | Modal, ConfirmDialog, Toast + ToastProvider | Minden CRUD-hoz kell |
| **3** | Tabs, Badge, Card, FormField, FormGroup, FormActions | Detail + create oldalakhoz |
| **4** | Drawer, Tooltip, Popover, Breadcrumb | Navigacio + UX finomitas |
| **5** | KpiCard (bovitett), Timeline, KeyValue, JsonViewer | Review + dashboard |
| **6** | Stepper, Chart wrappers, Skeleton (bovitett) | Wizard + dashboard |

### Phase 1 utan mar hasznalhato:
- Pipeline Create modal (Button + Textarea + Modal)
- Notification Channel config (Input + Select + FormField)

### Phase 3 utan mar hasznalhato:
- Review Detail page (Tabs + Card + FormField + Badge)
- Pipeline Detail page (Tabs + Card + KeyValue)

---

## 6. Minosegi Kovetelmennyek

### Minden komponensre:

- [ ] TypeScript: strict tipizalas, exportalt Props interface
- [ ] Tailwind: kizarolag utility class-ok, NEM inline style
- [ ] Dark mode: `dark:` prefix tamogatas MINDEN szinen
- [ ] i18n: ha szoveg van, `useTranslate()` hook-kal
- [ ] Accessibility: React Aria hook (ha interaktiv), aria-label (ha ikon-only)
- [ ] Responsive: mobil-first, breakpoint-ok ha releváns
- [ ] Story: Dokumentacio pelda a `COMPONENT_EXAMPLES.md`-ben (nem Storybook, tul nehez dep)

### Nem hasznalunk:

- MUI / Material UI (regi, React Admin maradek)
- Inline style / sx prop / emotion
- @mui/icons-material (helyette: SVG ikonok vagy @untitledui/icons)
- CSS-in-JS konyvtarak
- Storybook (tulzott overhead kis csapatnak — helyette: COMPONENT_EXAMPLES.md)

---

## 7. Verifikacio

```bash
# TypeScript HIBA NELKUL
cd aiflow-admin && npx tsc --noEmit

# Vizualis teszt: Playwright MCP
# Minden uj komponensre: render → screenshot → dark mode → screenshot → mobil meret → screenshot

# Oldalak tesztje:
# Pipeline lista → DataTable + Button + Modal (create) → mukodik
# Review detail → Tabs + Card + FormField + Toast (approve) → mukodik
# Notification config → Input + Select + Toggle + ConfirmDialog (delete) → mukodik
```
