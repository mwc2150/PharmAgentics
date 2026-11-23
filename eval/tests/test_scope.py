"""scope_match and the expected scope derived from a case's question prefix (core-011 packet F)."""
import yaml

from eval.harness.cases import Case, derive_scope, load_cases
from eval.harness.paths import GOLDEN_DIR
from eval.harness.scorers import scope_match

EXPECT = {"scope": {"territory": "SOUTHEAST", "week_start": "2026-08-24", "week_end": "2026-08-24",
                    "comparison": None, "intent": "brief"}}


def outputs(proposal):
    return {"answer": "x", "trajectory": {"scope_proposal": proposal}} if proposal is not None else {"answer": "x"}


def test_exact_match_scores_one():
    fb = scope_match(outputs=outputs(dict(EXPECT["scope"])), expectations=EXPECT)
    assert fb.value == 1.0


def test_lower_case_territory_still_matches():
    fb = scope_match(outputs=outputs({**EXPECT["scope"], "territory": "southeast"}), expectations=EXPECT)
    assert fb.value == 1.0


def test_partial_match_names_the_mismatches():
    fb = scope_match(outputs=outputs({**EXPECT["scope"], "territory": "ALL", "week_end": "2026-08-31"}), expectations=EXPECT)
    assert fb.value == 0.5  # 4 checked fields (territory, two weeks, intent); 2 right
    assert "territory: expected SOUTHEAST, got ALL" in fb.rationale and "week_end" in fb.rationale


def test_unset_expected_fields_are_not_checked_and_comparison_must_match_when_set():
    expect = {"scope": {"territory": None, "week_start": None, "week_end": None,
                        "comparison": {"kind": "last_year"}, "intent": None}}
    assert scope_match(outputs=outputs({"comparison": {"kind": "last_year", "weeks": None}}), expectations=expect).value == 1.0
    assert scope_match(outputs=outputs({"comparison": {"kind": "previous", "weeks": 4}}), expectations=expect).value == 0.0


def test_not_scored_without_a_proposal_or_without_expected_fields():
    assert scope_match(outputs=outputs(None), expectations=EXPECT).value is None
    assert scope_match(outputs={"answer": "x", "trajectory": {"scope": "free text"}}, expectations=EXPECT).value is None
    empty = {"scope": {k: None for k in EXPECT["scope"]}}
    assert scope_match(outputs=outputs({"territory": "ALL"}), expectations=empty).value is None


def test_prefix_derivation_examples():
    one = derive_scope("Week of 2026-06-08 in Pacific: Why did Pacific fall?")
    assert (one.territory, one.week_start, one.week_end, one.intent) == ("PACIFIC", "2026-06-08", "2026-06-08", "brief")
    span = derive_scope("Weeks of 2026-08-31 to 2026-09-28, South Central: How confident are we?")
    assert (span.territory, span.week_start, span.week_end) == ("SOUTH_CENTRAL", "2026-08-31", "2026-09-28")
    national = derive_scope("Week of 2026-05-04: Is this week's data complete?")
    assert national.territory == "ALL"
    two = derive_scope("Weeks of 2025-12-22 and 2025-12-29: Does this matter?")
    assert (two.week_start, two.week_end) == ("2025-12-22", "2025-12-29")
    assert derive_scope("Brief of 2026-07-13: Can I quote these numbers?").week_start == "2026-07-13"
    promo = derive_scope("Where should the next dollar go?")
    assert (promo.territory, promo.week_start, promo.intent) == (None, None, "promotion_review")
    assert derive_scope("How confident is the estimate, and when will we know more?").intent is None


def test_a_non_monday_date_is_read_as_its_reporting_week():
    assert derive_scope("Week of 2026-06-10: x").week_start == "2026-06-08"


def test_every_briefing_golden_question_derives_without_error():
    cases = load_cases("briefing")
    assert cases
    for case in cases:
        scope = case.expectations()["scope"]
        if case.question.startswith(("Week of", "Weeks of", "Brief of")):
            assert scope["week_start"] and scope["week_end"] and scope["territory"] and scope["intent"] == "brief", case.id
        else:
            assert scope["week_start"] is None and scope["territory"] is None, case.id  # no prefix: nothing to check


def test_case_comparison_flows_into_the_expected_scope():
    by_id = {c.id: c for c in load_cases("briefing")}
    assert by_id["C-031"].expectations()["scope"]["comparison"] == {"kind": "last_year"}
    assert by_id["C-032"].expectations()["scope"]["comparison"]["kind"] == "custom"
    assert by_id["C-030"].expectations()["scope"]["comparison"] is None


def test_an_explicit_scope_overrides_the_derived_one_and_existing_yaml_loads_unchanged():
    path = next(p for p in sorted((GOLDEN_DIR / "briefing").glob("*.yaml")))
    raw = yaml.safe_load(path.read_text(encoding="utf8"))
    assert "scope" not in raw
    assert Case.model_validate(raw).scope is None
    explicit = Case.model_validate({**raw, "scope": {"territory": "PACIFIC", "intent": "brief"}})
    assert explicit.expectations()["scope"] == {"territory": "PACIFIC", "week_start": None, "week_end": None,
                                                "comparison": None, "intent": "brief"}
