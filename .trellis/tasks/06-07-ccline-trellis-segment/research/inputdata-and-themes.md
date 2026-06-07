# Research: CCometixLine InputData Structure & Theme System

- **Query**: InputData struct, deserialization, extensibility, theme system, Powerline renderer
- **Scope**: internal (~/github/CCometixLine)
- **Date**: 2026-06-07

## 1. InputData Structure

### Definition

File: `src/config/types.rs:114-120`

```rust
#[derive(Deserialize)]
pub struct InputData {
    pub model: Model,
    pub workspace: Workspace,
    pub transcript_path: String,
    pub cost: Option<Cost>,
    pub output_style: Option<OutputStyle>,
}
```

### Nested Types

**Model** (`src/config/types.rs:89-92`):
```rust
#[derive(Deserialize)]
pub struct Model {
    pub id: String,
    pub display_name: String,
}
```

**Workspace** (`src/config/types.rs:94-97`):
```rust
#[derive(Deserialize)]
pub struct Workspace {
    pub current_dir: String,
}
```

**Cost** (`src/config/types.rs:99-106`) — all fields Optional:
```rust
#[derive(Deserialize)]
pub struct Cost {
    pub total_cost_usd: Option<f64>,
    pub total_duration_ms: Option<u64>,
    pub total_api_duration_ms: Option<u64>,
    pub total_lines_added: Option<u32>,
    pub total_lines_removed: Option<u32>,
}
```

**OutputStyle** (`src/config/types.rs:108-111`):
```rust
#[derive(Deserialize)]
pub struct OutputStyle {
    pub name: String,
}
```

### Complete Field Map

| Field Path | Type | Required | Source |
|---|---|---|---|
| `model.id` | `String` | yes | Claude Code sends the model API ID (e.g. `claude-opus-4-20250514[1m]`) |
| `model.display_name` | `String` | yes | Upstream display name from Claude Code |
| `workspace.current_dir` | `String` | yes | Absolute path to the workspace root |
| `transcript_path` | `String` | yes | Absolute path to the active `.jsonl` transcript file |
| `cost` | `Option<Cost>` | no | Session cost/duration metrics |
| `cost.total_cost_usd` | `Option<f64>` | no | Cumulative API cost in USD |
| `cost.total_duration_ms` | `Option<u64>` | no | Wall-clock session duration |
| `cost.total_api_duration_ms` | `Option<u64>` | no | Time spent in API calls |
| `cost.total_lines_added` | `Option<u32>` | no | Lines added in session |
| `cost.total_lines_removed` | `Option<u32>` | no | Lines removed in session |
| `output_style` | `Option<OutputStyle>` | no | Active output style |
| `output_style.name` | `String` | yes (within) | Name of the output style |

## 2. Deserialization Details

### How It's Read

File: `src/main.rs:64-65`
```rust
let stdin = io::stdin();
let input: InputData = serde_json::from_reader(stdin.lock())?;
```

Claude Code pipes a single JSON object to ccline's stdin. The binary reads it with `serde_json::from_reader`.

### Serde Attributes

- InputData uses **only** `#[derive(Deserialize)]` — no `Serialize`, no rename attributes, no `deny_unknown_fields`.
- All nested types also use plain `#[derive(Deserialize)]`.
- The `Cost` and `OutputStyle` fields are `Option<T>`, so they can be absent from the JSON.

### Key Implication: Extensibility via serde Default Behavior

Since InputData does **NOT** use `#[serde(deny_unknown_fields)]`, Claude Code (or any caller) can send extra JSON fields and they will be silently ignored. This means:
- **Adding new optional fields to InputData is backward-compatible** — old callers that don't send them just get `None`.
- **Callers can send extra fields** that ccline doesn't know about — serde ignores them.
- **However**, there is no `#[serde(flatten)]` catch-all on InputData itself, so unknown fields are truly discarded, not captured.

### Contrast with RawUsage

