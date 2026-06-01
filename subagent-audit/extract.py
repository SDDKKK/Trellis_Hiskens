#!/usr/bin/env python3
"""
Extract & aggregate Trellis sub-agent (Agent tool) dispatch records from
Claude Code session transcripts, for workflow analysis.

Reads ~/.claude/projects/<sanitized-cwd>/*.jsonl, pairs each `Agent` tool_use
with its `toolUseResult`, and emits aggregated JSON over two dimensions:
  - efficiency / token / redundancy
  - workflow deviation

VISIBILITY BOUNDARY (verified against this machine's transcripts):
  - Sub-agent INTERNAL turns are NOT in the transcript (isSidechain always
    false/None). We never see which concrete files a sub-agent touched — only
    toolStats COUNTS (readCount/editFileCount/linesAdded/...).
  - The dispatch tool is named "Agent" (not "Task").
  - Only SYNCHRONOUS calls inline totalTokens / usage / toolStats /
    totalDurationMs / status="completed". ASYNC (isAsync) calls only leave a
    status="async_launched" + a /tmp/.../*.output path deleted after the
    session. => Async OUTCOME is unobservable; failure/success cannot be read
    for async calls. Do NOT report async_launched as "failed".

Usage:
  python3 extract.py [<projectDirKey> ...]   # default: small-sample 2 projects
Output: aggregated JSON on stdout.
"""
import collections
import glob
import json
import os
import statistics
import sys

CLAUDE_ROOT = os.path.expanduser("~/.claude/projects")

PROJECT_NAMES = {
    "-home-hcx-github-Trellis-Hiskens": "Trellis_Hiskens",
    "-mnt-e-Github-repo-ZZ-KKX": "ZZ-KKX",
    "-mnt-e-Github-repo-Topo-Reliability": "Topo-Reliability",
    "-mnt-e-Github-repo-Anhui-CIM": "Anhui-CIM(E)",
    "-home-hcx-github-Anhui-CIM": "Anhui-CIM(home)",
    "-home-hcx-github-Auto-claude-code-research-in-sleep": "Auto-research",
}

SAMPLE_KEYS = ["-home-hcx-github-Trellis-Hiskens", "-mnt-e-Github-repo-ZZ-KKX"]
TRELLIS_AGENTS = {"trellis-research", "trellis-implement", "trellis-check"}

# implementation-intent verbs near the start of a dispatch prompt; combined with
# editFileCount>0 they flag a research dispatch that actually did implementer work.
IMPL_VERBS = ("write ", "port ", "implement", "rewire", "modify ",
              "create src", "rewrite", "refactor ")

SLOW_MS = 600_000  # 10 min — flag a single sub-agent call as a latency outlier


def iter_events(path):
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _impl_intent(prompt):
    return any(v in prompt[:200].lower() for v in IMPL_VERBS)


