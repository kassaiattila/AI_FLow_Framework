# AIFlow Admin - Complete Redesign Plan

**Date**: 2026-03-31
**Status**: PLANNING
**Target**: Professional AI workflow management platform

## Decision: Technology Migration

### Current Stack (aiflow-admin)
- React Admin 5 + MUI v7 + Emotion
- Custom theme.ts (Indigo accent, Inter font)
- Client-side data filtering

### New Stack
- **Untitled UI React** (MIT, open-source)
- React 19 + Tailwind CSS v4 + TypeScript + React Aria
- 1,100+ icons (@untitledui/icons)
- Claude Code integration (AGENT.md included)
- Figma ↔ Code bidirectional sync ready

### Why Untitled UI
1. World's largest React component library + matching Figma design system
2. React Aria = accessibility-first (WCAG AA out of box)
3. Tailwind v4 = token-based theming, fast iteration
4. Claude Code integration = AI-assisted development built-in
5. MIT license = no vendor lock-in
6. Copy-paste approach = full customization control

---

## Design Principles (from research)

### 1. Progressive Disclosure
- Show only what's needed at each level
- Expandable rows instead of detail page navigation
- Cmd+K command palette for power users

### 2. Governor Pattern (Stanford HAI)
- AI-extracted data appears at 70% opacity = "provisional"
- Human verified data = 100% opacity + checkmark
- Confidence-based routing: auto-accept >90%, flag <70%

### 3. Real-Time Status
- Favicon reflects active pipeline status
- Freshness indicator ("Last synced: 2m ago")
- SSE/WebSocket for live updates (not polling)
- Delta indicators on KPIs (sparklines + trends)

### 4. Honest Data Display
- Demo/Live badge always visible
- Skeleton loading (never empty + spinner)
- Cached snapshots with timestamps on failure

### 5. Keyboard-First (Linear-inspired)
- Cmd+K command palette
- Single-key shortcuts (E=edit, Enter=confirm, Esc=cancel)
- Tab navigation through data points

---

## Page Redesign Specifications

### 1. Dashboard (/)

**Current**: 4 KPI cards + 3 skill cards + backend status
**Redesign**:

```
┌──────────────────────────────────────────────────────────┐
│ AppBar: AI Flow logo | Cmd+K search | Notifications | Avatar │
├────────┬─────────────────────────────────────────────────┤
│Sidebar │  Welcome back, Admin          Last sync: 2m ago │
│        │                                                 │
│ Dash   │  ┌─KPI──┐ ┌─KPI──┐ ┌─KPI──┐ ┌─KPI──┐        │
│ Runs   │  │ 6    │ │ 247  │ │$4.82 │ │98.2% │        │
│ Inv.   │  │Skills│ │ Runs │ │ Cost │ │ Done │        │
│ Email  │  │▁▂▃▅▇│ │▇▅▃▂▁│ │▂▃▅▃▂│ │▇▇▇▇▇│        │
│ Costs  │  └──────┘ └──────┘ └──────┘ └──────┘        │
│        │                                                 │
│ ─────  │  Active Pipelines (real-time)                   │
│ Skills │  ┌──────────────────────────────────────────┐  │
│ Proc.  │  │ ● invoice_proc  ██████░░░ 67%  Step 3/5 │  │
│ RAG    │  │ ○ email_proc    Queued                    │  │
│ Cubix  │  └──────────────────────────────────────────┘  │
│ Upload │                                                 │
│        │  Skills Overview                                │
│        │  ┌────────┐ ┌────────┐ ┌────────┐             │
│        │  │ProcessD│ │RAGChat │ │Invoice │             │
│        │  │●Active │ │●Active │ │◐ Dev   │             │
│        │  │247 runs│ │89 runs │ │12 runs │             │
│        │  └────────┘ └────────┘ └────────┘             │
└────────┴─────────────────────────────────────────────────┘
```

**New Elements**:
- Sparkline trends in KPI cards (7-day)
- Active Pipelines section (real-time running jobs)
- Freshness indicator + manual refresh
- Welcome greeting with user context

### 2. Runs (/runs)

**Current**: React Admin DataGrid
**Redesign**:

- **Dual view toggle**: Table | Timeline
- **Table view**: Expandable rows (click to show StepTimeline inline)
- **Timeline view**: Horizontal Gantt-like bars showing run duration
- **Filters**: Date range picker, skill multi-select, status toggle chips
- **Bulk actions**: Export selected, re-run failed
- **Column controls**: Hide/show/reorder columns

### 3. Run Detail (/runs/:id)

**Current**: Metadata grid + StepTimeline
**Redesign**:

- **Slide-over panel** instead of full page (keeps list context)
- **Pipeline DAG**: Interactive node graph showing step dependencies
- **Step detail**: Click a step node → side panel with inputs/outputs/logs
- **Cost breakdown**: Pie chart per step
- **Retry button** for failed steps

### 4. Invoices (/invoices)

**Current**: DataGrid with All/Processed toggle
**Redesign**:

- **Smart filtering**: Date range, vendor search, amount range, validity
- **Batch operations**: Select multiple → bulk verify, export CSV/Excel
- **Preview on hover**: Quick invoice thumbnail tooltip
- **Confidence indicator column**: Mini progress bar per row
- **Quick actions**: Verify, Download, Compare

### 5. Invoice Detail (/invoices/:id/show)

**Current**: 3-column sections + line items table
**Redesign**:

