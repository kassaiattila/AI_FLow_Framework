/**
 * RecognizePanel — drag-drop file upload + result display.
 * Sprint V SV-4.
 */

import { useState } from "react";
import { fetchApi } from "../../lib/api-client";
import type { DoctypeListItem, RecognizeResponse } from "./types";

interface Props {
  doctypes: DoctypeListItem[];
}

export function RecognizePanel({ doctypes }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [docTypeHint, setDocTypeHint] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RecognizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Pick a file first");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (docTypeHint) formData.append("doc_type_hint", docTypeHint);

      const url = "/api/v1/document-recognizer/recognize";
      const response = await fetch(url, {
        method: "POST",
        body: formData,
        credentials: "include",
        headers: {
          // Bearer token wired by api-client interceptor
          Authorization: `Bearer ${localStorage.getItem("auth_token") ?? ""}`,
        },
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`HTTP ${response.status}: ${detail}`);
      }
      const data = (await response.json()) as RecognizeResponse;
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recognize failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="recognize-panel">
      <form
        onSubmit={handleSubmit}
        className="mb-4 rounded-lg border border-gray-200 p-4 dark:border-gray-700"
      >
        <h3 className="mb-3 text-sm font-semibold">Upload + recognize</h3>
        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            File (PDF / DOCX / image / text)
          </label>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.tiff"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm"
            data-testid="recognize-file-input"
          />
        </div>
        <div className="mb-3">
          <label className="mb-1 block text-xs text-gray-600 dark:text-gray-400">
            Doc-type hint (optional)
          </label>
          <select
            value={docTypeHint}
            onChange={(e) => setDocTypeHint(e.target.value)}
            className="block w-full rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800"
            data-testid="recognize-hint-select"
          >
            <option value="">Auto-detect</option>
            {doctypes.map((d) => (
              <option key={d.name} value={d.name}>
                {d.display_name} ({d.name})
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={busy || !file}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          data-testid="recognize-submit"
        >
          {busy ? "Recognizing…" : "Recognize"}
        </button>
      </form>

      {error && (
        <div
          className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-700 dark:bg-red-900/20 dark:text-red-200"
          data-testid="recognize-error"
        >
          {error}
        </div>
      )}

      {result && (
        <div
          className="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
          data-testid="recognize-result"
        >
          <h3 className="mb-2 text-sm font-semibold">Result</h3>
          <dl className="mb-3 grid grid-cols-2 gap-y-1 text-xs">
            <dt className="text-gray-500">Run ID</dt>
            <dd className="font-mono">{result.run_id}</dd>
            <dt className="text-gray-500">Doc type</dt>
            <dd className="font-mono">{result.match.doc_type}</dd>
            <dt className="text-gray-500">Confidence</dt>
            <dd>{(result.match.confidence * 100).toFixed(1)}%</dd>
            <dt className="text-gray-500">Method</dt>
            <dd>{result.classification_method}</dd>
            <dt className="text-gray-500">Intent</dt>
            <dd className="font-mono">{result.intent.intent}</dd>
            <dt className="text-gray-500">PII redacted</dt>
            <dd>{result.pii_redacted ? "Yes" : "No"}</dd>
            <dt className="text-gray-500">Cost</dt>
            <dd>${result.extraction.cost_usd.toFixed(4)}</dd>
          </dl>
          {result.intent.reason && (
            <p className="mb-3 text-xs italic text-gray-600 dark:text-gray-400">
              {result.intent.reason}
            </p>
          )}
          <h4 className="mb-1 text-xs font-semibold">Extracted fields</h4>
          {Object.keys(result.extraction.extracted_fields).length === 0 ? (
            <p className="text-xs text-gray-500">
              (No fields extracted — SV-3 ships a placeholder; SV-3+ wires
              PromptWorkflow extraction.)
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-left text-gray-500">
                <tr>
                  <th className="px-2 py-1">Field</th>
                  <th className="px-2 py-1">Value</th>
                  <th className="px-2 py-1 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {Object.entries(result.extraction.extracted_fields).map(
                  ([name, fv]) => (
                    <tr key={name}>
                      <td className="px-2 py-1 font-mono">{name}</td>
                      <td className="px-2 py-1">
                        {fv.value === null ? (
                          <span className="text-gray-400">—</span>
                        ) : (
                          String(fv.value)
                        )}
                      </td>
                      <td className="px-2 py-1 text-right">
                        {(fv.confidence * 100).toFixed(0)}%
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
