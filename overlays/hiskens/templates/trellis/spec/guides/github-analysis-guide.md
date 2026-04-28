# GitHub Repository Analysis Guide

> **Purpose**: When analyzing GitHub repositories (reference implementations, competitive research, dependency evaluation), follow this methodology to ensure comprehensive and high-quality analysis.

## Core Principles

1. **README is just the facade** — Real value lies in Issues, Commits, and community discussions
2. **Multi-source verification** — Cross-validate official info + community sentiment + competitor comparison
3. **Source attribution** — All references must include original links for traceability
4. **Avoid vague statements** — Don't write "highly rated"; write "User X said Y in post Z"

## Analysis Dimensions

### 1. Project Positioning

**Goal**: Explain in one sentence "what it is + what problem it solves"

**Method**:
- Read README's first paragraph and About description
- Check GitHub Topics tags
- Search community descriptions of the project

**Output**:
```
One-line positioning: {what it is, what problem it solves}
Core mechanism: {technical principles/architecture in plain language, including key tech stack}
```

### 2. Project Health

**Signal indicators**:
- **Stars/Forks/License** — Community recognition
- **Team/Author background** — Individual project vs company-backed vs open source org
- **Commit trends** — Activity in last 3 months (check `/commits` page)
- **Recent activity** — Summary of last 3-5 important commits

**Project stage assessment**:
- **Early experiment**: < 100 stars, irregular commits, weak documentation
- **Rapid growth**: 100-1k stars, high-frequency commits, active Issues
- **Mature stable**: 1k+ stars, regular maintenance, has roadmap
- **Maintenance mode**: High stars but sparse commits, mainly bug fixes
- **Stagnant**: No commits for 6 months, Issues unanswered

### 3. Quality Signals (Curated Issues)

**Why check Issues**:
- Expose architectural problems and design tradeoffs
- Show maintainer response speed and attitude
- Discover undocumented limitations and known issues

**Curation criteria** (Top 3-5):
- High comment count (> 10)
- Maintainer participation
- Expose architectural issues or design decisions
- Contain valuable technical discussions (e.g., performance optimization, API design)

**How to fetch**:
```bash
# Sort by comment count
python3 .trellis/scripts/search/web_fetch.py "https://github.com/{org}/{repo}/issues?q=sort:comments-desc"
```

### 4. Use Cases vs Limitations

**Use cases**:
- When should you use this project?
- What specific problems does it solve?
- What scale/scenarios is it suitable for?

**Limitations**:
- When should you avoid it?
- Known issues (extracted from Issues)
- Technical debt or architectural constraints

### 5. Competitor Comparison

**Goal**: Find projects in the same space, clarify differences

**How to find competitors**:
1. README's "Comparison" / "Alternatives" section
2. Comparison discussions in Issues
3. Search `<project> vs alternatives compare`

**Output format** (each competitor must have a link):
```markdown
- **vs [GraphRAG](https://github.com/microsoft/graphrag)** — Difference description
- **vs [RAGFlow](https://github.com/infiniflow/ragflow)** — Difference description
```

### 6. Community Sentiment

**Goal**: Understand real user feedback and pain points

**Sources**:
- **X/Twitter**: Tech community discussions
- **Chinese communities**: Zhihu, V2EX, Xiaohongshu
- **Reddit**: r/programming, r/MachineLearning, etc.
- **Tech blogs**: Medium, Dev.to, personal blogs

**Quality standards**:
- ❌ Don't write "highly rated", "very popular" (vague statements)
- ✅ Quote specific post/tweet content summary + link
- ✅ Format: `[@username](link): "specific quote..."`

## Tool Selection Strategy

Choose appropriate tools based on information type:

| Information Type | Recommended Tool | Invocation |
|-----------------|------------------|------------|
| **GitHub basic info** | `web_fetch.py` | `python3 .trellis/scripts/search/web_fetch.py "https://github.com/{org}/{repo}"` |
| **GitHub Issues** | `web_fetch.py` | `python3 .trellis/scripts/search/web_fetch.py "https://github.com/{org}/{repo}/issues?q=sort:comments-desc"` |
| **GitHub code search** | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "site:github.com <query>" --platform github` |
| **Docs site structure** | `web_map.py` | `python3 .trellis/scripts/search/web_map.py "https://docs.{project}.dev" --depth 2` |
| **Community discussions/reviews** | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "<project> review experience"` |
| **Competitor comparison** | `web_search.py` | `python3 .trellis/scripts/search/web_search.py "<project> vs alternatives compare"` |
| **Deep technical research** | `web_search.py` + `web_fetch.py` | Multiple rounds of search + fetch for comprehensive analysis |
| **Project dependency docs** | Context7 | `mcp__context7__resolve-library-id` → `mcp__context7__query-docs` |

