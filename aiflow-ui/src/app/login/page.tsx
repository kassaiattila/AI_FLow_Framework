"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Clear stale session data on login page load
  useEffect(() => {
    sessionStorage.removeItem("aiflow_user");
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.error || "Bejelentkezes sikertelen");
        return;
      }

      const data = await res.json();
      // Store user info in sessionStorage for client-side use
      sessionStorage.setItem("aiflow_user", JSON.stringify({ user_id: data.user_id, role: data.role }));
      router.push("/");
    } catch {
      setError("Szerverhiba");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-muted/30">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">AIFlow</CardTitle>
          <p className="text-sm text-muted-foreground">Bejelentkezes</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-sm font-medium" htmlFor="username">
                Felhasznalonev
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1 bg-background"
                placeholder="admin"
                autoFocus
              />
            </div>
            <div>
              <label className="text-sm font-medium" htmlFor="password">
                Jelszo
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1 bg-background"
                placeholder="********"
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 text-center">{error}</p>
            )}

            <Button type="submit" className="w-full" disabled={loading || !username || !password}>
              {loading ? "Bejelentkezes..." : "Bejelentkezes"}
            </Button>

            {process.env.NODE_ENV === "development" && (
              <p className="text-xs text-muted-foreground text-center">
                Dev: admin/admin, operator/operator, viewer/viewer
              </p>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
