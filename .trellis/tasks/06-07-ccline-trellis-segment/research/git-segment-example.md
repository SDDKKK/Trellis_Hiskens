# Research: Git Segment Implementation in CCometixLine

- **Query**: Full implementation analysis of the Git segment as a template for the Trellis segment
- **Scope**: internal (~/github/CCometixLine)
- **Date**: 2026-06-07

## Findings

### Files Found

| File Path | Description |
|---|---|
| `src/core/segments/git.rs` | Git segment: struct, Segment trait impl, all helper functions |
| `src/core/segments/mod.rs` | Segment trait definition, SegmentData struct, re-exports |
| `src/core/statusline.rs` | Segment instantiation, config option access, collect_all_segments() |
| `src/config/types.rs` | SegmentConfig, SegmentId enum, InputData, all shared types |
| `src/config/defaults.rs` | Config::default() delegates to theme presets |
| `src/ui/themes/theme_default.rs` | Default theme preset including git_segment() with options |
| `src/core/segments/directory.rs` | Simpler segment for comparison (no external data reads) |

---

## 1. Full Source Code Structure

### Segment Trait (mod.rs:14-18)

```rust
pub trait Segment {
    fn collect(&self, input: &InputData) -> Option<SegmentData>;
    fn id(&self) -> SegmentId;
}
```

Two methods: `collect` returns `Option<SegmentData>` (None = segment hidden), `id` returns enum variant.

### SegmentData (mod.rs:20-25)

```rust
#[derive(Debug, Clone)]
pub struct SegmentData {
    pub primary: String,      // Main display text (e.g., branch name)
    pub secondary: String,    // Status indicators (e.g., "✓ ↑2")
    pub metadata: HashMap<String, String>,  // Structured key-value data
}
```

### GitSegment Struct (git.rs:22-24)

```rust
pub struct GitSegment {
    show_sha: bool,  // Single config-driven field
}
```

Implements `Default` (delegates to `new()`), has builder method `with_sha(bool)`.

### SegmentId Enum (types.rs:64-76)

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SegmentId {
    Model, Directory, Git, ContextWindow, Usage, Cost, Session, OutputStyle, Update,
}
```

---

## 2. How It Reads External Data

All external data is read via `std::process::Command` subprocesses running `git` CLI commands. The pattern is consistent across all helpers:

### Command Pattern

```rust
Command::new("git")
    .args(["--no-optional-locks", "<subcommand>", ...])
    .current_dir(working_dir)
    .output()
```

Key detail: `--no-optional-locks` is always passed as the first arg to avoid git lock contention.

### Helper Functions (all take `&self, working_dir: &str`)

| Method | Git Command | Returns | Error Behavior |
|---|---|---|---|
| `is_git_repository()` | `git rev-parse --git-dir` | `bool` | `false` on any failure |
| `get_branch()` | `git branch --show-current`, fallback: `git symbolic-ref --short HEAD` | `Option<String>` | Falls through to second command, then `None` |
| `get_status()` | `git status --porcelain` | `GitStatus` enum | Defaults to `Clean` |
| `get_ahead_behind()` | `git rev-list --count @{u}..HEAD` / `HEAD..@{u}` | `(u32, u32)` | `(0, 0)` on failure |
| `get_sha()` | `git rev-parse --short=7 HEAD` | `Option<String>` | `None` on failure |

### Data Flow

```
get_git_info(working_dir) orchestrates all helpers:
  1. is_git_repository() → false? return None (hides segment)
  2. get_branch() → fallback "detached"
  3. get_status()
  4. get_ahead_behind()
  5. get_sha() → only if self.show_sha is true
  → returns Option<GitInfo>
