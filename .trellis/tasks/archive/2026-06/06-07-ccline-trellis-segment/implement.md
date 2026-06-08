# Implementation Plan: CCometixLine Trellis Segment

**目标仓库**: `~/github/CCometixLine`

## Checklist

### Step 0: 安装 Rust 环境
- [ ] 安装 rustup + stable 工具链：`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y`
- [ ] 加载环境：`source ~/.cargo/env`
- [ ] 验证 ccline 能编译：`cd ~/github/CCometixLine && cargo build --release`
- **验证**: `rustc --version && cargo --version && cargo clippy --version` 均有输出

### Step 1: SegmentId 枚举扩展
- [ ] `src/config/types.rs` — 在 `SegmentId` 枚举中添加 `TrellisDev` 和 `TrellisTasks` 变体（在 `Update` 之前）
- **验证**: `cargo check`（会有 exhaustive match 错误，后续步骤修复）

### Step 2: TrellisDevSegment 实现
- [ ] 创建 `src/core/segments/trellis_dev.rs`
- [ ] 实现 `TrellisDevSegment` struct + builder：`new()`, `with_priority(bool)`
- [ ] 实现 `Segment` trait (`collect`, `id`)
- [ ] 实现辅助函数：
  - `find_trellis_root(working_dir)` — 检查 `.trellis/` 是否存在
  - `resolve_active_task(trellis_root)` — 4 级 fallback（CLAUDE_CODE_SESSION_ID → TRELLIS_CONTEXT_ID → single-session → task scan）
  - `read_task_json(task_dir)` — 反序列化 TrellisTask
  - `read_developer(trellis_root)` — 解析 `.developer` 文件（`name=value` 格式）
  - `format_task_line(task, show_priority)` — 组装含 ANSI 颜色码的第二行字符串
- [ ] `collect()` 返回 SegmentData：primary=developer name, metadata 含 task_line
- **验证**: `cargo check`

### Step 3: TrellisTasksSegment 实现
- [ ] 创建 `src/core/segments/trellis_tasks.rs`
- [ ] 实现 `TrellisTasksSegment` struct：`new()`
- [ ] 实现 `Segment` trait (`collect`, `id`)
- [ ] 实现辅助函数：
  - `count_active_tasks(trellis_root)` — 遍历 `tasks/`，过滤非 archive 目录中含 `task.json` 的项
- [ ] `collect()` 返回 SegmentData：primary="{n} task(s)"
- **验证**: `cargo check`

### Step 4: Module 注册
- [ ] `src/core/segments/mod.rs` — 添加 `pub mod trellis_dev;` + `pub mod trellis_tasks;` + re-export
- **验证**: `cargo check`

### Step 5: Segment 分发注册
- [ ] `src/core/statusline.rs` — `collect_all_segments()` 的 match 中添加：
  - `SegmentId::TrellisDev` arm：读取 `show_priority` option，构建 `TrellisDevSegment::new().with_priority(...)`
  - `SegmentId::TrellisTasks` arm：构建 `TrellisTasksSegment::new()`
- [ ] `src/core/statusline.rs` — 将 `render_segment` 从 `fn` 改为 `pub fn`
- **验证**: `cargo check` 编译通过

### Step 6: 主题集成
- [ ] 在每个 `src/ui/themes/theme_*.rs` 文件（×9）中添加：
  - `pub fn trellis_dev_segment() -> SegmentConfig`（text=Green, icon 为空）
  - `pub fn trellis_tasks_segment() -> SegmentConfig`（text=Green, icon 为空）
  - Powerline 主题：添加对应背景色
- [ ] `src/ui/themes/presets.rs` — 每个主题的 segments vec 末尾（OutputStyle 之后）插入两个 trellis 调用
- **验证**: `cargo check` 编译通过

### Step 7: main.rs 双行输出
- [ ] `src/main.rs` — 修改 statusline 输出逻辑：
  ```rust
  let segments = collect_all_segments(&config, &input);
  // 提取 TrellisDev metadata 中的 task_line
  let task_line = segments.iter()
      .find(|(c, _)| c.id == SegmentId::TrellisDev)
      .and_then(|(_, d)| d.metadata.get("task_line").cloned());
  // 第一行
  let statusline = generator.generate(segments);
  println!("{}", statusline);
  // 第二行（仅当有 active task）
  if let Some(line) = task_line {
      println!("{}", line);
  }
  ```
- **验证**: `cargo check` 编译通过

### Step 8: TUI Preview 双行
- [ ] `src/ui/components/preview.rs` — `generate_mock_segments_data()` 添加：
  - TrellisDev mock：`primary="Hiskens"`, metadata 含 `task_line="[P1] example-task (in_progress)"`
  - TrellisTasks mock：`primary="5 task(s)"`
- [ ] TUI 预览渲染逻辑中追加第二行（同 main.rs 的 task_line 提取）
- **验证**: `cargo check` 编译通过

### Step 9: 构建 & 测试
- [ ] `cargo build --release` — 无 warning 编译
- [ ] `cargo clippy` — 无 warning
- [ ] 手动测试 — 在 Trellis 项目目录：
  ```bash
  echo '{"model":{"id":"claude-opus-4-20250514","display_name":"Claude Opus 4"},"workspace":{"current_dir":"/home/hcx/github/Trellis_Hiskens"},"transcript_path":"/tmp/test"}' | ./target/release/ccline
  ```
  预期：第一行末尾有 `Hiskens │ N task(s)`，第二行有 active task 信息
- [ ] 手动测试 — 在无 `.trellis/` 的目录：确认 Trellis segment 不显示
- [ ] 手动测试 — config.toml 中 `trellis_dev.enabled = false`：确认第一行无 developer 且第二行不输出

### Step 10: 集成到 Claude Code
- [ ] 将编译产物复制到 `~/.claude/ccline/ccline`
- [ ] 确认 `settings.json` 中的 `statusLine.command` 指向正确路径
- [ ] 在实际 Claude Code 会话中验证显示效果

## Rollback

每个步骤在独立 commit 中完成。如需回滚：
- `git revert <commit>` 回退单步
- 或 `git reset --hard upstream/master` 完全回退到 upstream 状态
