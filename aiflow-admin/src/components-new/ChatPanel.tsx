/**
 * ChatPanel — reusable RAG chat panel with collection selector, message display,
 * collapsible sources, and response time. Extracted from Rag.tsx for reuse.
 */

import { useState, useRef, useEffect, useCallback, type FormEvent, type KeyboardEvent } from "react";
import { fetchApi } from "../lib/api-client";
import { useTranslate } from "../lib/i18n";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface QueryResponse {
  query_id: string;
  question: string;
  answer: string;
  sources: { text: string; score: number; document_title?: string }[];
  response_time_ms: number;
  cost_usd: number;
  source: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: { text: string; score: number; document_title?: string }[];
  responseTime?: number;
}

interface ChatPanelProps {
  /** Available RAG collections */
  collections: { id: string; name: string }[];
  /** Pre-selected collection id — hides the dropdown when set */
  collectionId?: string;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ChatPanel({ collections, collectionId }: ChatPanelProps) {
  const translate = useTranslate();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedCol, setSelectedCol] = useState<string>(collectionId ?? collections[0]?.id ?? "");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  /* Keep selectedCol in sync when prop changes */
  useEffect(() => {
    if (collectionId) setSelectedCol(collectionId);
  }, [collectionId]);

  /* Auto-scroll on new messages */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  /* ---------------------------------------------------------------- */
  /*  Send question                                                    */
  /* ---------------------------------------------------------------- */

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || !selectedCol || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await fetchApi<QueryResponse>(
        "POST",
        `/api/v1/rag/collections/${selectedCol}/query`,
        { question, role: "expert", top_k: 5 },
      );

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer || translate("aiflow.ragChat.noAnswer"),
          sources: res.sources,
          responseTime: res.response_time_ms,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: translate("aiflow.ragChat.noAnswer") },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, selectedCol, loading, translate]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void handleSend();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="flex h-[500px] flex-col rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      {/* Collection selector — hidden when collectionId prop is provided */}
      {!collectionId && (
        <div className="border-b border-gray-200 px-4 py-2 dark:border-gray-700">
          <label className="mr-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {translate("aiflow.ragChat.collection")}
          </label>
          <select
            value={selectedCol}
            onChange={(e) => setSelectedCol(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          >
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && !loading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-400 dark:text-gray-500">
              {translate("aiflow.ragChat.empty")}
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-brand-500 text-white"
                  : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
              }`}
            >
              {/* Message content */}
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Sources (assistant only) */}
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <details className="mt-2 border-t border-gray-200 pt-2 dark:border-gray-700">
                  <summary className="cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">
                    {msg.sources.length} {translate("aiflow.ragChat.sources")}
                  </summary>
                  <ul className="mt-1 space-y-1">
                    {msg.sources.map((src, sIdx) => (
                      <li
                        key={sIdx}
                        className="rounded bg-gray-50 p-2 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                      >
                        {src.document_title && (
                          <span className="mb-0.5 block font-semibold">{src.document_title}</span>
                        )}
                        <span className="line-clamp-3">{src.text}</span>
                        <span className="mt-0.5 block text-gray-400 dark:text-gray-500">
                          {Math.round(src.score * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}

              {/* Response time (assistant only) */}
              {msg.role === "assistant" && msg.responseTime != null && (
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                  {msg.responseTime}ms
                </p>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-gray-100 px-4 py-2 text-sm text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              ...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 border-t border-gray-200 px-4 py-3 dark:border-gray-700"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={translate("aiflow.ragChat.placeholder")}
          disabled={!selectedCol || loading}
          className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500"
        />
        <button
          type="submit"
          disabled={!input.trim() || !selectedCol || loading}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 dark:focus:ring-offset-gray-900"
        >
          {translate("aiflow.ragChat.send")}
        </button>
      </form>
    </div>
  );
}
