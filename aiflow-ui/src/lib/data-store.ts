// Server-side JSON file persistence for API routes.
// Reads/writes from the data/ directory at project root.
// On first access, seeds from public/data/ if data/ files don't exist.

import { readFile, writeFile, copyFile, access } from "fs/promises";
import { join } from "path";

const DATA_DIR = join(process.cwd(), "data");
const SEED_DIR = join(process.cwd(), "public", "data");

async function ensureFile(filename: string): Promise<string> {
  const dataPath = join(DATA_DIR, filename);
  try {
    await access(dataPath);
    return dataPath;
  } catch {
    // Seed from public/data/
    try {
      const seedPath = join(SEED_DIR, filename);
      await access(seedPath);
      await copyFile(seedPath, dataPath);
      return dataPath;
    } catch {
      // Create empty array file
      await writeFile(dataPath, "[]", "utf-8");
      return dataPath;
    }
  }
}

export async function readJsonFile<T>(filename: string): Promise<T> {
  const path = await ensureFile(filename);
  const raw = await readFile(path, "utf-8");
  return JSON.parse(raw);
}

export async function writeJsonFile<T>(filename: string, data: T): Promise<void> {
  const path = await ensureFile(filename);
  await writeFile(path, JSON.stringify(data, null, 2), "utf-8");
}

// Convenience: read, modify, write
export async function updateJsonFile<T>(
  filename: string,
  updater: (data: T) => T
): Promise<T> {
  const data = await readJsonFile<T>(filename);
  const updated = updater(data);
  await writeJsonFile(filename, updated);
  return updated;
}
