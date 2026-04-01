# AIFlow — Page-by-Page Design Specification
# Using Untitled UI Components

> Reference file: `figma.com/design/GPg8UQzYXYust9vjN5AAwQ`
> Copy frames from the Untitled UI file into the AIFlow project, then modify content as specified below.

---

## Global Shell (every page)

### Sidebar Navigation
**Source**: Untitled UI `❖ Dashboards` → Desktop (white sidebar) → `Sidebar navigation` (node `6476:163535`)
**Width**: 312px (or 240px compact)

**Modify content to:**
```
Logo: "AI Flow" (brand-700 icon + text-md semibold)
Search: "Search runs, skills, invoices..." (Input component, sm)

─── MONITOR ─── (section label, text-xs, fg-quaternary)
  Overview        (Home icon)
  Runs            (Play icon)
  Invoices        (FileText icon)
  Emails          (Mail icon)
  Cost Analytics  (BarChart icon)

─── SKILLS ─── (section label)
  Process Docs    (FileCode icon)
  RAG Chat        (MessageCircle icon)
  Cubix Capture   (Video icon)
  Invoice Upload  (Upload icon)
  Email Upload    (MailPlus icon)

─── Footer ───
  ● Backend connected (BadgeWithDot, success)
  Last sync: 2 min ago (text-xs, fg-quaternary)
  ─────────
  Avatar + "Admin User" + "admin@bestix.hu"
```

### Top Navbar (alternative — for mobile/narrow)
**Source**: `❖ Dashboards` → Desktop with header nav → `Header navigation` (node `2849:300829`)
**Use only if**: no sidebar layout (mobile, embed mode)

---

## Page 1: Overview (Dashboard)

### Source Frames to Copy
1. **Full page**: `❖ Dashboards` → 2nd Desktop (node `1719:439380`) — white sidebar version
2. **Charts**: `↳ Charts` page (node `1050:146949`) — pick line chart + bar chart

### Layout
```
┌─ Sidebar (312px) ─┬─ Main Content ──────────────────────────┐
│                    │                                          │
│  [as above]        │  Page Header                             │
│                    │  ┌──────────────────────────────────────┐│
│                    │  │ "Overview"           [Import] [+ Add]││
│                    │  │ "Monitor your AI workflows..."       ││
│                    │  └──────────────────────────────────────┘│
│                    │                                          │
│                    │  KPI Cards (3 columns, from Metrics)     │
│                    │  ┌──────────┬──────────┬────────────────┐│
│                    │  │Total Runs│Today Cost│  Success Rate  ││
│                    │  │  1,247   │  $4.82   │    98.2%       ││
│                    │  │ ↑12% 7d  │ budget:  │  4 failed of   ││
│                    │  │ sparkline│  $50/day  │   1,247 total  ││
│                    │  └──────────┴──────────┴────────────────┘│
│                    │                                          │
│                    │  Active Pipelines (Table component)      │
│                    │  ┌──────────────────────────────────────┐│
│                    │  │ "Active Pipelines" [3]  View all →   ││
│                    │  │──────────────────────────────────────││
│                    │  │ Skill  │ Step    │ Progress │Duration││
│                    │  │──────────────────────────────────────││
│                    │  │ ● inv… │ 3/5 gen │ ████░ 60%│ 12.4s ││
│                    │  │ ● ema… │ 1/4 cla │ ██░░░ 25%│  3.1s ││
│                    │  │ ○ pro… │ Queued  │ ░░░░░  0%│   —   ││
│                    │  │──────────────────────────────────────││
│                    │  │ Showing 3 of 3     │  Prev │ Next   ││
│                    │  └──────────────────────────────────────┘│
│                    │                                          │
│                    │  Recent Activity (Table component)       │
│                    │  ┌──────────────────────────────────────┐│
│                    │  │ "Recent Activity"        View all →  ││
│                    │  │──────────────────────────────────────││
│                    │  │ Run ID │Skill│Status│Dur│Cost│Started││
│                    │  │──────────────────────────────────────││
│                    │  │ (5 rows with proper column widths)   ││
│                    │  │──────────────────────────────────────││
│                    │  │ Page 1 of N        │  Prev │ Next   ││
│                    │  └──────────────────────────────────────┘│
└────────────────────┴──────────────────────────────────────────┘
```

