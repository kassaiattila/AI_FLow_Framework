import { NextResponse } from "next/server";

// POST /api/auth/logout — clear auth cookie and redirect to login
export async function POST(request: Request) {
  const url = new URL("/login", request.url);
  const res = NextResponse.redirect(url);
  res.cookies.delete("aiflow_token");
  return res;
}

// GET also works for simple link-based logout
export async function GET(request: Request) {
  const url = new URL("/login", request.url);
  const res = NextResponse.redirect(url);
  res.cookies.delete("aiflow_token");
  return res;
}
