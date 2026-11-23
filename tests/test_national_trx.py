"""brief-010 packet NC: every brief carries one national card that states national BXA TRx direction, the holiday
driver, and the "ruled out nationally" rule (FR-006). Runs the real scripted engine on the data; no model."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.tools import DEFAULT_DB  # noqa: E402
from pharmagentics.tools.checks import Check  # noqa: E402
from pharmagentics.tools.definition import Definition  # noqa: E402
from pharmagentics.tools.lag_checks import national_ruled_out  # noqa: E402
from pharmagentics.tools.memo import competitor_card, national_block  # noqa: E402

needs_db = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")
HOLIDAY = "Weeks of 2025-12-22 and 2025-12-29: Does this matter for the brand, or can I ignore it?"
PRE_LAUNCH = "Week of 2025-04-21: Which changes are big enough to make the brief?"
LAUNCH_WEEK = "Week of 2026-04-27: What changed this week that I need to know about?"


def national(env: dict) -> list[dict]:
    return [s["card"] for s in env["sections"] if s["number"].startswith("3.") and s.get("card") and s["card"]["territory"] == "NATIONAL"]


def brief(question: str, **definition) -> dict:
    from briefing_baseline import answer

    return answer(question, definition=Definition(**definition)) if definition else answer(question)


@needs_db
def test_holiday_weeks_against_the_previous_four_weeks_are_down_with_the_holiday_driver():
    (card,) = national(brief(HOLIDAY, first_week="2025-12-22", last_week="2025-12-29"))
    assert card["directions"] == {"trx": "down"} and card["direction"] == "down"
    assert card["drivers_supported"] == ["holiday"] and "holiday" in card["drivers_checked"]
    assert "competitor" not in card["drivers_supported"] + card["drivers_checked"]  # a calendar week opens no competitor story
    assert card["drivers_ruled_out"] == []  # no story territory was tested in a calendar week


@needs_db
def test_the_same_holiday_weeks_against_last_year_are_up_with_no_holiday_driver():
    (card,) = national(brief(HOLIDAY, first_week="2025-12-22", last_week="2025-12-29", comparison={"kind": "last_year"}))
    assert card["directions"] == {"trx": "up"} and card["direction"] == "up"
    assert card["drivers_supported"] == [] and "holiday" not in card["drivers_checked"]


@needs_db
def test_p3_q1_rules_promotion_out_nationally_and_keeps_the_share_story():
    (card,) = national(brief(LAUNCH_WEEK, first_week="2026-04-27", last_week="2026-04-27", comparison={"kind": "pre_launch"}))  # golden P3-Q1's definition
    assert card["directions"]["bxa_share"] == "down" and card["directions"]["competitor_share"] == "up" and "trx" in card["directions"]
    assert card["direction"] == "down" and card["drivers_supported"] == ["competitor"]
    assert card["drivers_ruled_out"] == ["access", "promotion", "supply"]  # Great Lakes promotion has no story of its own
    assert "holiday" not in card["drivers_checked"]


@needs_db
def test_a_pre_launch_week_has_a_national_card_without_competitor_shares():
    env = brief(PRE_LAUNCH)
    (card,) = national(env)
    assert set(card["directions"]) == {"trx"} and card["direction"] == card["directions"]["trx"]
    assert "competitor" not in card["drivers_supported"] + card["drivers_checked"] + card["drivers_ruled_out"]
    assert card["headline"].startswith("National BXA TRx ") and "Metacora" not in card["headline"]
    assert "{c" not in card["headline"] and card["headline_citations"]  # the KPI strip's own percent, cited
    assert "Metacora holds" not in env["answer"]


@needs_db
def test_a_brief_without_national_grain_has_no_national_card():
    env = brief(LAUNCH_WEEK, grain=["territory", "plan", "channel", "specialty"])
    assert national(env) == []


def test_ruled_out_nationally_unless_a_story_territory_supports_or_cannot_rule_it_out():
    def checks(**v):
        return [Check(d, verdict, "") for d, verdict in v.items()]

    quiet = checks(access="ruled_out", promotion="ruled_out", supply="ruled_out")
    assert national_ruled_out([]) == ["access", "promotion", "supply"]  # no story territory
    assert national_ruled_out([quiet]) == ["access", "promotion", "supply"]
    live = checks(access="ruled_out", promotion="supported", supply="insufficient")
    assert national_ruled_out([quiet, live]) == ["access"]
    assert national_ruled_out([{c.driver: c for c in live}]) == ["access"]  # a {driver: Check} dict reads the same
    assert national_ruled_out([checks(access="ruled_out")]) == ["access"]  # an untested driver is not ruled out


def test_the_national_only_block_keeps_its_headline_and_never_claims_a_competitor():
    p = type("P", (), {"brand_id": "BXA"})()
    facts = {"directions": {"trx": "down"}, "trx_pct": "{c1}", "holiday": True, "ruled_out": ["access"]}
    block = national_block(p, facts)
    card = block.card
    assert card["territory"] == "NATIONAL" and card["direction"] == "down" and card["drivers_supported"] == ["holiday"]
    assert card["headline"].startswith("National BXA TRx fell {c1} on the comparison weeks.")
    assert card["drivers_checked"] == ["holiday", "access"] and card["drivers_ruled_out"] == ["access"]
    assert block.lines == [] and block.detail == [card["headline"]]
    bare = competitor_card(p, {"directions": {"trx": "flat"}})
    assert bare["direction"] == "flat" and bare["headline"] == "National BXA TRx was flat on the comparison weeks."
