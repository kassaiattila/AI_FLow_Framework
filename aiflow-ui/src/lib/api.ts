// AIFlow API client - communicates with FastAPI backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Health
export const getHealth = () => fetchAPI<{ status: string }>("/health");

// Workflows
export const getWorkflows = () => fetchAPI<{ workflows: any[] }>("/api/v1/workflows");

// Runs (will be implemented in FastAPI)
export const getRuns = (skill?: string) =>
  fetchAPI<{ runs: any[] }>(`/api/v1/runs${skill ? `?skill=${skill}` : ""}`);

export const getRunDetail = (id: string) =>
  fetchAPI<any>(`/api/v1/runs/${id}`);

// Costs
export const getCostSummary = () =>
  fetchAPI<any>("/api/v1/costs/summary");

// Invoice data (local file for now)
export async function loadInvoiceData(): Promise<any[]> {
  // In development: load from local JSON file
  // In production: load from API
  try {
    const res = await fetch("/api/invoices");
    return res.json();
  } catch {
    return [];
  }
}
