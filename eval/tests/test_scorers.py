"""Each code check on planted good and bad answers, plus the positive control on all 42 cases."""
import inspect

import pytest

from eval.harness import numbers
from eval.harness.cases import load_cases
from eval.harness.scorers import (DETERMINISTIC, governed_terms, must_not_say, no_individual_rep,
                                  numbers_match_golden, numbers_traced)

EXPECT = {
    "expected_response": "National BXA TRx was 3,860, down 18.4% from 4,729 the week before.",
    "golden_numbers": [3860],
    "must_not_say": ["BXA fell 18% nationally"],
}


def answer(text):
    return {"system": "test", "answer": text}


def test_numbers_skip_dates_ids_years_and_small_counts():
    text = "Week of 2026-04-06 (P2-Q1, EV-2.1): 7 of 8 territories, 3,860 TRx, −18.4%, since 2026, SYN_X_1, 31st week"
    assert [n.text for n in numbers.extract(text)] == ["3,860", "−18.4%"]


def test_rounding_follows_the_stated_precision():
    p = numbers.parse_token
    assert numbers.same(p("18%"), p("18.4%")) and numbers.same(p("0.66"), p("0.656"))
    assert not numbers.same(p("19%"), p("18.4%"))


def test_invented_numbers_are_flagged():
    fb = numbers_match_golden(outputs=answer("BXA TRx was 3,860, against about 4,100 last week."), expectations=EXPECT)
    assert fb.value == 0.5 and "4,100" in fb.rationale


def test_must_not_say_catches_a_rounded_paraphrase():
    assert must_not_say(outputs=answer("Overall, BXA fell by 18.4% nationally."), expectations=EXPECT).value is False
    assert must_not_say(outputs=answer("BXA TRx was 3,860; the dip is a data artifact."), expectations=EXPECT).value is True


@pytest.mark.parametrize("text, ok", [
    ("Competitive intelligence flagged the change.", True),
    ("Statistical surveillance flagged the change.", False),
    ("NRx rose, so new patients grew.", False),
    ("NBRx (new patients) rose 4%.", True),
])
def test_governed_terms(text, ok):
    assert governed_terms(outputs=answer(text)).value is ok


@pytest.mark.parametrize("text, ok", [
    ("Southeast rep calls fell to 19 a week.", True),
    ("Rep calls held at 50 a week.", True),
    ("Rep John Smith missed his visits.", False),
    ("Calls by rep ID 4471 fell.", False),
])
def test_no_individual_rep(text, ok):
    assert no_individual_rep(outputs=answer(text)).value is ok


def run_scorer(s, **kwargs):
    """Pass only the arguments the scorer declares, as mlflow.genai.evaluate does."""
    wanted = inspect.signature(getattr(s, "_original_func", s)).parameters
    return s(**{k: v for k, v in kwargs.items() if k in wanted})


@pytest.mark.parametrize("case", load_cases(), ids=lambda c: c.story)
def test_golden_answers_pass_every_code_check(case):
    """Positive control: a golden answer that fails a code check means the check, or the case, is wrong."""
    for s in DETERMINISTIC:
        fb = run_scorer(s, inputs={"question": case.question}, outputs=answer(case.reference_answer),
                        expectations=case.expectations())
        assert fb.value in (True, 1.0), f"{s.name}: {fb.rationale}"


def test_numbers_traced_counts_an_unfilled_claim_token():
    claims = [{"value": "19.5%", "evidence_id": "e1"}]
    clean = numbers_traced.run(outputs={"answer": "The headline total is down 19.5%.", "claims": claims, "evidence": []})
    left = numbers_traced.run(outputs={"answer": "Down 19.5%. {c8} calendar effects are present.", "claims": claims, "evidence": []})
    assert clean.value == 1.0
    assert left.value == 0.5 and "{c8}" in left.rationale


def test_every_scorer_has_a_kind_and_the_kinds_are_the_four_agreed():
    from mlflow.genai.scorers import Scorer

    from eval.harness import scorers as module

    defined = {v.name for v in vars(module).values() if isinstance(v, Scorer)}
    listed = {s.name for group in (module.DETERMINISTIC, module.REPORT_ONLY, module.EVIDENCE, module.TRAJECTORY) for s in group}
    assert defined >= listed and "scope_match" in defined
    assert (defined | listed | set(module.GATED)) <= set(module.KIND)
    assert set(module.KIND.values()) == {"code", "agent", "safety", "ops"}
    assert set(module.KIND) <= defined | {"judge_factual_correctness"}  # no stale name
    assert module.kind_of("judge_anything") == "agent"
    assert {module.KIND[k] for k in module.GATED} == {"code", "safety"}  # the gate is untouched


def test_a_percent_matches_only_a_percent():
    p = numbers.parse_token
    assert not numbers.matches(p("22.5%"), p("23"))  # "23 TRx" does not state 22.5%
    assert not numbers.matches(p("42"), p("42%"))
    assert numbers.matches(p("37%"), p("37.1%")) and numbers.matches(p("4,309"), p("4,309"))
    assert numbers.matches(p("-18.4%"), p("18%"))  # sign and coarser precision still match
    assert numbers.matches(numbers.as_numbers([22.5])[0], p("23%")) and numbers.matches(numbers.as_numbers([22.5])[0], p("23"))  # fact values carry no unit


def test_golden_number_recall_is_unit_aware_and_counts_a_repeated_golden_number_once():
    from eval.harness.scorers import golden_number_recall

    expect = {"expected_response": "Share was 22.5% on 4,309 TRx; 16.1% here, and again 16.1% there."}
    miss = golden_number_recall(outputs=answer("Share was 23 on 4,309 TRx; 16.1% overall."), expectations=expect)
    assert miss.value == round(2 / 3, 4) and "22.5%" in miss.rationale  # 3 distinct golden numbers, the % one missed
    full = golden_number_recall(outputs=answer("Share was 22.5% on 4,309 TRx; 16.1% overall."), expectations=expect)
    assert full.value == 1.0 and "3 of 3" in full.rationale


def test_numbers_match_golden_uses_the_same_unit_rule():
    expect = {"expected_response": "Share was 22.5% on 4,309 TRx.", "golden_numbers": [22.5, 4309]}
    fb = numbers_match_golden(outputs=answer("Share was 23 TRx on 4,309 TRx."), expectations=expect)
    assert fb.value == 0.5 and "23" in fb.rationale  # 22.5 is a percent in the text, so "23" is not a match
