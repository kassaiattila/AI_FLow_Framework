/** Chat header with collection selector, model selector, and clear history. */

import { AVAILABLE_MODELS } from "./types";

export function ChatHeader({
  collections,
  selectedCol,
  onSelectCol,
  showCollectionSelector,
  selectedModel,
  onSelectModel,
  onClearHistory,
  hasHistory,
  translate,
}: {
  collections: { id: string; name: string }[];
  selectedCol: string;
  onSelectCol: (id: string) => void;
  showCollectionSelector: boolean;
  selectedModel: string;
  onSelectModel: (model: string) => void;
  onClearHistory: () => void;
  hasHistory: boolean;
  translate: (key: string) => string;
}) {
  return (
    <div className="flex items-center gap-3 border-b border-gray-200 px-4 py-2 dark:border-gray-700">
      {/* Collection selector */}
      {showCollectionSelector && (
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {translate("aiflow.ragChat.collection")}
          </label>
          <select
            value={selectedCol}
            onChange={(e) => onSelectCol(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          >
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Model selector */}
      <div className="flex items-center gap-1.5">
        <label className="text-xs font-medium text-gray-500 dark:text-gray-400">
          {translate("aiflow.ragChat.model")}
        </label>
        <select
          value={selectedModel}
          onChange={(e) => {
            onSelectModel(e.target.value);
            try {
              localStorage.setItem("aiflow_chat_model", e.target.value);
            } catch {}
          }}
          className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          {AVAILABLE_MODELS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Clear history */}
      {hasHistory && (
        <button
          onClick={() => {
            if (
              window.confirm(translate("aiflow.ragChat.clearHistoryConfirm"))
            ) {
              onClearHistory();
            }
          }}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-300"
        >
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          {translate("aiflow.ragChat.clearHistory")}
        </button>
      )}
    </div>
  );
}