def extract_project(proj_dir):
    calls = {}
    order = []
    files = glob.glob(os.path.join(proj_dir, "*.jsonl"))
    for f in files:
        for o in iter_events(f):
            content = (o.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"
                        and b.get("name") == "Agent"):
                    continue
                bid = b.get("id")
                if not bid:
                    continue
                inp = b.get("input") or {}
                calls[bid] = {
                    "id": bid,
                    "subagent": inp.get("subagent_type"),
                    "prompt": inp.get("prompt") or "",
                    "description": inp.get("description") or "",
                    "session": o.get("sessionId"),
                    "ts": o.get("timestamp"),
                    "file": os.path.basename(f),
                    "status": None, "isAsync": None,
                    "totalTokens": None, "totalDurationMs": None,
                    "totalToolUseCount": None, "usage": None, "toolStats": None,
                    "result_len": None,
                }
                order.append((o.get("sessionId"), o.get("timestamp"), bid))
    for f in files:
        for o in iter_events(f):
            content = (o.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    continue
                rec = calls.get(b.get("tool_use_id"))
                if rec is None:
                    continue
                tur = o.get("toolUseResult")
                if not isinstance(tur, dict):
                    continue
                rec["status"] = tur.get("status")
                rec["isAsync"] = tur.get("isAsync")
                rec["totalTokens"] = tur.get("totalTokens")
                rec["totalDurationMs"] = tur.get("totalDurationMs")
                rec["totalToolUseCount"] = tur.get("totalToolUseCount")
                rec["usage"] = tur.get("usage")
                rec["toolStats"] = tur.get("toolStats")
                c = tur.get("content")
                if isinstance(c, list):
                    rec["result_len"] = sum(
                        len(x.get("text", "")) for x in c if isinstance(x, dict))
    return list(calls.values()), order


def _med(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(statistics.median(xs), 1) if xs else None


def _cache_hit(usages):
    tot_in = tot_cache = 0
    for u in usages:
        if not isinstance(u, dict):
            continue
        i = u.get("input_tokens", 0) or 0
        cc = u.get("cache_creation_input_tokens", 0) or 0
        cr = u.get("cache_read_input_tokens", 0) or 0
        tot_in += i + cc + cr
        tot_cache += cr
    return round(tot_cache / tot_in, 3) if tot_in else None


def aggregate(all_calls, seqs):
    tcalls = [c for c in all_calls if c["subagent"] in TRELLIS_AGENTS]
    sync = [c for c in tcalls if c.get("totalTokens") is not None]
    n = len(tcalls)

    # ---- efficiency: cost by subagent (sync subset only) ----
    cost = {}
    for sa in sorted(TRELLIS_AGENTS):
        grp = [c for c in sync if c["subagent"] == sa]
        if not grp:
            continue
        cost[sa] = {
            "n_sync": len(grp),
            "tokens_median": _med([c["totalTokens"] for c in grp]),
            "tokens_max": max(c["totalTokens"] for c in grp),
            "duration_median_ms": _med([c["totalDurationMs"] for c in grp]),
            "tooluse_median": _med([c["totalToolUseCount"] for c in grp]),
            "cache_hit_rate": _cache_hit([c["usage"] for c in grp]),
        }
    top_cost = sorted(sync, key=lambda c: c["totalTokens"] or 0, reverse=True)[:6]
    top_cost = [{
        "subagent": c["subagent"], "project": c["project"],
        "tokens": c["totalTokens"], "duration_ms": c["totalDurationMs"],
        "tooluse": c["totalToolUseCount"], "result_len": c["result_len"],
        "prompt_head": c["prompt"][:90],
    } for c in top_cost]
    slow = sorted([c for c in sync if (c["totalDurationMs"] or 0) > SLOW_MS],
                  key=lambda c: -(c["totalDurationMs"] or 0))
    slow = [{
        "subagent": c["subagent"], "project": c["project"],
        "duration_min": round((c["totalDurationMs"] or 0) / 60000, 1),
        "tokens": c["totalTokens"], "tooluse": c["totalToolUseCount"],
        "prompt_head": c["prompt"][:90],
    } for c in slow]

    # ---- workflow deviation ----
    # research dispatches that wrote files (path invisible -> needs manual check).
    research_writes = []
    type_mismatch = []
    for c in sync:
        ts = c.get("toolStats") or {}
        edits = ts.get("editFileCount") or 0
        if c["subagent"] == "trellis-research" and edits > 0:
            row = {
                "project": c["project"], "editFileCount": edits,
                "linesAdded": ts.get("linesAdded"),
                "impl_intent": _impl_intent(c["prompt"]),
                "prompt_head": c["prompt"][:90],
            }
            research_writes.append(row)
            if row["impl_intent"]:  # high-confidence: research did implementer work
                type_mismatch.append(row)
    research_writes.sort(key=lambda r: -(r["editFileCount"] or 0))

    # status: sync failures (should be ~0); async outcome is UNOBSERVABLE.
    sync_failures = [{
        "subagent": c["subagent"], "project": c["project"], "status": c["status"],
        "prompt_head": c["prompt"][:90],
    } for c in sync if c["status"] not in ("completed", None)]

    # ---- orchestration ----
    active_prefix = sum(1 for c in tcalls if c["prompt"].lstrip().startswith("Active task"))
    active_none = sum(1 for c in tcalls
                      if c["prompt"].lstrip().lower().startswith("active task: none"))
    has_injection = sum(1 for c in tcalls if "trellis-hook-injected" in c["prompt"])
    prompt_lens = [len(c["prompt"]) for c in tcalls]

    pingpong = {}
    repeated_research = {}
    research_only = {}
    for name, bysess in seqs.items():
        for sess, seq in bysess.items():
            ic = [s for s in seq if s in ("trellis-implement", "trellis-check")]
            switches = sum(1 for a, b in zip(ic, ic[1:]) if a != b)
            if switches >= 3:
                pingpong[f"{name}/{sess[:8]}"] = {"switches": switches, "ic_seq": ic}
            rcount = seq.count("trellis-research")
            if rcount >= 4:
                repeated_research[f"{name}/{sess[:8]}"] = rcount
            if len(seq) >= 4 and all(s == "trellis-research" for s in seq):
                research_only[f"{name}/{sess[:8]}"] = len(seq)

    return {
        "meta": {
            "total_agent_calls": len(all_calls),
            "trellis_calls": n,
            "sync_with_cost": len(sync),
            "async_outcome_unobservable": n - len(sync),
            "note": "cost/toolStats/deviation metrics cover the sync subset only; "
                    "orchestration metrics cover all trellis calls.",
        },
        "overview": {
            "by_project": dict(collections.Counter(c["project"] for c in tcalls)),
            "by_subagent": dict(collections.Counter(c["subagent"] for c in tcalls)),
            "status_dist": dict(collections.Counter(c["status"] for c in tcalls)),
            "isAsync_dist": dict(collections.Counter(str(c["isAsync"]) for c in tcalls)),
        },
        "efficiency": {
            "cost_by_subagent": cost,
            "top_token_calls": top_cost,
            "latency_outliers_gt10min": slow,
            "prompt_len_median": _med(prompt_lens),
            "prompt_len_max": max(prompt_lens) if prompt_lens else None,
        },
        "redundancy": {
            "repeated_research_sessions": repeated_research,
            "research_only_no_landing_sessions": research_only,
        },
        "deviation": {
            "research_wrote_files_needs_path_check": research_writes,
            "type_intent_mismatch_high_conf": type_mismatch,
            "checkimplement_pingpong_sessions": pingpong,
            "active_task_prefix_rate": round(active_prefix / n, 3) if n else None,
            "active_task_none_count": active_none,
            "injection_marker_rate": round(has_injection / n, 3) if n else None,
            "sync_failures": sync_failures,
        },
        "sequences_by_session": {
            name: {s[:8]: seq for s, seq in bysess.items()}
            for name, bysess in seqs.items()
        },
    }


def main():
    keys = sys.argv[1:] or SAMPLE_KEYS
    all_calls = []
    seqs = {}
    for key in keys:
        d = os.path.join(CLAUDE_ROOT, key)
        if not os.path.isdir(d):
            print(f"# skip missing: {key}", file=sys.stderr)
            continue
        calls, order = extract_project(d)
        name = PROJECT_NAMES.get(key, key)
        for c in calls:
            c["project"] = name
        all_calls.extend(calls)
        ids = {c["id"] for c in calls}
        id2sub = {c["id"]: c["subagent"] for c in calls}
        order = [t for t in order if t[2] in ids]
        order.sort(key=lambda x: (x[0] or "", x[1] or ""))
        bysess = collections.defaultdict(list)
        for s, _ts, bid in order:
            sub = id2sub.get(bid)
            if sub in TRELLIS_AGENTS:
                bysess[s].append(sub)
        seqs[name] = dict(bysess)
    print(json.dumps(aggregate(all_calls, seqs), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
