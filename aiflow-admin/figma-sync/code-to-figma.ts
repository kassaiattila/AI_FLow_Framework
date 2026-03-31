/**
 * Code → Figma Sync
 *
 * Reads design tokens from theme.ts and generates Figma MCP commands
 * to update the Figma design system variables and color swatches.
 *
 * Usage (with Claude Code):
 *   1. Run this script to generate MCP commands
 *   2. Claude executes the commands via Figma MCP
 *
 * Usage (standalone):
 *   npx tsx figma-sync/code-to-figma.ts > figma-commands.json
 */

import { hexToFigmaRgb, FIGMA_CONFIG, type DesignTokens } from "./config";

// --------------- Extract tokens from theme.ts ---------------

function extractTokensFromTheme(): DesignTokens {
  // These values are extracted from src/theme.ts
  // In a full implementation, this would parse theme.ts AST
  return {
    colors: {
      light: {
        "primary.main": {
          hex: "#4f46e5",
          figmaRgb: hexToFigmaRgb("#4f46e5"),
          cssVar: "--mui-palette-primary-main",
          themeKey: "palette.primary.main",
        },
        "primary.light": {
          hex: "#6366f1",
          figmaRgb: hexToFigmaRgb("#6366f1"),
          cssVar: "--mui-palette-primary-light",
          themeKey: "palette.primary.light",
        },
        "primary.dark": {
          hex: "#4338ca",
          figmaRgb: hexToFigmaRgb("#4338ca"),
          cssVar: "--mui-palette-primary-dark",
          themeKey: "palette.primary.dark",
        },
        "secondary.main": {
          hex: "#7c3aed",
          figmaRgb: hexToFigmaRgb("#7c3aed"),
          cssVar: "--mui-palette-secondary-main",
          themeKey: "palette.secondary.main",
        },
        "secondary.light": {
          hex: "#8b5cf6",
          figmaRgb: hexToFigmaRgb("#8b5cf6"),
          cssVar: "--mui-palette-secondary-light",
          themeKey: "palette.secondary.light",
        },
        "secondary.dark": {
          hex: "#6d28d9",
          figmaRgb: hexToFigmaRgb("#6d28d9"),
          cssVar: "--mui-palette-secondary-dark",
          themeKey: "palette.secondary.dark",
        },
        "background.default": {
          hex: "#f8fafc",
          figmaRgb: hexToFigmaRgb("#f8fafc"),
          cssVar: "--mui-palette-background-default",
          themeKey: "palette.background.default",
        },
        "background.paper": {
          hex: "#ffffff",
          figmaRgb: hexToFigmaRgb("#ffffff"),
          cssVar: "--mui-palette-background-paper",
          themeKey: "palette.background.paper",
        },
        "text.primary": {
          hex: "#0f172a",
          figmaRgb: hexToFigmaRgb("#0f172a"),
          cssVar: "--mui-palette-text-primary",
          themeKey: "palette.text.primary",
        },
        "text.secondary": {
          hex: "#64748b",
          figmaRgb: hexToFigmaRgb("#64748b"),
          cssVar: "--mui-palette-text-secondary",
          themeKey: "palette.text.secondary",
        },
        divider: {
          hex: "#e2e8f0",
          figmaRgb: hexToFigmaRgb("#e2e8f0"),
          cssVar: "--mui-palette-divider",
          themeKey: "palette.divider",
        },
        "success.main": {
          hex: "#059669",
          figmaRgb: hexToFigmaRgb("#059669"),
          cssVar: "--mui-palette-success-main",
          themeKey: "palette.success.main",
        },
        "error.main": {
          hex: "#dc2626",
          figmaRgb: hexToFigmaRgb("#dc2626"),
          cssVar: "--mui-palette-error-main",
          themeKey: "palette.error.main",
        },
        "warning.main": {
          hex: "#d97706",
          figmaRgb: hexToFigmaRgb("#d97706"),
          cssVar: "--mui-palette-warning-main",
          themeKey: "palette.warning.main",
        },
        "info.main": {
          hex: "#2563eb",
          figmaRgb: hexToFigmaRgb("#2563eb"),
          cssVar: "--mui-palette-info-main",
          themeKey: "palette.info.main",
        },
      },
      dark: {
        "primary.main": {
          hex: "#818cf8",
          figmaRgb: hexToFigmaRgb("#818cf8"),
          cssVar: "--mui-palette-primary-main",
          themeKey: "palette.primary.main",
        },
        "primary.light": {
          hex: "#a5b4fc",
          figmaRgb: hexToFigmaRgb("#a5b4fc"),
          cssVar: "--mui-palette-primary-light",
          themeKey: "palette.primary.light",
        },
        "primary.dark": {
          hex: "#6366f1",
          figmaRgb: hexToFigmaRgb("#6366f1"),
          cssVar: "--mui-palette-primary-dark",
          themeKey: "palette.primary.dark",
        },
        "secondary.main": {
          hex: "#a78bfa",
          figmaRgb: hexToFigmaRgb("#a78bfa"),
          cssVar: "--mui-palette-secondary-main",
          themeKey: "palette.secondary.main",
        },
        "background.default": {
          hex: "#0f172a",
          figmaRgb: hexToFigmaRgb("#0f172a"),
          cssVar: "--mui-palette-background-default",
          themeKey: "palette.background.default",
        },
        "background.paper": {
          hex: "#1e293b",
          figmaRgb: hexToFigmaRgb("#1e293b"),
          cssVar: "--mui-palette-background-paper",
          themeKey: "palette.background.paper",
        },
        "text.primary": {
          hex: "#f1f5f9",
          figmaRgb: hexToFigmaRgb("#f1f5f9"),
          cssVar: "--mui-palette-text-primary",
          themeKey: "palette.text.primary",
        },
        "text.secondary": {
          hex: "#94a3b8",
          figmaRgb: hexToFigmaRgb("#94a3b8"),
          cssVar: "--mui-palette-text-secondary",
          themeKey: "palette.text.secondary",
        },
        divider: {
          hex: "#334155",
          figmaRgb: hexToFigmaRgb("#334155"),
          cssVar: "--mui-palette-divider",
          themeKey: "palette.divider",
        },
      },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      fontSize: 13,
      headings: {
        h4: { size: 34, weight: 700, letterSpacing: "-0.02em" },
        h5: { size: 24, weight: 600, letterSpacing: "-0.01em" },
        h6: { size: 20, weight: 600 },
        subtitle1: { size: 16, weight: 600 },
        body1: { size: 13, weight: 400 },
        body2: { size: 12, weight: 400 },
        caption: { size: 11, weight: 400 },
        tableHeader: { size: 11, weight: 700 },
      },
    },
    spacing: {
      unit: 8,
      sidebar: { open: 220, closed: 48 },
      toolbar: 40,
      tableCell: { py: 6, px: 8 },
    },
    radius: {
      chip: 6,
      button: 8,
      card: 10,
    },
  };
}

