# Trellis Link Guide — Symlink 管理工具使用指南

> **Purpose**: 理解 trellis-link.py 的架构和使用方式，正确管理跨项目共享文件。

## Architecture

```
~/.trellis/
├── shared/              # symlink 目标（所有项目共享）
│   ├── .claude/         # agents, hooks, commands, skills
│   └── .trellis/        # scripts, spec/guides, templates
├── trellis-link.py      # 管理工具
└── trellis-sync.py      # [deprecated]
```

### 三种链接状态

| 状态 | 含义 |
|------|------|
| `directory_link` | 整目录 symlink → shared/ |
| `file_link` | 单文件 symlink → shared/ |
| `mixed` | 本地真实目录；shared 条目以 per-entry symlink 呈现；`detached_files` 列出项目独有条目（可为真实目录/文件或指向外部路径的 symlink） |

### mixed 模式的语义

`mixed` 的 detached 条目既可以是**真实目录/文件**（如 `.agents/skills/gurobi-docs`），也可以是**指向任意外部路径的 symlink**（如 `.claude/skills/consciousness-council` → `/mnt/e/Github/skills/...`）。

**`link`（无 `--force`）—— 加法对账**：当本地已是 mixed 真实目录时，`link` 只做加法：
- 遍历 shared 下的条目，本地缺什么就补一个 per-entry symlink；
- 本地已经是正确的 shared symlink → 跳过；
- 本地是真实文件/目录，或 symlink 指向别处 → 视为项目 override，**保留不动**；
- **永远不删** 本地任何条目。

日常加入项目独有 skill 的完整流程就是：
```bash
ln -s /path/to/external/my-skill .claude/skills/my-skill   # 或 mkdir ...
# 完成。不需要改 .link-state.json。下次 link 也不会被动到。
```

**`link --force` —— 完全重建**：这是"按状态权威重建"的破坏性操作，未登记在 `detached_files` 里的项目独有条目会被清理。重建流程：
1. 对真实文件/目录用 `shutil.copytree`/`copy2` 备份到 tempdir，之后恢复；
2. 对 symlink 用 `.__symlink_target__` sidecar 文件记录 `readlink` 目标，重建时用 `os.symlink` 原样恢复（symlink-safe）；
3. 对 shared 条目逐个建 per-entry symlink；
4. `note` 字段跨重建保留。

因此 `detached_files` 的语义是**"关键保留清单" —— 仅当你希望某项目独有条目在任何 `--force` 灾难恢复后必然存在时才需登记**。日常加新 skill 不需要动它。

**进入 mixed 态的两条路径**：
- **代码路径**：`trellis-link.py detach <project> <path>`，要求被 detach 的条目已存在于 shared。
- **手工路径**：`.link-state.json` 是 gitignored 的本地状态（见 `.trellis/.gitignore`），直接改 `"type": "mixed"`（保留 `"target"`），然后 `trellis-link.py link <project>` 做一次加法对账即可。适合"项目独有条目从未在 shared 存在过"的场景。

**`.claude/skills` 的推荐组织方式**：
```
<project>/.claude/skills/               ← 本地真实目录（.gitignored）
├── <shared-skill-a>  → ~/.trellis/shared/.claude/skills/<shared-skill-a>
├── <shared-skill-b>  → ~/.trellis/shared/.claude/skills/<shared-skill-b>
├── <local-skill-1>/                   ← 项目独有真实目录
└── <external-ref>    → /mnt/e/Github/skills/.../                ← 项目独有外部引用
```
本地容器被 `.gitignore` 隔离（见各项目 `.gitignore` 的 `.claude/skills/` 一行），shared 的编辑依然实时全局生效。

### settings.json 三层

| 层 | 文件 | 用途 |
|----|------|------|
| Base | `~/.trellis/shared/.claude/settings.json` | hooks + permissions（共享） |
| Project | `项目/.claude/settings.project.json` | 项目特有 env/hooks 覆盖 |
| Generated | `项目/.claude/settings.json` | 合并结果（Claude Code 读取） |

> **Gotcha: Hooks Override Semantics**
>
> Claude Code 的 hooks 同名事件类型（如 `PreToolUse`）在不同 scope 间是 **override（完全替换）**，不是数组合并。
> 项目级 `settings.json` 定义了 `PreToolUse` 后，全局 `~/.claude/settings.json` 的 `PreToolUse` 会被完全覆盖。
> 因此：**任何需要全局生效的 hook（如 RTK token 优化）必须写入 shared base settings，不能只放 `~/.claude/settings.json`。**
> `permissions.allow/deny` 等数组型设置会 concatenate+deduplicate，但 `hooks` 不遵循此规则。

## Commands

```bash
trellis-link.py link <project>          # 建立 symlink
trellis-link.py unlink <project>        # 移除 symlink，恢复独立副本
trellis-link.py detach <project> <path> # 单文件脱离共享
trellis-link.py attach <project> <path> # 恢复 symlink
trellis-link.py status [project]        # 查看链接状态
trellis-link.py verify [project]        # 验证完整性
trellis-link.py migrate <project>       # 从 sync 模式迁移
trellis-link.py settings-merge <project># 合并 settings.json
trellis-link.py discover                # 发现所有项目
```

