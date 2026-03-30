import { describe, it, expect } from "vitest";
import { toCsv } from "@/lib/csv-export";

describe("toCsv", () => {
  it("generates valid CSV with headers and rows", () => {
    const csv = toCsv(["Name", "Age"], [["Alice", "30"], ["Bob", "25"]]);
    expect(csv).toBe("Name,Age\nAlice,30\nBob,25");
  });

  it("escapes commas in values", () => {
    const csv = toCsv(["Name"], [["Doe, John"]]);
    expect(csv).toBe('Name\n"Doe, John"');
  });

  it("escapes double quotes in values", () => {
    const csv = toCsv(["Note"], [['He said "hello"']]);
    expect(csv).toBe('Note\n"He said ""hello"""');
  });

  it("escapes newlines in values", () => {
    const csv = toCsv(["Note"], [["line1\nline2"]]);
    expect(csv).toBe('Note\n"line1\nline2"');
  });

  it("handles empty rows", () => {
    const csv = toCsv(["A", "B"], []);
    expect(csv).toBe("A,B");
  });

  it("handles empty values", () => {
    const csv = toCsv(["A"], [[""]]);
    expect(csv).toBe("A\n");
  });
});
