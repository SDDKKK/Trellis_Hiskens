# Trellis Subagent 调用分析报告（小样）

> 小样范围：Trellis_Hiskens(本体 dogfood) + ZZ-KKX（下游消费项目）  
> 生成日期：2026-06-01 | 提取脚本：`subagent-audit/extract.py`

---

## 1. 概览

| 指标 | 值 |
|---|---|
| Agent 调用总数 | 168 |
| 其中 trellis 调用 | **160**（research 104 / implement 37 / check 19）|
| 同步（有完整成本数据） | 47 |
| 异步（结局不可观测） | 113 |
| 项目分布 | ZZ-KKX 147、Trellis_Hiskens 13 |
| session 数 | 18（ZZ-KKX 15、Trellis_Hiskens 3）|

**关键比例**：research 占 65%（104/160），是最频繁的 subagent。

---

## 2. 效率 / Token / 成本

> 以下指标仅覆盖同步完成的 47 次调用（异步 113 次无成本数据）。

### 2.1 各 Subagent 成本画像

| subagent | 同步样本 | token 中位 | token 最高 | 耗时中位 | 内部工具调用中位 | cache 命中率 |
|---|---|---|---|---|---|---|
| trellis-implement | 15 | **95,195** | 148,809 | 4.5 min | 24 | 0.992 |
| trellis-research | 22 | 72,255 | 122,575 | 5.4 min | 19 | 0.941 |
| trellis-check | 10 | 53,119 | 117,166 | 4.8 min | 44 | 0.989 |

**洞察**：
- implement **token 最贵**（中位 95k），但 cache 命中率 0.992 = 注入上下文几乎全缓存复用，效率良好。
- check 内部工具调用最多（中位 44 次），但 token 最低 → check agent 做了很多小操作（diff/read/edit），合理。
- research cache 命中率相对低（0.941 vs 其它 0.99）→ 每次 research 问题不同，缓存复用空间天然少，非问题。

### 2.2 高成本调用 Top 6

| subagent | 项目 | token | 耗时 | 内部工具 | prompt 开头 |
|---|---|---|---|---|---|
| implement | ZZ-KKX | 148,809 | 19.7 min | 81 | feeder-id-keying |
| implement | ZZ-KKX | 135,815 | 9.1 min | 41 | ledger-metrics-decoupling W3 |
| **research** | ZZ-KKX | **122,575** | **66.4 min** | 51 | ledger-metric-calibration |
| check | ZZ-KKX | 117,166 | 8.5 min | 56 | pipeline-parallel-and-ledger-std |
| check | ZZ-KKX | 116,275 | 8.1 min | 49 | ledger-metrics-decoupling |
| implement | ZZ-KKX | 114,269 | **39.0 min** | 79 | phase3-parallel-feeders |

### 2.3 ⚠️ 超时调用（>10 分钟）

| subagent | 耗时 | token | prompt 摘要 |
|---|---|---|---|
| **research** | **66.4 min** | 122,575 | ledger-metric-calibration 研究 |
| implement | 39.0 min | 114,269 | phase3-parallel-feeders 实现 |
| implement | 19.7 min | 148,809 | feeder-id-keying 实现 |

66 分钟的 research 调用是明确异常——单次研究子任务不应耗时超 10 分钟。

---

## 3. 冗余

### 3.1 重复 Research（同 session ≥4 次 research）

**13 / 18 个 session** 出现 ≥4 次 research dispatch。极端例子：

| session | research 次数 | 序列特征 |
|---|---|---|
| ZZ-KKX/45b01e58 | **11** | R×7→I×3→C→R×4→I×3→C（两轮 research fan-out） |
| ZZ-KKX/d1e4c592 | **10** | R×4→I×2→C→R×3→I→C×2→R×2→I→C→R→I→C×2 |
| ZZ-KKX/f9b5e873 | **10** | R×5→I→R×5→I（research 散布在两波 implement 间） |
| ZZ-KKX/296a2512 | **9** | **R×9（纯 research，零落地）** |
| ZZ-KKX/dec2ee4b | **8** | R×8（纯 research，零落地） |
| ZZ-KKX/e84fbcc6 | **8** | R×8（纯 research，零落地） |

### 3.2 纯 Research 无落地 Session

**4 个 session** 只 dispatch research，没有任何 implement/check：

| session | research 次数 |
|---|---|
| ZZ-KKX/296a2512 | 9 |
| ZZ-KKX/dec2ee4b | 8 |
| ZZ-KKX/e84fbcc6 | 8 |
| ZZ-KKX/c8936191 | 4 |

> 注：可能在别的 session 落地（task 跨 session）。但单 session 9 次 research 无产出值得审查。

**冗余风险评估**：research 占总调用 65%。高频 research fan-out 可能是每次 task 的多角度调研（合理），也可能是同一问题反复问（浪费）。需抽样看相邻 research 的 prompt 是否有实质区别。

