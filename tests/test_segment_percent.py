"""brief-010 packet S: channel and specialty percent movers (FR-003, User Story 2). Runs the real scripted engine on
P4-Q2 (the Promotion review) and P4-Q1 (a territory story); no model.

A story names its largest channel and specialty movers in percent, at most two, a small cell never given a number.
The Promotion review states the same for each lapse, over the lapse and over its first four weeks, and flags a small
cell instead of quoting it bare. Golden values are compared with the golden SQL at the precision the brief prints them."""
from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.tools import DEFAULT_DB, Registry, splits, stages  # noqa: E402
from pharmagentics.tools.definition import Definition  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402

pytestmark = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build local/pharmagentics.duckdb first")

GL_FOUR = ["2026-02-02", "2026-02-09", "2026-02-16", "2026-02-23"]
GL_BEFORE = ["2026-01-05", "2026-01-12", "2026-01-19", "2026-01-26"]


def golden(story: str):
    from eval.harness.cases import load_cases

    return next(c for c in load_cases("briefing") if c.story == story)


def brief_for(story: str, **override) -> tuple[dict, dict]:
    from briefing_baseline import answer

    case = golden(story)
    definition = {**case.definition.payload(engine=True), **override}
    return answer(case.question, definition=definition), case.expectations()


@pytest.fixture(scope="module")
def review() -> tuple[dict, dict]:
    return brief_for("P4-Q2")


@pytest.fixture(scope="module")
def story() -> tuple[dict, dict]:
    return brief_for("P4-Q1")


@pytest.fixture
def reg():
    r = Registry()
    yield r
    r.close()


def movers_lines(env: dict) -> list[str]:
    return [x for x in env["answer"].splitlines() if "by channel:" in x.lower() and "cuts of the change" not in x.lower()]


def period(reg, weeks, baseline, **fields) -> stages.Period:
    ok = [r[0] for r in reg.rows("select distinct territory_id from raw.dim_territory")]
    return stages.Period(question="", first="2024-10-14", latest="2026-10-05", requested=weeks, baseline=baseline, weeks=weeks,
                         ok=ok, definition=Definition.coerce(fields or None, None))


# User Story 2: P4-Q2 states both golden facts ------------------------------------------------------------------

def test_p4_q2_states_both_must_state_facts(review):
    from eval.harness.scorers import key_fact_counts

    env, expected = review
    must = {f["id"] for f in expected["key_facts"] if f.get("needs") == "segment_pct"}
    assert must == {"gl_cash_change_pct", "se_commercial_change_pct"}
    stated, missing, total = key_fact_counts(env, expected)
    assert not must & set(missing), missing
    assert stated == total == 2


@pytest.mark.parametrize("fact_id, printed", [("gl_cash_change_pct", "Cash down 31.4% (small cell: noisy)"),
                                              ("se_commercial_change_pct", "Commercial down 30.1%")])
def test_the_printed_value_equals_the_golden_sql_at_one_decimal(review, reg, fact_id, printed):
    """Great Lakes cash on 2026-02-02 to 02-23 against 2026-01-05 to 01-26, Southeast commercial on 2026-08-03 to 08-31
    against July: what the review prints is the golden SQL's value (exact -31.4 and -30.1)."""
    env, expected = review
    sql = next(f.sql for f in golden("P4-Q2").facts if f.id == fact_id)  # the golden query, run on the governed view
    exact = reg.scalar(sql)
    assert exact == pytest.approx(next(f["exact"] for f in expected["key_facts"] if f["id"] == fact_id))
    assert printed.split(" down ")[1].split("%")[0] == f"{abs(exact):.1f}"
    assert printed in env["answer"]


def test_the_review_reads_the_lapse_and_its_first_four_weeks(review):
    env, _ = review
    lines = movers_lines(env)
    assert len(lines) == 2 and all(x.startswith("Over the lapse, by channel:") and "In its first four weeks, by channel:" in x for x in lines)
    assert "Cash down 29.7% (small cell: noisy)" in lines[0] and "Cash down 31.4% (small cell: noisy)" in lines[0]
    assert "Commercial down 30.1%" in lines[1] and "Commercial down 29.0%" in lines[1]


def test_the_review_never_quotes_a_small_cell_without_its_flag(review):
    env, _ = review
    for line in movers_lines(env):
        for cell in re.findall(r"Cash down \d+\.\d%( \(small cell: noisy\))?", line):
            assert cell == " (small cell: noisy)", line


def test_the_movers_in_the_review_are_claims_with_a_grain_and_a_cut(review):
    env, _ = review
    by_id = {e["id"]: e for e in env["evidence"]}
    claims = [c for c in env["claims"] if by_id[c["evidence_id"]]["tool"] == "get_segment_metric"]
    assert {c["labels"]["grain"] for c in claims} == {"channel", "specialty"}
    for c in claims:
        assert c["labels"]["cut"].startswith(c["labels"]["grain"] + ":") and c["value"].endswith("%")
    cuts = {c["labels"]["cut"] for c in claims}
    assert {"channel:CASH", "channel:COMMERCIAL", "specialty:ENDOCRINOLOGY"} <= cuts


