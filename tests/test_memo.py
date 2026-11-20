"""brief-003 slice 1: the memo outline (User Story 2, FR-004, FR-020, FR-021), restatements and next checks in
the memo (User Story 4), and the leadership cut (FR-026). Runs the real scripted engine; no model."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api.views import executive_summary  # noqa: E402
from pharmagentics.tools import DEFAULT_DB  # noqa: E402
from pharmagentics.tools.memo import HEADINGS, MemoParts, StoryBlock, compose  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

needs_db = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")
ROUTINE, WITHHELD, EVENTFUL, RESTATED = "2025-04-21", "2026-05-04", "2026-08-24", "2026-07-13"


def brief(week: str, territory: str | None = None) -> dict:
    from briefing_baseline import answer

    return answer(f"Week of {week}" + (f" in {territory}" if territory else "") + ": Generate the weekly brand-performance briefing.")


def section(text: str, title: str) -> list[str]:
    lines, out, inside = text.splitlines(), [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:] == title
            continue
        if inside:
            out.append(line)
    return out


def _parts(**kw) -> MemoParts:
    base = dict(title=["Brief."], bottom_line=["National {c1}."], numbers=["Table {c2}."], limits=[],
                next_checks=[], appendix=["Method."])
    return MemoParts(**{**base, **kw})


def test_composition_is_pure_and_keeps_the_outline():
    parts = _parts(stories=[StoryBlock("territory:PACIFIC", "Pacific", ["Story one: Pacific {c3}.", "Confidence: High."], "Supply fell.")],
                   story_notes=["Considered and dropped: {c4} territories moved within their normal range."], answer="It fell.")
    first, second = compose(parts), compose(parts)
    assert first == second
    template, sections = first
    assert [x for x in template.splitlines() if x.startswith("## ")] == [f"## {t}" for _, t in HEADINGS]
    assert [s["number"] for s in sections] == ["1", "2", "3", "3.1", "4", "5", "6"]
    lines = template.splitlines()
    assert lines[lines.index("Story one: Pacific {c3}.") + 1] == "Supply fell."  # the story's prose sits under its head
    assert section(template, "What the data can't tell us") == ["Nothing in this period limits the figures above."]
    assert section(template, "Next checks") == ["No check is open."]


@needs_db
@pytest.mark.parametrize("week", [ROUTINE, WITHHELD, EVENTFUL])
def test_every_brief_is_the_six_section_memo(week):
    env = brief(week)
    text = env["answer"]
    assert [x for x in text.splitlines() if x.startswith("## ")] == [f"## {t}" for _, t in HEADINGS]
    assert not re.search(r"\{c\d+\}", text)
    assert [s["number"] for s in env["sections"]][:3] == ["1", "2", "3"] and env["sections"][-1]["number"] == "6"
    for s in env["sections"]:  # every claim a section cites is one of the envelope's claims
        assert all(0 <= i < len(env["claims"]) for i in s["claims"])


@needs_db
@pytest.mark.parametrize("week", [ROUTINE, WITHHELD, EVENTFUL, RESTATED])
def test_no_digit_outside_a_claim(week):
    from briefing_baseline.pipeline import Registry, _brief  # the template before rendering

    reg = Registry()
    try:
        captured = {}
        import pharmagentics.tools.memo as memo

        real = memo.compose
        memo.compose = lambda parts: captured.setdefault("t", real(parts))
        try:
            _brief(reg, f"Week of {week}: Generate the weekly brand-performance briefing.")
        finally:
            memo.compose = real
        assert digits_outside_tokens(captured["t"][0]) == []
    finally:
        reg.close()


@needs_db
def test_bottom_line_order_on_the_withheld_week():
    bottom = section(brief(WITHHELD)["answer"], "Bottom line")
    assert bottom[0].startswith("Data warning: New England's feed for 2026-05-04 is incomplete")
    assert bottom[1] == "Projected national BXA TRx is 4,491 for the week of 2026-05-04."
    assert bottom[2] == ("Like for like on 6 of 8 territories, BXA TRx is down 5.2% against the four weeks before "
                         "(2026-04-06 to 2026-04-27).")  # brief-007 FR-004: the comparison weeks are named
    assert bottom[3].startswith("BXA held ") and bottom[3].endswith("of the four-brand market basket.")
    assert bottom[4] == "Least sure: New England's TRx of 407 is an assumption, projected from panel coverage of 0.656."


@needs_db
@pytest.mark.parametrize("week, territory", [(WITHHELD, "New England"), ("2026-07-06", "Great Lakes"), ("2026-04-06", "Mid-Atlantic")])
def test_every_projected_or_estimated_level_is_flagged_as_an_assumption(week, territory):
    """FR-022 (Michael, 2026-11-20): a level the feed did not deliver is always called an assumption."""
    text = brief(week)["answer"]
    row = next(x for x in section(text, "The numbers") if x.startswith(f"- {territory}:"))
    assert "an assumption" in row
    assert "an assumption" in section(text, "Bottom line")[0]  # the data warning
    assert any(x.startswith("Assumption:") for x in section(text, "What the data can't tell us"))


@needs_db
def test_least_sure_falls_to_the_lowest_confidence_story_then_the_smallest_change():
    restated = section(brief(RESTATED)["answer"], "Bottom line")
    assert restated[-1] == "Least sure: the Pacific change (up 45.3%); its confidence, Low, is the lowest of this brief's stories."
    routine = section(brief(ROUTINE)["answer"], "Bottom line")
    assert routine[-1].startswith("Least sure: the week-over-week change")
    numbers = section(brief(ROUTINE)["answer"], "The numbers")
    rows = [x for x in numbers if x.startswith("- ") and "on the week before" not in x]  # the level table only
    assert len(rows) == 8 and not any("(projected" in x or "(estimated" in x for x in rows)  # nothing marked
    changes = [x for x in numbers if x.startswith("- ") and "on the week before" in x]  # brief-007 FR-007
    assert len(changes) == 8  # one change line per territory


@needs_db
def test_restatement_reaches_the_numbers_and_the_bottom_line():
    text = brief(RESTATED)["answer"]
    assert "Data note: an earlier week was restated." in section(text, "Bottom line")[0]
    assert any(x.startswith("Restated: Mid-Atlantic BXA TRx for the week of 2026-04-06 was 692 when first reported and is now 742")
               for x in section(text, "The numbers"))


@needs_db
def test_next_checks_name_an_owner_and_a_decision():
    checks = section(brief(RESTATED)["answer"], "Next checks")
    assert checks[0].startswith("- Pacific: split by plan and specialty") and "Owner: sales leadership." in checks[0]
    assert checks[-1].startswith("- Metacora:") and "Owner: marketing and sales." in checks[-1]
    assert all("Unlocks: " in x for x in checks)
    assert not any("Next:" in x for x in section(brief(RESTATED)["answer"], "What changed and why"))


@needs_db
def test_leaders_get_bottom_line_numbers_stories_without_checks_and_next_checks():
    text = brief(RESTATED)["answer"]
    summary = executive_summary(text)
    heads = [x for x in summary.splitlines() if x.startswith("## ")]
    assert heads == ["## Bottom line", "## The numbers", "## What changed and why", "## Next checks"]
    assert "Checked, in this order:" not in summary and "Considered and dropped" not in summary
    assert "Data version" not in summary and "Data health:" not in summary
    assert "Restated: Mid-Atlantic" in summary


def test_a_brief_from_before_the_memo_is_cut_as_before():
    old = "Brief.\nKPIs: x.\nStory one: P.\nChecked, in this order:\n- Supply: supported.\nConfidence: High.\nConsidered and dropped: y."
    assert executive_summary(old) == "Brief.\nKPIs: x.\nStory one: P.\nConfidence: High."


# --- brief-007 slice A: windows named, per-territory changes, feed figures, Assumptions block ---------------

SOUTHEAST_GAP = "Weeks of 2026-08-03 to 2026-08-31, Southeast: What should I do, and who should I loop in?"


@needs_db
def test_a_multi_week_window_compares_with_the_four_weeks_before():
    """FR-001, SC-005: the P3-Q5 window is compared with 2026-07-06 to 2026-07-27, so Southeast's baseline is 639."""
    from briefing_baseline import answer

    text = answer(SOUTHEAST_GAP)["answer"]
    assert "Southeast. BXA TRx averaged 481 a week against 639 before (down 24.8%)" in text
    assert "against the four weeks before (2026-07-06 to 2026-07-27)." in section(text, "Bottom line")[1]


