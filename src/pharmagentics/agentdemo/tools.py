"""Typed tools and the registry that writes evidence items (FR-010, FR-014).

Every tool is plain deterministic code over the governed views: no model inside, no
agent calls. The registry wraps each call in a span and records the evidence item
(tool, parameters, the exact SQL, the result, the pinned data version, the span).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Callable

from .config import DRIVER_RULES
from .contracts import EvidenceItem
from .db import GovernedDB
from .tracing import Tracer


def d(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def shift(day: date, weeks: int) -> date:
    return day + timedelta(weeks=weeks)


def month_start(day: date) -> date:
    return day.replace(day=1)


def add_months(day: date, months: int) -> date:
    m = day.month - 1 + months
    return date(day.year + m // 12, m % 12 + 1, 1)


def mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


class _Q:
    """Collects the SQL a tool runs so the evidence item shows it verbatim."""

    def __init__(self, db: GovernedDB):
        self.db, self.sql = db, []

    def __call__(self, sql: str, params: list[Any] | None = None):
        text = " ".join(sql.split())
        shown = text
        for p in params or []:
            shown = shown.replace("?", repr(p.isoformat() if isinstance(p, date) else p), 1)
        self.sql.append(shown)
        return self.db.query(text, params)


# ----------------------------------------------------------------- tools

def data_pin(q: _Q) -> dict:
    rows = q("""SELECT m.load_id, m.sha256, m.row_count, r.completed_at
                FROM metadata.import_manifest m JOIN metadata.import_runs r USING (load_id)
                WHERE m.table_name = 'rx_weekly' AND r.completed_at IS NOT NULL
                ORDER BY r.completed_at DESC LIMIT 1""")
    row = rows[0]
    return {"load_id": row["load_id"], "rx_weekly_sha256": row["sha256"], "rx_rows": row["row_count"],
            "loaded_at": str(row["completed_at"])}


def validate_feed(q: _Q, start: str, end: str, territory: str | None = None) -> dict:
    sql = """SELECT week_start, territory_id, health_status, flag_reasons, panel_coverage_ratio,
                    actual_lag_days, expected_lag_days, observed_rows, expected_key_count
             FROM reporting.v_feed_health WHERE week_start BETWEEN ? AND ?"""
    params: list[Any] = [d(start), d(end)]
    if territory:
        sql += " AND territory_id = ?"
        params.append(territory)
    rows = q(sql + " ORDER BY week_start, territory_id", params)
    out = [{"week": r["week_start"].isoformat(), "territory": r["territory_id"], "status": r["health_status"],
            "reasons": [x for x in (r["flag_reasons"] or "").split(";") if x],
            "coverage": r["panel_coverage_ratio"], "lag_days": r["actual_lag_days"],
            "target_lag_days": r["expected_lag_days"], "rows": r["observed_rows"],
            "expected_rows": r["expected_key_count"]} for r in rows]
    flagged = [r for r in out if r["status"] != "PASS"]
    return {"cuts": len(out), "passed": len(out) - len(flagged), "flagged": flagged, "rows": out}


def get_metric(q: _Q, product: str, start: str, end: str, territory: str | None = None) -> dict:
    sql = """SELECT week_start, territory_id, trx, nrx, nbrx FROM reporting.v_weekly_rx_kpis
             WHERE product_id = ? AND week_start BETWEEN ? AND ?"""
    params: list[Any] = [product, d(start), d(end)]
    if territory:
        sql += " AND territory_id = ?"
        params.append(territory)
    rows = q(sql + " ORDER BY week_start, territory_id", params)
    return {"rows": [{"week": r["week_start"].isoformat(), "territory": r["territory_id"],
                      "trx": r["trx"], "nrx": r["nrx"], "nbrx": r["nbrx"]} for r in rows]}


def compare_competitors(q: _Q, start: str, end: str, base_start: str, base_end: str) -> dict:
    rows = q("""SELECT territory_id, product_id, week_start, trx FROM reporting.v_weekly_rx_kpis
                WHERE (week_start BETWEEN ? AND ?) OR (week_start BETWEEN ? AND ?)""",
             [d(start), d(end), d(base_start), d(base_end)])
    launches = q("SELECT product_id, effective_start, launch_date FROM raw.market_basket ORDER BY product_id")
    sums: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for r in rows:
        period = "window" if d(start) <= r["week_start"] <= d(end) else "base"
        sums[period][r["territory_id"]][r["product_id"]] += r["trx"]
        sums[period]["NATIONAL"][r["product_id"]] += r["trx"]
    shares = {p: {t: {prod: (v / sum(prods.values()) if sum(prods.values()) else 0.0) for prod, v in prods.items()}
                  for t, prods in terr.items()} for p, terr in sums.items()}
    return {"shares": shares,
            "launches": [{"product": r["product_id"], "effective_start": r["effective_start"].isoformat(),
                          "launch_date": r["launch_date"]} for r in launches]}


def decompose_change(q: _Q, product: str, start: str, end: str, base_start: str, base_end: str,
                     by: str, territory: str | None = None) -> dict:
    if by not in ("territory_id", "payer_channel", "plan_id", "hcp_specialty"):
        raise ValueError(f"unknown dimension {by}")
    sql = f"""SELECT {by} AS seg, CASE WHEN week_start >= ? THEN 'window' ELSE 'base' END AS period,
                     sum(trx) AS trx, count(DISTINCT week_start) AS weeks
              FROM reporting.v_reportable_rx
              WHERE product_id = ? AND ((week_start BETWEEN ? AND ?) OR (week_start BETWEEN ? AND ?))"""
    params: list[Any] = [d(start), product, d(start), d(end), d(base_start), d(base_end)]
    if territory:
        sql += " AND territory_id = ?"
        params.append(territory)
    rows = q(sql + " GROUP BY ALL", params)
    seg: dict = defaultdict(dict)
    for r in rows:
        seg[r["seg"]][r["period"]] = r["trx"] / r["weeks"]
    parts = [{"segment": s, "window_avg": v.get("window", 0.0), "base_avg": v.get("base", 0.0),
              "contribution": v.get("window", 0.0) - v.get("base", 0.0)} for s, v in seg.items()]
    parts.sort(key=lambda p: p["contribution"])
    total = sum(p["contribution"] for p in parts)
    return {"by": by, "total_change": total, "parts": parts}


def scan_events(q: _Q, product: str, start: str, end: str, base_start: str) -> dict:
    """Territories with their own active event in [base_start, end]; used to drop controls."""
    floor = DRIVER_RULES["fill_floor"]
    inv = q("""SELECT territory_id, count(*) FILTER (WHERE inventory_fill_rate < ?) AS low_weeks
               FROM raw.inventory_weekly WHERE product_id = ? AND week_start BETWEEN ? AND ? GROUP BY 1""",
            [floor, product, d(base_start), d(end)])
    promo = q("""SELECT territory_id,
                        avg(rep_calls_aggregated) FILTER (WHERE week_start >= ?) AS calls_win,
                        avg(rep_calls_aggregated) FILTER (WHERE week_start < ?) AS calls_base,
                        max(rep_vacancy_count_aggregated) AS vacancy
                 FROM raw.promo_activity WHERE product_id = ? AND week_start BETWEEN ? AND ? GROUP BY 1""",
              [d(start), d(start), product, d(base_start), d(end)])
    acc = q("""SELECT territory_id, plan_id,
                      count(DISTINCT (covered, formulary_tier, prior_authorization, step_therapy)) AS states
               FROM raw.access_status_monthly WHERE product_id = ? AND month BETWEEN ? AND ? GROUP BY 1, 2""",
            [product, add_months(month_start(d(base_start)), -1), d(end)])
    events: dict = defaultdict(list)
    for r in inv:
        if r["low_weeks"] >= 2:
            events[r["territory_id"]].append("supply shortfall")
    for r in promo:
        base, win = r["calls_base"] or 0, r["calls_win"] or 0
        if (base and abs(win / base - 1) >= DRIVER_RULES["promo_change"]) or (r["vacancy"] or 0) > 0:
            events[r["territory_id"]].append("promotion change")
    for r in acc:
        if r["states"] > 1 and "access change" not in events[r["territory_id"]]:
            events[r["territory_id"]].append("access change")
    return {"events": dict(events)}


def compare_to_peers(q: _Q, territory: str, product: str, start: str, end: str, base_start: str, base_end: str,
                     exclude: list[str] | None = None) -> dict:
    rows = q("""SELECT territory_id, CASE WHEN week_start >= ? THEN 'window' ELSE 'base' END AS period,
                       avg(trx) AS avg_trx, count(*) AS weeks
                FROM reporting.v_weekly_rx_kpis
                WHERE product_id = ? AND ((week_start BETWEEN ? AND ?) OR (week_start BETWEEN ? AND ?))
                GROUP BY ALL""", [d(start), product, d(start), d(end), d(base_start), d(base_end)])
    avg: dict = defaultdict(dict)
    for r in rows:
        avg[r["territory_id"]][r["period"]] = r["avg_trx"]
    exclude = set(exclude or [])
    exp = avg.get(territory, {})
    controls = sorted(t for t in avg if t != territory and t not in exclude and {"window", "base"} <= set(avg[t]))
    dropped = sorted(t for t in exclude if t != territory)
    if not controls:  # never leave the comparison empty; record that controls were contaminated
        controls = sorted(t for t in avg if t != territory and {"window", "base"} <= set(avg[t]))
        dropped = []
    cw, cb = sum(avg[t]["window"] for t in controls), sum(avg[t]["base"] for t in controls)
    exp_rel = (exp["window"] / exp["base"] - 1) if exp.get("base") and "window" in exp else None
    ctl_rel = (cw / cb - 1) if cb else None
    return {"territory": territory, "window_avg": exp.get("window"), "base_avg": exp.get("base"),
            "exposed_rel": exp_rel, "control_rel": ctl_rel,
            "gap": (exp_rel - ctl_rel) if exp_rel is not None and ctl_rel is not None else None,
            "control_set": controls, "dropped_controls": dropped,
            "method": "exposed vs control territories, same weeks (difference in relative change)"}


def lookup_access_events(q: _Q, territory: str, product: str, month_from: str, month_to: str) -> dict:
    rows = q("""SELECT month, plan_id, payer_channel, covered, formulary_tier, prior_authorization, step_therapy,
                       covered_lives_weight
                FROM raw.access_status_monthly
                WHERE territory_id = ? AND product_id = ? AND month BETWEEN ? AND ?
                ORDER BY plan_id, month""", [territory, product, d(month_from), d(month_to)])
    by_plan: dict = defaultdict(list)
    for r in rows:
        by_plan[r["plan_id"]].append(r)

    def score(r):
        return (1 - r["covered"]) * 3 + max(r["formulary_tier"] - 2, 0) + r["prior_authorization"] + r["step_therapy"]

    events = []
    for plan, seq in by_plan.items():
        for prev, cur in zip(seq, seq[1:]):
            if score(cur) != score(prev):
                events.append({"plan_id": plan, "payer_channel": cur["payer_channel"], "month": cur["month"].isoformat(),
                               "kind": "restriction_added" if score(cur) > score(prev) else "restriction_removed",
                               "from": {"tier": prev["formulary_tier"], "pa": prev["prior_authorization"],
                                        "step": prev["step_therapy"], "covered": prev["covered"]},
                               "to": {"tier": cur["formulary_tier"], "pa": cur["prior_authorization"],
                                      "step": cur["step_therapy"], "covered": cur["covered"]},
                               "covered_lives_weight": cur["covered_lives_weight"]})
    return {"plans_checked": len(by_plan), "events": events}


def get_plan_metric(q: _Q, plan_id: str, start: str, end: str, base_start: str, base_end: str) -> dict:
    rows = q("""SELECT product_id, CASE WHEN week_start >= ? THEN 'window' ELSE 'base' END AS period,
                       sum(trx) * 1.0 / count(DISTINCT week_start) AS avg_trx
                FROM reporting.v_reportable_rx
                WHERE plan_id = ? AND ((week_start BETWEEN ? AND ?) OR (week_start BETWEEN ? AND ?))
                GROUP BY ALL""", [d(start), plan_id, d(start), d(end), d(base_start), d(base_end)])
    out: dict = defaultdict(dict)
    for r in rows:
        out[r["product_id"]][r["period"]] = r["avg_trx"]
    return {"plan_id": plan_id, "by_product": dict(out)}


def lookup_promo(q: _Q, territory: str, product: str, start: str, end: str, base_start: str, base_end: str) -> dict:
    rows = q("""SELECT CASE WHEN week_start >= ? THEN 'window' ELSE 'base' END AS period,
                       avg(rep_calls_aggregated) AS calls, avg(digital_impressions) AS impressions,
                       max(rep_vacancy_count_aggregated) AS vacancy, count(*) AS weeks
                FROM raw.promo_activity
                WHERE territory_id = ? AND product_id = ? AND ((week_start BETWEEN ? AND ?) OR (week_start BETWEEN ? AND ?))
                GROUP BY 1""", [d(start), territory, product, d(start), d(end), d(base_start), d(base_end)])
    per = {r["period"]: {"calls": r["calls"], "impressions": r["impressions"], "vacancy": r["vacancy"],
                         "weeks": r["weeks"]} for r in rows}
    return {"level": "territory (aggregated at source)", **per}


def lookup_inventory(q: _Q, territory: str, product: str, start: str, end: str, base_start: str, base_end: str) -> dict:
    rows = q("""SELECT CASE WHEN week_start >= ? THEN 'window' ELSE 'base' END AS period,
                       avg(inventory_fill_rate) AS fill, min(inventory_fill_rate) AS min_fill,
                       avg(distribution_backorder_rate) AS backorder,
                       count(*) FILTER (WHERE inventory_fill_rate < ?) AS low_weeks, count(*) AS weeks
                FROM raw.inventory_weekly
                WHERE territory_id = ? AND product_id = ? AND ((week_start BETWEEN ? AND ?) OR (week_start BETWEEN ? AND ?))
                GROUP BY 1""", [d(start), DRIVER_RULES["fill_floor"], territory, product,
                                d(start), d(end), d(base_start), d(base_end)])
    return {r["period"]: {k: r[k] for k in ("fill", "min_fill", "backorder", "low_weeks", "weeks")} for r in rows}


def lookup_calendar(q: _Q, start: str, end: str) -> dict:
    rows = q("""SELECT week_start, holiday_flag, holiday_name, business_days, plan_year_reset
                FROM raw.calendar WHERE week_start BETWEEN ? AND ? ORDER BY week_start""", [d(start), d(end)])
    return {"weeks": [{"week": r["week_start"].isoformat(), "holiday": bool(r["holiday_flag"]),
                       "holiday_name": r["holiday_name"], "business_days": r["business_days"],
                       "plan_year_reset": bool(r["plan_year_reset"])} for r in rows]}


def lookup_restatement(q: _Q, product: str, start: str, end: str, territory: str | None = None) -> dict:
    sql = """SELECT week_start, territory_id, count(*) AS cells, sum(trx_prior) AS trx_prior,
                    sum(trx_revised) AS trx_revised, sum(nbrx_prior) AS nbrx_prior, sum(nbrx_revised) AS nbrx_revised,
                    max(revised_at) AS revised_at, min(revision_reason) AS reason
             FROM raw.restatement_log WHERE product_id = ? AND week_start BETWEEN ? AND ?"""
    params: list[Any] = [product, d(start), d(end)]
    if territory:
        sql += " AND territory_id = ?"
        params.append(territory)
    rows = q(sql + " GROUP BY 1, 2 ORDER BY 1, 2", params)
    return {"restatements": [{"week": r["week_start"].isoformat(), "territory": r["territory_id"], "cells": r["cells"],
                              "trx_prior": r["trx_prior"], "trx_revised": r["trx_revised"],
                              "nbrx_prior": r["nbrx_prior"], "nbrx_revised": r["nbrx_revised"],
                              "revised_at": r["revised_at"].isoformat(), "reason": r["reason"]} for r in rows]}


TOOLS: dict[str, Callable[..., Any]] = {
    "data_pin": data_pin, "validate_feed": validate_feed, "get_metric": get_metric,
    "compare_competitors": compare_competitors, "decompose_change": decompose_change,
    "scan_events": scan_events, "compare_to_peers": compare_to_peers,
    "lookup_access_events": lookup_access_events, "get_plan_metric": get_plan_metric,
    "lookup_promo": lookup_promo, "lookup_inventory": lookup_inventory,
    "lookup_calendar": lookup_calendar, "lookup_restatement": lookup_restatement,
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    return value


class ToolRegistry:
    """One wrapper for every tool call: span, evidence item, typed errors."""

    def __init__(self, db: GovernedDB, tracer: Tracer, run_id: str):
        self.db, self.tracer, self.run_id = db, tracer, run_id
        self.data_version = "unpinned"
        self.evidence: dict[str, EvidenceItem] = {}

    def call(self, tool: str, agent: str = "code", **params: Any) -> tuple[Any, str]:
        if tool not in TOOLS:
            raise KeyError(f"Unknown tool {tool}")
        clean = _jsonable(params)
        with self.tracer.span(f"tool · {tool}", agent=agent, kind="tool", params=clean) as span:
            q = _Q(self.db)
            result = TOOLS[tool](q, **params)
            eid = f"E-{len(self.evidence) + 1:03d}"
            self.evidence[eid] = EvidenceItem(evidence_id=eid, run_id=self.run_id, tool=tool, params=clean,
                                              sql=";\n".join(q.sql), result=_jsonable(result),
                                              data_version=self.data_version, span_id=span["span_id"])
            span["attrs"]["evidence_id"] = eid
        return result, eid
