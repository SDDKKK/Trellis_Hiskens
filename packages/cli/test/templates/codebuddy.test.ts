import { describe, expect, it } from "vitest";
import { resolveCommands } from "../../src/configurators/shared.js";
import { AI_TOOLS } from "../../src/types/ai-tools.js";

// CodeBuddy uses nested directories: commands/trellis/<name>.md
// agentCapable=true so start is filtered out
const EXPECTED_COMMAND_NAMES = ["continue", "finish-work"];

describe("codebuddy getAllCommands", () => {
  it("returns the expected command set", () => {
    const commands = resolveCommands(AI_TOOLS.codebuddy.templateContext);
    const names = commands.map((cmd) => cmd.name);
    expect(names).toEqual(EXPECTED_COMMAND_NAMES);
  });

  it("each command has name and content", () => {
    const commands = resolveCommands(AI_TOOLS.codebuddy.templateContext);
    for (const cmd of commands) {
      expect(cmd.name.length).toBeGreaterThan(0);
      expect(cmd.content.length).toBeGreaterThan(0);
    }
  });

  it("command names do not include .md extension", () => {
    const commands = resolveCommands(AI_TOOLS.codebuddy.templateContext);
    for (const cmd of commands) {
      expect(cmd.name).not.toContain(".md");
    }
  });
});