`RawUsage` (`src/config/types.rs:132-182`) demonstrates the pattern for capturing unknown fields:
```rust
#[serde(flatten, skip_serializing)]
pub extra: HashMap<String, serde_json::Value>,
```
InputData does NOT have this — extra fields are lost.

## 3. Extensibility Assessment

### Can InputData Be Extended with Custom Fields?

**Yes, by modifying the struct.** The recommended pattern:

1. Add `Option<T>` fields with `#[serde(default)]` for backward compat.
2. Alternatively, add a `#[serde(flatten)] pub extra: HashMap<String, serde_json::Value>` to capture arbitrary data.

### Is the Workspace Path the Main Entry Point for External Data?

**Yes.** `workspace.current_dir` is the primary entry point for file-system-based data:
- `DirectorySegment` (`src/core/segments/directory.rs:41`) extracts the directory name from `input.workspace.current_dir`.
- `GitSegment` (`src/core/segments/git.rs:176`) runs `git` commands using `input.workspace.current_dir` as the working directory.
- `ContextWindowSegment` (`src/core/segments/context_window.rs:28`) reads the transcript file from `input.transcript_path` (which is also a file path derived from the workspace).

A new segment wanting Trellis data would use `input.workspace.current_dir` to locate `.trellis/` files on disk. No InputData extension is strictly required — the segment can read the filesystem at `workspace.current_dir`.

### Segment Trait Interface

File: `src/core/segments/mod.rs:15-18`
```rust
pub trait Segment {
    fn collect(&self, input: &InputData) -> Option<SegmentData>;
    fn id(&self) -> SegmentId;
}
```

Every segment receives the full `InputData` reference. Segments that don't need stdin fields (like `UsageSegment` and `UpdateSegment`) simply ignore the `input` parameter (`_input`) and read data from the filesystem or network.

### SegmentData Output

File: `src/core/segments/mod.rs:20-25`
```rust
#[derive(Debug, Clone)]
pub struct SegmentData {
    pub primary: String,       // Main display text
    pub secondary: String,     // Additional text (e.g., git status indicators)
    pub metadata: HashMap<String, String>,  // Key-value metadata
}
```

The `metadata` field supports `dynamic_icon` — if a segment puts `"dynamic_icon"` in metadata, the renderer uses it instead of the static icon from config (`src/core/statusline.rs:217-221`).

## 4. Theme System

### Architecture Overview

Themes are defined as **hardcoded Rust functions** that return a `Config` struct. Each theme module (e.g., `theme_powerline_dark.rs`) exports one function per segment type, each returning a `SegmentConfig` with colors, icons, and options.

### Config Structure

```rust
pub struct Config {
    pub style: StyleConfig,       // mode + separator
    pub segments: Vec<SegmentConfig>,  // ordered list of segments
    pub theme: String,            // theme name string
}
```

### StyleMode Enum

File: `src/config/types.rs:20-26`
```rust
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StyleMode {
    Plain,      // Uses plain text icons (emoji)
    NerdFont,   // Uses Nerd Font glyphs
    Powerline,  // Uses Nerd Font glyphs (same as NerdFont currently)
}
```

### SegmentConfig (per-segment theme data)

```rust
pub struct SegmentConfig {
    pub id: SegmentId,
    pub enabled: bool,
    pub icon: IconConfig,       // { plain: String, nerd_font: String }
    pub colors: ColorConfig,    // { icon: Option<AnsiColor>, text: Option<AnsiColor>, background: Option<AnsiColor> }
    pub styles: TextStyleConfig, // { text_bold: bool }
    pub options: HashMap<String, serde_json::Value>,  // segment-specific options
}
```

### AnsiColor Enum (how colors are specified)

File: `src/config/types.rs:56-62`
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum AnsiColor {
    Color16 { c16: u8 },       // Standard 16 colors (0-15)
    Color256 { c256: u8 },     // 256-color palette
    Rgb { r: u8, g: u8, b: u8 }, // True color RGB
}
```

The `#[serde(untagged)]` attribute means serde tries each variant in order during deserialization, matching based on which fields are present (`c16`, `c256`, or `r`/`g`/`b`).

