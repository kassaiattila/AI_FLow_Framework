/** Chat input textarea with auto-resize, Shift+Enter, and prompt history. */

import { useRef, useCallback, useEffect, type KeyboardEvent } from "react";

export function ChatInput({
  value,
  onChange,
  onSend,
  onNavigateUp,
  onNavigateDown,
  disabled,
  placeholder,
  sendLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onNavigateUp: () => string | null;
  onNavigateDown: () => string | null;
  disabled: boolean;
  placeholder: string;
  sendLabel: string;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea to fit content
  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  useEffect(autoResize, [value, autoResize]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter (without shift) or Cmd/Ctrl+Enter → submit
    if (e.key === "Enter" && (!e.shiftKey || e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSend();
      return;
    }

    // Escape → clear input
    if (e.key === "Escape") {
      e.preventDefault();
      onChange("");
      return;
    }

    if (e.key === "ArrowUp" && textareaRef.current) {
      const pos = textareaRef.current.selectionStart;
      if (pos === 0 || !value) {
        const prev = onNavigateUp();
        if (prev !== null) {
          e.preventDefault();
          onChange(prev);
        }
      }
    }

    if (e.key === "ArrowDown" && textareaRef.current) {
      const pos = textareaRef.current.selectionEnd;
      if (pos >= value.length) {
        const next = onNavigateDown();
        if (next !== null) {
          e.preventDefault();
          onChange(next);
        }
      }
    }
  };

  return (
    <div className="flex items-end gap-2 border-t border-gray-200 px-4 py-3 dark:border-gray-700">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
        style={{ maxHeight: 200 }}
      />
      <button
        onClick={onSend}
        disabled={!value.trim() || disabled}
        className="shrink-0 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 dark:focus:ring-offset-gray-900"
      >
        {sendLabel}
      </button>
    </div>
  );
}
