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
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip,
} from "@mui/material";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import VpnKeyIcon from "@mui/icons-material/VpnKey";
import DeleteIcon from "@mui/icons-material/Delete";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import RefreshIcon from "@mui/icons-material/Refresh";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  team_id: string | null;
  last_login_at: string | null;
  created_at: string;
}

interface APIKey {
  id: string;
  name: string;
  prefix: string;
  user_id: string | null;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

export const AdminPage = () => {
  const translate = useTranslate();
  const notify = useNotify();
  const [users, setUsers] = useState<User[]>([]);
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState("");
  const [userDialog, setUserDialog] = useState(false);
  const [keyDialog, setKeyDialog] = useState(false);
  const [newKeyResult, setNewKeyResult] = useState<string | null>(null);
  const [newUser, setNewUser] = useState({ email: "", name: "", role: "viewer" });
  const [newKeyName, setNewKeyName] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [usersRes, keysRes] = await Promise.all([
        fetch("/api/v1/admin/users"),
        fetch("/api/v1/admin/api-keys"),
      ]);
      if (usersRes.ok) {
        const ud = await usersRes.json();
        setUsers(ud.users);
        setSource(ud.source);
      }
      if (keysRes.ok) {
        const kd = await keysRes.json();
        setKeys(kd.keys);
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateUser = async () => {
    try {
      const res = await fetch("/api/v1/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newUser),
      });
      if (!res.ok) throw new Error();
      notify(translate("aiflow.admin.userCreated"), { type: "success" });
      setUserDialog(false);
      setNewUser({ email: "", name: "", role: "viewer" });
      fetchData();
    } catch {
      notify(translate("aiflow.admin.createFailed"), { type: "error" });
    }
  };

  const handleGenerateKey = async () => {
    try {
      const res = await fetch("/api/v1/admin/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setNewKeyResult(data.key);
      notify(translate("aiflow.admin.keyGenerated"), { type: "success" });
      setKeyDialog(false);
      setNewKeyName("");
      fetchData();
    } catch {
      notify(translate("aiflow.admin.createFailed"), { type: "error" });
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    try {
      const res = await fetch(`/api/v1/admin/api-keys/${keyId}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      notify(translate("aiflow.admin.keyDeleted"), { type: "success" });
      fetchData();
    } catch {
      notify(translate("aiflow.admin.deleteFailed"), { type: "error" });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    notify(translate("aiflow.admin.copied"), { type: "info" });
  };

  const formatDate = (d: string) => d ? new Date(d).toLocaleDateString() : "—";

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Title title={translate("aiflow.admin.title")} />

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {translate("aiflow.admin.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {translate("aiflow.admin.subtitle")}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          {source && (
            <Chip
              label={source === "backend" ? "Live" : "Demo"}
              color={source === "backend" ? "success" : "warning"}
              size="small"
            />
          )}
          <Button startIcon={<RefreshIcon />} onClick={fetchData} size="small" disabled={loading}>
            {translate("ra.action.refresh")}
          </Button>
        </Stack>
      </Stack>

      {loading && !users.length ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Users Section */}
          <Card variant="outlined" sx={{ mb: 3 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2, bgcolor: "action.hover" }}>
              <Typography fontWeight={600}>
                {translate("aiflow.admin.users")} ({users.length})
              </Typography>
              <Button
                variant="contained"
                startIcon={<PersonAddIcon />}
                size="small"
                onClick={() => setUserDialog(true)}
              >
                {translate("aiflow.admin.addUser")}
              </Button>
            </Stack>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.email")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.userName")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.role")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.status")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.created")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                        <Typography color="text.secondary">
                          {translate("aiflow.admin.noUsers")}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    users.map((u) => (
                      <TableRow key={u.id} hover>
                        <TableCell>{u.email}</TableCell>
                        <TableCell>{u.name}</TableCell>
                        <TableCell>
                          <Chip label={u.role} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={u.is_active ? translate("aiflow.admin.active") : translate("aiflow.admin.inactive")}
                            color={u.is_active ? "success" : "default"}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>{formatDate(u.created_at)}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>

          {/* API Keys Section */}
          <Card variant="outlined">
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2, bgcolor: "action.hover" }}>
              <Typography fontWeight={600}>
                {translate("aiflow.admin.apiKeys")} ({keys.length})
              </Typography>
              <Button
                variant="contained"
                startIcon={<VpnKeyIcon />}
                size="small"
                onClick={() => setKeyDialog(true)}
              >
                {translate("aiflow.admin.generateKey")}
              </Button>
            </Stack>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.keyName")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.prefix")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.created")}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>{translate("aiflow.admin.actions")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {keys.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                        <Typography color="text.secondary">
                          {translate("aiflow.admin.noKeys")}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    keys.map((k) => (
                      <TableRow key={k.id} hover>
                        <TableCell>{k.name}</TableCell>
                        <TableCell>
                          <Typography sx={{ fontFamily: "monospace" }}>{k.prefix}...</Typography>
                        </TableCell>
                        <TableCell>{formatDate(k.created_at)}</TableCell>
                        <TableCell>
                          <Tooltip title={translate("ra.action.delete")}>
                            <IconButton size="small" color="error" onClick={() => handleDeleteKey(k.id)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </>
      )}

      {/* Create User Dialog */}
      <Dialog open={userDialog} onClose={() => setUserDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{translate("aiflow.admin.addUser")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label={translate("aiflow.admin.email")}
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label={translate("aiflow.admin.userName")}
              value={newUser.name}
              onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
              fullWidth
              required
            />
            <FormControl fullWidth>
              <InputLabel>{translate("aiflow.admin.role")}</InputLabel>
              <Select
                value={newUser.role}
                label={translate("aiflow.admin.role")}
                onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              >
                <MenuItem value="admin">Admin</MenuItem>
                <MenuItem value="developer">Developer</MenuItem>
                <MenuItem value="operator">Operator</MenuItem>
                <MenuItem value="viewer">Viewer</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUserDialog(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" onClick={handleCreateUser} disabled={!newUser.email || !newUser.name}>
            {translate("ra.action.create")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Generate Key Dialog */}
      <Dialog open={keyDialog} onClose={() => setKeyDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{translate("aiflow.admin.generateKey")}</DialogTitle>
        <DialogContent>
          <TextField
            label={translate("aiflow.admin.keyName")}
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            fullWidth
            required
            sx={{ mt: 1 }}
            placeholder="e.g. Production API"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setKeyDialog(false)}>{translate("ra.action.cancel")}</Button>
          <Button variant="contained" onClick={handleGenerateKey} disabled={!newKeyName}>
            {translate("aiflow.admin.generateKey")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Key Created Result Dialog */}
      <Dialog open={!!newKeyResult} onClose={() => setNewKeyResult(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{translate("aiflow.admin.keyGenerated")}</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {translate("aiflow.admin.keyWarning")}
          </Alert>
          <Box
            sx={{
              bgcolor: "action.hover",
              p: 2,
              borderRadius: 1,
              fontFamily: "monospace",
              fontSize: 13,
              wordBreak: "break-all",
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <Typography sx={{ fontFamily: "monospace", flex: 1 }}>{newKeyResult}</Typography>
            <IconButton size="small" onClick={() => newKeyResult && copyToClipboard(newKeyResult)}>
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button variant="contained" onClick={() => setNewKeyResult(null)}>
            {translate("ra.action.confirm")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
