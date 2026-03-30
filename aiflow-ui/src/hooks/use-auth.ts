"use client";

import { useState, useEffect } from "react";

interface AuthUser {
  user_id: string;
  role: "admin" | "operator" | "viewer";
}

export function useAuth(): { user: AuthUser | null; loading: boolean } {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Try sessionStorage first (set on login)
    const cached = sessionStorage.getItem("aiflow_user");
    if (cached) {
      try {
        setUser(JSON.parse(cached));
        setLoading(false);
        return;
      } catch { /* fall through */ }
    }

    // Fetch from API
    fetch("/api/auth/me")
      .then((r) => {
        if (!r.ok) throw new Error("not authenticated");
        return r.json();
      })
      .then((data) => {
        const u = { user_id: data.user_id, role: data.role };
        sessionStorage.setItem("aiflow_user", JSON.stringify(u));
        setUser(u);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  return { user, loading };
}

export function canEdit(role: string): boolean {
  return role === "admin" || role === "operator";
}

export function isAdmin(role: string): boolean {
  return role === "admin";
}
