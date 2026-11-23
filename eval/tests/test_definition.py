"""The case's brief definition (brief-010 FR-000d, packet G): explicit on every Briefing case, the old top-level
`comparison:` read into it, passed to the system only when the system takes it, and findings that name a measure."""
import re

import pytest
import yaml
from pydantic import ValidationError

from eval.harness.cases import DEFAULT_COMPARISON, Case, Comparison, Definition, Finding, derive_scope, load_cases
from eval.harness.paths import GOLDEN_DIR
from eval.harness.scorers import finding_recall
from eval.harness.systems import accepts, definition_option

BRIEFING = load_cases("briefing")
FIELDS = {"first_week", "last_week", "comparison", "territories", "measure", "grain", "relative_to"}


def raw(story):
    return yaml.safe_load((GOLDEN_DIR / "briefing" / f"{story}.yaml").read_text(encoding="utf8"))


def case_from(**extra):
    base = raw("P1-Q1")
    base.pop("definition", None)
    return Case.model_validate({**base, **extra})


def test_every_briefing_case_states_every_definition_field():
    assert len(BRIEFING) == 32
    for path in sorted((GOLDEN_DIR / "briefing").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf8"))
        assert "comparison" not in data, f"{path.stem}: the old top-level comparison is gone"
        assert set(data["definition"]) == FIELDS, path.stem
        assert data["definition"]["territories"] == "like_for_like", path.stem
        assert data["definition"]["relative_to"] == "other_territories", path.stem
        assert set(data["definition"]["grain"]) == {"national", "territory", "plan", "channel", "specialty"}, path.stem


def test_period_comes_from_the_question_prefix_and_none_means_latest_closed_week():
    for c in BRIEFING:
        scope = derive_scope(c.question)
        assert c.definition.first_week == scope.week_start and c.definition.last_week == scope.week_end, c.story
    by = {c.story: c for c in BRIEFING}
    assert by["P2-Q6"].definition.first_week is None and by["P4-Q2"].definition.last_week is None
    assert (by["P3-Q2"].definition.first_week, by["P3-Q2"].definition.last_week) == ("2025-12-22", "2025-12-29")


def test_measure_is_trx_except_p1_q4_which_is_both_with_nbrx_primary():
    assert {c.story: c.definition.measure for c in BRIEFING if c.definition.measure != ["trx"]} == {"P1-Q4": ["nbrx", "trx"]}


def test_comparison_is_explicit_and_cases_without_one_use_the_previous_four_weeks():
    by = {c.story: c for c in BRIEFING}
    assert by["P1-Q1"].definition.comparison == [DEFAULT_COMPARISON]
    assert by["P1-Q5"].definition.primary_comparison.kind == "custom"
    assert by["WIN-1"].definition.primary_comparison.kind == "last_year"
    assert by["P3-Q1"].definition.primary_comparison.kind == "pre_launch"
    assert {c.story for c in BRIEFING if c.comparison} == {"WIN-1", "WIN-2", "P1-Q4", "P1-Q5", "P2-Q1", "P2-Q3", "P2-Q4", "P3-Q1", "P4-Q4"}


def test_an_old_top_level_comparison_is_read_into_the_definition():
    old = {"kind": "custom", "start": "2026-07-06", "end": "2026-07-27"}
    case = case_from(comparison=old)
    assert case.definition.primary_comparison.kind == "custom" and str(case.definition.primary_comparison.start) == "2026-07-06"
    assert case.definition.territories == ["like_for_like"] and case.definition.measure == ["trx"]  # the pre-selected values
    assert case.inputs()["comparison"] == old
    assert case.inputs()["definition"]["comparison"] == [old]
    assert case.expectations()["scope"]["comparison"] == old


def test_an_old_file_without_a_comparison_has_no_definition_and_loads_unchanged():
    case = case_from()
    assert case.definition is None and case.comparison is None
    assert "definition" not in case.inputs() and case.expectations()["definition"] is None


def test_the_definition_block_wins_and_an_old_comparison_fills_only_a_missing_one():
    old = {"kind": "last_year"}
    explicit = {"measure": "nbrx", "comparison": {"kind": "previous", "weeks": 2}}
    case = case_from(comparison=old, definition=explicit)
    assert case.definition.primary_comparison.weeks == 2 and case.definition.measure == ["nbrx"]
    filled = case_from(comparison=old, definition={"measure": "nbrx"})
    assert filled.definition.primary_comparison.kind == "last_year" and filled.definition.measure == ["nbrx"]


def test_the_house_comparison_goes_to_a_system_as_none_but_the_expectation_keeps_it_explicit():
    case = next(c for c in BRIEFING if c.story == "P1-Q1")
    assert case.inputs()["definition"]["comparison"] == [] and "comparison" not in case.inputs()
    assert case.expectations()["definition"]["comparison"] == [{"kind": "previous", "weeks": 4}]
    assert case.expectations()["scope"]["comparison"] is None  # the default is no scope choice


def test_a_definition_rejects_unknown_fields_and_values():
    with pytest.raises(ValidationError):
        Definition.model_validate({"territories": "everywhere"})
    with pytest.raises(ValidationError):
        Definition.model_validate({"unknown": 1})
    d = Definition()
    assert d.territories == ["like_for_like"] and d.measure == ["trx"] and d.relative_to == ["other_territories"] and d.comparison == []
    assert d.grain == ["national", "territory", "plan", "channel", "specialty"]


def test_the_definition_goes_to_a_system_only_when_it_takes_one():
    def old(question, comparison=None): ...
    def new(question, comparison=None, definition=None): ...
    assert not accepts(old, "definition") and accepts(new, "definition")
    assert definition_option(old, {"measure": "trx"}) == {}
    assert definition_option(new, {"measure": "trx"}) == {"definition": {"measure": "trx"}}
    assert definition_option(new, None) == {}


def test_findings_may_name_a_measure_and_a_card_must_cover_it():
    with pytest.raises(ValidationError):
        Finding(id="x", territory="NATIONAL", measure="revenue")
    assert Finding(id="x", territory="NATIONAL").measure is None  # None means BXA TRx
    by = {c.story: c for c in BRIEFING}
    got = {(c.story, f.id): f.measure for c in BRIEFING for f in c.findings if f.measure}
    assert got == {("P1-Q4", "mid_atlantic_plan_nbrx_drop"): "nbrx", ("P3-Q1", "national_metacora_share_gain"): "bxa_share",
                   ("P3-Q4", "national_metacora_continuing"): "competitor_share",
                   ("P1-Q5", "national_metacora_competitor"): "competitor_share",
                   ("P2-Q5", "mid_atlantic_restated_figure"): "restated_figure",  # packet X: the restatement is a data note
                   ("P3-Q6", "mid_atlantic_restated_figure"): "restated_figure"}
    expect = by["P3-Q4"].expectations()
    assert expect["findings"][0]["measure"] == "competitor_share"
    card = {"headline": "Story", "territory": "NATIONAL", "direction": "down", "drivers_supported": ["competitor"],
            "drivers_ruled_out": [], "directions": {"bxa_share": "down", "competitor_share": "flat"}}
    sections = [{"number": "3.1", "title": "Story", "text": "", "card": card}]
    fb = finding_recall(outputs={"system": "test", "answer": "", "sections": sections}, expectations=expect)
    assert fb.value == 1.0  # the finding's measure (competitor share) is read from the card's directions
    no_share = [{"number": "3.1", "title": "Story", "text": "", "card": {k: v for k, v in card.items() if k != "directions"}}]
    assert finding_recall(outputs={"system": "test", "answer": "", "sections": no_share}, expectations=expect).value == 0.0


def test_review_decisions_are_applied():
    """Michael, 2026-11-22: every must fact and every finding is reviewed; plan cuts, needs tags and the like-for-like restatements."""
    assert all(f.reviewed for c in BRIEFING for f in c.facts if f.role == "must")
    assert all(f.reviewed for c in BRIEFING for f in c.findings)
    cut = "plan:SYN_MID_ATLANTIC_MEDICARE_PART_D_1"
    cuts = {(c.story, f.id): (f.cut, f.needs) for c in BRIEFING for f in c.findings if f.cut}
    assert cuts == {("P1-Q4", "mid_atlantic_plan_nbrx_drop"): (cut, "plan_cut"), ("P2-Q2", "mid_atlantic_plan_access"): (cut, "plan_cut"),
                    ("P2-Q4", "mid_atlantic_plan_access"): (cut, "plan_cut"), ("P4-Q4", "mid_atlantic_access_restored"): (cut, "plan_cut")}
    needs = {(c.story, f.id): f.needs for c in BRIEFING for f in c.facts if f.needs and not f.id.startswith("plan_")}
    assert needs == {("P1-Q1", "gl_bxa_trx_naive_sum"): "restatement", ("P1-Q1", "gl_bxa_trx_deduplicated"): "restatement",
                     ("P2-Q5", "trx_signed_off"): "restatement", ("P2-Q5", "trx_restated"): "restatement",
                     ("P2-Q5", "restatement_change_pct"): "restatement", ("P3-Q6", "ma_restated_old"): "restatement",
                     ("P3-Q6", "ma_restated_new"): "restatement", ("P4-Q2", "gl_cash_change_pct"): "segment_pct",
                     ("P4-Q2", "se_commercial_change_pct"): "segment_pct"}
    values = {(c.story, f.id): f.value for c in BRIEFING for f in c.facts}
    assert [values[k] for k in [("P2-Q3", "sc_change_pct"), ("P2-Q3", "other_territories_change_pct"),
                                ("P2-Q4", "national_change_pct"), ("P2-Q4", "ma_change_pct"),
                                ("P1-Q5", "national_vs_4wk_avg_pct")]] == [-2.9, 9.1, 10.1, 4.3, -13.8]
    for story, text in [("P2-Q3", "2.9% from July while the other territories rose 9.1%"),
                        ("P2-Q4", "rose 10.1% against June and July. Mid-Atlantic rose only 4.3%"),
                        ("P1-Q5", "(−13.8%)")]:
        assert text in next(c for c in BRIEFING if c.story == story).reference_answer, story
    p24 = next(c for c in BRIEFING if c.story == "P2-Q4")
    assert {f.id: f.value for f in p24.facts if f.id in ("plan_change_pct", "ma_other_channels_change_pct", "plan_trx_drop_per_week",
                                                         "plan_primary_care_nbrx_after")} == {
        "plan_change_pct": -20.7, "ma_other_channels_change_pct": 15.9, "plan_trx_drop_per_week": 38, "plan_primary_care_nbrx_after": 7.7}
    assert "fell 20.7% (about 38 TRx a week)" in p24.reference_answer and "12.1 to 7.7" in p24.reference_answer
    p14 = next(c for c in BRIEFING if c.story == "P1-Q4")
    assert (p14.definition.primary_comparison.kind, str(p14.definition.primary_comparison.start), str(p14.definition.primary_comparison.end)) == ("custom", "2025-06-02", "2025-07-28")
    assert not re.search(r"10\.8|467 below", next(c for c in BRIEFING if c.story == "P1-Q5").reference_answer)


def test_the_pre_launch_comparison_is_accepted_and_reaches_an_engine_as_its_custom_window():
    assert Comparison(kind="pre_launch").kind == "pre_launch"
    for bad in ({"kind": "pre_launch", "weeks": 4}, {"kind": "pre_launch", "start": "2026-02-02"}, {"kind": "yesterday"}):
        with pytest.raises(ValidationError):
            Comparison.model_validate(bad)
    case = case_from(definition={"comparison": {"kind": "pre_launch"}})
    assert case.definition.primary_comparison.kind == "pre_launch" and case.comparison.kind == "pre_launch"
    assert case.definition.payload()["comparison"] == [{"kind": "pre_launch"}]
    assert case.inputs()["definition"]["comparison"] == [{"kind": "pre_launch"}]
    legacy = case.inputs()["comparison"]  # the keyword the shared engines already take
    assert legacy == {"kind": "custom", "start": "2026-02-02", "end": "2026-02-23"}
    from pharmagentics.tools.window import Comparison as EngineComparison
    EngineComparison.model_validate(legacy)
    old = case_from(comparison={"kind": "pre_launch"})  # the old top-level field takes it too
    assert old.definition.primary_comparison.kind == "pre_launch"


def test_holiday_weeks_are_out_of_the_period_in_every_fact_that_spans_one():
    """Michael, 2026-11-22: holiday weeks are always left out of the period. P3-Q2 and WIN-1 are about the holiday weeks
    themselves (the brief keeps them in calendar mode) and P3-Q4's block 7 is a trend series, not the period."""
    holidays = ("2025-09-01", "2025-11-24", "2026-09-07")
    by = {(c.story, f.id): f.sql.replace("''", "'") for c in BRIEFING for f in c.facts}
    spans = {"P1-Q4": ("2025-08-04", "2025-10-27"), "P2-Q2": ("2025-08-04", "2025-10-27"), "P2-Q3": ("2026-08-31", "2026-09-28"),
             "P2-Q4": ("2025-08-04", "2025-10-27"), "P4-Q4": ("2025-11-03", "2025-12-15")}
    for (story, fact), sql in by.items():
        if story in spans:
            window = f"between DATE '{spans[story][0]}' and DATE '{spans[story][1]}'"
            for hol in holidays:
                if window in sql and spans[story][0] <= hol <= spans[story][1]:
                    assert f"<> DATE '{hol}'" in sql, f"{story} {fact} counts {hol}"


def test_every_selector_but_the_period_takes_a_list_and_the_first_value_is_the_primary():
    d = Definition.model_validate({"comparison": {"kind": "last_year"}, "territories": "projected", "measure": "both",
                                   "relative_to": ["national", "none"], "grain": "plan"})
    assert [c.kind for c in d.comparison] == ["last_year"] and d.territories == ["projected"]
    assert d.measure == ["trx", "nbrx"] and d.relative_to == ["national", "none"] and d.grain == ["plan"]
    assert d.primary_comparison.kind == "last_year" and d.payload()["measure"] == ["trx", "nbrx"]
    several = Definition.model_validate({"comparison": [{"kind": "previous", "weeks": 4}, {"kind": "last_year"}],
                                         "measure": ["nbrx", "trx", "nbrx"]})
    assert [c.kind for c in several.comparison] == ["previous", "last_year"] and several.measure == ["nbrx", "trx"]
    assert several.explicit_comparison is None  # the primary is the house default
    assert several.payload(engine=True)["comparison"] == [c.model_dump(mode="json", exclude_none=True) for c in several.comparison]
    assert Definition.model_validate({"comparison": None}).comparison == []
    with pytest.raises(ValidationError):
        Definition.model_validate({"measure": []})
    with pytest.raises(ValidationError):
        Definition.model_validate({"measure": ["revenue"]})
    assert next(c for c in BRIEFING if c.story == "P1-Q4").definition.measure[0] == "nbrx"  # its facts follow the primary
