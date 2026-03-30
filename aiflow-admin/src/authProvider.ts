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
    const data = await res.json();
    localStorage.setItem("user", JSON.stringify(data.user));
  },

  async logout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem("user");
  },

  async checkAuth() {
    const res = await fetch("/api/auth/me");
    if (!res.ok) throw new Error("Not authenticated");
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
      const user = JSON.parse(stored);
      return { id: user.user_id, fullName: user.user_id, avatar: undefined };
    }
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      return { id: data.user.user_id, fullName: data.user.user_id };
    }
    return { id: "guest", fullName: "Guest" };
  },

  async getPermissions() {
    const stored = localStorage.getItem("user");
    if (stored) {
      const user = JSON.parse(stored);
      return user.role || "viewer";
    }
    return "viewer";
  },
};
