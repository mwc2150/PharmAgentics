"""core-011 scorers: key_fact_recall, finding_recall, false_drivers, brief_words. A case with nothing to check
is not scored (value None), which MLflow leaves out of the run mean."""
from eval.harness.cases import load_cases
from eval.harness.scorers import REPORT_ONLY, brief_words, finding_recall, false_drivers, key_fact_recall
from eval.harness import scorers as scorer_module


def fact(id, value, tolerance=None):
    return {"id": id, "value": value, "tolerance": tolerance}


def text(answer):
    return {"system": "test", "answer": answer}


def card(territory, direction, supported=(), ruled_out=(), headline="Story"):
    return {"headline": headline, "territory": territory, "direction": direction,
            "drivers_supported": list(supported), "drivers_ruled_out": list(ruled_out)}


def memo(*cards, extra=()):
    sections = [{"number": f"3.{i}", "title": "Story", "text": "", "card": c} for i, c in enumerate(cards, 1)]
    return {"system": "test", "answer": "", "sections": [*extra, *sections]}


SOUTHEAST = {"id": "se", "territory": "SOUTHEAST", "direction": "down",
             "drivers_supported": ["promotion"], "drivers_ruled_out": ["access"], "withheld": False}


def expect(*findings):
    return {"findings": list(findings)}


# key_fact_recall

def test_two_of_three_must_facts_name_the_missing_one():
    facts = [fact("a", 3860), fact("b", 4729), fact("c", 481)]
    fb = key_fact_recall(outputs=text("TRx was 3,860, down from 4,729."), expectations={"key_facts": facts})
    assert fb.value == 0.6667 and "missing: c" in fb.rationale


def test_no_must_facts_is_not_scored():
    fb = key_fact_recall(outputs=text("TRx was 3,860."), expectations={"key_facts": []})
    assert fb.value is None and "Not scored" in fb.rationale
    assert key_fact_recall(outputs=text("x"), expectations={}).value is None


def test_tolerance_accepts_a_close_value_and_no_tolerance_does_not():
    answer = text("Calls fell by 116 a week.")
    assert key_fact_recall(outputs=answer, expectations={"key_facts": [fact("f", 120, 0.05)]}).value == 1.0
    assert key_fact_recall(outputs=answer, expectations={"key_facts": [fact("f", 120)]}).value == 0.0
    assert key_fact_recall(outputs=answer, expectations={"key_facts": [fact("f", 120, 0.01)]}).value == 0.0


def test_fact_matches_at_its_stated_precision_and_ignores_sign():
    answer = text("TRx fell 18.4% to 3,860.")
    assert key_fact_recall(outputs=answer, expectations={"key_facts": [fact("p", 18.4), fact("t", 3860.0)]}).value == 1.0
    assert key_fact_recall(outputs=answer, expectations={"key_facts": [fact("p", -18.4)]}).value == 1.0
    assert key_fact_recall(outputs=answer, expectations={"key_facts": [fact("p", 19.4)]}).value == 0.0


# finding_recall and false_drivers

def test_full_match_scores_one_and_no_false_drivers():
    out = memo(card("SOUTHEAST", "down", ["promotion"], ["access"]))
    assert finding_recall(outputs=out, expectations=expect(SOUTHEAST)).value == 1.0
    assert false_drivers(outputs=out, expectations=expect(SOUTHEAST)).value == 0


def test_partial_match_counts_points():
    out = memo(card("SOUTHEAST", "down", ["promotion"], []))  # territory and direction, plus promotion: 2 of 3 points
    fb = finding_recall(outputs=out, expectations=expect(SOUTHEAST))
    assert fb.value == 0.6667 and "ruled out access" in fb.rationale
    assert finding_recall(outputs=memo(card("SOUTHEAST", "up", ["promotion"], ["access"])),
                          expectations=expect(SOUTHEAST)).value == 0.0
    assert finding_recall(outputs=memo(card("SOUTHEAST", "up", ["promotion"], ["access"])),
                          expectations=expect({**SOUTHEAST, "direction": None})).value == 1.0


def test_extra_supported_driver_is_a_false_driver():
    out = memo(card("SOUTHEAST", "down", ["promotion", "supply"], ["access"]))
    fb = false_drivers(outputs=out, expectations=expect(SOUTHEAST))
    assert fb.value == 1 and "supply" in fb.rationale
    assert finding_recall(outputs=out, expectations=expect(SOUTHEAST)).value == 1.0


