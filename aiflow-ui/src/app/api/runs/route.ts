import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";
import { fetchBackend } from "@/lib/backend";

// GET /api/runs — try FastAPI backend, fallback to local JSON
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const skill = searchParams.get("skill");

  // Try Python backend
  const query = skill ? `?skill=${encodeURIComponent(skill)}` : "";
  const backend = await fetchBackend<{ runs: unknown[]; total: number }>(
    `/api/v1/runs${query}`
  );
  if (backend) {
    return NextResponse.json(backend.data);
  }

  // Fallback to local JSON
  let runs = await readJsonFile<unknown[]>("runs.json");

  if (skill) {
    runs = runs.filter((r: any) => r.skill_name === skill);
  }

  return NextResponse.json({ runs, total: runs.length });
}
