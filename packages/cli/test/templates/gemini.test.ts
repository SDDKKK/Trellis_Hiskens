import { describe, expect, it } from "vitest";
import { resolveCommands } from "../../src/configurators/shared.js";
import { AI_TOOLS } from "../../src/types/ai-tools.js";

// Gemini uses subdirectory namespacing: commands/trellis/<name>.toml (no parallel)
// agentCapable=true so start is filtered out
const EXPECTED_COMMAND_NAMES = ["continue", "finish-work"];

describe("gemini getAllCommands", () => {
  it("returns the expected command set", () => {
    const commands = resolveCommands(AI_TOOLS.gemini.templateContext);
    const names = commands.map((c) => c.name);
    expect(names).toEqual(EXPECTED_COMMAND_NAMES);
  });

  it("each command has non-empty content", () => {
    const commands = resolveCommands(AI_TOOLS.gemini.templateContext);
    for (const command of commands) {
      expect(command.name.length).toBeGreaterThan(0);
      expect(command.content.length).toBeGreaterThan(0);
    }
  });

  it("command names do not include .toml extension", () => {
    const commands = resolveCommands(AI_TOOLS.gemini.templateContext);
    for (const cmd of commands) {
      expect(cmd.name).not.toContain(".toml");
    }
  });

  it("TOML-wrapped commands have valid TOML structure", () => {
    const commands = resolveCommands(AI_TOOLS.gemini.templateContext);
    for (const cmd of commands) {
      const toml = `description = "Trellis: ${cmd.name}"\n\nprompt = """\n${cmd.content}\n"""\n`;
      expect(toml).toContain("description = ");
      expect(toml).toContain('prompt = """');
    }
  });
});
