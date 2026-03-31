/**
 * Figma ↔ Code Sync Configuration
 *
 * Maps design tokens, components, and pages between
 * the Figma document and the aiflow-admin codebase.
 */

// --------------- Figma Document Reference ---------------

export const FIGMA_CONFIG = {
  /** MCP channel ID for Claude Talk to Figma */
  channelId: "e71e0crh",

  /** Page IDs in the Figma document */
  pages: {
    designSystem: "0:1",
    components: "2:2",
    dashboard: "2:3",
    runs: "2:4",
    invoices: "2:5",
    emails: "2:6",
    costs: "2:7",
    skillViewers: "2:8",
    verification: "2:9",
  },

  /** Component keys (created via create_component_from_node) */
  componentKeys: {
    "Chip/Success": "f0a1d64ab45d1b297194e721e82ca47a942311a9",
    "Chip/Error": "b86143842ee22f239b3332abd1ff3bc98188d51c",
    "Chip/Warning": "5a9bab6fbcaa455c5b5ef4bc27b58509b877e5d8",
    "Chip/Info": "4f7ce6dfc0f5827c5f5a7d76a4556d197da4479d",
    "Chip/Primary": "f5df91e01109e5432d71fb496ee7ff621579a07d",
    "KPI Card": "58025839264f828faaa2dae6caa2b7c02d2b8238",
    AppBar: "8c6faf1c6989a702cd9ef8fa23c324dfc2b25ea6",
    Sidebar: "a807261cd7ebef30f7a06af558a7bc6a653a8c70",
    "Button/Primary": "ef32e7ca3b6bdae63419c55155770e459b11b4ae",
    "Button/Outlined": "f6aaecd5b9942d1aa6243c1f3ff607d167be35f8",
  },
} as const;

// --------------- Design Tokens ---------------

export interface ColorToken {
  hex: string;
  figmaRgb: { r: number; g: number; b: number };
  cssVar: string;
  themeKey: string;
}

export interface DesignTokens {
  colors: {
    light: Record<string, ColorToken>;
    dark: Record<string, ColorToken>;
  };
  typography: {
    fontFamily: string;
    fontSize: number;
    headings: Record<string, { size: number; weight: number; letterSpacing?: string }>;
  };
  spacing: {
    unit: number;
    sidebar: { open: number; closed: number };
    toolbar: number;
    tableCell: { py: number; px: number };
  };
  radius: {
    chip: number;
    button: number;
    card: number;
  };
}

/** Hex to Figma RGB (0-1 range) */
export function hexToFigmaRgb(hex: string): { r: number; g: number; b: number } {
  const h = hex.replace("#", "");
  return {
    r: Math.round((parseInt(h.substring(0, 2), 16) / 255) * 100) / 100,
    g: Math.round((parseInt(h.substring(2, 4), 16) / 255) * 100) / 100,
    b: Math.round((parseInt(h.substring(4, 6), 16) / 255) * 100) / 100,
  };
}

