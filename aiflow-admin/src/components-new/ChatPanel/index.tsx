/**
 * ChatPanel — professional RAG chat with per-message avatars, timestamps,
 * copy button, model selector, prompt history, and localStorage persistence.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { fetchApi } from "../../lib/api-client";
import { useTranslate, useLocale } from "../../lib/i18n";
import type { ChatPanelProps, QueryResponse, ChatMessage } from "./types";
import { ChatHeader } from "./ChatHeader";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ScrollToBottom } from "./ScrollToBottom";
import { useChatHistory } from "./useChatHistory";
import { usePromptHistory } from "./usePromptHistory";

export type { ChatPanelProps } from "./types";

export function ChatPanel({ collections, collectionId }: ChatPanelProps) {
  const translate = useTranslate();
  const locale = useLocale();

  const [selectedCol, setSelectedCol] = useState(collectionId ?? collections[0]?.id ?? "");
  const [selectedModel, setSelectedModel] = useState<string>(() =>
    localStorage.getItem("aiflow_chat_model") || "openai/gpt-4o",
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Keep selectedCol in sync when prop changes
  useEffect(() => {
    if (collectionId) setSelectedCol(collectionId);
  }, [collectionId]);

  // Hooks
  const { messages, addMessage, clearHistory } = useChatHistory(selectedCol);
  const { addToHistory, navigateUp, navigateDown, resetNavigation } = usePromptHistory();

  // Scroll management
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, []);

  // Track scroll position
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleScroll = () => {
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 40;
      setIsAtBottom(atBottom);
    };
    el.addEventListener("scroll", handleScroll, { passive: true });
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  // Auto-scroll when new messages arrive (only if already at bottom)
  useEffect(() => {
    if (isAtBottom) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => scrollToBottom());
    }
  }, [messages.length, loading, isAtBottom, scrollToBottom]);

  // Scroll to bottom on initial load (history restore)
  useEffect(() => {
    requestAnimationFrame(() => {
      const el = containerRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }, [selectedCol]);

  // Send message
  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || !selectedCol || loading) return;

    setInput("");
    resetNavigation();

    const userMsg: ChatMessage = {
      role: "user",
      content: question,
      timestamp: Date.now(),
    };
    addMessage(userMsg);
    addToHistory(question);
    setLoading(true);

    try {
      const res = await fetchApi<QueryResponse>(
        "POST",
        `/api/v1/rag/collections/${selectedCol}/query`,
        { question, role: "expert", top_k: 5, model: selectedModel },
      );

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.answer || translate("aiflow.ragChat.noAnswer"),
        sources: res.sources,
        responseTime: res.response_time_ms,
        timestamp: Date.now(),
        model: res.model_used ?? selectedModel,
      };
      addMessage(assistantMsg);
    } catch {
      addMessage({
        role: "assistant",
        content: translate("aiflow.ragChat.noAnswer"),
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  }, [input, selectedCol, selectedModel, loading, translate, addMessage, addToHistory, resetNavigation]);

  return (
    <div
      className="relative flex flex-col rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900"
      style={{ height: "calc(100vh - 320px)", minHeight: 400 }}
    >
      <ChatHeader
        collections={collections}
        selectedCol={selectedCol}
        onSelectCol={setSelectedCol}
        showCollectionSelector={!collectionId}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        onClearHistory={clearHistory}
        hasHistory={messages.length > 0}
        translate={translate}
      />

      {/* Messages area */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-3">
        {messages.length === 0 && !loading && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-400 dark:text-gray-500">
              {translate("aiflow.ragChat.empty")}
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} locale={locale} translate={translate} />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex items-start gap-3 px-1 py-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700">
              <svg className="h-4 w-4 text-gray-600 dark:text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div className="rounded-lg bg-gray-50 px-4 py-3 dark:bg-gray-800/60">
              <div className="flex gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.3s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.15s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      <ScrollToBottom visible={!isAtBottom && messages.length > 3} onClick={scrollToBottom} />

      {/* Input */}
      <ChatInput
        value={input}
        onChange={v => { setInput(v); resetNavigation(); }}
        onSend={() => void handleSend()}
        onNavigateUp={navigateUp}
        onNavigateDown={navigateDown}
        disabled={!selectedCol || loading}
        placeholder={translate("aiflow.ragChat.placeholder")}
        sendLabel={translate("aiflow.ragChat.send")}
      />
    </div>
  );
}