@needs_db
@pytest.mark.parametrize("brand_id", ["BXA", "BXC"])
def test_screening_uses_common_reportable_weeks_in_the_longer_comparison(brand_id):
    from pharmagentics.tools import queries, stages
    from pharmagentics.tools.registry import Registry

    reg = Registry()
    try:
        p = stages.resolve(reg, "What changed from 2026-06-08 to 2026-07-13?", brand_id=brand_id)
        details = {}
        stages.screen(reg, p, details)

        # New England is withheld on May 4, so every territory's screening comparison drops that week.
        expected_weeks = ["2026-04-27", *p.baseline]
        for territory in ("NEW_ENGLAND", "PACIFIC"):
            actual = queries.mean_weekly(p.weeks, terrs=[territory], product=brand_id)
            baseline = queries.mean_weekly(expected_weeks, terrs=[territory], product=brand_id)
            expected = reg.scalar(queries.pct_change(actual, baseline)) / 100
            assert details[territory]["change"] == pytest.approx(expected)
    finally:
        reg.close()


@needs_db
def test_scope_line_and_assumptions_name_the_comparison_weeks():
    """FR-004, FR-012: leaders keep the scope line; the Assumptions block closes the Appendix."""
    text = brief(WITHHELD)["answer"]
    numbers = section(text, "The numbers")
    assert numbers[0] == ("Scope: week of 2026-05-04, compared with the four weeks before (2026-04-06 to 2026-04-27). "
                          "Levels marked projected or estimated are assumptions.")
    appendix = section(text, "Appendix")
    i = appendix.index("Assumptions:")
    assert appendix[i + 1].startswith("- Comparison weeks: the four weeks before (2026-04-06 to 2026-04-27).")
    assert any(x.startswith("- Not observed: New England is projected or estimated") for x in appendix[i:])
    assert not digits_outside_tokens("\n".join(appendix[i:]).replace("2026-04-06", "").replace("2026-04-27", ""))


