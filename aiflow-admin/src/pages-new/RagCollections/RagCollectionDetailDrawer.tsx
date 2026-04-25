import { useEffect, useState } from "react";
import { useTranslate } from "../../lib/i18n";
import { ApiClientError, fetchApi } from "../../lib/api-client";
import { EmbedderProfileBadge } from "./EmbedderProfileBadge";
import {
  EMBEDDER_PROFILE_OPTIONS,
  type RagCollectionDetail,
  type RagCollectionListItem,
} from "./types";

interface Props {
  collection: RagCollectionListItem;
  onClose: () => void;
  onSaved: (updated: RagCollectionDetail) => void;
}

const SELECT_PROFILE_VALUES = EMBEDDER_PROFILE_OPTIONS.map((o) =>
  o.value === null ? "__null__" : o.value,
);

function valueToProfileId(v: string): string | null {
  return v === "__null__" ? null : v;
}

function profileIdToValue(p: string | null): string {
  return p === null ? "__null__" : p;
}

export function RagCollectionDetailDrawer({
  collection,
  onClose,
  onSaved,
}: Props) {
  const t = useTranslate();
  const [detail, setDetail] = useState<RagCollectionDetail | null>(null);
  const [profileDraft, setProfileDraft] = useState<string>(
    profileIdToValue(collection.embedder_profile_id),
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    let aborted = false;
    setLoading(true);
    setError(null);
    fetchApi<RagCollectionDetail>(
      "GET",
      `/api/v1/rag-collections/${collection.id}`,
    )
      .then((d) => {
        if (aborted) return;
        setDetail(d);
        setProfileDraft(profileIdToValue(d.embedder_profile_id));
      })
      .catch((e) => {
        if (aborted) return;
        setError(e instanceof Error ? e.message : "Load failed");
      })
      .finally(() => {
        if (!aborted) setLoading(false);
      });
    return () => {
      aborted = true;
    };
  }, [collection.id]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setToast(null);
    try {
      const updated = await fetchApi<RagCollectionDetail>(
        "PATCH",
        `/api/v1/rag-collections/${collection.id}/embedder-profile`,
        { embedder_profile_id: valueToProfileId(profileDraft) },
      );
      setDetail(updated);
      onSaved(updated);
      setToast(t("aiflow.ragCollections.detail.savedToast"));
    } catch (e) {
      if (e instanceof ApiClientError && e.status === 409) {
        setError(t("aiflow.ragCollections.detail.dimMismatch"));
      } else if (e instanceof Error) {
        setError(e.message);
      } else {
        setError("Save failed");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      data-testid="rag-collections-drawer"
      className="fixed inset-0 z-50 flex justify-end bg-black/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside className="flex h-full w-full max-w-md flex-col bg-white shadow-xl dark:bg-gray-900">
        <header className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              {collection.name}
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {collection.tenant_id} · {collection.embedding_dim}-dim
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="rag-collections-drawer-close"
            className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {loading && (
            <p className="text-sm text-gray-500">
              {t("aiflow.common.loading")}
            </p>
          )}

          {!loading && detail && (
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-500">
                  {t("aiflow.ragCollections.column.embedderProfile")}
                </dt>
                <dd className="mt-1">
                  <EmbedderProfileBadge
                    profileId={detail.embedder_profile_id}
                  />
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-500">
                  {t("aiflow.ragCollections.column.embeddingDim")}
                </dt>
                <dd className="mt-1 text-gray-900 dark:text-gray-100">
                  {detail.embedding_dim}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-500">
                  {t("aiflow.ragCollections.column.chunks")}
                </dt>
                <dd className="mt-1 text-gray-900 dark:text-gray-100">
                  {detail.chunk_count}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-500">
                  {t("aiflow.ragCollections.detail.embeddingModel")}
                </dt>
                <dd className="mt-1 text-gray-700 dark:text-gray-200 break-all">
                  {detail.embedding_model}
                </dd>
              </div>
              {detail.description && (
                <div>
                  <dt className="text-xs uppercase tracking-wide text-gray-500">
                    {t("aiflow.ragCollections.detail.description")}
                  </dt>
                  <dd className="mt-1 text-gray-700 dark:text-gray-200">
                    {detail.description}
                  </dd>
                </div>
              )}

              <div className="pt-3">
                <label
                  htmlFor="rag-collections-profile-select"
                  className="block text-xs font-semibold uppercase tracking-wide text-gray-500"
                >
                  {t("aiflow.ragCollections.detail.setProfile")}
                </label>
                <select
                  id="rag-collections-profile-select"
                  data-testid="rag-collections-profile-select"
                  value={profileDraft}
                  onChange={(e) => setProfileDraft(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
                >
                  {EMBEDDER_PROFILE_OPTIONS.map((opt) => (
                    <option
                      key={opt.value ?? "__null__"}
                      value={opt.value ?? "__null__"}
                    >
                      {opt.label}
                    </option>
                  ))}
                </select>
                {detail.chunk_count > 0 && (
                  <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                    {t("aiflow.ragCollections.detail.dimGuardWarning").replace(
                      "{dim}",
                      String(detail.embedding_dim),
                    )}
                  </p>
                )}
              </div>
            </dl>
          )}

          {error && (
            <p
              data-testid="rag-collections-drawer-error"
              className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800/50 dark:bg-red-900/20 dark:text-red-300"
            >
              {error}
            </p>
          )}
          {toast && (
            <p
              data-testid="rag-collections-drawer-toast"
              className="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-800 dark:border-green-800/50 dark:bg-green-900/20 dark:text-green-300"
            >
              {toast}
            </p>
          )}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            {t("aiflow.common.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
            data-testid="rag-collections-drawer-save"
            className="rounded-lg bg-brand-500 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("aiflow.ragCollections.detail.save")}
          </button>
        </footer>
      </aside>
    </div>
  );
}

// Re-export the list of valid select values so tests / consumers do not
// have to recompute the null-encoding sentinel.
export { SELECT_PROFILE_VALUES };
