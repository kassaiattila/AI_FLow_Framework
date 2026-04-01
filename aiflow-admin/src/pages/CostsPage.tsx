import { useState, useEffect, useMemo } from "react";
import { useTranslate, Title } from "react-admin";
import {
  Card, CardContent, Typography, Box, Chip, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  CircularProgress, Alert,
} from "@mui/material";

interface StepExecution {
  step_name: string;
  cost_usd: number;
  tokens_used: number;
  duration_ms: number;
}

interface Run {
  run_id: string;
  skill_name: string;
  status: string;
  total_cost_usd: number;
  total_duration_ms: number;
  steps: StepExecution[];
}

interface SkillCost {
  skill: string;
  runs: number;
  totalCost: number;
  totalTokens: number;
  totalDuration: number;
  avgCost: number;
}

interface StepCost {
  skill: string;
  step: string;
  calls: number;
  totalCost: number;
  totalTokens: number;
  avgCost: number;
}

export const CostsPage = () => {
  const translate = useTranslate();
  const [runs, setRuns] = useState<Run[]>([]);
  const [source, setSource] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/runs")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setRuns(data.runs || []);
        setSource(data.source || null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const { skillCosts, stepCosts, totals } = useMemo(() => {
    const bySkill = new Map<string, SkillCost>();
    const byStep = new Map<string, StepCost>();
    let totalCost = 0;
    let totalTokens = 0;

    for (const run of runs) {
      totalCost += run.total_cost_usd;

      const existing = bySkill.get(run.skill_name) || {
        skill: run.skill_name, runs: 0, totalCost: 0, totalTokens: 0, totalDuration: 0, avgCost: 0,
      };
      existing.runs++;
      existing.totalCost += run.total_cost_usd;
      existing.totalDuration += run.total_duration_ms;

      for (const step of run.steps || []) {
        const stepTokens = (step.tokens_used ?? 0) || ((step as Record<string, unknown>).input_tokens as number ?? 0) + ((step as Record<string, unknown>).output_tokens as number ?? 0);
        existing.totalTokens += stepTokens;
        totalTokens += stepTokens;

        const key = `${run.skill_name}::${step.step_name}`;
        const s = byStep.get(key) || {
          skill: run.skill_name, step: step.step_name, calls: 0, totalCost: 0, totalTokens: 0, avgCost: 0,
        };
        s.calls++;
        s.totalCost += step.cost_usd || 0;
        s.totalTokens += stepTokens;
        byStep.set(key, s);
      }

      existing.avgCost = existing.totalCost / existing.runs;
      bySkill.set(run.skill_name, existing);
    }

    const stepCosts = [...byStep.values()]
      .map((s) => ({ ...s, avgCost: s.totalCost / s.calls }))
      .sort((a, b) => b.totalCost - a.totalCost);

    return {
      skillCosts: [...bySkill.values()].sort((a, b) => b.totalCost - a.totalCost),
      stepCosts,
      totals: { cost: totalCost, tokens: totalTokens, runs: runs.length },
    };
  }, [runs]);

  const fmt = (usd: number) => `$${usd.toFixed(4)}`;
  const fmtTokens = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;

  if (loading) return <Box sx={{ p: 4, textAlign: "center" }}><CircularProgress /></Box>;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.costs.title")} />

      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">{translate("aiflow.costs.title")}</Typography>
        {source && (
          <Chip
            label={translate(`aiflow.status.${source}`)}
            color={source === "demo" ? "warning" : "success"}
            size="small"
          />
        )}
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* KPI cards */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="caption" color="text.secondary">{translate("aiflow.costs.totalCost")}</Typography>
            <Typography variant="h4">{fmt(totals.cost)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="caption" color="text.secondary">{translate("aiflow.costs.totalTokens")}</Typography>
            <Typography variant="h4">{fmtTokens(totals.tokens)}</Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="caption" color="text.secondary">{translate("aiflow.costs.totalRuns")}</Typography>
            <Typography variant="h4">{totals.runs}</Typography>
          </CardContent>
        </Card>
      </Stack>

      {/* Skill cost bar chart */}
      {skillCosts.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>{translate("aiflow.costs.bySkill")}</Typography>
          <Stack spacing={1}>
            {skillCosts.map((s) => {
              const maxCost = skillCosts[0]?.totalCost || 1;
              const pct = (s.totalCost / maxCost) * 100;
              return (
                <Stack key={s.skill} direction="row" alignItems="center" spacing={1.5}>
                  <Typography variant="body2" sx={{ minWidth: 160, fontSize: "0.8rem" }}>{s.skill}</Typography>
                  <Box sx={{ flex: 1, height: 20, bgcolor: "action.hover", borderRadius: 1, overflow: "hidden" }}>
                    <Box sx={{ width: `${pct}%`, height: "100%", bgcolor: "primary.main", borderRadius: 1, transition: "width 0.5s" }} />
                  </Box>
                  <Typography variant="body2" sx={{ minWidth: 65, textAlign: "right", fontSize: "0.8rem", fontWeight: 600 }}>
                    {fmt(s.totalCost)}
                  </Typography>
                </Stack>
              );
            })}
          </Stack>
        </Paper>
      )}

      {/* Per-skill breakdown table */}
      <Typography variant="h6" gutterBottom>{translate("aiflow.costs.bySkill")}</Typography>
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Skill</TableCell>
              <TableCell align="right">{translate("aiflow.costs.runs")}</TableCell>
              <TableCell align="right">{translate("aiflow.costs.totalCostCol")}</TableCell>
              <TableCell align="right">{translate("aiflow.costs.avgCost")}</TableCell>
              <TableCell align="right">Tokens</TableCell>
              <TableCell align="right">{translate("aiflow.costs.avgDuration")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {skillCosts.map((s) => (
              <TableRow key={s.skill}>
                <TableCell>{s.skill}</TableCell>
                <TableCell align="right">{s.runs}</TableCell>
                <TableCell align="right">{fmt(s.totalCost)}</TableCell>
                <TableCell align="right">{fmt(s.avgCost)}</TableCell>
                <TableCell align="right">{fmtTokens(s.totalTokens)}</TableCell>
                <TableCell align="right">{(s.totalDuration / s.runs / 1000).toFixed(1)}s</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Per-step breakdown */}
      <Typography variant="h6" gutterBottom>{translate("aiflow.costs.byStep")}</Typography>
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Skill</TableCell>
              <TableCell>Step</TableCell>
              <TableCell align="right">{translate("aiflow.costs.calls")}</TableCell>
              <TableCell align="right">{translate("aiflow.costs.totalCostCol")}</TableCell>
              <TableCell align="right">{translate("aiflow.costs.avgCost")}</TableCell>
              <TableCell align="right">Tokens</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {stepCosts.map((s) => (
              <TableRow key={`${s.skill}::${s.step}`}>
                <TableCell>{s.skill}</TableCell>
                <TableCell>{s.step}</TableCell>
                <TableCell align="right">{s.calls}</TableCell>
                <TableCell align="right">{fmt(s.totalCost)}</TableCell>
                <TableCell align="right">{fmt(s.avgCost)}</TableCell>
                <TableCell align="right">{fmtTokens(s.totalTokens)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};
