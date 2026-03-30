import { NextResponse } from "next/server";
import { readFile, mkdir, readdir } from "fs/promises";
import { join, resolve } from "path";
import { execFile } from "child_process";
import { promisify } from "util";
import { readJsonFile, updateJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";
import type { ProcessDocResult } from "@/lib/types";

const execFileAsync = promisify(execFile);

// Project root (where skills/ directory lives)
const PROJECT_ROOT = resolve(process.cwd(), "..");
const PYTHON = join(PROJECT_ROOT, ".venv", "Scripts", "python.exe");

// POST /api/process-docs/generate — try FastAPI → subprocess → mock fallback
export async function POST(request: Request) {
  const body = await request.json();
  const { user_input } = body as { user_input: string };

  if (!user_input) {
    return NextResponse.json({ error: "user_input is required" }, { status: 400 });
  }

  // === Priority 1: FastAPI backend ===
  const backend = await fetchBackend<ProcessDocResult>(
    "/api/v1/workflows/process_documentation/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_data: { user_input } }),
    }
  );
  if (backend) {
    await updateJsonFile<ProcessDocResult[]>("process_docs.json", (docs) => [backend.data, ...docs]);
    return NextResponse.json({ ...backend.data, source: "backend" });
  }

  // === Priority 2: Subprocess (python -m skills.process_documentation) ===
  try {
    const outputDir = join(PROJECT_ROOT, "tmp_processdoc_output", Date.now().toString());
    await mkdir(outputDir, { recursive: true });

    console.log("[process-docs/generate] Running subprocess...");
    const { stdout, stderr } = await execFileAsync(
      PYTHON,
      ["-m", "skills.process_documentation", "--input", user_input, "--output", outputDir],
      {
        cwd: PROJECT_ROOT,
        timeout: 120_000, // 2 minutes
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
      }
    );

    if (stderr) {
      console.warn("[process-docs/generate] stderr:", stderr.slice(0, 500));
    }
    console.log("[process-docs/generate] stdout:", stdout.slice(0, 300));

    // Find the slug subdirectory created by export_all
    const entries = await readdir(outputDir, { withFileTypes: true });
    const subDir = entries.find((e) => e.isDirectory());

    if (subDir) {
      const exportDir = join(outputDir, subDir.name);

      // Read skill output files
      const mermaidCode = await readFile(join(exportDir, "diagram.mmd"), "utf-8");
      const extractionRaw = await readFile(join(exportDir, "extraction.json"), "utf-8");
      const extraction = JSON.parse(extractionRaw);

      // Read review (saved by updated export_all step)
      let review = {
        score: 0,
        is_acceptable: false,
        completeness_score: 0,
        logic_score: 0,
        actors_score: 0,
        decisions_score: 0,
        issues: [],
        suggestions: [],
        reasoning: "",
      };
      try {
        const reviewRaw = await readFile(join(exportDir, "review.json"), "utf-8");
        review = JSON.parse(reviewRaw);
      } catch {
        console.warn("[process-docs/generate] No review.json found, using defaults");
      }

      const doc: ProcessDocResult = {
        doc_id: `pd-${Date.now()}`,
        user_input,
        extraction,
        review,
        mermaid_code: mermaidCode,
        svg_url: null,
        drawio_url: null,
        created_at: new Date().toISOString(),
      };

      await updateJsonFile<ProcessDocResult[]>("process_docs.json", (docs) => [doc, ...docs]);

      console.log("[process-docs/generate] Subprocess success:", extraction.title);
      return NextResponse.json({ ...doc, source: "subprocess" });
    }

    console.error("[process-docs/generate] No output subdirectory found");
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    console.error("[process-docs/generate] Subprocess failed:", errMsg.slice(0, 500));
  }

  // === Priority 3: Mock fallback (labeled as demo) ===
  const docs = await readJsonFile<ProcessDocResult[]>("process_docs.json");
  if (docs.length === 0) {
    return NextResponse.json({ error: "Backend unavailable and no mock data" }, { status: 503 });
  }

  const template = docs[0];
  const newDoc: ProcessDocResult = {
    ...template,
    doc_id: `pd-${Date.now()}`,
    user_input,
    extraction: {
      ...template.extraction,
      title: user_input.slice(0, 60),
    },
    created_at: new Date().toISOString(),
  };

  await updateJsonFile<ProcessDocResult[]>("process_docs.json", (existing) => [newDoc, ...existing]);

  return NextResponse.json({ ...newDoc, source: "demo" });
}
