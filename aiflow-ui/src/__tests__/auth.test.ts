import { describe, it, expect, beforeEach } from "vitest";
import { canEdit, isAdmin } from "@/hooks/use-auth";

describe("RBAC helper functions", () => {
  it("canEdit returns true for admin", () => {
    expect(canEdit("admin")).toBe(true);
  });

  it("canEdit returns true for operator", () => {
    expect(canEdit("operator")).toBe(true);
  });

  it("canEdit returns false for viewer", () => {
    expect(canEdit("viewer")).toBe(false);
  });

  it("isAdmin returns true only for admin", () => {
    expect(isAdmin("admin")).toBe(true);
    expect(isAdmin("operator")).toBe(false);
    expect(isAdmin("viewer")).toBe(false);
  });
});

describe("Auth token parsing", () => {
  it("creates valid base64url token", () => {
    const payload = { sub: "admin", role: "admin", exp: Date.now() + 3600000 };
    const token = Buffer.from(JSON.stringify(payload)).toString("base64url");
    const decoded = JSON.parse(Buffer.from(token, "base64url").toString());
    expect(decoded.sub).toBe("admin");
    expect(decoded.role).toBe("admin");
    expect(decoded.exp).toBeGreaterThan(Date.now());
  });

  it("expired token is detectable", () => {
    const payload = { sub: "admin", role: "admin", exp: Date.now() - 1000 };
    const token = Buffer.from(JSON.stringify(payload)).toString("base64url");
    const decoded = JSON.parse(Buffer.from(token, "base64url").toString());
    expect(decoded.exp).toBeLessThan(Date.now());
  });
});

describe("Session storage management", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("stores and retrieves user data", () => {
    const user = { user_id: "admin", role: "admin" };
    sessionStorage.setItem("aiflow_user", JSON.stringify(user));
    const stored = JSON.parse(sessionStorage.getItem("aiflow_user")!);
    expect(stored.user_id).toBe("admin");
    expect(stored.role).toBe("admin");
  });

  it("clear removes user data", () => {
    sessionStorage.setItem("aiflow_user", JSON.stringify({ user_id: "admin" }));
    sessionStorage.removeItem("aiflow_user");
    expect(sessionStorage.getItem("aiflow_user")).toBeNull();
  });
});
