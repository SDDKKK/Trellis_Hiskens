# Research: CCometixLine Segment Trait Interface

- **Query**: Full Segment trait definition, SegmentData struct, SegmentId enum, helper traits/macros
- **Scope**: internal (~/github/CCometixLine)
- **Date**: 2026-06-07

## Findings

### Files Found

| File Path | Description |
|---|---|
| `src/core/segments/mod.rs` | **Segment trait** + **SegmentData struct** definitions; re-exports all segment types |
| `src/config/types.rs` | **SegmentId enum** (line 66), SegmentConfig, InputData, and all supporting config types |
| `src/core/statusline.rs` | `collect_all_segments()` — the dispatch function that matches SegmentId to concrete segments |
| `src/core/segments/model.rs` | ModelSegment implementation |
| `src/core/segments/directory.rs` | DirectorySegment implementation |
| `src/core/segments/git.rs` | GitSegment implementation |
| `src/core/segments/context_window.rs` | ContextWindowSegment implementation |
| `src/core/segments/usage.rs` | UsageSegment implementation |
| `src/core/segments/cost.rs` | CostSegment implementation |
| `src/core/segments/session.rs` | SessionSegment implementation |
| `src/core/segments/output_style.rs` | OutputStyleSegment implementation |
| `src/core/segments/update.rs` | UpdateSegment implementation |
| `src/config/models.rs` | ModelConfig — model name resolution and context limits |

---

### 1. Segment Trait (`src/core/segments/mod.rs:15-18`)

```rust
pub trait Segment {
    fn collect(&self, input: &InputData) -> Option<SegmentData>;
    fn id(&self) -> SegmentId;
}
```

