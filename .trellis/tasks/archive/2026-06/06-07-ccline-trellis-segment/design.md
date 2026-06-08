# Design: CCometixLine Trellis Segment

## Architecture Overview

Trellis 信息通过**两个独立 segment** 融入 ccline 状态栏，外加一个独立渲染的第二行：

```
Claude Code stdin JSON
    ↓
InputData { workspace: { current_dir } }
    ↓
┌─ TrellisDevSegment::collect(&input)
│   ├── .trellis/ 不存在？→ return None
│   ├── env CLAUDE_CODE_SESSION_ID → 构造 context key → 读 session file → active task
│   ├── 读取 .trellis/tasks/{task}/task.json → title/status/priority
│   └── 读取 .trellis/.developer → developer name
│   ↓
│   SegmentData { primary: "Hiskens", secondary: "", metadata: { task_line, ... } }
│
└─ TrellisTasksSegment::collect(&input)
    ├── .trellis/ 不存在？→ return None
    └── 遍历 .trellis/tasks/ → 非归档任务数
    ↓
    SegmentData { primary: "33 task(s)", secondary: "", metadata: { task_count } }
```

**最终输出布局**：

```
场景 A（有 active task）:
  Opus 4 │ ~/project │  main ↑1 │ ctx 42% │ Hiskens │ 33 task(s)
  [P2] CCometixLine Trellis segment — add native ... (planning)

场景 B（无 active task，有 .trellis/）:
  Opus 4 │ ~/project │  main ↑1 │ ctx 42% │ Hiskens │ 33 task(s)

场景 C（无 .trellis/）:
  Opus 4 │ ~/project │  main ↑1 │ ctx 42%
```

## 需要修改的文件

| # | 文件 | 改动 |
|---|------|------|
| 1 | `src/config/types.rs` | `SegmentId` 枚举添加 `TrellisDev` + `TrellisTasks` 变体 |
| 2 | `src/core/segments/trellis_dev.rs` | **新文件** — TrellisDevSegment |
| 3 | `src/core/segments/trellis_tasks.rs` | **新文件** — TrellisTasksSegment |
| 4 | `src/core/segments/mod.rs` | 添加 `pub mod` + re-export 两个新 segment |
| 5 | `src/core/statusline.rs` | `collect_all_segments()` 添加两个 match arm；`render_segment` 改为 `pub` |
| 6 | `src/ui/themes/theme_*.rs` (×9) | 每个主题添加 `trellis_dev_segment()` + `trellis_tasks_segment()` |
| 7 | `src/ui/themes/presets.rs` | 每个主题的 segments vec 末尾添加两个 trellis 调用 |
| 8 | `src/ui/components/preview.rs` | `generate_mock_segments_data()` 添加两个 mock；TUI 预览支持双行 |
| 9 | `src/main.rs` | 输出逻辑：提取 TrellisDev metadata 中的 task_line，渲染第二行 |

## 核心设计决策

### D1: Active Task 解析策略

Rust 侧基于 ccline 运行环境的实际约束简化为 4 级 fallback：

```
1. env CLAUDE_CODE_SESSION_ID → 构造 "claude_{uuid}" → 读 session file  ← 主路径
2. env TRELLIS_CONTEXT_ID → 直接用作 context key → 读 session file       ← 备用（Bash 上下文）
3. 列举 .trellis/.runtime/sessions/*.json
   - 恰好 1 个文件 → 读取其 current_task                                 ← single-session fallback
   - 0 或 ≥2 个 → 跳过 session 解析
4. 扫描 .trellis/tasks/*/task.json，找第一个 status=in_progress           ← 最终 fallback
5. 全部失败 → return None（无 active task，第二行不输出）
```

