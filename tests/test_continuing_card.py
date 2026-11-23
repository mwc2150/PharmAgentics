"""brief-010 packet C: continuing cards (FR-012). Runs the real scripted engine on the loaded release; no model.

A territory whose promotion lapse or plan access restriction is still running in the period gets a card measured
against the four weeks before the event, unless it already has a regular story or cut card."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.tools import DEFAULT_DB, Registry, continuing, stages  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build local/pharmagentics.duckdb first")

PLAN = "SYN_MID_ATLANTIC_MEDICARE_PART_D_1"
SOUTHEAST_WEEK = "Week of 2026-08-24: How much do I have to rewrite before this goes to my manager?"


def week(day: str, territory: str | None = None) -> str:
    return f"Week of {day}" + (f" in {territory}" if territory else "") + ": Generate the weekly brand-performance briefing."


def cards(env: dict) -> list[dict]:
    return [s["card"] for s in env["sections"] if s["number"].startswith("3.") and s.get("card")]


def running(env: dict) -> list[dict]:
    return [c for c in cards(env) if c.get("continuing")]


@pytest.fixture(scope="module")
def southeast() -> dict:
    from briefing_baseline import answer

    return answer(SOUTHEAST_WEEK)


def screen(question: str, covered: set[str] = frozenset(), cut_plans: set[str] = frozenset()) -> list[dict]:
    reg = Registry()
    try:
        return continuing.screen(reg, stages.resolve(reg, question), set(covered), set(cut_plans))
    finally:
        reg.close()


# the golden gap: P1-Q6 -------------------------------------------------------------------------------------------

def test_the_week_inside_the_lapse_gets_a_southeast_continuing_card(southeast):
    [card] = running(southeast)
    assert (card["territory"], card["cut"], card["direction"], card["since"]) == ("SOUTHEAST", None, "down", "2026-08-03")
    assert card["drivers_supported"] == ["promotion"] and "access" in card["drivers_ruled_out"]
    assert card["continuing"] is True and card["directions"] == {"trx": "down"}


def test_the_card_says_it_is_measured_against_the_weeks_before_the_lapse(southeast):
    [section] = [s for s in southeast["sections"] if (s.get("card") or {}).get("continuing")]
    assert section["card"]["headline"].startswith("Southeast, continuing since 2026-08-03: TRx fell from ")
    assert "against the four weeks before the rep coverage lapse began" in section["card"]["headline"]
    assert "Southeast (continuing since 2026-08-03)" in section["text"] and "Promotion: supported" in section["text"]


def test_every_number_of_the_card_is_a_claim_from_a_governed_query(southeast):
    [section] = [s for s in southeast["sections"] if (s.get("card") or {}).get("continuing")]
    cited = {c["claim"] for c in section["card"]["headline_citations"]}
    by_id = {e["id"]: e for e in southeast["evidence"]}
    assert len(cited) == 3
    for n in cited:
        claim = southeast["claims"][n]  # a citation names the claim by its position
        assert claim["labels"]["grain"] == "territory"
        assert (claim["labels"]["comparison"], claim["labels"]["comparison_kind"]) == ("2026-07-06 to 2026-07-27", "before_event")
        assert "reporting.v_reportable_rx" in by_id[claim["evidence_id"]]["query"]


def test_the_continuing_card_scores_the_golden_finding(southeast):
    from eval.harness.cases import load_cases
    from eval.harness.scorers import finding_counts

    expected = next(c for c in load_cases("briefing") if c.story == "P1-Q6").expectations()
    got, possible, notes = finding_counts(southeast, expected)
    assert got == possible and not notes, notes


def test_the_card_follows_the_regular_cards_and_precedes_the_competitor_card(southeast):
    order = [(c["territory"], bool(c.get("continuing"))) for c in cards(southeast)]
    assert order.index(("SOUTHEAST", True)) < order.index(("NATIONAL", False))


def test_section_five_has_a_next_check_for_the_continuing_story(southeast):
    assert "Southeast: confirm the promotion finding" in southeast["answer"]


# when there is no card --------------------------------------------------------------------------------------------

def test_a_week_after_the_lapse_ended_gets_none():
    from briefing_baseline import answer

    assert not running(answer(week("2026-09-07")))  # coverage resumed on 2026-09-07


def test_a_week_before_the_lapse_had_run_long_enough_to_count_gets_none():
    assert screen(week("2026-08-10")) == []  # the lapse began 2026-08-03: two weeks old, not yet a lapse
    assert [e["territory"] for e in screen(week("2026-08-17"))] == ["SOUTHEAST"]  # the third week of it counts


def test_a_territory_with_a_regular_story_card_gets_no_duplicate():
    from briefing_baseline import answer

    env = answer(week("2026-08-24", "Southeast"))  # the question names it, so it always has a regular story
    southeast = [c for c in cards(env) if c["territory"] == "SOUTHEAST"]
    assert southeast and not any(c.get("continuing") for c in southeast)  # its regular story (and its plan cut card) only
    assert screen(week("2026-08-24"), covered={"SOUTHEAST"}) == []


def test_a_period_that_starts_with_the_event_is_not_a_continuing_one():
    assert screen("Weeks of 2026-07-27 to 2026-08-17: Generate the weekly brand-performance briefing.") == []  # the lapse begins on its second week, not before it


def test_a_brief_that_leaves_territory_stories_out_has_no_lapse_card():
    from briefing_baseline import answer
    from pharmagentics.tools.definition import Definition

    d = Definition.model_validate({"grain": ["national", "plan"]})
    assert not [c for c in cards(answer(SOUTHEAST_WEEK, definition=d.to_json())) if c.get("continuing") and c["cut"] is None]


# access restrictions, plan level ----------------------------------------------------------------------------------

def test_a_restriction_that_began_before_the_period_gets_a_plan_card_when_nothing_else_has_it():
    [event] = screen(week("2025-09-22"))
    assert (event["kind"], event["territory"], event["plan"], event["start"]) == ("access", "MID_ATLANTIC", PLAN, "2025-08-04")
    assert event["end"] == "2025-10-27"


def test_the_plan_card_names_the_plan_and_supports_access():
    from briefing_baseline import answer

    env = answer(week("2025-09-22"))
    [card] = running(env)
    assert (card["territory"], card["cut"], card["direction"], card["since"]) == ("MID_ATLANTIC", f"plan:{PLAN}", "down", "2025-08-04")
    assert card["drivers_supported"] == ["access"] and "Medicare Part D plan one in Mid-Atlantic, continuing since 2025-08-04" in card["headline"]


def test_a_plan_with_a_cut_card_gets_no_second_card_for_the_same_event():
    assert screen(week("2025-09-22"), cut_plans={PLAN}) == []
    assert screen(week("2025-09-22"), covered={"MID_ATLANTIC"}) == []


def test_the_months_long_restriction_adds_no_card_to_the_golden_mid_atlantic_briefs():
    from briefing_baseline import pipeline
    from eval.harness.cases import load_cases

    for story in ("P1-Q4", "P2-Q2", "P2-Q4", "P4-Q4"):
        case = next(c for c in load_cases("briefing") if c.story == story)
        env = pipeline.answer(case.question, definition=case.definition.model_dump(mode="json"))
        assert not running(env), story


def test_a_restriction_lifted_before_the_period_is_over():
    assert screen(week("2025-11-03")) == []  # relief month 2025-11: the restriction ended the week before


# triage and the agent's manager (FR-007) ---------------------------------------------------------------------------

def test_the_triage_plan_proposes_the_continuing_card_before_the_competitor():
    from briefing_baseline import pipeline

    plan = pipeline.triage(SOUTHEAST_WEEK)
    ids = [c["id"] for c in plan["stories"]]
    assert ids[0] == "continuing:SOUTHEAST" and (len(ids) == 1 or ids[1].startswith("competitor:"))
    card = plan["stories"][0]
    assert (card["kind"], card["territory"], card["proposed"], card["title"]) == ("continuing", "SOUTHEAST", "investigate", "Southeast (continuing)")
    assert "continuing since 2026-08-03" in card["what_moved"] and "began on 2026-08-03" in card["decision"]
    assert plan["state"] == "TRIAGE_REVIEW"


def test_a_decision_may_drop_the_continuing_card_and_the_run_then_has_none():
    from briefing_baseline import pipeline

    plan = pipeline.triage(SOUTHEAST_WEEK)
    kept = pipeline.run_with_plan(SOUTHEAST_WEEK, {"plan_id": plan["plan_id"], "stories": ["continuing:SOUTHEAST"]})
    assert len(running(kept["envelope"])) == 1
    dropped = pipeline.run_with_plan(SOUTHEAST_WEEK, {"plan_id": plan["plan_id"], "stories": []})
    assert not running(dropped["envelope"])


def test_the_manager_may_drop_a_continuing_card_and_gives_it_no_drivers():
    from briefing_agent import plan as planmod
    from briefing_baseline import pipeline

    code = pipeline.triage(SOUTHEAST_WEEK)
    assert "continuing:SOUTHEAST" in planmod.cards_text(code)
    kept = planmod.apply(code, '{"order": ["continuing:SOUTHEAST"], "hypotheses": {"continuing:SOUTHEAST": ["promotion"]}}')
    card = next(c for c in kept["stories"] if c["kind"] == "continuing")
    assert card["manager"]["keep"] and card["manager"]["hypotheses"] == []


def test_the_agent_session_builds_the_same_card_and_assembles_it_before_the_competitor():
    from briefing_agent import write
    from pharmagentics.mcp_server import RunSession
    from pharmagentics.tools import memo

    from briefing_baseline import answer
    scripted = answer(SOUTHEAST_WEEK)
    [theirs] = running(scripted)
    s = RunSession()
    s.open_run(SOUTHEAST_WEEK)
    sections = s.brief_sections()
    close = s.memo_close(competitor=True, running=["SOUTHEAST"])
    [card] = close["continuing_stories"]
    assert card["id"] == "continuing:SOUTHEAST" and card["territory"] == "SOUTHEAST"
    ours = {k: s.reg.render(v) if isinstance(v, str) else v for k, v in close["story_cards"][card["id"]].items()}
    assert {k: v for k, v in ours.items() if k != "headline_citations"} == {k: v for k, v in theirs.items() if k != "headline_citations"}
    stories = write.place_continuing([{"id": "competitor:BXE", "section": "x", "territory": None}], close["continuing_stories"])
    assert [x["id"] for x in stories] == ["continuing:SOUTHEAST", "competitor:BXE"]
    _template, built = write.assemble(sections, close, stories, "", {}, [], s.dropped_line())
    rendered = memo.render_sections(built, s.reg.claims)
    assert any((x.get("card") or {}).get("continuing") for x in rendered)
    assert "Southeast: confirm the promotion finding" in "\n".join(close["next_checks"])