- **Tab layout**: Overview | Line Items | Validation | History
- **Overview tab**: 2-column (invoice info left, document preview right)
- **Line Items tab**: Editable data table with inline validation
- **Validation tab**: Confidence heatmap, extraction method, processing log
- **History tab**: Audit trail of all changes
- **PDF preview panel**: Side-by-side with extracted data

### 6. Verification (/invoices/:id/verify)

**Current**: Split-screen (Canvas 55% + Editor 45%)
**Redesign**:

- **Governor Pattern**: Unverified fields at 70% opacity
- **Smart ordering**: Low confidence items first
- **Batch approve**: "Approve all >95% confidence" button
- **Undo/Redo stack**: Full edit history
- **Audit trail**: Who changed what, when
- **Keyboard shortcuts panel**: Visible shortcut reference card
- **Auto-save with conflict detection**
- **Multi-page document navigation** (for multi-page PDFs)

### 7. Emails (/emails)

**Current**: DataGrid + EmailShow detail
**Redesign**:

- **Three-panel layout**: List (left) | Preview (center) | Analysis (right)
- **Email preview**: Rendered HTML with highlighted entities
- **Analysis panel**: Intent breakdown chart, entity extraction, routing decision tree
- **Thread view**: Group related emails
- **Attachment preview**: Inline PDF/image viewer

### 8. Costs (/costs)

**Current**: KPIs + bar chart + 2 tables
**Redesign**:

- **Date range selector**: Last 7d / 30d / 90d / custom
- **Interactive charts**: Recharts/Nivo with drill-down
- **Cost trend line**: Daily cost over time
- **Budget alerts**: Set thresholds, show when approaching limit
- **Export**: CSV/PDF report generation
- **Per-model breakdown**: Show cost by LLM model (gpt-4o vs gpt-4o-mini)

### 9. Process Docs (/process-docs)

**Current**: Split input/result
**Redesign**:

- **Template gallery**: Visual cards for preset types
- **Live preview**: Mermaid renders as you type (debounced)
- **Version history**: Compare previous generations
- **Export options**: Mermaid, SVG, PNG, BPMN, DrawIO
- **Collaboration**: Share link to generated diagram

### 10. RAG Chat (/rag-chat)

**Current**: Chat bubbles + preset questions
**Redesign**:

- **Source citations**: Clickable references to source documents
- **Confidence gauge**: Visual hallucination risk indicator
- **Chat history**: Sidebar with previous conversations
- **Document selector**: Choose which document collection to query
- **Streaming**: Token-by-token with typing indicator
- **Feedback**: Working thumbs up/down with reason selection

### 11. Invoice Upload & Email Upload

**Current**: Dropzone + file list + progress
**Redesign**:

- **Drag-and-drop with preview**: Show PDF thumbnail during upload
- **Pipeline visualization**: Step-by-step node graph per file
- **Batch dashboard**: Overall progress + per-file status cards
- **Error recovery**: Retry individual files, skip and continue
- **Results summary**: Success/failure chart after batch completes

---

## Figma Design Process

### Phase 1: Foundation (in Figma)
1. Import Untitled UI Figma kit as library
2. Define AIFlow brand tokens (colors, typography) as Figma Variables
3. Create AIFlow-specific components extending Untitled UI base

### Phase 2: Page Design (in Figma)
4. Design Dashboard (most visible page)
5. Design Verification (most complex page)
6. Design Runs + Invoice list/detail pages
7. Design remaining pages

### Phase 3: Review & Iterate
8. User review of Figma designs
9. Iterate based on feedback
10. Finalize design system

### Phase 4: Implementation
11. Set up Untitled UI in aiflow-admin (Vite + Tailwind v4)
12. Migrate page by page: Dashboard first
13. Connect to existing FastAPI backend
14. Test each page with real data

---

## Figma Resources to Use

| Resource | Purpose |
|----------|---------|
| **Untitled UI Figma Kit** | Base component library (buttons, inputs, tables, badges, etc.) |
| **Obra shadcn/ui Kit** | Reference for shadcn patterns (command palette, etc.) |
| **Data Visualization Package** | Charts for Costs page |
| **Tokens Studio plugin** | Export Figma Variables → Tailwind CSS tokens |
| **Styleframe plugin** | W3C DTCG token export (free, open-source alternative) |

---

## Implementation Priority

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | Set up Untitled UI + Tailwind v4 in aiflow-admin | 1 day | Foundation |
| 2 | Redesign Dashboard in Figma + implement | 2 days | High visibility |
| 3 | Redesign Verification panel | 3 days | Core feature |
| 4 | Redesign Runs list + detail (expandable rows) | 2 days | High usage |
| 5 | Redesign Invoice list + detail + upload | 2 days | Core workflow |
| 6 | Redesign Email list + detail + upload | 1 day | Similar pattern |
| 7 | Redesign Costs analytics | 1 day | Business value |
| 8 | Redesign Process Docs + RAG Chat | 2 days | Skill viewers |
| 9 | Add Cmd+K command palette | 0.5 day | Power user UX |
| 10 | Add skeleton loading + error states | 1 day | Polish |
| 11 | Accessibility audit (React Aria) | 1 day | Compliance |
| 12 | Design token sync pipeline (Figma ↔ Code) | 1 day | Sustainability |

**Total estimated**: ~17 days for full redesign + implementation

---

## Current State Snapshot (2026-03-31)

Saved in: `figma-sync/CURRENT_STATE.md` (to be generated)
Git status: All current changes documented
Figma document: 9 pages with wireframes of current state
