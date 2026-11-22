"""Follow-up questions on one finished report (fcst-001 step 7). A follow-up becomes exactly one operation:

    rerun     the same question for another territory or period, or with control territories dropped
    explain   why an episode was accepted or rejected, from the stored report (no new numbers)
    weekly    the miss week by week for the report's scope (claim tokens from governed queries)
    help      what a follow-up can do

A model, when one is configured, only chooses the operation and its arguments through tools; code runs it.
Without a model, keyword rules choose. Either way no figure comes from a model."""
from __future__ import annotations

import asyncio
import re
from typing import Annotated

from pharmagentics.tools import DEFAULT_DB, Registry
from pharmagentics.tools.queries import TERRITORY_NAMES, name
from pharmagentics.tools.registry import digits_outside_tokens
from pharmagentics.tools.window import parse

from . import sql as S

HELP = ("A follow-up can rerun this question for another territory or period, drop control territories and rerun, "
        "explain why an episode was accepted or rejected, break the miss down week by week, show a chart, or split "
        "where an unexplained gap sits by channel, specialty and plan.")
CHART_WORDS = [("weekly", r"\bweek"), ("trend", r"\b(trend|forecast (vs\.?|versus|against|and) actual|over time|line)"),
               ("territories", r"\b(territor\w*|region\w*|where)"), ("waterfall", r"\b(waterfall|split|driver\w*|bridge)")]


def chart_kind(question: str, parent: dict) -> str | None:
    """The chart a follow-up asks for: named by its words, else the answer's own default, else the first offered."""
    menu = parent.get("charts") or {}
    q = question.lower()
    for kind, pattern in CHART_WORDS:
        if re.search(pattern, q):
            return kind  # named: shown if offered, else the reply says which charts are offered
    shown = [k for k in parent.get("charts_shown") or [] if k in menu]
    return (shown or list(menu) or [None])[0]
DRIVER_WORDS = {"access": r"access|formulary|payer|plan|tier", "promotion": r"promo\w*|rep|coverage|calls?|field",
                "supply": r"supply|inventory|stock|backorder", "competitor": r"metacora|competit\w*|launch|share",
                "calendar": r"holiday|labor|calendar"}


def _territories(text: str) -> list[str]:
    return [t for t, label in TERRITORY_NAMES.items() if t != "NATIONAL" and re.search(rf"\b{re.escape(label)}\b", text, re.I)]


def route(question: str, parent: dict, first: str, latest: str) -> dict:
    """Keyword rules: the operation a follow-up asks for."""
    q = question.lower()
    named = _territories(question)
    if re.search(r"\b(drop|exclude|without|remove|leave out)\b", q) and named:
        return {"op": "rerun", "drop_controls": named, "territory": None, "weeks": None}
    if re.search(r"\b(split|break\w* (it )?down|drill|where (in|within)|which (plans?|channels?|specialt\w*|segments?))\b", q) \
            and re.search(r"\b(plans?|channels?|payers?|specialt\w*|segments?|prescribers?|residual|gap)\b", q):
        return {"op": "drill", "territory": named[0] if named else None}
    if re.search(r"\b(chart|plot|graph|visuali[sz]e|draw)\w*", q):
        return {"op": "chart", "kind": chart_kind(question, parent)}
    if re.search(r"\b(week by week|weekly|each week|which week|by week)\b", q):
        return {"op": "weekly"}
    if re.search(r"\b(why|reject\w*|ruled? out|accept\w*|not a driver|how sure|confiden\w*)\b", q):
        return {"op": "explain", "topic": question}
    ask = parse(question, first, latest)
    weeks = ask["weeks"] if re.search(r"\d{4}-\d{2}-\d{2}|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b \d{4}", q) else None
    nat = re.search(r"\b(national|nationally|overall|whole country)\b", q)
    territory = "NATIONAL" if nat else (named[0] if named else None)
    if territory or weeks:
        return {"op": "rerun", "territory": territory, "weeks": weeks, "drop_controls": []}
    return {"op": "help"}


