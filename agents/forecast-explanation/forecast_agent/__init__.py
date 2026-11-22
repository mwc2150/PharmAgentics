"""Forecast-Explanation agent (fcst-002): a model where the language is (reading the question, follow-ups, the
summary), code where the math is (data gate, episodes, comparisons, the rules investigation, every number).

    answer(question)                          no model: keyword reading, rules, code wording
    answer(question, model=spec)              the product: the model reads and writes; the rules investigate
    answer(question, model=spec, investigator="model")   the comparison arm: the model also investigates
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

from pharmagentics.tools import DEFAULT_DB, Registry

from .engine import Case
from .policy import run_rules
from .scope import INTENTS, parse_scope
from .write import compose

HERE = Path(__file__).resolve().parent


def config_version() -> str:
    """A hash of the engine's own files, so a changed prompt or rule shows as a new configuration in MLflow."""
    h = hashlib.sha256()
    for p in sorted(HERE.glob("*.py")) + sorted((HERE / "prompts").glob("*")):
        h.update(p.read_bytes())
    return h.hexdigest()[:10]


def context(db=DEFAULT_DB) -> tuple[str, str]:
    reg = Registry(db)
    try:
        return reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
    finally:
        reg.close()


class _Steps:
    """Stage progress for the UI: each step as it starts and finishes, with its time."""

    def __init__(self, on_step):
        self.on_step, self.t = on_step, None

    def __call__(self, step: str, model: bool = False):
        if self.on_step and self.t is not None:
            self.on_step({"tool": "step", "args": {"step": self.t[0]}, "result": f"done in {time.time() - self.t[1]:.0f} s"})
        self.t = (step, time.time())
        if self.on_step and step:
            self.on_step({"tool": "step", "args": {"step": step}, "result": "with the model" if model else "in code"})


def answer(question: str, model: str | None = None, db=DEFAULT_DB, territory: str | None = None,
           weeks: list[str] | None = None, on_step=None, drop_controls: list[str] | None = None,
           intent: str | None = None, investigator: str = "rules", writer: bool = True, drill: str | None = "rules") -> dict:
    """One question, end to end.

    model         the language model for reading the question (step 1) and writing the summary (step 8); None
                  uses the keyword rules and code wording, with the same numbers
    territory, weeks, intent
                  a scope the analyst confirmed on the scope card: reading is skipped
    investigator  "rules" (the default) or "model": the model also investigates (step 6), the comparison arm
    writer        False keeps the code summary even with a model (used when only the investigation is compared)
    drill         where an unexplained gap sits: "rules" (the default), "model" (the model picks the splits), or None
    """
    started = time.time()
    steps = _Steps(on_step)
    reg = Registry(db)
    try:
        first, latest = reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
        confirmed = weeks is not None or territory is not None or intent is not None
        if confirmed or not model:
            scope = parse_scope(question, first, latest, territory=territory, weeks=weeks)
            read_by = "confirmed" if confirmed else "rules"
        else:
            from .reader import read_scope
            scope, read_by = read_scope(question, first, latest, model)
        if intent in INTENTS:
            scope.intent = intent
        if scope.out_of_scope:
            return {"system": "forecast_agent", "answer": scope.out_of_scope, "claims": [], "evidence": [],
                    "abstained": True, "trajectory": {"scope_read_by": read_by},
                    "report": {"out_of_scope": scope.out_of_scope, "scope": scope.card(),
                               "question": scope.question, "intent": scope.intent}}
        steps("Checking the data and investigating")
        case = Case(reg, scope, drop_controls)
        trajectory = {"model": model, "scope_read_by": read_by, "investigator": "rules", "tool_calls": 0,
                      "llm_calls": 0, "fallback": None}
        if scope.intent == "screen" or case.cut_provisional():
            run_rules(case, "code") if case.cut_provisional() else None
            mode = "code"
        elif investigator == "model" and model:
            from .agent import investigate
            trajectory["investigator"] = "model"
            trajectory.update(investigate(case, model, on_step=on_step))
            mode = f"agent ({model})" + (" with rules fallback" if trajectory.get("fallback") else "")
        else:
            run_rules(case)
            mode = "rules"
        if drill and mode != "code":
            steps("Locating any unexplained gap", model=drill == "model" and bool(model))
            from . import drill as gaps
            if drill == "model" and model:
                trajectory["drill"] = {"by": "model", **gaps.run_model(case, model)}
            else:
                gaps.run_rules(case)
                trajectory["drill"] = {"by": "rules"}
        out = compose(case, mode, trajectory, writer_model=model if writer else None, steps=steps)
        steps("")
        trajectory["seconds"] = round(time.time() - started, 1)
        out["system"] = "forecast_agent" if model else "forecast_rules"
        out["report"]["scope_read_by"] = read_by
        return out
    finally:
        reg.close()
