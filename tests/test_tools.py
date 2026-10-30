"""Shared tools: governed access, rounding, the verifier rule and the question parser."""
import pytest

from pharmagentics.tools import DEFAULT_DB, Registry
from pharmagentics.tools.registry import Refused, check_sql, digits_outside_tokens, FORMATS
from pharmagentics.tools.window import parse

needs_db = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")


@pytest.mark.parametrize("sql", [
    "select sum(trx) from raw.rx_weekly",  # Rx metrics only through the reporting views
    "select 1",  # a query must read a governed relation
    "delete from raw.calendar",
    "select 1 from raw.calendar; select 2 from raw.calendar",
    "select * from metadata.secrets",
])
def test_ungoverned_queries_are_refused(sql):
    with pytest.raises(Refused):
        check_sql(sql)


def test_governed_queries_pass():
    check_sql("select sum(trx) from reporting.v_reportable_rx where product_id = 'BXA'")
    check_sql("with a as (select * from raw.calendar) select count(*) from a, raw.dim_territory")


def test_rounding_is_half_up_like_the_pack():
    assert FORMATS["int"](56.5) == "57" and FORMATS["int"](3860.4) == "3,860"
    assert FORMATS["pct1"](22.45) == "22.5%" and FORMATS["pct1"](-18.44) == "18.4%"
    assert FORMATS["dec3"](0.6559) == "0.656"


def test_verifier_allows_tokens_dates_and_ids_only():
    assert digits_outside_tokens("BXA TRx was {c1} in the week of 2026-04-06 on data 06bcba77fbe1 (plan SYN_X_1).") == []
    assert digits_outside_tokens("BXA TRx was 3,860 this week.") == ["3,860"]
    assert digits_outside_tokens("Normal is near 1.00.")


@pytest.mark.parametrize("question, weeks, territory", [
    ("Week of 2026-05-04: Is the data complete?", ["2026-05-04"], None),
    ("Weeks of 2026-06-01 to 2026-06-29, Pacific: Why?", ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"], "PACIFIC"),
    ("Weeks of 2025-12-22 and 2025-12-29: Does it matter?", ["2025-12-22", "2025-12-29"], None),
    ("Week of 2026-08-24, NATIONAL: What is the miss?", ["2026-08-24"], "NATIONAL"),
    ("Weeks of 2026-08-31 to 2026-09-28, South Central: How confident?", ["2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28"], "SOUTH_CENTRAL"),
    ("Is this freeing my team's time?", ["2026-10-05"], None),
])
def test_parse(question, weeks, territory):
    ask = parse(question, "2024-10-14", "2026-10-05")
    assert ask["weeks"] == weeks and ask["territory"] == territory
    assert (ask["note"] is not None) == (question.startswith("Is this"))


def test_month_span_resolves_to_mondays():
    ask = parse("Mar to Sep 2026: What are the drivers?", "2024-10-14", "2026-10-05")
    assert ask["weeks"][0] == "2026-03-02" and ask["weeks"][-1] == "2026-09-28"


def test_a_date_outside_the_release_runs_nothing():
    assert parse("Week of 2019-01-07: x", "2024-10-14", "2026-10-05")["weeks"] == []


@needs_db
def test_claims_carry_evidence_pinned_to_the_data_version():
    reg = Registry()
    try:
        token = reg.claim("get_metric", "select count(*) from raw.dim_territory", "int")
        assert reg.render(f"Territories: {token}") == "Territories: 8"
        assert reg.evidence[0]["data_version"] == reg.data_version != "unavailable"
        assert reg.claims[0]["evidence_id"] == reg.evidence[0]["id"]
    finally:
        reg.close()
