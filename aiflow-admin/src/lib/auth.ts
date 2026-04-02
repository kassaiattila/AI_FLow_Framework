/**
 * AIFlow Auth — JWT token management replacing React Admin authProvider.
 * Handles login, logout, token refresh, and auth state.
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

/** Login with email/password, store JWT token */
export async function login(credentials: LoginCredentials): Promise<AuthUser> {
  const data = await fetchApi<LoginResponse>("POST", "/api/v1/auth/login", credentials);
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

/** Refresh token */
export async function refreshToken(): Promise<boolean> {
  try {
    const data = await fetchApi<LoginResponse>("POST", "/api/v1/auth/refresh");
    localStorage.setItem(TOKEN_KEY, data.access_token);
    return true;
  } catch (error) {
    if (error instanceof ApiClientError && error.status === 401) {
      logout();
      return false;
    }
    throw error;
  }
}

/** Check if token is about to expire (within 5 minutes) */
export function isTokenExpiring(): boolean {
  const token = getToken();
  if (!token) return true;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const exp = payload.exp * 1000;
    const fiveMinutes = 5 * 60 * 1000;
    return Date.now() > exp - fiveMinutes;
  } catch {
    return true;
  }
}
