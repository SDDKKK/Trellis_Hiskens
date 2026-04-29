import { describe, expect, it } from "vitest";
import { resolveCommands } from "../../src/configurators/shared.js";
import { AI_TOOLS } from "../../src/types/ai-tools.js";

// Cursor uses prefix naming: trellis-<name>.md (no subdirectory, no parallel)
// agentCapable=true so start is filtered out
// The trellis- prefix is added by the configurator when writing the file
const EXPECTED_COMMAND_NAMES = ["trellis-continue", "trellis-finish-work"];

describe("cursor getAllCommands", () => {
  it("returns the expected command set", () => {
    const commands = resolveCommands(AI_TOOLS.cursor.templateContext);
    const names = commands.map((cmd) => `trellis-${cmd.name}`);
    expect(names).toEqual(EXPECTED_COMMAND_NAMES);
  });

  it("each command has name and content", () => {
    const commands = resolveCommands(AI_TOOLS.cursor.templateContext);
    for (const cmd of commands) {
      expect(cmd.name.length).toBeGreaterThan(0);
      expect(cmd.content.length).toBeGreaterThan(0);
    }
  });

  it("command names do not include .md extension", () => {
    const commands = resolveCommands(AI_TOOLS.cursor.templateContext);
    for (const cmd of commands) {
      expect(cmd.name).not.toContain(".md");
    }
  });
});
