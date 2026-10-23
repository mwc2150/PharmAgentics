"""Stage 3 · competitive intelligence (deterministic; FR-004).

Flags material changes for one week with the stand-in thresholds in config.py.
Withheld cuts never enter detection (they are absent from the gated views, never
read as zero).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .claims import ClaimBook
from .config import DETECTION, INDEX_PRODUCT, PRODUCTS, TERRITORIES
from .contracts import Candidate
from .tools import ToolRegistry, d, mean, shift


def weekly_series(tools: ToolRegistry, week: date, weeks_back: int = 15) -> tuple[dict, str]:
    result, eid = tools.call("get_metric", product=INDEX_PRODUCT, start=shift(week, -weeks_back), end=week)
    series: dict = defaultdict(dict)
    for r in result["rows"]:
        series[r["territory"]][d(r["week"])] = r
    return series, eid


def national_kpis(tools: ToolRegistry, claims: ClaimBook, week: date, series: dict, eid: str) -> dict:
    """National like-for-like move against the four-week average, plus the naive total."""
    prev = [shift(week, -k) for k in range(1, 5)]
    reporting = sorted(t for t in TERRITORIES if week in series.get(t, {}))
    cur = sum(series[t][week]["trx"] for t in reporting)
    nbrx = sum(series[t][week]["nbrx"] for t in reporting)
    base = sum(mean(series[t][w]["trx"] for w in prev if w in series[t]) or 0 for t in reporting)
    naive_weeks = [sum(series[t][w]["trx"] for t in series if w in series[t]) for w in prev]
    naive_base = mean([v for v in naive_weeks if v]) or 0
    rel = cur / base - 1 if base else 0.0
    naive_rel = cur / naive_base - 1 if naive_base else 0.0
    return {"week": week, "reporting": reporting, "trx": cur, "nbrx": nbrx, "base": base, "rel": rel,
            "naive_base": naive_base, "naive_rel": naive_rel, "evidence_id": eid}


def kpi_lines(tools: ToolRegistry, claims: ClaimBook, nat: dict) -> list[str]:
    week = nat["week"]
    comp, ceid = tools.call("compare_competitors", start=week, end=week, base_start=shift(week, -4), base_end=shift(week, -1))
    share = comp["shares"].get("window", {}).get("NATIONAL", {}).get(INDEX_PRODUCT)
    eid = nat["evidence_id"]
    k = claims.add("Territories reporting this week", len(nat["reporting"]), "int", eid)
    n = claims.add("Territories in the release", len(TERRITORIES), "int", eid)
    trx = claims.add(f"National {INDEX_PRODUCT} TRx, reportable cuts", nat["trx"], "int", eid)
    rel = claims.add("Like-for-like change vs four-week average", nat["rel"], "pct_signed", eid)
    nb = claims.add(f"National {INDEX_PRODUCT} NBRx, reportable cuts", nat["nbrx"], "int", eid)
    lines = [f"National {PRODUCTS[INDEX_PRODUCT]} TRx was {trx} ({rel} like-for-like against the four-week average) "
             f"from {k} of {n} territories. New-to-brand prescriptions (NBRx) were {nb}."]
    if share is not None:
        sh = claims.add(f"{INDEX_PRODUCT} share of the four-brand basket", share, "pct", ceid)
        lines.append(f"{PRODUCTS[INDEX_PRODUCT]} held {sh} of the four-brand basket.")
    return lines


def detect(tools: ToolRegistry, claims: ClaimBook, week: date, series: dict, eid: str, nat: dict) -> list[Candidate]:
    t = DETECTION
    out: list[Candidate] = []
    n = 0

    def nid() -> str:
        nonlocal n
        n += 1
        return f"K-{n:02d}"

    # National: like-for-like, or a naive move that only withheld cuts could explain.
    withheld = [x for x in TERRITORIES if x not in nat["reporting"]]
    if abs(nat["rel"]) >= t["national_rel"] or (withheld and abs(nat["naive_rel"]) >= t["national_rel"]):
        rel = nat["rel"] if abs(nat["rel"]) >= t["national_rel"] else nat["naive_rel"]
        out.append(Candidate(candidate_id=nid(), kind="national", week=week, window_start=week,
                             actual=nat["trx"], baseline=nat["base"], change_abs=nat["trx"] - nat["base"],
                             change_rel=rel, direction="down" if rel < 0 else "up",
                             impact=abs(nat["trx"] - (nat["naive_base"] if rel == nat["naive_rel"] else nat["base"])),
                             rule="national like-for-like vs four-week average" if rel == nat["rel"] else
                                  "naive national total vs four-week average, with withheld cuts",
                             evidence_id=eid,
                             extra={"withheld": withheld, "naive_rel": nat["naive_rel"], "lfl_rel": nat["rel"]}))

    prev4 = [shift(week, -k) for k in range(1, 5)]
    win = [shift(week, -k) for k in range(0, 4)]
    base8 = [shift(week, -k) for k in range(4, 12)]

    def avg(terr, weeks):
        return mean(series[terr][w]["trx"] for w in weeks if w in series.get(terr, {}))

    reporting = [x for x in TERRITORIES if week in series.get(x, {})]
    for terr in reporting:
        others = [x for x in reporting if x != terr]
        # Single-week, peer-adjusted.
        cur, b4 = series[terr][week]["trx"], avg(terr, prev4)
        o_cur = sum(series[x][week]["trx"] for x in others)
        o_b4 = sum(avg(x, prev4) or 0 for x in others)
        single = None
        if b4 and o_b4:
            rel, orel = cur / b4 - 1, o_cur / o_b4 - 1
            if abs(rel - orel) >= t["single_gap"] and abs(cur - b4) >= t["single_abs"]:
                single = Candidate(candidate_id="", kind="territory_single", territory=terr, week=week, window_start=week,
                                   actual=cur, baseline=b4, change_abs=cur - b4, change_rel=rel, peer_rel=orel,
                                   gap=rel - orel, direction="down" if rel < orel else "up", impact=abs(cur - b4),
                                   rule="single week vs four-week average, peer-adjusted", evidence_id=eid)
        # Sustained: last 4 weeks vs the 8 before, minus the same for peers.
        sustained = None
        cw, cb = avg(terr, win), avg(terr, base8)
        ow = sum(avg(x, win) or 0 for x in others)
        ob = sum(avg(x, base8) or 0 for x in others)
        if cw and cb and ow and ob:
            rel, orel = cw / cb - 1, ow / ob - 1
            if abs(rel - orel) >= t["sustained_gap"] and abs(cw - cb) >= t["sustained_abs"]:
                sustained = Candidate(candidate_id="", kind="territory_sustained", territory=terr, week=week,
                                      window_start=shift(week, -3), actual=cw, baseline=cb, change_abs=cw - cb,
                                      change_rel=rel, peer_rel=orel, gap=rel - orel,
                                      direction="down" if rel < orel else "up", impact=abs(cw - cb),
                                      rule="last four weeks vs eight before, peer-adjusted", evidence_id=eid)
        pick = sustained or single
        if pick:
            pick.candidate_id = nid()
            out.append(pick)

    # Competitor: a recent launch with material share is a continuing story.
    comp, ceid = tools.call("compare_competitors", start=week, end=week,
                            base_start=shift(week, -4), base_end=shift(week, -1))
    nat_share = comp["shares"].get("window", {}).get("NATIONAL", {})
    for launch in comp["launches"]:
        start = d(launch["effective_start"])
        if launch["product"] == INDEX_PRODUCT or not (shift(week, -t["competitor_launch_weeks"]) < start <= week):
            continue
        share = nat_share.get(launch["product"], 0.0)
        if share >= t["competitor_share"]:
            market = None
            out.append(Candidate(candidate_id=nid(), kind="competitor", product=launch["product"], week=week,
                                 window_start=start, actual=share, baseline=0.0, change_abs=share, change_rel=share,
                                 direction="up", impact=share * 10000, rule="recent launch with material share",
                                 evidence_id=ceid, extra={"launch": start.isoformat(), "market": market}))

    out.sort(key=lambda c: -c.impact)
    return out[: t["max_candidates"]]
