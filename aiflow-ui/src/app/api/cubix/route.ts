import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import type { CubixCourseResult } from "@/lib/types";

// GET /api/cubix — list all course capture results
export async function GET() {
  const courses = await readJsonFile<CubixCourseResult[]>("cubix_courses.json");
  return NextResponse.json({ courses, total: courses.length });
}
