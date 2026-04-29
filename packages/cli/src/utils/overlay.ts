import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolvePlaceholders } from "../configurators/shared.js";

export interface OverlayConfig {
  name: string;
  version: string;
  description?: string;
  compatible_upstream: string;
  author?: string;
  settings_merge?: Record<string, string>;
  dev_types?: string[];
}

type YamlValue = string | string[] | Record<string, string>;

type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
interface JsonObject {
  [key: string]: JsonValue;
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BUILTIN_OVERLAY_DIRS = [
  // Packaged CLI layout after build: dist/utils/overlay.js -> dist/overlays/
  path.resolve(__dirname, "../overlays"),
  // Optional package-root layout for local development or future packaging.
  path.resolve(__dirname, "../../overlays"),
  // Monorepo source layout: packages/cli/src/utils/overlay.ts -> repo overlays/
  path.resolve(__dirname, "../../../../overlays"),
];

function stripQuotes(value: string): string {
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

function parseSimpleYaml(content: string): Record<string, YamlValue> {
  const result: Record<string, YamlValue> = {};
  let activeKey: string | null = null;

  for (const rawLine of content.split(/\r?\n/)) {
    const trimmed = rawLine.trim();
    if (trimmed === "" || trimmed.startsWith("#")) {
      continue;
    }

    const indent = rawLine.length - rawLine.trimStart().length;

    if (indent === 0) {
      activeKey = null;
      const match = trimmed.match(/^([A-Za-z0-9_]+):(?:\s+(.*)|\s*)$/);
      if (!match) {
        continue;
      }

      const key = match[1];
      const rawValue = match[2];
      if (rawValue === undefined || rawValue === "") {
        activeKey = key;
        continue;
      }

      result[key] = stripQuotes(rawValue.trim());
      continue;
    }

    if (!activeKey) {
      continue;
    }

    if (trimmed.startsWith("- ")) {
      const current = result[activeKey];
      const values = Array.isArray(current) ? current : [];
      values.push(stripQuotes(trimmed.slice(2).trim()));
      result[activeKey] = values;
      continue;
    }

    const nestedMatch = trimmed.match(/^([A-Za-z0-9_]+):(?:\s+(.*)|\s*)$/);
    if (!nestedMatch) {
      continue;
    }

    const nestedKey = nestedMatch[1];
    const rawValue = stripQuotes((nestedMatch[2] ?? "").trim());
    const current = result[activeKey];
    const nested =
      current && !Array.isArray(current) && typeof current === "object"
        ? current
        : {};
    nested[nestedKey] = rawValue;
    result[activeKey] = nested;
  }

  return result;
}

function getRequiredString(
  parsed: Record<string, YamlValue>,
  key: string,
): string {
  const value = parsed[key];
  if (typeof value !== "string" || value === "") {
    throw new Error(`Invalid overlay config: missing ${key}`);
  }
  return value;
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function ensureObject(parent: JsonObject, key: string): JsonObject {
  const value = parent[key];
  if (isJsonObject(value)) {
    return value;
  }
  const next: JsonObject = {};
  parent[key] = next;
  return next;
}

function getMatcher(value: JsonValue): string | null {
  if (!isJsonObject(value)) {
    return null;
  }
  const matcher = value.matcher;
  return typeof matcher === "string" ? matcher : null;
}

function toPosixRelative(fromDir: string, filePath: string): string {
  return path.relative(fromDir, filePath).split(path.sep).join("/");
}

export function resolveOverlayPath(overlayName: string): string | null {
  if (path.isAbsolute(overlayName)) {
    if (fs.existsSync(overlayName) && fs.statSync(overlayName).isDirectory()) {
      return overlayName;
    }
    console.warn(`Warning: overlay "${overlayName}" not found`);
    return null;
  }

  const normalizedName = overlayName.replace(/\\/g, "/");
  if (
    normalizedName === "" ||
    normalizedName.startsWith("/") ||
    normalizedName.split("/").some((segment) => segment === "..")
  ) {
    console.warn(`Warning: overlay "${overlayName}" not found`);
    return null;
  }

  for (const builtinDir of BUILTIN_OVERLAY_DIRS) {
    const candidate = path.join(builtinDir, normalizedName);
    if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
      return candidate;
    }
  }

  console.warn(`Warning: overlay "${overlayName}" not found`);
  return null;
}

export function loadOverlayConfig(overlayPath: string): OverlayConfig {
  const configPath = path.join(overlayPath, "overlay.yaml");
  const parsed = parseSimpleYaml(fs.readFileSync(configPath, "utf-8"));
  const settingsMerge = parsed.settings_merge;
  const devTypes = parsed.dev_types;

  return {
    name: getRequiredString(parsed, "name"),
    version: getRequiredString(parsed, "version"),
    description:
      typeof parsed.description === "string" ? parsed.description : undefined,
    compatible_upstream: getRequiredString(parsed, "compatible_upstream"),
    author: typeof parsed.author === "string" ? parsed.author : undefined,
    settings_merge:
      settingsMerge &&
      !Array.isArray(settingsMerge) &&
      typeof settingsMerge === "object"
        ? settingsMerge
        : undefined,
    dev_types: Array.isArray(devTypes) ? devTypes : undefined,
  };
}

export function loadExcludeList(overlayPath: string): string[] {
  const excludePath = path.join(overlayPath, "exclude.yaml");
  if (!fs.existsSync(excludePath)) {
    return [];
  }

  const parsed = parseSimpleYaml(fs.readFileSync(excludePath, "utf-8"));
  return Array.isArray(parsed.exclude) ? parsed.exclude : [];
}

export function getOverlayTemplatePath(
  overlayPath: string,
  platform: string,
): string | null {
  const templatePath = path.join(overlayPath, "templates", platform);
  if (fs.existsSync(templatePath) && fs.statSync(templatePath).isDirectory()) {
    return templatePath;
  }
  return null;
}

export function readOverlayFiles(dirPath: string): Map<string, string> {
  const files = new Map<string, string>();

  function walk(currentDir: string): void {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name === "__pycache__") {
        continue;
      }

      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.isFile()) {
        files.set(
          toPosixRelative(dirPath, fullPath),
          fs.readFileSync(fullPath, "utf-8"),
        );
      }
    }
  }

  if (fs.existsSync(dirPath)) {
    walk(dirPath);
  }

  return files;
}

