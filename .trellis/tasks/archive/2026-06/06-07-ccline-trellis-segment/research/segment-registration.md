# Research: CCometixLine Segment Registration and Collection Mechanism

- **Query**: How segments are instantiated, collected, rendered, and ordered in CCometixLine
- **Scope**: internal
- **Date**: 2026-06-07

## Findings

### Files Found

| File Path | Description |
|---|---|
| `src/core/segments/mod.rs` | `Segment` trait definition + `SegmentData` struct + re-exports of all segment types |
| `src/core/statusline.rs` | `StatusLineGenerator` (rendering) + `collect_all_segments()` (collection/dispatch) |
| `src/core/mod.rs` | Re-exports `collect_all_segments` and `StatusLineGenerator` |
| `src/main.rs` | Entry point: stdin JSON → `collect_all_segments` → `StatusLineGenerator::generate` → stdout |
| `src/config/types.rs` | `Config`, `SegmentConfig`, `SegmentId` enum, `InputData`, `SegmentData` types |
| `src/config/defaults.rs` | `Default for Config` — delegates to `ThemePresets::get_default()` |
| `src/config/loader.rs` | `Config::load()` — reads `~/.claude/ccline/config.toml` (TOML), falls back to default |
| `src/ui/themes/presets.rs` | `ThemePresets` — defines segment order per theme as hardcoded `Vec<SegmentConfig>` |
| `src/ui/themes/theme_default.rs` | Example theme: factory functions like `model_segment()` returning `SegmentConfig` |
| `src/ui/components/preview.rs` | TUI preview: uses mock `SegmentData` + `StatusLineGenerator` for live preview |
| `src/core/segments/model.rs` | `ModelSegment` — impl `Segment` trait |
| `src/core/segments/directory.rs` | `DirectorySegment` — impl `Segment` trait |
| `src/core/segments/git.rs` | `GitSegment` — impl `Segment` trait |
| `src/core/segments/context_window.rs` | `ContextWindowSegment` — impl `Segment` trait |
| `src/core/segments/usage.rs` | `UsageSegment` — impl `Segment` trait |
| `src/core/segments/cost.rs` | `CostSegment` — impl `Segment` trait |
| `src/core/segments/session.rs` | `SessionSegment` — impl `Segment` trait |
| `src/core/segments/output_style.rs` | `OutputStyleSegment` — impl `Segment` trait |
| `src/core/segments/update.rs` | `UpdateSegment` — impl `Segment` trait |

---

### 1. Segment Trait and Data Model

**File**: `src/core/segments/mod.rs:14-25`

```rust
pub trait Segment {
    fn collect(&self, input: &InputData) -> Option<SegmentData>;
    fn id(&self) -> SegmentId;
}

#[derive(Debug, Clone)]
pub struct SegmentData {
    pub primary: String,      // main display text
    pub secondary: String,    // auxiliary text (e.g., git status symbols)
    pub metadata: HashMap<String, String>,  // key-value bag for dynamic icon etc.
}
```

Each segment struct (e.g., `ModelSegment`, `GitSegment`) implements this trait. The `collect()` method receives `InputData` (deserialized from stdin JSON) and returns `Option<SegmentData>` — `None` means "skip this segment."

**SegmentId enum** (`src/config/types.rs:64-76`):
```rust
pub enum SegmentId {
    Model, Directory, Git, ContextWindow,
    Usage, Cost, Session, OutputStyle, Update,
}
```

Nine variants total. Every segment has exactly one `SegmentId`.

---

### 2. Segment Instantiation — `collect_all_segments()`

**File**: `src/core/statusline.rs:456-520`

This is the **sole dispatch point** — a free function, not a method on `StatusLineGenerator`:

```rust
pub fn collect_all_segments(
    config: &Config,
    input: &crate::config::InputData,
) -> Vec<(SegmentConfig, SegmentData)> {
    let mut results = Vec::new();

    for segment_config in &config.segments {
        if !segment_config.enabled { continue; }

        let segment_data = match segment_config.id {
            SegmentId::Model        => ModelSegment::new().collect(input),
            SegmentId::Directory    => DirectorySegment::new().collect(input),
            SegmentId::Git          => {
                let show_sha = segment_config.options
                    .get("show_sha").and_then(|v| v.as_bool()).unwrap_or(false);
                GitSegment::new().with_sha(show_sha).collect(input)
            },
            SegmentId::ContextWindow => ContextWindowSegment::new().collect(input),
            SegmentId::Usage         => UsageSegment::new().collect(input),
            SegmentId::Cost          => CostSegment::new().collect(input),
            SegmentId::Session       => SessionSegment::new().collect(input),
            SegmentId::OutputStyle   => OutputStyleSegment::new().collect(input),
            SegmentId::Update        => UpdateSegment::new().collect(input),
        };

        if let Some(data) = segment_data {
            results.push((segment_config.clone(), data));
        }
    }
    results
}
```

