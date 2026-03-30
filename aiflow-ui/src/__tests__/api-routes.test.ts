import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const API_DIR = path.join(__dirname, "../app/api");

describe("API route structure", () => {
  const expectedRoutes = [
    "auth/login/route.ts",
    "auth/logout/route.ts",
    "auth/me/route.ts",
    "cubix/route.ts",
    "documents/route.ts",
    "emails/route.ts",
    "process-docs/route.ts",
    "process-docs/generate/route.ts",
    "rag/conversations/route.ts",
    "rag/query/route.ts",
    "rag/stream/route.ts",
    "runs/route.ts",
    "runs/stream/route.ts",
    "kroki/route.ts",
  ];

  for (const route of expectedRoutes) {
    it(`/api/${route} exists`, () => {
      const filePath = path.join(API_DIR, route);
      expect(fs.existsSync(filePath)).toBe(true);
    });
  }
});

describe("API route code quality", () => {
  it("no hardcoded localhost URLs in API routes", () => {
    const violations: string[] = [];
    function checkDir(dir: string) {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          checkDir(full);
        } else if (entry.name === "route.ts") {
          const content = fs.readFileSync(full, "utf-8");
          if (content.includes("localhost:3000") || content.includes("127.0.0.1:3000")) {
            violations.push(path.relative(API_DIR, full));
          }
        }
      }
    }
    checkDir(API_DIR);
    expect(violations).toEqual([]);
  });

  it("all API routes export at least one HTTP method", () => {
    const missing: string[] = [];
    function checkDir(dir: string) {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          checkDir(full);
        } else if (entry.name === "route.ts") {
          const content = fs.readFileSync(full, "utf-8");
          const hasMethod = /export\s+(async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)/m.test(content);
          if (!hasMethod) {
            missing.push(path.relative(API_DIR, full));
          }
        }
      }
    }
    checkDir(API_DIR);
    expect(missing).toEqual([]);
  });
});
