import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";
import type { ProcessDocResult } from "@/lib/types";

// POST /api/process-docs/generate — try FastAPI backend, fallback to mock
export async function POST(request: Request) {
  const body = await request.json();
  const { user_input } = body as { user_input: string };

  if (!user_input) {
    return NextResponse.json({ error: "user_input is required" }, { status: 400 });
  }

  // Try Python backend
  const backend = await fetchBackend<ProcessDocResult>(
    "/api/v1/workflows/process_documentation/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_data: { user_input } }),
    }
  );
  if (backend) {
    return NextResponse.json(backend.data);
  }

  // Fallback to mock data
  const docs = await readJsonFile<ProcessDocResult[]>("process_docs.json");
  if (docs.length > 0) {
    return NextResponse.json(docs[0]);
  }

  return NextResponse.json({ error: "Backend nem elerheto, mock data hianyzik" }, { status: 503 });
}
