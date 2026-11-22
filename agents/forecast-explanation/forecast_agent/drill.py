"""Where an unexplained gap sits (fcst-002). After the investigation, the territories whose gap has no driver are
split by payer channel, prescriber specialty and, when one channel stands out, by plan. Code computes every split
(engine.Case.split); the rules or a model choose which splits to run and when to stop, and a model may add a
conclusion in words. A split says where a gap sits, never why."""
from __future__ import annotations

import asyncio
import json
import os
import threading
from typing import Annotated

from .engine import Case, Refused, no_digits

MAX_TARGETS = 2
MAX_CALLS = int(os.environ.get("FORECAST_DRILL_MAX_CALLS", "8"))
DRILL_SECONDS = float(os.environ.get("FORECAST_DRILL_SECONDS", "300"))


def targets(case: Case) -> list[str]:
    """Territories whose gap beyond their peers has no accepted driver."""
    if case.abstained or not case.usable:
        return []
    covered = {e.territory for e, _ in case.accepted()}
    screen = case.screen()
    if case.cut != "NATIONAL":
        row = next((r for r in screen if r["territory"] == case.cut), None)
        return [case.cut] if row and row["standout"] and row["beyond_peers"] < 0 and case.cut not in covered else []
    return [r["territory"] for r in case.unexplained(screen)][:MAX_TARGETS]


def run_rules(case: Case, terrs: list[str] | None = None, by: str = "rules") -> None:
    for t in terrs if terrs is not None else targets(case):
        ch = case.split(t, "channel")
        case.split(t, "specialty")
        if ch["verdict"] == "concentrated":
            case.split(t, "plan", ch["top"])
        case.decide(by, "split_gap", t, "a gap with no driver is split by channel and specialty, and by plan when one "
                                         "channel stands out")


def run_model(case: Case, spec: str, terrs: list[str] | None = None) -> dict:
    """The model chooses the splits and concludes in words; the rules split whatever it leaves untouched."""
    from agent_framework import Agent, tool

    from pharmagentics.llm import chat_client

    from .models import options

    terrs = terrs if terrs is not None else targets(case)
    stats = {"calls": 0, "fallback": None}
    lock = threading.RLock()
    if not terrs:
        return stats

    def guard(fn) -> str:
        with lock:
            if stats["calls"] >= MAX_CALLS:
                return "Refused: the call budget is spent. Stop."
            stats["calls"] += 1
            try:
                return fn()
            except Refused as exc:
                return f"Refused: {exc}"

    @tool
    def split(territory: Annotated[str, "A territory id from the list"],
              dimension: Annotated[str, "channel, specialty or plan"],
              within_channel: Annotated[str | None, "For a plan split: the payer channel, e.g. COMMERCIAL"] = None) -> str:
        """Split a territory's gap by segment, against the same segment in the other territories."""
        def run() -> str:
            if territory not in terrs:
                raise Refused(f"Split only these territories: {', '.join(terrs)}.")
            s = case.split(territory, dimension, within_channel)
            return json.dumps({k: s[k] for k in ("id", "territory", "dimension", "within_channel", "verdict", "top",
                                                 "total_shortfall_trx")} | {"rows": s["rows"][:6]})
        return guard(run)

    @tool
    def conclude(territory: Annotated[str, "The territory"], note: Annotated[str, "Where the gap sits, in words, no digits"]) -> str:
        """Record where the territory's gap sits (a location, not a cause)."""
        def run() -> str:
            case.drill_notes.append({"territory": territory, "note": no_digits(note, "A conclusion")})
            case.decide("agent", "locate_gap", territory, case.drill_notes[-1]["note"])
            return "Recorded."
        return guard(run)

    brief = json.dumps({"territories_to_split": terrs,
                        "their_gap_beyond_peers_trx": {r["territory"]: r["beyond_peers"] for r in case.screen() if r["territory"] in terrs}})
    agent = Agent(client=chat_client(spec), name="gap_locator", default_options=options(spec), tools=[split, conclude],
                  instructions="Each territory listed missed beyond the other territories with no driver found. Find where "
                               "its gap sits: split it by channel and by specialty; when one channel is concentrated, split "
                               "that channel by plan. Small cells are noisy. Then call conclude once per territory, in words "
                               "only, saying where the gap sits; never claim a cause. Do not repeat a split.")
    try:
        asyncio.run(asyncio.wait_for(agent.run("Locate these gaps.\n" + brief), timeout=DRILL_SECONDS))
    except Exception as exc:  # noqa: BLE001 - the rules split what is left
        stats["fallback"] = type(exc).__name__
    done = {s["territory"] for s in case.splits}
    rest = [t for t in terrs if t not in done]
    if rest:
        run_rules(case, rest, by="rules (model left it)")
    return stats