### Components Used
| Element | Untitled UI Component | Props/Variant |
|---------|----------------------|---------------|
| Page title | Text `display-sm` semibold | fg-primary |
| Subtitle | Text `text-md` | fg-tertiary |
| KPI Card | Custom (see Metrics page `185:279` — 🔒PRO, recreate) | 3-col grid |
| KPI value | Text `display-md` semibold | fg-primary |
| KPI label | Text `text-sm` medium | fg-tertiary |
| KPI trend | Badge `success` pill + text-xs | ↑12% format |
| Pipeline table | Table (node `2219:471812`) | Columns: 4 |
| Activity table | Table (node `2219:472490`) | Columns: 6 |
| Status dot | BadgeWithDot `sm` | success/warning/error |
| Progress bar | Progress indicator (node `1154:89940`) | Linear, brand |
| Pagination | Pagination (node `225:7288`) | Previous/Next |

### Scalability Rules
- Active Pipelines: Show **max 5** rows, pagination for more
- Recent Activity: Show **max 10** rows, pagination
- "View all →" links navigate to /runs with appropriate filter
- Empty state: "No active pipelines" with illustration
- Loading state: Skeleton placeholders matching card/table shapes

---

## Page 2: Runs (/runs)

### Source Frames
1. **Table**: `↳ Tables` → Table example 1 (node `2219:471812`) — full featured table with avatar, badges, pagination
2. **Page header**: from Dashboard Main → Header section

### Layout
```
Sidebar + Main:
  Page Header: "Runs" + filter controls
  ┌─ Filter Bar ──────────────────────────────────────────────┐
  │ [All time ×] [Skill: All ×] [Status: All ×] [+ More]  🔍 │
  └────────────────────────────────────────────────────────────┘
  ┌─ Table ────────────────────────────────────────────────────┐
  │ ☑ Run ID      Skill              Status    Duration  Cost  │
  │───────────────────────────────────────────────────────────-│
  │ □ RUN-1247   invoice_processor   ●Complete  18.4s   $0.08 │
  │ □ RUN-1246   email_intent_proc   ●Running    3.1s     —   │
  │ □ RUN-1245   aszf_rag_chat       ●Complete   3.2s   $0.04 │
  │ □ RUN-1244   process_docs        ●Complete  12.4s   $0.07 │
  │ □ RUN-1243   cubix_capture       ●Failed    45.2s   $0.12 │
  │───────────────────────────────────────────────────────────-│
  │ ← Previous  1  2  3  ...  10  Next →    Page 1 of 10     │
  └────────────────────────────────────────────────────────────┘
```

### Table Columns
| Column | Width | Content | Component |
|--------|-------|---------|-----------|
| Checkbox | 40px | Select for bulk | Checkbox sm |
| Run ID | 120px | `RUN-{N}` monospace | Text sm medium |
| Skill | 200px | Skill name + type badge below | Text sm + Badge xs |
| Status | 120px | Dot + label | BadgeWithDot |
| Duration | 100px | `{N}s` or `{N}m {N}s` | Text sm |
| Cost | 100px | `${N.NN}` right-aligned | Text sm |
| Started | 140px | Relative time | Text sm, fg-tertiary |
| Actions | 60px | `⋯` menu | Dropdown |

### Row Click Behavior
- Click row → **slide-over panel** (right side, 480px wide) showing Run Detail
- Or expandable row showing StepTimeline inline

### Bulk Actions (when rows selected)
- "Export Selected" button
- "Re-run Failed" button (only if failed selected)

---

## Page 3: Run Detail (/runs/:id)

### Option A: Slide-over Panel
**Source**: `↳ Modals` (node `172:4293`) — use side panel/slideout pattern

### Layout
```
┌─ Panel Header ──────────────────────────┐
│ ← Back   Run #RUN-1247        ×  Close  │
├──────────────────────────────────────────┤
│ Skill: invoice_processor                 │
│ Status: ● Completed                      │
│ Duration: 18.4s    Cost: $0.082          │
│ Started: 2026-03-31 09:15:04             │
├──────────────────────────────────────────┤
│ Pipeline Steps                           │
│                                          │
│ ✓ 1. parse_input         0.8s   $0.002  │
│ │    Parse natural language input        │
│ ✓ 2. generate_extraction 5.2s   $0.045  │
│ │    Extract data with GPT-4o           │
│ ✓ 3. validate_output     2.1s   $0.008  │
│ │    Validate against schema            │
│ ✓ 4. export_formats      1.3s   $0.004  │
│ │    Generate CSV/Excel/JSON            │
│ ✓ 5. quality_review      3.0s   $0.023  │
│      Score completeness                  │
├──────────────────────────────────────────┤
│ Input Summary                            │
│ "invoice_001.pdf (2 pages)"              │
├──────────────────────────────────────────┤
│ Output Summary                           │
│ "Extracted 16 fields, 3 line items..."   │
└──────────────────────────────────────────┘
```

