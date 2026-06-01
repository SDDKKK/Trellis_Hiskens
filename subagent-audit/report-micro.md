# Trellis Subagent 内部工具使用分析

> **数据源**: 310 个 subagent 内部 transcript（`~/.claude/projects/<proj>/<session>/subagents/agent-*.jsonl`）  
> **覆盖**: ZZ-KKX 157 / Topo-Reliability 123 / Trellis_Hiskens 15 / Anhui-CIM 12 / Auto-research 3  
> **生成日期**: 2026-06-01

---

## 核心发现

> **三个 trellis subagent 加起来 10,112 次工具调用，其中 augment 使用 40 次（0.4%），codegraph 使用 0 次，smart-search 使用 1 次。几乎所有代码理解和探索工作靠 `Bash grep/ls/find` + `Read` 完成。**

---

## 1. trellis-research（185 runs / 5,572 次工具调用）

### 工具分布

| 工具 | 次数 | 占比 |
|---|---|---|
| **Bash** | 3,419 | **61.4%** |
| Read | 1,857 | 33.3% |
| Write | 219 | 3.9% |
| Skill | 26 | 0.5% |
| **augment codebase-retrieval** | **23** | **0.4%** |
| Grep (native) | 22 | 0.4% |

### Bash 命令分类（3,419 次）

| 命令类型 | 次数 | Bash 占比 | 分析 |
|---|---|---|---|
| **grep** | **985** | **28.8%** | 🔴 代码搜索主力，应大部分被 augment/codegraph 替代 |
| **ls/find** | **890** | **26.0%** | 🔴 目录探索，可被 codegraph_files 替代 |
| python/uv exec | 574 | 16.8% | 🟡 数据分析/验证，部分合理 |
| other | 778 | 22.8% | 混合 |
| cat/head/tail | 72 | 2.1% | 🔴 应直接用 Read |
| git | 69 | 2.0% | ✅ 合理 |
| wc | 48 | 1.4% | 🟡 |
| smart-search | **1** | **0.0%** | 🔴 外部调研几乎未使用 |

### 关键比率

| 指标 | 值 | 评价 |
|---|---|---|
| augment 使用率 | 23 / 5,572 = **0.4%** | 🔴 严重不足 |
| codegraph 使用率 | **0 / 5,572 = 0%** | 🔴 完全未使用 |
| smart-search 使用率 | **1 / 3,419 bash = 0.03%** | 🔴 外部调研能力闲置 |
| grep-via-bash 可替代量 | ~985 次（占 bash 29%） | 至少 60-70% 可被 augment 语义搜索替代 |
| ls/find 可替代量 | ~890 次（占 bash 26%） | 大部分可被 codegraph_files 替代 |
| cat/head/tail 可替代量 | 72 次 | 全部应直接用 Read |

### 问题总结

1. **research 几乎完全靠 bash grep + ls 暴力探索**——这正是 augment 和 codegraph 要解决的。985 次 grep 里很多是"找函数定义""找引用""理解代码结构"这类语义查询，用 augment 一次调用能替代多次 grep。
2. **smart-search 外部调研只用了 1 次**——research agent 应该在需要查规范/文献/最佳实践时主动调用。
3. **cat/head/tail 72 次完全是 Read 工具的职责**——浪费 bash 上下文。

---

## 2. trellis-implement（71 runs / 2,348 次工具调用）

### 工具分布

| 工具 | 次数 | 占比 |
|---|---|---|
| **Bash** | 1,204 | **51.3%** |
| Read | 727 | 31.0% |
| Edit | 323 | 13.8% |
| Write | 84 | 3.6% |
| **augment codebase-retrieval** | **10** | **0.4%** |

### Bash 命令分类（1,204 次）

| 命令类型 | 次数 | Bash 占比 | 分析 |
|---|---|---|---|
| other | 353 | 29.3% | 混合 |
| **python/uv exec** | **293** | **24.3%** | 🟡 大量 `python -c`/`uv run` 做验证 |
| **grep** | **236** | **19.6%** | 🔴 实现时仍大量 grep 找代码，应先 augment/codegraph 再定位 |
| **ls/find** | **212** | **17.6%** | 🔴 同上 |
| git | 34 | 2.8% | ✅ 合理 |
| cat/head/tail | 21 | 1.7% | 🔴 应用 Read |

### 关键比率

| 指标 | 值 | 评价 |
|---|---|---|
| augment 使用率 | 10 / 2,348 = **0.4%** | 🔴 严重不足 |
| codegraph 使用率 | **0%** | 🔴 完全未使用 |
| grep+ls/find 占 bash | **37.2%** | 实现前的代码定位，应被 augment/codegraph 替代 |
| python/uv exec 占 bash | 24.3% | 大量行内验证；**部分可通过 spec 里的验证命令替代** |

### 问题总结

1. **implement 做了大量本该在 research 阶段完成的代码探索**（236 grep + 212 ls/find = 448 次）→ research 没充分给 implement 准备好上下文。
2. **augment/codegraph 工具完全闲置**——implement 需要理解依赖关系（codegraph_callers/impact）才能安全改代码,但 0 次使用。
3. **python -c 验证 293 次**——很多是语法检查/小测试,暗示实现过程不够一次到位,需要反复验证。spec 里如果定义好 lint/typecheck 命令,可以减少 ad-hoc 验证。

---

## 3. trellis-check（36 runs / 2,192 次工具调用）

### 工具分布

| 工具 | 次数 | 占比 |
|---|---|---|
| **Bash** | 1,389 | **63.4%** |
| Read | 636 | 29.0% |
| Edit | 158 | 7.2% |
| **augment codebase-retrieval** | **7** | **0.3%** |

### Bash 命令分类（1,389 次）

