import { NextResponse } from "next/server";
import { readJsonFile, updateJsonFile } from "@/lib/data-store";

// GET /api/documents — list all documents
export async function GET() {
  const invoices = await readJsonFile<unknown[]>("invoices.json");
  return NextResponse.json({ documents: invoices, total: invoices.length });
}

// POST /api/documents — add new document(s) from upload
export async function POST(request: Request) {
  const body = await request.json();
  const newDocs: unknown[] = body.documents || [];

  if (newDocs.length === 0) {
    return NextResponse.json({ error: "No documents provided" }, { status: 400 });
  }

  const updated = await updateJsonFile<unknown[]>("invoices.json", (existing) => [
    ...newDocs,
    ...existing,
  ]);

  return NextResponse.json({ total: updated.length, added: newDocs.length });
}
