"""The exact value behind each golden fact, from the fact's own read-only SQL (core-011 FR-016).

A golden file writes a fact rounded (22.5); the data holds 22.45. Scoring against the written figure rounds twice
and fails a brief that prints the true value correctly (22%). Scorers compare against the exact value instead.
"""
from __future__ import annotations

from functools import lru_cache

import duckdb

from .paths import DATABASE


@lru_cache(maxsize=None)
def exact_value(sql: str) -> float | None:
    """The fact's value as the data holds it, or None when the database or the query is not available
    (the scorer then falls back to the written figure)."""
    if not DATABASE.exists():
        return None
    try:
        with duckdb.connect(str(DATABASE), read_only=True) as con:
            row = con.execute(sql).fetchone()
    except duckdb.Error:
        return None
    value = row[0] if row else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
