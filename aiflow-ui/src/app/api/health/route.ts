import { NextResponse } from "next/server";
import { fetchBackend } from "@/lib/backend";

export interface HealthStatus {
  status: "connected" | "offline";
  timestamp: string;
}

// GET /api/health — check if Python FastAPI backend is reachable
export async function GET() {
  const result = await fetchBackend<{ status: string }>("/health");

  const health: HealthStatus = {
    status: result ? "connected" : "offline",
    timestamp: new Date().toISOString(),
  };

  return NextResponse.json(health);
}
