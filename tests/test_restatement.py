"""brief-010 packet R: restatement detail (FR-004, FR-005, User Story 3). Runs the real scripted engine; no model.

P1-Q1 (the duplicated Great Lakes feed), P2-Q5 and P3-Q6 (the Mid-Atlantic week restated on 2026-07-13) are the
golden cases this serves. A brief reports a restatement when the restated week is inside its period or the
restatement was published inside its period."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api.views import leadership_sections  # noqa: E402
from pharmagentics.tools import DEFAULT_DB, Registry  # noqa: E402
from pharmagentics.tools.memo import MemoParts, StoryBlock, compose  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build local/pharmagentics.duckdb first")

P1_Q1 = "Week of 2026-07-06: Do the numbers tie out to the source tables?"
P2_Q5 = "Week of 2026-04-06, Mid-Atlantic: If someone challenges a claim, can I show the evidence behind it?"
P3_Q6 = "Brief of 2026-07-13: Can I quote these numbers in my leadership meeting?"
NONE = "Week of 2025-04-21: Generate the weekly brand-performance briefing."
ASSUMPTION = "A restatement is reported when the restated week is inside the period or the restatement was published inside it."


def brief(question: str) -> dict:
    from briefing_baseline import answer

    return answer(question)


def section(env: dict, number: str) -> dict:
    return next(s for s in env["sections"] if s["number"] == number)


def restatement_sections(env: dict) -> list[dict]:
    return [s for s in env["sections"] if s["number"].startswith("3.") and s["title"].endswith("restatement")]


def test_the_views_hold_the_restatement_record_and_the_duplicate_tie_out():
    reg = Registry()
    try:
        row = reg.rows("select week_start::varchar, territory_id, product_id, restated_at::varchar, reason, restated_cells, "
                       "trx_signed_off, trx_restated, nbrx_signed_off, nbrx_restated from reporting.v_restatements")
        assert row == [("2026-04-06", "MID_ATLANTIC", "BXA", "2026-07-13", "SYNTHETIC_LATE_CLAIMS_ADJUSTMENT", 32, 692, 742, 97, 98)]
        tie = reg.rows("select week_start::varchar, territory_id, naive_trx, deduplicated_trx from reporting.v_rx_duplicate_tieout "
                       "where product_id = 'BXA'")
        assert tie == [("2026-07-06", "GREAT_LAKES", 670, 624)]
    finally:
        reg.close()


# P1-Q1 -----------------------------------------------------------------------------------------------

def test_the_withheld_duplicate_feed_states_the_naive_sum_the_deduplicated_figure_and_the_overstatement():
    text = brief(P1_Q1)["answer"]
    line = next(x for x in text.splitlines() if x.startswith("- Great Lakes, week of 2026-07-06: not reportable"))
    assert "15 duplicate keys" in line
    assert "Raw, before deduplication, Great Lakes BXA TRx sums to 670" in line  # gl_bxa_trx_naive_sum
    assert "counted once it is 624" in line  # gl_bxa_trx_deduplicated
    assert "overstates it by 46 TRx (7.4%)" in line  # gl_overstatement_pct
    assert "Great Lakes BXA TRx was 670" not in text  # the golden case's must-not-say


def test_the_tie_out_is_a_labelled_claim_from_a_governed_view_and_the_cut_stays_withheld():
    env = brief(P1_Q1)
    by_value = {c["value"]: next(e for e in env["evidence"] if e["id"] == c["evidence_id"]) for c in env["claims"]}
    for value in ("670", "624", "46"):
        assert "reporting.v_rx_duplicate_tieout" in by_value[value]["query"], value
    assert "before deduplication" in by_value["670"]["params"]["scope"]
    rows = section(env, "2")["territory_table"]["rows"]
    assert any(r["cells"][0] == "Great Lakes" and r["basis"] == "estimated" for r in rows)  # never folded into a metric
    assert not restatement_sections(env)  # the restatement was published after this week


def test_no_duplicate_tie_out_when_the_gate_withholds_for_another_reason():
    env = brief("Week of 2026-05-04: Generate the weekly brand-performance briefing.")
    assert "Raw, before deduplication" not in env["answer"]


# P2-Q5 and P3-Q6 -------------------------------------------------------------------------------------

@pytest.mark.parametrize("question", [P2_Q5, P3_Q6])
def test_the_numbers_state_the_signed_off_and_restated_figures_and_the_change(question):
    env = brief(question)
    line = next(x for x in section(env, "2")["text"].splitlines() if x.startswith("Restated:"))
    assert line.startswith("Restated: Mid-Atlantic BXA TRx for the week of 2026-04-06 was 692 when first reported and is now 742, "
                           "up 50 TRx (7.2%).")
    assert "restated 2026-07-13; reason: synthetic late claims adjustment" in line


@pytest.mark.parametrize("question", [P2_Q5, P3_Q6])
def test_one_restatement_card_for_mid_atlantic_with_data_supported(question):
    env = brief(question)
    (item,) = restatement_sections(env)
    card = item["card"]
    assert card["territory"] == "MID_ATLANTIC" and card["cut"] is None
    assert card["direction"] == "up" and card["drivers_supported"] == ["data"] and card["drivers_ruled_out"] == []
    assert card["headline"] == "Mid-Atlantic TRx for the week of 2026-04-06 was restated from 692 to 742 (up 7.2%)."
    assert {"692", "742", "7.2%"} <= {c["value"] for c in env["claims"]}  # the card's numbers are claims of this run
    assert card["headline_citations"]


def test_the_week_in_the_period_and_the_date_in_the_period_each_bring_the_restatement():
    for question in (P2_Q5, P3_Q6):  # week 2026-04-06 in the period, or the 2026-07-13 restated date in it
        assert ASSUMPTION in section(brief(question), "6")["text"]


def test_a_period_that_ends_before_the_restated_date_does_not_report_it():
    env = brief(P1_Q1)  # the week of 2026-07-06 ends 2026-07-12; the restatement came on 2026-07-13
    assert "Restated:" not in env["answer"] and ASSUMPTION not in env["answer"]


def test_a_brief_with_no_restatement_has_no_card_and_no_assumption():
    env = brief(NONE)
    assert not restatement_sections(env)
    assert "restate" not in env["answer"].lower()


def test_the_leader_view_shows_the_card_but_no_sql():
    cut = leadership_sections(brief(P3_Q6)["sections"])
    (item,) = [s for s in cut if s["number"].startswith("3.") and s["title"].endswith("restatement")]
    assert item["card"]["direction"] == "up" and item["card"]["drivers_supported"] == ["data"]
    blob = repr(cut).lower()
    assert "select " not in blob and "reporting." not in blob and "evidence" not in blob
    assert "claims" not in item and "headline_citations" not in item["card"]


def test_the_agent_session_builds_the_same_card():
    from pharmagentics.mcp_server import RunSession

    s = RunSession()
    try:
        s.open_run(P3_Q6)
        sections = s.brief_sections()
        (story,) = sections["restatement_stories"]
        assert story["card"]["territory"] == "MID_ATLANTIC" and story["card"]["drivers_supported"] == ["data"]
        assert not digits_outside_tokens("\n".join(story["lines"] + [story["card"]["headline"]]))
        assert any(x.startswith("Restated:") for x in sections["numbers"])
        assert ASSUMPTION in "\n".join(sections["appendix"])
        _, rendered = compose(MemoParts(title=["T."], bottom_line=["B."], numbers=sections["numbers"], limits=[],
                                        next_checks=[], appendix=[], stories=[StoryBlock(**story)]))
        assert any(r["number"] == "3.1" and r["card"]["territory"] == "MID_ATLANTIC" for r in rendered)
    finally:
        s.close()
