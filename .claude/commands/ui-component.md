Generate a new shadcn/ui + TypeScript component for the AIFlow dashboard.

## Context
The UI project is at `aiflow-ui/` using Next.js 16 + TypeScript + shadcn/ui + Tailwind CSS.
Existing components are in `aiflow-ui/src/components/`.
shadcn/ui base components (button, card, badge, table, tabs, progress, tooltip) are already installed.

## Ask me for:
1. Component name (e.g., "workflow-timeline", "cost-bar", "step-detail")
2. Where it goes (e.g., `components/workflow/`, `components/viewers/`)
3. Props interface (what data it receives)
4. Visual description (what it should look like)

## Rules:
- Use TypeScript strict (no `any`)
- Import shadcn/ui components from `@/components/ui/`
- Import types from `@/lib/types`
- Use Tailwind CSS for styling (no inline styles, no CSS modules)
- Component must be a named export (not default)
- Add JSDoc comment describing the component
- Follow the existing patterns in `aiflow-ui/src/components/`
- Hungarian labels where user-facing, English for code

## Generate:
1. The component `.tsx` file
2. Example usage in a page

ARGUMENTS: $ARGUMENTS
