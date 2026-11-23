"""Export an aggregate snapshot of the golden-set runs for the hosted app's Telemetry view.

The image never holds eval/ or the MLflow store (.dockerignore), so the cloud app reads this snapshot instead:
src/pharmagentics/api/telemetry.json. It holds run-level scores, plus a per-case `cases` block (case id, story, persona label, scores and stuck/fallen
marks per scorer): no case text, no answers, no golden facts (core-011 FR-009). The API gives `cases` to analysts and
the test login only.
`deploy/gcp.py telemetry` (run by every `gcp.py app`) uploads a fresh copy to the state bucket, which the app prefers.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

from .insights import DEFAULT_STORE, build
from .paths import EXPERIMENT, tracking_uri
from .scorers import TARGETS, kind_of, unit_of

OUT = Path(__file__).resolve().parents[2] / "src" / "pharmagentics" / "api" / "telemetry.json"
JUDGE_HINTS = ("judge", "ragas", "faithfulness", "relevan")  # LLM judges are report-only (Evaluation Pack item 2)
CONTROLS = {"reference", "naive_llm"}
AGENT_SUFFIXES = ("_agent", "_lowcode")  # systems whose rows carry numbers_lost (insights.numbers_lost)
MAX_RUNS = 60


def _run(r) -> dict:
    p, t = r.data.params, r.data.tags
    metrics = {k.removesuffix("/mean"): round(v, 4) for k, v in sorted(r.data.metrics.items()) if k.endswith("/mean")}
    system = t.get("system", p.get("system", "?"))
    return {
        "run_id": r.info.run_id[:8],
        "started": datetime.fromtimestamp(r.info.start_time / 1000, timezone.utc).isoformat(timespec="minutes"),
        "minutes": round((r.info.end_time - r.info.start_time) / 60000, 1) if r.info.end_time else None,
        "system": system, "model": p.get("system", system).partition(":")[2] or None,
        "lane": t.get("lane", p.get("lane", "all")), "control": system in CONTROLS,
        "cases": int(p.get("cases", 0) or 0), "reruns": int(p.get("reruns", 1) or 1), "judge": p.get("judge", "off"),
        "code_version": p.get("code_version", "")[:12], "data_version": p.get("data_version", "")[:12],
        "metrics": {k: v for k, v in metrics.items() if not any(h in k.lower() for h in JUDGE_HINTS)},
        "judge_metrics": {k: v for k, v in metrics.items() if any(h in k.lower() for h in JUDGE_HINTS)},
    }


def cases_block(insights: dict, labels: dict[str, dict]) -> dict:
    """The per-case table from an insights dict. `labels` maps case id to {lane, story, persona}.

    One entry per (system, lane), from the latest run of each system. Only ids, labels, numbers and marks go in;
    a score that was not recorded is null, never 0.
    """
    stuck, fallen = defaultdict(set), defaultdict(dict)
    for e in insights.get("stuck", []):
        stuck[(e["system"], e["case"])].add(e["scorer"])
    for e in insights.get("fallen", []):
        fallen[(e["system"], e["case"])][e["scorer"]] = {"previous": e["previous"], "latest": e["latest"]}
    below = defaultdict(list)  # core-011 FR-018: counts only (no fact or finding IDs), split by the capability needed
    for e in insights.get("below_target", []):
        below[(e["system"], e["case"])].append({"scorer": e["scorer"], "score": e["score"], "target": e["target"],
                                                "needs": {k: len(v) for k, v in sorted(e["needs"].items())},
                                                "missed": len(e["missed"])})
    lost = defaultdict(dict)
    for e in insights.get("numbers_lost", []):
        lost[e["system"]][e["case"]] = e["lost"]
    entries = []
    for system, info in insights.get("systems", {}).items():
        if not info["runs"]:
            continue
        run, scorers = info["runs"][-1], info["scorers"]
        agent_system = system.partition(":")[0].endswith(AGENT_SUFFIXES)  # numbers_lost is a Briefing figure
        by_lane = defaultdict(list)
        for case_id, row in sorted(insights["matrix"].get(system, {}).items()):
            meta = labels.get(case_id)
            if meta is None:
                continue
            by_lane[meta["lane"]].append({
                "case": case_id, "story": meta["story"], "persona": meta["persona"],
                "scores": {k: (row[k][-1] if k in row else None) for k in scorers}
                          | ({"numbers_lost": lost[system].get(case_id)} if agent_system and meta["lane"] == "briefing" else {}),
                "stuck": sorted(stuck[(system, case_id)]),
                "fallen": [{"scorer": k, **v} for k, v in sorted(fallen[(system, case_id)].items())],
                **({"below": below[(system, case_id)]} if below.get((system, case_id)) else {}),
            })
        for lane, rows in sorted(by_lane.items()):
            used = [k for k in scorers if any(r["scores"][k] is not None for r in rows)]
            if agent_system and lane == "briefing":
                used.append("numbers_lost")
            entries.append({
                "system": system, "lane": lane, "control": system.partition(":")[0] in CONTROLS,
                "run_id": run["run_id"][:8], "started": run["started"], "golden_version": run["golden_version"],
                "scorers": used, "kinds": {k: kind_of(k) for k in used}, "units": {k: unit_of(k) for k in used},
                "report_only": [k for k in used if any(h in k.lower() for h in JUDGE_HINTS)],
                "rows": [{**r, "scores": {k: r["scores"][k] for k in used}} for r in rows]})
    return {"generated": insights.get("generated"), "targets": dict(TARGETS), "systems": entries}


def _labels() -> dict[str, dict]:
    from .cases import load_cases

    return {c.id: {"lane": c.lane, "story": c.story, "persona": c.persona} for c in load_cases()}


def _store_for(uri: str | None) -> Path | None:
    """The SQLite file behind a tracking uri, DEFAULT_STORE for None, and None for any other kind of store."""
    if uri is None:
        return DEFAULT_STORE
    return Path(uri.removeprefix("sqlite:///")) if uri.startswith("sqlite:///") else None


def export(out: Path = OUT, uri: str | None = None, insights: dict | None = None) -> dict:
    """Write the snapshot. `insights` is the dict `insights.build` returns; without it the per-case block is built from
    the SQLite store behind `uri` (the default local store when `uri` is None), and left out for any other store."""
    mlflow.set_tracking_uri(uri or tracking_uri())
    client = MlflowClient()
    exp = client.get_experiment_by_name(EXPERIMENT)
    runs = [] if exp is None else client.search_runs(
        [exp.experiment_id], "tags.suite = 'golden' and attributes.status = 'FINISHED'",
        order_by=["attributes.start_time DESC"], max_results=500)
    parents = [_run(r) for r in runs if "mlflow.parentRunId" not in r.data.tags][:MAX_RUNS]
    latest: dict[str, dict] = {}
    for r in parents:  # newest first, so the first per (system, lane) is the latest
        latest.setdefault(f"{r['system']}|{r['lane']}", r)
    snap = {"exported": datetime.now(timezone.utc).isoformat(timespec="minutes"), "source": "golden set (MLflow)",
            "note": "Run-level scores only. Judge scores are report-only until judge agreement clears the bar.",
            "latest": list(latest.values()), "runs": parents}
    store = _store_for(uri)
    if insights is None and store is not None and store.exists():
        from .cases import load_cases

        cases = load_cases()
        insights = build([store], [(c.id, c.question) for c in cases], stories={c.id: c.story for c in cases})
    if insights is not None:
        snap["cases"] = cases_block(insights, _labels())
    out.write_text(json.dumps(snap, indent=1) + "\n", encoding="utf-8")
    return snap


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    given = None
    if "--insights" in args:  # an insights.json from `python -m eval insights`, instead of reading the local store
        i = args.index("--insights")
        given = json.loads(Path(args[i + 1]).read_text(encoding="utf-8"))
        del args[i:i + 2]
    target = Path(args[0]) if args else OUT
    s = export(target, insights=given)
    print(f"Wrote {target} ({len(s['runs'])} runs, {len(s['latest'])} system/lane pairs, "
          f"{len(s.get('cases', {}).get('systems', []))} per-case tables)")
