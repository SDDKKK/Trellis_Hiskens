# 跨语言翻译指南

> **适用场景**: Python → Java, MATLAB → Python, 或其他语言间的算法翻译

## 核心原则

### 1. 算法保真
**目标**: 数值结果完全一致（浮点精度范围内）

**验证方法**:
- 逐行对比源代码和目标代码
- 编写验证脚本对比输出结果
- 设置严格的数值阈值（如 ASAI < 1e-6, 其他 < 1e-4）

### 2. 语言惯用法
**原则**: 使用目标语言的惯用模式，而非直译

**示例**:
```python
# Python
result = [x for x in data if x > 0]

# Java - 不要直译为 Stream API（Java 8 约束）
List<Integer> result = new ArrayList<Integer>();
for (int x : data) {
    if (x > 0) {
        result.add(x);
    }
}
```

### 3. 模块化设计
**原则**: 目标代码应比源代码更模块化

**示例**:
- Python 单文件 → Java 多模块（common/data/domain/export）
- Python tuple 返回 → Java POJO
- Python 全局函数 → Java 静态工具类

## Python → Java 映射表

### 数据结构

| Python | Java | 说明 |
|--------|------|------|
| `list` | `ArrayList<T>` | 动态数组 |
| `tuple` | POJO 类 | 不可变数据组合 |
| `dict` | `HashMap<K, V>` | 键值对 |
| `set` | `HashSet<T>` | 无序集合 |
| `np.ndarray` | `double[][]` | 多维数组 |
| `pl.DataFrame` | POI + `HashMap` | 表格数据 |

### 数组操作

| Python (NumPy) | Java | 说明 |
|----------------|------|------|
| `arr[:, col]` | `ArrayUtils.getColumn(arr, col)` | 列切片 |
| `arr[mask]` | 显式循环 + 条件判断 | Boolean masking |
| `np.sum(arr)` | `ArrayUtils.sum(arr)` | 求和 |
| `np.where(cond)` | `ArrayUtils.where(cond)` | 条件索引 |
| `np.nan` | `Double.NaN` | 非数值 |
| `np.isnan(x)` | `Double.isNaN(x)` | NaN 检查 |
| `np.lexsort((a, b))` | `Arrays.sort` + `Comparator` | 多键排序 |

### 集合操作

| Python | Java | 说明 |
|--------|------|------|
| `set1 & set2` | `set1.retainAll(set2)` | 交集（会修改 set1） |
| `set1 - set2` | `set1.removeAll(set2)` | 差集（会修改 set1） |
| `set1 \| set2` | `set1.addAll(set2)` | 并集（会修改 set1） |
| `len(set1)` | `set1.size()` | 大小 |

**注意**: Java 的集合操作会修改原集合，需要先复制：
```java
Set<Integer> intersection = new HashSet<Integer>(set1);
intersection.retainAll(set2);
```

### DataFrame 操作

| Python (Polars) | Java (POI) | 说明 |
|-----------------|------------|------|
| `pl.read_excel(file, sheet_name)` | `XSSFWorkbook` + 逐行读取 | Excel 读取 |
| `df.select(cols)` | 循环 + 列索引 | 列选择 |
| `df.filter(cond)` | 循环 + 条件判断 | 行过滤 |
| `df.group_by().agg()` | `HashMap` + 手动聚合 | 分组聚合 |
| `df.unique()` | `HashSet` 或 `TreeMap` | 去重 |

### 图算法

| Python (NetworkX) | Java (JGraphT) | 说明 |
|-------------------|----------------|------|
| `nx.DiGraph()` | `DefaultDirectedGraph<Integer, DefaultEdge>` | 有向图 |
| `G.add_edge(u, v)` | `G.addEdge(u, v)` | 添加边 |
| `nx.bfs_tree(G, source)` | 自定义 BFS 实现 | BFS 遍历 |
| `(u, v)` 作为字典键 | `(long)u << 32 \| v` | 边的唯一标识 |

### 边映射 (FN,TN)→index 的重复键行为（高危）

当图中存在并联设备（同一对节点间多条边），(FN,TN) 键会重复：

| 语言 | 数据结构 | 重复键行为 | 安全？ |
|------|---------|-----------|--------|
| Python | `dict` 推导式 | 覆盖（保留最后） | ✅ |
| Java | `HashMap.put()` | 覆盖（保留最后） | ✅ |
| MATLAB | `sparse(FN, TN, idx)` | **求和** | ❌ 越界 |

```matlab
% ❌ BAD — 重复 (FN,TN) 的 idx 被求和，如 423+424=847 > line_num
conn = sparse(line(:,FN), line(:,TN), (1:N)', maxFN, maxTN);

% ✅ GOOD — 去重后再建 sparse
[~, ui] = unique([line(:,FN), line(:,TN)], 'rows', 'last');
conn = sparse(line(ui,FN), line(ui,TN), ui, maxFN, maxTN);
```

**规则**：MATLAB 中用 `sparse` 做键值映射时，必须先 `unique` 去重。

### 返回值

| Python | Java | 说明 |
|--------|------|------|
| `return a, b, c` | `return new Result(a, b, c)` | 多返回值 → POJO |
| `x, y = func()` | `Result r = func(); int x = r.x; int y = r.y;` | 元组解包 → 字段访问 |

## 常见陷阱

### 1. 索引约定
**Python/Java**: 0-based
**MATLAB**: 1-based

**翻译时保持一致**: 如果源代码是 0-based，目标代码也用 0-based

### 2. 整数除法
```python
# Python 3
result = 5 / 2  # 2.5 (浮点除法)

# Java
double result = 5 / 2;      // 2.0 (整数除法)
double result = 5.0 / 2.0;  // 2.5 (浮点除法)
```

