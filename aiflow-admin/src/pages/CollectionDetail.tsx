import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box, Typography, Button, Stack, Card, CardContent, Chip,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  CircularProgress, Alert, IconButton, TablePagination, TextField,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DeleteIcon from "@mui/icons-material/Delete";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";

interface Collection {
  id: string;
  name: string;
  description: string;
  language: string;
  embedding_model: string;
  doc_count: number;
  chunk_count: number;
}

interface CollectionStats {
  doc_count: number;
  chunk_count: number;
  query_count: number;
  avg_response_time_ms: number;
  feedback_positive: number;
  feedback_negative: number;
}

interface Chunk {
  chunk_id: string;
  content: string;
  source_document: string;
  created_at: string;
}

interface IngestFile {
  name: string;
  status: "pending" | "running" | "done" | "error";
  chunks?: number;
  duration_ms?: number;
  error?: string;
}

export const CollectionDetail = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const notify = useNotify();
  const { id } = useParams<{ id: string }>();

  const [collection, setCollection] = useState<Collection | null>(null);
  const [stats, setStats] = useState<CollectionStats | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [chunkTotal, setChunkTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ingestFiles, setIngestFiles] = useState<IngestFile[]>([]);
  const [ingesting, setIngesting] = useState(false);
  const [chunkPage, setChunkPage] = useState(0);
  const [chunkSearch, setChunkSearch] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchCollection = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [colRes, statsRes, chunksRes] = await Promise.all([
        fetch(`/api/v1/rag/collections/${id}`),
        fetch(`/api/v1/rag/collections/${id}/stats`),
        fetch(`/api/v1/rag/collections/${id}/chunks?limit=50&offset=${chunkPage * 50}`),
      ]);
      if (!colRes.ok) throw new Error(`Collection not found`);
      const colData = await colRes.json();
      setCollection(colData);
      if (statsRes.ok) setStats(await statsRes.json());
      if (chunksRes.ok) {
        const chunkData = await chunksRes.json();
        setChunks(chunkData.chunks || []);
        setChunkTotal(chunkData.total || 0);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [id, chunkPage]);

  useEffect(() => { fetchCollection(); }, [fetchCollection]);

  const handleIngest = async (files: FileList) => {
    if (!id || files.length === 0) return;
    setIngesting(true);
    setIngestFiles(Array.from(files).map((f) => ({ name: f.name, status: "pending" })));

    const formData = new FormData();
    Array.from(files).forEach((f) => formData.append("files", f));

    try {
      const res = await fetch(`/api/v1/rag/collections/${id}/ingest`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Ingest failed: HTTP ${res.status}`);
      const data = await res.json();
      setIngestFiles(Array.from(files).map((f) => ({
        name: f.name,
        status: "done",
        chunks: data.chunks_created || 0,
        duration_ms: data.duration_ms || 0,
      })));
      notify(translate("aiflow.rag.ingestSuccess"), { type: "success" });
      fetchCollection();
    } catch (e) {
      setIngestFiles((prev) => prev.map((f) => ({ ...f, status: "error", error: (e as Error).message })));
      notify(e instanceof Error ? e.message : "Ingest failed", { type: "error" });
    } finally {
      setIngesting(false);
    }
  };

  const handleDeleteChunk = async (chunkId: string) => {
    if (!id) return;
    try {
      const res = await fetch(`/api/v1/rag/collections/${id}/chunks/${chunkId}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Delete failed`);
      notify("Chunk deleted", { type: "success" });
      fetchCollection();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Delete failed", { type: "error" });
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) handleIngest(e.dataTransfer.files);
  };

  if (loading) return <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" sx={{ m: 3 }}>{error}</Alert>;
  if (!collection) return null;

  const statCards = [
    { label: translate("aiflow.rag.statDocs"), value: stats?.doc_count ?? collection.doc_count },
    { label: translate("aiflow.rag.statChunks"), value: stats?.chunk_count ?? collection.chunk_count },
    { label: translate("aiflow.rag.statQueries"), value: stats?.query_count ?? 0 },
    { label: translate("aiflow.rag.statAvgTime"), value: stats?.avg_response_time_ms ? `${(stats.avg_response_time_ms / 1000).toFixed(1)}s` : "—" },
  ];

  return (
    <Box sx={{ p: 3 }}>
      <Title title={collection.name} />

      {/* Header */}
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/rag/collections")} sx={{ mb: 1 }}>
        {translate("aiflow.rag.backToCollections")}
      </Button>
      <Typography variant="h5" fontWeight={600}>{collection.name}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {collection.description} · {translate("aiflow.rag.language")}: {collection.language} · Embedding: {collection.embedding_model}
      </Typography>

      {/* Stats Cards */}
      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        {statCards.map((s) => (
          <Card key={s.label} sx={{ flex: 1 }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">{s.label}</Typography>
              <Typography variant="h5" fontWeight={600}>{s.value}</Typography>
            </CardContent>
          </Card>
        ))}
      </Stack>

      {/* Ingest Section */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>{translate("aiflow.rag.ingestTitle")}</Typography>
          <Box
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
            sx={{
              border: "2px dashed",
              borderColor: "divider",
              borderRadius: 2,
              p: 4,
              textAlign: "center",
              cursor: "pointer",
              "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 40, color: "primary.main", mb: 1 }} />
            <Typography color="primary" fontWeight={500}>
              {translate("aiflow.rag.ingestDropzone")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              PDF, DOCX, TXT, MD, XLSX
            </Typography>
            <input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt,.md,.xlsx" hidden onChange={(e) => e.target.files && handleIngest(e.target.files)} />
          </Box>

          {ingestFiles.length > 0 && (
            <Stack spacing={1} sx={{ mt: 2 }}>
              {ingestFiles.map((f) => (
                <Stack key={f.name} direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2" sx={{ minWidth: 200 }}>{f.name}</Typography>
                  <Chip
                    label={f.status}
                    size="small"
                    color={f.status === "done" ? "success" : f.status === "error" ? "error" : f.status === "running" ? "warning" : "default"}
                  />
                  {f.chunks != null && <Typography variant="body2" color="text.secondary">{f.chunks} chunks</Typography>}
                  {f.duration_ms != null && <Typography variant="body2" color="text.secondary">{(f.duration_ms / 1000).toFixed(1)}s</Typography>}
                  {f.error && <Typography variant="body2" color="error">{f.error}</Typography>}
                </Stack>
              ))}
            </Stack>
          )}
          {ingesting && <CircularProgress size={24} sx={{ mt: 1 }} />}
        </CardContent>
      </Card>

      {/* Chunk Browser */}
      <Card>
        <CardContent sx={{ pb: 0 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{translate("aiflow.rag.chunkBrowser")}</Typography>
            <TextField
              size="small"
              placeholder={translate("aiflow.rag.chunkSearch")}
              value={chunkSearch}
              onChange={(e) => setChunkSearch(e.target.value)}
              sx={{ width: 250 }}
            />
          </Stack>
        </CardContent>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{translate("aiflow.rag.chunkId")}</TableCell>
                <TableCell>{translate("aiflow.rag.chunkContent")}</TableCell>
                <TableCell>{translate("aiflow.rag.chunkSource")}</TableCell>
                <TableCell>{translate("aiflow.rag.chunkCreated")}</TableCell>
                <TableCell>{translate("aiflow.rag.colActions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {chunks
                .filter((c) => !chunkSearch || c.content.toLowerCase().includes(chunkSearch.toLowerCase()))
                .map((chunk) => (
                <TableRow key={chunk.chunk_id}>
                  <TableCell><Typography variant="body2" fontFamily="monospace">{chunk.chunk_id.slice(0, 8)}</Typography></TableCell>
                  <TableCell><Typography variant="body2" sx={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{chunk.content}</Typography></TableCell>
                  <TableCell><Typography variant="body2" color="text.secondary">{chunk.source_document}</Typography></TableCell>
                  <TableCell>{new Date(chunk.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <IconButton size="small" color="error" onClick={() => handleDeleteChunk(chunk.chunk_id)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {chunks.length === 0 && (
                <TableRow><TableCell colSpan={5} align="center"><Typography color="text.secondary" py={3}>{translate("aiflow.rag.noChunks")}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={chunkTotal}
          page={chunkPage}
          onPageChange={(_, p) => setChunkPage(p)}
          rowsPerPage={50}
          onRowsPerPageChange={() => {}}
          rowsPerPageOptions={[50]}
        />
      </Card>
    </Box>
  );
};
