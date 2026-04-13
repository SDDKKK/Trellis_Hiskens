# Task: [任务名称]

> **提示**: 这是标准 PRD 模板，基于 Plan Agent 的最佳实践。填写时确保每个章节都具体、可验证。

## Overview

[用 2-3 句话简要描述这个功能是什么，解决什么问题]

**示例**:
```
实现 API 端点的速率限制功能，防止滥用。使用滑动窗口算法，
限制每个 IP 地址每分钟最多 100 次请求。
```

## Premises (验证过的前提)

[列出经过 Premise Challenge 验证的假设]

**填写指导**:
- 记录用户确认或调整后的前提
- 标记状态：[Confirmed] / [Adjusted] / [Rejected]

**示例**:
```
- [Confirmed] 当前 solver 性能不足，处理 1000+ 节点网络超过 5 分钟
- [Adjusted] 不需要新建模块，扩展现有 OptimizationCore 即可
- [Rejected] 不是最高优先级，先完成数据导入功能
```

**你的前提**:
- [Confirmed/Adjusted/Rejected] [前提 1]
- [Confirmed/Adjusted/Rejected] [前提 2]

## Scope Mode

[根据任务上下文选择的 scope 模式]

**可选模式**:
- **EXPANSION**: 全新功能，自由添加新能力
- **SELECTIVE_EXPANSION**: 增强现有功能，谨慎扩展
- **HOLD_SCOPE**: Bug 修复/重构，不添加新功能
- **REDUCTION**: 有 deadline，最小可行实现

**你的选择**: [选择一个模式]

## Requirements

[列出具体的功能需求，每条需求应该清晰、可实现]

**填写指导**:
- ✅ 具体：说明"做什么"，而不是"为什么"
- ✅ 可验证：能够明确判断是否完成
- ✅ 完整：包含所有必要的细节
- ❌ 避免模糊：不要用"优化"、"改进"等模糊词汇

**示例**:
```
- 实现速率限制中间件，使用滑动窗口算法
- 限制：每个 IP 地址每分钟最多 100 次请求
- 超过限制时返回 HTTP 429 状态码
- 在 429 响应中包含 Retry-After 头部
- 支持从 X-Forwarded-For 头部提取真实 IP
```

**你的需求**:
- [ ] [需求 1]
- [ ] [需求 2]
- [ ] [需求 3]

## Acceptance Criteria

[列出可验证的验收标准，用于判断任务是否完成]

**填写指导**:
- ✅ 可测试：能够通过测试验证
- ✅ 具体：明确的成功标准
- ✅ 完整：覆盖所有重要方面
- 使用 checkbox 格式，便于跟踪

**示例**:
```
- [ ] 速率限制中间件已实现并集成到 API 路由
- [ ] 滑动窗口算法正确跟踪请求时间
- [ ] 超过限制时返回 429 状态码
- [ ] Retry-After 头部正确计算剩余时间
- [ ] 测试覆盖正常流量和限流场景
- [ ] 正常流量无性能下降（<5ms 延迟）
- [ ] 文档更新，说明速率限制策略
```

**你的验收标准**:
- [ ] [标准 1]
- [ ] [标准 2]
- [ ] [标准 3]

## Technical Notes

[记录技术考虑、设计决策、现有模式、依赖关系等]

**填写指导**:
- 参考现有代码模式
- 说明技术选型理由
- 列出依赖的库或模块
- 标注潜在的技术风险

**示例**:
```
### 现有模式
- 参考 `src/api/middleware/auth.py` 的中间件模式
- 使用 Redis 存储请求计数（支持分布式部署）

### 技术选型
- 滑动窗口算法：使用 Redis ZSET 存储请求时间戳
- IP 提取：优先使用 X-Forwarded-For，回退到 request.remote_addr

### 依赖
- redis-py >= 4.0.0
- 需要 Redis 服务器运行

### 风险
- Redis 不可用时的降级策略（考虑内存缓存）
- 分布式环境下的时钟同步问题
```

**你的技术注意事项**:
```
[在这里填写技术细节]
```

## Temporal Notes (Moderate/Complex 任务可选)

[时序推演：按实现时间线预测问题]

**填写指导**:
- 仅 Moderate/Complex 任务需要
- 按小时分段预测实现过程

**示例**:
```
- HOUR 1 (基础): 需要 Redis 连接配置，理解滑动窗口算法
- HOUR 2-3 (核心): 歧义：限制应用于每个端点还是全局？（明确：全局）
- HOUR 4-5 (集成): 意外：X-Forwarded-For 可能有多个 IP（使用第一个）
- HOUR 6+ (收尾): 后悔：应该从一开始就添加监控钩子
```

**你的时序预测**:
```
[在这里填写]
```

## Error & Rescue Map (Moderate/Complex 任务可选)

[失败模式分析：预测错误和处理策略]

**填写指导**:
- 仅 Moderate/Complex 任务需要
- 列出主要操作的失败场景

