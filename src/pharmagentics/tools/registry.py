"""Governed read-only access to the DuckDB release, with evidence items and claim tokens.

Rules (constitution Principle I; Briefing B-III, B-IV):
- Rx metrics only through the reporting views; no raw.rx_weekly.
- Context only from an allowlist of agent-visible tables. Read-only. SELECT only.
- Every number in an output is a claim token `{cN}` that code fills from one evidence query.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from contextlib import contextmanager
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb

from ..tracing import finish, span

DEFAULT_DB = Path(__file__).resolve().parents[3] / "local" / "pharmagentics.duckdb"

ALLOWED = {
    "reporting.v_reportable_rx", "reporting.v_weekly_rx_kpis", "reporting.v_feed_health",
    "reporting.v_rx_projection",  # projected national (brief-003 FR-022): levels only, never drivers
    "raw.calendar", "raw.dim_plan", "raw.dim_product", "raw.dim_territory", "raw.dim_specialty",
    "raw.access_status_monthly", "raw.inventory_weekly", "raw.promo_activity", "raw.market_basket",
    "raw.market_share_weekly", "raw.restatement_log", "raw.forecast_vs_actual_weekly",
    "metadata.import_manifest", "metadata.import_runs",
}

def _half_up(value: float, decimals: int, percent: bool = False) -> str:
    """Round half up, the convention the Evaluation Pack and the harness use (Python's round() goes to even)."""
    d = Decimal(str(abs(value) if percent else value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    return f"{d:,.{decimals}f}" + ("%" if percent else "")


FORMATS = {
    "int": lambda v: _half_up(v, 0),
    "pct1": lambda v: _half_up(v, 1, percent=True),
    "dec2": lambda v: _half_up(v, 2),
    "dec3": lambda v: _half_up(v, 3),
}


class Refused(Exception):
    """A query the governance rules do not allow."""


_parser = threading.local()  # one in-memory DuckDB per thread, used only to parse queries


def _tree(body: str) -> dict:
    """DuckDB's own parse of a query, so quoting, spacing and comments cannot hide a relation from the check."""
    con = getattr(_parser, "con", None)
    if con is None:
        con = _parser.con = duckdb.connect(":memory:", config={"enable_external_access": False})
    return json.loads(con.execute("select json_serialize_sql(?)", [body]).fetchone()[0])


def _references(node, tables: list[tuple[str, str]], functions: list[str], ctes: set[str]) -> None:
    if isinstance(node, dict):
        kind = node.get("type")
        if kind == "BASE_TABLE":
            tables.append(((node.get("catalog_name") or "") + "|" + (node.get("schema_name") or ""), node.get("table_name") or ""))
        elif kind == "TABLE_FUNCTION":
            functions.append(((node.get("function") or {}).get("function_name")) or "a table function")
        for entry in (node.get("cte_map") or {}).get("map") or []:
            ctes.add(str(entry.get("key", "")).lower())
        for value in node.values():
            _references(value, tables, functions, ctes)
    elif isinstance(node, list):
        for value in node:
            _references(value, tables, functions, ctes)


def check_sql(sql: str) -> None:
    body = sql.strip().rstrip(";").strip()
    if not re.match(r"(?is)^(select|with)\b", body) or ";" in body:
        raise Refused("only a single SELECT is allowed")
    tree = _tree(body)
    if tree.get("error") or len(tree.get("statements") or []) != 1:
        raise Refused("only a single SELECT is allowed" if not tree.get("error")
                      else f"the query does not parse: {str(tree.get('error_message', ''))[:120]}")
    tables, functions, ctes = [], [], set()
    _references(tree, tables, functions, ctes)
    if functions:  # read_csv, glob, duckdb_tables() and the like reach past the governed views
        raise Refused(f"table functions are not allowed: {', '.join(sorted(set(functions)))}")
    relations, refused = set(), set()
    for where, table in tables:
        catalog, schema = where.split("|")
        if not catalog and not schema and table.lower() in ctes:
            continue  # a name the query's own WITH clause defines
        name = f"{schema}.{table}".lower()
        (relations if not catalog and name in ALLOWED else refused).add(name if schema else table.lower())
    if refused:
        raise Refused(f"relation not allowed: {', '.join(sorted(refused))}")
    if not relations:
        raise Refused("a query must read a governed relation")


def data_version(con) -> str:
    try:
        rows = con.execute(
            "select table_name, sha256 from metadata.import_manifest where load_id = "
            "(select load_id from metadata.import_runs order by completed_at desc limit 1) order by 1").fetchall()
    except duckdb.Error:
        return "unavailable"
    return hashlib.sha256(repr(rows).encode()).hexdigest()[:12]


SPLIT_GRAINS = ("plan", "specialty", "channel")


def claim_labels(base: dict, params: dict) -> dict:
    """The labels one claim carries: the run's definition fields, plus the claim's own grain (national, territory, plan,
    channel or specialty) and, when it is one cut of a split or one plan, that cut (`plan:<id>`, `channel:<name>`)."""
    by, cut = params.get("by"), params.get("cut")
    out = dict(base)
    if by in SPLIT_GRAINS and cut is not None:
        out.update(grain=by, cut=f"{by}:{cut}")
    elif params.get("plan"):
        out.update(grain="plan", cut=f"plan:{params['plan']}")
    elif params.get("territory") and params["territory"] != "NATIONAL":
        out["grain"] = "territory"
    else:
        out["grain"] = "national"
    return out


class Registry:
    """One per run: pins the data version and collects evidence items and claims."""

    def __init__(self, db: Path | str = DEFAULT_DB):
        # Plain read-only: DuckDB refuses a second connection to one file with a different config, and the eval scorers
        # open the same file in this process. check_sql refuses table functions (read_csv and the like) instead.
        self.con = duckdb.connect(str(db), read_only=True)
        self.data_version = data_version(self.con)
        self.evidence: list[dict] = []
        self.claims: list[dict] = []
        self._by_query: dict[tuple, str] = {}
        self.labels: dict = {}  # the brief definition every claim is made under (brief-010 FR-000c); set by stages.resolve

    def close(self) -> None:
        self.con.close()

    @contextmanager
    def under(self, **labels):
        """Claims made inside the block record these definition values instead of the primary ones (an extra value's figure)."""
        old, self.labels = self.labels, {**self.labels, **labels}
        try:
            yield
        finally:
            self.labels = old

    def rows(self, sql: str) -> list[tuple]:
        """Internal screening query: governed, not recorded as evidence."""
        check_sql(sql)
        return self.con.execute(sql).fetchall()

    def scalar(self, sql: str):
        check_sql(sql)
        row = self.con.execute(sql).fetchone()
        return None if row is None else row[0]

    def _evidence(self, tool: str, sql: str, result, params: dict) -> str:
        key = (tool, sql)
        if key not in self._by_query:
            eid = f"e{len(self.evidence) + 1}"
            self.evidence.append({"id": eid, "tool": tool, "params": params, "query": sql.strip(),
                                  "result": result if isinstance(result, (int, float, str)) or result is None else str(result),
                                  "data_version": self.data_version})
            self._by_query[key] = eid
        return self._by_query[key]

    def claim(self, tool: str, sql: str, fmt: str = "int", **params) -> str:
        """Run `sql` (one value), record the evidence item and return the token `{cN}` for the narrative."""
        with span(tool, "TOOL", inputs={"query": sql.strip(), **params}, data_version=self.data_version) as sp:
            value = self.scalar(sql)
            if value is None:
                value = 0
            eid = self._evidence(tool, sql, float(value), params)
            self.claims.append({"value": FORMATS[fmt](float(value)), "evidence_id": eid, "labels": claim_labels(self.labels, params)})
            finish(sp, {"value": self.claims[-1]["value"], "evidence_id": eid})
        return "{c%d}" % len(self.claims)

    def table(self, tool: str, sql: str, **params) -> tuple[list[tuple], str]:
        """A governed multi-row query, recorded as one evidence item (its result is the row count)."""
        rows = self.rows(sql)
        return rows, self._evidence(tool, sql, f"{len(rows)} rows", params)

    def fact(self, tool: str, sql: str, **params):
        """A non-numeric or internal value that the narrative states in words; recorded as evidence."""
        value = self.scalar(sql)
        self._evidence(tool, sql, value, params)
        return value

    def render(self, text: str) -> str:
        return re.sub(r"\{c(\d+)\}", lambda m: self.claims[int(m.group(1)) - 1]["value"], text)

    def render_cited(self, text: str) -> tuple[str, list[dict]]:
        """`render`, plus where each claim value sits in the rendered text (inline citations in the UI)."""
        return cite(text, self.claims)


def cite(template: str, claims: list[dict], index: dict[int, int] | None = None) -> tuple[str, list[dict]]:
    """Fill `{cN}` tokens and return the text with spans `{start, end, claim}`; `claim` indexes `claims`, or
    `index` maps token numbers to positions in another claim list. Same text as `Registry.render`."""
    out, spans, pos = [], [], 0
    for m in re.finditer(r"\{c(\d+)\}", template):
        n = int(m.group(1))
        out.append(template[pos:m.start()])
        start = sum(len(s) for s in out)
        if 0 < n <= len(claims):
            value = claims[n - 1]["value"]
            out.append(value)
            spans.append({"start": start, "end": start + len(value), "claim": index[n] if index else n - 1})
        else:
            out.append(m.group(0))
        pos = m.end()
    out.append(template[pos:])
    return "".join(out), spans



def digits_outside_tokens(template: str) -> list[str]:
    """Verifier rule (FR-008): a digit may appear only inside a claim token or in an ISO date."""
    stripped = re.sub(r"\{c\d+\}", " ", template)
    stripped = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", stripped)
    # Identifiers are not measurements: a name that starts with a letter (plan SYN_X_1, BXA) and a hex hash of at
    # least eight characters (a data version such as 06bcba77fbe1). A word that starts with a digit is a number
    # however it ends ("12k", "3x", "300TRx", "2nd"), so it stays in and is refused.
    stripped = re.sub(r"(?<![\w.,])[A-Za-z_]\w*", " ", stripped)
    stripped = re.sub(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{8,}\b", " ", stripped)
    return re.findall(r"\S*\d\S*", stripped)
