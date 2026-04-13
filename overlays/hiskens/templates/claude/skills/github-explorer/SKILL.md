---
name: github-explorer
description: >
  Deep-dive analysis of GitHub projects. Use when the user mentions a GitHub repo/project name
  and wants to understand it — triggered by phrases like "帮我看看这个项目", "了解一下 XXX",
  "这个项目怎么样", "分析一下 repo", or any request to explore/evaluate a GitHub project.
  Covers architecture, community health, competitive landscape, and cross-platform knowledge sources.
---

# GitHub Explorer — 项目深度分析

> **Philosophy**: README 只是门面，真正的价值藏在 Issues、Commits 和社区讨论里。

## Workflow

```
[项目名] → [1. 定位 Repo] → [2. 多源采集] → [3. 分析研判] → [4. 结构化输出]
```

### Phase 1: 定位 Repo

1. 用 `web_search.py` 搜索 GitHub 确认完整 org/repo：
   ```bash
   python3 .trellis/scripts/search/web_search.py "site:github.com <project_name>" --platform github
   ```

2. 用 `web_search.py` 补充获取社区链接和非 GitHub 资源：
   ```bash
   python3 .trellis/scripts/search/web_search.py "<project_name> review 评测 使用体验"
   ```

3. 用 `web_fetch.py` 抓取 repo 主页获取基础信息（README、Stars、Forks、License、最近更新）：
   ```bash
   python3 .trellis/scripts/search/web_fetch.py "https://github.com/{org}/{repo}"
   ```

4. （可选）用 `web_map.py` 发现项目文档站点结构：
   ```bash
   python3 .trellis/scripts/search/web_map.py "https://docs.{project}.dev" --depth 2 --limit 50
   ```

### Phase 2: 多源采集（并行）

以下来源**按需检查**，有则采集，无则跳过。按三层搜索策略分配工具：

| 来源 | 采集内容 | 工具 | 调用方式 |
|---|---|---|---|
| GitHub Repo | README、About、Contributors | `web_fetch.py` | `python3 .trellis/scripts/search/web_fetch.py "https://github.com/{org}/{repo}"` |
| GitHub Issues | Top 3-5 高质量 Issue | `web_fetch.py` | `python3 .trellis/scripts/search/web_fetch.py "https://github.com/{org}/{repo}/issues?q=sort:comments-desc"` |
| 中文社区 | 深度评测、使用经验 | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "<project> 评测 使用体验 site:zhihu.com OR site:v2ex.com"` |
| 技术博客 | 技术架构分析 | `web_search.py` + `web_fetch.py` | Search-then-Fetch 模式（见下方） |
| 讨论区 | 用户反馈、槽点 | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "<project> discussion experience reddit OR v2ex"` |
| 竞品分析 | 同赛道对比 | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "<project> vs alternatives compare"` |
| 知识图谱 | DeepWiki/Zread 收录情况 | `web_fetch.py` | 直接抓取 `https://deepwiki.com/{org}/{repo}` 和 `https://zread.ai/{org}/{repo}` |
| 项目依赖库文档 | API 用法、版本特性 | Context7 | `mcp__context7__resolve-library-id` → `mcp__context7__query-docs` |

#### 三层搜索策略（按意图分配）

根据采集需求选择合适的搜索层级，从低到高逐级升级：

| 场景 | 层级 | 工具 | 示例 |
|------|------|------|------|
| **项目依赖库文档** | Layer 0 | Context7 | `mcp__context7__resolve-library-id(libraryName="<lib>", query="<question>")` → `mcp__context7__query-docs(libraryId="<id>", query="<question>")` |
| **快速事实查询** | Layer 1 | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "What is <project>?"` |
| **多源对比/社区声量** | Layer 2 | `web_search.py` + `web_fetch.py` | Search-then-Fetch：先搜索获取 URL 列表，再抓取关键页面全文 |
| **深度技术调研** | Layer 3 | `web_search.py` + `web_fetch.py` | 多轮搜索+抓取，综合分析 |
| **GitHub 代码搜索** | Grok | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "<query>" --platform github` |

#### Search-then-Fetch 模式（Layer 2 标准流程）

用于技术博客、社区讨论等需要全文内容的场景：

