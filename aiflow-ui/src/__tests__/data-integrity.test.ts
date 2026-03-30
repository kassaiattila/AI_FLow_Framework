import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const DATA_DIR = path.join(__dirname, "../../public/data");

describe("Mock data file integrity", () => {
  const requiredFiles = [
    "emails.json",
    "invoices.json",
    "process_docs.json",
    "rag_conversations.json",
    "runs.json",
    "cubix_courses.json",
  ];

  for (const file of requiredFiles) {
    it(`${file} exists and is valid JSON`, () => {
      const filePath = path.join(DATA_DIR, file);
      expect(fs.existsSync(filePath)).toBe(true);
      const content = fs.readFileSync(filePath, "utf-8");
      const data = JSON.parse(content);
      expect(Array.isArray(data)).toBe(true);
    });
  }

  it("emails.json has required fields per entry", () => {
    const data = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "emails.json"), "utf-8"));
    expect(data.length).toBeGreaterThan(0);
    for (const email of data) {
      expect(email.email_id).toBeTruthy();
      expect(email.subject).toBeTruthy();
      expect(email.sender).toBeTruthy();
      expect(email.intent).toBeDefined();
    }
  });

  it("runs.json has required fields per entry", () => {
    const data = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "runs.json"), "utf-8"));
    expect(data.length).toBeGreaterThan(0);
    for (const run of data) {
      expect(run.run_id).toBeTruthy();
      expect(run.skill_name).toBeTruthy();
      expect(run.status).toBeTruthy();
      expect(Array.isArray(run.steps)).toBe(true);
    }
  });

  it("process_docs.json has required fields per entry", () => {
    const data = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "process_docs.json"), "utf-8"));
    expect(data.length).toBeGreaterThan(0);
    for (const doc of data) {
      expect(doc.doc_id).toBeTruthy();
      expect(doc.user_input).toBeTruthy();
      expect(doc.extraction).toBeDefined();
      expect(doc.mermaid_code).toBeTruthy();
    }
  });

  it("rag_conversations.json has required fields per entry", () => {
    const data = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "rag_conversations.json"), "utf-8"));
    expect(data.length).toBeGreaterThan(0);
    for (const conv of data) {
      expect(conv.conversation_id).toBeTruthy();
      expect(conv.title).toBeTruthy();
      expect(Array.isArray(conv.messages)).toBe(true);
      expect(conv.messages.length).toBeGreaterThan(0);
    }
  });

  it("cubix_courses.json has required fields per entry", () => {
    const data = JSON.parse(fs.readFileSync(path.join(DATA_DIR, "cubix_courses.json"), "utf-8"));
    expect(data.length).toBeGreaterThan(0);
    for (const course of data) {
      expect(course.course_id).toBeTruthy();
      expect(course.structure).toBeDefined();
      expect(course.pipeline_state).toBeDefined();
      expect(Array.isArray(course.results)).toBe(true);
    }
  });
});

describe("No hardcoded dates in source files", () => {
  const srcDir = path.join(__dirname, "..");

  function findTsFiles(dir: string): string[] {
    const files: string[] = [];
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory() && !entry.name.startsWith("__") && entry.name !== "node_modules") {
        files.push(...findTsFiles(full));
      } else if (entry.name.endsWith(".tsx") || entry.name.endsWith(".ts")) {
        files.push(full);
      }
    }
    return files;
  }

  it("no page files fetch from /data/ directly (should use /api/)", () => {
    const pageFiles = findTsFiles(path.join(srcDir, "app")).filter((f) => f.endsWith("page.tsx"));
    const violations: string[] = [];
    for (const file of pageFiles) {
      const content = fs.readFileSync(file, "utf-8");
      // Check for direct /data/ fetch (should use /api/ instead)
      if (content.includes('fetch("/data/') || content.includes("fetch('/data/")) {
        violations.push(path.relative(srcDir, file));
      }
    }
    expect(violations).toEqual([]);
  });
});
