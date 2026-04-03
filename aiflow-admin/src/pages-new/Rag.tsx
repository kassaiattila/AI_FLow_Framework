/**
 * AIFlow RAG — F6.4 tabbed page (Collections + Chat).
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { ErrorState } from "../components-new/ErrorState";
import { ChatPanel } from "../components-new/ChatPanel";
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

  /* --- New Collection dialog state --- */
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newLang, setNewLang] = useState("hu");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim() || creating) return;
    setCreating(true);
    try {
      const res = await fetchApi<{ id: string }>("POST", "/api/v1/rag/collections", {
        name: newName.trim(),
        description: newDesc.trim() || null,
        language: newLang,
      });
      setShowCreate(false);
      setNewName("");
      setNewDesc("");
      setNewLang("hu");
      refetch();
      navigate(`/rag/${res.id}`);
    } catch {
      // stay in dialog so user can retry
    } finally {
      setCreating(false);
    }
  };

  const columns: Column<Record<string, unknown>>[] = [
    { key: "name", label: translate("aiflow.rag.colName"), render: (item) => <span className="font-medium text-gray-900 dark:text-gray-100">{String(item.name)}</span> },
    { key: "description", label: translate("aiflow.rag.colDescription"), render: (item) => <span className="text-gray-500 dark:text-gray-400 text-xs">{String(item.description ?? "\u2014")}</span> },
    { key: "document_count", label: translate("aiflow.rag.colDocs"), getValue: (item) => item.document_count as number },
    { key: "chunk_count", label: translate("aiflow.rag.colChunks"), getValue: (item) => item.chunk_count as number },
    { key: "created_at", label: translate("aiflow.rag.colCreated"), render: (item) => <span className="text-xs text-gray-500">{item.created_at ? new Date(String(item.created_at)).toLocaleDateString() : "\u2014"}</span> },
    { key: "actions", label: translate("aiflow.rag.colActions"), sortable: false, render: (item) => (
      <button onClick={() => navigate(`/rag/${item.id}`)} className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-100 dark:bg-brand-900/30 dark:text-brand-400">
        Open
      </button>
    )},
  ];

  return (
    <PageLayout titleKey="aiflow.rag.title" subtitleKey="aiflow.rag.subtitle" source={data?.source}
      actions={
        <button onClick={() => setShowCreate(true)} className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600">
          {translate("aiflow.rag.newCollection")}
        </button>
      }
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
        <ChatPanel collections={data?.collections ?? []} />
      )}

      {/* --- New Collection Dialog --- */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-xl dark:border-gray-700 dark:bg-gray-900">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
              {translate("aiflow.rag.createTitle")}
            </h2>

            {/* Name */}
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {translate("aiflow.rag.colName")} *
            </label>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="mb-3 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              placeholder={translate("aiflow.rag.colName")}
              autoFocus
            />

            {/* Description */}
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {translate("aiflow.rag.colDescription")}
            </label>
            <input
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="mb-3 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              placeholder={translate("aiflow.rag.colDescription")}
            />

            {/* Language */}
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {translate("aiflow.rag.language")}
            </label>
            <select
              value={newLang}
              onChange={(e) => setNewLang(e.target.value)}
              className="mb-4 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            >
              <option value="hu">Magyar (hu)</option>
              <option value="en">English (en)</option>
            </select>

            {/* Buttons */}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setShowCreate(false); setNewName(""); setNewDesc(""); setNewLang("hu"); }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                {translate("common.action.cancel")}
              </button>
              <button
                onClick={() => void handleCreate()}
                disabled={!newName.trim() || creating}
                className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {creating ? translate("aiflow.common.loading") : translate("common.action.create")}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
