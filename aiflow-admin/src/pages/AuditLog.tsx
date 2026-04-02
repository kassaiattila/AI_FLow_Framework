import { useState, useEffect, useCallback } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import {
  Box,
  Typography,
  Stack,
  Chip,
  CircularProgress,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  TablePagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import RefreshIcon from "@mui/icons-material/Refresh";

interface AuditEntry {
  id: number;
  action: string;
  resource_type: string;
  resource_id: string;
  user_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

interface AuditResponse {
  entries: AuditEntry[];
  total: number;
  source: string;
}

export const AuditLog = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const [data, setData] = useState<AuditResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [actionFilter, setActionFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (actionFilter) params.set("action", actionFilter);
      if (searchQuery) params.set("q", searchQuery);
      const url = `/api/v1/admin/audit${params.toString() ? `?${params}` : ""}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error("API error");
      const result: AuditResponse = await res.json();
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [actionFilter, searchQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = async (format: "csv" | "json") => {
    try {
      const res = await fetch("/api/v1/admin/audit/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format }),
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-log.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      notify(translate("aiflow.audit.exportSuccess"), { type: "success" });
    } catch {
      notify(translate("aiflow.audit.exportFailed"), { type: "error" });
    }
  };

  const uniqueActions = data
    ? [...new Set(data.entries.map((e) => e.action))]
    : [];

  const filteredEntries = data?.entries ?? [];
  const paginatedEntries = filteredEntries.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const formatTimestamp = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleString();
  };

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.audit.title")} />

      {/* Page Header */}
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {translate("aiflow.audit.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {translate("aiflow.audit.subtitle")}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          {data?.source && (
            <Chip
              label={data.source === "backend" ? "Live" : "Demo"}
              color={data.source === "backend" ? "success" : "warning"}
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
          <Button
            variant="contained"
            startIcon={<FileDownloadIcon />}
            onClick={() => handleExport("csv")}
            size="small"
          >
            {translate("aiflow.audit.export")}
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

      {/* Filter Bar */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>{translate("aiflow.audit.filterAction")}</InputLabel>
          <Select
            value={actionFilter}
            label={translate("aiflow.audit.filterAction")}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(0);
            }}
          >
            <MenuItem value="">{translate("aiflow.audit.all")}</MenuItem>
            {uniqueActions.map((a) => (
              <MenuItem key={a} value={a}>
                {a}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          size="small"
          placeholder={translate("aiflow.audit.search")}
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 250 }}
        />
      </Stack>

      {loading && !data ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Card variant="outlined">
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {translate("aiflow.audit.timestamp")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {translate("aiflow.audit.action")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {translate("aiflow.audit.resource")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {translate("aiflow.audit.user")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    {translate("aiflow.audit.details")}
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedEntries.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">
                        {translate("aiflow.audit.noEntries")}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedEntries.map((entry) => (
                    <TableRow
                      key={entry.id}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => setSelectedEntry(entry)}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                          {formatTimestamp(entry.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={entry.action} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        {entry.resource_type}
                        {entry.resource_id ? ` #${entry.resource_id}` : ""}
                      </TableCell>
                      <TableCell>{entry.user_id || "system"}</TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            maxWidth: 300,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {entry.details
                            ? JSON.stringify(entry.details).slice(0, 80)
                            : "—"}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={filteredEntries.length}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10));
              setPage(0);
            }}
            labelRowsPerPage={translate("ra.navigation.page_rows_per_page")}
          />
        </Card>
      )}

      {/* Detail Dialog */}
      <Dialog
        open={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        maxWidth="md"
        fullWidth
      >
        {selectedEntry && (
          <>
            <DialogTitle>
              {translate("aiflow.audit.entryDetail")} #{selectedEntry.id}
            </DialogTitle>
            <DialogContent>
              <Stack spacing={2} sx={{ mt: 1 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.audit.timestamp")}
                  </Typography>
                  <Typography>{formatTimestamp(selectedEntry.created_at)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.audit.action")}
                  </Typography>
                  <Typography>{selectedEntry.action}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.audit.resource")}
                  </Typography>
                  <Typography>
                    {selectedEntry.resource_type} #{selectedEntry.resource_id}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.audit.user")}
                  </Typography>
                  <Typography>{selectedEntry.user_id || "system"}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {translate("aiflow.audit.details")}
                  </Typography>
                  <Box
                    component="pre"
                    sx={{
                      bgcolor: "action.hover",
                      p: 2,
                      borderRadius: 1,
                      overflow: "auto",
                      fontSize: 12,
                      maxHeight: 300,
                    }}
                  >
                    {JSON.stringify(selectedEntry.details, null, 2)}
                  </Box>
                </Box>
              </Stack>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedEntry(null)}>
                {translate("ra.action.cancel")}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};
