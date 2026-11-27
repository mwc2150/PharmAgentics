"""The request intent (brief-010 packet I): a golden case states `intent`, default "brief", and a Briefing system gets
the question the app's API builds for that intent (service.normalize_question), without a second prefix."""
import yaml

from eval.harness.cases import Case, load_cases
from eval.harness.paths import GOLDEN_DIR
from eval.harness.systems import BRIEFING_SYSTEMS, briefing_question


def _case_dict(name: str = "P1-Q1") -> dict:
    return yaml.safe_load((GOLDEN_DIR / "briefing" / f"{name}.yaml").read_text(encoding="utf8"))


def test_intent_defaults_to_brief_when_absent():
    data = _case_dict()
    data.pop("intent", None)
    assert Case.model_validate(data).intent == "brief"


def test_explicit_intent_is_read():
    data = {**_case_dict(), "intent": "promotion_review"}
    assert Case.model_validate(data).intent == "promotion_review"


def test_unknown_intent_is_refused():
    data = {**_case_dict(), "intent": "forecast"}
    try:
        Case.model_validate(data)
    except ValueError:
        return
    raise AssertionError("an intent outside brief and promotion_review should not load")


def test_national_promotion_review_prefix():
    q = "How confident is the estimate, and when will we know more?"
    assert briefing_question(q, "promotion_review") == f"Promotion review in National: {q}"


def test_named_territory_takes_its_label():
    q = "Southeast: did the lapse hold, and by how much?"
    assert briefing_question(q, "promotion_review") == f"Promotion review in Southeast: {q}"


def test_no_double_prefix():
    q = "Promotion review in Great Lakes: Did it work?"
    assert briefing_question(q, "promotion_review") == q


def test_brief_intent_leaves_the_question_alone():
    q = "How confident is the estimate?"
    assert briefing_question(q, "brief") == q
    assert briefing_question(q) == q


def test_only_briefing_systems_get_the_prefix():
    from eval.harness.systems import ReferenceSystem, ForecastScripted
    assert ReferenceSystem not in BRIEFING_SYSTEMS and ForecastScripted not in BRIEFING_SYSTEMS


def test_p4_q5_is_a_promotion_review_and_the_prefixed_question_reads_as_one():
    from eval.harness.cases import derive_scope

    case = next(c for c in load_cases("briefing") if c.id == "C-023")
    assert case.story == "P4-Q5" and case.intent == "promotion_review"
    assert case.inputs()["intent"] == "promotion_review"
    assert case.expected_scope().intent == "promotion_review"
    sent = briefing_question(case.question, case.intent)
    assert sent == "Promotion review in National: How confident is the estimate, and when will we know more?"
    assert derive_scope(sent).intent == "promotion_review"


def test_p4_q3_is_a_promotion_review():
    """Michael, 2026-11-27: P4-Q3's assumptions are a release-wide Promotion review, which the engine read from its words."""
    case = next(c for c in load_cases("briefing") if c.story == "P4-Q3")
    assert case.intent == "promotion_review" and case.inputs()["intent"] == "promotion_review"


def test_other_briefing_cases_stay_brief():
    others = [c for c in load_cases("briefing") if c.story not in ("P4-Q5", "P4-Q3")]
    assert others and all(c.intent == "brief" for c in others)
