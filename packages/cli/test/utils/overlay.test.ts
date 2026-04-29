import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getOverlayTemplatePath,
  loadExcludeList,
  loadOverlayConfig,
  mergeSettings,
  resolveOverlayPath,
} from "../../src/utils/overlay.js";

function writeOverlaySettings(tmpDir: string, payload: object): string {
  const filePath = path.join(tmpDir, "settings.overlay.json");
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));
  return filePath;
}

function requireOverlayPath(name = "hiskens"): string {
  const overlayPath = resolveOverlayPath(name);
  expect(overlayPath).not.toBeNull();
  return overlayPath ?? "";
}

describe("overlay utils", () => {
  const tmpDirs: string[] = [];

  afterEach(() => {
    vi.restoreAllMocks();
    for (const tmpDir of tmpDirs.splice(0)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  it("#1 resolveOverlayPath('hiskens') locates the built-in overlay", () => {
    const overlayPath = resolveOverlayPath("hiskens");
    expect(overlayPath).not.toBeNull();
    expect(overlayPath).toContain(`${path.sep}overlays${path.sep}hiskens`);
  });

  it("#2 resolveOverlayPath supports absolute paths", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);

    expect(resolveOverlayPath(tmpDir)).toBe(tmpDir);
  });

  it("#3 resolveOverlayPath returns null for missing overlays", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(resolveOverlayPath("does-not-exist")).toBeNull();
    expect(warnSpy).toHaveBeenCalledOnce();
  });

  it("#4 loadExcludeList parses v0.5 overlay exclude.yaml", () => {
    const overlayPath = requireOverlayPath();

    const excludeList = loadExcludeList(overlayPath);
    expect(excludeList).toEqual([
      "claude/agents/review.md",
      "trellis/worktree.yaml",
    ]);
  });

  it("loads overlay metadata from overlay.yaml", () => {
    const overlayPath = requireOverlayPath();

    const config = loadOverlayConfig(overlayPath);
    expect(config.name).toBe("hiskens");
    expect(config.version).toBe("1.0.0");
    expect(config.settings_merge?.claude).toBe(
      "templates/claude/settings.overlay.json",
    );
    expect(config.dev_types).toContain("trellis");
  });

  it("returns the overlay template directory for an existing platform", () => {
    const overlayPath = requireOverlayPath();

    const templatePath = getOverlayTemplatePath(overlayPath, "claude");
    expect(templatePath).not.toBeNull();
    expect(fs.existsSync(templatePath ?? "")).toBe(true);
  });

  it("#5 mergeSettings initializes missing hooks safely", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      hooks: {
        Stop: [{ matcher: "", hooks: [{ type: "command", command: "stop" }] }],
      },
    });

    const merged = JSON.parse(mergeSettings('{"env":{"BASE":"1"}}', overlayPath));
    expect(merged.env.BASE).toBe("1");
    expect(merged.hooks.Stop[0].hooks[0].command).toBe("stop");
  });

  it("#6 mergeSettings merges env keys", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      env: { NEW_KEY: "value" },
    });

    const merged = JSON.parse(
      mergeSettings('{"env":{"BASE_KEY":"base"}}', overlayPath),
    );
    expect(merged.env).toEqual({ BASE_KEY: "base", NEW_KEY: "value" });
  });

  it("#7 mergeSettings appends new hook events", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      hooks: {
        PostToolUse: [
          { matcher: "TodoWrite", hooks: [{ type: "command", command: "todo" }] },
        ],
      },
    });

    const merged = JSON.parse(mergeSettings('{"hooks":{}}', overlayPath));
    expect(merged.hooks.PostToolUse).toHaveLength(1);
    expect(merged.hooks.PostToolUse[0].matcher).toBe("TodoWrite");
  });

  it("#8 mergeSettings overrides existing matcher entries", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      hooks: {
        PreToolUse: [{ matcher: "Bash", hooks: [{ type: "command", command: "new" }] }],
      },
    });

    const merged = JSON.parse(
      mergeSettings(
        '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"old"}]}]}}',
        overlayPath,
      ),
    );
    expect(merged.hooks.PreToolUse).toHaveLength(1);
    expect(merged.hooks.PreToolUse[0].hooks[0].command).toBe("new");
  });

  it("#9 mergeSettings appends new matchers to existing events", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      hooks: {
        PreToolUse: [
          { matcher: "Bash", hooks: [{ type: "command", command: "bash" }] },
        ],
      },
    });

    const merged = JSON.parse(
      mergeSettings(
        '{"hooks":{"PreToolUse":[{"matcher":"Edit","hooks":[{"type":"command","command":"edit"}]}]}}',
        overlayPath,
      ),
    );
    expect(merged.hooks.PreToolUse).toHaveLength(2);
    expect(merged.hooks.PreToolUse[1].matcher).toBe("Bash");
  });

  it("#10 mergeSettings deduplicates permissions.deny", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      permissions: { deny: ["WebFetch", "WebSearch"] },
    });

    const merged = JSON.parse(
      mergeSettings(
        '{"permissions":{"deny":["WebFetch","Read"]}}',
        overlayPath,
      ),
    );
    expect(merged.permissions.deny).toEqual(["WebFetch", "Read", "WebSearch"]);
  });

  it("#11 mergeSettings skips invalid non-array hook values", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      hooks: { PreToolUse: { matcher: "Bash" } },
    });

    const merged = JSON.parse(
      mergeSettings('{"hooks":{"PreToolUse":[]}}', overlayPath),
    );
    expect(merged.hooks.PreToolUse).toEqual([]);
  });

  it("#12 mergeSettings writes overlay default preferences", () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-overlay-"));
    tmpDirs.push(tmpDir);
    const overlayPath = writeOverlaySettings(tmpDir, {
      enabledPlugins: { github: true },
      model: "opus[1m]",
      alwaysThinkingEnabled: true,
      effortLevel: "medium",
    });

    const merged = JSON.parse(mergeSettings("{}", overlayPath));
    expect(merged.enabledPlugins).toEqual({ github: true });
    expect(merged.model).toBe("opus[1m]");
    expect(merged.alwaysThinkingEnabled).toBe(true);
    expect(merged.effortLevel).toBe("medium");
  });
});
