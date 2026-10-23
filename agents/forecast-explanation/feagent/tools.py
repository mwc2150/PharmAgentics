"""Deterministic analytical tools. Every cited number must come from DuckDB."""

from __future__ import annotations

import json
from typing import Any, Callable
from uuid import uuid4

from feagent.store import fetchall, fetchone

BASELINE_WEEK_OFFSET = 2
INVESTIGATOR_TABLES = {"weekly_performance", "commercial_events", "investigation_requests"}


def _record(name: str, arguments: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool_id": f"t_{uuid4().hex[:8]}",
        "name": name,
        "arguments": arguments,
        "payload": payload,
    }


def _decode_regions(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return json.loads(value)


def validate_and_quantify(week: int, case_id: str = "week18") -> dict[str, Any]:
    row = fetchone(
        """
        SELECT brand, week, week_ending, metric, forecast, actual, access_status
        FROM weekly_performance
        WHERE region = 'NATIONAL' AND metric = 'TRx' AND week = ?
        """,
        [week],
    )
    if row is None:
        return _record(
            "validate_and_quantify",
            {"week": week, "case_id": case_id},
            {"ok": False, "error": f"No national TRx row for week {week}"},
        )
    regions = fetchall(
        """
        SELECT region, forecast, actual
        FROM weekly_performance
        WHERE region != 'NATIONAL' AND metric = 'TRx' AND week = ?
        ORDER BY region
        """,
        [week],
    )
    forecast = float(row["forecast"])
    actual = float(row["actual"])
    variance = actual - forecast
    missing = [r["region"] for r in regions if r["actual"] is None or r["forecast"] is None]
    provisional = str(row.get("access_status") or "") == "provisional"
    payload = {
        "brand": row["brand"],
        "week": week,
        "week_ending": row["week_ending"],
        "metric": row["metric"],
        "forecast": forecast,
        "actual": actual,
        "variance_trx": variance,
        "variance_pct": variance / forecast if forecast else None,
        "n_regions": len(regions),
        "missing_regions": missing,
        "data_complete": not missing,
        "actual_is_provisional": provisional,
        "source": "duckdb.weekly_performance",
        "ok": True,
    }
    return _record("validate_and_quantify", {"week": week, "case_id": case_id}, payload)


def get_region_deltas(week: int, case_id: str = "week18") -> dict[str, Any]:
    baseline_week = week - BASELINE_WEEK_OFFSET
    current = {
        r["region"]: r
        for r in fetchall(
            """
            SELECT region, forecast, actual
            FROM weekly_performance
            WHERE region != 'NATIONAL' AND metric = 'TRx' AND week = ?
            """,
            [week],
        )
    }
    baseline = {
        r["region"]: r
        for r in fetchall(
            """
            SELECT region, actual
            FROM weekly_performance
            WHERE region != 'NATIONAL' AND metric = 'TRx' AND week = ?
            """,
            [baseline_week],
        )
    }
    deltas = []
    for region, row in current.items():
        base = baseline[region]
        deltas.append(
            {
                "region": region,
                "forecast": row["forecast"],
                "actual": row["actual"],
                "variance_trx": row["actual"] - row["forecast"],
                "baseline_week": baseline_week,
                "baseline_actual": base["actual"],
                "delta_vs_baseline": row["actual"] - base["actual"],
            }
        )
    payload = {"week": week, "baseline_week": baseline_week, "regions": deltas, "source": "duckdb.weekly_performance"}
    return _record("get_region_deltas", {"week": week, "case_id": case_id}, payload)


def list_candidate_events(week: int, window: int = 2, case_id: str = "week18") -> dict[str, Any]:
    lo, hi = week - window, week + window
    rows = fetchall(
        """
        SELECT event_id, driver, label, week, week_ending, exposed_regions,
               control_regions, excluded_regions, notes
        FROM commercial_events
        WHERE week BETWEEN ? AND ?
        ORDER BY week, event_id
        """,
        [lo, hi],
    )
    events = []
    for row in rows:
        events.append(
            {
                **row,
                "exposed_regions": _decode_regions(row["exposed_regions"]),
                "control_regions": _decode_regions(row["control_regions"]),
                "excluded_regions": _decode_regions(row["excluded_regions"]),
            }
        )
    payload = {
        "week": week,
        "window": window,
        "events": events,
        "n_events": len(events),
        "source": "duckdb.commercial_events",
    }
    return _record(
        "list_candidate_events",
        {"week": week, "window": window, "case_id": case_id},
        payload,
    )


def compare_exposed_control(
    event_id: str,
    week: int,
    case_id: str = "week18",
) -> dict[str, Any]:
    event = fetchone(
        """
        SELECT event_id, driver, label, week, week_ending, exposed_regions,
               control_regions, excluded_regions, notes
        FROM commercial_events
        WHERE event_id = ?
        """,
        [event_id],
    )
    if event is None:
        return _record(
            "compare_exposed_control",
            {"event_id": event_id, "week": week},
            {"ok": False, "error": f"Unknown event_id {event_id}"},
        )

    exposed = _decode_regions(event["exposed_regions"])
    control = _decode_regions(event["control_regions"])
    excluded = _decode_regions(event["excluded_regions"])
    baseline_week = week - BASELINE_WEEK_OFFSET
    actuals = {
        r["region"]: r["actual"]
        for r in fetchall(
            """
            SELECT region, week, actual
            FROM weekly_performance
            WHERE region != 'NATIONAL' AND metric = 'TRx' AND week IN (?, ?)
            """,
            [week, baseline_week],
        )
        if r["week"] == week
    }
    baseline = {
        r["region"]: r["actual"]
        for r in fetchall(
            """
            SELECT region, week, actual
            FROM weekly_performance
            WHERE region != 'NATIONAL' AND metric = 'TRx' AND week IN (?, ?)
            """,
            [week, baseline_week],
        )
        if r["week"] == baseline_week
    }

    def _mean_delta(regions: list[str]) -> tuple[float | None, list[dict[str, Any]]]:
        if not regions:
            return None, []
        rows = [{"region": region, "delta": actuals[region] - baseline[region]} for region in regions]
        return sum(r["delta"] for r in rows) / len(rows), rows

    exp_mean, exp_rows = _mean_delta(exposed)
    ctl_mean, ctl_rows = _mean_delta(control)
    did = None if exp_mean is None or ctl_mean is None else exp_mean - ctl_mean
    estimated_total = None if did is None else did * len(exposed)
    payload = {
        "ok": True,
        "event_id": event_id,
        "driver": event["driver"],
        "label": event["label"],
        "week": week,
        "baseline_week": baseline_week,
        "exposed_regions": exposed,
        "control_regions": control,
        "excluded_regions": excluded,
        "exposed_mean_delta": exp_mean,
        "control_mean_delta": ctl_mean,
        "did_per_exposed_region": did,
        "estimated_total_trx": estimated_total,
        "exposed_detail": exp_rows,
        "control_detail": ctl_rows,
        "method": "difference_in_differences_vs_named_controls",
        "notes": event.get("notes") or "",
        "assumption": "Named control regions are unaffected by this driver. Overlap is handled by excluding contaminated regions, not by a joint model.",
        "source": "duckdb.weekly_performance + duckdb.commercial_events",
    }
    return _record(
        "compare_exposed_control",
        {"event_id": event_id, "week": week, "case_id": case_id},
        payload,
    )


def reconcile_attribution(
    variance_trx: float,
    driver_impacts: dict[str, float],
) -> dict[str, Any]:
    explained = sum(driver_impacts.values())
    residual = variance_trx - explained
    payload = {
        "variance_trx": variance_trx,
        "driver_impacts": driver_impacts,
        "explained_trx": explained,
        "residual_trx": residual,
        "reconciles": abs(explained + residual - variance_trx) < 1e-6,
    }
    return _record(
        "reconcile_attribution",
        {"variance_trx": variance_trx, "driver_impacts": driver_impacts},
        payload,
    )


TOOL_SPECS: dict[str, dict[str, Any]] = {
    "validate_and_quantify": {
        "description": "Validate completeness and quantify national forecast vs actual variance for a week.",
        "parameters": {"week": "int", "case_id": "str, optional"},
    },
    "get_region_deltas": {
        "description": "Region-level actual vs forecast and vs a two-week baseline.",
        "parameters": {"week": "int", "case_id": "str, optional"},
    },
    "list_candidate_events": {
        "description": "Commercial events in a window around the flagged week.",
        "parameters": {"week": "int", "window": "int, optional", "case_id": "str, optional"},
    },
    "compare_exposed_control": {
        "description": "Difference-in-differences estimate for one event using its named exposed and control regions.",
        "parameters": {"event_id": "str", "week": "int", "case_id": "str, optional"},
    },
    "reconcile_attribution": {
        "description": "Check that driver estimates plus residual equal the national variance.",
        "parameters": {"variance_trx": "float", "driver_impacts": "object mapping driver -> TRx impact"},
    },
}


def run_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    fns: dict[str, Callable[..., dict[str, Any]]] = {
        "validate_and_quantify": validate_and_quantify,
        "get_region_deltas": get_region_deltas,
        "list_candidate_events": list_candidate_events,
        "compare_exposed_control": compare_exposed_control,
        "reconcile_attribution": reconcile_attribution,
    }
    if name not in fns:
        return _record(name, arguments, {"ok": False, "error": f"Unknown tool {name}"})
    return fns[name](**arguments)
