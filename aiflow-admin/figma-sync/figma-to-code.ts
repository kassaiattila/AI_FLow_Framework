/**
 * Figma → Code Sync
 *
 * Reads design tokens from Figma (via MCP node inspection) and
 * generates updated theme.ts code with the new values.
 *
 * Workflow:
 *   1. Claude reads Figma nodes via get_node_info / get_variables
 *   2. This script compares Figma values with current theme.ts
 *   3. Generates a diff + updated theme.ts content
 *
 * Usage (with Claude Code):
 *   "Read the Figma design system and sync changes back to theme.ts"
 *   Claude will: read Figma → run diff → apply changes to theme.ts
 */

import { figmaRgbToHex, FIGMA_CONFIG, PAGE_MAP, COMPONENT_MAP } from "./config";

// --------------- Types ---------------

interface FigmaColorFill {
  r: number;
  g: number;
  b: number;
  a?: number;
}

interface FigmaNodeInfo {
  id: string;
  name: string;
  type: string;
  fills?: Array<{ type: string; color: FigmaColorFill }>;
  children?: FigmaNodeInfo[];
  absoluteBoundingBox?: { x: number; y: number; width: number; height: number };
  style?: {
    fontSize?: number;
    fontWeight?: number;
    fontFamily?: string;
    letterSpacing?: number;
  };
}

interface ExtractedTokens {
  colors: Record<string, string>; // name -> hex
  typography: Record<string, { size: number; weight: number }>;
  spacing: Record<string, number>;
}

// --------------- Extract from Figma Nodes ---------------

