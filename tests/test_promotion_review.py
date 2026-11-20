from pathlib import Path

import pytest

from pharmagentics.tools import DEFAULT_DB, Registry, promotion
from pharmagentics.tools.window import parse


QUESTIONS = [
    "Did my campaign move brand sales, and by how much?",
    "Which geographies, segments and channels responded, and which did not?",
    "Did the campaign reach the people it was meant to reach?",
    "Is the lift real, or was it access, a competitor or the season?",
    "How confident is the estimate, and when will we know more?",
    "Where should the next dollar go?",
]


@pytest.mark.parametrize("question", QUESTIONS)
def test_promotion_questions_cover_the_release_without_an_explicit_week(question):
    parsed = parse(question, "2024-10-14", "2026-10-05", briefing=True)
    assert parsed["promotion"] and not parsed["explicit_week"]
    assert (parsed["weeks"][0], parsed["weeks"][-1]) == ("2024-10-14", "2026-10-05")
    assert not parse("Is this freeing my team's time without risking our credibility?",
                     "2024-10-14", "2026-10-05", briefing=True)["promotion"]
    assert parse(question, "2024-10-14", "2026-10-05")["weeks"] == ["2026-10-05"]


def test_review_lapses_and_evidence(monkeypatch):
    if not DEFAULT_DB.exists():
        pytest.skip("Build the synthetic database first")
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "agents" / "brand-briefing"))
    from briefing_baseline.pipeline import answer

    reg = Registry()
    try:
        assert [event.territory for event in promotion.lapses(reg, None)] == ["GREAT_LAKES", "SOUTHEAST"]
    finally:
        reg.close()
    result = answer("Where should the next dollar go?")
    assert "503 to 730" in result["answer"]
    assert "915 against a release median of 1,652" in result["answer"]
    assert "This is an association" in result["answer"]
    assert "territory holdout" in result["answer"]
    assert "no spend data" in result["answer"]
    assert {claim["evidence_id"] for claim in result["claims"]} <= {e["id"] for e in result["evidence"]}
    assert all(result["answer"][c["start"]:c["end"]] == result["claims"][c["claim"]]["value"]
               for c in result["citations"])
