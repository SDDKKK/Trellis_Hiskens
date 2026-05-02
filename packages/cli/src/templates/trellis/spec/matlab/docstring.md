# MATLAB Docstring Rules

## Function Docstring Format

```matlab
function [output1, output2] = func(param1, param2)
    %
    %   功能简述
    %
    % 输入：
    %    param1: 类型, 说明
    %    param2: 类型, 可选, 说明
    %
    % 输出：
    %    output1: 说明
    %    output2: 说明
```

## Rules

- Use **`输入：`** for parameters (not `参数:`, `Inputs:`)
- Use **`输出：`** for return values (not `返回:`, `Outputs:`)
- Blank line between description and parameter section
- Optional params marked with **`可选`**

## Comment Rules

No decorative lines:

```matlab
% BAD
% =============================
% ==== Section Title ====
% =============================

% BAD
% -----------------------------

% GOOD
% Section logic
x = compute();

% Another section
y = transform(x);
```

## Script Header

For scripts (not functions), use a brief header:

```matlab
% fmea_new.m
% FMEA可靠性分析主程序 — 改进版
%
% 依赖：read_data_all.m, ReliabilityIndexCal.m

clear; clc;
```