- **No associated types.** The trait is minimal — two methods only.
- `collect()` receives a reference to `InputData` (JSON-deserialized input from Claude Code's hook) and returns `Option<SegmentData>`. Returning `None` means "this segment has nothing to display."
- `id()` returns the `SegmentId` enum variant identifying this segment.
- The trait is **not** object-safe in the dyn-dispatch sense — it is used via exhaustive match in `collect_all_segments()` rather than trait objects.

---

### 2. SegmentData Struct (`src/core/segments/mod.rs:20-25`)

```rust
#[derive(Debug, Clone)]
pub struct SegmentData {
    pub primary: String,
    pub secondary: String,
    pub metadata: HashMap<String, String>,
}
```

| Field | Type | Purpose |
|---|---|---|
| `primary` | `String` | Main display text (e.g., branch name, model name, cost) |
| `secondary` | `String` | Secondary display text (e.g., git status icons, reset time). Can be empty. |
| `metadata` | `HashMap<String, String>` | Arbitrary key-value store. Segments stash raw data here (e.g., `"dynamic_icon"`, `"tokens"`, `"percentage"`, `"branch"`, `"model_id"`). The renderer checks `metadata.get("dynamic_icon")` to override the configured icon. |

**Derive macros**: `Debug`, `Clone` (no Serialize/Deserialize — SegmentData is internal, never serialized to disk/JSON).

---

### 3. SegmentId Enum (`src/config/types.rs:64-76`)

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

**Current variants (9)**:

| Variant | serde name | Concrete Segment Struct |
|---|---|---|
| `Model` | `model` | `ModelSegment` |
| `Directory` | `directory` | `DirectorySegment` |
| `Git` | `git` | `GitSegment` |
| `ContextWindow` | `context_window` | `ContextWindowSegment` |
| `Usage` | `usage` | `UsageSegment` |
| `Cost` | `cost` | `CostSegment` |
| `Session` | `session` | `SessionSegment` |
| `OutputStyle` | `output_style` | `OutputStyleSegment` |
| `Update` | `update` | `UpdateSegment` |

**Derive macros on SegmentId**: `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `Hash`, `Serialize`, `Deserialize`
**serde attribute**: `#[serde(rename_all = "snake_case")]` — JSON/TOML uses snake_case names.

**How to add a new variant**: Adding a new SegmentId requires changes in **3 places**:
1. Add the variant to the `SegmentId` enum in `src/config/types.rs`
2. Add a new segment file under `src/core/segments/` (e.g., `trellis.rs`) with a struct implementing `Segment`
3. Add the match arm in `collect_all_segments()` in `src/core/statusline.rs` (line 470-512)
4. Add `pub mod` + `pub use` in `src/core/segments/mod.rs`

---

### 4. Dispatch: `collect_all_segments()` (`src/core/statusline.rs:456-520`)

This function iterates `config.segments` (a `Vec<SegmentConfig>`) and dispatches to concrete segment structs via an exhaustive `match` on `segment_config.id`:

```rust
pub fn collect_all_segments(
    config: &Config,
    input: &crate::config::InputData,
) -> Vec<(SegmentConfig, SegmentData)> {
    let mut results = Vec::new();
    for segment_config in &config.segments {
        if !segment_config.enabled { continue; }
        let segment_data = match segment_config.id {
            SegmentId::Model => ModelSegment::new().collect(input),
            SegmentId::Directory => DirectorySegment::new().collect(input),
            SegmentId::Git => {
                let show_sha = segment_config.options.get("show_sha")
                    .and_then(|v| v.as_bool()).unwrap_or(false);
                GitSegment::new().with_sha(show_sha).collect(input)
            },
            SegmentId::ContextWindow => ContextWindowSegment::new().collect(input),
            SegmentId::Usage => UsageSegment::new().collect(input),
            SegmentId::Cost => CostSegment::new().collect(input),
            SegmentId::Session => SessionSegment::new().collect(input),
            SegmentId::OutputStyle => OutputStyleSegment::new().collect(input),
            SegmentId::Update => UpdateSegment::new().collect(input),
        };
        if let Some(data) = segment_data {
            results.push((segment_config.clone(), data));
        }
    }
    results
}
```

Key observations:
- Each segment struct is instantiated fresh per call (no persistent state).
- GitSegment has a builder pattern: `.with_sha(show_sha)` reads from `segment_config.options`.
- The match is **exhaustive** — the compiler enforces that every SegmentId variant has an arm. Adding a new variant without a match arm is a compile error.

---

### 5. Supporting Types

#### InputData (`src/config/types.rs:114-121`)

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

This is the JSON payload received from Claude Code's hook system. All segments receive the same `&InputData`.

#### SegmentConfig (`src/config/types.rs:28-36`)

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

The `options` field is a free-form map used for segment-specific configuration (e.g., `show_sha` for Git, `api_base_url`/`cache_duration`/`timeout` for Usage).

---

### 6. Helper Traits / Derive Macros

**No custom derive macros** are used in the segment system. All derives are standard:

| Type | Derives |
|---|---|
| `SegmentData` | `Debug`, `Clone` |
| `SegmentId` | `Debug`, `Clone`, `Copy`, `PartialEq`, `Eq`, `Hash`, `Serialize`, `Deserialize` |
| `SegmentConfig` | `Debug`, `Clone`, `Serialize`, `Deserialize` |
| Concrete segment structs | Mostly `Default` (via `#[derive(Default)]`); some have manual `Default` impls |

**No helper traits** beyond `Segment` itself. Each segment struct is standalone — there is no `SegmentBuilder` trait, no `SegmentRenderer` trait, etc. Rendering is handled entirely by `StatusLineGenerator::render_segment()`.

---

### 7. Segment Implementation Pattern

Every concrete segment follows the same pattern:

```rust
// 1. Define struct (usually unit struct or minimal fields)
#[derive(Default)]
pub struct FooSegment;

impl FooSegment {
    pub fn new() -> Self { Self }
}

// 2. Implement Segment trait
impl Segment for FooSegment {
    fn collect(&self, input: &InputData) -> Option<SegmentData> {
        // Extract data from input
        // Build primary/secondary strings
        // Populate metadata HashMap
        Some(SegmentData {
            primary: "...",
            secondary: "...",
            metadata: HashMap::new(),
        })
    }

    fn id(&self) -> SegmentId {
        SegmentId::Foo
    }
}
```

## Caveats / Not Found

- No proc macros or custom derive macros exist in this project. It is a binary crate with no macro exports.
- The `Segment` trait has no default method implementations — both `collect` and `id` must be provided by every implementor.
- There is no dynamic plugin system; all segments are statically known at compile time via the exhaustive match.
