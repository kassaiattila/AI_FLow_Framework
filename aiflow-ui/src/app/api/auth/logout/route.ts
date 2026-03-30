import { NextResponse } from "next/server";

// POST /api/auth/logout — clear auth cookie and redirect to login
export async function POST() {
  const res = NextResponse.redirect(new URL("/login", "http://localhost:3000"));
  res.cookies.delete("aiflow_token");
  return res;
}

// GET also works for simple link-based logout
export async function GET() {
  const res = NextResponse.redirect(new URL("/login", "http://localhost:3000"));
  res.cookies.delete("aiflow_token");
  return res;
}
