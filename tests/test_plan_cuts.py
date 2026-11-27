"""brief-010 packet P: plan cut cards (FR-001, FR-002, FR-007, FR-008, User Story 1). Runs the real scripted engine on
the four golden cases that need a cut (P1-Q4, P2-Q2, P2-Q4, P4-Q4); no model.

A cut card is a plan that moved against its territory or holds an access change, built by code from the plan's own
figures and its territory's checks, beside the territory's card. The golden facts are compared at the precision the
brief prints them (the scorer's own rule)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api.views import leadership_sections  # noqa: E402
from pharmagentics.tools import DEFAULT_DB, Registry, memo, splits, stages  # noqa: E402
from pharmagentics.tools.definition import Definition  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build local/pharmagentics.duckdb first")

PLAN = "SYN_MID_ATLANTIC_MEDICARE_PART_D_1"
CUT = f"plan:{PLAN}"
CASES = ["P1-Q4", "P2-Q2", "P2-Q4", "P4-Q4"]
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
    return {story: brief_for(story) for story in CASES}


def cut_sections(env: dict) -> list[dict]:
    return [s for s in env["sections"] if (s.get("card") or {}).get("cut")]


# User Story 1: the card and its direction, drivers and facts ------------------------------------------------

@pytest.mark.parametrize("story, direction, directions, supported, ruled_out", [
    ("P1-Q4", "down", {"nbrx": "down", "trx": "down"}, ["access"], ["data", "promotion", "supply", "competitor"]),
    ("P2-Q2", "down", {"trx": "down"}, ["access"], ["data", "promotion", "supply", "competitor"]),
    ("P2-Q4", "down", {"trx": "down"}, ["access"], ["data", "promotion", "supply", "competitor"]),
    ("P4-Q4", "up", {"trx": "up"}, ["access"], ["data", "promotion", "supply", "competitor"]),
])
def test_each_target_case_has_a_cut_card_for_the_mid_atlantic_plan(briefs, story, direction, directions, supported, ruled_out):
    env, _ = briefs[story]
    [section] = cut_sections(env)
    card = section["card"]
    assert (card["territory"], card["cut"], card["direction"], card["directions"]) == ("MID_ATLANTIC", CUT, direction, directions)
    assert (card["drivers_supported"], sorted(card["drivers_ruled_out"])) == (supported, sorted(ruled_out))
    assert section["number"].startswith("3.") and section["title"] == "Medicare Part D plan one in Mid-Atlantic"


@pytest.mark.parametrize("story", CASES)
def test_the_cut_card_follows_its_territory_card(briefs, story):
    env, _ = briefs[story]
    cards = [(s["number"], s["card"]) for s in env["sections"] if s["number"].startswith("3.") and s.get("card")]
    at = next(i for i, (_, c) in enumerate(cards) if c.get("cut"))
    before = cards[at - 1][1]
    assert before["territory"] == "MID_ATLANTIC" and not before.get("cut")
    assert sum(1 for _, c in cards if c.get("cut")) == 1


@pytest.mark.parametrize("story", CASES)
def test_the_golden_plan_facts_and_the_cut_finding_are_stated(briefs, story):
    """The plan's level before and after and its change print at the golden precision; the finding scores in full."""
    from eval.harness.scorers import finding_counts, key_fact_counts

    env, expected = briefs[story]
    plan_facts = [f["id"] for f in expected["key_facts"] if f.get("needs") == "plan_cut"]
    assert plan_facts
    _, missing, _ = key_fact_counts(env, expected)
    assert not set(plan_facts) & set(missing), missing
    got, possible, notes = finding_counts(env, expected)
    assert got == possible and not notes, notes


def test_the_cut_text_states_each_measure_the_definition_holds(briefs):
    env, _ = briefs["P1-Q4"]
    text = cut_sections(env)[0]["text"]
    assert "new patients (NBRx) averaged 15.9 a week on the comparison weeks against 23.8 before (down 33%)" in text
    assert "TRx averaged 145 a week on the comparison weeks against 183 before (down 21%)" in text
    assert "Confidence: High. Leading driver: access." in text
    assert "Checked for this plan" in cut_sections(env)[0]["detail"] and "restrictions" in cut_sections(env)[0]["detail"]
    one, _ = briefs["P2-Q2"]
    only = cut_sections(one)[0]["text"]
    assert "TRx averaged 145 a week on the comparison weeks against 158 before (down 8.0%)" in only and "NBRx" not in only


