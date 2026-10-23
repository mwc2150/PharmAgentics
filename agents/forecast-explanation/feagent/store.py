"""DuckDB shared data layer for briefing + forecast-explanation.

Investigator tools may read weekly_performance, commercial_events, and
investigation_requests. They must not read eval_ground_truth.
"""

from __future__ import annotations

import json
from typing import Any

import duckdb

from feagent import config
from feagent.config import BRAND, METRIC
from feagent.synthetic import build_case, week_ending

SCHEMA_VERSION = "2"
_connection: duckdb.DuckDBPyConnection | None = None

BRIEFING_REQUEST = {
    "request_id": "brief_lumina_w18",
    "source": "briefing_agent",
    "brand": BRAND,
    "week": 18,
    "week_ending": week_ending(18),
    "metric": METRIC,
    "notes": (
        "Brand-Performance Briefing Agent flagged a material national TRx miss "
        "in week 18 (actual 9,600 vs forecast 12,000). Please explain drivers, "
        "magnitude, confidence, and what to check."
    ),
}


def reset() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def connect() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        _connection = duckdb.connect(config.DUCKDB_PATH)
        _ensure_schema(_connection)
    return _connection


def fetchone(sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
    rel = connect().execute(sql, params or [])
    columns = [c[0] for c in rel.description]
    row = rel.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def fetchall(sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
    rel = connect().execute(sql, params or [])
    columns = [c[0] for c in rel.description]
    return [dict(zip(columns, row)) for row in rel.fetchall()]


def default_request() -> dict[str, Any]:
    connect()
    row = fetchone(
        "SELECT request_id, source, brand, week, week_ending, metric, notes "
        "FROM investigation_requests WHERE request_id = 'req_lumina_w18'"
    )
    if row is None:
        return BRIEFING_REQUEST
    return row


def briefing_request() -> dict[str, Any]:
    connect()
    row = fetchone(
        "SELECT request_id, source, brand, week, week_ending, metric, notes "
        "FROM investigation_requests WHERE request_id = 'brief_lumina_w18'"
    )
    return row or dict(BRIEFING_REQUEST)


def _ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS meta (key VARCHAR PRIMARY KEY, value VARCHAR)")
    current = con.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ).fetchone()
    if current and current[0] == SCHEMA_VERSION:
        n = con.execute("SELECT COUNT(*) FROM weekly_performance").fetchone()[0]
        if n:
            return
    for table in (
        "weekly_performance",
        "commercial_events",
        "investigation_requests",
        "eval_ground_truth",
        "meta",
    ):
        con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute("CREATE TABLE meta (key VARCHAR PRIMARY KEY, value VARCHAR)")
    con.execute(
        """
        CREATE TABLE weekly_performance (
            brand VARCHAR,
            week INTEGER,
            week_ending VARCHAR,
            region VARCHAR,
            segment VARCHAR,
            metric VARCHAR,
            forecast DOUBLE,
            actual DOUBLE,
            access_status VARCHAR,
            competitor_share DOUBLE
        )
        """
    )
    con.execute(
        """
        CREATE TABLE commercial_events (
            event_id VARCHAR,
            driver VARCHAR,
            label VARCHAR,
            week INTEGER,
            week_ending VARCHAR,
            exposed_regions VARCHAR,
            control_regions VARCHAR,
            excluded_regions VARCHAR,
            notes VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE investigation_requests (
            request_id VARCHAR PRIMARY KEY,
            source VARCHAR,
            brand VARCHAR,
            week INTEGER,
            week_ending VARCHAR,
            metric VARCHAR,
            notes VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE eval_ground_truth (
            case_id VARCHAR,
            driver VARCHAR,
            event_id VARCHAR,
            impact_trx DOUBLE,
            start_week INTEGER
        )
        """
    )
    _seed(con)
    con.execute(
        "INSERT INTO meta VALUES ('schema_version', ?), ('restricted', 'eval_ground_truth is evaluator-only')",
        [SCHEMA_VERSION],
    )


def _seed(con: duckdb.DuckDBPyConnection) -> None:
    case = build_case()
    obs = case["observable"]
    truth = case["ground_truth"]
    perf_rows = []
    for row in obs["weekly_region"]:
        access = "preferred"
        share = 0.05
        if row["region"] in {"Northeast", "South"} and row["week"] >= 17:
            access = "formulary_downgrade"
        if row["region"] == "Midwest" and row["week"] >= 18:
            share = 0.18
        for metric, forecast, actual in (
            ("TRx", row["forecast"], row["actual"]),
            ("NRx", None, None),
            ("NBRx", None, None),
        ):
            perf_rows.append(
                (
                    row["brand"],
                    row["week"],
                    row["week_ending"],
                    row["region"],
                    "all",
                    metric,
                    forecast,
                    actual,
                    access if metric == "TRx" else None,
                    share if metric == "TRx" else None,
                )
            )
    for row in obs["weekly_national"]:
        for metric, forecast, actual in (
            ("TRx", row["forecast"], row["actual"]),
            ("NRx", None, None),
            ("NBRx", None, None),
        ):
            perf_rows.append(
                (
                    row["brand"],
                    row["week"],
                    row["week_ending"],
                    "NATIONAL",
                    "all",
                    metric,
                    forecast,
                    actual,
                    None,
                    None,
                )
            )
    con.executemany(
        "INSERT INTO weekly_performance VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        perf_rows,
    )
    event_rows = [
        (
            event["event_id"],
            event["driver"],
            event["label"],
            event["week"],
            event["week_ending"],
            json.dumps(event["exposed_regions"]),
            json.dumps(event["control_regions"]),
            json.dumps(event.get("excluded_regions", [])),
            event.get("notes", ""),
        )
        for event in obs["events"]
    ]
    con.executemany(
        "INSERT INTO commercial_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        event_rows,
    )
    manual = obs["default_request"]
    con.executemany(
        "INSERT INTO investigation_requests VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                manual["request_id"],
                manual["source"],
                manual["brand"],
                manual["week"],
                manual["week_ending"],
                manual["metric"],
                manual.get("notes"),
            ),
            (
                BRIEFING_REQUEST["request_id"],
                BRIEFING_REQUEST["source"],
                BRIEFING_REQUEST["brand"],
                BRIEFING_REQUEST["week"],
                BRIEFING_REQUEST["week_ending"],
                BRIEFING_REQUEST["metric"],
                BRIEFING_REQUEST["notes"],
            ),
        ],
    )
    truth_rows = [
        (
            "week18",
            item["driver"],
            item["event_id"],
            item["impact_trx"],
            item["start_week"],
        )
        for item in truth["injected_drivers"]
    ]
    truth_rows.append(("week18", "residual", None, truth["residual_trx"], 18))
    con.executemany(
        "INSERT INTO eval_ground_truth VALUES (?, ?, ?, ?, ?)",
        truth_rows,
    )
