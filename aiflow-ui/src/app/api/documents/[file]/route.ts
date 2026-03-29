import { NextResponse } from "next/server";
import { readJsonFile, updateJsonFile } from "@/lib/data-store";

interface Invoice {
  source_file: string;
  extraction_confidence: number;
  validation: { confidence_score: number; is_valid: boolean; errors: string[]; warnings: string[] };
  [key: string]: unknown;
}

// GET /api/documents/[file] — get single document by source_file
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ file: string }> }
) {
  const { file } = await params;
  const decoded = decodeURIComponent(file);
  const invoices = await readJsonFile<Invoice[]>("invoices.json");
  const doc = invoices.find((i) => i.source_file === decoded);

  if (!doc) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }
  return NextResponse.json(doc);
}

// PUT /api/documents/[file] — update document (verification, processing result)
export async function PUT(
  request: Request,
  { params }: { params: Promise<{ file: string }> }
) {
  const { file } = await params;
  const decoded = decodeURIComponent(file);
  const updates = await request.json();

  const updated = await updateJsonFile<Invoice[]>("invoices.json", (invoices) =>
    invoices.map((inv) =>
      inv.source_file === decoded ? { ...inv, ...updates } : inv
    )
  );

  const doc = updated.find((i) => i.source_file === decoded);
  if (!doc) {
    return NextResponse.json({ error: "Document not found" }, { status: 404 });
  }
  return NextResponse.json(doc);
}
