import { NextResponse } from "next/server";
import { readFile, readdir } from "fs/promises";
import { join, resolve } from "path";
import { readJsonFile } from "@/lib/data-store";
import type { CubixCourseResult } from "@/lib/types";

const PROJECT_ROOT = resolve(process.cwd(), "..");
const CUBIX_OUTPUT_DIR = join(PROJECT_ROOT, "skills", "cubix_course_capture", "output");

// GET /api/cubix — try filesystem scan first, fallback to mock
export async function GET() {
  // === Priority 1: Scan real pipeline output ===
  try {
    const entries = await readdir(CUBIX_OUTPUT_DIR, { withFileTypes: true });
    const courseDirs = entries.filter((e) => e.isDirectory());

    const realCourses: CubixCourseResult[] = [];
    for (const dir of courseDirs) {
      try {
        const statePath = join(CUBIX_OUTPUT_DIR, dir.name, "pipeline_state.json");
        const raw = await readFile(statePath, "utf-8");
        const state = JSON.parse(raw);
        // Build a CubixCourseResult from real pipeline state
        realCourses.push(state as CubixCourseResult);
      } catch {
        // No pipeline_state.json in this dir, skip
      }
    }

    if (realCourses.length > 0) {
      return NextResponse.json({
        courses: realCourses,
        total: realCourses.length,
        source: "filesystem",
      });
    }
  } catch {
    // Output dir doesn't exist — fall through to mock
  }

  // === Priority 2: Mock data ===
  const courses = await readJsonFile<CubixCourseResult[]>("cubix_courses.json");
  return NextResponse.json({ courses, total: courses.length, source: "demo" });
}
