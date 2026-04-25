/**
 * AIFlow shared hooks — useApi, useBackendStatus, etc.
 */

import { useState, useEffect, useCallback } from "react";
import { fetchApi, ApiClientError } from "./api-client";

/** Generic data fetching hook replacing React Admin's useGetList/useGetOne */
export function useApi<T>(
  path: string | null,
  options?: { refetchInterval?: number },
): {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(!!path);
  const [error, setError] = useState<string | null>(null);

  const doFetch = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchApi<T>("GET", path);
      setData(result);
    } catch (e) {
      if (e instanceof ApiClientError) {
        setError(`${e.status}: ${e.message}`);
      } else {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    doFetch();
  }, [doFetch]);

  useEffect(() => {
    if (!options?.refetchInterval || !path) return;
    const interval = setInterval(doFetch, options.refetchInterval);
    return () => clearInterval(interval);
  }, [doFetch, options?.refetchInterval, path]);

  return { data, loading, error, refetch: doFetch };
}

/** Backend connection status hook */
export function useBackendStatus(): "checking" | "connected" | "offline" {
  const [status, setStatus] = useState<"checking" | "connected" | "offline">(
    "checking",
  );

  useEffect(() => {
    fetch("/health")
      .then((r) => setStatus(r.ok ? "connected" : "offline"))
      .catch(() => setStatus("offline"));
  }, []);

  return status;
}

/** Theme hook — persists in localStorage, defaults to dark */
export function useTheme(): {
  theme: "light" | "dark";
  toggleTheme: () => void;
} {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "dark";
    return (localStorage.getItem("aiflow_theme") as "light" | "dark") || "dark";
  });

  useEffect(() => {
    localStorage.setItem("aiflow_theme", theme);
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "light" ? "dark" : "light"));
  }, []);

  return { theme, toggleTheme };
}
