# Research: CCometixLine Config System

- **Query**: Full config system — structs, TOML mapping, defaults, segment options, model config
- **Scope**: internal (~/github/CCometixLine)
- **Date**: 2026-06-07

## Architecture Overview

The config system lives in `src/config/` with 5 files. Default generation delegates to `src/ui/themes/presets.rs` which assembles `Config` from per-theme segment builder functions. Config is serialized/deserialized to TOML via serde.

**Config file location**: `~/.claude/ccline/config.toml`
**Theme files location**: `~/.claude/ccline/themes/{name}.toml`
**Model config location**: `~/.claude/ccline/models.toml`

## Files Found

| File Path | Description |
|---|---|
| `src/config/types.rs` | All core type definitions: Config, SegmentConfig, SegmentId, AnsiColor, ColorConfig, IconConfig, TextStyleConfig, StyleConfig, StyleMode, plus input/usage data types |
| `src/config/models.rs` | ModelConfig, ModelEntry, ContextModifier, BuiltinModelFamily — model display name resolution and context limits |
| `src/config/defaults.rs` | `impl Default for Config` — delegates to `ThemePresets::get_default()` |
| `src/config/loader.rs` | ConfigLoader, Config::load/save/init/check/print — file I/O and theme initialization |
| `src/config/mod.rs` | Module re-exports |
| `src/ui/themes/presets.rs` | ThemePresets — orchestrates all built-in themes, file-based theme loading/saving |
| `src/ui/themes/theme_default.rs` | Default theme segment builders (representative example) |
| `src/core/statusline.rs:470-512` | Segment dispatch — reads `options` from SegmentConfig per segment ID |
| `src/core/segments/git.rs` | GitSegment — consumes `show_sha` option |
| `src/core/segments/usage.rs:183-220` | UsageSegment — consumes `api_base_url`, `cache_duration`, `timeout` options |
| `src/main.rs` | Entry point — loads config, applies theme override, pipes to statusline |
| `src/cli.rs` | CLI args: `--config` (TUI), `--theme <name>`, `--patch <path>` |

## 1. Config Struct (types.rs:6-10)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub style: StyleConfig,
    pub segments: Vec<SegmentConfig>,
    pub theme: String,
}
```

### StyleConfig (types.rs:14-18)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StyleConfig {
    pub mode: StyleMode,
    pub separator: String,
}
```

### StyleMode (types.rs:20-26)

```rust
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StyleMode {
    Plain,
    NerdFont,
    Powerline,
}
```

### TOML Mapping

```toml
theme = "default"

[style]
mode = "nerd_font"          # snake_case via serde rename_all
separator = " | "

[[segments]]                # Vec<SegmentConfig> maps to TOML array of tables
id = "model"
enabled = true
# ...
```

### Config Methods (loader.rs:114-200)

- `Config::load()` — loads from `~/.claude/ccline/config.toml`, ensures themes exist, falls back to `Config::default()`
- `Config::save()` — serializes to TOML pretty format, writes to default path
- `Config::init()` — creates dir + themes + default config, returns `InitResult::Created` or `AlreadyExists`
- `Config::check()` — validates non-empty segments, unique segment IDs
- `Config::print()` — dumps TOML to stdout
- `Config::matches_theme(&self, theme_name)` — deep comparison against theme preset
- `Config::is_modified_from_theme(&self)` — checks if user customized from selected theme

## 2. SegmentConfig Struct (types.rs:28-36)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SegmentConfig {
    pub id: SegmentId,
    pub enabled: bool,
    pub icon: IconConfig,
    pub colors: ColorConfig,
    pub styles: TextStyleConfig,
    pub options: HashMap<String, serde_json::Value>,
}
```

### Sub-types

**IconConfig** (types.rs:38-42):
```rust
pub struct IconConfig {
    pub plain: String,       // emoji fallback
    pub nerd_font: String,   // nerd font glyph
}
```

**ColorConfig** (types.rs:44-49):
```rust
pub struct ColorConfig {
    pub icon: Option<AnsiColor>,
    pub text: Option<AnsiColor>,
    pub background: Option<AnsiColor>,
}
```

**TextStyleConfig** (types.rs:51-54):
```rust
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TextStyleConfig {
    pub text_bold: bool,
}
```

**AnsiColor** (types.rs:56-62) — untagged serde enum:
```rust
#[serde(untagged)]
pub enum AnsiColor {
    Color16 { c16: u8 },
    Color256 { c256: u8 },
    Rgb { r: u8, g: u8, b: u8 },
}
```

TOML examples:
```toml
[segments.colors.icon]
c16 = 14                    # Color16 variant

