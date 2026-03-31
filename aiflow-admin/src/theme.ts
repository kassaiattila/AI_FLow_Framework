/**
 * AIFlow Theme — based on React Admin Nano theme pattern
 * Dense, professional, Inter font, indigo accent
 */
import { createTheme, type Theme } from "@mui/material";

const alert = {
  error: { main: "#dc2626" },
  warning: { main: "#d97706" },
  info: { main: "#2563eb" },
  success: { main: "#059669" },
};

const componentsOverrides = (theme: Theme) => ({
  MuiAppBar: {
    defaultProps: { elevation: 0 },
    styleOverrides: {
      root: { borderBottom: `1px solid ${theme.palette.divider}` },
    },
  },
  MuiButton: {
    defaultProps: { size: "small" as const },
    styleOverrides: {
      root: { borderRadius: 8, textTransform: "none" as const, fontWeight: 600 },
    },
  },
  MuiCard: {
    styleOverrides: {
      root: { borderRadius: 10, border: `1px solid ${theme.palette.divider}`, boxShadow: "none" },
    },
  },
  MuiChip: {
    styleOverrides: { root: { borderRadius: 6, fontWeight: 500 } },
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
        borderBottom: `1px solid ${theme.palette.divider}`,
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
    styleOverrides: { root: { "& .MuiOutlinedInput-root": { borderRadius: 8 } } },
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
        borderRadius: 8,
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
    shape: { borderRadius: 8 },
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
  primary: { main: "#4f46e5", light: "#6366f1", dark: "#4338ca" },
  secondary: { main: "#7c3aed", light: "#8b5cf6", dark: "#6d28d9" },
  background: { default: "#f8fafc", paper: "#ffffff" },
  text: { primary: "#0f172a", secondary: "#64748b" },
  divider: "#e2e8f0",
  ...alert,
});

export const darkTheme = createAiflowTheme({
  mode: "dark",
  primary: { main: "#818cf8", light: "#a5b4fc", dark: "#6366f1" },
  secondary: { main: "#a78bfa", light: "#c4b5fd", dark: "#8b5cf6" },
  background: { default: "#0f172a", paper: "#1e293b" },
  text: { primary: "#f1f5f9", secondary: "#94a3b8" },
  divider: "#334155",
  ...alert,
});
