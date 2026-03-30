import { useEffect, useState } from "react";
import { Card, CardContent, Typography, Grid, Box, Chip } from "@mui/material";
import { useTranslate, Title } from "react-admin";

interface SkillInfo {
  name: string;
  display_name: string;
  status: string;
  description: string;
}

const SKILLS: SkillInfo[] = [
  { name: "process_documentation", display_name: "Process Documentation", status: "production", description: "BPMN diagrams from natural language" },
  { name: "aszf_rag_chat", display_name: "ASZF RAG Chat", status: "production", description: "Legal document RAG chat (86% eval pass)" },
  { name: "email_intent_processor", display_name: "Email Intent Processor", status: "in-development", description: "Email classification & routing (hybrid ML+LLM)" },
  { name: "invoice_processor", display_name: "Invoice Processor", status: "in-development", description: "PDF invoice extraction (parse step only)" },
  { name: "cubix_course_capture", display_name: "Cubix Course Capture", status: "results-viewer", description: "Video transcript pipeline (CLI only)" },
];

const STATUS_COLOR: Record<string, "success" | "info" | "default" | "warning"> = {
  production: "success",
  "in-development": "info",
  "results-viewer": "default",
  stub: "warning",
};

interface RunSummary {
  total: number;
  completed: number;
  totalCost: number;
}

export const Dashboard = () => {
  const translate = useTranslate();
  const [runs, setRuns] = useState<RunSummary>({ total: 0, completed: 0, totalCost: 0 });

  useEffect(() => {
    fetch("/api/runs")
      .then((r) => r.json())
      .then((data) => {
        const list = data.runs || [];
        setRuns({
          total: list.length,
          completed: list.filter((r: { status: string }) => r.status === "completed").length,
          totalCost: list.reduce((s: number, r: { total_cost_usd: number }) => s + r.total_cost_usd, 0),
        });
      })
      .catch(() => {});
  }, []);

  return (
    <Box p={2}>
      <Title title={translate("aiflow.dashboard.title")} />
      <Typography variant="h5" gutterBottom>{translate("aiflow.dashboard.title")}</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>{translate("aiflow.dashboard.subtitle")}</Typography>

      {/* KPIs */}
      <Grid container spacing={2} mb={4}>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card><CardContent>
            <Typography variant="caption" color="text.secondary">Skills</Typography>
            <Typography variant="h4">{SKILLS.length}</Typography>
            <Typography variant="caption" color="text.secondary">{SKILLS.filter((s) => s.status === "production").length} production</Typography>
          </CardContent></Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card><CardContent>
            <Typography variant="caption" color="text.secondary">{translate("aiflow.dashboard.allRuns")}</Typography>
            <Typography variant="h4">{runs.total}</Typography>
            <Typography variant="caption" color="text.secondary">{runs.completed} completed</Typography>
          </CardContent></Card>
        </Grid>
        <Grid size={{ xs: 6, md: 3 }}>
          <Card><CardContent>
            <Typography variant="caption" color="text.secondary">{translate("aiflow.dashboard.todayCost")}</Typography>
            <Typography variant="h4">${runs.totalCost.toFixed(3)}</Typography>
            <Typography variant="caption" color="text.secondary">total</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>

      {/* Skill Cards */}
      <Typography variant="h6" gutterBottom>{translate("aiflow.dashboard.skills")}</Typography>
      <Grid container spacing={2}>
        {SKILLS.map((skill) => (
          <Grid size={{ xs: 12, md: 4 }} key={skill.name}>
            <Card sx={{ cursor: "pointer", "&:hover": { boxShadow: 4 } }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="subtitle2">{skill.display_name}</Typography>
                  <Chip label={translate(`aiflow.status.${skill.status === "in-development" ? "inDevelopment" : skill.status === "results-viewer" ? "resultsViewer" : skill.status}`)} color={STATUS_COLOR[skill.status] || "default"} size="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">{skill.description}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};
