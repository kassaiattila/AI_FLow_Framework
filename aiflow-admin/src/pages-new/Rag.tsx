/**
 * AIFlow RAG — F6.4 tabbed page (Collections + Chat).
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { DataTable, type Column } from "../components-new/DataTable";

interface Collection {
  id: string;
  name: string;
  description: string | null;
  language: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

interface CollectionsResponse {
  collections: Collection[];
  total: number;
  source: string;
}

export function Rag() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"collections" | "chat">("collections");
  const { data, loading, error, refetch } = useApi<CollectionsResponse>("/api/v1/rag/collections");

  const columns: Column<Record<string, unknown>>[] = [
    { key: "name", label: translate("aiflow.rag.colName"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.name)}</span> },
    { key: "description", label: translate("aiflow.rag.colDescription"), render: (item) => <span className="text-gray-500 dark:text-gray-400 text-xs">{String(item.description ?? "—")}</span> },
    { key: "document_count", label: translate("aiflow.rag.colDocs"), getValue: (item) => item.document_count as number },
    { key: "chunk_count", label: translate("aiflow.rag.colChunks"), getValue: (item) => item.chunk_count as number },
    { key: "created_at", label: translate("aiflow.rag.colCreated"), render: (item) => <span className="text-xs text-gray-500">{item.created_at ? new Date(String(item.created_at)).toLocaleDateString() : "—"}</span> },
    { key: "actions", label: translate("aiflow.rag.colActions"), sortable: false, render: (item) => (
      <button onClick={() => navigate(`/rag/${item.id}`)} className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-400">
        Open
      </button>
    )},
  ];

  return (
    <PageLayout titleKey="aiflow.rag.title" subtitleKey="aiflow.rag.subtitle" source={data?.source}
      actions={<button className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">{translate("aiflow.rag.newCollection")}</button>}
    >
      <div className="mb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-6">
          {["collections", "chat"].map((t) => (
            <button key={t} onClick={() => setTab(t as "collections" | "chat")}
              className={`border-b-2 pb-2 text-sm font-medium ${tab === t ? "border-brand-500 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
            >{t === "collections" ? translate("aiflow.ragChat.collection") : "Chat"}</button>
          ))}
        </div>
      </div>

      {tab === "collections" ? (
        error ? <ErrorState error={error} onRetry={refetch} /> :
        <DataTable data={(data?.collections ?? []) as unknown as Record<string, unknown>[]} columns={columns} loading={loading} searchKeys={["name", "description"]} />
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
          <p className="text-sm text-gray-500">{translate("aiflow.ragChat.empty")}</p>
        </div>
      )}
    </PageLayout>
  );
}