### Theme Preset System

File: `src/ui/themes/presets.rs`

**ThemePresets** (`struct ThemePresets`) is the central dispatcher:

```rust
impl ThemePresets {
    pub fn get_theme(theme_name: &str) -> Config {
        // 1. Try loading from ~/.claude/ccline/themes/<name>.toml
        if let Ok(config) = Self::load_theme_from_file(theme_name) {
            return config;
        }
        // 2. Fall back to built-in Rust functions
        match theme_name {
            "cometix" => Self::get_cometix(),
            "default" => Self::get_default(),
            // ... 7 more built-in themes
            _ => Self::get_default(),
        }
    }
}
```

### Built-in Theme List (9 themes)

| Theme Name | StyleMode | Separator | Background Colors |
|---|---|---|---|
| `cometix` | NerdFont | ` \| ` | None (transparent) |
| `default` | Plain | ` \| ` | None (transparent) |
| `minimal` | Plain | ` │ ` | None (transparent) |
| `gruvbox` | NerdFont | ` \| ` | None (transparent) |
| `nord` | NerdFont | `` (Powerline arrow U+E0B0) | Has background colors |
| `powerline-dark` | NerdFont | `` (Powerline arrow U+E0B0) | Has background colors (dark palette) |
| `powerline-light` | NerdFont | `` (Powerline arrow U+E0B0) | Has background colors (light palette) |
| `powerline-rose-pine` | NerdFont | `` (Powerline arrow U+E0B0) | Has background colors (Rose Pine palette) |
| `powerline-tokyo-night` | NerdFont | `` (Powerline arrow U+E0B0) | Has background colors (Tokyo Night palette) |

### Custom Themes

Custom themes are TOML files stored at `~/.claude/ccline/themes/<name>.toml`.

- The `load_theme_from_file()` method tries to load a TOML file **before** falling back to built-in themes.
- Users can save custom themes via `ThemePresets::save_theme()` which serializes a `Config` to TOML.
- `list_available_themes()` merges built-in names with `.toml` files found in the themes directory.

### How Themes Override Colors

Each theme module defines segment factory functions (e.g., `model_segment() -> SegmentConfig`) that hardcode the full `ColorConfig`:
- **Non-Powerline themes** (default, minimal, cometix, gruvbox): Set `icon` and `text` colors but leave `background: None`.
- **Powerline themes** (powerline-dark, powerline-light, rose-pine, tokyo-night, nord): Set all three — `icon`, `text`, AND `background` — because the Powerline arrow renderer needs background colors for proper fg/bg transitions.

### Theme Detection / Comparison

`Config::matches_theme()` (`src/config/types.rs:243-267`) compares the current config against a named theme preset field-by-field (style mode, separator, segment count, segment order, colors, icons, options). `Config::is_modified_from_theme()` returns true if the current config no longer matches its declared theme.

## 5. Powerline Renderer — Segment Transition Logic

### Entry Point

File: `src/core/statusline.rs:59-66`

The `generate()` method checks if the separator is the Powerline arrow character (U+E0B0 ``):
```rust
if self.config.style.separator == "\u{e0b0}" {
    self.join_with_powerline_arrows(&output, &enabled_segments)
} else {
    self.join_with_white_separators(&output)
}
```

### Powerline Arrow Join

File: `src/core/statusline.rs:371-404`

`join_with_powerline_arrows()` iterates through rendered segments and inserts color-transitioning arrows between them:

```rust
fn join_with_powerline_arrows(&self, rendered_segments: &[String], segment_configs: &[(SegmentConfig, SegmentData)]) -> String {
    let mut result = rendered_segments[0].clone();
    for (i, _) in rendered_segments.iter().enumerate().skip(1) {
        let prev_bg = segment_configs.get(i - 1).and_then(|(config, _)| config.colors.background.as_ref());
        let curr_bg = segment_configs.get(i).and_then(|(config, _)| config.colors.background.as_ref());
        let arrow = self.create_powerline_arrow(prev_bg, curr_bg);
        result.push_str(&arrow);
        result.push_str(&rendered_segments[i]);
    }
    result.push_str("\x1b[0m"); // Reset at end
    result
}
```