### Search-then-Fetch Pattern

For scenarios requiring full-text content (tech blogs, in-depth reviews):

```
Step 1: web_search.py to get URL list
Step 2: Select 2-3 most relevant URLs
Step 3: web_fetch.py to extract full text
Step 4: Synthesize analysis, cite all sources
```

## Fallback Strategy

| Tool Unavailable | Fallback Plan |
|-----------------|---------------|
| `web_search.py` unavailable | Use agent knowledge with caveat (knowledge cutoff limitation) |
| `web_fetch.py` all tiers fail | Use web_search.py for summary; inform user to provide full text manually |
| `web_map.py` unavailable | Skip docs site structure discovery, doesn't affect core analysis |
| Context7 library not indexed | Use agent knowledge with caveat (knowledge cutoff limitation) |

**High-risk domains** (WeChat, Zhihu, Xiaohongshu):
- Prioritize `web_search.py` for content summaries
- If original text needed, try `web_fetch.py` (Tavily tier may succeed)
- If fails, mark as "full text unavailable"

## Common Mistakes

### ❌ Mistake 1: Only reading README

**Problem**: README is marketing copy, doesn't reflect real issues

**Correct approach**:
- Check high-engagement discussions in Issues
- Check bug fixes and breaking changes in Commits
- Search for real user experiences in community

### ❌ Mistake 2: Vague descriptions

**Problem**:
```markdown
Community sentiment: Highly rated, very popular
```

**Correct approach**:
```markdown
Community sentiment:
- [@username](link): "Used in production for 3 months, memory usage 40% lower than X"
- [Zhihu: Post title](link): Discussed performance comparison with Y, conclusion is...
```

### ❌ Mistake 3: Competitors without links

**Problem**:
```markdown
Competitors: GraphRAG, RAGFlow
```

**Correct approach**:
```markdown
- **vs [GraphRAG](https://github.com/microsoft/graphrag)** — Difference description
- **vs [RAGFlow](https://github.com/infiniflow/ragflow)** — Difference description
```

### ❌ Mistake 4: Concluding without checking Issues

**Problem**: Judging "project is mature" based on README alone

**Correct approach**:
- Check number and types of open issues
- Check maintainer response speed
- Check for long-standing unresolved critical bugs

## Output Quality Checklist

After analysis, verify each item:

- [ ] One-line positioning is clear, understandable to non-technical people
- [ ] Core mechanism explains "why designed this way", not just copying README
- [ ] Project health has concrete data (Stars/Forks/recent commit time)
- [ ] Curated Issues explain "why curated" (not just picking 3 random ones)
- [ ] Use cases and limitations have specific examples
- [ ] Competitor comparison has links for each, specific differences
- [ ] Community sentiment has specific quotes + links, no vague statements
- [ ] All external information is traceable (has links)

## Use Case Scenarios

### Scenario 1: Reference Implementation

**Task**: Implementing a feature, want to reference an open source project's approach

**Analysis focus**:
- Core mechanism (technical principles)
- Curated Issues (design tradeoffs and known issues)
- Code quality (judged through Commits and PRs)

### Scenario 2: Dependency Evaluation

**Task**: Deciding whether to introduce a library as dependency

**Analysis focus**:
- Project health (maintenance status)
- Limitations (known issues and compatibility)
- Competitor comparison (whether better alternatives exist)

### Scenario 3: Competitive Research

**Task**: Understanding other solutions in the same space

**Analysis focus**:
- Competitor comparison (differences and pros/cons)
- Community sentiment (real user feedback)
- Use cases (optimal scenarios for each)

## Relationship to Other Guides

- **[External Search Strategy Guide](./search-guide.md)** — Search tools and strategies used by this guide
- **[Codebase Search Guide](./codebase-search-guide.md)** — For analyzing local code
- **[Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)** — After referencing implementation, how to reuse in this project

## Complete Example

See nocturne_memory project analysis example in `.claude/skills/github-explorer/SKILL.md`.

---

**Core Philosophy**: Analyzing GitHub repositories is not about writing reports, but about making better technical decisions.
