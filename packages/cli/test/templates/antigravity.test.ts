import { describe, expect, it } from "vitest";
import { getAllWorkflows } from "../../src/templates/antigravity/index.js";

// Antigravity workflows come from common skill templates (getSkillTemplates)
const EXPECTED_SKILL_NAMES = [
  "before-dev",
  "brainstorm",
  "break-loop",
  "check",
  "update-spec",
];

describe("antigravity getAllWorkflows", () => {
  it("returns the expected workflow set", () => {
    const workflows = getAllWorkflows();
    const names = workflows.map((workflow) => workflow.name);
    expect(names).toEqual(EXPECTED_SKILL_NAMES);
  });

  it("each workflow has non-empty content", () => {
    const workflows = getAllWorkflows();
    for (const workflow of workflows) {
      expect(workflow.content.length).toBeGreaterThan(0);
    }
  });

  it("adapts codex skill paths to antigravity workflow paths", () => {
    const workflows = getAllWorkflows();

    for (const workflow of workflows) {
      expect(workflow.content).not.toContain(".agents/skills/");
    }
  });
});
