import { AuthProvider } from "react-admin";

export const authProvider: AuthProvider = {
  async login({ username, password }) {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      throw new Error("Invalid credentials");
    }
    // API returns { token, user_id, role } — flat, not wrapped in "user"
    const data = await res.json();
    localStorage.setItem("user", JSON.stringify({ user_id: data.user_id, role: data.role }));
  },

  async logout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem("user");
  },

  async checkAuth() {
    const stored = localStorage.getItem("user");
    if (stored) {
      try {
        JSON.parse(stored);
        return;
      } catch {
        // corrupted — fall through to server check
      }
    }
    const res = await fetch("/api/auth/me");
    if (!res.ok) throw new Error("ra.auth.auth_check_error");
    // Cache the user info from the server response
    const data = await res.json();
    localStorage.setItem("user", JSON.stringify({ user_id: data.user_id, role: data.role }));
  },

  async checkError(error) {
    if (error?.status === 401 || error?.status === 403) {
      localStorage.removeItem("user");
      throw new Error("Session expired");
    }
  },

  async getIdentity() {
    const stored = localStorage.getItem("user");
    if (stored) {
      try {
        const user = JSON.parse(stored);
        if (user?.user_id) {
          return { id: user.user_id, fullName: user.user_id, avatar: undefined };
        }
      } catch {
        // corrupted localStorage — fall through
      }
    }
    // Fallback: fetch from server — API returns { user_id, role }
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("user", JSON.stringify({ user_id: data.user_id, role: data.role }));
      return { id: data.user_id, fullName: data.user_id };
    }
    return { id: "guest", fullName: "Guest" };
  },

  async getPermissions() {
    const stored = localStorage.getItem("user");
    if (stored) {
      try {
        const user = JSON.parse(stored);
        return user?.role || "viewer";
      } catch {
        return "viewer";
      }
    }
    return "viewer";
  },
};
