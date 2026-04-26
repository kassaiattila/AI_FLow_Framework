/**
 * DocTypeDetailDrawer — descriptor detail + YAML editor + save / delete.
 * Sprint V SV-4.
 */

import { useState } from "react";
import { fetchApi } from "../../lib/api-client";
import { PiiBadge } from "./PiiBadge";
import type {
  DoctypeDetailResponse,
  DoctypeListItem,
  DoctypeOverrideResponse,
} from "./types";

interface Props {
  item: DoctypeListItem;
  detail: DoctypeDetailResponse;
  onClose: () => void;
  onSaved: () => void;
}

export function DocTypeDetailDrawer({ item, detail, onClose, onSaved }: Props) {
  const [editing, setEditing] = useState(false);
  const [yamlText, setYamlText] = useState<string>(() => yamlPreview(detail));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setBusy(true);
    setError(null);
    try {
      await fetchApi<DoctypeOverrideResponse>(
        "PUT",
        `/api/v1/document-recognizer/doctypes/${encodeURIComponent(item.name)}`,
        { yaml_text: yamlText },
      );
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteOverride = async () => {
    setBusy(true);
    setError(null);
    try {
      await fetchApi<void>(
        "DELETE",
        `/api/v1/document-recognizer/doctypes/${encodeURIComponent(item.name)}`,
      );
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside
      className="fixed right-0 top-0 z-50 flex h-screen w-[640px] flex-col border-l border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900"
      data-testid="doctype-detail-drawer"
    >
      <header className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <h2 className="font-mono text-sm">{item.name}</h2>
          <PiiBadge level={item.pii_level} />
          {detail.has_tenant_override && (
            <span
              className="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-800 dark:bg-purple-900 dark:text-purple-200"
              data-testid="drawer-override-badge"
            >
              Tenant override
            </span>
          )}
        </div>
        <button
          type="button"
          className="rounded px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          onClick={onClose}
          data-testid="drawer-close"
        >
          ✕
        </button>
      </header>

      <div className="flex-1 overflow-auto p-4">
        <dl className="mb-4 grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-gray-500">Display name</dt>
          <dd>{detail.descriptor.display_name}</dd>
          <dt className="text-gray-500">Language</dt>
          <dd>{detail.descriptor.language}</dd>
          <dt className="text-gray-500">Category</dt>
          <dd>{detail.descriptor.category}</dd>
          <dt className="text-gray-500">Workflow</dt>
          <dd className="font-mono text-xs">{detail.descriptor.extraction.workflow}</dd>
          <dt className="text-gray-500">Default intent</dt>
          <dd className="font-mono text-xs">
            {detail.descriptor.intent_routing.default}
          </dd>
          <dt className="text-gray-500">PII redaction</dt>
          <dd>{detail.descriptor.intent_routing.pii_redaction ? "Yes" : "No"}</dd>
          <dt className="text-gray-500">Field count</dt>
          <dd>{detail.descriptor.extraction.fields.length}</dd>
          <dt className="text-gray-500">Source</dt>
          <dd className="text-xs">{detail.source}</dd>
        </dl>

        <div className="mb-4">
          <h3 className="mb-2 text-sm font-semibold">Classifier rules</h3>
          <ul className="space-y-1 text-xs">
            {detail.descriptor.type_classifier.rules.map((rule, idx) => (
              <li
                key={`${rule.kind}-${idx}`}
                className="flex items-start gap-2 rounded bg-gray-50 p-2 dark:bg-gray-800/50"
              >
                <span className="rounded bg-blue-100 px-1.5 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                  {rule.kind}
                </span>
                <span className="text-gray-500">w={rule.weight}</span>
                {rule.pattern && (
                  <code className="flex-1 truncate">{rule.pattern}</code>
                )}
                {rule.keywords && (
                  <span className="flex-1 truncate">
                    {rule.keywords.join(", ")} (≥{rule.threshold})
                  </span>
                )}
                {rule.hint && <code className="flex-1 truncate">{rule.hint}</code>}
              </li>
            ))}
          </ul>
        </div>

        <div className="mb-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">YAML editor</h3>
            <button
              type="button"
              className="rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700"
              onClick={() => setEditing(!editing)}
              data-testid="toggle-edit"
            >
              {editing ? "Cancel edit" : "Override for tenant"}
            </button>
          </div>
          <textarea
            className="h-64 w-full rounded border border-gray-300 bg-gray-50 p-2 font-mono text-xs dark:border-gray-700 dark:bg-gray-800/50"
            value={yamlText}
            onChange={(e) => setYamlText(e.target.value)}
            readOnly={!editing}
            data-testid="yaml-editor"
          />
        </div>

        {error && (
          <div className="mb-4 rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800 dark:border-red-700 dark:bg-red-900/20 dark:text-red-200">
            {error}
          </div>
        )}
      </div>

      <footer className="flex items-center justify-end gap-2 border-t border-gray-200 px-4 py-3 dark:border-gray-700">
        {detail.has_tenant_override && (
          <button
            type="button"
            className="rounded border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/20"
            onClick={handleDeleteOverride}
            disabled={busy}
            data-testid="delete-override"
          >
            Delete tenant override
          </button>
        )}
        {editing && (
          <button
            type="button"
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            onClick={handleSave}
            disabled={busy}
            data-testid="save-override"
          >
            {busy ? "Saving…" : "Save tenant override"}
          </button>
        )}
      </footer>
    </aside>
  );
}

function yamlPreview(detail: DoctypeDetailResponse): string {
  // Lightweight YAML preview — operators can paste a full YAML to override.
  // We don't pull js-yaml; a simple deterministic dump is sufficient.
  const d = detail.descriptor;
  return `name: ${d.name}
display_name: ${JSON.stringify(d.display_name)}
language: ${d.language}
category: ${d.category}
version: ${d.version}
pii_level: ${d.pii_level}
parser_preferences:
${d.parser_preferences.map((p) => `  - ${p}`).join("\n")}
type_classifier:
  llm_fallback: ${d.type_classifier.llm_fallback}
  llm_threshold_below: ${d.type_classifier.llm_threshold_below}
  rules:
${d.type_classifier.rules
  .map(
    (r) =>
      `    - kind: ${r.kind}\n      weight: ${r.weight}` +
      (r.pattern ? `\n      pattern: ${JSON.stringify(r.pattern)}` : "") +
      (r.keywords
        ? `\n      keywords: ${JSON.stringify(r.keywords)}\n      threshold: ${r.threshold}`
        : "") +
      (r.hint ? `\n      hint: ${JSON.stringify(r.hint)}` : ""),
  )
  .join("\n")}
extraction:
  workflow: ${d.extraction.workflow}
  fields:
${d.extraction.fields
  .map((f) => `    - name: ${f.name}\n      type: ${f.type}\n      required: ${f.required}`)
  .join("\n")}
intent_routing:
  default: ${d.intent_routing.default}
  pii_redaction: ${d.intent_routing.pii_redaction}
`;
}
