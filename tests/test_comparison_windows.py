from decimal import Decimal

import pytest

from pharmagentics.mcp_server import ADMIN_TOOLS, AGENT_TOOLS, RunSession
from pharmagentics.tools import DEFAULT_DB, Registry, followup, queries as q, splits, stages
from pharmagentics.tools.checks import check_competitor
from pharmagentics.tools.window import Comparison, comparison_weeks


def test_validation_does_not_silently_substitute_a_baseline():
    requested = ["2026-06-08"]
    available = {"2026-06-01", "2026-06-08", "2026-06-15"}
    assert comparison_weeks(Comparison(kind="previous", weeks=1), requested, available) == ["2026-06-01"]
    with pytest.raises(ValueError, match="outside the data release"):
        comparison_weeks(Comparison(kind="last_year"), requested, available)
    with pytest.raises(ValueError, match="end before"):
        comparison_weeks(Comparison(kind="custom", start="2026-06-01", end="2026-06-08"), requested, available)
    with pytest.raises(ValueError, match="Monday"):
        Comparison(kind="custom", start="2026-06-02", end="2026-06-08")
    with pytest.raises(ValueError):
        Comparison(kind="previous", weeks=14)


def test_window_is_pinned_in_a_caller_only_mcp_tool():
    assert "open_run" in ADMIN_TOOLS
    assert all("open_run" not in tools for tools in AGENT_TOOLS.values())
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    session = RunSession()
    try:
        choice = Comparison(kind="custom", start="2026-07-06", end="2026-07-27")
        scope = session.open_run("Week of 2026-08-24, Southeast: What changed?", choice)
        assert "2026-07-06 to 2026-07-27" in scope and "analyst's choice" in scope
        assert any("2026-07-27" in line and "analyst's choice" in line
                   for line in session.brief_sections()["appendix"])
    finally:
        session.close()


@pytest.mark.parametrize("by", sorted(splits.SPLITS))
def test_displayed_cuts_reconcile_to_the_territory_change(by):
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    reg = Registry()
    try:
        choice = Comparison(kind="custom", start="2026-07-06", end="2026-07-27")
        p = stages.resolve(reg, "Week of 2026-08-24, Southeast: What changed?", comparison=choice)
        lines = splits.split_change(reg, p, "SOUTHEAST", by)
        total, *cuts = (Decimal(c["value"].replace(",", "")) for c in reg.claims)
        assert total == sum(cuts) == Decimal("-170.00")
        assert any("small cell: noisy" in line for line in lines)
    finally:
        reg.close()


def test_comparison_followup_offers_a_new_brief():
    result = {"territory_id": "SOUTHEAST", "week_start": "2026-08-24",
              "sections": [{"number": "1", "title": "Bottom line"}]}
    turn = followup.answer(result, "Can you compare the same week last year?")
    assert turn["kind"] == "out_of_scope"
    assert turn["offer"]["comparison"] == {"kind": "last_year"}
    assert turn["offer"]["week"] == result["week_start"]


def test_competitor_check_keeps_the_chosen_prelaunch_window():
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    reg = Registry()
    try:
        result = check_competitor(reg, "PACIFIC", ["2026-06-08"], ["2025-06-09"], exact_comparison=True)
        assert result.verdict == "insufficient"
        assert "chosen comparison ends before" in result.text and not reg.claims
    finally:
        reg.close()


def test_multiweek_screen_uses_the_explicit_window():
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    reg = Registry()
    try:
        choice = Comparison(kind="custom", start="2026-07-06", end="2026-07-27")
        p = stages.resolve(reg, "Weeks of 2026-08-03 to 2026-08-31, Southeast: What changed?", comparison=choice)
        details = {}
        stages.screen(reg, p, details)
        recent = reg.scalar(q.mean_weekly(p.weeks, terrs=["SOUTHEAST"]))
        baseline = reg.scalar(q.mean_weekly(p.baseline, terrs=["SOUTHEAST"]))
        assert details["SOUTHEAST"]["change"] == pytest.approx(recent / baseline - 1)
    finally:
        reg.close()


def test_the_confidence_question_is_not_a_promotion_question():
    from pharmagentics.tools.window import parse

    first, latest = "2024-10-14", "2026-10-05"
    asked = parse("How confident is the estimate, and when will we know more?", first, latest, briefing=True)
    assert not asked["promotion"] and asked["weeks"] == [latest]
    assert parse("Where should the next dollar go?", first, latest, briefing=True)["promotion"]


@pytest.mark.parametrize("asked, weeks", [
    ("Why did Southeast change in the week of Aug 24, 2026?", ["2026-08-24"]),
    ("Week of August 26th 2026 in Southeast: How did BXA do?", ["2026-08-24"]),  # a Wednesday reads as its week
    ("24 Aug 2026, Pacific: what moved?", ["2026-08-24"]),
    ("8/24/2026 Southeast: what moved?", ["2026-08-24"]),
    ("Sept. 7, 2026: how did BXA do?", ["2026-09-07"]),
    ("Aug 3, 2026 to Aug 31, 2026 in Southeast: why?", ["2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31"]),
    ("Aug 2026: how did BXA do?", ["2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31"]),
])
def test_the_briefing_reader_takes_the_dates_the_app_prints(asked, weeks):
    """UAT review 2026-11-27, C-6: "week of Aug 24, 2026" fell back to the latest week. The Forecast reading is unchanged."""
    from pharmagentics.tools.window import parse

    first, latest = "2024-10-14", "2026-10-05"
    got = parse(asked, first, latest, briefing=True)
    assert got["weeks"] == weeks and got["note"] is None
    assert parse(asked.replace("Aug 24, 2026", "2026-08-24"), first, latest, briefing=True)["weeks"] == weeks


def test_a_date_that_is_not_a_real_day_is_named_not_ignored():
    from pharmagentics.tools.window import parse

    got = parse("Week of Feb 30, 2026 in Southeast: How did BXA do?", "2024-10-14", "2026-10-05", briefing=True)
    assert got["weeks"] == ["2026-10-05"] and got["note"].startswith("The date in the question is not a real day")


def test_the_forecast_reading_of_written_dates_is_unchanged():
    from pharmagentics.tools.window import parse

    assert parse("Why did Southeast change in the week of Aug 24, 2026?", "2024-10-14", "2026-10-05")["weeks"] == ["2026-10-05"]