def test_no_digit_stands_outside_a_claim_token_in_the_movers(review):
    env, _ = review
    template = re.sub(r"\d+(\.\d+)?%", "{c0}", " ".join(movers_lines(env)))
    assert not digits_outside_tokens(template)


# S1: a story names at most two movers a grain; a small cell is named, never quoted ----------------------------------

def test_a_story_names_at_most_two_channel_and_specialty_movers_in_percent(story):
    env, _ = story
    line = next(x for x in env["answer"].splitlines() if x.startswith("By channel:"))
    assert line == ("By channel: Medicaid down 24.9%, Commercial down 16.2%, Cash too small to quote; "
                    "by specialty: Internal medicine down 21.7%, Primary care down 19.7%.")
    assert line.count("%") == 4


def test_the_story_line_comes_after_the_head_and_before_the_checks(story):
    env, _ = story
    lines = env["answer"].splitlines()
    at = next(i for i, x in enumerate(lines) if x.startswith("Story one:"))
    assert lines[at + 1].startswith("By channel:") and lines[at + 2] == "Checked, in this order:"


def test_a_small_cell_is_withheld_in_a_story_and_flagged_in_the_review(reg):
    """Cash in Great Lakes is 48 TRx a week before and 33 during: a small cell, named with no number in a story."""
    p = period(reg, GL_FOUR, GL_BEFORE)
    assert reg.render(splits.mover_text(reg, p, "GREAT_LAKES", "channel")) == "Medicaid down 24.6%, Commercial down 14.4%, Cash too small to quote"
    assert not [c for c in reg.claims if c["labels"].get("cut") == "channel:CASH"]
    assert (reg.render(splits.mover_text(reg, p, "GREAT_LAKES", "channel", quote_small=True))
            == "Cash down 31.4% (small cell: noisy), Medicaid down 24.6%")


def test_the_story_claims_carry_the_channel_and_specialty_labels(story):
    env, _ = story
    cuts = {c["labels"]["cut"] for c in env["claims"] if c["labels"].get("grain") in ("channel", "specialty")}
    assert {"channel:MEDICAID", "channel:COMMERCIAL", "specialty:INTERNAL_MEDICINE", "specialty:PRIMARY_CARE"} <= cuts


def test_the_movers_are_the_largest_absolute_changes_in_order(reg):
    p = period(reg, GL_FOUR, GL_BEFORE)
    assert [c["cut"] for c in splits._cells(reg, p, "GREAT_LAKES", "specialty")[:3]] == ["CARDIOLOGY", "INTERNAL_MEDICINE", "PRIMARY_CARE"]
    assert reg.render(splits.mover_text(reg, p, "GREAT_LAKES", "specialty")) == "Cardiology down 20.0%, Internal medicine down 19.9%"


# a grain without channel or specialty shows none -------------------------------------------------------------------

@pytest.mark.parametrize("grain", [["national", "territory", "plan", "specialty"], ["national", "territory", "plan", "channel"],
                                   ["national", "territory", "plan"]])
def test_a_grain_without_channel_or_specialty_names_none_of_them(reg, grain):
    p = period(reg, GL_FOUR, GL_BEFORE, grain=grain)
    text = splits.segment_line(reg, p, "GREAT_LAKES")
    assert ("by channel" in text.lower()) == ("channel" in grain) and ("by specialty" in text.lower()) == ("specialty" in grain)


def test_a_brief_without_either_grain_has_no_mover_line_and_no_segment_claim():
    env, _ = brief_for("P4-Q1", grain=["national", "territory", "plan"])
    assert not movers_lines(env)
    assert not [c for c in env["claims"] if c["labels"].get("grain") in ("channel", "specialty")]


def test_the_review_honours_the_grain():
    env, _ = brief_for("P4-Q2", grain=["national", "territory", "plan"])
    assert not movers_lines(env) and "Over the lapse" not in env["answer"]


# nothing moved, or nothing reportable: no sentence -----------------------------------------------------------------

def test_nothing_outside_the_flat_band_gives_an_empty_line(reg):
    p = period(reg, GL_BEFORE[:2], GL_BEFORE[:2])
    assert splits.segment_line(reg, p, "GREAT_LAKES") == "" and not reg.claims


def test_a_territory_the_gate_withholds_names_no_movers(reg):
    p = replace(period(reg, GL_FOUR[:1], GL_BEFORE[-1:]), ok=[])
    assert splits.segment_line(reg, p, "GREAT_LAKES") == ""


def test_a_story_without_a_mover_line_reads_as_before(monkeypatch):
    """With no line built the story is the head and the checks only: no blank, nothing moved."""
    from briefing_baseline import answer

    monkeypatch.setattr(splits, "segment_line", lambda *a, **k: "")
    case = golden("P4-Q1")
    env = answer(case.question, definition=case.definition.payload(engine=True))
    lines = env["answer"].splitlines()
    at = next(i for i, x in enumerate(lines) if x.startswith("Story one:"))
    assert lines[at + 1] == "Checked, in this order:" and "By channel:" not in env["answer"]


# S3: the analyst view stays inside the word budget -----------------------------------------------------------------

def test_the_analyst_view_stays_inside_the_word_budget(review, story):
    from eval.harness.scorers import WORD_BUDGET, count_words

    for env, _ in (review, story):
        assert count_words(env["sections"]) <= WORD_BUDGET["analyst"]