**示例**:

| Operation | Failure Mode | Impact | Rescue Strategy |
|-----------|--------------|--------|-----------------|
| XML 解析 | 文件不存在 | 馈线数据缺失 | Skip + log warning |
| FMEA 计算 | 矩阵奇异 | 结果为 NaN | Fallback to zero |
| Solver 迭代 | 超预算无解 | 返回空列表 | Return partial solution |

**你的错误映射**:

| Operation | Failure Mode | Impact | Rescue Strategy |
|-----------|--------------|--------|-----------------|
| [操作 1] | [失败模式] | [影响] | [处理策略] |

## Architecture (3+ 模块时可选)

[架构快照：数据流和依赖关系]

**填写指导**:
- 仅涉及 3+ 模块或复杂数据流时需要
- 使用 ASCII 图表示数据流

**示例**:
```
数据流:
  HTTP Request → Rate Limiter Middleware → Redis (check count)
                                        → Handler (if allowed)
                                        → 429 Response (if exceeded)

依赖关系:
  - 现有: Redis client, middleware framework
  - 新增: RateLimiter class, sliding window logic

边界条件:
  - 空 IP (X-Forwarded-For 缺失): 使用 request.remote_addr
  - Redis 不可用: Fail open (允许请求, 记录错误)
  - 时钟偏移: 使用服务器时间，不用客户端时间
```

**你的架构**:
```
[在这里填写 ASCII 图和说明]
```

## Test Plan (Optional -- required when task.json tdd=true)

[List behaviors and edge cases to test]

- [ ] [Behavior 1]: Input X -> Expected output Y
- [ ] [Edge case 1]: Empty input -> Expected behavior
- [ ] [Error scenario 1]: Invalid parameter -> Expected exception

## Out of Scope

[明确列出不包含在本次任务中的内容，防止范围蔓延]

**填写指导**:
- 列出相关但不在本次实现的功能
- 说明为什么不包含（可以简要说明）
- 帮助后续任务规划

**示例**:
```
- 按用户的速率限制（本次只实现按 IP）
- 动态调整速率限制配置（使用固定配置）
- 速率限制监控面板（后续单独实现）
- 不同端点的不同限制（本次统一限制）
```

**你的范围界定**:
- [ ] [不包含的内容 1]
- [ ] [不包含的内容 2]

---

## 填写检查清单

完成 PRD 后，检查以下项目：

- [ ] **Overview** 清晰简洁，非技术人员也能理解
- [ ] **Requirements** 每条都具体、可实现、可验证
- [ ] **Acceptance Criteria** 包含所有重要方面，可测试
- [ ] **Technical Notes** 包含必要的技术细节和设计决策
- [ ] **Out of Scope** 明确界定范围，防止范围蔓延
- [ ] 没有使用"优化"、"改进"等模糊词汇
- [ ] 所有需求都有对应的验收标准

---

## 常见错误

### ❌ 错误示例 1: 需求模糊

```markdown
## Requirements
- 优化性能
- 改进用户体验
- 修复 bug
```

**问题**: 无法判断"完成"的标准

### ✅ 正确示例 1

```markdown
## Requirements
- 将 BusBranch.by_type() 查询时间从 2.5s 降低到 <500ms
- 为 type 字段添加数据库索引
- 添加查询结果缓存（TTL: 5 分钟）
```

### ❌ 错误示例 2: 缺少验收标准

```markdown
## Acceptance Criteria
- [ ] 功能实现
- [ ] 测试通过
```

**问题**: 太笼统，无法验证

### ✅ 正确示例 2

```markdown
## Acceptance Criteria
- [ ] BusBranch.by_type() 查询时间 <500ms（10k 记录）
- [ ] 数据库索引创建成功，explain 显示使用索引
- [ ] 缓存命中率 >80%（生产环境监控）
- [ ] 单元测试覆盖率 >90%
- [ ] 集成测试验证缓存失效逻辑
```

### ❌ 错误示例 3: 范围不清

```markdown
## Requirements
- 实现用户认证
- 添加权限管理
- 支持 OAuth
- 实现审计日志
```

**问题**: 范围过大，应该拆分

### ✅ 正确示例 3

```markdown
## Requirements
- 实现基本的用户名/密码认证
- 支持登录、登出功能
- 生成 JWT token（有效期 24 小时）

## Out of Scope
- 权限管理（后续任务）
- OAuth 集成（后续任务）
- 审计日志（后续任务）
- 密码重置功能（后续任务）
```

---

## 参考资源

- **Plan Agent 文档**: `.claude/agents/plan.md`
- **Multi-Agent Pipeline 指南**: `.trellis/docs/multi-agent-pipeline.md`
- **Workflow 文档**: `.trellis/workflow.md`

---

**记住**: 好的 PRD 是成功实施的基础。花 10 分钟写清楚 PRD，可以节省 1 小时的返工时间。
