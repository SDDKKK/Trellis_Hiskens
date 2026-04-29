# Root-level Platform Files Cleanup and Overlay Refresh

## Background

Trellis_Hiskens 有两层文件结构：

1. **模板源码层** (`packages/cli/src/templates/`) — CLI 发布的模板，用户 `trellis init` 时复制到项目
2. **根目录安装层** (`.claude/`, `.agents/`, `.codex/`, `.cursor/`, `.opencode/`, `.pi/`) — 本 repo 自身的 Trellis 安装副本

beta.18 sync 后，模板源码层已与上游一致。但根目录安装层存在 66 个不属于上游 beta.18 的多余文件，分为两类：

### 类别 A: Legacy 残留（41 个）
- 来源：上游旧版本（beta.1~beta.15）曾安装，后续版本删除但 ours-strategy merge 保留
- 状态：**零手动修改**，全部是纯安装副本
- 风险：旧 agent 定义与新版并存导致重复加载（如 `check.md` + `trellis-check.md`）
- 处理：**安全删除**

### 类别 B: Overlay 副本过期（25 个）
- 来源：`overlays/hiskens/templates/` 注入到根目录，但根副本未跟随 overlay 源更新
- 状态：**零手动修改**，overlay 源均比根副本新
- 差异举例：`statusline.py` 缺少 Sub2API caching、`ralph-loop.py` 缺少 escalation loop
- 处理：**从当前 overlay 源刷新**

### 特殊文件
- `.claude/skills/fork-sync-strategy/SKILL.md` — 今天新建的 skill 文件（untracked），需先保存到 overlay 或单独提交

## Goal

让根目录安装层 = 上游 beta.18 内容 + overlay 当前版本内容，删除所有不属于这两者的残留。

## Constraints

1. `trellis update --overlay hiskens` **不会自动删除** legacy 文件（只有 migration manifest 的 `safe-file-delete` 才行）
2. `.trellis/spec/` 受 `PROTECTED_PATHS` 保护，overlay 的 spec 文件不会被 update 安装
3. `exclude.yaml` 排除了 2 个文件：`claude/agents/review.md` 和 `trellis/worktree.yaml`
4. `.trellis/.template-hashes.json` 中没有 legacy 文件的记录（因为它们在 hash 追踪机制引入前就存在）

## Approach

### Option A: 手动清理（推荐）
1. 手动删除 41 个 legacy 文件
2. 运行 `node packages/cli/bin/trellis.js update --overlay hiskens` 刷新所有模板（包括 overlay）
3. 验证根目录状态

### Option B: 全量清理 + 重新安装
1. 删除所有根目录平台文件（`.claude/`, `.agents/` 等）
2. 运行 `node packages/cli/bin/trellis.js init --claude --codex --overlay hiskens -y --no-monorepo` 重新初始化
3. 恢复 `.claude/settings.local.json` 和 fork-sync-strategy skill

### 推荐 Option A — 更可控，改动最小。

## Acceptance Criteria

- [ ] 根目录的上游文件与 beta.18 完全一致（261 个已确认一致的文件不变）
- [ ] 41 个 legacy 文件已删除
- [ ] 25 个 overlay 副本已从 overlay 源刷新
- [ ] `.claude/skills/fork-sync-strategy/SKILL.md` 已保留（移入 overlay 或单独提交）
- [ ] `trellis update --overlay hiskens --dry-run` 报告零变更（可选验证）
- [ ] Build / typecheck / test 通过

## Research References

- `.trellis/tasks/04-29-sync-upstream-beta18/research/root-level-audit.md` — 全量文件清单
- `.trellis/tasks/04-29-sync-upstream-beta18/research/update-mechanism.md` — update 命令机制
- `.trellis/tasks/04-29-sync-upstream-beta18/research/overlay-mapping.md` — overlay 映射关系
- `.trellis/tasks/04-29-sync-upstream-beta18/research/root-customization-check.md` — 文件定制状态