### 3. 数组复制
```python
# Python - 浅拷贝
arr2 = arr1[:]

# Java - 需要显式复制
double[] arr2 = Arrays.copyOf(arr1, arr1.length);
```

### 4. NaN 比较
```python
# Python
if x == np.nan:  # 永远为 False

# Java
if (x == Double.NaN)  // 永远为 false
if (Double.isNaN(x))  // 正确
```

### 5. 集合修改
```python
# Python - 不修改原集合
intersection = set1 & set2

# Java - 修改原集合
set1.retainAll(set2);  // set1 被修改了！
```

### 6. Python Falsy vs Java Null（高频陷阱）

**背景**: Python 的 `if not x` 同时拦截 `None` 和空字符串 `""`，Java 的 `x == null` 只拦截 null。

**典型场景**: XML 解析中 `rdf:resource` 属性可能为空字符串或 `"#"`，经 `stripHash()` 后变为 `""`。

```python
# Python — 安全：None 和 "" 都被拦截
cn_ids = [term.get("connectivity_node_id") for t in terminals]
if len(cn_ids) != 2 or not cn_ids[0] or not cn_ids[1]:
    continue  # 跳过无效
```

```java
// ❌ Bad — 只检查 null，空字符串 "" 会通过
if (cn0 == null || cn1 == null) continue;

// ✅ Good — 同时检查 null 和空字符串
if (cn0 == null || cn0.isEmpty() || cn1 == null || cn1.isEmpty()) continue;
```

**规则**: 翻译 Python 的 `if not x` / `if x` 时，Java 侧必须同时检查 `null` 和 `isEmpty()`。

**受影响的典型方法**:
- BFS 遍历中的 CN ID 检查
- 图构建中的 equipment_id / node_id 检查
- 负荷收集中的 CN ID 检查

## 验证策略

### 1. 单元测试
**方法**: 对关键算法编写单元测试

```java
@Test
public void testFmeaCalculation() {
    // 准备测试数据
    double[][] line = loadTestData();

    // 执行计算
    FmeaResult result = FmeaCalculator.fmea(line, ...);

    // 验证结果
    assertEquals(expectedASAI, result.asai, 1e-6);
}
```

### 2. 端到端验证
**方法**: 编写验证脚本对比完整输出

```python
# scripts/compare_java_matlab.py
def compare_results(matlab_file, java_file):
    matlab_data = load_matlab_results(matlab_file)
    java_data = load_java_results(java_file)

    for feeder in matlab_data.keys():
        for metric in ['ASAI', 'AENS', 'SAIFI', 'SAIDI']:
            diff = abs(matlab_data[feeder][metric] - java_data[feeder][metric])
            threshold = 1e-6 if metric == 'ASAI' else 1e-4
            assert diff < threshold, f"{feeder} {metric} 超出阈值"
```

### 3. 中间结果对比
**方法**: 在关键步骤输出中间结果，逐步验证

```java
// 调试模式：输出中间结果
if (DEBUG) {
    System.out.println("Area assignment: " + Arrays.toString(area));
    System.out.println("Impact matrix shape: " + impactMatrix.length);
}
```

## 性能考虑

### Python → Java 性能提升点

1. **并行处理**: Python GIL 限制 → Java 真正的多线程
   ```java
   ExecutorService executor = Executors.newFixedThreadPool(4);
   List<Future<Result>> futures = executor.invokeAll(tasks);
   ```

2. **数组操作**: NumPy → 原生 Java 数组（减少开销）
   ```java
   double[][] matrix = new double[rows][cols];  // 连续内存
   ```

3. **类型安全**: 动态类型 → 静态类型（编译时优化）

### 性能陷阱

1. **频繁装箱/拆箱**: 使用基本类型数组而非包装类
   ```java
   // ✅ Good
   double[] arr = new double[1000];

   // ❌ Bad - 频繁装箱
   List<Double> list = new ArrayList<Double>();
   ```

2. **字符串拼接**: 循环中使用 `StringBuilder`
   ```java
   StringBuilder sb = new StringBuilder();
   for (String s : strings) {
       sb.append(s);
   }
   ```

## 文档要求

### 源代码映射注释
```java
/**
 * 计算区域负荷统计
 *
 * 对应 Python: aggregator.py aggregate_region_load_stats()
 */
public static RegionStats.RegionLoadStats aggregateRegionLoadStats(...) {
    // ...
}
```

### 算法关键点注释
```java
// BFS 遍历计算下游负荷点（按拓扑顺序）
// 对应 Python: graph_engine.py bfs_node_ordered()
List<Integer> orderedNodes = GraphEngine.bfsNodeOrdered(G, sourceNode);
```

### 数据结构映射注释
```java
/**
 * 故障影响详情
 *
 * 对应 Python: fmea_calculator.py FaultImpactDetails dataclass
 */
public class FaultImpactDetails {
    public int[][] impactCategory;  // Python: np.ndarray (N, M)
    // ...
}
```

## 检查清单

翻译完成后检查：

- [ ] 所有算法逻辑与源代码一致
- [ ] 数值结果验证通过（设定阈值）
- [ ] 边界条件处理正确（空数组、NaN、null）
- [ ] 性能可接受（不比源代码慢太多）
- [ ] 代码符合目标语言规范
- [ ] 关键方法有源代码映射注释
- [ ] 编写了验证脚本
- [ ] 文档说明了翻译的映射关系

## 相关文档

- [Java 开发规范](../java/index.md)
- [Python 质量规范](../python/quality-guidelines.md)
- [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)
