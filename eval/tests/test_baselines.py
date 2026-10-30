"""The scripted baselines: anchor behaviours, and the invariants that must hold on all 42 cases."""
import inspect

import pytest

from eval.harness.cases import load_cases
from eval.harness.paths import DATABASE
from eval.harness.scorers import DETERMINISTIC, EVIDENCE
from eval.harness.systems import SYSTEMS

pytestmark = pytest.mark.skipif(not DATABASE.exists(), reason="build the DuckDB database first")
CASES = load_cases()
BY_STORY = {c.story: c for c in CASES}


@pytest.fixture(scope="module")
def systems():
    return {n: SYSTEMS[n](CASES) for n in ("briefing_scripted", "forecast_scripted")}


def run(systems, name, story):
    return systems[name].predict(BY_STORY[story].question)


def scored(s, **kwargs):
    wanted = inspect.signature(getattr(s, "_original_func", s)).parameters
    return s(**{k: v for k, v in kwargs.items() if k in wanted})


def test_incomplete_feed_names_the_cut_and_its_reasons(systems):
    text = run(systems, "briefing_scripted", "P1-Q2")["answer"]
    assert "New England" in text and "not reportable" in text and "missing keys" in text
    assert "0.656" in text and "7 of 8" in text


def test_quiet_week_is_routine_with_no_story(systems):
    text = run(systems, "briefing_scripted", "P1-Q3")["answer"]
    assert "Routine week" in text and "Story" not in text and "surged" not in text


def test_supply_week_names_supply_at_high_confidence(systems):
    text = run(systems, "briefing_scripted", "P1-Q5")["answer"]
    assert "Supply: supported" in text and "Confidence: High. Leading driver: supply" in text


def test_access_change_is_found_without_naming_the_territory(systems):
    text = run(systems, "briefing_scripted", "P2-Q4")["answer"]
    assert "Mid-Atlantic" in text and "Access: supported" in text and "Leading driver: access" in text


def test_a_gap_with_no_driver_abstains_and_names_no_cause(systems):
    out = run(systems, "briefing_scripted", "P2-Q3")
    assert out["abstained"] and "Unresolved, investigate next" in out["answer"]
    assert "because of Metacora" not in out["answer"]


def test_holiday_weeks_are_a_calendar_effect_not_a_story(systems):
    text = run(systems, "briefing_scripted", "P3-Q2")["answer"]
    assert "Calendar effect" in text and "Story" not in text


def test_restatement_is_disclosed_with_old_and_new_values(systems):
    text = run(systems, "briefing_scripted", "P2-Q1")["answer"]
    assert "692" in text and "742" in text and "data artifact" in text


def test_provisional_actual_pauses_the_forecast_case(systems):
    out = run(systems, "forecast_scripted", "CA-Q1")
    assert out["abstained"] and "provisional" in out["answer"] and "names no driver" in out["answer"]


def test_forecast_attribution_reconciles_and_keeps_the_residual(systems):
    out = run(systems, "forecast_scripted", "BM-Q3")
    assert "-1,036" in out["answer"] and "Unexplained residual" in out["answer"]
    values = {c["evidence_id"]: c["value"] for c in out["claims"]}
    parts = [e for e in out["evidence"] if e["tool"] == "reconcile_attribution"]
    assert len(parts) >= 2 and abs(sum(e["result"] for e in parts) - (-1036)) < 1  # contributions + residual = miss


@pytest.mark.parametrize("name, cases", [("briefing_scripted", "briefing"), ("forecast_scripted", "forecast")])
def test_every_case_runs_and_every_claim_checks_out(systems, name, cases):
    """The gated invariants: no crash, every claim reconciles, traces and links, and no banned wording."""
    for c in (x for x in CASES if x.lane == cases):
        out = systems[name].predict(c.question)
        for s in EVIDENCE + [d for d in DETERMINISTIC if d.name in ("must_not_say", "governed_terms", "no_individual_rep")]:
            fb = scored(s, outputs=out, expectations=c.expectations())
            assert fb.value in (True, 1.0), f"{c.story} {s.name}: {fb.rationale}"
