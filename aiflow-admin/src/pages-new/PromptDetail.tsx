/**
 * AIFlow PromptDetail — S109b.
 *
 * Edit YAML text for a single prompt + save → PUT /api/v1/prompts/:name.
 * The endpoint writes the file back and invalidates the PromptManager cache
 * so the next skill run picks up the new content.
 *
 * No Langfuse SDK write-back here — YAML is still the SSOT, and the Langfuse
 * sync is driven by the existing ``prompts/sync.py`` CLI / backend job.
 */

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi, ApiClientError } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";

interface PromptDetail {
  name: string;
  version: string | number | null;
  path: string;
  updated_at: string;
  tags: string[];
  yaml_text: string;
  source: string;
}

export function PromptDetail() {
  const { "*": splat } = useParams<{ "*": string }>();
  const promptName = splat ?? "";
  const translate = useTranslate();
  const navigate = useNavigate();
  const apiPath = promptName ? `/api/v1/prompts/${encodeURI(promptName)}` : null;
  const { data, loading, error, refetch } = useApi<PromptDetail>(apiPath);
  const [yamlText, setYamlText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  useEffect(() => {
    if (data?.yaml_text !== undefined) setYamlText(data.yaml_text);
  }, [data]);

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState error={error || "Not found"} onRetry={refetch} />;

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      await fetchApi<PromptDetail>(
        "PUT",
        `/api/v1/prompts/${encodeURI(promptName)}`,
        { yaml_text: yamlText },
      );
      setSaveOk(true);
      refetch();
      setTimeout(() => setSaveOk(false), 2000);
    } catch (e) {
      if (e instanceof ApiClientError) {
        const detail = typeof e.detail === "string"
          ? e.detail
          : JSON.stringify(e.detail, null, 2);
        setSaveError(`${e.status}: ${detail}`);
      } else {
        setSaveError(e instanceof Error ? e.message : "Save failed");
      }
    } finally {
      setSaving(false);
    }
  };

  const dirty = yamlText !== data.yaml_text;
  const updatedFmt = data.updated_at
    ? new Date(data.updated_at).toLocaleString()
    : "—";

  return (
    <PageLayout titleKey="aiflow.prompts.editorTitle">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button
          onClick={() => navigate("/prompts")}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
        >
          ← {translate("common.action.back")}
        </button>
        <span className="font-mono text-sm text-gray-500">{data.name}</span>
        {data.version && (
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
            v{data.version}
          </span>
        )}
        {data.tags.map(t => (
          <span key={t} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
            {t}
          </span>
        ))}
        <span className="text-xs text-gray-400">updated {updatedFmt}</span>
      </div>

      <div className="mb-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          YAML
        </h3>
        <textarea
          value={yamlText}
          onChange={e => setYamlText(e.target.value)}
          spellCheck={false}
          className="h-[500px] w-full rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-xs text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
        />
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          A <code>name</code> mezot nem szabad megvaltoztatni (URL-lel egyeznie kell).
          A mentes utan a PromptManager cache invalidalodik, a kovetkezo hivas mar
          az uj verziot hasznalja.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving || !dirty}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {saving ? translate("aiflow.common.loading") : translate("common.action.save")}
        </button>
        {dirty && !saving && (
          <span className="text-xs text-amber-600 dark:text-amber-400">
            Mentetlen valtoztatasok
          </span>
        )}
        {saveOk && (
          <span className="rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
            ✓ Mentve
          </span>
        )}
        {saveError && (
          <pre className="flex-1 overflow-auto rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            {saveError}
          </pre>
        )}
      </div>
    </PageLayout>
  );
}
