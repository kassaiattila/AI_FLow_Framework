import { useState, useEffect, useCallback } from "react";
import { useTranslate, Title } from "react-admin";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stack,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Grid,
  Tooltip,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningIcon from "@mui/icons-material/Warning";
import ErrorIcon from "@mui/icons-material/Error";

interface ServiceHealth {
  service_name: string;
  status: string;
  latency_ms: number;
  details: Record<string, unknown> | null;
  checked_at: string;
}

interface HealthResponse {
  services: ServiceHealth[];
  total: number;
  overall_status: string;
  source: string;
}

interface ServiceMetric {
  service_name: string;
  check_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  success_rate: number;
}

interface MetricsResponse {
  metrics: ServiceMetric[];
  source: string;
}

const statusIcon = (status: string) => {
  switch (status) {
    case "healthy":
      return <CheckCircleIcon sx={{ color: "success.main", fontSize: 18 }} />;
    case "degraded":
      return <WarningIcon sx={{ color: "warning.main", fontSize: 18 }} />;
    default:
      return <ErrorIcon sx={{ color: "error.main", fontSize: 18 }} />;
  }
};

const statusColor = (status: string) => {
  switch (status) {
    case "healthy":
      return "success" as const;
    case "degraded":
      return "warning" as const;
    default:
      return "error" as const;
  }
};

export const MonitoringDashboard = () => {
  const translate = useTranslate();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthRes, metricsRes] = await Promise.all([
        fetch("/api/v1/admin/health"),
        fetch("/api/v1/admin/metrics"),
      ]);
      if (!healthRes.ok || !metricsRes.ok) throw new Error("API error");
      const healthData: HealthResponse = await healthRes.json();
      const metricsData: MetricsResponse = await metricsRes.json();
      setHealth(healthData);
      setMetrics(metricsData);
      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getMetric = (serviceName: string): ServiceMetric | undefined =>
    metrics?.metrics.find((m) => m.service_name === serviceName);

  const avgLatency =
    metrics?.metrics.length
      ? Math.round(
          metrics.metrics.reduce((s, m) => s + m.avg_latency_ms, 0) /
            metrics.metrics.length
        )
      : 0;

  const avgP95 =
    metrics?.metrics.length
      ? Math.round(
          metrics.metrics.reduce((s, m) => s + m.p95_latency_ms, 0) /
            metrics.metrics.length
        )
      : 0;

  const overallUptime =
    metrics?.metrics.length
      ? Math.round(
          (metrics.metrics.reduce((s, m) => s + m.success_rate, 0) /
            metrics.metrics.length) *
            10
        ) / 10
      : 0;

  const healthyCount =
    health?.services.filter((s) => s.status === "healthy").length ?? 0;
  const degradedCount =
    health?.services.filter((s) => s.status === "degraded").length ?? 0;
  const downCount =
    health?.services.filter(
      (s) => s.status !== "healthy" && s.status !== "degraded"
    ).length ?? 0;

  const timeSinceRefresh = () => {
    const seconds = Math.round(
      (new Date().getTime() - lastRefresh.getTime()) / 1000
    );
    if (seconds < 60) return `${seconds}s`;
    return `${Math.round(seconds / 60)}m`;
  };

  const getServiceDetail = (svc: ServiceHealth): string => {
    if (!svc.details) return "";
    if ("version" in svc.details) return String(svc.details.version);
    if ("record_count" in svc.details)
      return `${svc.details.record_count} ${translate("aiflow.monitoring.records")}`;
    return "";
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.monitoring.title")} />

      {/* Page Header */}
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {translate("aiflow.monitoring.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {translate("aiflow.monitoring.subtitle")}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {health?.source && (
            <Chip
              label={health.source === "backend" ? "Live" : "Demo"}
              color={health.source === "backend" ? "success" : "warning"}
              size="small"
            />
          )}
          <Button
            startIcon={<RefreshIcon />}
            onClick={fetchData}
            size="small"
            disabled={loading}
          >
            {translate("ra.action.refresh")}
          </Button>
        </Stack>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} action={
          <Button color="inherit" size="small" onClick={fetchData}>
            {translate("aiflow.pipeline.retry")}
          </Button>
        }>
          {error}
        </Alert>
      )}

      {loading && !health ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : health ? (
        <>
          {/* Status Banner */}
          <Alert
            severity={statusColor(health.overall_status)}
            icon={statusIcon(health.overall_status)}
            sx={{ mb: 3 }}
          >
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography fontWeight={600}>
                {health.overall_status === "healthy"
                  ? translate("aiflow.monitoring.allOperational")
                  : translate("aiflow.monitoring.degradedBanner")}
                {" — "}
                {healthyCount}/{health.total}{" "}
                {translate("aiflow.monitoring.servicesHealthy")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {translate("aiflow.monitoring.lastChecked")}: {timeSinceRefresh()}{" "}
                {translate("aiflow.monitoring.ago")}
              </Typography>
            </Stack>
          </Alert>

          {/* KPI Cards */}
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.monitoring.totalServices")}
                  </Typography>
                  <Typography variant="h4" fontWeight={700}>
                    {health.total}
                  </Typography>
                  <Typography variant="body2" color="success.main">
                    {healthyCount} {translate("aiflow.monitoring.healthy")} · {degradedCount}{" "}
                    {translate("aiflow.monitoring.degraded")} · {downCount}{" "}
                    {translate("aiflow.monitoring.down")}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.monitoring.avgLatency")}
                  </Typography>
                  <Typography variant="h4" fontWeight={700}>
                    {avgLatency} ms
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    p95: {avgP95} ms
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.monitoring.overallUptime")}
                  </Typography>
                  <Typography
                    variant="h4"
                    fontWeight={700}
                    color={overallUptime >= 99 ? "success.main" : "warning.main"}
                  >
                    {overallUptime}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {translate("aiflow.monitoring.successRate")}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Service Health Section */}
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            {translate("aiflow.monitoring.serviceHealth")}
          </Typography>
          <Grid container spacing={2}>
            {health.services.map((svc) => {
              const metric = getMetric(svc.service_name);
              return (
                <Grid size={{ xs: 12, sm: 6, md: 4 }} key={svc.service_name}>
                  <Card
                    variant="outlined"
                    sx={{
                      borderColor:
                        svc.status === "healthy"
                          ? "divider"
                          : svc.status === "degraded"
                            ? "warning.main"
                            : "error.main",
                    }}
                  >
                    <CardContent>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                        {statusIcon(svc.status)}
                        <Typography fontWeight={600}>
                          {svc.service_name
                            .replace(/_/g, " ")
                            .replace(/\b\w/g, (c) => c.toUpperCase())}
                        </Typography>
                      </Stack>
                      <Chip
                        label={translate(`aiflow.monitoring.${svc.status}`)}
                        color={statusColor(svc.status)}
                        size="small"
                        sx={{ mb: 1 }}
                      />
                      <Typography variant="body2" color="text.secondary">
                        {translate("aiflow.monitoring.latencyLabel")}:{" "}
                        {Math.round(svc.latency_ms)} ms
                        {metric && (
                          <>
                            {" · p95: "}
                            {Math.round(metric.p95_latency_ms)} ms{" · "}
                            {translate("aiflow.monitoring.uptimeLabel")}:{" "}
                            {metric.success_rate}%
                          </>
                        )}
                      </Typography>
                      {getServiceDetail(svc) && (
                        <Tooltip title={JSON.stringify(svc.details)}>
                          <Typography variant="caption" color="text.disabled">
                            {getServiceDetail(svc)}
                          </Typography>
                        </Tooltip>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>
        </>
      ) : null}
    </Box>
  );
};
