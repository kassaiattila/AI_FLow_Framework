/**
 * AIFlow IntentRules — S109a.
 *
 * List view (/emails/intent-rules):
 *   - tenant_id rows with rule_count + default_action
 *   - "+ Uj szabaly" button → opens editor for a blank tenant_id
 *
 * Editor view (/emails/intent-rules/:tenantId):
 *   - raw YAML textarea + inline validation (server returns 422 with detail)
 *   - save triggers PUT /api/v1/emails/intent-rules/:tenantId, navigates back
 *   - delete removes the YAML file
 *
 * The schema is ``aiflow.policy.intent_routing.IntentRoutingPolicy`` —
 * the server revalidates on every PUT so the UI only needs a lightweight
 * YAML check.
 */

import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslate } from "../lib/i18n";
import { useApi } from "../lib/hooks";
import { fetchApi, ApiClientError } from "../lib/api-client";
import { PageLayout } from "../layout/PageLayout";
import { LoadingState } from "../components-new/LoadingState";
import { ErrorState } from "../components-new/ErrorState";

interface IntentRulesListItem {
  tenant_id: string;
  rule_count: number;
  default_action: string;
  default_target: string;
  path: string;
}

interface IntentRulesListResponse {
  rules: IntentRulesListItem[];
  total: number;
  source: string;
}

interface IntentRulesDetail {
  tenant_id: string;
  default_action: string;
  default_target: string;
  rules: Array<Record<string, unknown>>;
  yaml_text: string;
  path: string;
  source: string;
}

const YAML_TEMPLATE = `tenant_id: default
default_action: manual_review
default_target: inbox
rules:
  - intent_label: invoice_question
    action: extract
    target: invoice_pipeline
    min_confidence: 0.6
  - intent_label: support_request
    action: notify_dept
    target: helpdesk
    min_confidence: 0.5
  - intent_label: spam
    action: archive
    target: ""
    min_confidence: 0.5
`;

export function IntentRules() {
  const { tenantId } = useParams<{ tenantId?: string }>();
  return tenantId ? <IntentRulesEditor tenantId={tenantId} /> : <IntentRulesList />;
}

