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
    // 401 on non-login paths = session expired → force logout
    if (response.status === 401 && !url.includes("/api/v1/auth/login")) {
      const { logout } = await import("./auth");
      logout();
      window.location.href = "/login";
      throw new ApiClientError(401, "Session expired — please log in again");
    }

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

  // 204 No Content — nothing to parse
  if (response.status === 204) {
    return undefined as unknown as T;
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
 * SSE stream via fetch (supports POST + auth headers).
 * EventSource only supports GET without headers, so we use fetch + ReadableStream.
 * Returns an AbortController to cancel the stream.
 */
export function streamApi(
  path: string,
  onMessage: (data: string) => void,
  onError?: (error: Event) => void,
  onDone?: () => void,
  options?: { method?: string; body?: unknown },
): { close: () => void } {
  const url = path.startsWith("/") ? path : `/${path}`;
  const controller = new AbortController();
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (options?.body) {
    headers["Content-Type"] = "application/json";
  }

  (async () => {
    try {
      const response = await fetch(url, {
        method: options?.method ?? "POST",
        headers,
        body: options?.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        if (onError) onError(new Event("error"));
        if (onDone) onDone();
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        if (onDone) onDone();
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") {
              if (onDone) onDone();
              return;
            }
            onMessage(data);
          }
        }
      }
      if (onDone) onDone();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        if (onError) onError(new Event("error"));
      }
      if (onDone) onDone();
    }
  })();

  return { close: () => controller.abort() };
}
