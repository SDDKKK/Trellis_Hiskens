# Excel Reading Strategy for AI Agents

> **When to use**: Agent needs to read, compare, or analyze `.xlsx` / `.xls` / `.csv` files during development sessions

## Problem

Claude Code cannot directly read binary Excel files. Need to convert to text-based format first.

## Decision Table

| Scenario | Tool | Why |
|----------|------|-----|
| Quick overview of Excel structure/content | `markitdown` skill | One-shot, no code needed |
| Compare two Excel files column-by-column | `openpyxl` one-liner | Precise cell-level access |
| Data analysis, filtering, aggregation | `polars` | Fast, expressive, handles large files |
| Excel with formulas (need computed values) | `openpyxl` with `data_only=True` | Reads cached formula results |
| Large Excel (>10k rows) | `polars` | Memory-efficient, lazy evaluation |

## Strategy 1: markitdown (Quick Overview)

Best for: understanding structure, checking headers, small files.

```
/markitdown path/to/file.xlsx
```

Converts entire workbook to markdown tables. Limitations:
- Large files produce very long output (context pollution)
- No cell-level type inspection
- No cross-file comparison

## Strategy 2: openpyxl (Precise Comparison)

Best for: cell-by-cell comparison, type checking, targeted extraction.

### Check structure
```python
import openpyxl
wb = openpyxl.load_workbook('file.xlsx', data_only=True)
ws = wb.active
print(f'Sheets: {wb.sheetnames}, rows: {ws.max_row}, cols: {ws.max_column}')
headers = [ws.cell(1, c).value for c in range(1, ws.max_column+1)]
print(headers)
```

### Compare two files
```python
import openpyxl
m = openpyxl.load_workbook('a.xlsx', data_only=True).active
p = openpyxl.load_workbook('b.xlsx', data_only=True).active

for col in range(2, m.max_column+1):
    diffs = 0
    for r in range(2, m.max_row+1):
        mv, pv = m.cell(r, col).value or 0, p.cell(r, col).value or 0
        if abs(float(mv) - float(pv)) > 1e-10: diffs += 1
    if diffs: print(f'{m.cell(1,col).value}: {diffs} rows differ')
```

### Dump specific rows
```python
for r in range(2, min(ws.max_row+1, 7)):
    vals = [ws.cell(r, c).value for c in range(1, ws.max_column+1)]
    print(vals)
```

Key patterns:
- Always use `data_only=True` to get computed values instead of formula strings
- Use `or 0` / `or ''` to handle None cells
- Print headers first to understand column layout before accessing by index

## Strategy 3: polars (Data Analysis)

Best for: filtering, grouping, statistical comparison, large files.

### Read and inspect
```python
import polars as pl
df = pl.read_excel('file.xlsx', sheet_name='Sheet1')
print(df.schema)       # Column names and types
print(df.shape)        # (rows, cols)
print(df.head(5))      # First 5 rows
```

### Compare two result files
```python
import polars as pl
m = pl.read_excel('matlab.xlsx').sort('馈线名称')
p = pl.read_excel('python.xlsx').sort('馈线名称')

for col in ['SAIFI', 'SAIDI']:
    diff = (m[col] - p[col]).abs()
    n = (diff > 1e-10).sum()
    print(f'{col}: {n}/{len(m)} rows differ, max={diff.max():.2e}')
```

### Filter and aggregate
```python
# Find outliers
df.filter(pl.col('SAIFI') > 1.0).select(['馈线名称', 'SAIFI', 'SAIDI'])

# Group statistics
df.group_by('区域').agg(pl.col('SAIFI').mean().alias('avg_SAIFI'))
```

## Anti-Patterns

### Don't: Read entire large Excel into context
```
# BAD: markitdown on 10000-row file → context explosion
/markitdown huge_result.xlsx
```

### Don't: Use pandas when polars is available
```python
# BAD: pandas is slower and not in this project's venv
import pandas as pd

# GOOD: polars is already installed
import polars as pl
```

### Don't: Guess column indices without checking headers
```python
# BAD: assume SAIFI is column 4
saifi = ws.cell(r, 4).value

# GOOD: find column by header name first
headers = {ws.cell(1, c).value: c for c in range(1, ws.max_column+1)}
saifi = ws.cell(r, headers['SAIFI']).value
```

## Environment Notes

- This project's venv (`.venv/bin/python`) has `openpyxl` and `polars` installed
- System Python may lack these packages — always use project venv
- `markitdown` is a Claude Code skill, invoked via `/markitdown`, not a Python package
