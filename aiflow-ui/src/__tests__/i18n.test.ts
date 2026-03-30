import { describe, it, expect, beforeEach } from "vitest";
import { t, tWithLocale, getLocale, setLocale } from "@/lib/i18n";

describe("i18n", () => {
  beforeEach(() => {
    localStorage.clear();
    setLocale("hu");
  });

  it("returns Hungarian translation by default", () => {
    expect(tWithLocale("sidebar.dashboard", "hu")).toBe("Dashboard");
    expect(tWithLocale("sidebar.costs", "hu")).toBe("Koltsegek");
  });

  it("returns English translation when locale is en", () => {
    expect(tWithLocale("sidebar.costs", "en")).toBe("Costs");
    expect(tWithLocale("sidebar.runs", "en")).toBe("Runs");
  });

  it("returns key if translation missing", () => {
    expect(tWithLocale("nonexistent.key", "hu")).toBe("nonexistent.key");
  });

  it("persists locale to localStorage", () => {
    setLocale("en");
    expect(localStorage.getItem("aiflow_locale")).toBe("en");
  });

  it("reads locale from localStorage", () => {
    localStorage.setItem("aiflow_locale", "en");
    expect(getLocale()).toBe("en");
  });

  it("defaults to hu when localStorage is empty", () => {
    expect(getLocale()).toBe("hu");
  });

  it("ignores invalid locale in localStorage", () => {
    localStorage.setItem("aiflow_locale", "fr");
    expect(getLocale()).toBe("hu");
  });

  it("has matching keys in both languages", () => {
    const testKeys = [
      "sidebar.dashboard", "sidebar.costs", "sidebar.runs", "sidebar.logout",
      "common.loading", "common.save", "common.export",
      "skill.invoice", "skill.email", "skill.rag",
    ];
    for (const key of testKeys) {
      const hu = tWithLocale(key, "hu");
      const en = tWithLocale(key, "en");
      expect(hu).not.toBe(key); // should have a translation, not return the key
      expect(en).not.toBe(key);
    }
  });
});
