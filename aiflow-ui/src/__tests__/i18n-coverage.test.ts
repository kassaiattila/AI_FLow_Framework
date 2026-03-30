import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const SRC_DIR = path.join(__dirname, "..");

function findFiles(dir: string, ext: string): string[] {
  const files: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && entry.name !== "node_modules" && entry.name !== "__tests__" && entry.name !== "ui") {
      files.push(...findFiles(full, ext));
    } else if (entry.name.endsWith(ext)) {
      files.push(full);
    }
  }
  return files;
}

describe("i18n coverage", () => {
  it("every page.tsx imports useI18n", () => {
    const pages = findFiles(path.join(SRC_DIR, "app"), ".tsx")
      .filter((f) => f.endsWith("page.tsx"))
      .filter((f) => !f.includes("invoice_processor")); // invoice has own patterns

    const missing: string[] = [];
    for (const page of pages) {
      const content = fs.readFileSync(page, "utf-8");
      if (!content.includes("useI18n")) {
        missing.push(path.relative(SRC_DIR, page));
      }
    }
    expect(missing).toEqual([]);
  });

  it("every skill component with visible text imports useI18n", () => {
    const componentDirs = ["email", "rag-chat", "process-docs", "cubix"];
    // Pure wrappers/logic files that don't render user-visible strings
    const EXEMPT = ["step-trace.tsx", "process-step-trace.tsx", "chat-messages.tsx"];
    const missing: string[] = [];

    for (const dir of componentDirs) {
      const dirPath = path.join(SRC_DIR, "components", dir);
      if (!fs.existsSync(dirPath)) continue;
      const files = findFiles(dirPath, ".tsx");
      for (const file of files) {
        const basename = path.basename(file);
        if (EXEMPT.includes(basename)) continue;
        const content = fs.readFileSync(file, "utf-8");
        if (!content.includes("useI18n")) {
          missing.push(path.relative(SRC_DIR, file));
        }
      }
    }
    expect(missing).toEqual([]);
  });

  it("all i18n keys have both hu and en translations", () => {
    const i18nPath = path.join(SRC_DIR, "lib", "i18n.ts");
    const content = fs.readFileSync(i18nPath, "utf-8");

    // Extract keys from hu section (between first { and matching })
    const huMatch = content.match(/hu:\s*\{([\s\S]*?)\n  \},\n\n\s*en:/);
    const enMatch = content.match(/en:\s*\{([\s\S]*?)\n  \},?\n\};/);

    if (!huMatch || !enMatch) {
      // Fallback: extract all "key": patterns
      expect(huMatch).toBeTruthy();
      return;
    }

    const extractKeys = (section: string): Set<string> => {
      const keys = new Set<string>();
      const regex = /"([^"]+)":/g;
      let match;
      while ((match = regex.exec(section)) !== null) {
        keys.add(match[1]);
      }
      return keys;
    };

    const huKeys = extractKeys(huMatch[1]);
    const enKeys = extractKeys(enMatch[1]);

    const missingInEn = [...huKeys].filter((k) => !enKeys.has(k));
    const missingInHu = [...enKeys].filter((k) => !huKeys.has(k));

    expect(missingInEn).toEqual([]);
    expect(missingInHu).toEqual([]);
  });

  it("no page files fetch from /data/ directly", () => {
    const pageFiles = findFiles(path.join(SRC_DIR, "app"), ".tsx")
      .filter((f) => f.endsWith("page.tsx"));

    const violations: string[] = [];
    for (const file of pageFiles) {
      const content = fs.readFileSync(file, "utf-8");
      if (content.includes('fetch("/data/') || content.includes("fetch('/data/")) {
        violations.push(path.relative(SRC_DIR, file));
      }
    }
    expect(violations).toEqual([]);
  });

  it("no hardcoded localhost URLs in components", () => {
    const allFiles = [
      ...findFiles(path.join(SRC_DIR, "app"), ".tsx"),
      ...findFiles(path.join(SRC_DIR, "components"), ".tsx"),
    ];

    const violations: string[] = [];
    for (const file of allFiles) {
      const content = fs.readFileSync(file, "utf-8");
      if (content.includes("localhost:3000") || content.includes("localhost:8000")) {
        violations.push(path.relative(SRC_DIR, file));
      }
    }
    expect(violations).toEqual([]);
  });

  it("no useState with localStorage/sessionStorage initializer", () => {
    const allFiles = [
      ...findFiles(path.join(SRC_DIR, "app"), ".tsx"),
      ...findFiles(path.join(SRC_DIR, "components"), ".tsx"),
    ];

    const violations: string[] = [];
    for (const file of allFiles) {
      const content = fs.readFileSync(file, "utf-8");
      // Match useState(() => { ... localStorage ... }) or useState(localStorage.getItem(...))
      if (/useState\([^)]*localStorage/.test(content) || /useState\([^)]*sessionStorage/.test(content)) {
        violations.push(path.relative(SRC_DIR, file));
      }
    }
    expect(violations).toEqual([]);
  });
});
