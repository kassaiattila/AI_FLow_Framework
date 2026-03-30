import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";
import type { EmailProcessingResult } from "@/lib/types";

// GET /api/emails — try FastAPI backend, fallback to local JSON
export async function GET() {
  // Try Python backend
  const backend = await fetchBackend<{ emails: unknown[]; total: number }>("/api/v1/emails");
  if (backend) {
    return NextResponse.json(backend.data);
  }

  // Fallback to local mock data
  const emails = await readJsonFile<EmailProcessingResult[]>("emails.json");
  return NextResponse.json({ emails, total: emails.length });
}