**关键约束**：
- `CLAUDE_ENV_FILE`（`TRELLIS_CONTEXT_ID` 的注入机制）仅对 Bash tool calls 生效
- `statusLine.command` 是 Claude Code UI 直接 spawn 的子进程，不走 Bash tool 通道
- Claude Code 给**所有子进程**设置 `CLAUDE_CODE_SESSION_ID`（值为 session UUID），ccline 可靠获取
- Context key 构造：`format!("claude_{}", session_id)` — 与 Python 侧 `_context_key("claude", "session", uuid)` 一致
- Session file 路径：`.trellis/.runtime/sessions/{context_key}.json`
- 不扩展 ccline 的 `InputData` 结构 — 所有数据通过 env var + 文件系统获取

### D2: 双 Segment + 双行布局

Trellis 信息拆成**两个独立 segment** + **一个独立渲染的第二行**：

| 组件 | SegmentId | 位置 | 内容 | 参与 generate() |
|------|-----------|------|------|:---:|
| TrellisDevSegment | `TrellisDev` | 第一行 | Developer name | ✅ |
| TrellisTasksSegment | `TrellisTasks` | 第一行 | Task count | ✅ |
| Task line | — | 第二行 | `[P{n}] {full_title} ({status})` | ❌ |

**两个 segment 各自独立读取 `.trellis/` 文件**，不共享缓存（总耗时 <5ms，远低于 Git segment 的 subprocess 开销）。

**main.rs 输出逻辑**：

```rust
let segments = collect_all_segments(&config, &input);

// 提取 TrellisDev metadata 中的 task_line（如果有）
let task_line: Option<String> = segments.iter()
    .find(|(c, _)| c.id == SegmentId::TrellisDev)
    .and_then(|(_, d)| d.metadata.get("task_line").cloned());

// 第一行：所有 segments 正常渲染（含 TrellisDev + TrellisTasks）
let statusline = generator.generate(segments);
println!("{}", statusline);

// 第二行：仅当 TrellisDev enabled 且有 active task 时
if let Some(line) = task_line {
    println!("{}", line);  // 已含 ANSI 颜色码
}
```

**TrellisDev 被禁用时，第二行也不显示** — task_line 数据由 TrellisDev 负责收集。

### D3: SegmentData 字段映射

**TrellisDevSegment**:
```rust
SegmentData {
    primary:   "Hiskens",
    secondary: "",
    metadata: {
        "task_line":   "\x1b[36m[P2]\x1b[0m CCometixLine Trellis segment — ... \x1b[33m(planning)\x1b[0m",
        "task_dir":    "06-07-ccline-trellis-segment",
        "status":      "planning",
        "priority":    "2",
        "developer":   "Hiskens",
    }
}
```
- `primary` = developer name
- `metadata["task_line"]` = 第二行完整内容（含 ANSI 颜色码），无 active task 时此 key 不存在
- `metadata["task_line"]` 受 `show_priority` 控制：关闭时不含 `[P{n}]`

**TrellisTasksSegment**:
```rust
SegmentData {
    primary:   "33 task(s)",
    secondary: "",
    metadata: {
        "task_count": "33",
    }
}
```

### D4: 第二行配色 — 硬编码仿 statusline.py

第二行不走 segment 管线渲染，配色硬编码：
- Priority `[P{n}]` → **cyan** (`\x1b[36m`)
- Status `({status})` → **yellow** (`\x1b[33m`)
- Title → 默认色（无 ANSI）

task_line 在 TrellisDevSegment 的 `collect()` 中组装好含颜色码的完整字符串，main.rs 直接 `println!`。

### D5: Segment Structs

```rust
// trellis_dev.rs
pub struct TrellisDevSegment {
    show_priority: bool,
}

// trellis_tasks.rs
pub struct TrellisTasksSegment;
```

TrellisDevSegment 用 builder pattern：`new()` + `with_priority(bool)`。
TrellisTasksSegment 无配置项，只需 `new()`。

### D6: Config — 两个独立 segment

