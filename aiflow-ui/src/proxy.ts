import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that don't require authentication
const PUBLIC_ROUTES = [
  "/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/api/documents/upload",
  "/api/documents/process",
  "/api/emails/upload",
  "/api/emails/process",
];

// Routes that require admin role
const ADMIN_ROUTES = ["/api/documents/reset"];

// Routes that require at least operator role (operator or admin)
const OPERATOR_ROUTES = [
  "/api/documents/upload",
  "/api/documents/process",
];

const ROLE_HIERARCHY: Record<string, number> = {
  viewer: 1,
  operator: 2,
  admin: 3,
};

function parseToken(token: string): { sub: string; role: string; exp: number } | null {
  try {
    return JSON.parse(Buffer.from(token, "base64url").toString());
  } catch {
    return null;
  }
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes and general API routes
  if (
    PUBLIC_ROUTES.some((r) => pathname.startsWith(r)) ||
    (pathname.startsWith("/api/") &&
      !pathname.startsWith("/api/auth/me") &&
      !ADMIN_ROUTES.some((r) => pathname.startsWith(r)) &&
      !OPERATOR_ROUTES.some((r) => pathname.startsWith(r)))
  ) {
    return NextResponse.next();
  }

  // Check for auth cookie
  const token = request.cookies.get("aiflow_token")?.value;
  if (!token) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const payload = parseToken(token);
  if (!payload || (payload.exp && payload.exp < Date.now())) {
    const res = pathname.startsWith("/api/")
      ? NextResponse.json({ error: "Token expired" }, { status: 401 })
      : NextResponse.redirect(new URL("/login", request.url));
    res.cookies.delete("aiflow_token");
    return res;
  }

  const userLevel = ROLE_HIERARCHY[payload.role] || 0;

  // Check admin-only routes
  if (ADMIN_ROUTES.some((r) => pathname.startsWith(r)) && userLevel < 3) {
    return NextResponse.json({ error: "Admin role required" }, { status: 403 });
  }

  // Check operator-only routes
  if (OPERATOR_ROUTES.some((r) => pathname.startsWith(r)) && userLevel < 2) {
    return NextResponse.json({ error: "Operator role required" }, { status: 403 });
  }

  // Pass role to the client via header
  const res = NextResponse.next();
  res.headers.set("x-user-role", payload.role);
  res.headers.set("x-user-id", payload.sub);
  return res;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|images/).*)",
  ],
};
