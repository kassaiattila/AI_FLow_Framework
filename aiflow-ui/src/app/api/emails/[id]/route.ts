import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import type { EmailProcessingResult } from "@/lib/types";

// GET /api/emails/[id] — get single email by email_id
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const emails = await readJsonFile<EmailProcessingResult[]>("emails.json");
  const email = emails.find((e) => e.email_id === id);

  if (!email) {
    return NextResponse.json({ error: "Email not found" }, { status: 404 });
  }

  return NextResponse.json(email);
}