def test_the_headline_names_the_plan_and_the_territory(briefs):
    env, _ = briefs["P2-Q2"]
    head = cut_sections(env)[0]["card"]["headline"]
    assert head == ("Medicare Part D plan one in Mid-Atlantic fell from 158 to 145 TRx a week (down 8.0%), "
                    "while Mid-Atlantic rose 9.9%.")
    assert not any(x in head for x in ("SYN_", "MID_ATLANTIC", "plan:"))


def test_the_claims_carry_the_plan_grain_and_cut(briefs):
    env, _ = briefs["P1-Q4"]
    plan_claims = [c for c in env["claims"] if c["labels"].get("cut") == CUT]
    assert plan_claims and all(c["labels"]["grain"] == "plan" for c in plan_claims)
    assert {c["labels"]["measure"] for c in plan_claims} >= {"nbrx", "trx"}  # the extra measure is labelled with its own


# the leader sees the headline only, the analyst the text and the folded checks ---------------------------------

def test_the_leader_view_shows_the_cut_headline_only(briefs):
    env, _ = briefs["P2-Q2"]
    leader = [s for s in leadership_sections(env["sections"]) if (s.get("card") or {}).get("headline", "").startswith("Medicare")]
    assert len(leader) == 1
    assert leader[0]["text"] == "" and leader[0]["prose"] == "" and "detail" not in leader[0]
    assert leader[0]["card"]["territory"] == "MID_ATLANTIC" and leader[0]["card"]["drivers_supported"] == ["access"]


# a brief with no flagged plan is unchanged ------------------------------------------------------------------------

def test_a_brief_with_a_story_and_no_flagged_plan_has_no_cut_card():
    """P4-Q1 tells a Great Lakes story, and none of its plans runs against it or holds an access change."""
    env, _ = brief_for("P4-Q1")
    assert [s["card"]["territory"] for s in env["sections"] if s["number"].startswith("3.") and s.get("card")][:1] == ["GREAT_LAKES"]
    assert not cut_sections(env)
    assert not any("cut:" in str(c.get("labels", {}).get("cut")) for c in env["claims"])


# the screen ----------------------------------------------------------------------------------------------------------

def screen(story: str, territories: list[str]) -> list[dict]:
    case = golden(story)
    reg = Registry()
    try:
        p = stages.resolve(reg, case.question, definition=case.definition.model_dump(mode="json"))
        return splits.screen_cuts(reg, p, territories)
    finally:
        reg.close()


def test_the_screen_flags_the_plan_that_holds_the_access_change():
    [cut] = screen("P2-Q2", ["MID_ATLANTIC"])
    assert (cut["territory"], cut["plan"], cut["cut"], cut["access"], cut["direction"]) == ("MID_ATLANTIC", PLAN, CUT, True, "down")


def test_a_plan_that_moves_against_its_territory_is_flagged_without_an_access_change():
    # P4-Q4 compares with the summer; Mid-Atlantic and the plan both rose, so only the access change flags it
    [cut] = screen("P4-Q4", ["MID_ATLANTIC"])
    assert cut["access"] and not cut["against"]
    # the same period, a territory that is not Mid-Atlantic, has no access change on any plan and none that runs against it
    assert all(c["territory"] == "MID_ATLANTIC" for c in screen("P4-Q4", ["MID_ATLANTIC", "NEW_ENGLAND"]))


def test_the_screen_never_returns_more_than_two_cut_cards_and_orders_them_by_change():
    cuts = screen("P2-Q4", list(__import__("pharmagentics.tools.queries", fromlist=["x"]).TERRITORY_NAMES)[:8])
    assert len(cuts) <= splits.MOST_CUT_CARDS
    assert [c["impact"] for c in cuts] == sorted((c["impact"] for c in cuts), reverse=True)


def test_a_small_cell_is_never_quoted(monkeypatch):
    monkeypatch.setattr(splits, "SMALL_CELL", 10_000)
    assert screen("P2-Q2", ["MID_ATLANTIC"]) == []


def test_the_screen_asks_nothing_without_a_comparison_or_a_plan_grain():
    case = golden("P2-Q2")
    d = Definition.model_validate({**case.definition.model_dump(mode="json"), "grain": ["national", "territory"]})
    reg = Registry()
    try:
        p = stages.resolve(reg, case.question, definition=d)
        assert splits.screen_cuts(reg, p, ["MID_ATLANTIC"]) == []
    finally:
        reg.close()


# the budget (FR-008) -------------------------------------------------------------------------------------------------

def story(id_: str, n_words: int, *, territory: str = "MID_ATLANTIC", cut: str | None = None) -> memo.StoryBlock:
    lines = [" ".join(["word"] * n_words)]
    card = {"headline": "A short headline.", "confidence": "High", "drivers_checked": [], "territory": territory, "direction": "up",
            "drivers_supported": [], "drivers_ruled_out": [], "cut": cut}
    return memo.StoryBlock(id_, id_, lines, card=card, detail=["folded"])


