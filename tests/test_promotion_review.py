import re
from pathlib import Path

import pytest

from pharmagentics.tools import DEFAULT_DB, Registry, promotion, queries as q
from pharmagentics.tools.window import parse


QUESTIONS = [
    "Did my campaign move brand sales, and by how much?",
    "Which geographies, segments and channels responded, and which did not?",
    "Did the campaign reach the people it was meant to reach?",
    "Is the lift real, or was it access, a competitor or the season?",
    "Where should the next dollar go?",
]
CONFIDENCE_QUESTION = "How confident is the estimate, and when will we know more?"
NOT_PROMOTION = [  # brief-008 FR-010 and the UI's suggestion lists: none of these is a Promotion review
    CONFIDENCE_QUESTION,
    "How confident are we, and what is unexplained?",
    "What should be checked next, and by whom?",
    "Is this freeing my team's time without risking our credibility?",
]


@pytest.mark.parametrize("question", QUESTIONS)
def test_promotion_questions_cover_the_release_without_an_explicit_week(question):
    parsed = parse(question, "2024-10-14", "2026-10-05", briefing=True)
    assert parsed["promotion"] and not parsed["explicit_week"]
    assert (parsed["weeks"][0], parsed["weeks"][-1]) == ("2024-10-14", "2026-10-05")
    assert parse(question, "2024-10-14", "2026-10-05")["weeks"] == ["2026-10-05"]


@pytest.mark.parametrize("question", NOT_PROMOTION)
def test_confidence_and_other_questions_are_not_promotion_questions(question):
    parsed = parse(question, "2024-10-14", "2026-10-05", briefing=True)
    assert not parsed["promotion"]
    assert parsed["weeks"] == ["2026-10-05"]  # the latest closed week, as any other brief


def test_dollar_questions_are_told_apart_by_code():
    assert promotion.is_dollar_question("Where should the next dollar go?")
    assert promotion.is_dollar_question("Promotion review in Southeast: Where should the next dollar go?")
    assert promotion.is_dollar_question("What is the ROI of the Q3 campaign?")
    assert not promotion.is_dollar_question("Did the campaign reach the people it was meant to reach?")
    assert not promotion.is_dollar_question("Promotion review in Southeast: What changed?")


def _answer(question, monkeypatch):
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "agents" / "brand-briefing"))
    from briefing_baseline.pipeline import answer

    return answer(question)


def _section(result, number):
    return next(s for s in result["sections"] if s["number"] == number)


def test_review_lapses_and_evidence(monkeypatch):
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    reg = Registry()
    try:
        assert [event.territory for event in promotion.lapses(reg, None)] == ["GREAT_LAKES", "SOUTHEAST"]
    finally:
        reg.close()
    result = _answer("Where should the next dollar go?", monkeypatch)
    assert "503 to 730" in result["answer"]
    assert "915 against a release median of 1,652" in result["answer"]
    assert "This is an association" in result["answer"]
    assert "territory holdout" in result["answer"]
    assert "no spend data" in result["answer"]
    assert {claim["evidence_id"] for claim in result["claims"]} <= {e["id"] for e in result["evidence"]}
    assert all(result["answer"][c["start"]:c["end"]] == result["claims"][c["claim"]]["value"]
               for c in result["citations"])


def test_dollar_and_reach_questions_get_different_bottom_lines(monkeypatch):
    dollar = _section(_answer("Where should the next dollar go?", monkeypatch), "1")["text"]
    reach = _section(_answer("Did the campaign reach the people it was meant to reach?", monkeypatch), "1")["text"]
    assert dollar != reach
    assert "cannot say where the next dollar should go" in dollar
    assert "no spend data" in dollar and "rank channels" in dollar
    assert "moved together (correlation 0.80)" in dollar
    assert "116 to 177 a week below" in dollar and "coverage backfill with sales operations" in dollar
    assert "dollar" not in reach and "which people were reached" in reach


def test_the_review_is_blocks_and_paragraphs(monkeypatch):
    result = _answer("Where should the next dollar go?", monkeypatch)
    text = result["answer"]
    assert not re.search(r"\b1 weeks\b|\b0 weeks\b|SYN_|[A-Z]{2,}_[A-Z]{2,}|(?<![\w.])-\d+\.\d+", text)
    assert "longest push 0" not in text
    sections = {s["number"]: s for s in result["sections"]}
    tiles = sections["1"]["kpis"]
    assert [t["label"] for t in tiles] == ["Territories with a lapse", "Longest lapse, in weeks", "Push threshold"]
    assert [t["value"] for t in tiles] == ["2", "10", "1.50"]
    table = sections["2"]["territory_table"]
    assert table["columns"][0] == "Territory" and len(table["rows"]) == 8
    assert all(len(r["cells"]) == len(table["columns"]) == len(r["cell_citations"]) for r in table["rows"])
    assert table["rows"][0]["cells"][0] == "Great Lakes" and table["rows"][0]["cells"][3] == "none"
    assert len(sections["2"]["text"].splitlines()) <= 3  # the table and the folded detail carry the eight territories
    assert "Great Lakes: aggregated calls peaked" in sections["2"]["detail"]
    stories = [s for n, s in sections.items() if n.startswith("3.")]
    assert [s["card"]["confidence"] for s in stories] == ["Medium", "Medium"]
    assert stories[0]["card"]["headline"].startswith("Great Lakes: aggregated calls fell from 49 to 21 a week")
    assert "Medicare Part D plan one: down 25 TRx a week" in stories[0]["detail"]
    assert "Primary care: down 53 TRx a week" in stories[0]["detail"] and "Cash: down 14" in stories[0]["detail"]
    assert all(len(s["text"].splitlines()) <= 3 for s in stories)


def test_the_assumptions_state_the_scope_and_the_lapse_comparison(monkeypatch):
    result = _answer("Did the campaign reach the people it was meant to reach?", monkeypatch)
    appendix = _section(result, "6")["text"]
    assert "no earlier weeks" not in result["answer"]
    items = [x for x in appendix.splitlines() if x.startswith("- ")]
    assert 3 <= len(items) <= 5
    assert any(x.startswith("- Review scope: No week was given. The Promotion review covers the full release") for x in items)
    assert any(x.startswith("- Lapse:") and "four weeks before the lapse" in x and "0.70" in x for x in items)


def test_the_confidence_question_gets_a_brief_with_confidence_not_a_review(monkeypatch):
    result = _answer(CONFIDENCE_QUESTION, monkeypatch)
    assert "Promotion review" not in result["answer"]
    assert "Confidence:" in result["answer"]
    assert "Re-read: re-run this brief four weeks after any change" in result["answer"]


def test_lapse_count_query_matches_the_lapse_rule():
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    reg = Registry()
    try:
        found = promotion.lapses(reg, None)
        sql = promotion._runs_sql(None) + "select territory_id, first_week::varchar, last_week::varchar from runs order by 2, 1"
        assert [(e.territory, e.start, e.end) for e in found] == [tuple(r) for r in reg.rows(sql)]
        _, k = promotion._lapse_kpis(reg, None, found, "{c1}")
        assert k["w"] == max(len(q.mondays(e.start, e.end)) for e in found)
    finally:
        reg.close()
