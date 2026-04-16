#!/usr/bin/env python3
# Created Time: 2026-04-16
# Content: 解析模块：Sub2API 用量响应解析
#
# 解析 Sub2API `/v1/usage` 返回的 JSON，输出可读摘要或标准化 JSON。
# 支持从 stdin、文件或直接携带 API Key 请求接口。

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_URL = "https://sub2api.qianfuv.fun/v1/usage"
DEFAULT_API_KEY_ENV = "SUB2API_KEY"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
GRAY = "\033[90m"
RESET = "\033[0m"


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数

    输入：
        无

    输出：
        argparse.Namespace: 解析后的命令行参数
    """
    parser = argparse.ArgumentParser(description="Parse Sub2API usage response")
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Read raw usage JSON from file instead of stdin",
    )
    parser.add_argument(
        "--raw-json",
        help="Read raw usage JSON directly from the command line",
    )
    parser.add_argument(
        "--api-key",
        help="Fetch usage data from Sub2API with the provided x-api-key",
    )
    parser.add_argument(
        "--api-key-env",
        default=DEFAULT_API_KEY_ENV,
        help=(
            "Read API key from this env var when --api-key is omitted "
            f"(default: {DEFAULT_API_KEY_ENV})"
        ),
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Usage endpoint URL (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "statusline"],
        default="text",
        help="Output format",
    )
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    """
    加载原始响应负载

    输入：
        args: argparse.Namespace, 命令行参数

    输出：
        dict[str, Any]: 解析后的 JSON 对象
    """
    if args.raw_json:
        return json.loads(args.raw_json)

    if args.input_file:
        return json.loads(args.input_file.read_text(encoding="utf-8"))

    api_key = args.api_key or os.environ.get(args.api_key_env, "")
    if api_key:
        return fetch_usage(args.url, api_key)

    stdin_text = sys.stdin.read().strip()
    if not stdin_text:
        raise ValueError(
            "No input provided. Use stdin, --input-file, --raw-json, or --api-key."
        )
    return json.loads(stdin_text)


def fetch_usage(url: str, api_key: str) -> dict[str, Any]:
    """
    请求 Sub2API 用量接口

    输入：
        url: str, 接口地址
        api_key: str, Sub2API 密钥

    输出：
        dict[str, Any]: 接口返回的 JSON 对象
    """
    req = request.Request(url, headers={"x-api-key": api_key})
    with request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def as_float(value: Any) -> float:
    """
    将数值安全转换为浮点数

    输入：
        value: Any, 原始数值

    输出：
        float: 转换后的浮点数
    """
    if value is None:
        return 0.0
    return float(value)


def as_int(value: Any) -> int:
    """
    将数值安全转换为整数

    输入：
        value: Any, 原始数值

    输出：
        int: 转换后的整数
    """
    if value is None:
        return 0
    return int(value)


def percent(part: float, whole: float) -> float:
    """
    计算百分比

    输入：
        part: float, 分子
        whole: float, 分母

    输出：
        float: 百分比数值
    """
    if whole <= 0:
        return 0.0
    return (part / whole) * 100


def format_utc_offset_cn(dt: datetime) -> str:
    """
    格式化时区偏移

    输入：
        dt: datetime, 含时区的时间对象

    输出：
        str: 中文可读的 UTC 偏移
    """
    offset = dt.utcoffset()
    if offset is None:
        return ""

    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    abs_minutes = abs(total_minutes)
    hours, minutes = divmod(abs_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def format_datetime_cn(value: str) -> str:
    """
    将 ISO 时间格式化为中文日期时间

    输入：
        value: str, ISO 8601 时间字符串

    输出：
        str: 中文日期时间字符串
    """
    if not value:
        return ""

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value

    base = dt.strftime("%Y年%m月%d日 %H时%M分%S秒")
    tz_label = format_utc_offset_cn(dt)
    if not tz_label:
        return base
    return f"{base}（{tz_label}）"


def format_datetime_short(value: str) -> str:
    """
    将 ISO 时间格式化为短时间文本

    输入：
        value: str, ISO 8601 时间字符串

    输出：
        str: 适合状态栏的短时间文本
    """
    if not value:
        return ""

    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value

    return dt.strftime("%m-%d %H:%M")


def build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """
    构建标准化摘要

    输入：
        payload: dict[str, Any], 原始接口响应

    输出：
        dict[str, Any]: 标准化后的摘要结构
    """
    usage = payload.get("usage", {})
    today = usage.get("today", {})
    total = usage.get("total", {})

    models: list[dict[str, Any]] = []
    for item in payload.get("model_stats", []):
        models.append(
            {
                "model": item.get("model", ""),
                "requests": as_int(item.get("requests")),
                "cost": as_float(item.get("cost")),
                "actual_cost": as_float(item.get("actual_cost")),
                "account_cost": as_float(item.get("account_cost")),
                "input_tokens": as_int(item.get("input_tokens")),
                "output_tokens": as_int(item.get("output_tokens")),
                "cache_creation_tokens": as_int(item.get("cache_creation_tokens")),
                "cache_read_tokens": as_int(item.get("cache_read_tokens")),
                "total_tokens": as_int(item.get("total_tokens")),
            }
        )

    rate_limits: list[dict[str, Any]] = []
    for item in payload.get("rate_limits", []):
        limit = as_float(item.get("limit"))
        used = as_float(item.get("used"))
        remaining = as_float(item.get("remaining"))
        rate_limits.append(
            {
                "window": item.get("window", ""),
                "limit": limit,
                "used": used,
                "remaining": remaining,
                "used_percent": percent(used, limit),
                "remaining_percent": percent(remaining, limit),
                "reset_at": item.get("reset_at", ""),
                "reset_at_cn": format_datetime_cn(item.get("reset_at", "")),
                "reset_at_short": format_datetime_short(item.get("reset_at", "")),
                "window_start": item.get("window_start", ""),
            }
        )

    return {
        "is_valid": bool(payload.get("isValid")),
        "status": payload.get("status", ""),
        "mode": payload.get("mode", ""),
        "performance": {
            "average_duration_ms": as_float(usage.get("average_duration_ms")),
            "rpm": as_float(usage.get("rpm")),
            "tpm": as_float(usage.get("tpm")),
        },
        "today": {
            "requests": as_int(today.get("requests")),
            "cost": as_float(today.get("cost")),
            "actual_cost": as_float(today.get("actual_cost")),
            "input_tokens": as_int(today.get("input_tokens")),
            "output_tokens": as_int(today.get("output_tokens")),
            "cache_creation_tokens": as_int(today.get("cache_creation_tokens")),
            "cache_read_tokens": as_int(today.get("cache_read_tokens")),
            "total_tokens": as_int(today.get("total_tokens")),
        },
        "total": {
            "requests": as_int(total.get("requests")),
            "cost": as_float(total.get("cost")),
            "actual_cost": as_float(total.get("actual_cost")),
            "input_tokens": as_int(total.get("input_tokens")),
            "output_tokens": as_int(total.get("output_tokens")),
            "cache_creation_tokens": as_int(total.get("cache_creation_tokens")),
            "cache_read_tokens": as_int(total.get("cache_read_tokens")),
            "total_tokens": as_int(total.get("total_tokens")),
        },
        "models": models,
        "rate_limits": rate_limits,
    }


def format_number(value: float, digits: int = 4) -> str:
    """
    格式化浮点数显示

    输入：
        value: float, 数值
        digits: int, 可选, 保留小数位

    输出：
        str: 格式化后的字符串
    """
    return f"{value:.{digits}f}"


def format_currency(value: float) -> str:
    """
    格式化金额显示

    输入：
        value: float, 金额

    输出：
        str: 美元金额字符串
    """
    amount = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"${amount}"


def colorize(text: str, color: str) -> str:
    """
    为文本添加 ANSI 颜色

    输入：
        text: str, 原始文本
        color: str, ANSI 颜色码

    输出：
        str: 着色后的文本
    """
    return f"{color}{text}{RESET}"


def pick_usage_color(used_percent: float) -> str:
    """
    根据占用比例选择颜色

    输入：
        used_percent: float, 已用百分比

    输出：
        str: ANSI 颜色码
    """
    if used_percent >= 80:
        return RED
    if used_percent >= 50:
        return YELLOW
    return GREEN


def render_text(summary: dict[str, Any]) -> str:
    """
    渲染文本摘要

    输入：
        summary: dict[str, Any], 标准化摘要

    输出：
        str: 文本格式摘要
    """
    today = summary["today"]
    perf = summary["performance"]
    lines = [
        "Sub2API usage summary",
        (
            f"status={summary['status']} valid={summary['is_valid']} "
            f"mode={summary['mode']}"
        ),
        (
            "today: "
            f"requests={today['requests']} "
            f"cost={format_number(today['cost'])} "
            f"actual_cost={format_number(today['actual_cost'])} "
            f"input_tokens={today['input_tokens']} "
            f"output_tokens={today['output_tokens']} "
            f"cache_creation_tokens={today['cache_creation_tokens']} "
            f"cache_read_tokens={today['cache_read_tokens']} "
            f"total_tokens={today['total_tokens']}"
        ),
        (
            "performance: "
            f"avg_duration_ms={format_number(perf['average_duration_ms'], 2)} "
            f"rpm={format_number(perf['rpm'], 2)} "
            f"tpm={format_number(perf['tpm'], 2)}"
        ),
        "models:",
    ]

    models = summary["models"]
    if models:
        for item in models:
            lines.append(
                "  - "
                f"{item['model']}: requests={item['requests']} "
                f"cost={format_number(item['cost'])} "
                f"input={item['input_tokens']} "
                f"output={item['output_tokens']} "
                f"cache_create={item['cache_creation_tokens']} "
                f"cache_read={item['cache_read_tokens']} "
                f"total={item['total_tokens']}"
            )
    else:
        lines.append("  - none")

    lines.append("rate_limits:")
    rate_limits = summary["rate_limits"]
    if rate_limits:
        for item in rate_limits:
            lines.append(
                "  - "
                f"{item['window']}: "
                f"used={format_number(item['used_percent'], 2)}% "
                f"remaining={format_number(item['remaining_percent'], 2)}% "
                f"reset_at={item['reset_at']} "
                f"reset_at_cn={item['reset_at_cn']}"
            )
    else:
        lines.append("  - none")

    return "\n".join(lines)


def render_statusline(summary: dict[str, Any]) -> str:
    """
    渲染单行状态栏摘要

    输入：
        summary: dict[str, Any], 标准化摘要

    输出：
        str: 单行状态栏文本
    """
    rate_limits = summary["rate_limits"]
    if not rate_limits:
        return "Sub2API unavailable"

    parts = []
    for item in rate_limits:
        usage_text = f"{format_currency(item['used'])}/{format_currency(item['limit'])}"
        colored_usage = colorize(usage_text, pick_usage_color(item["used_percent"]))
        part = f"{colorize(item['window'], DIM)} {colored_usage}"
        if item["reset_at_short"]:
            part += colorize(f" ({item['reset_at_short']})", GRAY)
        parts.append(part)

    return colorize(" · ", GRAY).join(parts)


def main() -> int:
    """
    脚本入口

    输入：
        无

    输出：
        int: 进程退出码
    """
    args = parse_args()

    try:
        payload = load_payload(args)
        summary = build_summary(payload)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, error.URLError) as exc:
        print(f"Failed to parse usage payload: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.output == "statusline":
        print(render_statusline(summary))
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
