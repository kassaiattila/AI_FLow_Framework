/**
 * CodeBlock — Syntax-highlighted code block with copy-to-clipboard button.
 *
 * Tailwind-styled, dark mode aware, no external highlighting library required.
 */

import { useState, useCallback } from "react";
import { useTranslate } from "../lib/i18n";

interface CodeBlockProps {
  code: string;
  language?: string;
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const translate = useTranslate();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [code]);

  const displayLang = language || "text";

  return (
    <div className="group relative rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-gray-200 px-3 py-1.5 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          {displayLang}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className={[
            "rounded px-2 py-0.5 text-xs font-medium transition-colors",
            copied
              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
              : "text-gray-500 hover:bg-gray-200 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200",
          ].join(" ")}
          aria-label={translate("aiflow.code.copy")}
        >
          {copied
            ? translate("aiflow.code.copied")
            : translate("aiflow.code.copy")}
        </button>
      </div>
      {/* Code content */}
      <pre className="overflow-x-auto p-3 text-sm leading-relaxed">
        <code className="font-mono text-gray-800 dark:text-gray-200">
          {code}
        </code>
      </pre>
    </div>
  );
}