**Key observations**:
- **No trait-object registry / dynamic dispatch** — segments are matched via a `match` on `SegmentId` and instantiated inline.
- Segment structs are **stateless** (created via `::new()` per call), except `GitSegment` which accepts a builder-style `.with_sha()`.
- Segment-specific options (like `show_sha`) are extracted from `segment_config.options: HashMap<String, serde_json::Value>`.
- The `config.segments` vec is iterated **in order** — ordering comes from the config, not from the match arms.
- Disabled segments (`enabled: false`) are skipped **before** instantiation — no `collect()` call, no API cost.

---

### 3. Full Rendering Pipeline

#### Entry Point (`src/main.rs:63-74`)

```
stdin (JSON) → serde_json::from_reader → InputData
                                           ↓
Config::load() → Config (from TOML or default theme)
                                           ↓
collect_all_segments(&config, &input) → Vec<(SegmentConfig, SegmentData)>
                                           ↓
StatusLineGenerator::new(config).generate(segments) → String (ANSI)
                                           ↓
println!("{}", statusline) → stdout
```

#### Step-by-step:

1. **InputData arrives via stdin as JSON**:
   ```rust
   let input: InputData = serde_json::from_reader(stdin.lock())?;
   ```
   The `InputData` struct contains: `model` (id, display_name), `workspace` (current_dir), `transcript_path`, optional `cost`, optional `output_style`.

2. **Config loads from `~/.claude/ccline/config.toml`** (TOML format):
   ```rust
   let mut config = Config::load().unwrap_or_else(|_| Config::default());
   ```
   Falls back to `Config::default()` which delegates to `ThemePresets::get_default()`.

3. **Collection phase** — `collect_all_segments()`:
   - Iterates `config.segments` in order
   - Skips disabled segments
   - Dispatches to the correct segment struct via `match` on `SegmentId`
   - Each segment's `collect()` reads from `InputData` and/or external sources (git CLI, Anthropic API, filesystem)
   - Returns `Vec<(SegmentConfig, SegmentData)>` preserving config order

4. **Rendering phase** — `StatusLineGenerator::generate()`:

   **File**: `src/core/statusline.rs:40-66`
   ```rust
   pub fn generate(&self, segments: Vec<(SegmentConfig, SegmentData)>) -> String {
       // Filter to enabled segments (second pass — belt-and-suspenders)
       let enabled_segments: Vec<_> = segments.into_iter()
           .filter(|(config, _)| config.enabled).collect();

       // Render each segment: icon + primary text + optional secondary text
       for (config, data) in enabled_segments.iter() {
           let rendered = self.render_segment(config, data);
           // ... push non-empty rendered strings
       }

       // Join with separator (Powerline arrows vs. simple separator)
       if self.config.style.separator == "\u{e0b0}" {
           self.join_with_powerline_arrows(&output, &enabled_segments)
       } else {
           self.join_with_white_separators(&output)
       }
   }
   ```

5. **`render_segment()`** (`src/core/statusline.rs:216-282`):
   - Resolves icon: checks `data.metadata["dynamic_icon"]` first, falls back to `config.icon` (plain vs. nerd_font based on `StyleMode`)
   - Applies ANSI color codes: icon color, text color, optional background color
   - Formats: `" {icon_colored} {text_styled} "` (with background) or `"{icon_colored} {text_styled}"` (without)
   - Applies bold if `config.styles.text_bold == true`
   - Appends `secondary` text if non-empty

6. **Separator joining**:
   - **Powerline mode** (`\u{e0b0}`): creates color-transition arrows between segments using foreground=prev_bg, background=next_bg
   - **All other separators**: wraps separator in white ANSI color (`\x1b[37m{sep}\x1b[0m`) and joins

7. **Output**: final ANSI-escaped string printed to stdout

---

### 4. Segment Ordering

**Ordering is config-driven, not hardcoded.**

The order of segments in the output is determined by the order of elements in `config.segments: Vec<SegmentConfig>`. This vector comes from one of three sources:

#### Source A: Theme presets (hardcoded order per theme)

**File**: `src/ui/themes/presets.rs:125-143` (example: cometix theme)
```rust
segments: vec![
    theme_cometix::model_segment(),       // 1st
    theme_cometix::directory_segment(),   // 2nd
    theme_cometix::git_segment(),         // 3rd
    theme_cometix::context_window_segment(), // 4th
    theme_cometix::usage_segment(),       // 5th
    theme_cometix::cost_segment(),        // 6th
    theme_cometix::session_segment(),     // 7th
    theme_cometix::output_style_segment(), // 8th
],
```

All 9 built-in themes use the **same order**: Model → Directory → Git → ContextWindow → Usage → Cost → Session → OutputStyle. The `Update` segment is **not included** in any theme preset's segment list.

#### Source B: User config file (`~/.claude/ccline/config.toml`)

When TOML is loaded via `Config::load()`, the `segments` array order in the file directly controls rendering order. Users can reorder, remove, or add segments by editing the TOML.

#### Source C: CLI theme override

```rust
if let Some(theme) = cli.theme {
    config = ThemePresets::get_theme(&theme);
}
```

The `--theme` CLI flag replaces the entire config with a preset.

#### TUI configurator

The `PreviewComponent` in the TUI (`src/ui/components/preview.rs`) also respects config order — it iterates `config.segments` to generate mock data in the same order, then passes it to `StatusLineGenerator`.

