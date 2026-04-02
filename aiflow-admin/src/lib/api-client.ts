/**
 * AIFlow API Client — typed fetch wrapper replacing React Admin dataProvider.
 * All API calls go through Vite proxy (/api → FastAPI :8101).
 */

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

export class ApiClientError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

/** Get JWT token from localStorage */
function getToken(): string | null {
  return localStorage.getItem("aiflow_token");
}

/** Build headers with optional auth token */
function buildHeaders(extra?: Record<string, string>): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extra,
  };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Core fetch wrapper. All API calls go through this.
 * Returns typed JSON response or throws ApiClientError.
 */
export async function fetchApi<T>(
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH",
  path: string,
  body?: unknown,
  options?: { signal?: AbortSignal; rawResponse?: boolean },
): Promise<T> {
  const url = path.startsWith("/") ? path : `/${path}`;
  const init: RequestInit = {
    method,
    headers: buildHeaders(),
    signal: options?.signal,
  };

  if (body !== undefined && method !== "GET") {
    init.body = JSON.stringify(body);
  }

  const response = await fetch(url, init);

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new ApiClientError(
      response.status,
      `API error ${response.status}: ${response.statusText}`,
      detail,
    );
  }

  if (options?.rawResponse) {
    return response as unknown as T;
  }

  const contentType = response.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return response.json() as Promise<T>;
  }

  return response.text() as unknown as T;
}

/**
 * Upload file(s) via FormData. Does NOT set Content-Type header (browser sets boundary).
 */
export async function uploadFile<T>(
  path: string,
  formData: FormData,
  options?: { signal?: AbortSignal },
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(path, {
    method: "POST",
    headers,
    body: formData,
    signal: options?.signal,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => response.text());
    throw new ApiClientError(response.status, `Upload error ${response.status}`, detail);
  }

  return response.json() as Promise<T>;
}

/**
 * SSE stream for real-time updates (document processing, etc.)
 * Returns an EventSource-like async iterator.
 */
export function streamApi(
  path: string,
  onMessage: (data: string) => void,
  onError?: (error: Event) => void,
  onDone?: () => void,
): EventSource {
  const url = path.startsWith("/") ? path : `/${path}`;
  const source = new EventSource(url);

  source.onmessage = (event) => {
    onMessage(event.data);
  };

  source.onerror = (event) => {
    if (onError) onError(event);
    source.close();
    if (onDone) onDone();
  };

  source.addEventListener("done", () => {
    source.close();
    if (onDone) onDone();
  });

  return source;
}
