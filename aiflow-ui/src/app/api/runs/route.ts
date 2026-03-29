import { NextResponse } from "next/server";
import { readJsonFile } from "@/lib/data-store";

// GET /api/runs — list all runs, optionally filtered by skill
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const skill = searchParams.get("skill");

  let runs = await readJsonFile<unknown[]>("runs.json");

  if (skill) {
    runs = runs.filter((r: any) => r.skill_name === skill);
  }

  return NextResponse.json({ runs, total: runs.length });
}