```
Step 1: python3 .trellis/scripts/search/web_search.py "<project> architecture deep dive"
        → 返回结构化结果：标题、URL、摘要

Step 2: 从结果中挑选 2-3 个最相关的 URL

Step 3: python3 .trellis/scripts/search/web_fetch.py "<url1>"
        python3 .trellis/scripts/search/web_fetch.py "<url2>"
        → 获取完整 Markdown 内容

Step 4: 综合分析，引用所有来源
```

---

### 抓取降级协议

`web_fetch.py` 内置 3-tier fallback 机制，大部分场景无需手动干预：

1. **Tier 1**: Content negotiation (`text/markdown`) — 免费，最快
2. **Tier 2**: Cloudflare Workers AI toMarkdown — 需 CF 凭证
3. **Tier 3**: Tavily Extract API — 需 TAVILY_API_KEY

当 `web_fetch.py` 所有 tier 均失败时（如严格反爬站点）：
- 尝试 `web_search.py` 获取该页面的摘要信息作为替代
- 如仍需全文，告知用户手动提供内容

**高风险域名**（`mp.weixin.qq.com`, `zhihu.com`, `xiaohongshu.com`）：
- 优先用 `web_search.py` 搜索相关内容摘要，避免直接抓取
- 如需原文，尝试 `web_fetch.py`（Tavily tier 可能成功），失败则标注"无法获取全文"

### Phase 3: 分析研判

基于采集数据进行判断：

- **项目阶段**: 早期实验 / 快速成长 / 成熟稳定 / 维护模式 / 停滞（基于 commit 频率和内容）
- **精选 Issue 标准**: 评论数多、maintainer 参与、暴露架构问题、或包含有价值的技术讨论
- **竞品识别**: 从 README 的 "Comparison"/"Alternatives" 章节、Issues 讨论、以及 web 搜索中提取

### Phase 4: 结构化输出

严格按以下模板输出，**每个模块都必须有实质内容或明确标注"未找到"**。

#### 排版规则（强制）

1. **标题必须链接到 GitHub 仓库**（格式：`# [Project Name](https://github.com/org/repo)`，确保可点击跳转）
2. **标题前后都统一空行**（上一板块结尾 → 空行 → 标题 → 空行 → 内容，确保视觉分隔清晰）
3. **Telegram 空行修复（强制）**：Telegram 会吞掉列表项（`-` 开头）后面的空行。解决方案：在列表末尾与下一个标题之间，插入一行盲文空格 `⠀`（U+2800），格式如下：
   ```
   - 列表最后一项

   ⠀
   **下一个标题**
   ```
   这确保在 Telegram 渲染时标题前的空行不被吞掉。
4. **所有标题加粗**（emoji + 粗体文字）
5. **竞品对比必须附链接**（GitHub / 官网 / 文档，至少一个）
6. **社区声量必须具体**：引用具体的帖子/推文/讨论内容摘要，附原始链接。不要写"评价很高"、"热度很高"这种概括性描述，要写"某某说了什么"或"某帖讨论了什么具体问题"
7. **信息溯源原则**：所有引用的外部信息都应附上原始链接，让读者能追溯到源头

#### 输出模板

