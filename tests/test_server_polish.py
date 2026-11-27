"""UAT review fixes on the server (2026-11-27): readable plan names on triage cards (3.1) and a territory-scoped
brief that opens §1 with that territory's change (3.7). Runs the real scripted engine; no model."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.tools import DEFAULT_DB  # noqa: E402

needs_db = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")
CARD_TEXT = ("title", "what_moved", "decision", "population", "granularity", "time")


def _routine(week: str, territory: str | None = None) -> str:
    return f"Week of {week}" + (f" in {territory}" if territory else "") + ": Generate the weekly brand-performance briefing."


def test_a_plan_card_names_its_plan_the_way_the_prose_does():
    from briefing_baseline import triage

    class Reg:
        def claim(self, tool, sql, fmt, **params):
            return "{c1}"

        def scalar(self, sql):
            return -20.0

    p = SimpleNamespace(weeks=["2026-06-29"], baseline=["2026-06-01"], calendar_note=None, terrs=["SOUTHEAST"], ok=["SOUTHEAST"],
                        brand_id="BXA", focus=None)
    story = {"territory": "SOUTHEAST", "kind": "plan", "plan": "SYN_SOUTHEAST_MEDICARE_PART_D_1", "impact": 1.0}
    card = triage._card(Reg(), SimpleNamespace(p=p), story, 1, "investigate")
    assert card["title"] == "Southeast, Medicare Part D plan one"
    assert card["what_moved"].startswith("Medicare Part D plan one in Southeast: BXA TRx averaged")
    assert card["granularity"] == "Medicare Part D plan one, in Southeast."
    assert card["id"] == "plan:SYN_SOUTHEAST_MEDICARE_PART_D_1"  # the id stays an id
    assert not any("SYN_" in card[k] for k in CARD_TEXT)


@needs_db
@pytest.mark.parametrize("week", ["2025-09-08", "2026-06-29"])  # a continuing card and a plan cut card
def test_no_plan_id_reaches_the_text_of_a_triage_card(week):
    from briefing_baseline import pipeline

    plan = pipeline.triage(_routine(week))
    cards = [c for c in plan["stories"] if c["kind"] in ("continuing", "cut")]
    assert cards
    for card in cards:
        assert not any("SYN_" in card[k] for k in CARD_TEXT), card
    assert {c["granularity"] for c in cards} <= {"Territory Mid-Atlantic, Medicare Part D plan one.", "Medicare Part D plan two, in New England."}


@needs_db
def test_a_territory_brief_opens_with_that_territorys_change_then_national():
    from briefing_baseline import answer

    env = answer(_routine("2026-06-08", "Pacific"))
    lines = env["sections"][0]["text"].splitlines()
    assert lines[0].startswith("Pacific: BXA TRx is down ") and "against the four weeks before (" in lines[0]
    assert lines[1].startswith("Projected national BXA TRx is ")
    pct = lines[0].split(" is down ")[1].split(" against")[0]
    assert pct.endswith("%") and any(c["value"] == pct for c in env["claims"])  # the figure is a claim, filled by code


@needs_db
def test_a_national_brief_has_no_territory_lead():
    from briefing_baseline import answer

    first = answer(_routine("2026-06-08"))["sections"][0]["text"].splitlines()[0]
    assert first.startswith("Projected national BXA TRx is ")
