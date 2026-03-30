import { NextResponse } from "next/server";
import { readFile, mkdir, access } from "fs/promises";
import { join, resolve } from "path";
import { execFile } from "child_process";
import { promisify } from "util";
import { fetchBackend } from "@/lib/backend";

const execFileAsync = promisify(execFile);

const PROJECT_ROOT = resolve(process.cwd(), "..");
const PYTHON = join(PROJECT_ROOT, ".venv", "Scripts", "python.exe");
const UPLOAD_DIR = join(process.cwd(), "data", "uploads", "emails");

// POST /api/emails/process — classify an uploaded email file
// Body: { file: string }
// Priority: 1. FastAPI backend → 2. subprocess → 3. error
export async function POST(request: Request) {
  const body = await request.json();
  const { file } = body as { file: string };

  if (!file) {
    return NextResponse.json({ error: "file is required" }, { status: 400 });
  }

  const filePath = join(UPLOAD_DIR, file);
  try {
    await access(filePath);
  } catch {
    return NextResponse.json({ error: "File not found" }, { status: 404 });
  }

  // === Priority 1: FastAPI backend ===
  const backend = await fetchBackend<Record<string, unknown>>(
    "/api/v1/emails/classify",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: filePath }),
    }
  );
  if (backend) {
    return NextResponse.json({ ...backend.data, source: "backend" });
  }

  // === Priority 2: Subprocess ===
  try {
    const outputDir = join(PROJECT_ROOT, "tmp_email_output", Date.now().toString());
    await mkdir(outputDir, { recursive: true });

    console.log(`[emails/process] Running subprocess for: ${file}`);
    const { stdout, stderr } = await execFileAsync(
      PYTHON,
      ["-m", "skills.email_intent_processor", "classify", "--input", filePath, "--output", outputDir],
      {
        cwd: PROJECT_ROOT,
        timeout: 120_000,
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      }
    );

    if (stderr) {
      console.warn("[emails/process] stderr:", stderr.slice(0, 500));
    }
    console.log("[emails/process] stdout:", stdout.slice(0, 300));

    // Read result.json from output
    const resultPath = join(outputDir, "result.json");
    try {
      const raw = await readFile(resultPath, "utf-8");
      const result = JSON.parse(raw);
      return NextResponse.json({ ...result, source: "subprocess" });
    } catch {
      // No result.json — parse stdout for basic info
      console.warn("[emails/process] No result.json, returning stdout summary");
      return NextResponse.json({
        file,
        stdout: stdout.slice(0, 1000),
        source: "subprocess",
      });
    }
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    console.error("[emails/process] Subprocess failed:", errMsg.slice(0, 500));
    return NextResponse.json(
      { error: "Processing failed", details: errMsg.slice(0, 200), source: "error" },
      { status: 500 }
    );
  }
}