// --------------- Generate Figma Variable Commands ---------------

interface FigmaVariableCommand {
  action: "set_variable";
  collection: string;
  name: string;
  type: "COLOR" | "FLOAT" | "STRING";
  valueLight: string | number | { r: number; g: number; b: number };
  valueDark?: string | number | { r: number; g: number; b: number };
}

function generateVariableCommands(tokens: DesignTokens): FigmaVariableCommand[] {
  const commands: FigmaVariableCommand[] = [];

  // Color variables
  for (const [key, token] of Object.entries(tokens.colors.light)) {
    const darkToken = tokens.colors.dark[key];
    commands.push({
      action: "set_variable",
      collection: "AIFlow Tokens",
      name: `color/${key}`,
      type: "COLOR",
      valueLight: token.figmaRgb,
      valueDark: darkToken?.figmaRgb,
    });
  }

  // Spacing variables
  commands.push(
    { action: "set_variable", collection: "AIFlow Tokens", name: "spacing/unit", type: "FLOAT", valueLight: tokens.spacing.unit },
    { action: "set_variable", collection: "AIFlow Tokens", name: "spacing/sidebar-open", type: "FLOAT", valueLight: tokens.spacing.sidebar.open },
    { action: "set_variable", collection: "AIFlow Tokens", name: "spacing/sidebar-closed", type: "FLOAT", valueLight: tokens.spacing.sidebar.closed },
    { action: "set_variable", collection: "AIFlow Tokens", name: "spacing/toolbar", type: "FLOAT", valueLight: tokens.spacing.toolbar },
  );

  // Radius variables
  commands.push(
    { action: "set_variable", collection: "AIFlow Tokens", name: "radius/chip", type: "FLOAT", valueLight: tokens.radius.chip },
    { action: "set_variable", collection: "AIFlow Tokens", name: "radius/button", type: "FLOAT", valueLight: tokens.radius.button },
    { action: "set_variable", collection: "AIFlow Tokens", name: "radius/card", type: "FLOAT", valueLight: tokens.radius.card },
  );

  // Typography
  commands.push(
    { action: "set_variable", collection: "AIFlow Tokens", name: "font/family", type: "STRING", valueLight: tokens.typography.fontFamily },
    { action: "set_variable", collection: "AIFlow Tokens", name: "font/base-size", type: "FLOAT", valueLight: tokens.typography.fontSize },
  );

  return commands;
}

// --------------- Generate Diff Report ---------------

export interface TokenDiff {
  key: string;
  source: "code" | "figma";
  codeValue: string;
  figmaValue: string;
  action: "update_figma" | "update_code" | "conflict";
}

export function compareTokens(
  codeTokens: DesignTokens,
  figmaTokens: Partial<DesignTokens>,
): TokenDiff[] {
  const diffs: TokenDiff[] = [];

  // Compare light mode colors
  if (figmaTokens.colors?.light) {
    for (const [key, codeToken] of Object.entries(codeTokens.colors.light)) {
      const figmaToken = figmaTokens.colors.light[key];
      if (figmaToken && figmaToken.hex !== codeToken.hex) {
        diffs.push({
          key: `light.${key}`,
          source: "code",
          codeValue: codeToken.hex,
          figmaValue: figmaToken.hex,
          action: "conflict",
        });
      }
    }
  }

  return diffs;
}

// --------------- Main ---------------

function main() {
  const tokens = extractTokensFromTheme();
  const commands = generateVariableCommands(tokens);

  const output = {
    generated: new Date().toISOString(),
    source: "aiflow-admin/src/theme.ts",
    target: "Figma Document",
    figmaConfig: FIGMA_CONFIG,
    tokenCount: {
      colors: Object.keys(tokens.colors.light).length + Object.keys(tokens.colors.dark).length,
      spacing: 4,
      radius: 3,
      typography: 2,
    },
    commands,
    instructions: [
      "Connect to Figma channel: " + FIGMA_CONFIG.channelId,
      "Execute each command via mcp__ClaudeTalkToFigma__set_variable",
      "Verify colors on Design System page match theme.ts values",
      "After Figma redesign, run figma-to-code.ts to sync back",
    ],
  };

  console.log(JSON.stringify(output, null, 2));
}

main();
