import React, { useState, useEffect, useCallback } from "react";
import { useTranslate } from "react-admin";
import {
  Box, Typography, Card, CardContent, Button, IconButton,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Select, FormControl, InputLabel, Switch,
  FormControlLabel, Alert, CircularProgress, Snackbar, Tooltip,
  Collapse,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import WifiIcon from "@mui/icons-material/Wifi";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";

interface ConnectorConfig {
  id: string;
  name: string;
  provider: string;
  host: string | null;
  port: number | null;
  use_ssl: boolean;
  mailbox: string | null;
  filters: Record<string, unknown>;
  polling_interval_minutes: number;
  max_emails_per_fetch: number;
  is_active: boolean;
  last_fetched_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface FetchHistoryItem {
  id: string;
  config_id: string;
  status: string;
  email_count: number;
  new_emails: number;
  duration_ms: number | null;
  error: string | null;
  fetched_at: string | null;
}

const PROVIDERS = ["imap", "o365_graph", "gmail"] as const;

const PROVIDER_LABELS: Record<string, string> = {
  imap: "IMAP",
  o365_graph: "Office 365",
  gmail: "Gmail",
};

const emptyForm = (): Partial<ConnectorConfig> => ({
  name: "",
  provider: "imap",
  host: "",
  port: 993,
  use_ssl: true,
  mailbox: "INBOX",
  polling_interval_minutes: 15,
  max_emails_per_fetch: 50,
});

export const EmailConnectors = () => {
  const translate = useTranslate();
  const [configs, setConfigs] = useState<ConnectorConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<ConnectorConfig>>(emptyForm());
  const [snack, setSnack] = useState<{ message: string; severity: "success" | "error" } | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [fetchingId, setFetchingId] = useState<string | null>(null);
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null);
  const [history, setHistory] = useState<FetchHistoryItem[]>([]);

  const loadConfigs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/emails/connectors");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setConfigs(data);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfigs(); }, [loadConfigs]);

  const handleSave = async () => {
    try {
      const method = editId ? "PUT" : "POST";
      const url = editId
        ? `/api/v1/emails/connectors/${editId}`
        : "/api/v1/emails/connectors";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setDialogOpen(false);
      setEditId(null);
      setForm(emptyForm());
      loadConfigs();
      setSnack({ message: editId ? "Updated" : "Created", severity: "success" });
    } catch (e) {
      setSnack({ message: String(e), severity: "error" });
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(translate("aiflow.connectors.confirmDelete"))) return;
    try {
      await fetch(`/api/v1/emails/connectors/${id}`, { method: "DELETE" });
      loadConfigs();
      setSnack({ message: "Deleted", severity: "success" });
    } catch (e) {
      setSnack({ message: String(e), severity: "error" });
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const res = await fetch(`/api/v1/emails/connectors/${id}/test`, { method: "POST" });
      const data = await res.json();
      setSnack({
        message: data.success
          ? `${translate("aiflow.connectors.testSuccess")}: ${data.message}`
          : `${translate("aiflow.connectors.testFailed")}: ${data.message}`,
        severity: data.success ? "success" : "error",
      });
    } catch (e) {
      setSnack({ message: String(e), severity: "error" });
    } finally {
      setTestingId(null);
    }
  };

  const handleFetch = async (id: string) => {
    setFetchingId(id);
    try {
      const res = await fetch("/api/v1/emails/fetch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config_id: id, limit: 50 }),
      });
      const data = await res.json();
      if (data.error) {
        setSnack({ message: `${translate("aiflow.connectors.fetchFailed")}: ${data.error}`, severity: "error" });
      } else {
        setSnack({
          message: `${translate("aiflow.connectors.fetchSuccess")}: ${data.new_count} new / ${data.total_count} total (${data.duration_ms.toFixed(0)}ms)`,
          severity: "success",
        });
      }
      loadConfigs();
    } catch (e) {
      setSnack({ message: String(e), severity: "error" });
    } finally {
      setFetchingId(null);
    }
  };

  const toggleHistory = async (id: string) => {
    if (expandedHistory === id) {
      setExpandedHistory(null);
      return;
    }
    try {
      const res = await fetch(`/api/v1/emails/connectors/${id}/history`);
      const data = await res.json();
      setHistory(data);
      setExpandedHistory(id);
    } catch (e) {
      setSnack({ message: String(e), severity: "error" });
    }
  };

  const openEdit = (config: ConnectorConfig) => {
    setEditId(config.id);
    setForm({ ...config });
    setDialogOpen(true);
  };

  const openCreate = () => {
    setEditId(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  if (loading) return <Box sx={{ p: 4, textAlign: "center" }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">{translate("aiflow.connectors.title")}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          {translate("aiflow.connectors.create")}
        </Button>
      </Box>

      {configs.length === 0 ? (
        <Card>
          <CardContent>
            <Typography color="text.secondary">{translate("aiflow.connectors.noConnectors")}</Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{translate("aiflow.connectors.name")}</TableCell>
                <TableCell>{translate("aiflow.connectors.provider")}</TableCell>
                <TableCell>{translate("aiflow.connectors.host")}</TableCell>
                <TableCell>{translate("aiflow.connectors.mailbox")}</TableCell>
                <TableCell>{translate("aiflow.connectors.pollingInterval")}</TableCell>
                <TableCell>{translate("aiflow.connectors.active")}</TableCell>
                <TableCell>{translate("aiflow.connectors.lastFetched")}</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {configs.map((c) => (
                <React.Fragment key={c.id}>
                  <TableRow hover>
                    <TableCell><strong>{c.name}</strong></TableCell>
                    <TableCell>
                      <Chip label={PROVIDER_LABELS[c.provider] || c.provider} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{c.host}{c.port ? `:${c.port}` : ""}</TableCell>
                    <TableCell>{c.mailbox || "-"}</TableCell>
                    <TableCell>{c.polling_interval_minutes} min</TableCell>
                    <TableCell>
                      <Chip
                        label={c.is_active ? translate("aiflow.connectors.active") : "Inactive"}
                        color={c.is_active ? "success" : "default"}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {c.last_fetched_at ? new Date(c.last_fetched_at).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title={translate("aiflow.connectors.testConnection")}>
                        <span>
                          <IconButton size="small" onClick={() => handleTest(c.id)} disabled={testingId === c.id}>
                            {testingId === c.id ? <CircularProgress size={18} /> : <WifiIcon />}
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title={translate("aiflow.connectors.fetchNow")}>
                        <span>
                          <IconButton size="small" onClick={() => handleFetch(c.id)} disabled={fetchingId === c.id}>
                            {fetchingId === c.id ? <CircularProgress size={18} /> : <PlayArrowIcon />}
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title={translate("aiflow.connectors.history")}>
                        <IconButton size="small" onClick={() => toggleHistory(c.id)}>
                          {expandedHistory === c.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={translate("aiflow.connectors.edit")}>
                        <IconButton size="small" onClick={() => openEdit(c)}>
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={translate("aiflow.connectors.delete")}>
                        <IconButton size="small" color="error" onClick={() => handleDelete(c.id)}>
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                  {expandedHistory === c.id && (
                    <TableRow>
                      <TableCell colSpan={8} sx={{ p: 0 }}>
                        <Collapse in={expandedHistory === c.id}>
                          <Box sx={{ p: 2, bgcolor: "action.hover" }}>
                            <Typography variant="subtitle2" gutterBottom>
                              {translate("aiflow.connectors.history")}
                            </Typography>
                            {history.length === 0 ? (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            ) : (
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell>{translate("aiflow.connectors.status")}</TableCell>
                                    <TableCell>{translate("aiflow.connectors.emailCount")}</TableCell>
                                    <TableCell>New</TableCell>
                                    <TableCell>Duration</TableCell>
                                    <TableCell>Error</TableCell>
                                    <TableCell>Date</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {history.map((h) => (
                                    <TableRow key={h.id}>
                                      <TableCell>
                                        <Chip
                                          label={h.status}
                                          size="small"
                                          color={h.status === "completed" ? "success" : h.status === "failed" ? "error" : "default"}
                                        />
                                      </TableCell>
                                      <TableCell>{h.email_count}</TableCell>
                                      <TableCell>{h.new_emails}</TableCell>
                                      <TableCell>{h.duration_ms ? `${h.duration_ms.toFixed(0)}ms` : "-"}</TableCell>
                                      <TableCell>{h.error || "-"}</TableCell>
                                      <TableCell>{h.fetched_at ? new Date(h.fetched_at).toLocaleString() : "-"}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editId ? translate("aiflow.connectors.edit") : translate("aiflow.connectors.create")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <TextField
            label={translate("aiflow.connectors.name")}
            value={form.name || ""}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            fullWidth
          />
          <FormControl fullWidth>
            <InputLabel>{translate("aiflow.connectors.provider")}</InputLabel>
            <Select
              value={form.provider || "imap"}
              label={translate("aiflow.connectors.provider")}
              onChange={(e) => setForm({ ...form, provider: e.target.value })}
            >
              {PROVIDERS.map((p) => (
                <MenuItem key={p} value={p}>{PROVIDER_LABELS[p]}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label={translate("aiflow.connectors.host")}
            value={form.host || ""}
            onChange={(e) => setForm({ ...form, host: e.target.value })}
            fullWidth
          />
          <TextField
            label={translate("aiflow.connectors.port")}
            type="number"
            value={form.port || ""}
            onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || null })}
            fullWidth
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.use_ssl ?? true}
                onChange={(e) => setForm({ ...form, use_ssl: e.target.checked })}
              />
            }
            label={translate("aiflow.connectors.ssl")}
          />
          <TextField
            label={translate("aiflow.connectors.mailbox")}
            value={form.mailbox || ""}
            onChange={(e) => setForm({ ...form, mailbox: e.target.value })}
            fullWidth
          />
          <TextField
            label={translate("aiflow.connectors.credentials")}
            value={form.credentials_encrypted || ""}
            onChange={(e) => setForm({ ...form, credentials_encrypted: e.target.value })}
            type="password"
            fullWidth
          />
          <TextField
            label={translate("aiflow.connectors.pollingInterval")}
            type="number"
            value={form.polling_interval_minutes || 15}
            onChange={(e) => setForm({ ...form, polling_interval_minutes: parseInt(e.target.value) || 15 })}
            fullWidth
          />
          <TextField
            label={translate("aiflow.connectors.maxEmails")}
            type="number"
            value={form.max_emails_per_fetch || 50}
            onChange={(e) => setForm({ ...form, max_emails_per_fetch: parseInt(e.target.value) || 50 })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" onClick={handleSave}>{translate("ra.action.save")}</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={!!snack}
        autoHideDuration={4000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        {snack ? (
          <Alert severity={snack.severity} onClose={() => setSnack(null)} variant="filled">
            {snack.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  );
};
