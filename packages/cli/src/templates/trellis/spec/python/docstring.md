# Python Docstring & Comment Rules

## Docstring Format

Functions and classes must use standard docstring:

```python
def func(param1, param2=None):
    """
    功能简述

    输入：
        param1: 类型, 说明
        param2: 类型, 可选, 说明

    输出：
        返回类型: 说明
    """
```

## Rules

- Use **`输入：`** for parameters (not `参数:`, `Args:`, `Inputs:`)
- Use **`输出：`** for return values (not `返回:`, `Returns:`)
- Blank line between description and parameter section
- Optional params marked with **`可选`**
- Format: `参数名: 类型, 说明`

## Comments

- No decorative lines:

```python
# BAD
# ============================
# ==== Section Title ====
# ============================

# BAD
# ----------------------------

# GOOD (use blank lines for separation)

# Section logic
x = compute()

# Another section
y = transform(x)
```

- Comments follow "非必要不形成" — only add when genuinely needed
- Never use comment blocks as substitute for docstring