def parts(*stories: memo.StoryBlock, filler: int = 0) -> memo.MemoParts:
    return memo.MemoParts(title=["Title."], bottom_line=[" ".join(["fill"] * filler) or "Fill."], numbers=["Numbers."], limits=["Limits."],
                          next_checks=["Next."], appendix=["Appendix."], stories=list(stories))


def test_under_the_budget_nothing_shrinks():
    template, sections = memo.compose(parts(story("territory:A", 100), story("territory:B", 100)))
    assert memo.visible_words(sections) <= memo.WORD_BUDGET
    assert [s["lines"] for s in sections if s["number"].startswith("3.")] == [story("territory:A", 100).lines, story("territory:B", 100).lines]


def test_over_the_budget_territory_cards_shrink_to_the_headline_longest_first_and_a_cut_card_never_does():
    big, small, cut = story("territory:A", 500), story("territory:B", 200), story("cut:P", 150, cut="plan:P")
    template, sections = memo.compose(parts(small, big, cut, filler=100))
    cards = {s["title"]: s for s in sections if s["number"].startswith("3.")}
    assert cards["territory:A"]["lines"] == [] and cards["territory:A"]["card"]["headline"] and "word" in cards["territory:A"]["detail"]
    assert cards["territory:B"]["lines"] == small.lines  # the longest shrank first, and that was enough
    assert cards["cut:P"]["lines"] == cut.lines
    assert memo.visible_words(sections) <= memo.WORD_BUDGET
    assert template.count("word") == 500 + 200 + 150  # nothing leaves the scored answer


def test_when_shrinking_every_territory_card_is_not_enough_nothing_is_dropped():
    template, sections = memo.compose(parts(story("territory:A", 400), story("cut:P", 600, cut="plan:P"), story("cut:Q", 600, cut="plan:Q")))
    cards = [s for s in sections if s["number"].startswith("3.")]
    assert len(cards) == 3 and cards[0]["lines"] == [] and cards[1]["lines"] and cards[2]["lines"]
    assert memo.visible_words(sections) > memo.WORD_BUDGET


def test_the_budget_and_the_word_count_match_the_scorer():
    from eval.harness.scorers import WORD_BUDGET, count_words

    assert memo.WORD_BUDGET == WORD_BUDGET["analyst"]
    template, built = memo.compose(parts(story("territory:A", 40), story("cut:P", 30, cut="plan:P"), filler=20))
    filled = memo.render_sections(built, [])
    assert memo.visible_words(built) == count_words(filled)


def test_a_shrunk_brief_scores_as_before(briefs):
    """P1-Q4 was 898 analyst words before the cut card; it prints inside the budget with the card and the shrink."""
    from eval.harness.scorers import WORD_BUDGET, count_words

    env, _ = briefs["P1-Q4"]
    assert count_words(env["sections"]) <= WORD_BUDGET["analyst"]
    assert any(s["number"].startswith("3.") and not s["text"] and s["card"] for s in env["sections"])


def test_the_shrink_brings_p4_q1_back_inside_the_analyst_budget():
    """P4-Q1 reports the Mid-Atlantic restatement and runs 908 analyst words unshrunk; its territory card shrinks to the headline."""
    from eval.harness.scorers import WORD_BUDGET, count_words

    env, _ = brief_for("P4-Q1")
    # UAT review 3.7: a brief about one territory now opens §1 with that territory's change. That line is a deliberate
    # addition of its own (the budget was set before it), so the shrink is judged on the words without it.
    lead = next(x for x in env["sections"][0]["text"].splitlines() if x.startswith("Great Lakes: "))
    assert count_words(env["sections"]) - memo._words(lead) <= WORD_BUDGET["analyst"]
    stories = [x for x in env["sections"] if x["number"].startswith("3.") and (x.get("card") or {}).get("territory") == "GREAT_LAKES"]
    assert stories and not stories[0]["text"] and stories[0]["card"]["headline"] and "Checked, in this order" in stories[0]["detail"]
    assert "Checked, in this order" in env["answer"]  # nothing left the scored answer


# triage and the agent's manager (FR-007) ------------------------------------------------------------------------------

