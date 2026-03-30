import { describe, it, expect } from "vitest";
import { SKILLS } from "@/lib/types";

describe("SKILLS constant", () => {
  it("has 6 skills", () => {
    expect(SKILLS).toHaveLength(6);
  });

  it("contains all expected skill names", () => {
    const names = SKILLS.map((s) => s.name);
    expect(names).toContain("process_documentation");
    expect(names).toContain("aszf_rag_chat");
    expect(names).toContain("email_intent_processor");
    expect(names).toContain("invoice_processor");
    expect(names).toContain("cubix_course_capture");
    expect(names).toContain("qbpp_test_automation");
  });

  it("each skill has required fields", () => {
    for (const skill of SKILLS) {
      expect(skill.name).toBeTruthy();
      expect(skill.display_name).toBeTruthy();
      expect(skill.status).toBeTruthy();
      expect(typeof skill.test_count).toBe("number");
      expect(skill.description).toBeTruthy();
    }
  });
});
