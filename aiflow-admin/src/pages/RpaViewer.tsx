import { useState, useEffect, useCallback } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import {
  Box, Typography, Button, Stack, Card, CardContent, Chip,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  CircularProgress, Alert, IconButton, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";

interface RpaConfig {
  id: string;
  name: string;
  description: string | null;
  yaml_config: string;
  target_url: string | null;
  is_active: boolean;
  schedule_cron: string | null;
  created_at: string;
  source: string;
}

interface RpaExecution {
  id: string;
  config_id: string;
  status: string;
  steps_total: number | null;
  steps_completed: number;
  results: Record<string, unknown> | null;
  error: string | null;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
  source: string;
}

const YAML_PLACEHOLDER = `steps:
  - name: navigate
    action: goto
    url: "https://example.com"
  - name: click_button
    action: click
    selector: "#login-btn"
  - name: capture
    action: screenshot`;

function countYamlSteps(yaml: string): number {
  return (yaml.match(/^\s*- (?:action|name):/gm) || []).length;
}

export const RpaViewer = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const [configs, setConfigs] = useState<RpaConfig[]>([]);
  const [executions, setExecutions] = useState<RpaExecution[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(true);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<RpaConfig | null>(null);
  const [deleteDialogId, setDeleteDialogId] = useState<string | null>(null);
  const [executing, setExecuting] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState("");
  const [formTargetUrl, setFormTargetUrl] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formYaml, setFormYaml] = useState(YAML_PLACEHOLDER);
  const [formSchedule, setFormSchedule] = useState("");

  const fetchConfigs = useCallback(async () => {
    setLoadingConfigs(true);
    try {
      const res = await fetch("/api/v1/rpa/configs");
      if (res.ok) {
        const data = await res.json();
        setConfigs(data.configs || []);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load configs");
    } finally {
      setLoadingConfigs(false);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    setLoadingLogs(true);
    try {
      const res = await fetch("/api/v1/rpa/logs?limit=50");
      if (res.ok) {
        const data = await res.json();
        setExecutions(data.executions || []);
      }
    } catch {
      // logs are secondary, don't block
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  useEffect(() => { fetchConfigs(); fetchLogs(); }, [fetchConfigs, fetchLogs]);

  const openCreateDialog = () => {
    setEditingConfig(null);
    setFormName("");
    setFormTargetUrl("");
    setFormDescription("");
    setFormYaml(YAML_PLACEHOLDER);
    setFormSchedule("");
    setDialogOpen(true);
  };

  const openEditDialog = (config: RpaConfig) => {
    setEditingConfig(config);
    setFormName(config.name);
    setFormTargetUrl(config.target_url || "");
    setFormDescription(config.description || "");
    setFormYaml(config.yaml_config);
    setFormSchedule(config.schedule_cron || "");
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!formName.trim() || !formYaml.trim()) return;
    try {
      const body = {
        name: formName,
        target_url: formTargetUrl || null,
        description: formDescription || null,
        yaml_config: formYaml,
        schedule_cron: formSchedule || null,
      };
      const url = editingConfig
        ? `/api/v1/rpa/configs/${editingConfig.id}`
        : "/api/v1/rpa/configs";
      const method = editingConfig ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || "Save failed");
      }
      notify("aiflow.rpa.createSuccess", { type: "success" });
      setDialogOpen(false);
      fetchConfigs();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Save failed", { type: "error" });
    }
  };

  const handleDelete = async () => {
    if (!deleteDialogId) return;
    try {
      await fetch(`/api/v1/rpa/configs/${deleteDialogId}`, { method: "DELETE" });
      notify("aiflow.rpa.deleteSuccess", { type: "success" });
      setDeleteDialogId(null);
      fetchConfigs();
      fetchLogs();
    } catch {
      notify("Delete failed", { type: "error" });
    }
  };

  const handleExecute = async (configId: string) => {
    setExecuting(configId);
    try {
      const res = await fetch(`/api/v1/rpa/configs/${configId}/execute`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || "Execution failed");
      }
      notify("aiflow.rpa.executeSuccess", { type: "success" });
      fetchLogs();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Execution failed", { type: "error" });
    } finally {
      setExecuting(null);
    }
  };

  const statusColor = (s: string): "success" | "warning" | "error" | "default" => {
    if (s === "completed") return "success";
    if (s === "running") return "warning";
    if (s === "failed") return "error";
    return "default";
  };

  const getConfigName = (configId: string): string => {
    const cfg = configs.find((c) => c.id === configId);
    return cfg?.name || configId.slice(0, 8);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Title title={translate("aiflow.rpa.title")} />

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>{translate("aiflow.rpa.title")}</Typography>
          <Typography variant="body2" color="text.secondary">{translate("aiflow.rpa.subtitle")}</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>
          {translate("aiflow.rpa.newConfig")}
        </Button>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Configs Table */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ pb: 0 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{translate("aiflow.rpa.configsTitle")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {configs.length} {translate("aiflow.rpa.configsCount")}
            </Typography>
          </Stack>
        </CardContent>
        {loadingConfigs ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}><CircularProgress /></Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{translate("aiflow.rpa.name")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.targetUrl")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.steps")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.active")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.schedule")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.created")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {configs.map((cfg) => (
                  <TableRow key={cfg.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>{cfg.name}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="primary" sx={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {cfg.target_url || "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>{countYamlSteps(cfg.yaml_config)}</TableCell>
                    <TableCell>
                      <Chip
                        label={cfg.is_active ? translate("aiflow.rpa.active") : translate("aiflow.rpa.inactive")}
                        size="small"
                        color={cfg.is_active ? "success" : "default"}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {cfg.schedule_cron || "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(cfg.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5}>
                        <IconButton
                          size="small"
                          color="primary"
                          title={translate("aiflow.rpa.run")}
                          onClick={() => handleExecute(cfg.id)}
                          disabled={executing === cfg.id}
                        >
                          {executing === cfg.id ? <CircularProgress size={18} /> : <PlayArrowIcon fontSize="small" />}
                        </IconButton>
                        <IconButton size="small" title={translate("aiflow.rpa.edit")} onClick={() => openEditDialog(cfg)}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" title={translate("aiflow.rpa.delete")} onClick={() => setDeleteDialogId(cfg.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {configs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary" py={3}>{translate("aiflow.rpa.noConfigs")}</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {/* Execution Log */}
      <Card>
        <CardContent sx={{ pb: 0 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{translate("aiflow.rpa.logsTitle")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {executions.length} {translate("aiflow.rpa.logsCount")}
            </Typography>
          </Stack>
        </CardContent>
        {loadingLogs ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}><CircularProgress /></Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{translate("aiflow.rpa.config")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.status")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.stepsProgress")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.duration")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.started")}</TableCell>
                  <TableCell>{translate("aiflow.rpa.error")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {executions.map((exec) => (
                  <TableRow key={exec.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>{getConfigName(exec.config_id)}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={translate(`aiflow.rpa.${exec.status}`)} size="small" color={statusColor(exec.status)} />
                    </TableCell>
                    <TableCell>
                      {exec.steps_total ? `${exec.steps_completed} / ${exec.steps_total}` : "—"}
                    </TableCell>
                    <TableCell>
                      {exec.duration_ms != null ? `${(exec.duration_ms / 1000).toFixed(1)}s` : "—"}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {exec.started_at ? new Date(exec.started_at).toLocaleString() : "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {exec.error ? (
                        <Typography variant="body2" color="error" sx={{ maxWidth: 350, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {exec.error}
                        </Typography>
                      ) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
                {executions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary" py={3}>{translate("aiflow.rpa.noLogs")}</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingConfig ? translate("aiflow.rpa.editTitle") : translate("aiflow.rpa.dialogTitle")}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label={translate("aiflow.rpa.name")}
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              required
              fullWidth
              size="small"
            />
            <TextField
              label={translate("aiflow.rpa.targetUrl")}
              value={formTargetUrl}
              onChange={(e) => setFormTargetUrl(e.target.value)}
              fullWidth
              size="small"
              placeholder="https://example.com"
            />
            <TextField
              label={translate("aiflow.rpa.description")}
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              fullWidth
              size="small"
            />
            <TextField
              label={translate("aiflow.rpa.yamlConfig")}
              value={formYaml}
              onChange={(e) => setFormYaml(e.target.value)}
              required
              fullWidth
              multiline
              minRows={6}
              maxRows={14}
              InputProps={{ sx: { fontFamily: "monospace", fontSize: 13 } }}
            />
            <TextField
              label={translate("aiflow.rpa.schedule")}
              value={formSchedule}
              onChange={(e) => setFormSchedule(e.target.value)}
              fullWidth
              size="small"
              placeholder="0 6 * * * (optional cron)"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" onClick={handleSave} disabled={!formName.trim() || !formYaml.trim()}>
            {editingConfig ? translate("ra.action.save") : translate("aiflow.rpa.dialogCreate")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={!!deleteDialogId} onClose={() => setDeleteDialogId(null)}>
        <DialogTitle>{translate("aiflow.rpa.deleteTitle")}</DialogTitle>
        <DialogContent>
          <Typography>{translate("aiflow.rpa.deleteConfirm")}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogId(null)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>{translate("ra.action.delete")}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
