# Figma ↔ Code Bidirectional Pipeline

## Architecture

```
┌─────────────────┐                    ┌─────────────────┐
│   aiflow-admin   │  code-to-figma.ts │   Figma Design   │
│   src/theme.ts   │ ───────────────►  │   Document       │
│   src/pages/*    │                    │                  │
│   src/resources/*│  figma-to-code.ts  │   9 pages        │
│   src/components/│ ◄───────────────── │   10 components  │
└─────────────────┘                    │   14 screens     │
         │                             └─────────────────┘
         │  config.ts                          │
         └───── Component Map ─────────────────┘
                Page Map
                Token Map
```

## Figma Document Structure

| Page | ID | Content |
|------|----|---------|
| 🎨 Design System | 0:1 | Light/Dark palettes, typography, spacing, radius |
| 🧩 Components | 2:2 | Chips, KPI Card, AppBar, Sidebar, Buttons (10 Figma components) |
| 📊 Dashboard | 2:3 | KPI cards + Skill cards grid |
| ▶️ Runs | 2:4 | RunList DataGrid + RunShow with StepTimeline |
| 🧾 Invoices | 2:5 | InvoiceList + InvoiceShow (3-col + line items) |
| 📧 Emails | 2:6 | EmailList + EmailShow (body + intent + routing) |
| 💰 Costs | 2:7 | KPIs + Chart + Skill/Step breakdown tables |
| 🔧 Skill Viewers | 2:8 | ProcessDocs, RAG Chat, Invoice Upload, Email Upload |
| ✅ Verification | 2:9 | Split view: Document Canvas + DataPoint Editor |

## Workflow 1: Code → Figma (Push design changes)

When theme.ts changes (new colors, spacing, etc.):

```bash
# 1. Generate Figma update commands
npx tsx figma-sync/code-to-figma.ts > figma-commands.json

# 2. Tell Claude Code:
#    "Apply these design token changes to Figma"
#    Claude reads figma-commands.json and executes MCP commands
```

Or with Claude Code directly:
```
"The theme changed. Read src/theme.ts and update the Figma Design System page
to match the new colors and tokens."
```

## Workflow 2: Figma → Code (Pull design changes)

After redesigning in Figma:

```
# Tell Claude Code:
"Read the Figma Design System page, compare with theme.ts,
and update the code to match the new Figma design."
```

Claude will:
1. `get_node_info` on the Design System page (0:1)
2. Extract colors from named frames (e.g., `primary-main #4f46e5`)
3. Compare with current `src/theme.ts` values
4. Generate a diff report
5. Update `theme.ts` with new color values via `generateThemeCode()`
6. Report any layout changes that need manual component updates

## Workflow 3: Full Round-Trip

```
1. Design Phase (Figma)
   - Designer modifies colors on Design System page
   - Designer rearranges page layouts
   - Designer adds/removes components

2. Sync Phase (Claude Code)
   - "Sync Figma changes back to code"
   - Claude reads Figma → generates diff → updates theme.ts
   - Claude reports layout changes for manual review

3. Implementation Phase (Code)
   - Developer implements layout changes based on sync report
   - Developer runs `npm run build` to verify
   - Developer runs `npm run dev` to visual-test

4. Push Back Phase (Claude Code)
   - "Push current code state to Figma"
   - Claude reads theme.ts → updates Figma Design System
```

## Config Files

### config.ts
- `FIGMA_CONFIG` — page IDs, component keys, channel ID
- `COMPONENT_MAP` — maps Figma components to React components
- `PAGE_MAP` — maps Figma pages/frames to routes and React files
- Helper functions: `hexToFigmaRgb()`, `figmaRgbToHex()`

### code-to-figma.ts
- `extractTokensFromTheme()` — reads all tokens from theme.ts
- `generateVariableCommands()` — creates Figma MCP commands
- `compareTokens()` — detects code vs Figma differences

### figma-to-code.ts
- `extractColorsFromNodes()` — reads colors from Figma node tree
- `generateThemeCode()` — generates complete theme.ts content
- `detectLayoutChanges()` — finds position/size changes in page frames
- `generateSyncReport()` — creates human-readable diff report

## Color Naming Convention

Figma frames use this naming pattern:
```
{semantic-name} #{hex}
```
Examples:
- `primary-main #4f46e5`
- `dk-primary #818cf8` (dark mode prefix: `dk-`)
- `bg-default #f8fafc`
- `text-secondary #64748b`

The sync scripts parse these names to map back to theme.ts keys.

## Component Mapping

| Figma Component | React Component | File |
|----------------|-----------------|------|
| Chip/Success | StatusChip (success) | RunList.tsx |
| Chip/Error | StatusChip (error) | RunList.tsx |
| Chip/Warning | StatusChip (warning) | RunList.tsx |
| KPI Card | KpiCard | Dashboard.tsx |
| AppBar | AppBar | AppBar.tsx |
| Sidebar | Menu | Menu.tsx |
| Button/Primary | Button variant=contained | @mui/material |
| Button/Outlined | Button variant=outlined | @mui/material |

## Claude Code Prompts

### Quick sync (colors only)
```
"Read the Figma Design System page colors and update theme.ts to match"
```

### Full audit
```
"Compare all Figma pages with the current aiflow-admin code.
Generate a report of what's different."
```

### Redesign flow
```
"I've redesigned the Dashboard in Figma. Read the new layout
and update Dashboard.tsx to match the new card positions and sizes."
```

### Push new component
```
"I added a new PipelineProgress component. Create it as a
Figma component on the Components page."
```
