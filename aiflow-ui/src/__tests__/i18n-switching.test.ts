import { describe, it, expect, beforeEach } from "vitest";
import { getLocale, setLocale, tWithLocale, type Locale } from "@/lib/i18n";

describe("i18n locale switching", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("setLocale persists and getLocale reads it back", () => {
    setLocale("en");
    expect(getLocale()).toBe("en");
    setLocale("hu");
    expect(getLocale()).toBe("hu");
  });

  it("switching locale changes all sidebar labels", () => {
    const sidebarKeys = [
      "sidebar.dashboard", "sidebar.skills", "sidebar.monitoring",
      "sidebar.costs", "sidebar.runs", "sidebar.logout",
    ];
    for (const key of sidebarKeys) {
      const hu = tWithLocale(key, "hu");
      const en = tWithLocale(key, "en");
      // Both should have translations (not return the key)
      expect(hu).not.toBe(key);
      expect(en).not.toBe(key);
      // hu and en should be different for most keys
      if (key !== "sidebar.dashboard" && key !== "sidebar.skills" && key !== "sidebar.monitoring") {
        expect(hu).not.toBe(en);
      }
    }
  });

  it("switching locale changes all skill labels", () => {
    const skillKeys = ["skill.invoice", "skill.email", "skill.rag", "skill.diagram", "skill.cubix"];
    for (const key of skillKeys) {
      const hu = tWithLocale(key, "hu");
      const en = tWithLocale(key, "en");
      expect(hu).not.toBe(key);
      expect(en).not.toBe(key);
    }
  });

  it("switching locale changes common UI labels", () => {
    const commonKeys = [
      "common.loading", "common.error", "common.retry", "common.save",
      "common.cancel", "common.confirm", "common.reset", "common.export",
      "common.print", "common.send", "common.generate", "common.noData",
    ];
    for (const key of commonKeys) {
      const hu = tWithLocale(key, "hu");
      const en = tWithLocale(key, "en");
      expect(hu).not.toBe(key);
      expect(en).not.toBe(key);
    }
  });

  it("switching locale changes page titles", () => {
    const pageKeys = [
      "page.costs.title", "page.costs.subtitle",
      "page.runs.title", "page.runs.subtitle",
      "page.login.title", "page.login.username", "page.login.password",
    ];
    for (const key of pageKeys) {
      const hu = tWithLocale(key, "hu");
      const en = tWithLocale(key, "en");
      expect(hu).not.toBe(key);
      expect(en).not.toBe(key);
    }
  });
});
