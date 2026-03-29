import { NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join, basename } from "path";
import { updateJsonFile } from "@/lib/data-store";

const UPLOAD_DIR = join(process.cwd(), "data", "uploads");

// Increase body size limit for large folder uploads (100MB)
export const maxDuration = 60;

interface Invoice {
  source_file: string;
  [key: string]: unknown;
}

// POST /api/documents/upload — receive actual PDF files via FormData
export async function POST(request: Request) {
  await mkdir(UPLOAD_DIR, { recursive: true });

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch (err) {
    return NextResponse.json(
      { error: "Feltoltes sikertelen: tul nagy fajlmeret vagy ervenytelen formatum", details: String(err) },
      { status: 413 }
    );
  }

  const files = formData.getAll("files") as File[];
  console.log(`[Upload API] Received ${files.length} files`);
  files.slice(0, 3).forEach((f, i) =>
    console.log(`  [${i}] name="${f.name}" type="${f.type}" size=${f.size}`)
  );

  if (files.length === 0) {
    return NextResponse.json({ error: "Nincs fajl a feltoltesben" }, { status: 400 });
  }

  const added: string[] = [];
  const errors: string[] = [];
  let skipped = 0;

  for (const file of files) {
    const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
    if (!isPdf) { skipped++; continue; }

    try {
      // webkitdirectory gives "folder/file.pdf" — extract just the filename
      const safeName = basename(file.name);
      const buffer = Buffer.from(await file.arrayBuffer());
      const filePath = join(UPLOAD_DIR, safeName);
      await writeFile(filePath, buffer);
      console.log(`[Upload API] Saved: ${safeName} (${buffer.length} bytes)`);

      const newDoc = {
        source_file: safeName,
        direction: "incoming",
        vendor: { name: safeName.replace(/\.pdf$/i, "").replace(/_/g, " "), address: "", tax_number: "", bank_account: "", bank_name: "" },
        buyer: { name: "", address: "", tax_number: "", bank_account: "", bank_name: "" },
        header: {
          invoice_number: "",
          invoice_date: new Date().toISOString().slice(0, 10),
          fulfillment_date: "", due_date: "", currency: "HUF",
          payment_method: "", invoice_type: "szamla", language: "hu",
        },
        line_items: [],
        totals: { net_total: 0, vat_total: 0, gross_total: 0 },
        validation: { is_valid: false, errors: [], warnings: [], confidence_score: 0 },
        parser_used: "pending",
        extraction_confidence: 0,
      };

      let isDuplicate = false;
      await updateJsonFile<Invoice[]>("invoices.json", (invoices) => {
        if (invoices.some((i) => i.source_file === safeName)) {
          isDuplicate = true;
          return invoices;
        }
        return [newDoc, ...invoices];
      });

      if (isDuplicate) {
        // File already in system — still save the PDF (update), but note it
        errors.push(`${safeName}: mar letezik (PDF felulirva)`);
      }
      added.push(safeName);
    } catch (err) {
      errors.push(`${file.name}: ${String(err).slice(0, 100)}`);
    }
  }

  console.log(`[Upload API] Result: ${added.length} uploaded, ${skipped} skipped, ${errors.length} errors`);
  return NextResponse.json({ uploaded: added.length, files: added, errors, skipped, totalReceived: files.length });
}
