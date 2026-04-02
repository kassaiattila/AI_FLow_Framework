import { useState, useEffect, useCallback } from "react";
import { useTranslate, Title, useNotify } from "react-admin";
import {
  Box, Typography, Button, Stack, Card, CardContent, Chip,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  CircularProgress, Alert, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";

interface ReviewItem {
  id: string;
  entity_type: string;
  entity_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  reviewer: string | null;
  comment: string | null;
  created_at: string;
  reviewed_at: string | null;
  source: string;
}

export const ReviewQueue = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const [pending, setPending] = useState<ReviewItem[]>([]);
  const [history, setHistory] = useState<ReviewItem[]>([]);
  const [loadingPending, setLoadingPending] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [decisionDialog, setDecisionDialog] = useState<{ id: string; action: "approve" | "reject" } | null>(null);
  const [decisionComment, setDecisionComment] = useState("");
  const [deciding, setDeciding] = useState(false);

  const fetchPending = useCallback(async () => {
    setLoadingPending(true);
    try {
      const res = await fetch("/api/v1/reviews/pending");
      if (res.ok) {
        const data = await res.json();
        setPending(data.reviews || []);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoadingPending(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch("/api/v1/reviews/history");
      if (res.ok) {
        const data = await res.json();
        setHistory(data.reviews || []);
      }
    } catch {
      // secondary, don't block
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => { fetchPending(); fetchHistory(); }, [fetchPending, fetchHistory]);

  const handleDecision = async () => {
    if (!decisionDialog) return;
    setDeciding(true);
    try {
      const res = await fetch(`/api/v1/reviews/${decisionDialog.id}/${decisionDialog.action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviewer: "admin", comment: decisionComment || null }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || "Decision failed");
      }
      notify(
        decisionDialog.action === "approve" ? "aiflow.reviews.approveSuccess" : "aiflow.reviews.rejectSuccess",
        { type: "success" },
      );
      setDecisionDialog(null);
      setDecisionComment("");
      fetchPending();
      fetchHistory();
    } catch (e) {
      notify(e instanceof Error ? e.message : "Failed", { type: "error" });
    } finally {
      setDeciding(false);
    }
  };

  const priorityColor = (p: string): "error" | "warning" | "default" | "info" => {
    if (p === "critical") return "error";
    if (p === "high") return "warning";
    if (p === "low") return "info";
    return "default";
  };

  const statusColor = (s: string): "success" | "error" | "default" => {
    if (s === "approved") return "success";
    if (s === "rejected") return "error";
    return "default";
  };

  return (
    <Box sx={{ p: 3 }}>
      <Title title={translate("aiflow.reviews.title")} />

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>{translate("aiflow.reviews.title")}</Typography>
          <Typography variant="body2" color="text.secondary">{translate("aiflow.reviews.subtitle")}</Typography>
        </Box>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Pending Reviews */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ pb: 0 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{translate("aiflow.reviews.pendingTitle")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {pending.length} {translate("aiflow.reviews.pendingCount")}
            </Typography>
          </Stack>
        </CardContent>
        {loadingPending ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}><CircularProgress /></Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{translate("aiflow.reviews.itemTitle")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.type")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.priority")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.created")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pending.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500} sx={{ maxWidth: 350, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {item.title}
                      </Typography>
                      {item.description && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ maxWidth: 350, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {item.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip label={item.entity_type} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip label={translate(`aiflow.reviews.${item.priority}`)} size="small" color={priorityColor(item.priority)} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(item.created_at).toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          startIcon={<CheckCircleIcon />}
                          onClick={() => { setDecisionDialog({ id: item.id, action: "approve" }); setDecisionComment(""); }}
                        >
                          {translate("aiflow.reviews.approve")}
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          color="error"
                          startIcon={<CancelIcon />}
                          onClick={() => { setDecisionDialog({ id: item.id, action: "reject" }); setDecisionComment(""); }}
                        >
                          {translate("aiflow.reviews.reject")}
                        </Button>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {pending.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" py={3}>{translate("aiflow.reviews.noPending")}</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {/* Review History */}
      <Card>
        <CardContent sx={{ pb: 0 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">{translate("aiflow.reviews.historyTitle")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {history.length} {translate("aiflow.reviews.historyCount")}
            </Typography>
          </Stack>
        </CardContent>
        {loadingHistory ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}><CircularProgress /></Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{translate("aiflow.reviews.itemTitle")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.decision")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.reviewer")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.comment")}</TableCell>
                  <TableCell>{translate("aiflow.reviews.reviewed")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500} sx={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {item.title}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={translate(`aiflow.reviews.${item.status}`)} size="small" color={statusColor(item.status)} />
                    </TableCell>
                    <TableCell>{item.reviewer || "—"}</TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {item.comment || "—"}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {item.reviewed_at ? new Date(item.reviewed_at).toLocaleString() : "—"}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
                {history.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" py={3}>{translate("aiflow.reviews.noHistory")}</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {/* Decision Dialog */}
      <Dialog open={!!decisionDialog} onClose={() => setDecisionDialog(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {decisionDialog?.action === "approve"
            ? translate("aiflow.reviews.approveTitle")
            : translate("aiflow.reviews.rejectTitle")}
        </DialogTitle>
        <DialogContent>
          <TextField
            label={translate("aiflow.reviews.commentLabel")}
            value={decisionComment}
            onChange={(e) => setDecisionComment(e.target.value)}
            fullWidth
            multiline
            minRows={2}
            maxRows={5}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDecisionDialog(null)}>{translate("ra.action.cancel")}</Button>
          <Button
            variant="contained"
            color={decisionDialog?.action === "approve" ? "success" : "error"}
            onClick={handleDecision}
            disabled={deciding}
          >
            {deciding ? <CircularProgress size={20} /> : (
              decisionDialog?.action === "approve"
                ? translate("aiflow.reviews.confirmApprove")
                : translate("aiflow.reviews.confirmReject")
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