---

## Page 4: Invoices (/invoices)

### Same table pattern as Runs, with these columns:
| Column | Width | Content |
|--------|-------|---------|
| Checkbox | 40px | Multi-select |
| File | 180px | Filename + icon |
| Vendor | 180px | Company name |
| Invoice # | 120px | INV-XXXX |
| Date | 100px | YYYY-MM-DD |
| Amount | 120px | Formatted + currency |
| Valid | 80px | Badge success/error |
| Confidence | 100px | Progress bar + % |
| Actions | 80px | Show · Verify |

### Filter Bar
- Toggle: All / Processed only
- Date range picker (🔒PRO — recreate with Input + Dropdown)
- Vendor search (Input with icon)
- Amount range (two Inputs)

---

## Page 5: Invoice Detail (/invoices/:id)

### Layout: Tab-based
```
  ← Back to Invoices    invoice_001.pdf    ● Valid    [Verify]

  [Overview]  [Line Items]  [Validation]  [History]

  ┌─ Tab: Overview ────────────────────────────────────────────┐
  │ ┌─ Header ─────┐ ┌─ Vendor ─────┐ ┌─ Buyer ──────┐      │
  │ │ Invoice #    │ │ Name         │ │ Name          │      │
  │ │ Type         │ │ Address      │ │ Address       │      │
  │ │ Issue date   │ │ Tax #        │ │ Tax #         │      │
  │ │ Due date     │ │ EU VAT       │ │               │      │
  │ │ Payment      │ │              │ │               │      │
  │ └──────────────┘ └──────────────┘ └───────────────┘      │
  │                                                            │
  │ ┌─ Totals ─────────────────────────────────────────┐      │
  │ │  Net: 1,190,000    VAT: 321,300    Gross: 1,511,300  │  │
  │ └──────────────────────────────────────────────────┘      │
  └────────────────────────────────────────────────────────────┘
```

---

## Page 6: Verification (/invoices/:id/verify)

### THE MOST CRITICAL PAGE — needs special attention

### Layout: Full-width split
```
┌─ Header Bar ─────────────────────────────────────────────────┐
│ ← Back   invoice_001.pdf   Invoice · Incoming                │
│ Auto: 12  Corrected: 2  Pending: 2     87% verified  [Save] │
├──────────────────────┬───────────────────────────────────────┤
│                      │                                       │
│  Document Canvas     │  Data Points                          │
│  (55% width)         │  (45% width)                          │
│                      │                                       │
│  ┌────────────────┐  │  ┌─ Invoice Number ──────────────┐   │
│  │                │  │  │ INV-2026-042         98% ✓ Auto│   │
│  │  PDF/SVG       │  │  └────────────────────────────────┘   │
│  │  Document      │  │  ┌─ Vendor Name ─────────────────┐   │
│  │  with          │  │  │ BestIx Kft           95% ✓ Auto│   │
│  │  bounding      │  │  └────────────────────────────────┘   │
│  │  box           │  │  ┌─ Vendor Address ──────────────┐   │
│  │  overlays      │  │  │ 1234 Budapest...   72% ✎ Edit │   │
│  │                │  │  │ [___________________]  ← inline│   │
│  │  [highlighted  │  │  └────────────────────────────────┘   │
│  │   fields]      │  │  ┌─ Issue Date ──────────────────┐   │
│  │                │  │  │ 2026-03-15           99% ✓ Auto│   │
│  └────────────────┘  │  └────────────────────────────────┘   │
│                      │  ...more data points...               │
│  Zoom: [−] 100% [+]  │                                       │
│  [ ] Show overlays   │  ┌─ Action Bar ──────────────────┐   │
│                      │  │ [Reset]  [Approve all >95%]    │   │
│                      │  │        [Confirm All] [Save]    │   │
│                      │  └────────────────────────────────┘   │
└──────────────────────┴───────────────────────────────────────┘
```