[segments.colors.background]
c256 = 237                  # Color256 variant

[segments.colors.text]
r = 255                     # Rgb variant
g = 128
b = 0
```

### SegmentId Enum (types.rs:64-76)

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SegmentId {
    Model,
    Directory,
    Git,
    ContextWindow,
    Usage,
    Cost,
    Session,
    OutputStyle,
    Update,
}
```

Serializes as: `"model"`, `"directory"`, `"git"`, `"context_window"`, `"usage"`, `"cost"`, `"session"`, `"output_style"`, `"update"`.

## 3. Default Config Generation

### Flow

1. `Config::default()` (defaults.rs:6-10) calls `ThemePresets::get_default()`
2. `ThemePresets::get_default()` (presets.rs:145-163) assembles a `Config` with:
   - `style: { mode: Plain, separator: " | " }`
   - `theme: "default"`
   - 8 segments built by `theme_default::*_segment()` functions
3. Each theme module (e.g., `theme_default.rs`) exports per-segment builder functions like `model_segment()`, `git_segment()`, etc.

### Init Flow (Config::init, loader.rs:155-174)

1. Creates `~/.claude/ccline/` directory
2. Calls `ConfigLoader::init_themes()` which creates `~/.claude/ccline/themes/` and writes all 9 built-in themes as TOML files
3. If `config.toml` doesn't exist, serializes `Config::default()` and writes it

### Theme Loading Priority (presets.rs:14-33)

1. Try loading from file: `~/.claude/ccline/themes/{name}.toml`
2. Fallback to built-in Rust code (match on theme name)
3. Unknown theme name falls back to `get_default()`

### Available Built-in Themes

`cometix`, `default`, `minimal`, `gruvbox`, `nord`, `powerline-dark`, `powerline-light`, `powerline-rose-pine`, `powerline-tokyo-night`

## 4. Segment-Specific Options

The `options: HashMap<String, serde_json::Value>` field is a generic key-value bag. Each segment reads its own keys at runtime.

### Git Segment Options

| Key | Type | Default | Consumed At |
|---|---|---|---|
| `show_sha` | bool | `false` | `statusline.rs:480-484` — passed to `GitSegment::with_sha()` |

**Dispatch code** (statusline.rs:479-486):
```rust
SegmentId::Git => {
    let show_sha = segment_config
        .options
        .get("show_sha")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let segment = GitSegment::new().with_sha(show_sha);
    segment.collect(input)
}
```

### Usage Segment Options

| Key | Type | Default | Consumed At |
|---|---|---|---|
| `api_base_url` | string | `"https://api.anthropic.com"` | `usage.rs:191-194` |
| `cache_duration` | u64 | `300` (note: default theme sets `180`) | `usage.rs:196-199` |
| `timeout` | u64 | `2` | `usage.rs:201-204` |

**Consumption pattern** (usage.rs:187-204):
```rust
let config = crate::config::Config::load().ok()?;
let segment_config = config.segments.iter().find(|s| s.id == SegmentId::Usage);

let api_base_url = segment_config
    .and_then(|sc| sc.options.get("api_base_url"))
    .and_then(|v| v.as_str())
    .unwrap_or("https://api.anthropic.com");
```

### Other Segments

All other segments (Model, Directory, ContextWindow, Cost, Session, OutputStyle, Update) use `options: HashMap::new()` in their defaults and do not read any options at runtime. The `options` field is present but unused for them.

### Options Pattern Summary

Two patterns exist for reading options:
1. **Statusline dispatch** (Git): options are read in `statusline.rs` during segment dispatch and passed as constructor arguments
2. **Self-load** (Usage): the segment loads the full config itself and reads its own options

