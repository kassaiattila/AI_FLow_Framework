import { useState, useEffect, useCallback } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import { useNavigate } from "react-router-dom";
import {
  Box, Card, CardContent, Typography, Button, Stack, Chip,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  MenuItem, CircularProgress, Alert, IconButton, TablePagination,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import ChatIcon from "@mui/icons-material/Chat";
import UploadIcon from "@mui/icons-material/Upload";
import BarChartIcon from "@mui/icons-material/BarChart";

interface Collection {
  id: string;
  name: string;
  description: string;
  language: string;
  embedding_model: string;
  doc_count: number;
  chunk_count: number;
  created_at: string;
}

interface CollectionForm {
  name: string;
  description: string;
  language: string;
  embedding_model: string;
}

const EMPTY_FORM: CollectionForm = {
  name: "",
  description: "",
  language: "hu",
  embedding_model: "text-embedding-3-small",
};

export const CollectionManager = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const notify = useNotify();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<CollectionForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const fetchCollections = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rag/collections");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSource(data.source || "backend");
      setCollections(data.collections || []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load collections");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCollections(); }, [fetchCollections]);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch("/api/v1/rag/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      notify("aiflow.rag.createSuccess", { type: "success" });
      setCreateOpen(false);
      setForm(EMPTY_FORM);
      fetchCollections();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Create failed", { type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async () => {
    if (!selectedId || !form.name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/v1/rag/collections/${selectedId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: form.name, description: form.description }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      notify("aiflow.rag.editSuccess", { type: "success" });
      setEditOpen(false);
      fetchCollections();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Edit failed", { type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedId) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/v1/rag/collections/${selectedId}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      notify("aiflow.rag.deleteSuccess", { type: "success" });
      setDeleteOpen(false);
      setSelectedId(null);
      fetchCollections();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Delete failed", { type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const openEdit = (col: Collection) => {
    setSelectedId(col.id);
    setForm({ name: col.name, description: col.description, language: col.language, embedding_model: col.embedding_model });
    setEditOpen(true);
  };

  const openDelete = (id: string) => {
    setSelectedId(id);
    setDeleteOpen(true);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Title title={translate("aiflow.rag.title")} />

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>{translate("aiflow.rag.title")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {translate("aiflow.rag.subtitle")}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          {source && (
            <Chip label={translate(`aiflow.status.${source}`)} color={source === "demo" ? "warning" : "success"} size="small" />
          )}
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setForm(EMPTY_FORM); setCreateOpen(true); }}>
            {translate("aiflow.rag.newCollection")}
          </Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>
      ) : collections.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: "center", py: 6 }}>
            <Typography color="text.secondary">{translate("aiflow.rag.noCollections")}</Typography>
            <Button variant="contained" sx={{ mt: 2 }} startIcon={<AddIcon />} onClick={() => { setForm(EMPTY_FORM); setCreateOpen(true); }}>
              {translate("aiflow.rag.newCollection")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>{translate("aiflow.rag.colName")}</TableCell>
                  <TableCell>{translate("aiflow.rag.colDescription")}</TableCell>
                  <TableCell align="right">{translate("aiflow.rag.colDocs")}</TableCell>
                  <TableCell align="right">{translate("aiflow.rag.colChunks")}</TableCell>
                  <TableCell>{translate("aiflow.rag.colCreated")}</TableCell>
                  <TableCell>{translate("aiflow.rag.colActions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {collections.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((col) => (
                  <TableRow key={col.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/rag/collections/${col.id}`)}>
                    <TableCell><Typography fontWeight={500}>{col.name}</Typography></TableCell>
                    <TableCell><Typography variant="body2" color="text.secondary">{col.description}</Typography></TableCell>
                    <TableCell align="right">{col.doc_count}</TableCell>
                    <TableCell align="right">{col.chunk_count}</TableCell>
                    <TableCell>{new Date(col.created_at).toLocaleDateString()}</TableCell>
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <Stack direction="row" spacing={0.5}>
                        <IconButton size="small" title="Edit" onClick={() => openEdit(col)}><EditIcon fontSize="small" /></IconButton>
                        <IconButton size="small" title="Ingest" onClick={() => navigate(`/rag/collections/${col.id}`)}><UploadIcon fontSize="small" /></IconButton>
                        <IconButton size="small" title="Chat" onClick={() => navigate(`/rag-chat?collection=${col.id}`)}><ChatIcon fontSize="small" /></IconButton>
                        <IconButton size="small" title="Stats" onClick={() => navigate(`/rag/collections/${col.id}`)}><BarChartIcon fontSize="small" /></IconButton>
                        <IconButton size="small" title="Delete" color="error" onClick={() => openDelete(col.id)}><DeleteIcon fontSize="small" /></IconButton>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={collections.length}
            page={page}
            onPageChange={(_, p) => setPage(p)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
          />
        </Card>
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{translate("aiflow.rag.createTitle")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label={translate("aiflow.rag.colName") + " *"} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} fullWidth autoFocus />
            <TextField label={translate("aiflow.rag.colDescription")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} fullWidth multiline rows={2} />
            <TextField label={translate("aiflow.rag.language")} value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })} select fullWidth>
              <MenuItem value="hu">Magyar (hu)</MenuItem>
              <MenuItem value="en">English (en)</MenuItem>
              <MenuItem value="auto">Auto-detect</MenuItem>
            </TextField>
            <TextField label={translate("aiflow.rag.embeddingModel")} value={form.embedding_model} onChange={(e) => setForm({ ...form, embedding_model: e.target.value })} select fullWidth>
              <MenuItem value="text-embedding-3-small">text-embedding-3-small</MenuItem>
              <MenuItem value="text-embedding-3-large">text-embedding-3-large</MenuItem>
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" onClick={handleCreate} disabled={saving || !form.name.trim()}>
            {saving ? <CircularProgress size={20} /> : translate("ra.action.create")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{translate("aiflow.rag.editTitle")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label={translate("aiflow.rag.colName") + " *"} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} fullWidth autoFocus />
            <TextField label={translate("aiflow.rag.colDescription")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} fullWidth multiline rows={2} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" onClick={handleEdit} disabled={saving || !form.name.trim()}>
            {saving ? <CircularProgress size={20} /> : translate("ra.action.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)}>
        <DialogTitle>{translate("aiflow.rag.deleteTitle")}</DialogTitle>
        <DialogContent>
          <Typography>{translate("aiflow.rag.deleteConfirm")}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteOpen(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" color="error" onClick={handleDelete} disabled={saving}>
            {saving ? <CircularProgress size={20} /> : translate("ra.action.delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