### Governor Pattern Implementation
- **Unverified fields**: opacity 70%, normal border
- **Verified fields**: opacity 100%, green left-border, checkmark icon
- **Low confidence (<70%)**: red left-border, warning icon, forced review
- **Medium confidence (70-90%)**: amber left-border, review suggested
- **High confidence (>90%)**: auto-approved with green indicator

### Data Point Component (repeat for each field)
```
┌─────────────────────────────────────────────────────┐
│ Label                    Confidence  Status          │
│ ┌─────────────────────────────────────────────────┐ │
│ │ Value text                          [Edit] [✓]  │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```
- Uses: Input (for edit mode), Badge (for status), Progress bar (for confidence)
- Keyboard: Tab/Shift+Tab navigate, Enter confirm, E edit, Esc cancel

### Scalability
- Data points grouped by category (Document, Vendor, Buyer, Line Items, Totals)
- Collapsible category groups
- "Approve all fields with >95% confidence" batch action
- Pagination for documents with many pages

---

## Page 7: Emails (/emails)

### Same table pattern as Runs/Invoices
| Column | Content |
|--------|---------|
| Checkbox | Multi-select |
| Sender | Email address |
| Subject | Email subject line |
| Intent | Badge with intent name |
| Confidence | Progress bar + % |
| Priority | Badge (critical=error, high=warning, medium=info, low=success) |
| Received | Relative time |
| Attachments | Count badge |

---

## Page 8: Email Detail (/emails/:id)

### Layout: 2-column with tabs
```
  ← Back    "Re: Szamla mellekletben"    ● billing   High

  ┌─ Left Column (60%) ──────────┬─ Right Column (40%) ──────┐
  │ Email Body                   │ Intent Analysis            │
  │ ┌──────────────────────────┐ │ ┌────────────────────────┐ │
  │ │ From: info@bestix.hu     │ │ │ Intent: billing (92%)  │ │
  │ │ Date: 2026-03-31         │ │ │ Method: sklearn → LLM  │ │
  │ │ ─────────────────────── │ │ │                        │ │
  │ │ Kedves Kollegak,         │ │ │ Entities:              │ │
  │ │ Mellekelem a ...         │ │ │  company: BestIx Kft   │ │
  │ │ ...                      │ │ │  amount: 1,250,000     │ │
  │ └──────────────────────────┘ │ │  currency: HUF         │ │
  │                              │ └────────────────────────┘ │
  │ Attachments                  │ Routing                    │
  │ ┌──────────────────────────┐ │ ┌────────────────────────┐ │
  │ │ 📎 invoice_001.pdf       │ │ │ Queue: billing         │ │
  │ │    application/pdf 245KB │ │ │ Department: Finance    │ │
  │ │    [Preview] [Process]   │ │ │ Priority: High         │ │
  │ └──────────────────────────┘ │ │ SLA: 4 hours           │ │
  │                              │ └────────────────────────┘ │
  └──────────────────────────────┴────────────────────────────┘
```

---

## Page 9: Cost Analytics (/costs)

### Layout
```
  Page Header: "Cost Analytics"   [Date range: Last 7 days ▼]

  ┌─ KPI Row (3 cards) ──────────────────────────────────────┐
  │ Total Cost: $142.50  │ Total Tokens: 2.4M │ Total Runs: 1,247 │
  └──────────────────────────────────────────────────────────────┘

  ┌─ Cost Trend Chart ──────────────────────────────────────────┐
  │ Line chart: daily cost over selected period                  │
  │ Source: Charts page (node 1050:146949)                       │
  └──────────────────────────────────────────────────────────────┘

  ┌─ Cost by Skill (Table) ────────────────────────────────────┐
  │ Skill          │ Runs │ Total Cost │ Avg Cost │ Tokens     │
  │ process_docs   │  247 │    $3.12   │   $0.013 │   450K     │
  │ aszf_rag_chat  │   89 │    $2.45   │   $0.028 │   380K     │
  │ invoice_proc   │   12 │    $0.84   │   $0.070 │   120K     │
  └────────────────────────────────────────────────────────────┘

  ┌─ Cost by Step (Table) ─────────────────────────────────────┐
  │ Skill          │ Step              │ Calls │ Avg Cost      │
  │ process_docs   │ generate_mermaid  │   247 │ $0.008        │
  │ process_docs   │ quality_review    │   247 │ $0.004        │
  │ invoice_proc   │ extract_data      │    12 │ $0.045        │
  └────────────────────────────────────────────────────────────┘
```

