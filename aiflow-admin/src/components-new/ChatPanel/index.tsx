/**
 * ChatPanel — professional RAG chat with per-message avatars, timestamps,
 * copy button, model selector, prompt history, and localStorage persistence.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
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

  const [selectedCol, setSelectedCol] = useState(
    collectionId ?? collections[0]?.id ?? "",
  );
  const [selectedModel, setSelectedModel] = useState<string>(
    () => localStorage.getItem("aiflow_chat_model") || "openai/gpt-4o",
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Keep selectedCol in sync when prop changes
  useEffect(() => {
    if (collectionId) setSelectedCol(collectionId);
  }, [collectionId]);

  // If collections arrive after mount and no selection exists yet, pick the first one
  useEffect(() => {
    if (!selectedCol && collections.length > 0) {
      setSelectedCol(collections[0].id);
    }
  }, [collections, selectedCol]);

  // Hooks
  const { messages, addMessage, clearHistory } = useChatHistory(selectedCol);
  const { addToHistory, navigateUp, navigateDown, resetNavigation } =
    usePromptHistory();

  // Virtual scroll & scroll management
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Item count: messages + optional loading indicator
  const itemCount = messages.length + (loading ? 1 : 0);

  const virtualizer = useVirtualizer({
    count: itemCount,
    getScrollElement: () => containerRef.current,
    estimateSize: () => 100,
    overscan: 5,
  });

  const scrollToBottom = useCallback(() => {
    if (itemCount > 0) {
      virtualizer.scrollToIndex(itemCount - 1, {
        align: "end",
        behavior: "smooth",
      });
    }
  }, [virtualizer, itemCount]);

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
    if (isAtBottom && itemCount > 0) {
      requestAnimationFrame(() => {
        virtualizer.scrollToIndex(itemCount - 1, { align: "end" });
      });
    }
  }, [itemCount, isAtBottom, virtualizer]);

  // Scroll to bottom on collection change (history restore)
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
  }, [
    input,
    selectedCol,
    selectedModel,
    loading,
    translate,
    addMessage,
    addToHistory,
    resetNavigation,
  ]);

  return (
    <div
      className="relative flex flex-col rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 max-md:h-[calc(100dvh-64px)] max-md:rounded-none max-md:border-0"
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

      {/* Messages area — virtualized */}
      <div ref={containerRef} className="flex-1 overflow-y-auto px-4 py-3">
        {messages.length === 0 && !loading ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-gray-400 dark:text-gray-500">
              {translate("aiflow.ragChat.empty")}
            </p>
          </div>
        ) : (
          <div
            style={{
              height: `${virtualizer.getTotalSize()}px`,
              width: "100%",
              position: "relative",
            }}
          >
            {virtualizer.getVirtualItems().map((virtualItem) => {
              const idx = virtualItem.index;
              const isLoadingItem = idx === messages.length;

              return (
                <div
                  key={virtualItem.key}
                  data-index={idx}
                  ref={virtualizer.measureElement}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${virtualItem.start}px)`,
                  }}
                >
                  {isLoadingItem ? (
                    <div className="flex items-start gap-3 px-1 py-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700">
                        <svg
                          className="h-4 w-4 text-gray-600 dark:text-gray-300"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                          />
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
                  ) : (
                    <MessageBubble
                      message={messages[idx]}
                      locale={locale}
                      translate={translate}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Scroll to bottom button */}
      <ScrollToBottom
        visible={!isAtBottom && messages.length > 3}
        onClick={scrollToBottom}
      />

      {/* Input — sticky on mobile */}
      <div className="max-md:sticky max-md:bottom-0 max-md:bg-white max-md:dark:bg-gray-900">
        <ChatInput
          value={input}
          onChange={(v) => {
            setInput(v);
            resetNavigation();
          }}
          onSend={() => void handleSend()}
          onNavigateUp={navigateUp}
          onNavigateDown={navigateDown}
          disabled={!selectedCol || loading}
          placeholder={translate("aiflow.ragChat.placeholder")}
          sendLabel={translate("aiflow.ragChat.send")}
        />
      </div>
    </div>
  );
}