---

### 5. Segment Implementation Patterns

Each segment follows this pattern:

```rust
#[derive(Default)]
pub struct XxxSegment;

impl XxxSegment {
    pub fn new() -> Self { Self }
}

impl Segment for XxxSegment {
    fn collect(&self, input: &InputData) -> Option<SegmentData> {
        // Extract data from InputData or external sources
        // Return None to hide this segment
        Some(SegmentData {
            primary: "...",
            secondary: "...",
            metadata: HashMap::new(),
        })
    }

    fn id(&self) -> SegmentId {
        SegmentId::Xxx
    }
}
```

**Data sources per segment**:

| Segment | Data Source | Can Return None? |
|---|---|---|
| `ModelSegment` | `input.model.id`, `input.model.display_name` + `ModelConfig` file | No (always Some) |
| `DirectorySegment` | `input.workspace.current_dir` | No (always Some) |
| `GitSegment` | `git` CLI commands (branch, status, ahead/behind, sha) | Yes (not a git repo) |
| `ContextWindowSegment` | `input.transcript_path` → parse JSONL transcript + `ModelConfig` | No (returns "-" fallback) |
| `UsageSegment` | Anthropic OAuth API (`/api/oauth/usage`) with file cache | Yes (no token / API fail) |
| `CostSegment` | `input.cost.total_cost_usd` | Yes (no cost data) |
| `SessionSegment` | `input.cost.total_duration_ms` + line counts | Yes (no duration data) |
| `OutputStyleSegment` | `input.output_style.name` | Yes (no output_style) |
| `UpdateSegment` | `UpdateState::load()` from local state file | Yes (no update available) |

### 6. Adding a New Segment — Required Touchpoints

To add a new segment to CCometixLine, these files must be modified:

1. **`src/config/types.rs`** — add variant to `SegmentId` enum
2. **`src/core/segments/`** — create new `xxx.rs` module file implementing `Segment` trait
3. **`src/core/segments/mod.rs`** — add `pub mod xxx;` and `pub use xxx::XxxSegment;`
4. **`src/core/statusline.rs`** — add `match` arm in `collect_all_segments()` for new `SegmentId`
5. **`src/ui/themes/theme_*.rs`** — add factory function `xxx_segment() -> SegmentConfig` to each theme
6. **`src/ui/themes/presets.rs`** — add the new segment call to each theme's `segments` vec
7. **`src/ui/components/preview.rs`** — add mock `SegmentData` case in `generate_mock_segments_data()` match

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│  stdin (JSON)                                                       │
│  { model, workspace, transcript_path, cost?, output_style? }       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Config::load()                                                      │
│  ~/.claude/ccline/config.toml  OR  ThemePresets::get_default()       │
│  Config { style, segments: Vec<SegmentConfig>, theme }               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  collect_all_segments(&config, &input)                               │
│                                                                      │
│  for segment_config in config.segments:                              │
│    skip if !enabled                                                  │
│    match segment_config.id {                                         │
│      Model        => ModelSegment::new().collect(input)              │
│      Directory    => DirectorySegment::new().collect(input)          │
│      Git          => GitSegment::new().with_sha(opt).collect(input)  │
│      ContextWindow => ContextWindowSegment::new().collect(input)     │
│      Usage        => UsageSegment::new().collect(input)              │
│      Cost         => CostSegment::new().collect(input)               │
│      Session      => SessionSegment::new().collect(input)            │
│      OutputStyle  => OutputStyleSegment::new().collect(input)        │
│      Update       => UpdateSegment::new().collect(input)             │
│    }                                                                 │
│    if Some(data) → push (segment_config, data)                      │
│                                                                      │
│  Returns: Vec<(SegmentConfig, SegmentData)> in config order          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  StatusLineGenerator::generate(segments)                             │
│                                                                      │
│  1. Filter enabled (second pass)                                     │
│  2. For each: render_segment(config, data)                          │
│     - resolve icon (dynamic_icon metadata > style-based icon)        │
│     - apply ANSI colors (icon, text, background)                    │
│     - format: " {icon} {primary} {secondary?} "                    │
│  3. Join with separator:                                            │
│     - Powerline (U+E0B0): color-transition arrows                   │
│     - Other: white-colored separator string                         │
│  4. Return: ANSI-escaped String                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
                     println!() → stdout
```

## Caveats / Notes

- There is **no dynamic segment registry** or plugin system. Adding a new segment requires modifying the `match` in `collect_all_segments()` and adding the `SegmentId` enum variant. This is a closed, compile-time dispatch system.
- The `Update` segment exists in the `SegmentId` enum and has an implementation, but is **not included** in any theme preset's default segment list. It can still appear if added to user config manually.
- `UsageSegment` is notable because it ignores `input` entirely (`_input`) and instead loads its own config from disk and makes HTTP requests to the Anthropic API.
- The `enabled` flag is checked **twice**: once in `collect_all_segments()` before instantiation, and once in `StatusLineGenerator::generate()` before rendering. The first check prevents unnecessary work (e.g., API calls for `UsageSegment`).
