import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";
import type { EmailProcessingResult } from "@/lib/types";

// GET /api/emails/[id] — try FastAPI backend, fallback to local JSON
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const backend = await fetchBackend<EmailProcessingResult>(
    `/api/v1/emails/${encodeURIComponent(id)}`
  );
  if (backend) {
    return NextResponse.json({ ...backend.data, source: "backend" });
  }

  const emails = await readJsonFile<EmailProcessingResult[]>("emails.json");
  const email = emails.find((e) => e.email_id === id);

  if (!email) {
    return NextResponse.json({ error: "Email not found" }, { status: 404 });
  }

  return NextResponse.json({ ...email, source: "demo" });
}