export function extractColorsFromNodes(nodes: FigmaNodeInfo[]): Record<string, string> {
  const colors: Record<string, string> = {};

  for (const node of nodes) {
    // Color swatch frames are named like "primary-main #4f46e5"
    if (node.fills?.length && node.fills[0].type === "SOLID") {
      const fill = node.fills[0].color;
      const hex = figmaRgbToHex(fill.r, fill.g, fill.b);

      // Parse the semantic name from the node name
      const name = node.name
        .replace(/#[0-9a-fA-F]{6}/, "")
        .trim()
        .replace(/^dk-/, "dark/")
        .replace(/-/g, ".");

      colors[name] = hex;
    }

    // Recurse into children
    if (node.children) {
      Object.assign(colors, extractColorsFromNodes(node.children));
    }
  }

  return colors;
}

export function extractTypographyFromNodes(
  nodes: FigmaNodeInfo[],
): Record<string, { size: number; weight: number }> {
  const typography: Record<string, { size: number; weight: number }> = {};

  for (const node of nodes) {
    if (node.type === "TEXT" && node.style) {
      const name = node.name || node.id;
      typography[name] = {
        size: node.style.fontSize ?? 13,
        weight: node.style.fontWeight ?? 400,
      };
    }
  }

  return typography;
}

// --------------- Generate Theme Update ---------------

interface ThemeUpdate {
  lightPalette: Record<string, string>;
  darkPalette: Record<string, string>;
  typography?: Record<string, { size: number; weight: number }>;
  radius?: Record<string, number>;
}

export function generateThemeCode(update: ThemeUpdate): string {
  const lp = update.lightPalette;
  const dp = update.darkPalette;

  return `/**
 * AIFlow Theme — based on React Admin Nano theme pattern
 * Dense, professional, Inter font, indigo accent
 *
 * AUTO-SYNCED from Figma — ${new Date().toISOString()}
 * Do not edit colors manually. Use Figma → figma-to-code.ts
 */
import { createTheme, type Theme } from "@mui/material";

const alert = {
  error: { main: "${lp["error.main"] ?? "#dc2626"}" },
  warning: { main: "${lp["warning.main"] ?? "#d97706"}" },
  info: { main: "${lp["info.main"] ?? "#2563eb"}" },
  success: { main: "${lp["success.main"] ?? "#059669"}" },
};

const componentsOverrides = (theme: Theme) => ({
  MuiAppBar: {
    defaultProps: { elevation: 0 },
    styleOverrides: {
      root: { borderBottom: \`1px solid \${theme.palette.divider}\` },
    },
  },
  MuiButton: {
    defaultProps: { size: "small" as const },
    styleOverrides: {
      root: { borderRadius: ${update.radius?.button ?? 8}, textTransform: "none" as const, fontWeight: 600 },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: { borderRadius: ${update.radius?.card ?? 10}, border: \`1px solid \${theme.palette.divider}\`, boxShadow: "none" },
    },
  },
  MuiChip: {
    styleOverrides: { root: { borderRadius: ${update.radius?.chip ?? 6}, fontWeight: 500 } },
  },
  MuiFormControl: {
    defaultProps: { variant: "outlined" as const, margin: "dense" as const, size: "small" as const, fullWidth: true },
  },
  MuiIconButton: { defaultProps: { size: "small" as const } },
  MuiListItem: { defaultProps: { dense: true } },
  MuiListItemIcon: {
    styleOverrides: { root: { "&.MuiListItemIcon-root": { minWidth: theme.spacing(4) } } },
  },
  MuiTable: { defaultProps: { size: "small" as const } },
  MuiTableCell: {
    styleOverrides: {
      root: {
        padding: theme.spacing(0.75, 1),
        borderBottom: \`1px solid \${theme.palette.divider}\`,
      },
    },
  },
  MuiTableHead: {
    styleOverrides: {
      root: {
        "& .MuiTableCell-head": {
          fontWeight: 700,
          fontSize: "0.7rem",
          textTransform: "uppercase" as const,
          letterSpacing: "0.05em",
          color: theme.palette.text.secondary,
        },
      },
    },
  },
  MuiTableRow: {
    styleOverrides: {
      root: {
        "&:hover": { backgroundColor: theme.palette.action.hover },
      },
    },
  },
  MuiTextField: {
    defaultProps: { variant: "outlined" as const, margin: "dense" as const, size: "small" as const, fullWidth: true },
    styleOverrides: { root: { "& .MuiOutlinedInput-root": { borderRadius: ${update.radius?.button ?? 8} } } },
  },
  MuiToolbar: {
    defaultProps: { variant: "dense" as const },
    styleOverrides: {
      root: { minHeight: theme.spacing(5) },
      regular: { backgroundColor: theme.palette.background.paper },
    },
  },
  RaDatagrid: {
    styleOverrides: {
      root: {
        "& .RaDatagrid-headerCell": { color: theme.palette.primary.main },
      },
    },
  },
  RaLayout: {
    styleOverrides: {
      root: { "& .RaLayout-appFrame": { marginTop: theme.spacing(6) } },
    },
  },
  RaMenuItemLink: {
    styleOverrides: {
      root: {
        borderRadius: ${update.radius?.button ?? 8},
        marginLeft: 6,
        marginRight: 6,
        paddingLeft: theme.spacing(1.5),
        paddingRight: theme.spacing(1.5),
        "&.RaMenuItemLink-active": {
          fontWeight: 700,
        },
      },
    },
  },
});

function createAiflowTheme(palette: Record<string, unknown>): Theme {
  const themeOptions = {
    palette,
    shape: { borderRadius: ${update.radius?.button ?? 8} },
    sidebar: { width: 220, closedWidth: 48 },
    spacing: 8,
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      fontSize: 13,
      h4: { fontWeight: 700, letterSpacing: "-0.02em" },
      h5: { fontWeight: 600, letterSpacing: "-0.01em" },
      h6: { fontWeight: 600 },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 600 },
      button: { textTransform: undefined },
    },
  };
  const theme = createTheme(themeOptions);
  theme.components = componentsOverrides(theme);
  return theme;
}

export const lightTheme = createAiflowTheme({
  mode: "light",
  primary: { main: "${lp["primary.main"] ?? "#4f46e5"}", light: "${lp["primary.light"] ?? "#6366f1"}", dark: "${lp["primary.dark"] ?? "#4338ca"}" },
  secondary: { main: "${lp["secondary.main"] ?? "#7c3aed"}", light: "${lp["secondary.light"] ?? "#8b5cf6"}", dark: "${lp["secondary.dark"] ?? "#6d28d9"}" },
  background: { default: "${lp["background.default"] ?? "#f8fafc"}", paper: "${lp["background.paper"] ?? "#ffffff"}" },
  text: { primary: "${lp["text.primary"] ?? "#0f172a"}", secondary: "${lp["text.secondary"] ?? "#64748b"}" },
  divider: "${lp["divider"] ?? "#e2e8f0"}",
  ...alert,
});

export const darkTheme = createAiflowTheme({
  mode: "dark",
  primary: { main: "${dp["primary.main"] ?? "#818cf8"}", light: "${dp["primary.light"] ?? "#a5b4fc"}", dark: "${dp["primary.dark"] ?? "#6366f1"}" },
  secondary: { main: "${dp["secondary.main"] ?? "#a78bfa"}", light: "${dp["secondary.light"] ?? "#c4b5fd"}", dark: "${dp["secondary.dark"] ?? "#8b5cf6"}" },
  background: { default: "${dp["background.default"] ?? "#0f172a"}", paper: "${dp["background.paper"] ?? "#1e293b"}" },
  text: { primary: "${dp["text.primary"] ?? "#f1f5f9"}", secondary: "${dp["text.secondary"] ?? "#94a3b8"}" },
  divider: "${dp["divider"] ?? "#334155"}",
  ...alert,
});
`;
}

// --------------- Layout Diff ---------------

export interface LayoutChange {
  page: string;
  component: string;
  property: string;
  oldValue: string | number;
  newValue: string | number;
  figmaNodeId: string;
}

export function detectLayoutChanges(
  figmaNodes: FigmaNodeInfo[],
  pageMapping: typeof PAGE_MAP,
): LayoutChange[] {
  const changes: LayoutChange[] = [];

  for (const node of figmaNodes) {
    const mapping = pageMapping.find((p) => p.figmaFrameName === node.name);
    if (!mapping) continue;

    // Detect size changes (viewport width changes)
    if (node.absoluteBoundingBox) {
      const { width, height } = node.absoluteBoundingBox;
      if (width !== 1440) {
        changes.push({
          page: mapping.route,
          component: mapping.reactComponent,
          property: "viewport.width",
          oldValue: 1440,
          newValue: width,
          figmaNodeId: node.id,
        });
      }
    }

    // Detect child layout changes
    if (node.children) {
      for (const child of node.children) {
        const compMapping = COMPONENT_MAP.find((c) => c.figmaName === child.name);
        if (compMapping && child.absoluteBoundingBox) {
          changes.push({
            page: mapping.route,
            component: compMapping.reactComponent,
            property: "position",
            oldValue: "original",
            newValue: `x:${child.absoluteBoundingBox.x} y:${child.absoluteBoundingBox.y} w:${child.absoluteBoundingBox.width} h:${child.absoluteBoundingBox.height}`,
            figmaNodeId: child.id,
          });
        }
      }
    }
  }

  return changes;
}

// --------------- Main ---------------

/**
 * Claude Code workflow for Figma → Code sync:
 *
 * 1. Read Design System page:
 *    const dsPage = await mcp.get_node_info({ nodeId: "0:1" })
 *
 * 2. Extract colors:
 *    const colors = extractColorsFromNodes(dsPage.children)
 *
 * 3. Separate light/dark:
 *    const light = Object.fromEntries(
 *      Object.entries(colors).filter(([k]) => !k.startsWith("dark/"))
 *    )
 *    const dark = Object.fromEntries(
 *      Object.entries(colors)
 *        .filter(([k]) => k.startsWith("dark/"))
 *        .map(([k, v]) => [k.replace("dark/", ""), v])
 *    )
 *
 * 4. Generate theme:
 *    const code = generateThemeCode({ lightPalette: light, darkPalette: dark })
 *
 * 5. Write to theme.ts:
 *    await fs.writeFile("src/theme.ts", code)
 */

export function generateSyncReport(
  extractedColors: Record<string, string>,
  layoutChanges: LayoutChange[],
): string {
  const lines: string[] = [
    "# Figma → Code Sync Report",
    `Generated: ${new Date().toISOString()}`,
    "",
    "## Color Changes",
  ];

  for (const [key, hex] of Object.entries(extractedColors)) {
    lines.push(`  ${key}: ${hex}`);
  }

  if (layoutChanges.length > 0) {
    lines.push("", "## Layout Changes");
    for (const change of layoutChanges) {
      lines.push(
        `  ${change.page} / ${change.component}: ${change.property} = ${change.newValue}`,
      );
    }
  }

  lines.push(
    "",
    "## Actions",
    "  1. Review color changes above",
    "  2. Run: generateThemeCode() to create updated theme.ts",
    "  3. Review layout changes for manual component updates",
    "  4. Run: npm run build to verify TypeScript compilation",
    "  5. Run: npm run dev to visually verify changes",
  );

  return lines.join("\n");
}