---

## Page 10: Process Docs (/process-docs)

### Layout: Split panel
```
  ┌─ Input (35%) ───────────────┬─ Result (65%) ─────────────────┐
  │ "Process Documentation"      │ (empty until generated)        │
  │                              │                                │
  │ ┌─ Textarea ──────────────┐ │ ┌─ Mermaid Diagram ──────────┐ │
  │ │ Describe your business  │ │ │                            │ │
  │ │ process...              │ │ │  [rendered SVG diagram]    │ │
  │ │                         │ │ │                            │ │
  │ └─────────────────────────┘ │ └────────────────────────────┘ │
  │                              │                                │
  │ Templates:                   │ Review                         │
  │ [Invoice] [Support] [Onb.]  │ Score: 8/10                    │
  │                              │ ✓ Completeness  ✓ Logic       │
  │ [Generate]                   │ ✓ Actors  ⚠ Decisions         │
  │                              │                                │
  │ After generation:            │ Issues: (list)                 │
  │ [More detail] [Simpler]      │ Suggestions: (list)            │
  │ [Regenerate]                 │                                │
  │                              │ [Export: SVG | BPMN | DrawIO]  │
  └──────────────────────────────┴────────────────────────────────┘
```

---

## Page 11: RAG Chat (/rag-chat)

### Source: `↳ Messaging` (node `1251:12271`)

### Layout
```
  ┌─ Chat Area ──────────────────────────────────────────────────┐
  │                                                               │
  │ Empty state: 3 preset question chips                          │
  │ [Mi a visszaviteli jog?] [ASZF osszefoglalas] [Privacy]      │
  │                                                               │
  │ ┌─ User message ─────────────────────────────────────┐       │
  │ │ Mi a visszaviteli jog az ASZF szerint?      (right) │       │
  │ └─────────────────────────────────────────────────────┘       │
  │ ┌─ Assistant message ─────────────────────────────────┐      │
  │ │ A visszaviteli jog lehetoseget biztosit...   (left) │      │
  │ │                                                      │      │
  │ │ Sources: [ASZF 4.2.1] [ASZF 4.2.3]                 │      │
  │ │ 📊 1.2s · 450 tokens · $0.003 · Halluc: 0.12       │      │
  │ │ [👍] [👎]                                            │      │
  │ └──────────────────────────────────────────────────────┘      │
  │                                                               │
  ├───────────────────────────────────────────────────────────────┤
  │ ┌─ Input ──────────────────────────────────────┐ [Send]      │
  │ │ Ask a question about your documents...        │             │
  │ └──────────────────────────────────────────────┘             │
  └───────────────────────────────────────────────────────────────┘
```

---

## Page 12: Invoice Upload (/invoice-upload)

### Layout
```
  Page Header: "Invoice Upload"

  ┌─ Upload Zone ──────────────────────────────────────────────┐
  │                                                             │
  │   📎 Click to upload or drag and drop                       │
  │      PDF files (max 10MB each)                              │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘

  [Batch Process]  [Reset]   Uploaded: 3 files

  ┌─ File Queue Table ──────────────────────────────────────────┐
  │ File          │ Status     │ Progress       │ Confidence │ ─ │
  │───────────────────────────────────────────────────────────── │
  │ inv_001.pdf   │ ✓ Done     │ █████████ 100% │    94%     │ → │
  │ inv_002.pdf   │ ● Running  │ ████░░░░░  60% │     —      │   │
  │ inv_003.pdf   │ ○ Pending  │ ░░░░░░░░░   0% │     —      │   │
  │───────────────────────────────────────────────────────────── │
  │ 1 completed · 1 running · 1 pending                         │
  └─────────────────────────────────────────────────────────────┘
```

- Uses: Table, Progress indicator, Badge, Button
- Upload zone: recreate from File upload (🔒PRO) or use Input + dashed border frame
- "→" action navigates to Verification page for completed files

---

## Page 13: Email Upload (/email-upload)

### Same pattern as Invoice Upload, with:
- Accept: `.eml`, `.msg`, `.txt` files
- Results show: Intent + Priority + Entities instead of Confidence

---

## Page 14: Email Connectors (/email-connectors) — F2

