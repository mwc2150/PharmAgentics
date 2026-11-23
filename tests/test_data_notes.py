"""brief-010 packet X: data notes (FR-010, FR-011). Runs the real scripted engine on P2-Q1, P2-Q5 and P3-Q6; no model.

A restatement is a fact about the data record, not the business: its card covers its own measure
(`restated_figure`), so it never counts as the territory's TRx story. A national data-artifact card says when the
change over the reportable territories differs materially from the like-for-like change because a territory dropped
out of a period."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api.views import leadership_sections  # noqa: E402
from pharmagentics.tools import DEFAULT_DB, Registry, memo, stages  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build local/pharmagentics.duckdb first")

ROUTINE = "Week of 2025-04-21: Generate the weekly brand-performance briefing."


def golden(story: str):
    from eval.harness.cases import load_cases

    return next(c for c in load_cases("briefing") if c.story == story)


def brief_for(story: str) -> tuple[dict, dict]:
    from briefing_baseline import answer

    case = golden(story)
    return answer(case.question, definition=case.definition.model_dump(mode="json")), case.expectations()


@pytest.fixture(scope="module")
def briefs() -> dict[str, tuple[dict, dict]]:
    return {story: brief_for(story) for story in ("P2-Q1", "P2-Q5", "P3-Q6")}


def cards(env: dict) -> list[dict]:
    return [s["card"] for s in env["sections"] if s["number"].startswith("3.") and s.get("card")]


def artifact_sections(env: dict) -> list[dict]:
    return [s for s in env["sections"] if s["number"].startswith("3.") and s["title"] == "National data artifact"]


def test_the_case_definition_compares_with_the_previous_week():
    d = golden("P2-Q1").definition
    assert d.primary_comparison.kind == "previous" and d.primary_comparison.weeks == 1


def test_p2_q1_has_the_national_data_artifact_card(briefs):
    env, _ = briefs["P2-Q1"]
    (item,) = artifact_sections(env)
    card = item["card"]
    assert card["territory"] == "NATIONAL" and card["cut"] is None
    assert card["direction"] == "down" and card["directions"] == {"trx": "down"}
    assert card["drivers_supported"] == ["data"] and card["drivers_ruled_out"] == []
    assert card["headline"] == ("National BXA TRx over the reportable territories fell 18.4%, but on the 7 territories that "
                                "report both weeks it fell 3.6%: Mid-Atlantic is withheld.")
    assert {"18.4%", "3.6%", "7"} <= {c["value"] for c in env["claims"]}  # the card's numbers are claims of this run
    assert card["headline_citations"]


def test_p2_q1_has_no_mid_atlantic_trx_card(briefs):
    env, _ = briefs["P2-Q1"]
    mine = [c for c in cards(env) if c["territory"] == "MID_ATLANTIC"]
    assert mine and all(c["directions"] == {"restated_figure": c["direction"]} for c in mine)  # only the data-record note


@pytest.mark.parametrize("story", ["P2-Q1", "P2-Q5", "P3-Q6"])
def test_the_findings_are_met_through_the_scorers_own_counts(briefs, story):
    from eval.harness.scorers import finding_counts

    env, expectations = briefs[story]
    got, possible, notes = finding_counts(env, expectations)
    assert got == possible and possible > 0, notes


def test_the_golden_findings_name_the_restated_figure_measure():
    for story in ("P2-Q5", "P3-Q6"):
        (f,) = [f for f in golden(story).findings if f.id == "mid_atlantic_restated_figure"]
        assert f.measure == "restated_figure"


def test_a_restatement_card_is_a_restated_figure_card_beside_the_card_of_the_old_shape(briefs):
    for story in ("P2-Q5", "P3-Q6"):
        env, _ = briefs[story]
        (item,) = [s for s in env["sections"] if s["number"].startswith("3.") and s["title"].endswith("restatement")]
        assert item["card"]["directions"] == {"restated_figure": "up"} and item["card"]["direction"] == "up"


def test_a_brief_with_no_withheld_territory_has_no_data_artifact_card():
    from briefing_baseline import answer

    env = answer(ROUTINE)
    assert not artifact_sections(env)
    assert "withheld" not in " ".join(c["headline"] for c in cards(env) if c["territory"] == "NATIONAL")


def test_the_card_stands_on_the_house_gap_between_the_two_changes():
    """`stages.MATERIAL_GAP` (8 points): the P2-Q1 gap is 14.8 points (18.4 against 3.6); no facts, no card."""
    reg = Registry()
    try:
        p = stages.resolve(reg, "Week of 2026-04-06: is this change real?",
                           definition={"first_week": "2026-04-06", "last_week": "2026-04-06", "comparison": {"kind": "previous", "weeks": 1}})
        facts: dict = {}
        stages.kpis(reg, p, facts)
        a = facts["data_artifact"]
        assert a["dropped"] == ["Mid-Atlantic"] and a["col"] == "trx"
        assert 100 * stages.MATERIAL_GAP < 18.4 - 3.6
        assert memo.data_artifact_block({}) is None and memo.data_artifact_block({"avg": {}}) is None
    finally:
        reg.close()


def test_the_leader_view_shows_the_card_headline_but_no_sql(briefs):
    env, _ = briefs["P2-Q1"]
    cut = leadership_sections(env["sections"])
    (item,) = [s for s in cut if s["number"].startswith("3.") and s["title"] == "National data artifact"]
    assert item["card"]["headline"].startswith("National BXA TRx over the reportable territories fell")
    assert item["card"]["territory"] == "NATIONAL" and item["card"]["drivers_supported"] == ["data"]
    assert "directions" not in item["card"] and "headline_citations" not in item["card"]
    blob = repr(cut).lower()
    assert "select " not in blob and "reporting." not in blob and "evidence" not in blob
    assert "claims" not in item


def test_the_agent_session_builds_the_same_card():
    from pharmagentics.mcp_server import RunSession

    s = RunSession()
    try:
        s.open_run("Week of 2026-04-06, today's snapshot: is this change real?",
                   definition=golden("P2-Q1").definition.model_dump(mode="json"))
        sections = s.brief_sections()
        (story,) = sections["data_artifact_stories"]
        assert story["card"]["territory"] == "NATIONAL" and story["card"]["directions"] == {"trx": "down"}
        assert not digits_outside_tokens("\n".join(story["lines"] + [story["card"]["headline"]]))
    finally:
        s.close()