```toml
[[segments]]
id = "trellis_dev"
enabled = true
[segments.icon]
plain = ""
nerd_font = ""
[segments.colors]
text = "Green"

[[segments]]
id = "trellis_tasks"
enabled = true
[segments.icon]
plain = ""
nerd_font = ""
[segments.colors]
text = "Green"

[segments.options]
# TrellisDev options:
show_priority = true   # 第二行是否显示 [P{n}]

# TrellisTasks 无 options
```

- 两个 segment 可**独立**启用/禁用
- Icon 设为空字符串（不显示图标）
- 用户可分别设置颜色

### D7: 文件读取 — 容错模式

跟随 GitSegment 的静默降级模式：

| 场景 | 行为 |
|------|------|
| `.trellis/` 不存在 | 两个 segment 的 `collect()` 都返回 `None` |
| `.developer` 不可读 | TrellisDev 返回 `None` |
| `task.json` 格式异常 | 跳过该 task，继续扫描 |
| 无 in_progress 任务 | TrellisDev 正常显示 developer name，metadata 无 task_line → 第二行不输出 |
| `.runtime/sessions/` 不存在 | 跳过 session 解析，走 task scan |

无 panic、无 error propagation、无日志输出。

### D8: 主题配色方案

两个 segment 使用相同的**绿色系**配色：

| 主题类型 | text | background |
|---------|------|-----------|
| Non-Powerline (cometix, default, minimal, gruvbox) | Green | None |
| Powerline-dark | Green | Rgb(40,40,40) |
| Powerline-light | Green | Rgb(220,220,220) |
| Nord | Green | Rgb(67,76,94) |
| Rose-pine | Green | Rgb(38,35,53) |
| Tokyo-night | Green | Rgb(36,40,59) |

Icon 均为空字符串。具体 RGB 值参考各主题中已有 segment 的配色。

### D9: Segment 排序位置

两个 Trellis segment 放在**末尾**（OutputStyle 之后、Update 之前）：

```
Model → Directory → Git → ContextWindow → Usage → Cost → Session → OutputStyle → TrellisDev → TrellisTasks
```

理由：跟 statusline.py 布局一致（developer/count 在行尾）。Trellis 信息是可选的（只有 Trellis 项目才有），放末尾不影响主要 segment 的位置稳定性。

### D10: TUI 预览双行支持

TUI 配置器的预览区域使用 ratatui `Paragraph` widget，高度动态计算（max 8 行），天然支持多行。
`generate_for_tui_preview()` 中做同样的 task_line 提取逻辑，在第一行 segments 之后追加第二行。

### D11: SegmentId 枚举

```rust
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SegmentId {
    Model, Directory, Git, ContextWindow,
    Usage, Cost, Session, OutputStyle,
    TrellisDev,    // → "trellis_dev"
    TrellisTasks,  // → "trellis_tasks"
    Update,
}
```

### D12: task.json 反序列化

只需要部分字段，serde 不设 `deny_unknown_fields`：

```rust
#[derive(Deserialize)]
struct TrellisTask {
    title: Option<String>,
    status: Option<String>,
    priority: Option<u8>,
    name: Option<String>,  // slug，作为 fallback title
}
```

### D13: `render_segment` 可见性

将 `StatusLineGenerator::render_segment` 从 private 改为 `pub`，
供 main.rs 和 TUI preview 在管线外渲染独立 segment。

### D14: task(s) 格式

Task count 统一使用 `{n} task(s)` 格式，不做单复数判断。

## 性能考量

- 两个 segment 各自独立读文件，总共 ~5-8 次 `fs::read_to_string`
- 目录遍历：`fs::read_dir` 两次（TrellisDev 读 sessions/，TrellisTasks 读 tasks/）
- 无子进程调用
- 总增量延迟：< 5ms，远低于 Git segment 的 subprocess 开销

## 兼容性

- 不修改 InputData：所有数据通过 env var + `workspace.current_dir` + 文件系统获取
- 不改变已有 segment 的行为
- `.trellis/` 不存在时完全透明（两个 segment 返回 None）
- Powerline/NerdFont/Plain 三种样式模式均支持
