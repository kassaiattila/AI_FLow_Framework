/**
 * AIFlow Auth — JWT token management replacing React Admin authProvider.
 * Handles login, logout, token refresh, session monitoring, and auth state.
 */

import { fetchApi, ApiClientError } from "./api-client";

const TOKEN_KEY = "aiflow_token";
const USER_KEY = "aiflow_user";

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface LoginResponse {
  token: string;
  user_id: string;
  role: string;
  team_id: string | null;
  expires_in: number;
}

interface MeResponse {
  user_id: string;
  role: string;
  team_id: string | null;
}

interface RefreshResponse {
  token: string;
  expires_in: number;
}

/** Login with email/password, store JWT token */
export async function login(credentials: LoginCredentials): Promise<AuthUser> {
  const data = await fetchApi<LoginResponse>(
    "POST",
    "/api/v1/auth/login",
    credentials,
  );
  localStorage.setItem(TOKEN_KEY, data.token);

  // Fetch user info
  const me = await fetchApi<MeResponse>("GET", "/api/v1/auth/me");
  const user: AuthUser = {
    id: me.user_id,
    email: credentials.username,
    name: credentials.username.split("@")[0],
    role: me.role,
  };
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

/** Logout — clear token and user data */
export function logout(): void {
  stopSessionMonitor();
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Get stored token */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/** Check if user is authenticated (has token) */
export function isAuthenticated(): boolean {
  return !!getToken();
}

/** Get stored user info */
export function getUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

/** Refresh token via backend */
export async function refreshToken(): Promise<boolean> {
  const currentToken = getToken();
  if (!currentToken) return false;

  try {
    const data = await fetchApi<RefreshResponse>(
      "POST",
      "/api/v1/auth/refresh",
      {
        token: currentToken,
      },
    );
    localStorage.setItem(TOKEN_KEY, data.token);
    return true;
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 401) {
      logout();
      return false;
    }
    throw error;
  }
}

/** Get token expiration timestamp (ms) or null if no/invalid token */
export function getTokenExpiry(): number | null {
  const token = getToken();
  if (!token) return null;

  try {
    // Standard JWT: header.payload.signature (3 parts)
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** Check if token is about to expire (within 5 minutes) */
export function isTokenExpiring(): boolean {
  const exp = getTokenExpiry();
  if (!exp) return true;
  const fiveMinutes = 5 * 60 * 1000;
  return Date.now() > exp - fiveMinutes;
}

// ---------------------------------------------------------------------------
// Session monitor — periodic token expiry check (60s interval)
// ---------------------------------------------------------------------------

let _sessionCheckInterval: ReturnType<typeof setInterval> | null = null;

export type SessionCallback = () => void;

/**
 * Start monitoring token expiry.
 * - onWarning: called when token expires within 5 minutes
 * - onExpired: called when token has expired (auto-logout triggered)
 */
export function startSessionMonitor(
  onWarning: SessionCallback,
  onExpired: SessionCallback,
): void {
  stopSessionMonitor();
  _sessionCheckInterval = setInterval(() => {
    const exp = getTokenExpiry();
    if (!exp) {
      logout();
      onExpired();
      return;
    }
    const now = Date.now();
    if (now >= exp) {
      logout();
      onExpired();
    } else if (now > exp - 5 * 60 * 1000) {
      onWarning();
    }
  }, 60_000);
}

/** Stop the session monitor interval. */
export function stopSessionMonitor(): void {
  if (_sessionCheckInterval !== null) {
    clearInterval(_sessionCheckInterval);
    _sessionCheckInterval = null;
  }
}
