/** localStorage-backed chat history per collection. */

import { useState, useCallback, useRef, useEffect } from "react";
import type { ChatMessage } from "./types";

const MAX_MESSAGES = 100;
const DEBOUNCE_MS = 500;

function storageKey(collectionId: string) {
  return `aiflow_chat_history_${collectionId}`;
}

function loadMessages(collectionId: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(storageKey(collectionId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(-MAX_MESSAGES) : [];
  } catch {
    return [];
  }
}

export function useChatHistory(collectionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadMessages(collectionId),
  );
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  // Reload when collection changes
  useEffect(() => {
    setMessages(loadMessages(collectionId));
  }, [collectionId]);

  // Debounced persist
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      try {
        const trimmed = messages.slice(-MAX_MESSAGES);
        localStorage.setItem(storageKey(collectionId), JSON.stringify(trimmed));
      } catch {
        /* quota exceeded — ignore */
      }
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [messages, collectionId]);

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg].slice(-MAX_MESSAGES));
  }, []);

  const clearHistory = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(storageKey(collectionId));
  }, [collectionId]);

  return { messages, addMessage, clearHistory };
}