def test_the_triage_plan_proposes_the_cut_card_between_the_territory_stories_and_the_competitor():
    from briefing_baseline import pipeline

    case = golden("P2-Q2")
    plan = pipeline.triage(case.question, definition=case.definition.model_dump(mode="json"))
    ids = [c["id"] for c in plan["stories"]]
    assert ids == ["territory:MID_ATLANTIC", f"cut:{PLAN}"] + ([c for c in ids if c.startswith("competitor:")])
    card = next(c for c in plan["stories"] if c["kind"] == "cut")
    assert (card["territory"], card["proposed"], card["title"]) == ("MID_ATLANTIC", "investigate", "Medicare Part D plan one in Mid-Atlantic")
    assert "Medicare Part D plan one in Mid-Atlantic" in card["what_moved"] and "(down 8.0%)" in card["what_moved"]
    assert "access change" in card["decision"] and "there is nothing to investigate" in card["decision"]


def test_the_plan_of_a_run_without_a_cut_card_keeps_its_ids():
    from briefing_baseline import pipeline

    plan = pipeline.triage(ROUTINE)
    assert not any(c["kind"] == "cut" for c in plan["stories"])


def test_a_decision_may_drop_the_cut_card_and_the_run_then_has_none():
    from briefing_baseline import pipeline

    case = golden("P2-Q2")
    d = case.definition.model_dump(mode="json")
    plan = pipeline.triage(case.question, definition=d)
    kept = pipeline.run_with_plan(case.question, {"plan_id": plan["plan_id"], "stories": ["territory:MID_ATLANTIC"]}, definition=d)
    assert not cut_sections(kept["envelope"])
    assert "Medicare Part D plan one" in kept["envelope"]["answer"].split("Left out of this brief by the analyst:")[-1]
    both = pipeline.run_with_plan(case.question, {"plan_id": plan["plan_id"], "stories": ["territory:MID_ATLANTIC", f"cut:{PLAN}"]}, definition=d)
    assert len(cut_sections(both["envelope"])) == 1


def test_the_manager_may_drop_a_cut_card_and_gives_it_no_drivers():
    from briefing_agent import plan as planmod
    from briefing_baseline import pipeline

    case = golden("P2-Q2")
    code = pipeline.triage(case.question, definition=case.definition.model_dump(mode="json"))
    text = planmod.cards_text(code)
    assert f"cut:{PLAN}" in text and "plan cut card" in text
    kept = planmod.apply(code, '{"order": ["territory:MID_ATLANTIC", "cut:%s"], "hypotheses": {"cut:%s": ["access"]}}' % (PLAN, PLAN))
    card = next(c for c in kept["stories"] if c["kind"] == "cut")
    assert card["manager"]["keep"] and card["manager"]["hypotheses"] == []
    dropped = planmod.apply(code, '{"order": ["territory:MID_ATLANTIC"], "drop": {"cut:%s": "repeats the territory story"}}' % PLAN)
    assert f"cut:{PLAN}" not in dropped["manager_order"]


# the agent's engine builds the same card (FR-007) -------------------------------------------------------------------

def test_the_agent_session_builds_the_same_cut_card_and_assembles_it_after_its_territory():
    from briefing_agent import write
    from pharmagentics.mcp_server import RunSession

    case = golden("P2-Q2")
    d = case.definition.model_dump(mode="json")
    scripted_env, _ = brief_for("P2-Q2")
    s = RunSession()
    s.open_run(case.question, definition=Definition.model_validate(d))
    sections = s.brief_sections()
    for check in (s.check_data, s.check_access, s.check_promotion, s.check_supply, s.check_competitor):
        check("MID_ATLANTIC")
    told = [{"id": "territory:MID_ATLANTIC", "n": 1, "section": s.story_section("MID_ATLANTIC", 1), "territory": "MID_ATLANTIC"}]
    close = s.memo_close(competitor=False, cuts=[PLAN])
    [cut] = close["cut_stories"]
    assert cut["id"] == f"cut:{PLAN}" and cut["territory"] == "MID_ATLANTIC"
    ours = {k: s.reg.render(v) if isinstance(v, str) else v for k, v in close["story_cards"][cut["id"]].items()}
    theirs = cut_sections(scripted_env)[0]["card"]
    assert {k: v for k, v in ours.items() if k != "headline_citations"} == {k: v for k, v in theirs.items() if k != "headline_citations"}
    assert s.reg.render(cut["section"]) == cut_sections(scripted_env)[0]["text"]
    stories = write.place_cuts(told, close["cut_stories"])
    assert [x["id"] for x in stories] == ["territory:MID_ATLANTIC", cut["id"]]
    _template, built = write.assemble(sections, close, stories, "", {}, [], s.dropped_line())
    rendered = memo.render_sections(built, s.reg.claims)
    cards = [x for x in rendered if x["number"].startswith("3.") and (x.get("card") or {}).get("territory") != "NATIONAL"]  # the national card (packet NC) is not a territory story
    assert [bool(x["card"].get("cut")) for x in cards] == [False, True]
    assert cards[1]["detail"].startswith("Checked for this plan")
    s.close()
