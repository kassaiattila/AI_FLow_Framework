import { NextResponse } from "next/server";
import { cookies } from "next/headers";

// GET /api/auth/me — return current user from cookie token
export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("aiflow_token")?.value;

  if (!token) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  try {
    const payload = JSON.parse(Buffer.from(token, "base64url").toString());
    if (payload.exp && payload.exp < Date.now()) {
      return NextResponse.json({ error: "Token expired" }, { status: 401 });
    }
    return NextResponse.json({ user_id: payload.sub, role: payload.role });
  } catch {
    return NextResponse.json({ error: "Invalid token" }, { status: 401 });
  }
}
