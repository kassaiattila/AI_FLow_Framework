import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";
import type { ProcessDocResult } from "@/lib/types";

// GET /api/process-docs — try FastAPI backend, fallback to local JSON
export async function GET() {
  const backend = await fetchBackend<{ documents: ProcessDocResult[]; total: number }>(
    "/api/v1/process-docs"
  );
  if (backend) {
    return NextResponse.json({ ...backend.data, source: "backend" });
  }

  const docs = await readJsonFile<ProcessDocResult[]>("process_docs.json");
  return NextResponse.json({ documents: docs, total: docs.length, source: "demo" });
}
