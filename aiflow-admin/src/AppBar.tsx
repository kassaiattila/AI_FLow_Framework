import { AppBar, TitlePortal, ToggleThemeButton, LocalesMenuButton } from "react-admin";
import { Typography, Box } from "@mui/material";
import SmartToyIcon from "@mui/icons-material/SmartToy";

const Toolbar = () => (
  <>
    <LocalesMenuButton />
    <ToggleThemeButton />
  </>
);

export const AIFlowAppBar = () => (
  <AppBar color="inherit" elevation={0} toolbar={<Toolbar />}>
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mr: 1 }}>
      <SmartToyIcon sx={{ color: "primary.main", fontSize: 28 }} />
      <Typography
        variant="h6"
        sx={{
          fontWeight: 700,
          letterSpacing: "-0.02em",
          background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        AIFlow
      </Typography>
    </Box>
    <TitlePortal />
  </AppBar>
);
