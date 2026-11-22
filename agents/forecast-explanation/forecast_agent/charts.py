"""Charts (fcst-002). Code offers a small menu of charts for each answer, built only from that answer's own
numbers; a model decides whether a chart helps the question, and which (at most two). A model never supplies a
value: it picks chart ids, and the UI draws the stored data. Without a model, code shows a default per intent."""
from __future__ import annotations

import asyncio
import os
from typing import Annotated

from pharmagentics.tools.queries import name
from pharmagentics.tools.registry import FORMATS

from . import sql as S

CHOOSE_SECONDS = float(os.environ.get("FORECAST_CHART_SECONDS", "90"))
MAX_SHOWN = 2
DEFAULTS = {"attribution": ["waterfall"], "drivers": ["waterfall"], "unknowns": ["waterfall"],
            "communicate": ["waterfall"], "next_checks": [], "where": ["territories"], "screen": ["territories"],
            "assumptions": ["trend"], "reliability": ["weekly"], "audit": []}
DESCRIBE = {
    "waterfall": "how the miss splits into the usual bias, each driver and the unexplained residual, from forecast to actual",
    "territories": "each territory's miss beside its miss beyond what the other territories' rate predicts",
    "weekly": "the miss week by week, with provisional weeks marked",
    "trend": "forecast and actual week by week over the period",
    "segments": "where an unexplained gap sits: each segment's change beside the same segment in other territories",
}


def _whole(x: float) -> float:
    return float(FORMATS["int"](x).replace(",", ""))


def catalog(w, parts: list[dict]) -> dict[str, dict]:
    """Every chart this answer can support, keyed by kind."""
    case, out = w.case, {}
    if case.abstained or not case.weeks:
        return out
    var = case.variance()
    if parts and var.get("forecast") is not None:
        steps = [{"label": "Forecast", "value": _whole(var["forecast"]), "kind": "total"}]
        steps += [{"label": "Usual bias" if p["episode"] is None else p["label"].replace(", in every territory", ""),
                   "value": _whole(p["value"]), "kind": "delta"} for p in parts]
        steps.append({"label": "Unexplained", "value": _whole(w.V - sum(p["value"] for p in parts)), "kind": "delta"})
        steps.append({"label": "Actual", "value": _whole(var["actual"]), "kind": "total"})
        out["waterfall"] = {"kind": "waterfall", "title": f"From forecast to actual, {name(w.cut)}", "steps": steps}
    if w.cut == "NATIONAL":
        rows = case.screen(w.W)
        out["territories"] = {"kind": "bars", "title": "Miss by territory, and beyond its peers", "unit": "TRx",
                              "rows": [{"label": name(r["territory"]), "a": r["miss"], "b": r["beyond_peers"]} for r in rows],
                              "series": ["Miss", "Beyond peers"]}
    if 1 < len(case.weeks) <= 60:
        rows, eid = w.reg.table("chart_weekly", f"select week_start::varchar, sum(forecast_trx), sum(actual_trx), "
                                f"sum(variance_trx), max(actual_is_provisional) from {S.FVA} where product_id = 'BXA' "
                                f"and territory_id = '{w.cut}' and week_start in {S.dates(case.weeks)} group by 1 order by 1",
                                cut=w.cut)
        out["weekly"] = {"kind": "bars", "title": f"Miss by week, {name(w.cut)}", "unit": "TRx", "evidence": eid,
                         "rows": [{"label": r[0], "a": float(r[3]), "flag": bool(r[4])} for r in rows], "series": ["Miss"]}
        if len(rows) >= 4:
            out["trend"] = {"kind": "lines", "title": f"Forecast and actual by week, {name(w.cut)}", "unit": "TRx",
                            "evidence": eid, "rows": [{"label": r[0], "a": float(r[1]), "b": float(r[2])} for r in rows],
                            "series": ["Forecast", "Actual"]}
    if case.splits:
        sp = next((x for x in case.splits if x["verdict"] == "concentrated"), case.splits[0])
        dim = {"channel": "payer channel", "specialty": "specialty", "plan": "plan"}[sp["dimension"]]
        out["segments"] = {"kind": "bars", "title": f"{name(sp['territory'])} by {dim}: change against the same segment elsewhere",
                           "unit": "%", "series": [name(sp["territory"]), "Other territories"],
                           "rows": [{"label": r["segment"].replace("_", " ").title() if not r["segment"].startswith("SYN_") else r["segment"],
                                     "a": r["change_pct"] or 0, "b": r["peer_change_pct"] or 0} for r in sp["rows"]]}
    return out


def choose(question: str, intent: str, menu: dict[str, dict], spec: str | None) -> tuple[list[str], str]:
    """Which charts to show, and who chose: the model when one is set (it may choose none), else code's default."""
    default = [k for k in DEFAULTS.get(intent, []) if k in menu]
    if "segments" in menu and intent in ("unknowns", "attribution", "drivers", "where", "next_checks"):
        default = (default + ["segments"])[:MAX_SHOWN]
    if not spec or not menu:
        return default, "code"
    from agent_framework import Agent, tool

    from pharmagentics.llm import chat_client

    from .models import options

    got: dict = {}

    @tool
    def show_charts(chart_ids: Annotated[list[str], "Zero, one or two chart ids from the menu"]) -> str:
        """Record which charts to show under the answer."""
        got["ids"] = chart_ids
        return "Recorded. Stop."

    lines = "\n".join(f"- {k}: {DESCRIBE[k]}" for k in menu)
    agent = Agent(client=chat_client(spec), name="chart_chooser", default_options=options(spec), tools=[show_charts],
                  instructions="A brand analyst asked a question about a forecast miss. Choose the charts, from the menu "
                               "only, that would help them see the answer; choose none if words and the table suffice. "
                               "At most two. Call show_charts once.")
    try:
        asyncio.run(asyncio.wait_for(agent.run(f"Question: {question}\nMenu:\n{lines}"), timeout=CHOOSE_SECONDS))
    except Exception:  # noqa: BLE001 - code's default stands
        return default, "code"
    if "ids" not in got:
        return default, "code"
    picked = [k for k in dict.fromkeys(str(x).strip().lower() for x in got["ids"] or []) if k in menu][:MAX_SHOWN]
    return picked, "model"
