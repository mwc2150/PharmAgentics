"""brief-008 FR-017: the agent records the scope a model reads from the question text, for core-011's scope_match.

No model call: the reader's tool call is stubbed. The proposal is a record for scoring and never changes the brief."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from briefing_agent import reader  # noqa: E402

TERRITORIES = ["NEW_ENGLAND", "PACIFIC", "SOUTHEAST", "GREAT_LAKES"]
RAW = {"period_start": "2026-08-24", "period_end": "2026-08-24", "territory": "southeast", "comparison_weeks": 4,
       "promotion_review": False, "comparison_kind": "previous"}


@pytest.mark.parametrize("question, text, week", [
    ("Week of 2026-08-24 in Southeast: What changed this week?", "What changed this week?", "2026-08-24"),
    ("Weeks of 2025-08-04 to 2025-10-27, Mid-Atlantic: Where did this come from?", "Where did this come from?", "2025-10-27"),
    ("Weeks of 2025-12-22 and 2025-12-29: Compare with last year.", "Compare with last year.", "2025-12-29"),
    ("Brief of 2026-07-13: Can I quote these?", "Can I quote these?", "2026-07-13"),
    ("Week of 2026-04-06, today's snapshot: Is it real?", "Is it real?", "2026-04-06"),
    ("Where should the next dollar go?", "Where should the next dollar go?", None),
])
def test_the_prefix_is_cut_and_its_last_week_returned(question, text, week):
    assert reader.split_prefix(question) == (text, week)


def test_the_proposal_has_the_fields_and_formats_the_scorer_reads():
    assert reader.to_proposal(RAW, TERRITORIES) == {"territory": "SOUTHEAST", "week_start": "2026-08-24", "week_end": "2026-08-24",
                                                    "comparison": None, "intent": "brief"}
    got = reader.to_proposal({**RAW, "period_start": "2025-08-04", "period_end": "2025-10-27", "territory": "", "comparison_weeks": 8,
                              "promotion_review": True}, TERRITORIES)
    assert got == {"territory": "ALL", "week_start": "2025-08-04", "week_end": "2025-10-27",
                   "comparison": {"kind": "previous", "weeks": 8}, "intent": "promotion_review"}
    assert reader.to_proposal({**RAW, "comparison_kind": "last_year"}, TERRITORIES)["comparison"] == {"kind": "last_year"}
    assert reader.to_proposal({**RAW, "period_start": "2026-08-26", "period_end": "2026-08-27"}, TERRITORIES)["week_start"] == "2026-08-24"


@pytest.mark.parametrize("bad", [{"territory": "ATLANTIS"}, {"period_start": "soon"}, {"comparison_weeks": 20},
                                 {"comparison_weeks": True}, {"comparison_kind": "custom"}, {"promotion_review": "yes"},
                                 {"period_start": "2026-09-01", "period_end": "2026-08-01"}])
def test_an_unusable_reading_raises(bad):
    with pytest.raises(ValueError):
        reader.to_proposal({**RAW, **bad}, TERRITORIES)


def test_the_reader_sees_the_text_after_the_prefix_and_the_prefix_week_as_today():
    seen = {}

    def ask(text, **kw):
        seen.update(text=text, **kw)
        return RAW

    got = reader.scope_proposal("Week of 2026-08-24 in Southeast: What changed this week?", spec="anthropic:m", first="2025-01-06",
                                latest="2026-11-16", territories=TERRITORIES, ask=ask)
    assert seen["text"] == "What changed this week?" and seen["latest"] == "2026-08-24" and seen["first"] == "2025-01-06"
    assert got["territory"] == "SOUTHEAST"
    reader.scope_proposal("Where should the next dollar go?", spec="anthropic:m", first="a", latest="2026-11-16",
                          territories=TERRITORIES, ask=ask)
    assert seen["text"] == "Where should the next dollar go?" and seen["latest"] == "2026-11-16"  # no prefix: the release's latest week


def _agent(monkeypatch, ask):
    import briefing_agent as agent
    from pharmagentics.api import service

    if not service.DB.is_file():
        pytest.skip("Build local/pharmagentics.duckdb first")

    async def triage(question, spec, log, comparison=None, definition=None):
        return {"manager_order": []}

    async def run(question, plan, order, spec, reviewed, log):
        return {"envelope": {"answer": "brief", "trajectory": {"llm_calls": 3, "model": spec}}}

    monkeypatch.setattr(agent, "_triage", triage)
    monkeypatch.setattr(agent, "_run", run)
    monkeypatch.setattr(reader, "propose", ask)
    return agent


def test_the_envelope_records_the_proposal_and_one_more_llm_call(monkeypatch):
    seen = []

    def ask(text, **kw):
        seen.append((text, kw["latest"]))
        return RAW

    agent = _agent(monkeypatch, ask)
    env = agent.answer("Week of 2026-08-24 in Southeast: What changed this week?", "ollama:x")
    assert env["trajectory"]["scope_proposal"] == {"territory": "SOUTHEAST", "week_start": "2026-08-24", "week_end": "2026-08-24",
                                                   "comparison": None, "intent": "brief"}
    assert env["answer"] == "brief" and len(seen) == 1 and seen[0] == ("What changed this week?", "2026-08-24")
    assert env["trajectory"]["llm_calls"] == 1  # the stub run made none of its own; the log counts the reader's call


def test_a_reader_that_fails_records_nothing(monkeypatch):
    def ask(text, **kw):
        raise ValueError("The model made no usable scope call.")

    agent = _agent(monkeypatch, ask)
    env = agent.answer("Week of 2026-08-24 in Southeast: What changed this week?", "ollama:x")
    assert "scope_proposal" not in env["trajectory"] and env["answer"] == "brief"
