/**
 * AIFlow Admin — F6.5 users + API keys tabbed page.
 * S39: C2.5 — Create User, Generate Key, Revoke Key CRUD dialogs.
 */
import { useState } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";
import { ConfirmDialog } from "../components-new/ConfirmDialog";

interface UserItem { id: string; email: string; name: string | null; role: string; is_active: boolean; created_at: string; }
interface UsersResponse { users: UserItem[]; total: number; source?: string; }
interface ApiKeyItem { id: string; name: string; prefix: string; is_active: boolean; created_at: string; }
interface KeysResponse { keys: ApiKeyItem[]; total: number; source?: string; }

export function Admin() {
  const translate = useTranslate();
  const [tab, setTab] = useState<"users" | "keys">("users");
  const { data: usersData, loading: ul, error: ue, refetch: ur } = useApi<UsersResponse>("/api/v1/admin/users");
  const { data: keysData, loading: kl, error: ke, refetch: kr } = useApi<KeysResponse>("/api/v1/admin/api-keys");

  // Create User dialog state
  const [createUserOpen, setCreateUserOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("viewer");
  const [createError, setCreateError] = useState<string | null>(null);

  // Generate Key dialog state
  const [generateKeyOpen, setGenerateKeyOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);
  const [keyCopied, setKeyCopied] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);

  // Revoke Key state
  const [revokeTarget, setRevokeTarget] = useState<string | null>(null);
  const [revoking, setRevoking] = useState(false);

  const resetCreateForm = () => {
    setNewEmail(""); setNewName(""); setNewPassword(""); setNewRole("viewer"); setCreateError(null);
  };

  const handleCreateUser = async () => {
    setCreating(true);
    setCreateError(null);
    try {
      await fetchApi("POST", "/api/v1/admin/users", {
        email: newEmail, name: newName, password: newPassword, role: newRole,
      });
      setCreateUserOpen(false);
      resetCreateForm();
      ur();
    } catch {
      setCreateError(translate("aiflow.admin.createFailed"));
    } finally {
      setCreating(false);
    }
  };

  const handleGenerateKey = async () => {
    setGenerating(true);
    setKeyError(null);
    try {
      const res = await fetchApi<{ id: string; name: string; key: string; prefix: string }>(
        "POST", "/api/v1/admin/api-keys", { name: keyName }
      );
      setRevealedKey(res.key);
    } catch {
      setKeyError(translate("aiflow.admin.createFailed"));
    } finally {
      setGenerating(false);
    }
  };

  const handleCopyKey = async () => {
    if (revealedKey) {
      await navigator.clipboard.writeText(revealedKey);
      setKeyCopied(true);
      setTimeout(() => setKeyCopied(false), 2000);
    }
  };

  const closeKeyDialog = () => {
    setGenerateKeyOpen(false);
    setRevealedKey(null);
    setKeyName("");
    setKeyCopied(false);
    setKeyError(null);
    kr();
  };

  const handleRevokeKey = async () => {
    if (!revokeTarget) return;
    setRevoking(true);
    try {
      await fetchApi("DELETE", `/api/v1/admin/api-keys/${revokeTarget}`);
      setRevokeTarget(null);
      kr();
    } catch {
      // error silently — key might already be revoked
      setRevokeTarget(null);
    } finally {
      setRevoking(false);
    }
  };

  const userCols: Column<Record<string, unknown>>[] = [
    { key: "email", label: translate("aiflow.admin.email"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.email)}</span> },
    { key: "name", label: translate("aiflow.admin.userName"), render: (item) => <span className="text-gray-600 dark:text-gray-400">{String(item.name ?? "—")}</span> },
    { key: "role", label: translate("aiflow.admin.role"), render: (item) => <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">{String(item.role)}</span> },
    { key: "is_active", label: translate("aiflow.admin.status"), render: (item) => {
      const active = item.is_active as boolean;
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>{active ? translate("aiflow.admin.active") : translate("aiflow.admin.inactive")}</span>;
    }},
    { key: "created_at", label: translate("aiflow.admin.created"), render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.created_at)).toLocaleDateString()}</span> },
  ];

  const keyCols: Column<Record<string, unknown>>[] = [
    { key: "name", label: translate("aiflow.admin.keyName"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.name)}</span> },
    { key: "prefix", label: translate("aiflow.admin.prefix"), render: (item) => <span className="font-mono text-xs text-gray-500">{String(item.prefix)}...</span> },
    { key: "is_active", label: translate("aiflow.admin.status"), render: (item) => {
      const active = item.is_active as boolean;
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"}`}>{active ? translate("aiflow.admin.active") : translate("aiflow.admin.inactive")}</span>;
    }},
    { key: "created_at", label: translate("aiflow.admin.created"), render: (item) => <span className="text-xs text-gray-500">{new Date(String(item.created_at)).toLocaleDateString()}</span> },
    { key: "actions", label: "", sortable: false, render: (item) => {
      if (!(item.is_active as boolean)) return null;
      return (
        <button
          onClick={(e) => { e.stopPropagation(); setRevokeTarget(item.id as string); }}
          className="text-xs text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
        >
          Revoke
        </button>
      );
    }},
  ];

  const handleActionClick = () => {
    if (tab === "users") setCreateUserOpen(true);
    else setGenerateKeyOpen(true);
  };

  return (
    <PageLayout titleKey="aiflow.admin.title" subtitleKey="aiflow.admin.subtitle"
      actions={
        <button
          data-testid={tab === "users" ? "admin-create-user" : "admin-generate-key"}
          onClick={handleActionClick}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
        >
          {tab === "users" ? translate("aiflow.admin.addUser") : translate("aiflow.admin.generateKey")}
        </button>
      }
    >
      <div className="mb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-6">
          {(["users", "keys"] as const).map((t) => (
            <button
              key={t}
              data-testid={`admin-tab-${t}`}
              onClick={() => setTab(t)}
              className={`border-b-2 pb-2 text-sm font-medium ${tab === t ? "border-brand-500 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >{t === "users" ? translate("aiflow.admin.users") : translate("aiflow.admin.apiKeys")}</button>
          ))}
        </div>
      </div>

      {tab === "users" ? (
        ue ? <ErrorState error={ue} onRetry={ur} /> :
        <DataTable data={(usersData?.users ?? []) as unknown as Record<string, unknown>[]} columns={userCols} loading={ul} searchKeys={["email", "name", "role"]} />
      ) : (
        ke ? <ErrorState error={ke} onRetry={kr} /> :
        <DataTable data={(keysData?.keys ?? []) as unknown as Record<string, unknown>[]} columns={keyCols} loading={kl} searchKeys={["name", "prefix"]} />
      )}

      {/* Create User Dialog */}
      {createUserOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.admin.createUserTitle")}
            </h3>
            {createError && (
              <div className="mb-3 rounded-lg bg-red-50 p-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">{createError}</div>
            )}
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{translate("aiflow.admin.email")}</label>
                <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{translate("aiflow.admin.userName")}</label>
                <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Password</label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{translate("aiflow.admin.role")}</label>
                <select value={newRole} onChange={(e) => setNewRole(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100">
                  <option value="viewer">Viewer</option>
                  <option value="operator">Operator</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => { setCreateUserOpen(false); resetCreateForm(); }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800">
                Cancel
              </button>
              <button onClick={handleCreateUser} disabled={creating || !newEmail || !newPassword}
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
                {creating ? "..." : translate("aiflow.admin.addUser")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Generate Key Dialog */}
      {generateKeyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.admin.generateKeyTitle")}
            </h3>
            {keyError && (
              <div className="mb-3 rounded-lg bg-red-50 p-2 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">{keyError}</div>
            )}
            {revealedKey ? (
              <div className="space-y-3">
                <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-3 dark:border-yellow-700 dark:bg-yellow-900/20">
                  <p className="mb-2 text-sm font-medium text-yellow-800 dark:text-yellow-300">
                    {translate("aiflow.admin.keyRevealWarning")}
                  </p>
                  <code className="block break-all rounded bg-gray-100 p-2 text-xs text-gray-900 dark:bg-gray-800 dark:text-gray-100">
                    {revealedKey}
                  </code>
                </div>
                <div className="flex justify-end gap-2">
                  <button onClick={handleCopyKey}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800">
                    {keyCopied ? translate("aiflow.admin.copied") : translate("aiflow.admin.copyKey")}
                  </button>
                  <button onClick={closeKeyDialog}
                    className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">
                    OK
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{translate("aiflow.admin.keyName")}</label>
                  <input type="text" value={keyName} onChange={(e) => setKeyName(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100" />
                </div>
                <div className="mt-5 flex justify-end gap-2">
                  <button onClick={() => { setGenerateKeyOpen(false); setKeyName(""); setKeyError(null); }}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800">
                    Cancel
                  </button>
                  <button onClick={handleGenerateKey} disabled={generating || !keyName.trim()}
                    className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50">
                    {generating ? "..." : translate("aiflow.admin.generateKey")}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Revoke Key ConfirmDialog */}
      <ConfirmDialog
        open={!!revokeTarget}
        title={translate("aiflow.admin.revokeKeyConfirm")}
        message={`Key ID: ${revokeTarget?.substring(0, 8) ?? ""}...`}
        variant="danger"
        confirmLabel="Revoke"
        loading={revoking}
        onConfirm={handleRevokeKey}
        onCancel={() => setRevokeTarget(null)}
      />
    </PageLayout>
  );
}
