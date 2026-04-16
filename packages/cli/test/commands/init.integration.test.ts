/**
 * Integration tests for the init() command.
 *
 * Tests the full init flow in real temp directories with minimal mocking.
 * Only external dependencies are mocked: figlet, inquirer, child_process.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

// === External dependency mocks (hoisted by vitest) ===

vi.mock("figlet", () => ({
  default: { textSync: vi.fn(() => "TRELLIS") },
}));

vi.mock("inquirer", () => ({
  default: { prompt: vi.fn().mockResolvedValue({}) },
}));

vi.mock("node:child_process", async () => {
  const actual = await vi.importActual<typeof import("node:child_process")>(
    "node:child_process",
  );

  return {
    ...actual,
    execSync: vi.fn((command: string, options?: Parameters<typeof actual.execSync>[1]) => {
      if (
        command.includes("--version") ||
        command.includes("init_developer.py") ||
        command.includes("create_bootstrap.py")
      ) {
        return actual.execSync(command, options);
      }
      return Buffer.from("");
    }),
  };
});

// === Imports ===

import { init } from "../../src/commands/init.js";
import { VERSION } from "../../src/constants/version.js";
import { DIR_NAMES, PATHS } from "../../src/constants/paths.js";
import { resolveOverlayPath } from "../../src/utils/overlay.js";
import { execSync } from "node:child_process";

// eslint-disable-next-line @typescript-eslint/no-empty-function
const noop = () => {};
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe("init() integration", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "trellis-init-int-"));
    vi.spyOn(process, "cwd").mockReturnValue(tmpDir);
    vi.spyOn(console, "log").mockImplementation(noop);
    vi.spyOn(console, "error").mockImplementation(noop);
    vi.mocked(execSync).mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("#1 creates expected directory structure with defaults", async () => {
    await init({ yes: true });

    // Core workflow structure
    expect(fs.existsSync(path.join(tmpDir, DIR_NAMES.WORKFLOW))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, PATHS.SCRIPTS))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, PATHS.WORKSPACE))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, PATHS.TASKS))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, PATHS.SPEC))).toBe(true);

    // Default platforms: cursor + claude
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".codex"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".agents", "skills"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".agent", "workflows"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".kiro", "skills"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".gemini"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".qoder"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".codebuddy"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".windsurf", "workflows"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".github", "copilot"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".factory"))).toBe(false);

    // Root files
    expect(fs.existsSync(path.join(tmpDir, "AGENTS.md"))).toBe(true);
  });

  it("#2 single platform creates only that platform directory", async () => {
    await init({ yes: true, claude: true });

    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".iflow"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".opencode"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".codex"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".agents", "skills"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".agent", "workflows"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".kiro", "skills"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".gemini"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".qoder"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".codebuddy"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".windsurf", "workflows"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".github", "copilot"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".factory"))).toBe(false);
  });

  it("#3 multi platform creates all selected platform directories", async () => {
    await init({ yes: true, claude: true, cursor: true, opencode: true });

    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".opencode"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".iflow"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".codex"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".agents", "skills"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".agent", "workflows"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".kiro", "skills"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".gemini"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".qoder"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".codebuddy"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".windsurf", "workflows"))).toBe(
      false,
    );
    expect(fs.existsSync(path.join(tmpDir, ".github", "copilot"))).toBe(
      false,
    );
  });

  it("#3b codex platform creates skills plus .codex assets", async () => {
    await init({ yes: true, codex: true });

    expect(fs.existsSync(path.join(tmpDir, ".agents", "skills"))).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".agents", "skills", "start", "SKILL.md"),
      ),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".codex", "config.toml"))).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".codex", "agents", "check.toml"),
      ),
    ).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".codex", "skills", "parallel", "SKILL.md"),
      ),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".codex", "hooks.json"))).toBe(
      true,
    );
    expect(
      fs.existsSync(
        path.join(tmpDir, ".codex", "hooks", "session-start.py"),
      ),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".gemini"))).toBe(false);
  });

  it("#3c kiro platform creates .kiro/skills", async () => {
    await init({ yes: true, kiro: true });

    expect(fs.existsSync(path.join(tmpDir, ".kiro", "skills"))).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, ".kiro", "skills", "start", "SKILL.md")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, ".kiro", "skills", "parallel")),
    ).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#3d antigravity platform creates .agent/workflows", async () => {
    await init({ yes: true, antigravity: true });

    expect(fs.existsSync(path.join(tmpDir, ".agent", "workflows"))).toBe(
      true,
    );
    expect(
      fs.existsSync(path.join(tmpDir, ".agent", "workflows", "start.md")),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".gemini"))).toBe(false);
  });

  it("#3f windsurf platform creates .windsurf/workflows", async () => {
    await init({ yes: true, windsurf: true });

    expect(
      fs.existsSync(path.join(tmpDir, ".windsurf", "workflows")),
    ).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".windsurf", "workflows", "trellis-start.md"),
      ),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#3g qoder platform creates .qoder/skills", async () => {
    await init({ yes: true, qoder: true });

    expect(
      fs.existsSync(path.join(tmpDir, ".qoder", "skills")),
    ).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".qoder", "skills", "start", "SKILL.md"),
      ),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#3h codebuddy platform creates .codebuddy/commands/trellis", async () => {
    await init({ yes: true, codebuddy: true });

    expect(
      fs.existsSync(path.join(tmpDir, ".codebuddy", "commands", "trellis")),
    ).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".codebuddy", "commands", "trellis", "start.md"),
      ),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#3i copilot platform creates .github/copilot hooks and discovery config", async () => {
    await init({ yes: true, copilot: true });

    expect(fs.existsSync(path.join(tmpDir, ".github", "prompts"))).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, ".github", "prompts", "start.prompt.md")),
    ).toBe(true);

    expect(fs.existsSync(path.join(tmpDir, ".github", "copilot", "hooks"))).toBe(
      true,
    );
    expect(
      fs.existsSync(
        path.join(tmpDir, ".github", "copilot", "hooks", "session-start.py"),
      ),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, ".github", "copilot", "hooks.json")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, ".github", "hooks", "trellis.json")),
    ).toBe(true);

    const hashFile = path.join(
      tmpDir,
      DIR_NAMES.WORKFLOW,
      ".template-hashes.json",
    );
    const hashes = JSON.parse(
      fs.readFileSync(hashFile, "utf-8"),
    ) as Record<string, string>;
    const trackedPaths = Object.keys(hashes).map((p) => p.replace(/\\/g, "/"));
    expect(trackedPaths).toContain(".github/prompts/start.prompt.md");
    expect(trackedPaths).toContain(".github/copilot/hooks.json");
    expect(trackedPaths).toContain(".github/hooks/trellis.json");

    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#3e gemini platform creates .gemini/commands/trellis", async () => {
    await init({ yes: true, gemini: true });
    expect(fs.existsSync(path.join(tmpDir, ".gemini", "commands", "trellis"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".gemini", "commands", "trellis", "start.toml"))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#3j droid platform creates .factory/commands/trellis", async () => {
    await init({ yes: true, droid: true });
    expect(
      fs.existsSync(path.join(tmpDir, ".factory", "commands", "trellis")),
    ).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".factory", "commands", "trellis", "start.md"),
      ),
    ).toBe(true);
    // Frontmatter with description should be present
    const startContent = fs.readFileSync(
      path.join(tmpDir, ".factory", "commands", "trellis", "start.md"),
      "utf-8",
    );
    expect(startContent.startsWith("---\n")).toBe(true);
    expect(startContent).toMatch(/\ndescription:/);
    expect(fs.existsSync(path.join(tmpDir, ".claude"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, ".cursor"))).toBe(false);
  });

  it("#4 force mode overwrites previously modified files", async () => {
    await init({ yes: true, force: true });

    const workflowMd = path.join(tmpDir, PATHS.WORKFLOW_GUIDE_FILE);
    const original = fs.readFileSync(workflowMd, "utf-8");
    fs.writeFileSync(workflowMd, "user modified content");

    await init({ yes: true, force: true });

    expect(fs.readFileSync(workflowMd, "utf-8")).toBe(original);
  });

  it("#5 skip mode preserves previously modified files", async () => {
    await init({ yes: true, force: true });

    const workflowMd = path.join(tmpDir, PATHS.WORKFLOW_GUIDE_FILE);
    fs.writeFileSync(workflowMd, "user modified content");

    await init({ yes: true, skipExisting: true });

    expect(fs.readFileSync(workflowMd, "utf-8")).toBe("user modified content");
  });

  it("#6 re-init with force produces identical file set", async () => {
    await init({ yes: true, force: true });

    const collectFiles = (dir: string): string[] => {
      const files: string[] = [];
      const walk = (d: string) => {
        for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
          const full = path.join(d, entry.name);
          if (entry.isDirectory()) walk(full);
          else files.push(path.relative(tmpDir, full));
        }
      };
      walk(dir);
      return files.sort();
    };

    const first = collectFiles(tmpDir);
    await init({ yes: true, force: true });
    const second = collectFiles(tmpDir);

    expect(second).toEqual(first);
  });

  it("#7 passes developer name to init_developer script", async () => {
    await init({ yes: true, user: "testdev" });

    const calls = vi.mocked(execSync).mock.calls;
    const match = calls.find(
      ([cmd]) => typeof cmd === "string" && cmd.includes("init_developer.py"),
    );
    expect(match).toBeDefined();
    expect(String((match as [unknown])[0])).toContain('"testdev"');
  });

  it("#8 writes correct version file", async () => {
    await init({ yes: true });

    const content = fs.readFileSync(
      path.join(tmpDir, DIR_NAMES.WORKFLOW, ".version"),
      "utf-8",
    );
    expect(content).toBe(VERSION);
  });

  it("#9 initializes template hash tracking file", async () => {
    await init({ yes: true });

    const hashPath = path.join(
      tmpDir,
      DIR_NAMES.WORKFLOW,
      ".template-hashes.json",
    );
    expect(fs.existsSync(hashPath)).toBe(true);
    const hashes = JSON.parse(fs.readFileSync(hashPath, "utf-8"));
    expect(Object.keys(hashes).length).toBeGreaterThan(0);
  });

  it("#10 creates spec templates for backend, frontend, and guides", async () => {
    await init({ yes: true });

    const specDir = path.join(tmpDir, PATHS.SPEC);
    expect(fs.existsSync(path.join(specDir, "backend", "index.md"))).toBe(true);
    expect(fs.existsSync(path.join(specDir, "frontend", "index.md"))).toBe(
      true,
    );
    expect(fs.existsSync(path.join(specDir, "guides", "index.md"))).toBe(true);
  });

  it("#11 backend project init skips frontend spec templates", async () => {
    // go.mod triggers detectProjectType → "backend"
    fs.writeFileSync(path.join(tmpDir, "go.mod"), "module example.com/app\n");

    await init({ yes: true });

    const specDir = path.join(tmpDir, PATHS.SPEC);
    expect(fs.existsSync(path.join(specDir, "backend", "index.md"))).toBe(true);
    expect(fs.existsSync(path.join(specDir, "frontend"))).toBe(false);
    expect(fs.existsSync(path.join(specDir, "guides", "index.md"))).toBe(true);
  });

  it("#12 frontend project init skips backend spec templates", async () => {
    // vite.config.ts triggers detectProjectType → "frontend"
    fs.writeFileSync(
      path.join(tmpDir, "vite.config.ts"),
      "export default {}\n",
    );

    await init({ yes: true });

    const specDir = path.join(tmpDir, PATHS.SPEC);
    expect(fs.existsSync(path.join(specDir, "frontend", "index.md"))).toBe(
      true,
    );
    expect(fs.existsSync(path.join(specDir, "backend"))).toBe(false);
    expect(fs.existsSync(path.join(specDir, "guides", "index.md"))).toBe(true);
  });

  // ===========================================================================
  // Monorepo integration tests
  // ===========================================================================

  /** Helper: set up a pnpm workspace with two packages */
  function setupPnpmWorkspace(
    dir: string,
    packages: { rel: string; name: string; files?: Record<string, string> }[],
  ): void {
    fs.writeFileSync(
      path.join(dir, "pnpm-workspace.yaml"),
      "packages:\n  - 'packages/*'\n",
    );
    for (const pkg of packages) {
      const pkgDir = path.join(dir, pkg.rel);
      fs.mkdirSync(pkgDir, { recursive: true });
      fs.writeFileSync(
        path.join(pkgDir, "package.json"),
        JSON.stringify({ name: pkg.name }),
      );
      if (pkg.files) {
        for (const [name, content] of Object.entries(pkg.files)) {
          fs.writeFileSync(path.join(pkgDir, name), content);
        }
      }
    }
  }

  it("#13 monorepo: creates per-package spec directories", async () => {
    // @app/web: vite.config.ts → frontend (package.json also present → still frontend)
    // @app/api: package.json + go.mod → fullstack (both indicators present)
    setupPnpmWorkspace(tmpDir, [
      { rel: "packages/web", name: "@app/web", files: { "vite.config.ts": "" } },
      { rel: "packages/api", name: "@app/api", files: { "go.mod": "" } },
    ]);

    await init({ yes: true });

    const specDir = path.join(tmpDir, PATHS.SPEC);
    // Per-package spec dirs created with sanitized names (scope stripped)
    expect(fs.existsSync(path.join(specDir, "web"))).toBe(true);
    expect(fs.existsSync(path.join(specDir, "api"))).toBe(true);

    // web: frontend (vite.config.ts) → has frontend/, no backend/
    expect(
      fs.existsSync(path.join(specDir, "web", "frontend", "index.md")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(specDir, "web", "backend")),
    ).toBe(false);

    // api: fullstack (package.json + go.mod) → has both backend/ and frontend/
    expect(
      fs.existsSync(path.join(specDir, "api", "backend", "index.md")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(specDir, "api", "frontend", "index.md")),
    ).toBe(true);

    // Guides still created (shared)
    expect(fs.existsSync(path.join(specDir, "guides", "index.md"))).toBe(true);

    // Global backend/frontend should NOT exist (monorepo mode)
    expect(fs.existsSync(path.join(specDir, "backend"))).toBe(false);
    expect(fs.existsSync(path.join(specDir, "frontend"))).toBe(false);
  });

  it("#14 monorepo: writes packages section to config.yaml", async () => {
    setupPnpmWorkspace(tmpDir, [
      { rel: "packages/cli", name: "@trellis/cli" },
      { rel: "packages/docs", name: "@trellis/docs" },
    ]);

    await init({ yes: true });

    const configPath = path.join(tmpDir, DIR_NAMES.WORKFLOW, "config.yaml");
    expect(fs.existsSync(configPath)).toBe(true);

    const configContent = fs.readFileSync(configPath, "utf-8");
    expect(configContent).toContain("packages:");
    expect(configContent).toContain("cli:");
    expect(configContent).toContain("path: packages/cli");
    expect(configContent).toContain("docs:");
    expect(configContent).toContain("path: packages/docs");
    expect(configContent).toContain("default_package: cli");
  });

  it("#15 monorepo: bootstrap task references per-package spec paths", async () => {
    setupPnpmWorkspace(tmpDir, [
      { rel: "packages/core", name: "core" },
      { rel: "packages/ui", name: "ui" },
    ]);

    await init({ yes: true, user: "dev" });

    const taskDir = path.join(tmpDir, PATHS.TASKS, "00-bootstrap-guidelines");
    expect(fs.existsSync(taskDir)).toBe(true);

    // task.json has per-package subtasks
    const taskJson = JSON.parse(
      fs.readFileSync(path.join(taskDir, "task.json"), "utf-8"),
    );
    const subtaskNames: string[] = taskJson.subtasks.map(
      (s: { name: string }) => s.name,
    );
    expect(subtaskNames).toContain("Fill guidelines for core");
    expect(subtaskNames).toContain("Fill guidelines for ui");

    // relatedFiles point to spec/<name>/
    expect(taskJson.relatedFiles).toContain(".trellis/spec/core/");
    expect(taskJson.relatedFiles).toContain(".trellis/spec/ui/");

    // prd.md mentions packages
    const prd = fs.readFileSync(path.join(taskDir, "prd.md"), "utf-8");
    expect(prd).toContain("core");
    expect(prd).toContain("ui");
    expect(prd).toContain("spec/");
  });

  it("#16 --no-monorepo skips detection even with workspace config", async () => {
    setupPnpmWorkspace(tmpDir, [
      { rel: "packages/a", name: "a" },
    ]);

    await init({ yes: true, monorepo: false });

    const specDir = path.join(tmpDir, PATHS.SPEC);
    // Single-repo spec (global backend + frontend), no per-package dirs
    expect(fs.existsSync(path.join(specDir, "backend", "index.md"))).toBe(true);
    expect(fs.existsSync(path.join(specDir, "frontend", "index.md"))).toBe(true);
    expect(fs.existsSync(path.join(specDir, "a"))).toBe(false);

    // config.yaml should NOT have packages: section
    const configContent = fs.readFileSync(
      path.join(tmpDir, DIR_NAMES.WORKFLOW, "config.yaml"),
      "utf-8",
    );
    expect(configContent).not.toMatch(/^packages\s*:/m);
  });

  it("#17 --monorepo without workspace config exits with error", async () => {
    // Empty directory — no workspace configs
    const logSpy = vi.mocked(console.log);

    await init({ yes: true, monorepo: true });

    // Should log error about missing monorepo config
    const errorCall = logSpy.mock.calls.find(
      ([msg]) => typeof msg === "string" && msg.includes("no monorepo"),
    );
    expect(errorCall).toBeDefined();

    // Should NOT create .trellis/ (early return)
    expect(fs.existsSync(path.join(tmpDir, DIR_NAMES.WORKFLOW))).toBe(false);
  });

  it("#18 monorepo: re-init does not duplicate packages in config.yaml", async () => {
    setupPnpmWorkspace(tmpDir, [
      { rel: "packages/lib", name: "lib" },
    ]);

    await init({ yes: true, force: true });
    await init({ yes: true, force: true });

    const configContent = fs.readFileSync(
      path.join(tmpDir, DIR_NAMES.WORKFLOW, "config.yaml"),
      "utf-8",
    );
    // packages: should appear exactly once
    const matches = configContent.match(/^packages\s*:/gm);
    expect(matches).toHaveLength(1);
  });

  it("overlay #13 init applies OVERRIDE files on top of base templates", async () => {
    const overlayPath = resolveOverlayPath("hiskens");
    expect(overlayPath).not.toBeNull();
    if (!overlayPath) {
      throw new Error("Expected hiskens overlay to exist");
    }

    await init({ yes: true, claude: true, overlay: "hiskens" });

    const targetPath = path.join(
      tmpDir,
      ".claude",
      "commands",
      "trellis",
      "brainstorm.md",
    );
    const overlayFile = path.join(
      overlayPath,
      "templates",
      "claude",
      "commands",
      "trellis",
      "brainstorm.md",
    );
    expect(fs.readFileSync(targetPath, "utf-8")).toBe(
      fs.readFileSync(overlayFile, "utf-8"),
    );
  });

  it("overlay #14 init adds overlay-only APPEND files", async () => {
    await init({ yes: true, claude: true, overlay: "hiskens" });

    expect(
      fs.existsSync(
        path.join(
          tmpDir,
          ".claude",
          "commands",
          "trellis",
          "before-python-dev.md",
        ),
      ),
    ).toBe(true);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".claude", "hooks", "context-monitor.py"),
      ),
    ).toBe(true);
  });

  it("overlay #15 init installs overlay statusline template when provided", async () => {
    const overlayPath = resolveOverlayPath("hiskens");
    expect(overlayPath).not.toBeNull();
    if (!overlayPath) {
      throw new Error("Expected hiskens overlay to exist");
    }

    await init({ yes: true, claude: true, overlay: "hiskens" });

    const targetPath = path.join(tmpDir, ".claude", "hooks", "statusline.py");
    const overlayTemplatePath = path.join(
      overlayPath,
      "templates",
      "claude",
      "hooks",
      "statusline.py",
    );
    const baseTemplatePath = path.join(
      __dirname,
      "..",
      "..",
      "src",
      "templates",
      "claude",
      "hooks",
      "statusline.py",
    );

    expect(fs.existsSync(targetPath)).toBe(true);
    expect(fs.readFileSync(targetPath, "utf-8")).toBe(
      fs.existsSync(overlayTemplatePath)
        ? fs.readFileSync(overlayTemplatePath, "utf-8")
        : fs.readFileSync(baseTemplatePath, "utf-8"),
    );
  });

  it("overlay #16 init removes EXCLUDE paths from output", async () => {
    await init({ yes: true, claude: true, codex: true, overlay: "hiskens" });

    expect(
      fs.existsSync(
        path.join(tmpDir, ".claude", "commands", "trellis", "before-dev.md"),
      ),
    ).toBe(false);
    expect(
      fs.existsSync(
        path.join(tmpDir, ".agents", "skills", "before-dev", "SKILL.md"),
      ),
    ).toBe(false);
  });

  it("overlay #17 init resolves PYTHON_CMD placeholders in merged claude settings", async () => {
    await init({ yes: true, claude: true, overlay: "hiskens" });

    const settingsPath = path.join(tmpDir, ".claude", "settings.json");
    const settingsContent = fs.readFileSync(settingsPath, "utf-8");
    const settings = JSON.parse(settingsContent) as {
      hooks: Record<
        string,
        { matcher: string; hooks: { command: string }[] }[]
      >;
    };
    const expectedPython = process.platform === "win32" ? "python" : "python3";

    expect(settingsContent).not.toContain("{{PYTHON_CMD}}");
    expect(settings.hooks.UserPromptSubmit[0].hooks[0].command).toContain(
      `${expectedPython} "$CLAUDE_PROJECT_DIR/.claude/hooks/intent-gate.py"`,
    );
    expect(settings.hooks.PostToolUse[0].hooks[0].command).toContain(
      `${expectedPython} "$CLAUDE_PROJECT_DIR/.claude/hooks/todo-enforcer.py"`,
    );
  });

  it("overlay #18 monorepo init creates package-scoped bootstrap via generated script", async () => {
    setupPnpmWorkspace(tmpDir, [
      { rel: "packages/solver", name: "@smoke/solver" },
      { rel: "packages/viz", name: "@smoke/viz", files: { "vite.config.ts": "" } },
    ]);

    await init({ yes: true, user: "dev", overlay: "hiskens" });

    const taskDir = path.join(tmpDir, PATHS.TASKS, "00-bootstrap-guidelines");
    expect(fs.existsSync(taskDir)).toBe(true);

    const taskJson = JSON.parse(
      fs.readFileSync(path.join(taskDir, "task.json"), "utf-8"),
    ) as {
      package: string | null;
      relatedFiles: string[];
    };
    expect(taskJson.package).toBe("solver");
    expect(taskJson.relatedFiles).toContain(".trellis/spec/solver/python/");
    expect(taskJson.relatedFiles).toContain(".trellis/spec/solver/matlab/");

    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "solver", "python", "index.md")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "solver", "matlab", "index.md")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "viz", "python", "index.md")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "viz", "matlab", "index.md")),
    ).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, PATHS.SPEC, "python"))).toBe(false);
    expect(fs.existsSync(path.join(tmpDir, PATHS.SPEC, "matlab"))).toBe(false);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "solver", "backend")),
    ).toBe(false);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "viz", "frontend")),
    ).toBe(false);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "frontend")),
    ).toBe(false);
    expect(
      fs.existsSync(path.join(tmpDir, PATHS.SPEC, "backend")),
    ).toBe(false);

    const prd = fs.readFileSync(path.join(taskDir, "prd.md"), "utf-8");
    expect(prd).toContain(".trellis/spec/solver/python/");
    expect(prd).toContain(".trellis/spec/solver/matlab/");

    const currentTask = fs.readFileSync(
      path.join(tmpDir, DIR_NAMES.WORKFLOW, ".current-task"),
      "utf-8",
    );
    expect(currentTask.trim()).toBe(".trellis/tasks/00-bootstrap-guidelines");
  });

  it("overlay #19 init copies statusline companion files and skills", async () => {
    await init({ yes: true, claude: true, overlay: "hiskens" });

    expect(
      fs.existsSync(path.join(tmpDir, ".claude", "hooks", "parse_sub2api_usage.py")),
    ).toBe(true);
    expect(
      fs.existsSync(path.join(tmpDir, ".claude", "skills", "grok-search", "SKILL.md")),
    ).toBe(true);
  });
});
