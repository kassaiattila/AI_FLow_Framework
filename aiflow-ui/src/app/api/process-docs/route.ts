import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import type { ProcessDocResult } from "@/lib/types";

// GET /api/process-docs — list all generated documents
export async function GET() {
  const docs = await readJsonFile<ProcessDocResult[]>("process_docs.json");
  return NextResponse.json({ documents: docs, total: docs.length });
}
