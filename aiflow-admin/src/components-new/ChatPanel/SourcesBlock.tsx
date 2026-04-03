/** Collapsible sources display for assistant messages. */

import { useState } from "react";
import type { ChatSource } from "./types";

export function SourcesBlock({
  sources,
  translate,
}: {
  sources: ChatSource[];
  translate: (key: string) => string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2 border-t border-gray-200 pt-1.5 dark:border-gray-700">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
      >
        <svg
          className={`h-3 w-3 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {sources.length} {translate("aiflow.ragChat.sources")}
      </button>
      {open && (
        <div className="mt-1.5 space-y-1">
          {sources.map((src, sIdx) => (
            <div
              key={sIdx}
              className="flex items-start gap-2 rounded-md bg-gray-50 px-2.5 py-2 text-xs dark:bg-gray-700/60"
            >
              <span className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded bg-brand-100 text-[10px] font-bold text-brand-700 dark:bg-brand-900/40 dark:text-brand-400">
                {sIdx + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium text-gray-700 dark:text-gray-300">
                    {src.document_title || `Source ${sIdx + 1}`}
                  </span>
                  <span className="shrink-0 rounded-full bg-brand-100 px-1.5 py-0.5 text-[10px] font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-400">
                    {Math.round(src.score * 100)}%
                  </span>
                </div>
                <p className="mt-0.5 line-clamp-3 text-gray-500 dark:text-gray-400">{src.text}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
