import { NextResponse } from "next/server";
import { writeFile, mkdir } from "fs/promises";
import { join, basename } from "path";

const UPLOAD_DIR = join(process.cwd(), "data", "uploads", "emails");

const ACCEPTED_EXTENSIONS = [".eml", ".msg", ".txt"];

// POST /api/emails/upload — receive email files via FormData
export async function POST(request: Request) {
  await mkdir(UPLOAD_DIR, { recursive: true });

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch (err) {
    return NextResponse.json(
      { error: "Upload failed: invalid format", details: String(err) },
      { status: 413 }
    );
  }

  const files = formData.getAll("files") as File[];
  if (files.length === 0) {
    return NextResponse.json({ error: "No files" }, { status: 400 });
  }

  const added: string[] = [];
  const errors: string[] = [];

  for (const file of files) {
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    if (!ACCEPTED_EXTENSIONS.includes(ext)) continue;

    try {
      const safeName = basename(file.name);
      const buffer = Buffer.from(await file.arrayBuffer());
      await writeFile(join(UPLOAD_DIR, safeName), buffer);
      added.push(safeName);
      console.log(`[emails/upload] Saved: ${safeName} (${buffer.length} bytes)`);
    } catch (err) {
      errors.push(`${file.name}: ${String(err).slice(0, 100)}`);
    }
  }

  return NextResponse.json({ uploaded: added.length, files: added, errors });
}
