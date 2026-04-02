/**
 * EmptyState — meaningful empty state with icon + message + optional CTA.
 * Use instead of inline "no data" text.
 */

import { useTranslate } from "../lib/i18n";

interface EmptyStateProps {
  messageKey: string;
  icon?: "inbox" | "search" | "file" | "mail";
  actionLabel?: string;
  onAction?: () => void;
}

const ICONS: Record<string, string> = {
  inbox: "M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4",
  search: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  file: "M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z",
  mail: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z",
};

export function EmptyState({ messageKey, icon = "inbox", actionLabel, onAction }: EmptyStateProps) {
  const translate = useTranslate();

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <svg
        className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={ICONS[icon]} />
      </svg>
      <p className="text-sm text-gray-500 dark:text-gray-400">{translate(messageKey)}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-3 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          {translate(actionLabel)}
        </button>
      )}
    </div>
  );
}