## 5. ModelConfig (models.rs:7-13)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    #[serde(rename = "models", default)]
    pub model_entries: Vec<ModelEntry>,
    #[serde(default)]
    pub context_modifiers: Vec<ContextModifier>,
}
```

### ModelEntry (models.rs:15-20)

```rust
pub struct ModelEntry {
    pub pattern: String,        // substring match against model ID
    pub display_name: String,   // human-readable name
    pub context_limit: u32,     // context window size
}
```

### ContextModifier (models.rs:24-29)

```rust
pub struct ContextModifier {
    pub pattern: String,        // e.g., "[1m]"
    pub display_suffix: String, // e.g., " 1M"
    pub context_limit: u32,     // overrides base limit
}
```

### Model Resolution (models.rs:180-217)

Three-layer resolution via `ModelConfig::resolve()`:
1. **User model entries** — simple substring match (highest priority for display name)
2. **Built-in Claude families** — regex-based version extraction for Sonnet/Opus/Haiku
3. **Context modifiers** — matched independently, override context limit

### Default ModelConfig (models.rs:296-329)

Built-in entries: `GLM-4.5` (128k), `Kimi K2 Turbo` (128k), `Kimi K2` (128k), `Qwen Coder` (256k).
Built-in modifier: `[1m]` -> " 1M" suffix, 1M context limit.
Claude models (Sonnet/Opus/Haiku) are handled by `BuiltinModelFamily` regex, not explicit entries.

### ModelConfig File

Location: `~/.claude/ccline/models.toml`
Auto-created on first `ModelConfig::load()` if missing. Contains commented-out examples.

TOML format:
```toml
[[models]]
pattern = "my-model"
display_name = "My Model"
context_limit = 128000

[[context_modifiers]]
pattern = "[1m]"
display_suffix = " 1M"
context_limit = 1000000
```

## 6. Other Config Types (types.rs)

### Input Data Types (not user-configurable)

| Struct | Purpose |
|---|---|
| `InputData` | Top-level stdin JSON from Claude Code: model, workspace, transcript_path, cost, output_style |
| `Model` | `{ id, display_name }` |
| `Workspace` | `{ current_dir }` |
| `Cost` | `{ total_cost_usd, total_duration_ms, total_api_duration_ms, total_lines_added, total_lines_removed }` |
| `OutputStyle` | `{ name }` |

### Usage Types (not user-configurable)

| Struct | Purpose |
|---|---|
| `RawUsage` | Flexible parsing for both Anthropic and OpenAI token formats, with `#[serde(flatten)]` for unknown fields |
| `NormalizedUsage` | Unified representation after `RawUsage::normalize()` |
| `PromptTokensDetails` | OpenAI nested token details |
| `Message` | `{ usage: Option<Usage> }` |
| `TranscriptEntry` | `{ type, message, leafUuid, uuid, parentUuid, summary }` |

### Legacy Types

| Struct | Purpose |
|---|---|
| `SegmentsConfig` | Legacy `{ directory: bool, git: bool, model: bool }` — backward compat only |

## TOML Config Example (actual ~/.claude/ccline/config.toml)

```toml
theme = "MyStyle"

[style]
mode = "nerd_font"
separator = " | "

[[segments]]
id = "model"
enabled = true

[segments.icon]
plain = "🤖"
nerd_font = ""

[segments.colors.icon]
c16 = 14

[segments.colors.text]
c16 = 14

[segments.styles]
text_bold = true

[segments.options]

[[segments]]
id = "git"
enabled = true

[segments.icon]
plain = "🌿"
nerd_font = "󰊢"

[segments.colors.icon]
c16 = 12

[segments.colors.text]
c16 = 12

[segments.styles]
text_bold = true

[segments.options]
show_sha = false

[[segments]]
id = "usage"
enabled = true
# ...
[segments.options]
timeout = 2
api_base_url = "https://api.anthropic.com"
cache_duration = 180
```

## Caveats / Notes

- The `Update` variant exists in `SegmentId` but no theme includes it by default — it is dispatched in `statusline.rs:508-511` but has no options.
- `SegmentsConfig` (legacy) at types.rs:79-85 is kept for backward compat but appears unused in current flow.
- Usage segment has a subtle default mismatch: code default is `300` for `cache_duration` but theme default sets `180`.
- The `options` field uses `serde_json::Value` as the value type, making it fully dynamic — any JSON-compatible value can be stored. This is the extension point for new segment-specific settings.
- `background` color is defined in `ColorConfig` but powerline themes are the only ones that use it (plain/nerd_font themes leave it `None`).
