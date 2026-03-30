// FastAPI backend proxy helper.
// Tries the Python backend first, falls back to local JSON data.

const BACKEND_URL = process.env.AIFLOW_BACKEND_URL || "http://localhost:8000";

export async function fetchBackend<T>(
  path: string,
  options?: RequestInit
): Promise<{ data: T; source: "backend" | "fallback" } | null> {
  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      ...options,
      signal: AbortSignal.timeout(3000),
    });
    if (res.ok) {
      const data = await res.json();
      return { data, source: "backend" };
    }
  } catch {
    // Backend unavailable — caller should use fallback
  }
  return null;
}