export function mergeSettings(
  baseContent: string,
  overlaySettingsPath: string,
): string {
  const parsedBase = JSON.parse(baseContent) as unknown;
  const parsedOverlay = JSON.parse(
    resolvePlaceholders(fs.readFileSync(overlaySettingsPath, "utf-8")),
  ) as unknown;

  const base = isJsonObject(parsedBase) ? parsedBase : {};
  const overlay = isJsonObject(parsedOverlay) ? parsedOverlay : {};

  const baseHooks = ensureObject(base, "hooks");
  const baseEnv = ensureObject(base, "env");
  const basePermissions = ensureObject(base, "permissions");

  const overlayEnv = overlay.env;
  if (isJsonObject(overlayEnv)) {
    base.env = { ...baseEnv, ...overlayEnv };
  }

  const overlayPermissions = overlay.permissions;
  if (isJsonObject(overlayPermissions)) {
    for (const [key, value] of Object.entries(overlayPermissions)) {
      if (key !== "deny") {
        basePermissions[key] = value;
      }
    }

    const baseDeny = Array.isArray(basePermissions.deny)
      ? basePermissions.deny
      : [];
    const overlayDeny = Array.isArray(overlayPermissions.deny)
      ? overlayPermissions.deny
      : [];
    if (overlayDeny.length > 0) {
      basePermissions.deny = [
        ...new Set(
          [...baseDeny, ...overlayDeny].filter(
            (value): value is string => typeof value === "string",
          ),
        ),
      ];
    }
  }

  const overlayHooks = overlay.hooks;
  if (isJsonObject(overlayHooks)) {
    for (const [event, overlayMatchers] of Object.entries(overlayHooks)) {
      if (!Array.isArray(overlayMatchers)) {
        continue;
      }

      const baseEvent = baseHooks[event];
      if (!Array.isArray(baseEvent)) {
        baseHooks[event] = [...overlayMatchers];
        continue;
      }

      for (const overlayEntry of overlayMatchers) {
        const overlayMatcher = getMatcher(overlayEntry);
        const existingIndex =
          overlayMatcher === null
            ? -1
            : baseEvent.findIndex(
                (entry) => getMatcher(entry) === overlayMatcher,
              );

        if (existingIndex >= 0) {
          baseEvent[existingIndex] = overlayEntry;
        } else {
          baseEvent.push(overlayEntry);
        }
      }
    }
  }

  for (const [key, value] of Object.entries(overlay)) {
    if (key !== "hooks" && key !== "env" && key !== "permissions") {
      base[key] = value;
    }
  }

  return JSON.stringify(base, null, 2);
}