| 命令类型 | 次数 | Bash 占比 | 分析 |
|---|---|---|---|
| **grep** | **352** | **25.3%** | 🔴 check 时大量 grep 找引用/验证一致性 |
| python/uv exec | 246 | 17.7% | 🟡 运行测试/验证 |
| other | 266 | 19.2% | 混合 |
| **ls/find** | **190** | **13.7%** | 🔴 |
| **git** | **182** | **13.1%** | ✅ git diff/status 合理（check 核心动作）|
| **rtk** | **125** | **9.0%** | ✅ RTK token-saving proxy 使用良好 |
| cat/head/tail | 18 | 1.3% | 🔴 |

### 关键比率

| 指标 | 值 | 评价 |
|---|---|---|
| augment 使用率 | 7 / 2,192 = **0.3%** | 🔴 不足 |
| codegraph 使用率 | **0%** | 🔴 check 需要 impact analysis 但完全没用 |
| rtk 使用 | 125 次（bash 9%） | ✅ 唯一正面——check 用了 RTK 省 token |
| grep 用于一致性检查 | 352 次 | codegraph_callers + codegraph_impact 能替代大部分 |

### 问题总结

1. **check 需要验证修改不破坏依赖——这正是 codegraph_impact 的职责**,但 0 次使用。352 次 grep 里大量是找"谁引用了这个函数/变量",codegraph_callers 一次调用搞定。
2. **RTK 使用 125 次是正面信号**——check agent 是三者中唯一有效使用 RTK 的,但 research/implement 几乎未用(2 次)。
3. **augment 仅 7 次**——check 需要理解改动的上下文影响,augment 语义检索应更频繁。

---

## 4. 跨 Subagent 对比总表

| 指标 | research (185) | implement (71) | check (36) |
|---|---|---|---|
| 总工具调用 | 5,572 | 2,348 | 2,192 |
| Bash 占比 | 61.4% | 51.3% | **63.4%** |
| grep-via-bash | **985 (28.8%)** | 236 (19.6%) | 352 (25.3%) |
| ls/find-via-bash | **890 (26.0%)** | 212 (17.6%) | 190 (13.7%) |
| augment | **23 (0.4%)** | 10 (0.4%) | 7 (0.3%) |
| codegraph | **0** | **0** | **0** |
| smart-search | **1** | 0 | 0 |
| python exec | 574 | **293** | 246 |
| rtk | 2 | 47 | **125** |

---

## 5. 优化建议

### P0: Agent Prompt 必须显式引导使用 augment/codegraph

| 改动 | 对象 | 具体修改 |
|---|---|---|
| **research** agent | `.claude/agents/trellis-research.md` | 加 "代码理解必须优先用 `mcp__augment-context-engine__codebase-retrieval` 和 `codegraph_context`；禁止用 `bash grep/ls/find` 做代码语义搜索（精确字符串查找除外）" |
| **implement** agent | `.claude/agents/trellis-implement.md` | 加 "修改代码前必须用 `codegraph_impact` 查 blast radius；用 `augment codebase-retrieval` 理解上下文，不要 grep" |
| **check** agent | `.claude/agents/trellis-check.md` | 加 "验证依赖影响必须用 `codegraph_callers` + `codegraph_impact`；一致性检查用 `augment` 语义搜索替代 grep" |

**预期效果**: grep 985+236+352 = 1,573 次中，估计 60-70%（~1,000 次）可被 augment/codegraph 替代。每次 augment 调用约等于 3-5 次 grep 的信息量，总工具调用预计下降 30-40%。

### P1: Research Agent 必须主动使用 smart-search

| 改动 | 对象 | 具体修改 |
|---|---|---|
| research agent | `.claude/agents/trellis-research.md` | 加 "涉及规范/标准/最佳实践/外部文档时，必须调用 `smart-search` CLI；不要仅靠本地代码推断" |
| tools 声明 | agent frontmatter `tools:` | 确认 Bash 在 tools 列表中（smart-search 通过 Bash 调用） |

### P2: Implement Agent 加强 spec 遵守 + 减少 ad-hoc 验证

| 改动 | 对象 | 具体修改 |
|---|---|---|
| implement agent | `.claude/agents/trellis-implement.md` | 加 "实现前必须读 `.trellis/spec/` 相关 spec 文件；验证用 spec 定义的 lint/typecheck 命令，不要 `python -c` ad-hoc 检查" |
| implement.jsonl | 各 task 的 implement.jsonl | 应包含明确的验证命令（`uv run pytest`, `uv run mypy` 等），减少 subagent 自行发明验证方式 |

### P3: cat/head/tail → Read（全 agent）

| 改动 | 对象 | 具体修改 |
|---|---|---|
| 所有 agent | 各 `.claude/agents/trellis-*.md` | 加 "读文件内容用 Read 工具，禁止 `cat/head/tail`" |

**统计**: cat/head/tail 共 111 次（research 72 + implement 21 + check 18），全部可用 Read 替代。

### P4: RTK 推广到 research/implement

| 改动 | 对象 |
|---|---|
| research + implement agent | 确认 RTK hook 对 subagent 生效（check 的 125 次 rtk 说明 hook 在部分 agent 已生效） |

---

## 6. 方法论注记

- 数据来源: `<session-dir>/subagents/agent-<agentId>.jsonl`（每个 subagent dispatch 的完整内部 transcript）
- 310 个文件，覆盖 5 个项目
- Bash 命令分类用前缀匹配（grep/ls/find/cat/head/tail/git/python/uv/smart-search/rtk），"other" 为未分类
- augment/codegraph 计数精确（匹配 tool_use name）
- smart-search 只统计了 Bash 里含 `smart-search` 的调用
