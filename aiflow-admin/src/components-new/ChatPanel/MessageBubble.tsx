/** Single chat message — left-aligned, with avatar, timestamp, copy button. */

import { useState } from "react";
import type { ChatMessage } from "./types";
import { SourcesBlock } from "./SourcesBlock";

/** Format timestamp as HH:mm or date+time for older messages */
function formatTime(ts: number, locale: string): string {
  const d = new Date(ts);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) return d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString(locale, { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
}

/** Extract short model label from full id */
function modelLabel(model?: string): string {
  if (!model) return "";
  const parts = model.split("/");
  const name = parts[parts.length - 1];
  return name.replace(/-\d{8}$/, "").replace(/^gpt-/, "GPT-").replace(/^claude-/, "Claude ");
}

export function MessageBubble({
  message,
  locale,
  translate,
}: {
  message: ChatMessage;
  locale: string;
  translate: (key: string) => string;
}) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard API not available */ }
  };

  return (
    <div className="group flex items-start gap-3 px-1 py-2">
      {/* Avatar */}
      <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
        isUser
          ? "bg-brand-100 text-brand-600 dark:bg-brand-900/40 dark:text-brand-400"
          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
      }`}>
        {isUser ? (
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        ) : (
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
          </svg>
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        {/* Name + timestamp + copy button */}
        <div className="mb-1 flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {isUser ? translate("aiflow.ragChat.you") : translate("aiflow.ragChat.assistant")}
          </span>
          <span className="text-xs text-gray-400">
            {formatTime(message.timestamp, locale)}
          </span>
          {!isUser && (
            <button
              onClick={handleCopy}
              className="ml-auto opacity-0 transition-opacity group-hover:opacity-100"
              title={copied ? translate("aiflow.ragChat.copied") : "Copy"}
            >
              {copied ? (
                <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="h-4 w-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                </svg>
              )}
            </button>
          )}
        </div>

        {/* Message body */}
        <div className={`rounded-lg px-4 py-3 text-sm ${
          isUser
            ? "bg-brand-50 text-gray-900 dark:bg-brand-900/20 dark:text-gray-100"
            : "bg-gray-50 text-gray-900 dark:bg-gray-800/60 dark:text-gray-100"
        }`}>
          <p className="whitespace-pre-wrap">{message.content}</p>

          {/* Sources */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <SourcesBlock sources={message.sources} translate={translate} />
          )}
        </div>

        {/* Metadata (assistant only) */}
        {!isUser && (message.responseTime != null || message.model) && (
          <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
            {message.responseTime != null && <span>{message.responseTime}ms</span>}
            {message.model && (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                {modelLabel(message.model)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
