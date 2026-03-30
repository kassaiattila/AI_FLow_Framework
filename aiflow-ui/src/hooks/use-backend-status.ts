"use client";

import { useState, useEffect, useCallback } from "react";

export interface BackendStatus {
  status: "connected" | "offline" | "checking";
  isDemo: boolean;
  timestamp: string | null;
}

const POLL_INTERVAL = 30000; // 30 seconds

export function useBackendStatus(): BackendStatus {
  const [state, setState] = useState<BackendStatus>({
    status: "checking",
    isDemo: true,
    timestamp: null,
  });

  const check = useCallback(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((data: { status: "connected" | "offline"; timestamp: string }) => {
        setState({
          status: data.status,
          isDemo: data.status !== "connected",
          timestamp: data.timestamp,
        });
      })
      .catch(() => {
        setState({ status: "offline", isDemo: true, timestamp: new Date().toISOString() });
      });
  }, []);

  useEffect(() => {
    check();
    const interval = setInterval(check, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [check]);

  return state;
}