def route_with_model(question: str, parent: dict, spec: str) -> dict | None:
    """The model picks one operation through tools; None if it picks none or fails (the rules then route)."""
    from agent_framework import Agent, tool

    from pharmagentics.llm import chat_client

    from .models import options

    picked: dict = {}

    @tool
    def rerun(territory: Annotated[str | None, "A territory id or NATIONAL, or null to keep the report's"] = None,
              first_week: Annotated[str | None, "First week, YYYY-MM-DD, or null to keep the report's period"] = None,
              last_week: Annotated[str | None, "Last week, YYYY-MM-DD"] = None,
              drop_controls: Annotated[list[str] | None, "Territory ids to keep out of every control group"] = None) -> str:
        """Run the investigation again with a changed territory, period or control group."""
        picked.update(op="rerun", territory=territory, weeks=[first_week, last_week or first_week] if first_week else None,
                      drop_controls=drop_controls or [])
        return "Done. Stop."

    @tool
    def explain(topic: Annotated[str, "What to explain, in the analyst's words"]) -> str:
        """Explain why an episode was accepted or rejected, or how confident a driver is, from the report."""
        picked.update(op="explain", topic=topic)
        return "Done. Stop."

    @tool
    def chart(kind: Annotated[str, "A chart id the report offers: " + ", ".join(parent.get("charts") or {}) or "none"]) -> str:
        """Show one of the report's charts."""
        picked.update(op="chart", kind=kind if kind in (parent.get("charts") or {}) else chart_kind(question, parent))
        return "Done. Stop."

    @tool
    def split_gap(territory: Annotated[str | None, "A territory id, or null for the report's territory or the one furthest behind"] = None) -> str:
        """Split where an unexplained gap sits by payer channel, specialty and plan."""
        picked.update(op="drill", territory=territory)
        return "Done. Stop."

    @tool
    def weekly() -> str:
        """Break the report's miss down week by week."""
        picked.update(op="weekly")
        return "Done. Stop."

    context = (f"Report question: {parent.get('question')}\nScope: {parent.get('territory_id')} from {parent.get('week_start')} "
               f"for {parent.get('window_weeks')} weeks.\nEpisodes: " +
               "; ".join(f"{c['id']} {c['label']} ({c['status']})" for c in parent.get("candidates", [])) +
               f"\nTerritory ids: {', '.join(S.TERRITORIES)}, NATIONAL.")
    agent = Agent(client=chat_client(spec), name="followup_router", default_options=options(spec),
                  instructions="An analyst asks a follow-up about a forecast-miss report. Call exactly one tool that "
                               "does what they ask, then stop. Never answer with numbers yourself.",
                  tools=[rerun, explain, weekly, chart, split_gap])
    try:
        asyncio.run(asyncio.wait_for(agent.run(context + "\n\nFollow-up: " + question), timeout=180))
    except Exception:  # noqa: BLE001 - the rules route instead
        return None
    return picked or None


def drill(parent: dict, territory: str | None, spec: str | None, db=DEFAULT_DB) -> dict:
    """Split where a gap sits for the report's scope: the named territory, else the asked one, else the territory
    furthest beyond its peers. Rules or a model choose the splits; code computes them."""
    from . import drill as gaps
    from .engine import Case
    from .scope import parse_scope
    from .write import Writer

    reg = Registry(db)
    try:
        first, latest = reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
        weeks = (parent.get("scope") or {}).get("weeks")
        scope = parse_scope(parent.get("question") or "", first, latest, territory=parent["territory_id"], weeks=weeks)
        case = Case(reg, scope)
        if not case.usable:
            return {"answer": "Every week in this scope has a provisional actual, so there is no gap to split.", "claims": [], "evidence": []}
        target = territory or (case.cut if case.cut != "NATIONAL" else None)
        if not target:
            neg = sorted((r for r in case.screen() if r["beyond_peers"] < 0), key=lambda r: r["beyond_peers"])
            target = neg[0]["territory"] if neg else None
        if not target:
            return {"answer": "No territory missed beyond its peers here, so there is no gap to split.", "claims": [], "evidence": []}
        gaps.run_model(case, spec, [target]) if spec else gaps.run_rules(case, [target])
        w = Writer(case)
        template = w.gap()
        assert not digits_outside_tokens(template)
        sp = next((x for x in case.splits if x["verdict"] == "concentrated"), case.splits[0])
        chart = {"id": "segments", "kind": "bars", "unit": "%", "series": [name(target), "Other territories"],
                 "title": f"{name(target)} by {sp['dimension']}: change against the same segment elsewhere",
                 "rows": [{"label": r["segment"] if r["segment"].startswith("SYN_") else r["segment"].replace("_", " ").title(),
                           "a": r["change_pct"] or 0, "b": r["peer_change_pct"] or 0} for r in sp["rows"]]}
        return {"answer": reg.render(template), "claims": reg.claims, "evidence": reg.evidence, "chart": chart,
                "splits": [{k: v for k, v in x.items() if k != "base_weeks"} for x in case.splits], "territory": target}
    finally:
        reg.close()


