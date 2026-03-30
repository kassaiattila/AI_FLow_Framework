import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import type { ProcessDocResult } from "@/lib/types";

// GET /api/process-docs/[id] — get single document
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const docs = await readJsonFile<ProcessDocResult[]>("process_docs.json");
  const doc = docs.find((d) => d.doc_id === id);

  if (!doc) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }

  return NextResponse.json(doc);
}
