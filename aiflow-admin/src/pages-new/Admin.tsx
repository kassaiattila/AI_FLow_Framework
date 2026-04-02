/**
 * AIFlow Admin — F6.5 users + API keys tabbed page.
 */
import { useState } from "react";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface UserItem { id: string; email: string; name: string | null; role: string; is_active: boolean; created_at: string; }
interface UsersResponse { users: UserItem[]; total: number; source?: string; }
interface ApiKeyItem { id: string; name: string; prefix: string; is_active: boolean; created_at: string; }
interface KeysResponse { keys: ApiKeyItem[]; total: number; source?: string; }

export function Admin() {
  const translate = useTranslate();
  const [tab, setTab] = useState<"users" | "keys">("users");
  const { data: usersData, loading: ul, error: ue, refetch: ur } = useApi<UsersResponse>("/api/v1/admin/users");
  const { data: keysData, loading: kl, error: ke, refetch: kr } = useApi<KeysResponse>("/api/v1/admin/api-keys");

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
  ];

  return (
    <PageLayout titleKey="aiflow.admin.title" subtitleKey="aiflow.admin.subtitle"
      actions={<button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">{tab === "users" ? translate("aiflow.admin.addUser") : translate("aiflow.admin.generateKey")}</button>}
    >
      <div className="mb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-6">
          {(["users", "keys"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
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
    </PageLayout>
  );
}
