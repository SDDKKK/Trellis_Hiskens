import { describe, expect, it } from "vitest";
import { resolveAllAsSkills } from "../../src/configurators/shared.js";
import { AI_TOOLS } from "../../src/types/ai-tools.js";

// Kiro is skill-only (agentCapable=true): all common templates become trellis-* skills
// start is filtered out for agent-capable platforms
const EXPECTED_SKILL_NAMES = [
  "trellis-before-dev",
  "trellis-brainstorm",
  "trellis-break-loop",
  "trellis-check",
  "trellis-continue",
  "trellis-finish-work",
  "trellis-update-spec",
];

describe("kiro getAllSkills", () => {
  it("returns the expected skill set (without parallel)", () => {
    const skills = resolveAllAsSkills(AI_TOOLS.kiro.templateContext);
    const names = skills.map((skill) => skill.name).sort();
    expect(names).toEqual(EXPECTED_SKILL_NAMES);
  });

  it("each skill has matching frontmatter name", () => {
    const skills = resolveAllAsSkills(AI_TOOLS.kiro.templateContext);
    for (const skill of skills) {
      expect(skill.content.length).toBeGreaterThan(0);
      expect(skill.content).toContain("description:");
      const nameMatch = skill.content.match(/^name:\s*(.+)$/m);
      expect(nameMatch?.[1]?.trim()).toBe(skill.name);
    }
  });

  it("skill content does not contain .agents/skills/ paths", () => {
    const skills = resolveAllAsSkills(AI_TOOLS.kiro.templateContext);
    for (const skill of skills) {
      expect(skill.content).not.toContain(".agents/skills/");
    }
  });
});
