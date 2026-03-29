Generate a skill-specific result viewer component for the AIFlow dashboard.

## Context
Viewers display the output of a specific AIFlow skill in a user-friendly way.
They live in `aiflow-ui/src/components/viewers/` and are used by skill pages.
The invoice viewer (`aiflow-ui/src/app/skills/invoice_processor/page.tsx`) is the reference implementation.

## Pattern (from invoice viewer):
- Left panel: extracted structured data (vendor, buyer, header fields)
- Right panel: line items table with totals
- Confidence badges (green >= 90%, yellow >= 70%, red < 70%)
- Validation errors/warnings display
- KPI summary cards at top

## Ask me for:
1. Skill name (e.g., "email_intent_processor", "aszf_rag_chat")
2. What data fields to display
3. Side-by-side layout or single panel
4. Special visualizations needed (charts, highlights, badges)

## Existing viewers to reference:
- Invoice: `aiflow-ui/src/app/skills/invoice_processor/page.tsx`
- Types: `aiflow-ui/src/lib/types.ts`

## Rules:
- Match the visual style of the invoice viewer
- Use the same component library (shadcn/ui Card, Table, Badge, Tabs)
- Include confidence/quality score display
- Include validation status (errors/warnings)
- Use `"use client"` for interactive components
- Add TypeScript interface for the skill's data model in `lib/types.ts`

ARGUMENTS: $ARGUMENTS
