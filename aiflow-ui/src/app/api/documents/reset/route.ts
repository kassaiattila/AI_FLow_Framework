import { NextResponse } from "next/server";
import { writeFile, rm, mkdir } from "fs/promises";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "data");
const IMAGES_DIR = join(process.cwd(), "public", "images", "documents");

// POST /api/documents/reset — clear all data and start fresh
export async function POST() {
  // Reset invoices.json to empty
  await writeFile(join(DATA_DIR, "invoices.json"), "[]", "utf-8");
  // Reset runs.json to empty
  await writeFile(join(DATA_DIR, "runs.json"), "[]", "utf-8");

  // Clean uploads
  try { await rm(join(DATA_DIR, "uploads"), { recursive: true, force: true }); } catch { /* ok */ }
  await mkdir(join(DATA_DIR, "uploads"), { recursive: true });

  // Clean processed
  try { await rm(join(DATA_DIR, "processed"), { recursive: true, force: true }); } catch { /* ok */ }

  // Clean rendered images
  try { await rm(IMAGES_DIR, { recursive: true, force: true }); } catch { /* ok */ }
  await mkdir(IMAGES_DIR, { recursive: true });

  return NextResponse.json({ status: "reset", message: "All data cleared" });
}