function IntentRulesList() {
  const translate = useTranslate();
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useApi<IntentRulesListResponse>(
    "/api/v1/emails/intent-rules",
  );
  const [newTenantId, setNewTenantId] = useState("");

  const validate = (id: string) => /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$/.test(id);

  const handleNew = () => {
    if (!validate(newTenantId)) return;
    navigate(`/emails/intent-rules/${encodeURIComponent(newTenantId)}`);
  };

  return (
    <PageLayout
      titleKey="aiflow.intentRules.title"
      subtitleKey="aiflow.intentRules.subtitle"
    >
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate("/emails")}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
        >
          ← {translate("common.action.back")}
        </button>
      </div>

      <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          {translate("aiflow.intentRules.newTitle") || "Uj szabaly"}
        </h3>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={newTenantId}
            onChange={e => setNewTenantId(e.target.value)}
            placeholder="tenant_id (pl: default, acme, partner1)"
            className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
          <button
            onClick={handleNew}
            disabled={!validate(newTenantId)}
            className="rounded-lg bg-brand-500 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {translate("common.action.create") || "Letrehozas"}
          </button>
        </div>
        {newTenantId && !validate(newTenantId) && (
          <p className="mt-2 text-xs text-red-600">
            Ervenytelen tenant_id: csak a-z A-Z 0-9 _ . - karaktereket tartalmazhat.
          </p>
        )}
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState error={error} onRetry={refetch} />}
      {!loading && !error && (
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
          {data && data.rules.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
              {translate("aiflow.intentRules.empty") || "Meg nincs intent szabaly. Hozz letre egyet fent."}
            </div>
          ) : (
            <table className="w-full">
              <thead className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-2">tenant_id</th>
                  <th className="px-4 py-2">szabalyok</th>
                  <th className="px-4 py-2">default action</th>
                  <th className="px-4 py-2">default target</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data?.rules.map(r => (
                  <tr
                    key={r.tenant_id}
                    onClick={() => navigate(`/emails/intent-rules/${encodeURIComponent(r.tenant_id)}`)}
                    className="cursor-pointer border-t border-gray-100 hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800"
                  >
                    <td className="px-4 py-3 font-mono text-sm text-gray-900 dark:text-gray-100">{r.tenant_id}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{r.rule_count}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{r.default_action}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{r.default_target || "—"}</td>
                    <td className="px-4 py-3 text-right text-sm text-brand-600 dark:text-brand-400">Szerkesztes →</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </PageLayout>
  );
}

function IntentRulesEditor({ tenantId }: { tenantId: string }) {
  const translate = useTranslate();
  const navigate = useNavigate();
  const { data, loading, error } = useApi<IntentRulesDetail>(
    `/api/v1/emails/intent-rules/${encodeURIComponent(tenantId)}`,
  );
  const [yamlText, setYamlText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const is404 = useMemo(
    () => typeof error === "string" && error.includes("404"),
    [error],
  );

  useEffect(() => {
    if (data?.yaml_text) setYamlText(data.yaml_text);
    else if (is404 && !yamlText) {
      // new tenant — seed template with the path-provided tenant_id
      setYamlText(YAML_TEMPLATE.replace("tenant_id: default", `tenant_id: ${tenantId}`));
    }
  }, [data, is404, tenantId]); // yamlText intentionally omitted — only seed once

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      await fetchApi<IntentRulesDetail>(
        "PUT",
        `/api/v1/emails/intent-rules/${encodeURIComponent(tenantId)}`,
        { yaml_text: yamlText },
      );
      setSaveOk(true);
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

  const handleDelete = async () => {
    setSaving(true);
    try {
      await fetchApi<void>(
        "DELETE",
        `/api/v1/emails/intent-rules/${encodeURIComponent(tenantId)}`,
      );
      navigate("/emails/intent-rules");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setSaving(false);
      setShowDeleteConfirm(false);
    }
  };

  if (loading && !is404) return <LoadingState />;

  return (
    <PageLayout
      titleKey="aiflow.intentRules.editorTitle"
      subtitleKey="aiflow.intentRules.subtitle"
    >
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate("/emails/intent-rules")}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400"
        >
          ← {translate("common.action.back")}
        </button>
        <span className="font-mono text-sm text-gray-500">{tenantId}</span>
        {is404 && (
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
            uj
          </span>
        )}
      </div>

      <div className="mb-3 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            YAML
          </h3>
          <textarea
            value={yamlText}
            onChange={e => setYamlText(e.target.value)}
            spellCheck={false}
            className="h-[400px] w-full rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-xs text-gray-800 focus:border-brand-500 focus:outline-none dark:border-gray-700 dark:bg-gray-950 dark:text-gray-200"
          />
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Schema cheatsheet
          </h3>
          <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">tenant_id</code>: string (URL-lel egyeznie kell)</li>
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">default_action</code>: extract | notify_dept | archive | manual_review | reply_auto</li>
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">default_target</code>: string (opcionalis)</li>
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">rules[].intent_label</code>: string (intent_id)</li>
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">rules[].action</code>: same enum as default_action</li>
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">rules[].target</code>: string (queue / department / template id)</li>
            <li><code className="rounded bg-gray-100 px-1 dark:bg-gray-800">rules[].min_confidence</code>: 0.0 — 1.0</li>
          </ul>
          <p className="mt-3 text-xs text-gray-500">
            Ertekeles: <em>first-match-wins</em>. Ha egy szabaly sem passzol, a <code>default_action</code> aktivalodik.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving || !yamlText.trim()}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
        >
          {saving ? translate("aiflow.common.loading") : (translate("common.action.save") || "Mentes")}
        </button>
        {!is404 && (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            disabled={saving}
            className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            {translate("common.action.delete") || "Torles"}
          </button>
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

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl dark:bg-gray-900">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Szabaly torlese: {tenantId}?
            </h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Ez torli a <code>{data?.path}</code> fajlt. A folyamatban levo scan-ek
              visszaesnek a default policy-re.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                {translate("common.action.cancel")}
              </button>
              <button
                onClick={handleDelete}
                disabled={saving}
                className="rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white hover:bg-red-600 disabled:opacity-50"
              >
                {translate("common.action.delete") || "Torles"}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
