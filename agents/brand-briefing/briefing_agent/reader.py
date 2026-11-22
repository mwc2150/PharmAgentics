"""Step 1 of a Briefing question with a model (brief-008 FR-008; constitution B-II v1.1.0): the model reads a typed
question and proposes a scope with one tool call: the period, the territory, how many weeks to compare with and
whether it is a promotion question. It writes no prose and no number of its own. The API validates every field
against the release (api/service.py::validate_scope) and falls back to the code parser (tools/window.parse) on any
failure. The analyst then confirms or edits the form; nothing runs on a proposal. The eval harness never calls this.
"""
from __future__ import annotations

import asyncio
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
                  promotion_review: Annotated[bool, "True for a release-wide promotion question"] = False) -> str:
        """Record how the question should be read."""
        got.update(period_start=period_start, period_end=period_end, territory=territory,
                   comparison_weeks=comparison_weeks, promotion_review=promotion_review)
        return "Recorded. Stop."

    system = instructions(first=first, latest=latest, territories=territories, brand_id=brand_id)
    asyncio.run(_run_agent(spec, system, question, set_scope, seconds))
    if not got:
        raise ValueError("The model made no usable scope call.")
    return got