## Universal Feature 处理策略

| 文件类型 | 策略 | 原因 |
|---------|------|------|
| Python 脚本 | Config 驱动 | `.trellis/config.yaml` 的 `features` 段控制分支 |
| Markdown (commands/guides) | Base + Extension | `*-base.md` 共享 + `*-{project}.md` 项目增量 |
| Agent 定义 (.claude/agents/) | 直接 symlink | Claude Code 直接读取，不支持拆分 |
| 高度定制文件 | 保持项目独有 | 不参与 symlink |

### Config 驱动示例

```yaml
# .trellis/config.yaml
features:
  ccr_routing: true      # Topo only
  java_support: false     # Anhui only
  reference_support: true
```

### Base + Extension 示例

```jsonl
{"file": "commands/trellis/brainstorm-base.md", "reason": "通用流程"}
{"file": "commands/trellis/brainstorm-topo.md", "reason": "Topo 特有 DoD"}
```

Extension 缺失时静默跳过。

## Common Mistakes

### Don't: 直接编辑 symlinked 文件以为只影响当前项目

shared/ 下的文件被所有项目共享。编辑 `项目/.claude/agents/implement.md` 实际修改的是 `~/.trellis/shared/.claude/agents/implement.md`，影响所有项目。

**需要项目定制时**：先 `detach`，再编辑独立副本。

### Don't: 超集合并 universal_feature 文件

项目无关内容会浪费 context tokens 并误导 agent。用 config 驱动或 base+extension 替代。

### Don't: 手动编辑 generated settings.json

`settings-merge` 会覆盖。修改应放在 `settings.project.json` 中。

### Don't: 只在 ~/.claude/settings.json 配置全局 hook

全局 settings 的 hooks 会被项目级 settings 同名事件类型覆盖。如果需要所有项目都生效（如 RTK 的 `PreToolUse.Bash` matcher），必须加入 shared base settings (`~/.trellis/shared/.claude/settings.json`)，然后 `settings-merge` 同步。

**实际案例**：RTK hook 在 `~/.claude/settings.json` 配置了 `PreToolUse.Bash` matcher，但所有 Trellis 项目的 generated settings.json 定义了自己的 `PreToolUse`（只有 Task + Agent），导致 RTK 完全失效 5 天未被发现。

## Upstream Merge Strategy

When the upstream Trellis releases a new version (e.g., v0.4.0-beta.7), use **selective merge** — not full upgrade.

### Why Selective

The local framework evolves independently and may contain features upstream doesn't have (CCR routing, review agent, codex-implement, escalation mechanism). Full upgrade would overwrite these.

### Decision Framework

| Category | Action | Example |
|----------|--------|---------|
| Local is superset | **SKIP** — keep local | inject-subagent-context.py (has CCR, state machine) |
| Upstream has new value | **ADOPT** — copy from upstream | new common/ modules, new task.py commands |
| Both have value | **ADAPT** — merge selectively | session-start.py (take spec_scope, keep memory injection) |
| Not relevant | **SKIP** — ignore | Marketplace web templates, CodeBuddy platform |

### Process

```bash
# 1. Clone upstream to /tmp
git clone --branch <tag> --depth 1 https://github.com/mindfold-ai/Trellis.git /tmp/trellis-upstream

# 2. Research with Context7 + Augment + direct file reading
#    Compare each area: hooks, agents, scripts, config

# 3. Modify ~/.trellis/shared/ (NOT project .trellis/)
#    Changes propagate instantly via symlink

# 4. Run L1-L4 verification (see verification-before-completion.md)

# 5. Cleanup
rm -rf /tmp/trellis-upstream
```

### Protected Files

These files are local superset — never overwrite with upstream:

- `inject-subagent-context.py` — CCR routing, review agent, codex-* variants, state machine
- `ralph-loop.py` — per-agent state, escalation mechanism, atomic writes
- `research.md` — richer tool list (context7/augment/morph/grok scripts)
- `review.md` — domain-specific 6-dimension review (local-only)
- `codex-implement.md` — Codex CLI integration (local-only)

## Common Modules (v0.3.7+)

New utility modules available in `common/` after upstream merge:

| Module | Import | Purpose |
|--------|--------|---------|
| `io.py` | `from common.io import read_json, write_json` | Unified JSON file I/O |
| `git.py` | `from common.git import run_git` | Unified git commands, returns `(rc, stdout, stderr)` |
| `log.py` | `from common.log import Colors, colored` | Unified terminal color output |
| `types.py` | `from common.types import TaskData, TaskInfo` | TypedDict/dataclass for task.json |
| `tasks.py` | `from common.tasks import iter_active_tasks` | Task query/iteration (requires `tasks_dir` arg) |

These coexist with existing modules — old code still works, new code can use either.
