# PRD: CCometixLine Trellis Segment

## Background

Trellis 当前使用 `.claude/hooks/statusline.py`（Python stop hook）在终端显示任务状态。
CCometixLine (`ccline`) 是 Rust 编写的高性能 Claude Code statusline 替代方案，
支持主题系统、Powerline 样式、TUI 配置器。

目标：在 ccline 中新增原生 `TrellisSegment`，将 Trellis 独有信息融入 ccline 状态栏，
最终取代 statusline.py 的大部分职责。

## Scope

**目标仓库**：`~/github/CCometixLine`（fork from Haleclipse/CCometixLine）

### 必须实现

1. **TrellisSegment** — 实现 `Segment` trait 的新 segment，显示：
   - Active task：`[P{n}] {title} ({status})`（优先级 + 标题 + 状态）
   - Developer name（从 `.trellis/.developer` 读取）
   - Task count（非归档任务数量）

2. **配置支持** — 在 `config.toml` 中增加 `[trellis]` section：
   - `enabled: bool`（默认 `true`）
   - `show_priority: bool`（默认 `true`）
   - `show_developer: bool`（默认 `true`）
   - `show_task_count: bool`（默认 `true`）
   - 标准 segment 样式字段（icon、colors、styles）

3. **Active task 解析** — 移植 statusline.py 中的 active task 发现逻辑：
   - 读取 `.trellis/tasks/*/task.json`
   - 识别 `status: in_progress` 的任务
   - 按 `.current_task` 指针或 fallback 策略定位

4. **Segment 注册** — 在 ccline 的 segment 注册机制中正确接入 TrellisSegment

### 可选（后续迭代）

- Sub2API 用量段（需要 API key 支持）
- Rate limit 段（5h/7d 用量百分比）— 依赖 Claude Code stdin 数据是否包含
- 上游 PR 贡献回 Haleclipse/CCometixLine

### 不做

- 修改 Trellis 本身的代码
- 改变 ccline 已有 segment 的行为
- 任何 Claude Code patching 功能

## Acceptance Criteria

1. `ccline` 在包含 `.trellis/` 目录的项目中能显示 active task 信息
2. 无 `.trellis/` 目录时 segment 优雅降级（不显示）
3. `config.toml` 中 `[trellis].enabled = false` 时完全不显示
4. 主题系统正确应用到 Trellis segment 的颜色和图标
5. `cargo build --release` 无 warning 编译通过
6. 不影响已有 segment 的功能和测试

## Constraints

- 遵循 ccline 已有的代码风格和 Segment trait 接口
- 文件读取需要容错（`.trellis/` 可能不存在、task.json 可能格式异常）
- 性能：文件 I/O 应快速，statusline 渲染延迟不应明显增加