```

### Intermediate Data Struct (git.rs:7-13)

```rust
pub struct GitInfo {
    pub branch: String,
    pub status: GitStatus,
    pub ahead: u32,
    pub behind: u32,
    pub sha: Option<String>,
}
```

---

## 3. How It Constructs SegmentData

In `Segment::collect()` (git.rs:175-213):

```rust
fn collect(&self, input: &InputData) -> Option<SegmentData> {
    let git_info = self.get_git_info(&input.workspace.current_dir)?;
    // ^ If not a git repo, returns None → segment is hidden

    // Metadata: structured key-value pairs
    let mut metadata = HashMap::new();
    metadata.insert("branch".to_string(), git_info.branch.clone());
    metadata.insert("status".to_string(), format!("{:?}", git_info.status));
    metadata.insert("ahead".to_string(), git_info.ahead.to_string());
    metadata.insert("behind".to_string(), git_info.behind.to_string());
    if let Some(ref sha) = git_info.sha {
        metadata.insert("sha".to_string(), sha.clone());
    }

    // Primary: the branch name
    let primary = git_info.branch;

    // Secondary: status symbols joined by space
    let mut status_parts = Vec::new();
    match git_info.status {
        GitStatus::Clean => status_parts.push("✓".to_string()),
        GitStatus::Dirty => status_parts.push("●".to_string()),
        GitStatus::Conflicts => status_parts.push("⚠".to_string()),
    }
    if git_info.ahead > 0 {
        status_parts.push(format!("↑{}", git_info.ahead));
    }
    if git_info.behind > 0 {
        status_parts.push(format!("↓{}", git_info.behind));
    }
    if let Some(ref sha) = git_info.sha {
        status_parts.push(sha.clone());
    }

    Some(SegmentData {
        primary,                              // "main"
        secondary: status_parts.join(" "),    // "✓ ↑2"
        metadata,                             // { "branch": "main", "status": "Clean", ... }
    })
}
```

Pattern summary:
- **primary** = the main human-readable label (branch name)
- **secondary** = compact status indicators joined by spaces
- **metadata** = every raw value as string key-value pairs (for programmatic use)

---

## 4. How Segment-Specific Config Options Are Accessed

### Option Definition (theme_default.rs:56-60)

Options are `HashMap<String, serde_json::Value>` on `SegmentConfig`:

```rust
options: {
    let mut opts = HashMap::new();
    opts.insert("show_sha".to_string(), serde_json::Value::Bool(false));
    opts
},
```

### Option Access (statusline.rs:479-485)

In `collect_all_segments()`, options are read from the `SegmentConfig` and used to configure the segment instance:

```rust
crate::config::SegmentId::Git => {
    let show_sha = segment_config
        .options
        .get("show_sha")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    let segment = GitSegment::new().with_sha(show_sha);
    segment.collect(input)
}
```

Pattern: `segment_config.options.get("key").and_then(|v| v.as_TYPE()).unwrap_or(default)`.

### Contrast: Segments Without Options

Most segments (Directory, Model, Cost, etc.) have `options: HashMap::new()` and are instantiated as:

```rust
let segment = DirectorySegment::new();
segment.collect(input)
```

---

## 5. Error Handling Patterns

### Philosophy: Silent Degradation

Every error path either hides the segment or provides a safe default. No panics, no error propagation to the caller.

| Failure Scenario | Behavior |
|---|---|
| `git` binary not found | `is_git_repository()` returns `false` → `collect()` returns `None` → segment hidden |
| Not in a git repo | Same as above |
| `git branch --show-current` fails | Falls through to `git symbolic-ref --short HEAD`; if both fail, uses `"detached"` |
| `git status --porcelain` fails | Returns `GitStatus::Clean` (optimistic default) |
| `git rev-list --count` fails | Returns `0` for both ahead and behind |
| `git rev-parse --short HEAD` fails | Returns `None` → sha omitted from display |
| UTF-8 decode fails | `.ok()?.trim()` pattern → `None` → falls through to default |

### Key Code Pattern

```rust
// The canonical error handling pattern used throughout:
Command::new("git")
    .args([...])
    .current_dir(working_dir)
    .output()                          // Result<Output> → could fail if git not found
    .map(|output| output.status.success())  // Only care about exit code
    .unwrap_or(false)                  // Any error → false
```

For string extraction:
```rust
String::from_utf8(output.stdout)
    .ok()?        // UTF-8 failure → None (propagated via ?)
    .trim()       // Strip whitespace
    .to_string()
```

---

## Additional Patterns

### InputData Access

The `collect()` method receives `&InputData` which contains:
```rust
pub struct InputData {
    pub model: Model,
    pub workspace: Workspace,       // workspace.current_dir is what Git uses
    pub transcript_path: String,
    pub cost: Option<Cost>,
    pub output_style: Option<OutputStyle>,
}
```

Git segment only uses `input.workspace.current_dir` from InputData. For a Trellis segment, the equivalent would be using relevant fields from InputData (or extending InputData if needed).

### Segment Instantiation Flow (statusline.rs:456-520)

```
collect_all_segments(config, input)
  → for each SegmentConfig in config.segments:
      → skip if !enabled
      → match segment_config.id:
          → construct segment with options from segment_config.options
          → call segment.collect(input)
          → if Some(data), push (config, data) to results
```

### Module Registration (mod.rs)

Each segment module is declared in `mod.rs` and re-exported:
```rust
pub mod git;
pub use git::GitSegment;
```

The SegmentId enum in `types.rs` must include a variant for every segment, and the match in `collect_all_segments()` must handle it.

## Caveats / Not Found

- The Git segment uses synchronous subprocess execution. There is no async or caching layer; every statusline refresh runs all git commands.
- The `working_dir` parameter comes from `input.workspace.current_dir`, which is the Claude Code workspace directory passed in the InputData JSON from the Claude Code process.
- The `--no-optional-locks` flag is git-specific optimization; a Trellis segment reading Trellis state would not need this but would need its own equivalent safety measures (e.g., graceful handling of missing `.trellis/` directory).