### Arrow Color Transition Logic

File: `src/core/statusline.rs:407-437`

`create_powerline_arrow()` implements the classic Powerline fg/bg handoff:

```rust
fn create_powerline_arrow(&self, prev_bg: Option<&AnsiColor>, curr_bg: Option<&AnsiColor>) -> String {
    let arrow_char = "\u{e0b0}";
    match (prev_bg, curr_bg) {
        (Some(prev), Some(curr)) => {
            // Arrow fg = previous segment's bg color
            // Arrow bg = current segment's bg color
            let fg_code = self.color_to_foreground_code(prev);
            let bg_code = self.apply_background_color(curr);
            format!("{}{}{}\x1b[0m", bg_code, fg_code, arrow_char)
        }
        (Some(prev), None) => {
            // Previous has bg, current doesn't — arrow shows prev color fading out
            let fg_code = self.color_to_foreground_code(prev);
            format!("{}{}\x1b[0m", fg_code, arrow_char)
        }
        (None, Some(curr)) => {
            // Current has bg, previous doesn't — arrow shows curr color appearing
            let bg_code = self.apply_background_color(curr);
            format!("{}{}\x1b[0m", bg_code, arrow_char)
        }
        (None, None) => {
            // Neither has bg — plain arrow
            arrow_char.to_string()
        }
    }
}
```

### Segment Rendering

File: `src/core/statusline.rs:216-282`

`render_segment()` applies colors based on whether a background is set:
- **With background**: Wraps entire content in `\x1b[48;...m` (bg code), strips internal `\x1b[0m` resets to keep bg continuous, resets bg only at end with `\x1b[49m`.
- **Without background**: Standard foreground-only coloring with normal resets.

Format: ` <icon> <primary_text> [<secondary_text>] ` (padded with spaces when bg is set).

### Non-Powerline Join

File: `src/core/statusline.rs:360-368`

For non-Powerline separators, segments are joined with a white-colored separator:
```rust
let white_separator = format!("\x1b[37m{}\x1b[0m", self.config.style.separator);
rendered_segments.join(&white_separator)
```

## 6. Segment Registration

### SegmentId Enum

File: `src/config/types.rs:64-76`
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

### Segment Dispatch

File: `src/core/statusline.rs:456-520`

`collect_all_segments()` iterates through `config.segments` and dispatches by `SegmentId`:
```rust
let segment_data = match segment_config.id {
    SegmentId::Model => ModelSegment::new().collect(input),
    SegmentId::Directory => DirectorySegment::new().collect(input),
    SegmentId::Git => { /* with options */ },
    SegmentId::ContextWindow => ContextWindowSegment::new().collect(input),
    SegmentId::Usage => UsageSegment::new().collect(input),
    SegmentId::Cost => CostSegment::new().collect(input),
    SegmentId::Session => SessionSegment::new().collect(input),
    SegmentId::OutputStyle => OutputStyleSegment::new().collect(input),
    SegmentId::Update => UpdateSegment::new().collect(input),
};
```

Adding a new segment requires:
1. Add a variant to `SegmentId` enum
2. Create a new segment struct implementing `Segment` trait
3. Add a match arm in `collect_all_segments()`
4. Add segment config entries in each theme module

## Caveats / Notes

- There is no `ThemePreset` enum — the term in the task refers to the `ThemePresets` struct (a namespace for static methods), not an enum. Theme selection is string-based.
- The `Powerline` StyleMode variant is currently identical to `NerdFont` — the comment says "Future: use Powerline icons" (`src/core/statusline.rs:288`).
- `Config` derives both `Serialize` and `Deserialize`, but `InputData` is `Deserialize` only — it flows one-way from Claude Code into ccline.
- The `Update` segment is in the `SegmentId` enum and dispatch table but is NOT included in any theme preset's segment list — it appears to be added programmatically or via custom config.