/** Figma RGB (0-1 range) to Hex */
export function figmaRgbToHex(r: number, g: number, b: number): string {
  const toHex = (v: number) =>
    Math.round(v * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

// --------------- Component Map ---------------

export interface ComponentMapping {
  figmaName: string;
  figmaKey: string;
  reactPath: string;
  reactComponent: string;
  props: string[];
}

export const COMPONENT_MAP: ComponentMapping[] = [
  {
    figmaName: "Chip/Success",
    figmaKey: FIGMA_CONFIG.componentKeys["Chip/Success"],
    reactPath: "src/resources/RunList.tsx",
    reactComponent: "StatusChip",
    props: ["label", "color"],
  },
  {
    figmaName: "Chip/Error",
    figmaKey: FIGMA_CONFIG.componentKeys["Chip/Error"],
    reactPath: "src/resources/RunList.tsx",
    reactComponent: "StatusChip",
    props: ["label", "color"],
  },
  {
    figmaName: "KPI Card",
    figmaKey: FIGMA_CONFIG.componentKeys["KPI Card"],
    reactPath: "src/pages/Dashboard.tsx",
    reactComponent: "KpiCard",
    props: ["value", "label", "sublabel", "icon"],
  },
  {
    figmaName: "AppBar",
    figmaKey: FIGMA_CONFIG.componentKeys["AppBar"],
    reactPath: "src/AppBar.tsx",
    reactComponent: "AppBar",
    props: [],
  },
  {
    figmaName: "Sidebar",
    figmaKey: FIGMA_CONFIG.componentKeys["Sidebar"],
    reactPath: "src/Menu.tsx",
    reactComponent: "Menu",
    props: [],
  },
  {
    figmaName: "Button/Primary",
    figmaKey: FIGMA_CONFIG.componentKeys["Button/Primary"],
    reactPath: "@mui/material/Button",
    reactComponent: "Button",
    props: ["variant=contained", "color=primary"],
  },
  {
    figmaName: "Button/Outlined",
    figmaKey: FIGMA_CONFIG.componentKeys["Button/Outlined"],
    reactPath: "@mui/material/Button",
    reactComponent: "Button",
    props: ["variant=outlined", "color=primary"],
  },
];

// --------------- Page Map ---------------

export interface PageMapping {
  figmaPageId: string;
  figmaFrameName: string;
  route: string;
  reactPath: string;
  reactComponent: string;
}

export const PAGE_MAP: PageMapping[] = [
  {
    figmaPageId: FIGMA_CONFIG.pages.dashboard,
    figmaFrameName: "Dashboard - 1440px",
    route: "/",
    reactPath: "src/pages/Dashboard.tsx",
    reactComponent: "Dashboard",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.runs,
    figmaFrameName: "RunList - 1440px",
    route: "/runs",
    reactPath: "src/resources/RunList.tsx",
    reactComponent: "RunList",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.runs,
    figmaFrameName: "RunShow - 1440px",
    route: "/runs/:id",
    reactPath: "src/resources/RunShow.tsx",
    reactComponent: "RunShow",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.invoices,
    figmaFrameName: "InvoiceList - 1440px",
    route: "/invoices",
    reactPath: "src/resources/InvoiceList.tsx",
    reactComponent: "InvoiceList",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.invoices,
    figmaFrameName: "InvoiceShow - 1440px",
    route: "/invoices/:id/show",
    reactPath: "src/resources/InvoiceShow.tsx",
    reactComponent: "InvoiceShow",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.emails,
    figmaFrameName: "EmailList - 1440px",
    route: "/emails",
    reactPath: "src/resources/EmailList.tsx",
    reactComponent: "EmailList",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.emails,
    figmaFrameName: "EmailShow - 1440px",
    route: "/emails/:id",
    reactPath: "src/resources/EmailShow.tsx",
    reactComponent: "EmailShow",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.costs,
    figmaFrameName: "Costs - 1440px",
    route: "/costs",
    reactPath: "src/pages/CostsPage.tsx",
    reactComponent: "CostsPage",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.skillViewers,
    figmaFrameName: "ProcessDocs - 1440px",
    route: "/process-docs",
    reactPath: "src/pages/ProcessDocViewer.tsx",
    reactComponent: "ProcessDocViewer",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.skillViewers,
    figmaFrameName: "RAG Chat - 1440px",
    route: "/rag-chat",
    reactPath: "src/pages/RagChat.tsx",
    reactComponent: "RagChat",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.skillViewers,
    figmaFrameName: "Invoice Upload - 1440px",
    route: "/invoice-upload",
    reactPath: "src/pages/InvoiceUpload.tsx",
    reactComponent: "InvoiceUpload",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.skillViewers,
    figmaFrameName: "Email Upload - 1440px",
    route: "/email-upload",
    reactPath: "src/pages/EmailUpload.tsx",
    reactComponent: "EmailUpload",
  },
  {
    figmaPageId: FIGMA_CONFIG.pages.verification,
    figmaFrameName: "Verification - 1440px",
    route: "/invoices/:id/verify",
    reactPath: "src/verification/VerificationPanel.tsx",
    reactComponent: "VerificationPanel",
  },
];