def explain(topic: str, parent: dict) -> str:
    """Lines already in the verified report about the episodes the topic names; no new numbers."""
    t = topic.lower()
    drivers = [d for d, pat in DRIVER_WORDS.items() if re.search(pat, t)]
    places = _territories(topic)
    cands = [c for c in parent.get("candidates", [])
             if (not drivers or c["driver"] in drivers) and (not places or c["territory"] in places + ["ALL"])]
    if not cands:
        if drivers:
            return (f"No {' or '.join(drivers)} episode was visible in this report's weeks, so it was never a candidate. "
                    "The report's list of what was investigated shows what each context table held.")
        return HELP
    sections = {s["id"]: s["text"] for s in parent.get("sections", [])}
    lines = []
    for c in cands:
        verdict = {"accepted": "accepted", "rejected": "rejected", "candidate": "left untested"}[c["status"]]
        lines.append(f"{c['label']} was {verdict}" + (f": {c['reason']}." if c.get("reason") else "."))
        for key in ("candidates", "attribution"):
            lines += [ln[2:] if ln.startswith("- ") else ln for ln in sections.get(key, "").splitlines()
                      if ln.startswith("- ") and c["label"].split(",")[0] in ln]
        d = next((d for d in parent.get("drivers", []) if d.get("label", "").startswith(c["label"].split(",")[0])), None)
        if d:
            lines.append(f"Confidence {d['confidence']}: " + "; ".join(d.get("confidence_reasons", [])) + ".")
    return "\n".join(dict.fromkeys(lines))


def weekly(parent: dict, db=DEFAULT_DB) -> dict:
    """The miss for each week of the report's scope, every figure a claim token."""
    reg = Registry(db)
    try:
        cut = parent["territory_id"]
        weeks = [r[0] for r in reg.rows(f"select week_start::varchar from raw.calendar where week_start >= DATE '{parent['week_start']}' "
                                        f"order by 1 limit {int(parent['window_weeks'])}")]
        lines = [f"Week by week for {name(cut)} (miss is actual minus forecast; percent of forecast):"]
        rows = []
        for w in weeks:
            v = reg.claim("get_forecast", S.fva("variance_trx", [w], cut), territory=cut, week=w)
            p = reg.claim("get_forecast", S.pct_of_forecast([w], cut), "pct1", territory=cut, week=w)
            prov = reg.scalar(f"select max(actual_is_provisional) from {S.FVA} where product_id = 'BXA' and territory_id = '{cut}' and week_start = DATE '{w}'")
            lines.append(f"- {w}: {v} TRx ({p})" + (", provisional actual" if prov else ""))
            rows.append({"week": w, "miss": reg.scalar(S.fva("variance_trx", [w], cut)),
                         "pct": reg.scalar(S.pct_of_forecast([w], cut)), "provisional": bool(prov)})
        template = "\n".join(lines)
        assert not digits_outside_tokens(template)
        return {"answer": reg.render(template), "claims": reg.claims, "evidence": reg.evidence,
                "table": {"territory": cut, "rows": rows}}
    finally:
        reg.close()