@needs_db
def test_territory_changes_match_the_golden_swings():
    """FR-007 (P1-Q3): each territory's week-over-week change, with its direction."""
    numbers = section(brief(ROUTINE)["answer"], "The numbers")
    assert "- Pacific: up 24.8% on the week before; up 8.4% on the comparison weeks." in numbers
    assert "- Southeast: down 10.8% on the week before; down 16.0% on the comparison weeks." in numbers


@needs_db
def test_feed_figures_carry_the_floor_target_and_comparison_range():
    """FR-009 (P1-Q2): coverage against the gate floor, lateness against its target, and the comparison range."""
    limits = section(brief(WITHHELD)["answer"], "What the data can't tell us")
    joined = "\n".join(limits)
    assert "panel coverage 0.656 against a 0.98 floor, 10.29 days after week end against a target of 7 days" in joined
    assert "New England's observed BXA TRx ranged from 397 to 422 a week in the comparison weeks" in joined
    focus = section(brief(WITHHELD, "New England")["answer"], "What the data can't tell us")
    assert any(x.startswith("Feed for New England in these weeks: 84 rows received against 128 expected") for x in focus)


@needs_db
def test_bxc_memo_uses_the_selected_brand_for_withheld_cut_evidence():
    from briefing_baseline import answer

    result = answer(f"Week of {WITHHELD} in New England: What changed?", brand_id="BXC")
    assert "New England's observed BXC TRx ranged from" in result["answer"]
    assert "Product: BXC (Lipidara), synthetic data." in result["answer"]
    assert any("product_id = 'BXC'" in e["query"] and "select min(s)" in e["query"] for e in result["evidence"])
    assert not any("product_id = 'BXA'" in e["query"] for e in result["evidence"])
