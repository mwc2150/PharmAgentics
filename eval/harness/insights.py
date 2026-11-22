"""Read the local MLflow store(s) and say what the golden-set runs show (core-011 FR-008).

Read-only: every store is opened with mode=ro, and nothing is written to a store. Parent runs are the runs with no
`mlflow.parentRunId` tag; their child run holds the traces (trace metadata `mlflow.sourceRun`); scores are the
assessments on those traces. Each trace's question is matched to a golden case. Output: insights.md (for people) and
insights.json (the per-case matrix and the lists).
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from statistics import pstdev

from .paths import MLFLOW_DIR

OUT_DIR = MLFLOW_DIR / "insights"
DEFAULT_STORE = MLFLOW_DIR / "mlflow.db"
PARAM_KEYS = ("system", "lane", "golden_version", "code_version", "data_version")
# Run counters, not quality scores: kept in the matrix, left out of stuck, fallen, engine and spread lists.
OPERATIONAL = {"seconds", "llm_calls", "tool_calls", "hit_cap", "needed_revision"}
EPS = 0.001
STD_LIMIT = 0.1
QUESTION = re.compile(r'"question":\s*"((?:[^"\\]|\\.)*)"')


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)


def _number(value) -> float | None:
    """A score as stored in assessments.value (JSON text): numbers and booleans count, strings do not."""
    try:
        v = json.loads(value)
    except (TypeError, ValueError):
        return None
    if isinstance(v, (bool, int, float)):
        return float(v)
    return None


def _question(preview) -> str:
    match = QUESTION.search(preview or "")
    if not match:
        return preview or ""
    try:
        return json.loads(f'"{match.group(1)}"')
    except ValueError:
        return match.group(1)


def _norm(text: str) -> str:
    return " ".join(text.split())


def _tail(text: str) -> str:
    return _norm(text.rsplit(":", 1)[-1])


def case_index(pairs) -> tuple[dict, dict]:
    """Index golden (case_id, question) pairs by the text after the last colon, and by the first 60 characters."""
    tails, heads = defaultdict(set), defaultdict(set)
    for case_id, question in pairs:
        tails[_tail(question)].add(case_id)
        heads[_norm(question)[:60]].add(case_id)
    return tails, heads


def map_question(question: str, tails: dict, heads: dict) -> str | None:
    text = _norm(question)
    for index, key in ((tails, _tail(text)), (heads, text[:60])):
        ids = index.get(key, set())
        if len(ids) == 1:
            return next(iter(ids))
    return None


def _read_store(path: Path) -> list[dict]:
    """One dict per parent run in a store, with its traces as (question, {scorer: value})."""
    with closing(_connect(path)) as c:
        def rows(sql, args=()):
            return c.execute(sql, args).fetchall()

        runs = {rid: (name, start) for rid, name, start in
                rows("select run_uuid, name, start_time from runs "
                     "where lifecycle_stage = 'active' and status = 'FINISHED'")}  # a run still going is not the latest
        params = defaultdict(dict)
        for rid, key, value in rows("select run_uuid, key, value from params where key in (?,?,?,?,?)", PARAM_KEYS):
            params[rid][key] = value
        child_parent = dict(rows("select run_uuid, value from tags where key = 'mlflow.parentRunId'"))
        scores = defaultdict(dict)
        for trace_id, name, value in rows("select trace_id, name, value from assessments "
                                          "where coalesce(valid, 1) = 1 and assessment_type != 'expectation'"):
            number = _number(value)
            if number is not None:
                scores[trace_id][name] = number
        traces = rows("select m.value, t.request_preview, t.request_id from trace_info t "
                      "join trace_request_metadata m on m.request_id = t.request_id and m.key = 'mlflow.sourceRun'")

    parents = {}
    for rid, (name, start) in runs.items():
        if rid in child_parent:
            continue
        p = params[rid]
        parents[rid] = {"store": str(path), "run_id": rid, "system": p.get("system") or name, "start": start or 0,
                        "golden_version": p.get("golden_version"), "code_version": p.get("code_version"),
                        "data_version": p.get("data_version"), "traces": []}
    for child_id, preview, trace_id in traces:
        parent = child_parent.get(child_id)
        if parent in parents:
            parents[parent]["traces"].append((_question(preview), scores.get(trace_id, {})))
    return list(parents.values())


def _case_scores(parent: dict, tails: dict, heads: dict) -> tuple[dict, int]:
    """{case_id: {scorer: (mean, std)}} over the traces of the run (reruns pooled), and the unmapped trace count."""
    acc = defaultdict(lambda: defaultdict(list))
    unmapped = 0
    for question, values in parent["traces"]:
        case_id = map_question(question, tails, heads)
        if case_id is None:
            unmapped += 1
            continue
        for name, value in values.items():
            acc[case_id][name].append(value)
    cases = {c: {k: (sum(v) / len(v), pstdev(v)) for k, v in row.items()} for c, row in acc.items()}
    return cases, unmapped


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="minutes")


def _base(system: str) -> str:
    return system.split(":")[0]


def build(stores, pairs, system: str | None = None, last: int = 5, stories: dict | None = None) -> dict:
    """The insights as a dict (insights.json). `pairs` are golden (case_id, question) pairs; `stories` maps case_id to story ID."""
    tails, heads = case_index(pairs)
    stories = stories or {}
    parents = []
    for path in stores:
        parents += _read_store(Path(path))
    groups = defaultdict(list)
    for p in sorted(parents, key=lambda p: p["start"]):
        if system and system not in (p["system"], _base(p["system"])):
            continue
        p["cases"], p["unmapped"] = _case_scores(p, tails, heads)
        groups[p["system"]].append(p)
    runs = {s: rs[-max(last, 1):] for s, rs in groups.items()}

    def series(rs, case_id, scorer):
        return [(r["cases"].get(case_id, {}).get(scorer) or (None, None)) for r in rs]

    systems, matrix, std = {}, {}, {}
    for s, rs in runs.items():
        cases = sorted({c for r in rs for c in r["cases"]})
        scorers = sorted({k for r in rs for row in r["cases"].values() for k in row})
        matrix[s], std[s] = {}, {}
        for c in cases:
            for k in scorers:
                pts = series(rs, c, k)
                if any(m is not None for m, _ in pts):
                    matrix[s].setdefault(c, {})[k] = [None if m is None else round(m, 4) for m, _ in pts]
                    std[s].setdefault(c, {})[k] = [None if sd is None else round(sd, 4) for _, sd in pts]
        systems[s] = {"runs": [{"run_id": r["run_id"], "store": r["store"], "started": _iso(r["start"]),
                                "golden_version": r["golden_version"], "code_version": r["code_version"],
                                "data_version": r["data_version"], "cases": len(r["cases"]),
                                "traces": len(r["traces"]), "unmapped_traces": r["unmapped"]} for r in rs],
                      "scorers": [k for k in scorers if k not in OPERATIONAL]}

    stuck, fallen, breaks, spread = [], [], [], []
    for s, rs in runs.items():
        for a, b in zip(rs, rs[1:]):
            if a["golden_version"] != b["golden_version"]:
                breaks.append({"system": s, "from_run": a["run_id"], "to_run": b["run_id"],
                               "from_golden": a["golden_version"], "to_golden": b["golden_version"],
                               "comparable": False})
        for c, row in matrix[s].items():
            for k, vals in row.items():
                present = [v for v in vals if v is not None]
                if k not in OPERATIONAL and len(present) == len(vals) and all(v <= EPS for v in present):
                    stuck.append({"system": s, "story": stories.get(c, ""), "case": c, "scorer": k, "runs": len(present)})
        if len(rs) >= 2 and rs[-2]["golden_version"] == rs[-1]["golden_version"]:
            prev, last_run = rs[-2], rs[-1]
            for c in set(prev["cases"]) & set(last_run["cases"]):
                for k in set(prev["cases"][c]) & set(last_run["cases"][c]):
                    if k in OPERATIONAL:
                        continue
                    before, now = prev["cases"][c][k][0], last_run["cases"][c][k][0]
                    if now < before - EPS:
                        fallen.append({"system": s, "story": stories.get(c, ""), "case": c, "scorer": k, "previous": round(before, 4),
                                       "latest": round(now, 4), "drop": round(before - now, 4),
                                       "previous_run": prev["run_id"], "latest_run": last_run["run_id"]})
        for r in rs:
            for c, row in r["cases"].items():
                for k, (mean, sd) in row.items():
                    if k not in OPERATIONAL and sd > STD_LIMIT:
                        spread.append({"system": s, "run_id": r["run_id"], "story": stories.get(c, ""), "case": c, "scorer": k,
                                       "mean": round(mean, 4), "std": round(sd, 4)})

    latest = {s: rs[-1] for s, rs in runs.items() if rs}
    scripted = {s.split("_")[0]: s for s in latest if _base(s).endswith("_scripted")}
    engine = []
    for s in latest:
        b = _base(s)
        lane = s.split("_")[0]
        if not (b.endswith("_agent") or b.endswith("_lowcode")) or lane not in scripted:
            continue
        base_run, agent_run = latest[scripted[lane]], latest[s]
        cases = {}
        for c in sorted(set(base_run["cases"]) & set(agent_run["cases"])):
            row = {}
            for k in set(base_run["cases"][c]) & set(agent_run["cases"][c]):
                if k in OPERATIONAL:
                    continue
                before, now = base_run["cases"][c][k][0], agent_run["cases"][c][k][0]
                row[k] = {"scripted": round(before, 4), "agent": round(now, 4), "delta": round(now - before, 4)}
            if row:
                cases[c] = row
        engine.append({"lane": lane, "scripted": scripted[lane], "agent": s,
                       "scripted_run": base_run["run_id"], "agent_run": agent_run["run_id"],
                       "same_golden": base_run["golden_version"] == agent_run["golden_version"], "cases": cases})

    return {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stores": [str(p) for p in stores],
            "unmapped_traces": sum(p["unmapped"] for rs in runs.values() for p in rs),
            "systems": systems, "matrix": matrix, "std": std, "stuck": stuck, "fallen": fallen,
            "engine": engine, "rerun_spread": spread, "golden_breaks": breaks}


def _table(lines: list, title: str, cols: list, rows: list, empty: str, cap: int | None = None, note: str = ""):
    lines += ["", f"## {title}", ""]
    if not rows:
        lines.append(empty)
        return
    lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    shown = rows[:cap] if cap else rows
    for r in shown:
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    if cap and len(rows) > cap:
        lines.append(f"\n{len(rows) - cap} more in insights.json.")
    if note:
        lines.append(f"\n{note}")


def render_md(d: dict) -> str:
    lines = ["# Eval insights", "",
             f"Generated {d['generated']} from {len(d['stores'])} store(s). Scores are means over the traces of a case "
             f"in a run. Run counters ({', '.join(sorted(OPERATIONAL))}) are in insights.json only. "
             f"Unmapped traces (no golden case matched): {d['unmapped_traces']}."]
    lines += ["", "## Runs compared", "", "| system | run | started (UTC) | golden | code | cases |",
              "|---|---|---|---|---|---|"]
    for s, info in d["systems"].items():
        for r in info["runs"]:
            lines.append(f"| {s} | {r['run_id'][:8]} | {r['started']} | {r['golden_version']} | "
                         f"{r['code_version']} | {r['cases']} |")
    _table(lines, "Golden-version breaks (not comparable)", ["system", "from_golden", "to_golden", "from_run", "to_run"],
           [{**b, "from_run": b["from_run"][:8], "to_run": b["to_run"][:8]} for b in d["golden_breaks"]],
           "None in the listed runs.")
    _table(lines, "Stuck (a scorer at 0 in every listed run)", ["system", "story", "case", "scorer", "runs"], d["stuck"],
           "None.")
    _table(lines, "Fallen (lower in the latest run than the one before, by more than 0.001)",
           ["system", "story", "case", "scorer", "previous", "latest", "drop"], d["fallen"], "None.")
    lines += ["", "## Engine comparison (latest scripted vs latest agent, per lane)"]
    if not d["engine"]:
        lines += ["", "No scripted and agent pair in the listed runs."]
    for pair in d["engine"]:
        note = "" if pair["same_golden"] else " NOT COMPARABLE: golden versions differ."
        lines += ["", f"### {pair['lane']}: {pair['scripted']} vs {pair['agent']}{note}", "",
                  "| scorer | cases | scripted mean | agent mean | cases where agent is lower |", "|---|---|---|---|---|"]
        by_scorer = defaultdict(list)
        for row in pair["cases"].values():
            for k, v in row.items():
                by_scorer[k].append(v)
        for k in sorted(by_scorer):
            vs = by_scorer[k]
            lower = sum(v["delta"] < -EPS for v in vs)
            lines.append(f"| {k} | {len(vs)} | {sum(v['scripted'] for v in vs) / len(vs):.3f} | "
                         f"{sum(v['agent'] for v in vs) / len(vs):.3f} | {lower} |")
    _table(lines, "Rerun spread (std above 0.1, per run)", ["system", "story", "case", "scorer", "mean", "std"],
           sorted(d["rerun_spread"], key=lambda r: -r["std"]), "None.", cap=30)
    return "\n".join(lines) + "\n"


def run(stores=None, system: str | None = None, last: int = 5, out: Path | None = None) -> dict:
    from .cases import load_cases

    paths = [Path(p) for p in stores] if stores else [DEFAULT_STORE]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"no MLflow store at: {', '.join(missing)}")
    cases = load_cases()
    data = build(paths, [(c.id, c.question) for c in cases], system=system, last=last,
                 stories={c.id: c.story for c in cases})
    out = Path(out) if out else OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    (out / "insights.json").write_text(json.dumps(data, indent=2), encoding="utf8")
    (out / "insights.md").write_text(render_md(data), encoding="utf8")
    print(f"wrote {out / 'insights.md'} and insights.json ({len(data['systems'])} system(s), "
          f"{len(data['stuck'])} stuck, {len(data['fallen'])} fallen)")
    return data
