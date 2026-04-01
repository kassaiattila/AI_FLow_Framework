import { useEffect, useState } from "react";
import { Card, CardContent, Typography, Grid, Box, Chip, Stack, Avatar } from "@mui/material";
import { useTranslate, Title } from "react-admin";
import { useNavigate } from "react-router-dom";
import CircleIcon from "@mui/icons-material/Circle";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";

interface SkillInfo {
  name: string;
  display_name: string;
  status: string;
  description: string;
  viewerPath?: string;
}

const SKILLS: SkillInfo[] = [
  { name: "process_documentation", display_name: "Process Documentation", status: "production", description: "skillDesc.process_documentation", viewerPath: "/process-docs" },
  { name: "aszf_rag_chat", display_name: "ASZF RAG Chat", status: "production", description: "skillDesc.aszf_rag_chat", viewerPath: "/rag-chat" },
  { name: "email_intent_processor", display_name: "Email Intent Processor", status: "in-development", description: "skillDesc.email_intent_processor", viewerPath: "/email-upload" },
  { name: "document_extractor", display_name: "Document Extractor", status: "in-development", description: "skillDesc.document_extractor", viewerPath: "/document-upload" },
  { name: "cubix_course_capture", display_name: "Cubix Course Capture", status: "results-viewer", description: "skillDesc.cubix_course_capture", viewerPath: "/cubix" },
];

const STATUS_COLOR: Record<string, "success" | "info" | "default" | "warning"> = {
  production: "success",
  "in-development": "info",
  "results-viewer": "default",
  stub: "warning",
};

const KPI_ACCENT = ["primary.main", "info.main", "success.main", "warning.main"];

interface RunSummary {
  total: number;
  completed: number;
  totalCost: number;
  source: string | null;
}

export const Dashboard = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunSummary>({ total: 0, completed: 0, totalCost: 0, source: null });
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "offline">("checking");

  useEffect(() => {
    fetch("/api/v1/runs")
      .then((r) => r.json())
      .then((data) => {
        const list = data.runs || [];
        setRuns({
          total: list.length,
          completed: list.filter((r: { status: string }) => r.status === "completed").length,
          totalCost: list.reduce((s: number, r: { total_cost_usd: number }) => s + r.total_cost_usd, 0),
          source: data.source || null,
        });
      })
      .catch(() => {});

    fetch("/health")
      .then((r) => {
        if (r.ok) setBackendStatus("connected");
        else setBackendStatus("offline");
      })
      .catch(() => setBackendStatus("offline"));
  }, []);

  const kpis = [
    { label: "Skills", value: SKILLS.length, sub: `${SKILLS.filter((s) => s.status === "production").length} production`, icon: <SmartToyIcon /> },
    { label: translate("aiflow.dashboard.allRuns"), value: runs.total, sub: `${runs.completed} completed`, icon: <PlayArrowIcon /> },
    { label: translate("aiflow.dashboard.todayCost"), value: `$${runs.totalCost.toFixed(3)}`, sub: "total", icon: <AttachMoneyIcon /> },
    { label: "Completed", value: runs.completed, sub: runs.total > 0 ? `${((runs.completed / runs.total) * 100).toFixed(0)}%` : "-", icon: <CheckCircleIcon /> },
  ];

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: "auto" }}>
      <Title title={translate("aiflow.dashboard.title")} />

      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
        <Typography variant="h5">{translate("aiflow.dashboard.title")}</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          {runs.source && (
            <Chip
              label={translate(`aiflow.status.${runs.source}`)}
              color={runs.source === "demo" ? "warning" : "success"}
              size="small"
              variant="outlined"
            />
          )}
          <Chip
            icon={<CircleIcon sx={{ fontSize: 8 }} />}
            label={translate(`aiflow.dashboard.${backendStatus}`)}
            color={backendStatus === "connected" ? "success" : backendStatus === "offline" ? "error" : "default"}
            variant="outlined"
            size="small"
          />
        </Stack>
      </Stack>
      <Typography variant="body2" color="text.secondary" mb={3}>
        {translate("aiflow.dashboard.subtitle")}
      </Typography>

      {/* KPI Cards */}
      <Grid container spacing={2} mb={4}>
        {kpis.map((kpi, i) => (
          <Grid size={{ xs: 6, md: 3 }} key={kpi.label}>
            <Card sx={{ borderLeft: 4, borderLeftColor: KPI_ACCENT[i] }}>
              <CardContent sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Avatar sx={{ bgcolor: `${KPI_ACCENT[i]}22`, color: KPI_ACCENT[i], width: 48, height: 48 }}>
                  {kpi.icon}
                </Avatar>
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600, fontSize: "0.8rem" }}>
                    {kpi.label}
                  </Typography>
                  <Typography variant="h4" sx={{ lineHeight: 1.1, fontWeight: 700 }}>{kpi.value}</Typography>
                  <Typography variant="caption" color="text.secondary">{kpi.sub}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Skill Cards */}
      <Typography variant="h6" gutterBottom>{translate("aiflow.dashboard.skills")}</Typography>
      <Grid container spacing={2}>
        {SKILLS.map((skill) => (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={skill.name}>
            <Card
              sx={{
                cursor: skill.viewerPath ? "pointer" : "default",
                transition: "transform 0.2s, box-shadow 0.2s",
                "&:hover": skill.viewerPath ? { transform: "translateY(-2px)", boxShadow: 6 } : {},
              }}
              onClick={() => skill.viewerPath && navigate(skill.viewerPath)}
            >
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="subtitle1">{skill.display_name}</Typography>
                  <Chip
                    label={translate(`aiflow.status.${skill.status === "in-development" ? "inDevelopment" : skill.status === "results-viewer" ? "resultsViewer" : skill.status}`)}
                    color={STATUS_COLOR[skill.status] || "default"}
                    size="small"
                  />
                </Stack>
                <Typography variant="body2" color="text.secondary" mb={1.5}>
                  {translate(`aiflow.${skill.description}`)}
                </Typography>
                {skill.viewerPath && (
                  <Stack direction="row" alignItems="center" spacing={0.5}>
                    <Typography variant="caption" color="primary.main" sx={{ fontWeight: 600 }}>
                      {translate("aiflow.dashboard.openViewer")}
                    </Typography>
                    <ArrowForwardIcon sx={{ fontSize: 14, color: "primary.main" }} />
                  </Stack>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};
