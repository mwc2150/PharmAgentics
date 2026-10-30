"""Version pins recorded on every run (Briefing B-III)."""
from __future__ import annotations

import hashlib
import subprocess

import duckdb

from .paths import DATABASE, REPO_ROOT


def data_fingerprint() -> str:
    """Same algorithm as pharmagentics.tools.registry.data_version, so evidence can be checked against it."""
    try:
        with duckdb.connect(str(DATABASE), read_only=True) as con:
            rows = con.execute(
                "select table_name, sha256 from metadata.import_manifest where load_id = "
                "(select load_id from metadata.import_runs order by completed_at desc limit 1) order by 1"
            ).fetchall()
    except duckdb.Error:
        return "unavailable"
    return hashlib.sha256(repr(rows).encode()).hexdigest()[:12]


def code_version() -> str:
    def git(*args):
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True).stdout.strip()

    sha = git("rev-parse", "--short", "HEAD") or "unknown"
    return sha + ("+dirty" if git("status", "--porcelain") else "")
