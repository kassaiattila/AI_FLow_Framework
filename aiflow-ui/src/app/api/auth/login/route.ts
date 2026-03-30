import { NextResponse } from "next/server";
import { fetchBackend } from "@/lib/backend";

// Hardcoded fallback users for when FastAPI is unavailable
const FALLBACK_USERS: Record<string, { password: string; role: string }> = {
  admin: { password: "admin", role: "admin" },
  operator: { password: "operator", role: "operator" },
  viewer: { password: "viewer", role: "viewer" },
};

// POST /api/auth/login — proxy to FastAPI or use fallback
export async function POST(request: Request) {
  const body = await request.json();
  const { username, password } = body as { username: string; password: string };

  if (!username || !password) {
    return NextResponse.json({ error: "Username and password required" }, { status: 400 });
  }

  // Try FastAPI backend
  const backend = await fetchBackend<{ token: string; user_id: string; role: string }>(
    "/api/v1/auth/login",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }
  );
  if (backend) {
    const res = NextResponse.json(backend.data);
    res.cookies.set("aiflow_token", backend.data.token, {
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      maxAge: 3600,
    });
    return res;
  }

  // Fallback: local validation
  const user = FALLBACK_USERS[username];
  if (!user || user.password !== password) {
    return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  }

  // Create a simple token (not cryptographically secure — dev only)
  const token = Buffer.from(JSON.stringify({ sub: username, role: user.role, exp: Date.now() + 3600000 })).toString("base64url");

  const res = NextResponse.json({ token, user_id: username, role: user.role });
  res.cookies.set("aiflow_token", token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 3600,
  });
  return res;
}
