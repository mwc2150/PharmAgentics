"""Assumptions first: every week a Briefing claim reads is a week the brief states.

The brief prints its period and comparison weeks (the Assumptions block, §2's scope line, chart captions); the driver
checks may also read one or two weeks earlier, which the Assumptions state as the tested lags. A claim whose SQL reads
any other week used a window the reader cannot see (mentor review 2026-11-20, item 2.1: a promotion verdict computed
on an unstated thirteen-week window that held a lapse). Runs the scripted engine on every Briefing golden case.
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAY = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
SPAN = re.compile(r"(\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})")
LAUNCH = re.compile(r"launch(?:ed)?(?: on)? (\d{4}-\d{2}-\d{2})")
LAGS = (1, 2)  # memo.assumptions: "the checks evaluate the same week and delays of one and two weeks"
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "eight": 8, "thirteen": 13}


def _shift(day: str, weeks: int = 0, days: int = 0) -> str:
    return (date.fromisoformat(day) + timedelta(weeks=weeks, days=days)).isoformat()


def _mondays(start: str, end: str) -> set[str]:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return {(a + timedelta(weeks=i)).isoformat() for i in range((b - a).days // 7 + 1)}


def stated_weeks(text: str) -> set[str]:
    """The weeks a reader can see the brief uses: every printed date and every week inside a printed range, the tested
    lags before each, each week's last day (a publication cut-off), the weeks before a printed launch the brief names
    ("the four weeks before launch") and, when the brief says so, the same weeks a year earlier."""
    weeks = set(DAY.findall(text))
    for start, end in SPAN.findall(text):
        weeks |= _mondays(start, end)
    for launched in LAUNCH.findall(text):
        for n in (WORDS[m] for m in re.findall(r"\b(\w+) weeks before launch", text) if m in WORDS):
            weeks |= {_shift(launched, -i) for i in range(1, n + 1)}
    weeks |= {_shift(w, -lag) for w in weeks for lag in LAGS}
    if "a year earlier" in text or "last year" in text:
        weeks |= {_shift(w, -52) for w in weeks}
    return weeks | {_shift(w, days=6) for w in weeks}


def _release() -> tuple[str, str]:
    import duckdb
    from eval.harness.paths import DATABASE
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        return con.execute("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar").fetchone()


def unstated(envelope: dict) -> dict[str, set[str]]:
    """Claim tool -> the weeks of the release its SQL reads that the brief does not state. Dates outside the release
    are constants, not weeks read (promotion.lapses numbers weeks from 2000-01-03)."""
    allowed, (first, last) = stated_weeks(envelope["answer"]), _release()
    queries = {e["id"]: e for e in envelope.get("evidence", [])}
    out: dict[str, set[str]] = {}
    for claim in envelope.get("claims", []):
        ev = queries.get(claim.get("evidence_id"))
        if not ev:
            continue
        extra = {d for d in DAY.findall(ev.get("query") or "") if first <= d <= _shift(last, days=6) and d not in allowed}
        if extra:
            out.setdefault(ev.get("tool") or "?", set()).update(extra)
    return out


def _cases():
    sys.path.insert(0, str(ROOT))
    from eval.harness.cases import load_cases
    return [c for c in load_cases(lane="briefing") if getattr(c, "brand", "BXA") == "BXA"]


@pytest.fixture(scope="module")
def scripted():
    from eval.harness.systems import BriefingScripted
    return BriefingScripted([])


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c.story)
def test_claims_read_only_stated_weeks(case, scripted):
    from eval.harness.systems import briefing_question, definition_option
    inputs = case.inputs()
    sent = briefing_question(inputs["question"], inputs.get("intent") or "brief")
    options = {"comparison": inputs["comparison"]} if inputs.get("comparison") else {}
    out = scripted.predict(sent, **options, **definition_option(scripted.predict, inputs.get("definition")))
    assert not unstated(out), f"{case.story} reads weeks the brief does not state: {unstated(out)}"


def test_the_mentor_southeast_week():
    """2026-11-20 review 2.1: the week of Oct 5, 2026 in Southeast. The calls are compared over the stated weeks, the
    lapse behind the comparison is named, and §1 says the change is within Southeast's normal range."""
    sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))
    from briefing_baseline.pipeline import answer
    out = answer("Week of 2026-10-05 in Southeast: How did BXA do?")  # ISO: the reader does not parse "Oct 5, 2026" yet
    text = out["answer"]
    assert not unstated(out)
    # Stricter than `unstated` (the chart's printed range would cover a longer window): the calls read only the period
    # and the comparison weeks Sep 7-28, each up to two weeks earlier.
    allowed = {_shift(w, -lag) for w in _mondays("2026-09-07", "2026-10-05") for lag in (0, *LAGS)}
    queries = {e["id"]: e for e in out["evidence"]}
    read = {d for c in out["claims"] if (e := queries.get(c.get("evidence_id"))) and e.get("tool") == "lookup_promo"
            for d in DAY.findall(e.get("query") or "") if d > "2020-01-01"}
    assert read and read <= allowed, sorted(read - allowed)
    assert "reference weeks" not in text
    assert "recovery after the promotion lapse of 2026-08-03 to 2026-08-31" in text
    assert "within its normal range; reported because the question asks about it" in text
    assert "Metacora's local share: 2026-07-06 to 2026-09-28." in text  # the competitor check's weeks, stated
