"""Governed, read-only data access for the brief-006 tools (FR-014).

Rx metrics come only from the gated reporting views. Context comes only from an
allowlist of agent-visible tables. The ground-truth store and its environment
variable are never read here or anywhere in this package.
"""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = ROOT / "local" / "pharmagentics.duckdb"

ALLOWED_RELATIONS = frozenset({
    # Rx metrics: gated views only (raw.rx_weekly is deliberately absent).
    "reporting.v_feed_health",
    "reporting.v_reportable_rx",
    "reporting.v_weekly_rx_kpis",
    # Context tables, agent-visible, already aggregated at source.
    "raw.access_status_monthly",
    "raw.promo_activity",
    "raw.inventory_weekly",
    "raw.calendar",
    "raw.restatement_log",
    "raw.market_basket",
    "raw.dim_territory",
    "raw.dim_plan",
    "raw.dim_product",
    # Pins.
    "metadata.import_manifest",
    "metadata.import_runs",
})

_RELATION = re.compile(r"\b(raw|reporting|metadata|main|runtime)\s*\.\s*\"?([a-z_0-9]+)\"?", re.IGNORECASE)
_FORBIDDEN = re.compile(r"\b(read_csv|read_parquet|read_json|attach|copy|install|load|pragma|export|import|create|insert|update|delete|drop|alter|getenv)\b",
                        re.IGNORECASE)


class AccessRefused(PermissionError):
    """A query named a relation or operation outside the allowlist."""


def check_sql(sql: str) -> None:
    """Refuse any statement that is not a plain read over allowlisted relations."""
    if _FORBIDDEN.search(sql):
        raise AccessRefused(f"Operation not allowed: {_FORBIDDEN.search(sql).group(0)}")
    named = {f"{s.lower()}.{t.lower()}" for s, t in _RELATION.findall(sql)}
    if not named:
        raise AccessRefused("Query names no governed relation")
    outside = named - ALLOWED_RELATIONS
    if outside:
        raise AccessRefused(f"Relation not on the allowlist: {sorted(outside)}")


class GovernedDB:
    """One read-only connection; every query passes the allowlist first."""

    def __init__(self, db_path: Path | str | None = None):
        path = Path(db_path or os.environ.get("PHARMAGENTICS_DB") or DEFAULT_DB_PATH).resolve()
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Build it first: python src/pharmagentics/data/load_duckdb.py")
        self.path = path
        self._con = duckdb.connect(str(path), read_only=True)
        self._lock = threading.Lock()

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        check_sql(sql)
        with self._lock:
            cur = self._con.cursor()
            try:
                cur.execute(sql, params or [])
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
            finally:
                cur.close()

    def close(self) -> None:
        self._con.close()