---

## 4. 工作流偏离

### 4.1 dispatch 协议遵守

| 指标 | 值 |
|---|---|
| 带 `Active task:` 前缀 | **63.1%**（101/160）|
| 其中 `Active task: none`（显式声明无 task） | 若干次 |
| 含 hook 注入 marker `trellis-hook-injected` | **0%** |

- **37% dispatch 不带 `Active task` 前缀** → 违反 dispatch 协议（协议要求每条 dispatch 以 `Active task:` 开头）。不合规的 prompt 以 `## Task\n`、`## Context\n`、`Research task:` 等直接开头。
- **injection marker 0%** → transcript 记录的是 hook 注入前的原始 prompt（符合预期：hook mutate 发生在工具执行层，transcript 记录的是 assistant 输出的原始 tool_use input）。

### 4.2 check↔implement 不收敛

| session | 切换次数 | 序列 |
|---|---|---|
| ZZ-KKX/d1e4c592 | **7** | I→I→C→I→C→C→I→C→I→C→C |
| ZZ-KKX/45b01e58 | 3 | I×3→C→I×3→C |

d1e4c592 的 7 次切换说明 check 发现问题→implement 修→check 又发现新问题→循环不收敛。这是 check/implement agent 协作效率的直接信号。

### 4.3 research 写盘行为

19 个同步 research 调用有文件写入（editFileCount > 0）。其中高改动：

| editFileCount | linesAdded | task | prompt 摘要 |
|---|---|---|---|
| 9 | 594 | ledger-metric-calibration | 校准研究 |
| 7 | 1,052 | ledger-metric-calibration | 校准研究 |
| 6 | 757 | ledger-metric-calibration | 校准研究 |
| 5 | 586 | (pre-task) | 数据管线研究 |
| 4 | 833 | ledger-metric-calibration | 校准研究 |

> **路径不可见**（只有 toolStats 计数，没有内部 turn）。trellis-research 被允许写 `research/` 目录。高改动（9 文件/1052 行）可能越出 research/。**需人工核实** `ledger-metric-calibration` task 的 research 产物路径。

### 4.4 Type-意图错配

sync 可见范围内：**0 例高置信**（research prompt 不含 implement 动词）。  
但 async 不可见范围可能存在（如某些 research dispatch 的 prompt 疑似 implement 任务）。小样不够定论，扩全量后重评。

---

## 5. 优化建议

| # | 发现 | 建议 | 改动对象 |
|---|---|---|---|
| **R1** | 13/18 session research ≥4 次，4 个 session 纯 research 无落地 | 主 session 编排 research 前先评估前次 research 结果；dispatch protocol 加"重复 research 前必须引用前次 result" | `.trellis/workflow.md` dispatch protocol |
| **R2** | 1 个 research 跑 66 分钟 | subagent dispatch 加 timeout 参数（如 `max_duration_ms: 600000`），或主 session 设异步超时检测 | `.claude/agents/trellis-research.md` + dispatch 层 |
| **R3** | check↔implement 7 次横跳不收敛 | check agent 加"必须一次列全所有问题"+ implement agent 加"批处理全部 check 发现"，减少往返 | `.claude/agents/trellis-check.md` + `trellis-implement.md` |
| **R4** | 37% dispatch 无 `Active task` 前缀 | hook 在 dispatch 时检测缺前缀并 warn/reject | `.claude/hooks/inject-subagent-context.py` |
| **R5** | research 写盘 19 例，最高 9 文件/1052 行 | 先核实 ledger-metric-calibration 的 research 写了什么；如确认越权，在 research agent prompt 加强 write 边界 | `.claude/agents/trellis-research.md` |

---

## 6. 方法论注记

### 数据可见性边界

| 数据 | 全量 160 | 仅同步 47 |
|---|---|---|
| subagent_type、prompt 全文、status | ✅ | ✅ |
| 调用序列/频率、协议遵守 | ✅ | ✅ |
| token/cache/耗时/`toolStats` | ❌ | ✅ |
| 内部 turn（具体改了哪些文件） | ❌ | ❌ |
| 异步调用最终结局（成功/失败） | ❌ | N/A |

### 数据源

- Claude Code session transcripts: `~/.claude/projects/<proj>/*.jsonl`
- Agent 工具名: `Agent`（非 `Task`）
- subagent 内部 turns 不在主 transcript（isSidechain 全为 false/None）
- 异步 `outputFile` 指向 `/tmp` 临时文件，已删除

### 覆盖率局限

- 同步 47 / 总 160 = **29%** 有完整成本数据。结论基于此 29% 子样本，存在选择偏差（同步/异步行为可能不同）。
- 小样仅 2 个项目。扩全量（+Topo-Reliability 124、Anhui-CIM 12）后结论更稳健。
