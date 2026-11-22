"""brief-009: the agent run's event log. A thin layer over `pharmagentics.tools.events`: which prompt each step
used (file and short hash), and `note`, the one call the run makes to record a step done by code. Every function
is a no-op without a log and never raises, so recording cannot change what the run answers (FR-008)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pharmagentics.tools.events import EventLog

_CONFIDENCE = re.compile(r"Confidence(?: for [^:]+)?: (High|Medium|Low)\b")


def prompt_ref(path: Path) -> str:
    return f"{path.stem}@{hashlib.sha256(path.read_bytes()).hexdigest()[:7]}"


def new_log(cfg: dict, here: Path, *, on_event=None, seed: list[dict] | None = None) -> EventLog:
    """An event log that knows each prompt's file and hash (a prompt changed after a brief is a different hash)."""
    log = EventLog(on_event=on_event, seed=seed)
    refs = {name: prompt_ref(here / rel) for name, rel in cfg["prompts"].items()}
    for p in cfg["participants"]:
        refs[p["name"]] = prompt_ref(here / p["instructions"])
    log.prompts = refs
    story_done = (here / cfg["prompts"]["story_done"]).read_text(encoding="utf-8")
    log.done_marker = next((x.strip() for x in story_done.splitlines() if x.strip() and "{task}" not in x), "")
    return log


async def note(run_log, step: str, text: str = "", *, summary: str = "", tool: str | None = None, args: dict | None = None,
               verdict: str | None = None, story=...) -> None:
    """Record a step done by code (actor Code). `text` is what the step produced: its claim tokens are its claims."""
    log = getattr(run_log, "events", None)
    if log is None:
        return
    try:
        await log.refresh(text)
        extra = {} if story is ... else {"story": story}
        log.emit("Code", "code", step, tool=tool, args=args, verdict=verdict, summary=summary or text.split("\n")[0],
                 text=text, **extra)
    except Exception:  # noqa: BLE001
        pass


def confidence(section: str) -> str:
    """The closing confidence line of a story section, by code."""
    m = _CONFIDENCE.search(section or "")
    return f"Closed with {m.group(1)} confidence." if m else "Closed the story."


def screened(plan: dict) -> str:
    if plan.get("promotion_review"):
        return "Code read the question as a release-wide Promotion review."
    n = sum(c.get("proposed") == "investigate" for c in plan.get("stories", []))
    return f"Code screened the territories and proposed {n} stor{'y' if n == 1 else 'ies'} to investigate."


def manager_check(plan: dict) -> str:
    if plan.get("flagged"):
        return "Code flagged the manager's plan for the analyst: " + " ".join(plan.get("flags", []))[:200]
    n = len(plan.get("manager_order", []))
    return f"Code checked the manager's plan against its own and kept {n} stor{'y' if n == 1 else 'ies'} in the manager's order."


async def claims_of(mcp) -> list[dict]:
    """The run's claims so far, for filling tokens in a summary. Read-only: it changes nothing in the run."""
    from briefing_lowcode.team import _call

    import json

    return json.loads(await _call(mcp, "export_run"))["claims"]


def attach(result: dict, run_log, n_claims: int, index: dict[int, int] | None) -> dict:
    """Add the finished event log to a run's result, with each event's claims as indexes into the brief's claims."""
    log = getattr(run_log, "events", None)
    if log is not None:
        result["events"], result["claim_events"] = log.finalize(n_claims, index)
    return result
