"""Step 1 of a Briefing question with a model (brief-008 FR-008; constitution B-II v1.1.0): the model reads a typed
question and proposes a scope with one tool call: the period, the territory, how many weeks to compare with and
whether it is a promotion question. It writes no prose and no number of its own. The API validates every field
against the release (api/service.py::validate_scope) and falls back to the code parser (tools/window.parse) on any
failure. The analyst then confirms or edits the form; nothing runs on a proposal. The eval harness never calls this
for a live proposal; it asks for one to score (`scope_proposal` below, brief-008 FR-017), and the brief never
follows it.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Callable

PROMPT = Path(__file__).resolve().parent / "prompts" / "scope_reader.md"


def instructions(*, first: str, latest: str, territories: list[str], brand_id: str) -> str:
    text = PROMPT.read_text(encoding="utf-8")
    for key, value in {"brand": brand_id, "first": first, "latest": latest, "territories": ", ".join(territories)}.items():
        text = text.replace("{" + key + "}", value)  # not str.format: the prompt file may hold other braces
    return text


async def _run_agent(spec: str, system: str, question: str, set_scope: Callable[..., str], seconds: float) -> None:
    from agent_framework import Agent, tool

    from pharmagentics.llm import chat_client, chat_options

    agent = Agent(client=chat_client(spec), name="scope_reader", instructions=system, tools=[tool(set_scope)],
                  default_options=chat_options(spec))
    await asyncio.wait_for(agent.run("Question: " + question), timeout=seconds)


def propose(question: str, *, spec: str, first: str, latest: str, territories: list[str], brand_id: str = "BXA",
            seconds: float = 25.0) -> dict:
    """The model's raw proposal: period_start, period_end, territory, comparison_weeks, promotion_review. Unchecked.
    Raises when the model makes no tool call; the caller treats any exception as "use the rules"."""
    got: dict = {}

    def set_scope(period_start: Annotated[str, "YYYY-MM-DD"], period_end: Annotated[str, "YYYY-MM-DD"],
                  territory: Annotated[str, "A territory id, or empty"] = "",
                  comparison_weeks: Annotated[int, "Whole weeks to compare with, 1 to 13"] = 4,
                  promotion_review: Annotated[bool, "True for a release-wide promotion question"] = False,
                  comparison_kind: Annotated[str, "previous, or last_year for the same weeks a year earlier"] = "previous") -> str:
        """Record how the question should be read."""
        got.update(period_start=period_start, period_end=period_end, territory=territory,
                   comparison_weeks=comparison_weeks, promotion_review=promotion_review, comparison_kind=comparison_kind)
        return "Recorded. Stop."

    system = instructions(first=first, latest=latest, territories=territories, brand_id=brand_id)
    asyncio.run(_run_agent(spec, system, question, set_scope, seconds))
    if not got:
        raise ValueError("The model made no usable scope call.")
    return got


# --- The scope an agent proposes for scoring (brief-008 FR-017) -----------------------------------------------
_PREFIX = re.compile(r"^\s*(?:Weeks? of|Brief of)\s+(\d{4}-\d{2}-\d{2})(?:\s*(?:to|and)\s*(\d{4}-\d{2}-\d{2}))?[^:]*:\s*", re.I)
DEFAULT_COMPARISON_WEEKS = 4


def split_prefix(question: str) -> tuple[str, str | None]:
    """The question text after a code-written "Week of D[, Territory]:" prefix, and the prefix's last week (None when
    the question has no such prefix). The prefix states the scope; the text after it is what a person typed."""
    m = _PREFIX.match(question or "")
    text = (question[m.end():] if m else question or "").strip()
    return (text or (question or "").strip()), (m.group(2) or m.group(1)) if m else None


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _weeks(start: str, end: str) -> list[str]:
    """Calendar dates to Monday weeks: under a week is the week holding it; longer is every Monday inside."""
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if b < a:
        raise ValueError("The last week comes before the first week.")
    if (b - a).days < 7:
        return [_monday(a).isoformat()]
    a, b = a + timedelta(days=(7 - a.weekday()) % 7), _monday(b)
    return [(a + timedelta(weeks=i)).isoformat() for i in range((b - a).days // 7 + 1)] if a <= b else []


def to_proposal(raw: dict, territories: list[str]) -> dict:
    """The reader's raw call as the record the scorer reads: {territory, week_start, week_end, comparison, intent}.
    Territory IDs upper-case ("ALL" for no territory), ISO Monday dates, comparison None for the default four
    weeks, else {"kind": "previous", "weeks": N} or {"kind": "last_year"}; intent "brief" or "promotion_review".
    Raises ValueError for anything unusable, so a bad reading records nothing."""
    weeks = _weeks(str(raw.get("period_start", "")), str(raw.get("period_end", "")))
    if not weeks:
        raise ValueError("The proposed weeks hold no Monday.")
    territory = str(raw.get("territory") or "").strip().upper().replace(" ", "_").replace("-", "_")
    if territory in ("", "NATIONAL", "ALL"):
        territory = "ALL"
    elif territory not in territories:
        raise ValueError("The proposed territory is not in the release.")
    count = raw.get("comparison_weeks", DEFAULT_COMPARISON_WEEKS)
    count = DEFAULT_COMPARISON_WEEKS if count is None else count
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 13:
        raise ValueError("The comparison must be a whole number of weeks from 1 to 13.")
    kind = str(raw.get("comparison_kind") or "previous").strip().lower()
    if kind not in ("previous", "last_year"):
        raise ValueError("The comparison kind is not usable.")
    comparison = {"kind": "last_year"} if kind == "last_year" else (
        None if count == DEFAULT_COMPARISON_WEEKS else {"kind": "previous", "weeks": count})
    promotion = raw.get("promotion_review", False)
    if not isinstance(promotion, bool):
        raise ValueError("The promotion flag is not usable.")
    return {"territory": territory, "week_start": weeks[0], "week_end": weeks[-1], "comparison": comparison,
            "intent": "promotion_review" if promotion else "brief"}


def scope_proposal(question: str, *, spec: str, first: str, latest: str, territories: list[str],
                   seconds: float = 25.0, ask: Callable[..., dict] | None = None) -> dict:
    """What the model reads from the question TEXT (the code-written prefix is cut off), with the prefix's week as
    "today" so "this week" resolves. A real test of inference: the brief still runs on the prefix scope. Raises on
    any failure; the caller records nothing then. `ask` replaces the model call in tests."""
    text, week = split_prefix(question)
    raw = (ask or propose)(text, spec=spec, first=first, latest=week or latest, territories=territories, seconds=seconds)
    return to_proposal(raw, territories)
