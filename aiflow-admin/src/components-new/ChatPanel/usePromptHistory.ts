/** Arrow-key prompt history (like terminal). */

import { useState, useCallback, useRef } from "react";

const MAX_HISTORY = 50;

export function usePromptHistory() {
  const [history, setHistory] = useState<string[]>([]);
  const indexRef = useRef(-1);

  const addToHistory = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setHistory((prev) => {
      const next = prev.filter((h) => h !== trimmed);
      next.push(trimmed);
      return next.slice(-MAX_HISTORY);
    });
    indexRef.current = -1;
  }, []);

  const navigateUp = useCallback((): string | null => {
    if (history.length === 0) return null;
    const next =
      indexRef.current === -1
        ? history.length - 1
        : Math.max(0, indexRef.current - 1);
    indexRef.current = next;
    return history[next] ?? null;
  }, [history]);

  const navigateDown = useCallback((): string | null => {
    if (indexRef.current === -1) return null;
    const next = indexRef.current + 1;
    if (next >= history.length) {
      indexRef.current = -1;
      return "";
    }
    indexRef.current = next;
    return history[next] ?? null;
  }, [history]);

  const resetNavigation = useCallback(() => {
    indexRef.current = -1;
  }, []);

  return { history, addToHistory, navigateUp, navigateDown, resetNavigation };
}
