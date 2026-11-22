"""core-011 packet H (FR-017 to FR-021): cuts, capability tags, targets and pooled metrics, the word budget, and the
below-target split in insights. No model, no MLflow run."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from eval.harness import scorers
from eval.harness.cases import Fact, Finding, load_cases
from eval.harness.insights import build, missed_ids, render_md
from eval.harness.run import pooled_metrics
from eval.harness.scorers import (TARGETS, WORD_BUDGET, brief_words, count_words, false_drivers, finding_recall,
                                  leader_words)
from eval.harness.telemetry_export import cases_block
from eval.tests.test_insights import PAIRS, Q_BRIEF, Q_CONF, Q_DOLLAR, _store


# H1 schema

def test_a_finding_cut_takes_plan_channel_or_segment():
    for cut in ("plan:P-12", "channel:retail", "segment:new_to_brand"):
        assert Finding(id="f", territory="SOUTHEAST", cut=cut).cut == cut
    assert Finding(id="f", territory="SOUTHEAST").cut is None


@pytest.mark.parametrize("cut", ["plan", "plan:", "region:west", "SOUTHEAST", " :x"])
def test_a_malformed_cut_is_refused(cut):
    with pytest.raises(ValidationError):
        Finding(id="f", territory="SOUTHEAST", cut=cut)


def test_needs_is_one_of_the_four_capabilities():
    for need in ("plan_cut", "segment_pct", "restatement", "national_card"):
        assert Fact(id="a", value=1.5, sql="select 1.5", needs=need).needs == need
        assert Finding(id="f", territory="NATIONAL", needs=need).needs == need
    assert Fact(id="a", value=1.5, sql="select 1.5").needs is None
    with pytest.raises(ValidationError):
        Fact(id="a", value=1.5, sql="select 1.5", needs="magic")
    with pytest.raises(ValidationError):
        Finding(id="f", territory="NATIONAL", needs="magic")


def test_expectations_carry_cut_and_needs():
    case = load_cases("briefing")[0].model_copy(update={
        "facts": [Fact(id="x", value=22.5, sql="select 22.45", role="must", needs="segment_pct")],
        "findings": [Finding(id="f", territory="SOUTHEAST", cut="plan:P1", needs="plan_cut")]})
    expected = case.expectations()
    assert expected["key_facts"][0]["needs"] == "segment_pct"
    assert expected["findings"][0]["cut"] == "plan:P1" and expected["findings"][0]["needs"] == "plan_cut"


def test_the_golden_set_still_validates_with_the_new_fields():
    assert len(load_cases()) >= 42


# H2 cut matching

def card(territory, direction="down", supported=(), ruled_out=(), cut=None):
    out = {"headline": "Story", "territory": territory, "direction": direction,
           "drivers_supported": list(supported), "drivers_ruled_out": list(ruled_out)}
    if cut is not None:
        out["cut"] = cut
    return out


def memo(*cards):
    return {"answer": "", "sections": [{"number": f"3.{i}", "title": "Story", "text": "", "card": c} for i, c in enumerate(cards, 1)]}


def finding(id="f", territory="SOUTHEAST", cut=None, **kw):
    return {"id": id, "territory": territory, "direction": "down", "drivers_supported": ["promotion"],
            "drivers_ruled_out": [], "withheld": False, "cut": cut, **kw}


def test_a_cut_finding_is_met_only_by_a_card_with_the_same_cut():
    expected = {"findings": [finding(cut="plan:P1")]}
    whole = memo(card("SOUTHEAST", supported=["promotion"]))
    other = memo(card("SOUTHEAST", supported=["promotion"], cut="plan:P2"))
    same = memo(card("SOUTHEAST", supported=["promotion"], cut="plan:P1"))
    assert finding_recall(outputs=whole, expectations=expected).value == 0.0
    assert finding_recall(outputs=other, expectations=expected).value == 0.0
    assert finding_recall(outputs=same, expectations=expected).value == 1.0
    assert finding_recall(outputs=memo(card("SOUTHEAST", supported=["promotion"], cut=" PLAN:p1 ")),
                          expectations=expected).value == 1.0  # case and edge space do not matter


def test_a_whole_territory_finding_ignores_cut_cards_and_a_missing_cut_key_is_no_cut():
    expected = {"findings": [finding()]}
    only_cut = memo(card("SOUTHEAST", supported=["promotion"], cut="plan:P1"))
    assert finding_recall(outputs=only_cut, expectations=expected).value == 0.0
    both = memo(card("SOUTHEAST", supported=["promotion"], cut="plan:P1"), card("SOUTHEAST", supported=["promotion"]))
    assert finding_recall(outputs=both, expectations=expected).value == 1.0
    assert finding_recall(outputs=memo(card("SOUTHEAST", supported=["promotion"])), expectations=expected).value == 1.0
    legacy = {"findings": [{k: v for k, v in finding().items() if k != "cut"}]}  # an older expectation has no cut key
    assert finding_recall(outputs=memo(card("SOUTHEAST", supported=["promotion"])), expectations=legacy).value == 1.0


def test_a_withheld_cut_is_withheld_only_when_no_card_has_that_cut():
    expected = {"findings": [finding(cut="plan:P1", withheld=True)]}
    assert finding_recall(outputs=memo(card("SOUTHEAST", cut="plan:P2"), card("PACIFIC")), expectations=expected).value == 1.0
    assert finding_recall(outputs=memo(card("SOUTHEAST", cut="plan:P1")), expectations=expected).value == 0.0


def test_false_drivers_hold_a_cut_card_to_the_finding_with_the_same_cut():
    expected = {"findings": [finding("whole"), finding("cut", cut="plan:P1", drivers_supported=["access"])]}
    ok = memo(card("SOUTHEAST", supported=["promotion"]), card("SOUTHEAST", supported=["access"], cut="plan:P1"))
    assert false_drivers(outputs=ok, expectations=expected).value == 0
    swapped = memo(card("SOUTHEAST", supported=["access"]), card("SOUTHEAST", supported=["promotion"], cut="plan:P1"))
    assert false_drivers(outputs=swapped, expectations=expected).value == 2
    unlisted = memo(card("SOUTHEAST", supported=["promotion"]), card("SOUTHEAST", supported=["supply"], cut="channel:retail"))
    assert false_drivers(outputs=unlisted, expectations=expected).value == 0  # no finding for that cut: not a wrong attribution


def test_both_engines_cards_name_a_cut_of_none():
    from pharmagentics.tools.memo import competitor_card, story_card

    facts = {"word": "down", "pct": "{c1}", "peer_word": "up", "peer_pct": "{c2}"}
    assert story_card("Southeast", facts, "High", ["promotion"], territory="SOUTHEAST")["cut"] is None
    assert competitor_card(SimpleNamespace(brand_id="BXA"), {"bxe": "{c1}", "bxa": "{c2}"})["cut"] is None


# H3 targets and pooled metrics

def _case(question, facts=(), findings=(), lane="briefing"):
    expectations = {"key_facts": [{"id": i, "value": v, "tolerance": None} for i, v in facts], "findings": list(findings)}
    return SimpleNamespace(lane=lane, inputs=lambda: {"question": question, "follow_up": None, "section": None},
                           expectations=lambda: expectations)


def _key(question, follow_up=None, section=None, comparison=None):
    return question, follow_up, section, comparison


def _sections(words):
    return [{"number": "1", "title": "t", "text": " ".join(["w"] * words)}]


def test_targets_live_in_code():
    assert TARGETS == {"key_fact_recall": 0.85, "finding_recall": 0.90}


def test_pooled_metrics_and_target_flags(monkeypatch):
    monkeypatch.setitem(WORD_BUDGET, "analyst", 50)
    monkeypatch.setitem(WORD_BUDGET, "leader", 50)
    cases = [_case("a", facts=[("x", 3860), ("y", 4729)], findings=[finding("f1", "SOUTHEAST")]),
             _case("b", facts=[("z", 481)], findings=[finding("f2", "PACIFIC", drivers_supported=[])]),
             _case("forecast", facts=[("w", 999)], lane="forecast")]
    answered = {
        _key("a"): {"answer": "TRx 3,860 and 4,729", "sections": memo(card("SOUTHEAST", supported=["promotion"]))["sections"]
                    + _sections(10)},
        _key("b"): {"answer": "nothing", "sections": memo(card("PACIFIC"))["sections"] + _sections(80)},
    }
    out = pooled_metrics(cases, answered, _key)
    assert out["key_fact_recall_pooled"] == round(2 / 3, 4) and out["key_fact_target_met"] == 0.0
    # f1: 2 of 2 points; f2: no drivers, direction matches: 1 of 1
    assert out["finding_recall_pooled"] == 1.0 and out["finding_target_met"] == 1.0
    assert out["over_word_budget"] == 1.0  # case b has 80 words against a budget of 50; the forecast case is not counted


def test_a_target_is_met_at_exactly_the_target():
    cases = [_case("a", facts=[(f"f{i}", 1000 + i * 10) for i in range(20)])]
    text = " ".join(f"{1000 + i * 10}" for i in range(17))  # 17 of 20 = 0.85
    out = pooled_metrics(cases, {_key("a"): {"answer": text}}, _key)
    assert out["key_fact_recall_pooled"] == 0.85 and out["key_fact_target_met"] == 1.0
    assert "finding_recall_pooled" not in out  # no case has an expected finding


def test_a_crashed_case_counts_its_points_and_facts_as_missed():
    cases = [_case("a", facts=[("x", 3860)], findings=[finding("f1", "SOUTHEAST")]), _case("crashed", findings=[finding("f2", "PACIFIC")])]
    out = pooled_metrics(cases, {_key("a"): {"answer": "3,860", "sections": memo(card("SOUTHEAST", supported=["promotion"]))["sections"]}}, _key)
    assert out["finding_recall_pooled"] == 0.5  # f1: 2 points of 2; f2: none of 2


# H4 word budget

def test_count_words_follows_brief_words_and_the_leader_view_is_the_servers_cut():
    sections = [
        {"number": "1", "title": "Bottom line", "text": "one two three", "prose": "four five",
         "kpis": [{"label": "L", "value": "10 pct", "detail": "a b", "direction": None}]},
        {"number": "3.1", "title": "Story", "text": "a b c\nChecked, in this order:\n- x y z", "prose": "", "detail": ["folded words here"],
         "card": {"headline": "h1 h2", "confidence": "High", "drivers_checked": ["x"], "territory": "S", "direction": "up",
                  "drivers_supported": [], "drivers_ruled_out": []}},
        {"number": "6", "title": "Appendix", "text": "Method words here that a leader never sees"},
    ]
    # §1: text 3, prose 2, tile 2 + 2; §3.1: text 11 (the checks list counts for the analyst), headline 2, the folded
    # detail is left out; §6: 8
    assert count_words(sections) == 9 + 13 + 8
    # the leader cut drops the checks list and the appendix: §1 as before, §3.1 text 3 and headline 2
    assert leader_words(sections) == 9 + 5


def test_brief_words_reports_both_views_and_the_budget(monkeypatch):
    monkeypatch.setitem(WORD_BUDGET, "analyst", 100)
    monkeypatch.setitem(WORD_BUDGET, "leader", 20)
    fb = brief_words(outputs={"sections": _sections(30)})
    assert fb.value == 30
    assert "leader view 30" in fb.rationale and "over budget: leader 30 over 20" in fb.rationale
    assert "analyst" not in fb.rationale.split("over budget:")[1]
    assert brief_words(outputs={"sections": _sections(10)}).rationale.endswith("budget 100 analyst, 20 leader.")
    assert brief_words(outputs={"sections": []}).value is None


def test_the_budget_is_measured_and_rounded_down_to_fifty():
    assert set(WORD_BUDGET) == {"analyst", "leader"}
    assert all(v > 0 for v in WORD_BUDGET.values())
    assert set(scorers.MEASURED_ANCHORS) and len(scorers.MEASURED_ANCHORS) == 5
    for view, at in (("analyst", 0), ("leader", 1)):
        widest = max(counts[at] for counts in scorers.MEASURED_ANCHORS.values())
        assert WORD_BUDGET[view] == widest


def test_the_budget_check_waits_for_the_reviewed_gate():
    assert not set(scorers.GATED_WHEN_REVIEWED) & set(scorers.GATED)  # report-only now (FR-006, FR-021)
    assert "over_word_budget" in scorers.GATED_WHEN_REVIEWED


def test_measured_anchor_counts_still_hold():
    """Recompute the five anchor briefs with the scripted engine and compare to MEASURED_ANCHORS."""
    from pharmagentics.tools import DEFAULT_DB
    if not DEFAULT_DB.exists():
        pytest.skip("build the DuckDB first")
    from eval.harness.systems import SYSTEMS

    cases = {c.story: c for c in load_cases("briefing") if c.story in scorers.MEASURED_ANCHORS}
    sut = SYSTEMS["briefing_scripted"](list(cases.values()))
    for story, case in cases.items():
        inputs = case.inputs()
        out = sut.predict(inputs["question"], **({"comparison": inputs["comparison"]} if inputs.get("comparison") else {}))
        assert (count_words(out["sections"]), leader_words(out["sections"])) == scorers.MEASURED_ANCHORS[story], story


# H5 insights

def _below_store(path):
    """Two scripted runs; the latest has C-1 below the key-fact target with two facts missing and one finding missed."""
    _store(str(path), {
        "P1": ("briefing_scripted", "g1", 1000, [(Q_DOLLAR, {"key_fact_recall": "1.0", "finding_recall": "1.0"}),
                                                   (Q_CONF, {"key_fact_recall": "0.5"})]),
        "P2": ("briefing_scripted", "g1", 2000, [
            (Q_DOLLAR, {"key_fact_recall": ("0.5", "1 of 4 must-state facts stated; missing: seg_pct, plan_trx, plain_fact"),
                        "finding_recall": ("0.5", "2 of 4 points over 2 findings; f1: missing supported access; f2: no down-direction card for PACIFIC (plan:P1)")}),
            (Q_CONF, {"key_fact_recall": ("0.9", None), "finding_recall": ("1.0", "4 of 4 points over 2 findings.")}),
            (Q_BRIEF, {"key_fact_recall": ("0.0", "0 of 1 must-state facts stated; missing: gone")})]),
    })


def test_missed_ids_are_read_from_the_rationale():
    assert missed_ids("key_fact_recall", ["1 of 3 must-state facts stated; missing: a, b"]) == ["a", "b"]
    assert missed_ids("key_fact_recall", ["3 of 3 must-state facts stated."]) == []
    assert missed_ids("finding_recall", ["2 of 4 points over 2 findings; f1: missing supported access; f2: should be withheld"]) == ["f1", "f2"]
    assert missed_ids("key_fact_recall", ["x; missing: a", "y; missing: a, c"]) == ["a", "c"]  # reruns: each id once


def test_insights_split_below_target_misses_by_needs(tmp_path):
    path = tmp_path / "below.db"
    _below_store(path)
    needs = {"C-1": {"facts": {"seg_pct": "segment_pct", "plan_trx": "plan_cut"}, "findings": {"f2": "plan_cut"}}}
    d = build([path], PAIRS, needs=needs)
    rows = {(r["case"], r["scorer"]): r for r in d["below_target"]}
    assert set(rows) == {("C-1", "key_fact_recall"), ("C-1", "finding_recall"), ("C-3", "key_fact_recall")}  # C-2 meets both
    facts = rows[("C-1", "key_fact_recall")]
    assert facts["needs"] == {"segment_pct": ["seg_pct"], "plan_cut": ["plan_trx"]} and facts["missed"] == ["plain_fact"]
    findings = rows[("C-1", "finding_recall")]
    assert findings["needs"] == {"plan_cut": ["f2"]} and findings["missed"] == ["f1"]
    assert rows[("C-3", "key_fact_recall")]["missed"] == ["gone"] and rows[("C-3", "key_fact_recall")]["needs"] == {}
    assert d["targets"] == TARGETS
    text = render_md(d)
    assert "## Below target" in text and "needs plan cut: plan_trx" in text and "needs segment percentage: seg_pct" in text
    assert "plain_fact" in text


def test_a_run_with_no_below_target_case_says_none(tmp_path):
    path = tmp_path / "ok.db"
    _store(str(path), {"P1": ("briefing_scripted", "g1", 1000, [(Q_DOLLAR, {"key_fact_recall": "0.9", "finding_recall": "0.95"})])})
    d = build([path], PAIRS)
    assert d["below_target"] == []
    assert "## Below target (latest run of each system)" in render_md(d)


def test_controls_are_not_held_to_the_targets(tmp_path):
    path = tmp_path / "ctl.db"
    _store(str(path), {"P1": ("naive_llm", "g1", 1000, [(Q_DOLLAR, {"key_fact_recall": "0.0"})])})
    assert build([path], PAIRS)["below_target"] == []


def test_the_export_carries_counts_only(tmp_path):
    path = tmp_path / "below.db"
    _below_store(path)
    needs = {"C-1": {"facts": {"seg_pct": "segment_pct", "plan_trx": "plan_cut"}, "findings": {}}}
    d = build([path], PAIRS, needs=needs)
    labels = {c: {"lane": "briefing", "story": "S", "persona": "P"} for c in ("C-1", "C-2", "C-3")}
    block = cases_block(d, labels)
    assert block["targets"] == TARGETS
    rows = {r["case"]: r for r in block["systems"][0]["rows"]}
    below = {b["scorer"]: b for b in rows["C-1"]["below"]}
    assert below["key_fact_recall"]["needs"] == {"plan_cut": 1, "segment_pct": 1} and below["key_fact_recall"]["missed"] == 1
    assert "below" not in rows["C-2"]  # at or over target: no key
    assert "seg_pct" not in str(block) and "plan_trx" not in str(block)  # no fact IDs leave the store
