import { describe, expect, it } from "vitest";
import { getSkillTemplates } from "../../src/templates/common/index.js";

// Qoder skills come from the shared common skill templates
const EXPECTED_SKILL_NAMES = [
  "before-dev",
  "brainstorm",
  "break-loop",
  "check",
  "update-spec",
];

describe("qoder getAllSkills", () => {
  it("returns the expected skill set", () => {
    const skills = getSkillTemplates();
    const names = skills.map((s) => s.name);
    expect(names).toEqual(EXPECTED_SKILL_NAMES);
  });

  it("each skill has non-empty content", () => {
    const skills = getSkillTemplates();
    for (const skill of skills) {
      expect(skill.name.length).toBeGreaterThan(0);
      expect(skill.content.length).toBeGreaterThan(0);
    }
  });
});