**Phase:** F2 (Email Connector + Classifier)
**Layout:** Full-width table with action buttons + Create/Edit modal dialog
**Data Source:** `GET /api/v1/emails/connectors` (CRUD), `POST /api/v1/emails/fetch`, `POST /api/v1/emails/connectors/{id}/test`

**Header:**
- Title: "Email Connectors" (i18n: `aiflow.connectors.title`)
- "New connector" button (primary, top-right)

**Table Columns:**
| Column | Source | i18n Key |
|--------|--------|----------|
| Name | `name` | `aiflow.connectors.name` |
| Provider | `provider` (Chip: IMAP/O365/Gmail) | `aiflow.connectors.provider` |
| Server | `host:port` | `aiflow.connectors.host` |
| Mailbox | `mailbox` | `aiflow.connectors.mailbox` |
| Polling Interval | `polling_interval_minutes` min | `aiflow.connectors.pollingInterval` |
| Active | `is_active` (Chip: green/grey) | `aiflow.connectors.active` |
| Last Fetched | `last_fetched_at` (date) | `aiflow.connectors.lastFetched` |
| Actions | 5 icon buttons | — |

**Row Actions (IconButtons):**
1. Test Connection (WifiIcon) → `POST /connectors/{id}/test` → Snackbar success/error
2. Fetch Now (PlayArrowIcon) → `POST /emails/fetch` → Snackbar with count
3. Fetch History (ExpandMoreIcon) → Toggle inline sub-table
4. Edit (EditIcon) → Open modal dialog pre-filled
5. Delete (DeleteIcon, red) → Confirm dialog → `DELETE /connectors/{id}`

**Expandable History Sub-table:**
- Columns: Status (Chip), Email Count, New, Duration, Error, Date
- Data: `GET /api/v1/emails/connectors/{id}/history`

**Create/Edit Dialog (Modal):**
- Fields: Name*, Provider* (Select: IMAP/O365/Gmail), Server, Port, SSL (Switch), Mailbox, Credentials (password), Polling Interval, Max Emails
- Actions: Cancel, Save
- Validation: Name required

**States:**
- Loading: CircularProgress centered
- Error: Alert severity="error"
- Empty: Card with "No connectors configured." text

**i18n Keys (connectors.* namespace):**
- title, menuLabel, name, provider, host, port, mailbox, pollingInterval, maxEmails
- active, lastFetched, create, edit, delete, testConnection, testSuccess, testFailed
- fetchNow, fetchSuccess, fetchFailed, noConnectors, confirmDelete, ssl, credentials
- filters, imap, o365, gmail, history, emailCount, status

**Playwright E2E Verified:** 2026-04-01 (commit 8fbdb19) — 9 checks, 0 console errors, i18n HU/EN toggle OK

---

## Untitled UI Component Quick Reference

### FREE Components (directly usable)
| Component | Page | Node ID |
|-----------|------|---------|
| Avatars | `↳ Avatars` | `18:1350` |
| Badges | `↳ Badges` | `12:539` |
| Buttons | `↳ Buttons` | `1:1183` |
| Button Groups | `↳ Button groups` | `16:399` |
| Checkboxes | `↳ Checkboxes` | `1097:63638` |
| Dropdowns | `↳ Dropdowns` | `18:0` |
| Inputs | `↳ Inputs` | `85:1269` |
| Progress | `↳ Progress indicators` | `1154:89940` |
| Radio | `↳ Radio groups` | `122:3484` |
| Select | `↳ Select` | `7684:90446` |
| Sliders | `↳ Sliders` | `1086:1423` |
| Toggles | `↳ Toggles` | `1102:4631` |
| Tooltips | `↳ Tooltips` | `1052:485` |
| Tables | `↳ Tables` | `214:0` |
| Charts | `↳ Charts` | `1050:146949` |
| Messaging | `↳ Messaging` | `1251:12271` |
| Modals | `↳ Modals` | `172:4293` |
| Pagination | `↳ Pagination` | `225:7288` |

### Components to Recreate (PRO alternatives)
| Need | Recreate Using |
|------|---------------|
| Command palette (Cmd+K) | Modal + Input + List |
| File upload zone | Frame + dashed border + Input |
| Tabs | Button group with active state |
| Breadcrumbs | Text links with `/` separator |
| Empty states | Frame + illustration + text |
| Date picker | Input + Dropdown with calendar grid |
| Card headers | Frame + text + divider |
| Navigation | Frame + nav items (already in Dashboard) |