def test_no_cards_or_no_findings_is_not_scored():
    for scorer_fn in (finding_recall, false_drivers):
        assert scorer_fn(outputs=text("no sections"), expectations=expect(SOUTHEAST)).value is None
        assert scorer_fn(outputs={"answer": "", "sections": None}, expectations=expect(SOUTHEAST)).value is None
        # today's cards carry no territory
        today = {"sections": [{"number": "3.1", "card": {"headline": "x", "drivers_checked": ["access"]}}]}
        assert scorer_fn(outputs=today, expectations=expect(SOUTHEAST)).value is None
        assert scorer_fn(outputs=memo(card("SOUTHEAST", "down")), expectations=expect()).value is None
        assert scorer_fn(outputs=memo(card("SOUTHEAST", "down")), expectations={}).value is None


def test_cards_outside_section_three_are_ignored():
    out = {"sections": [{"number": "2", "card": card("SOUTHEAST", "down", ["promotion"], ["access"])}]}
    assert finding_recall(outputs=out, expectations=expect(SOUTHEAST)).value is None


def test_withheld_finding_scores_when_no_card_has_the_territory():
    withheld = {"id": "w", "territory": "FLORIDA", "withheld": True}
    assert finding_recall(outputs=memo(card("SOUTHEAST", "down")), expectations=expect(withheld)).value == 1.0
    fb = finding_recall(outputs=memo(card("FLORIDA", "down")), expectations=expect(withheld))
    assert fb.value == 0.0 and "withheld" in fb.rationale
    both = finding_recall(outputs=memo(card("SOUTHEAST", "down", ["promotion"], ["access"])),
                          expectations=expect(SOUTHEAST, withheld))
    assert both.value == 1.0


# brief_words

def test_brief_words_counts_text_headline_and_cells_but_not_detail():
    sections = [
        {"number": "1", "text": "one two three", "detail": "never counted " * 50},
        {"number": "2", "text": "four five", "territory_table": {"rows": [{"cells": ["Great Lakes", "down 9%"]}]}},
        {"number": "3.1", "text": "six", "card": {"headline": "Southeast fell sharply"}, "detail": "ignored"},
    ]
    fb = brief_words(outputs={"sections": sections})
    assert fb.value == 3 + 2 + 4 + 1 + 3


def test_brief_words_is_not_scored_without_sections():
    assert brief_words(outputs=text("words")).value is None
    assert brief_words(outputs={"sections": []}).value is None


# registration and existing golden files

def test_new_scorers_are_report_only():
    assert {s.name for s in REPORT_ONLY} == {"key_fact_recall", "finding_recall", "false_drivers", "brief_words"}
    assert not set(scorer_module.GATED) & {s.name for s in REPORT_ONLY}
    assert not {s.name for s in scorer_module.DETERMINISTIC} & {s.name for s in REPORT_ONLY}


def test_golden_key_facts_can_be_matched():
    """Every Briefing case loads, and no must-state fact is a value the answer-side extractor skips
    (integers 0 to 10), which no brief could ever be credited for."""
    cases = load_cases("briefing")
    assert len(cases) == 32
    for case in cases:
        for f in case.expectations()["key_facts"]:
            assert not (isinstance(f["value"], int) and abs(f["value"]) <= 10), (case.id, f["id"])


def test_pooled_share_counts_facts_across_cases_and_skips_unanswered_ones():
    from types import SimpleNamespace
    from eval.harness.run import _pooled_key_facts

    def case(question, facts):
        return SimpleNamespace(inputs=lambda: {"question": question, "follow_up": None, "section": None},
                               expectations=lambda: {"key_facts": facts})

    def key(question, follow_up=None, section=None, comparison=None):
        return question, follow_up, section, comparison

    cases = [case("a", [fact("x", 3860), fact("y", 4729)]), case("b", [fact("z", 481)]), case("c", []),
             case("crashed", [fact("w", 999)])]
    answered = {key("a"): text("3,860 only"), key("b"): text("481"), key("c"): text("nothing")}
    assert _pooled_key_facts(cases, answered, key) == round(2 / 3, 4)
    assert _pooled_key_facts([case("c", [])], {key("c"): text("x")}, key) is None


def test_a_story_the_case_does_not_mention_adds_no_false_driver():
    out = memo(card("SOUTHEAST", "down", ["promotion"], ["access"]), card("PACIFIC", "down", ["supply"]))
    assert false_drivers(outputs=out, expectations=expect(SOUTHEAST)).value == 0