```markdown
# [{Project Name}]({GitHub Repo URL})

**🎯 一句话定位**

{是什么、解决什么问题}

**⚙️ 核心机制**

{技术原理/架构，用人话讲清楚，不是复制 README。包含关键技术栈。}

**📊 项目健康度**

- **Stars**: {数量}  |  **Forks**: {数量}  |  **License**: {类型}
- **团队/作者**: {背景}
- **Commit 趋势**: {最近活跃度 + 项目阶段判断}
- **最近动态**: {最近几条重要 commit 概述}

**🔥 精选 Issue**

{Top 3-5 高质量 Issue，每条包含标题、链接、核心讨论点。如无高质量 Issue 则注明。}

**✅ 适用场景**

{什么时候该用，解决什么具体问题}

**⚠️ 局限**

{什么时候别碰，已知问题}

**🆚 竞品对比**

{同赛道项目对比，差异点。每个竞品必须附 GitHub 或官网链接，格式示例：}
- **vs [GraphRAG](https://github.com/microsoft/graphrag)** — 差异描述
- **vs [RAGFlow](https://github.com/infiniflow/ragflow)** — 差异描述

**🌐 知识图谱**

- **DeepWiki**: {链接或"未收录"}
- **Zread.ai**: {链接或"未收录"}

**🎬 Demo**

{在线体验链接，或"无"}

**📄 关联论文**

{arXiv 链接，或"无"}

**📰 社区声量**

**X/Twitter**

{具体引用推文内容摘要 + 链接，格式示例：}
- [@某用户](链接): "具体说了什么..."
- [某讨论串](链接): 讨论了什么具体问题...
{如未找到则注明"未找到相关讨论"}

**中文社区**

{具体引用帖子标题/内容摘要 + 链接，格式示例：}
- [知乎: 帖子标题](链接) — 讨论了什么
- [V2EX: 帖子标题](链接) — 讨论了什么
{如未找到则注明"未找到相关讨论"}

**💬 我的判断**

{主观评价：值不值得投入时间，适合什么水平的人，建议怎么用}
```

## Execution Notes

- 优先使用 `web_search.py` + `web_fetch.py` 进行 GitHub 信息采集
- 社区声量和竞品分析使用 `web_search.py`（Layer 2），需要全文时追加 `web_fetch.py`
- 深度技术调研使用多轮 `web_search.py` + `web_fetch.py`（Layer 3）
- 并行采集不同来源以提高效率（独立的 Bash 调用和 MCP 调用可并行）
- 所有链接必须真实可访问，不要编造 URL
- 中文输出，技术术语保留英文

### 降级策略

| 工具不可用 | 降级方案 |
|---|---|
| `web_search.py` 不可用（GROK_API_KEY 未配置） | 使用 agent 自身知识回答（标注知识截止日期） |
| `web_fetch.py` 全部 tier 失败 | `web_search.py` 获取摘要；告知用户手动提供全文 |
| `web_map.py` 不可用（TAVILY_API_KEY 未配置） | 跳过文档站点结构发现，不影响核心流程 |
| Context7 库未收录 | 使用 agent 自身知识回答（标注知识截止日期） |
| 所有外部工具不可用 | 基于 agent 自身知识回答（标注知识截止日期） |

## 输出自检清单（强制，每次输出前逐条核对）

输出报告前，**必须逐条检查以下项目**，全部通过才可发送：

- [ ] **标题链接**：`# [Project Name](GitHub URL)` 格式，可点击跳转
- [ ] **标题空行**：每个粗体标题（`**🎯 ...**`）前后各有一个空行
- [ ] **Telegram 空行**：每个列表块末尾与下一个标题之间有盲文空格 `⠀` 行（防止 Telegram 吞空行）
- [ ] **Issue 链接**：精选 Issue 每条都有完整 `[#号 标题](完整URL)` 格式
- [ ] **竞品链接**：每个竞品都附 `[名称](GitHub/官网链接)`
- [ ] **社区声量链接**：每条引用都有 `[来源: 标题](URL)` 格式
- [ ] **无空泛描述**：社区声量部分没有"评价很高"、"热度很高"等概括性描述
- [ ] **信息溯源**：所有外部引用都附原始链接

## Dependencies

本 Skill 依赖以下工具和脚本：

| 依赖 | 类型 | 用途 | 必需 |
|------|------|------|------|
| `web_search.py` | 项目脚本 (`.trellis/scripts/search/`) | Grok API 搜索（GitHub 定位、代码搜索） | 否（可用 agent 知识替代） |
| `web_fetch.py` | 项目脚本 (`.trellis/scripts/search/`) | 3-tier Markdown 抓取（repo 页面、Issue、博客） | 是 |
| `web_map.py` | 项目脚本 (`.trellis/scripts/search/`) | 站点结构发现（文档站点） | 否 |
| `resolve-library-id` / `query-docs` | Context7 MCP | 项目依赖库文档查询（Layer 0） | 否 |

### 环境变量

参见 `.trellis/scripts/search/API_CONFIG.md`。最低可用配置：`TAVILY_API_KEY`（启用 `web_fetch.py` tier 3 + `web_map.py`）。
