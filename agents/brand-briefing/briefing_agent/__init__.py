"""Briefing build 3: the Briefing agent (Briefing Architecture §14; brief-002 Phase B).

    scope gate (code) -> code triage (Phase A) -> manager's plan (agent; A1) -> P1 by exception (always in UAT)
    -> per-story Magentic team: manager, Data Forensics, Driver Investigator (MCP tools, no-repeat ledger)
    -> code-built brief sections + writer's answer and story sentences (LLM) -> verification, one revision

Entry points: `answer(question)` for the eval harness (no person: the manager's plan runs and the record
says whether it would have paused); `triage(question)` and `run_with_plan(question, decision, plan)` for
the UAT worker. Agent code never imports eval/.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path

import yaml
from agent_framework import Agent
from mcp.client.client import Client

from pharmagentics.llm import chat_client, chat_options, model_spec
from pharmagentics.tools.memo import render_sections as memo_sections_rendered
from pharmagentics.tools.registry import digits_outside_tokens
from pharmagentics.tools.definition import Definition, prompt_words
from pharmagentics.tools.window import Comparison
from pharmagentics.tracing import finish, span

from briefing_baseline import pipeline as scripted
from briefing_baseline.triage import stage_flow
from briefing_lowcode.team import RunLog, _call

from pharmagentics.tools.events import EventLog

from . import lessons
from . import plan as planmod
from . import reader, trace, write
from .investigate import investigate, server
from .scope import out_of_scope

HERE = Path(__file__).resolve().parent
NAME = "briefing_agent"


def load_config() -> dict:
    return yaml.safe_load((HERE / "agent.yaml").read_text(encoding="utf-8"))


def config_version() -> str:
    h = hashlib.sha256()
    for f in [HERE / "agent.yaml", *sorted((HERE / "prompts").glob("*.md")), lessons.FILE]:
        h.update(f.name.encode() + f.read_bytes())
    return h.hexdigest()[:12]


def answer(question: str, model: str | None = None, *, comparison: Comparison | None = None,
           definition: Definition | dict | None = None) -> dict:
    """Eval entry point: question in, AnswerEnvelope dict out. `definition` (brief-010) is what the brief is built from;
    None is the pre-selected values and `comparison` maps into it."""
    return asyncio.run(_answer(question, model, comparison, definition))


def _options(comparison: Comparison | None, definition: Definition | dict | None) -> dict:
    """The scripted engine's keywords: only what was given, so the pre-selected run is the call it always was."""
    return {k: v for k, v in (("comparison", comparison), ("definition", definition)) if v is not None}


def _definition_text(plan: dict) -> str:
    return prompt_words(Definition.coerce(plan.get("definition"), None))


def events_for(*, on_event=None, seed: list[dict] | None = None) -> EventLog:
    """brief-009: an event log that knows this build's prompts. The worker passes one to `triage` and `run_with_plan`."""
    return trace.new_log(load_config(), HERE, on_event=on_event, seed=seed)


def triage(question: str, model: str | None = None, *, comparison: Comparison | None = None,
           events: EventLog | None = None, definition: Definition | dict | None = None) -> dict:
    """UAT: the plan P1 reviews (code plan plus the manager's calls)."""
    cfg = load_config()
    return asyncio.run(_triage(question, model_spec(model or cfg.get("model")), RunLog(events), comparison, definition))


def run_with_plan(question: str, decision: dict, plan: dict, model: str | None = None, *,
                  events: EventLog | None = None) -> dict:
    """UAT: the brief on P1's decision over the reviewed plan. Returns envelope, triage record and flow."""
    cfg = load_config()
    if decision.get("plan_id") != plan.get("plan_id"):
        raise scripted.StalePlan("The decision is for another plan.")
    allowed = [c["id"] for c in plan["stories"] if c["proposed"] == "investigate"]
    order = list(decision.get("stories", []))
    if any(s not in allowed for s in order) or len(set(order)) != len(order):
        raise ValueError(f"Not a story this plan proposes: {', '.join(s for s in order if s not in allowed)}")
    return asyncio.run(_run(question, plan, order, model_spec(model or cfg.get("model")), reviewed=True, log=RunLog(events)))


async def _ask(spec: str, prompt: str, log: RunLog, name: str) -> str:
    agent = Agent(client=chat_client(spec), name=name, default_options=chat_options(spec), middleware=[log.chat(name)])
    return (await agent.run(prompt)).text or ""


async def _triage(question: str, spec: str, log: RunLog, comparison: Comparison | None = None,
                  definition: Definition | dict | None = None) -> dict:
    cfg = load_config()
    code_plan = scripted.triage(question, **_options(comparison, definition))
    if code_plan["promotion_review"]:
        await trace.note(log, "Screen territories", summary=trace.screened(code_plan))
        return dict(planmod.apply(code_plan, '{"order": []}', question), model=spec)
    scope = out_of_scope(question)
    if scope:  # no territories were screened for a question outside the release
        return dict(code_plan, engine="agent", state="OUT_OF_SCOPE", scope=scope, stories=[], flagged=False, flags=[],
                    manager_order=[], manager_drop={}, manager_note="", model=spec)
    await trace.note(log, "Screen territories", summary=trace.screened(code_plan))
    if code_plan["state"] != "TRIAGE_REVIEW":
        return dict(planmod.apply(code_plan, '{"order": []}', question), model=spec)
    prompt = (HERE / cfg["prompts"]["manager_triage"]).read_text(encoding="utf-8").format(
        question=question.split(":", 1)[-1].strip(), cards=planmod.cards_text(code_plan), definition=_definition_text(code_plan))
    with span("4_triage_manager", inputs={"cards": planmod.cards_text(code_plan)}) as sp:
        reply = await _ask(spec, prompt, log, "manager_triage")
        plan = planmod.apply(code_plan, reply, question)
        finish(sp, {"reply": reply, "order": plan["manager_order"], "flags": plan["flags"]})
    await trace.note(log, "Review the manager's plan", summary=trace.manager_check(plan))
    return dict(plan, model=spec)


def _left_out(plan: dict, order: list[str]) -> list[str]:
    proposed = [c for c in plan["stories"] if c["proposed"] == "investigate"]
    manager = plan.get("manager_order", [c["id"] for c in proposed])
    by_manager, by_analyst = [], []
    for c in proposed:
        if c["id"] in order:
            continue
        if c["id"] not in manager:
            why = (plan.get("manager_drop") or {}).get(c["id"]) or ""
            reason = why.rstrip(".") if why and not digits_outside_tokens(why) and "{c" not in why else ""
            by_manager.append(c["title"] + (f", because: {reason[0].lower()}{reason[1:]}" if reason else ""))
        else:
            by_analyst.append(c["title"])
    return ([f"Left out of this brief by the manager: {'; '.join(by_manager)}."] if by_manager else []) + \
           ([f"Left out of this brief by the analyst: {', '.join(by_analyst)}."] if by_analyst else [])


_CMP_NOTE = 'The token {cmp} is available: code fills it with the comparison the analyst chose, as in "against {cmp}".'
_NO_CMP_NOTE = "This brief has no comparison (no earlier week). Do not write {cmp} or any comparison."


async def _write(cfg: dict, spec: str, question: str, sections: dict, close: dict, stories: list[dict],
                 claims: list[dict], evidence: list[dict], log: RunLog, definition: dict | None = None) -> tuple[str, dict, dict, bool, list[str]]:
    n_claims = len(claims)
    story_tokens = {s["id"]: write.tokens(s["section"]) for s in stories}
    story_tokens["_sections"] = write.section_tokens(sections, close)
    confidences = {s["id"]: write.confidence(s["section"]) for s in stories}  # causal words only for a High story
    mentions = {s["id"]: write.mention(s["id"]) for s in stories}
    shown = write.sections_text(sections, close, stories)
    cmp = sections.get("comparison_phrase")  # the comparison in words, by code; the writer only places {cmp}
    gloss_text, glosses = write.glossary(shown, claims, evidence, sections.get("comparison_weeks"))  # what each number measures, by code
    prompt = (HERE / cfg["prompts"]["writer"]).read_text(encoding="utf-8").format(
        question=question.split(":", 1)[-1].strip(), sections=shown, glossary=gloss_text or "(no numbers)",
        definition=prompt_words(Definition.coerce(definition, None)),
        comparison=_CMP_NOTE if cmp else _NO_CMP_NOTE) \
        + lessons.block("writer")  # approved lessons only (core-008 FR-022); empty adds nothing
    with span("5_writer") as sp:
        raw = await _ask(spec, prompt, log, "writer")
        try:
            reply = planmod.parse(raw)
        except Exception:  # noqa: BLE001 - an unreadable reply means no LLM sentences, never a crash
            reply = {}
        finish(sp, {"reply": raw})
    revised = False
    with span("6_verification") as sp:
        bad = write.check(reply, story_tokens, n_claims, glosses, confidences, bool(cmp), mentions)
        if bad:
            allowed = "\n".join(f"- {k}: {', '.join(sorted(v)) or '(none)'}" for k, v in story_tokens.items() if k != "_sections")
            allowed += "\n- answer: any token above, or " + (", ".join(sorted(story_tokens["_sections"])) or "(none)")
            allowed += "\n- every piece: " + (f"{write.CMP} (code fills it with the comparison)" if cmp else "no comparison placeholder (the brief has none)")
            allowed += f"\n- every piece: {write.LINK} (code fills it with the causal verb for the story's confidence)"
            fix = (HERE / cfg["prompts"]["revise"]).read_text(encoding="utf-8").format(
                problems="\n".join(f"- {k}: {'; '.join(v)}" for k, v in bad.items()), allowed=allowed,
                glossary=gloss_text or "(no numbers)", reply=json.dumps(reply))
            raw2 = await _ask(spec, fix, log, "reviser")
            try:
                reply = planmod.parse(raw2)
            except Exception:  # noqa: BLE001
                pass
            revised = True
        answer_text, sentences, dropped = write.clean(reply, story_tokens, n_claims, glosses, confidences, bool(cmp), mentions)
        chart_lines, chart_dropped = write.chart_explanations(reply, close, stories, n_claims, glosses, bool(cmp))
        dropped += chart_dropped
        # code's words go in after every check: the comparison, and each piece's causal verb from its confidence
        all_high = write.answer_high("", confidences)  # a chart of §2 or §4 speaks for the whole brief
        answer_text = write.fill(answer_text, cmp, write.link_verb(write.answer_high(answer_text, confidences, mentions)))
        sentences = {k: write.fill(v, cmp, write.link_verb(confidences.get(k) == "High")) for k, v in sentences.items()}
        chart_lines = {k: write.fill(v, cmp, write.link_verb(confidences[k] == "High" if k in confidences else all_high))
                       for k, v in chart_lines.items()}
        finish(sp, {"problems": bad, "revised": revised, "dropped": dropped, "chart_lines": sorted(chart_lines)})
    n_bad = sum(len(v) for v in bad.values())  # `bad` maps each part to its list of problems
    await trace.note(log, "Check the writer's sentences", summary=(
        f"Code checked every sentence: {n_bad} problem{'' if n_bad == 1 else 's'} found" + ("; rewritten once" if revised else "")
        + f"; {len(dropped)} dropped."))
    return answer_text, sentences, chart_lines, revised, dropped


async def _run(question: str, plan: dict, order: list[str], spec: str, reviewed: bool, log: RunLog) -> dict:
    cfg = load_config()
    started = time.time()
    if plan.get("promotion_review"):
        async with Client(server()) as mcp:
            with span("1_load_and_pin", inputs={"question": question}, model=spec) as sp:
                pinned = await _call(mcp, "open_run", question=question)
                finish(sp, {"run_context": pinned})
            env = json.loads(await _call(mcp, "promotion_review"))
        env.update(system=f"{NAME}:{spec}", trajectory={"llm_calls": 0, "model": spec, "scope": "promotion_review"})
        record = planmod.record(plan, [], reviewed)
        return trace.attach({"envelope": env, "triage": record, "flow": stage_flow(plan, record, verified=True)},
                            log, len(env.get("claims") or []), None)  # the saved brief keeps its timeline
    if plan.get("state") == "OUT_OF_SCOPE":
        choice = Comparison.model_validate(plan["comparison"]) if plan.get("comparison") else None
        env = scripted.answer(question, **_options(choice, plan.get("definition")))
        env.update(system=f"{NAME}:{spec}", answer=plan["scope"] + "\n" + env["answer"],
                   comparison=plan.get("comparison"),
                   trajectory={"scope": "out", "tools": [], "llm_calls": 0, "capped": None, "model": spec,
                               "config_version": config_version(), "seconds": round(time.time() - started, 1)})
        return trace.attach({"envelope": env, "triage": None, "flow": None}, log, len(env.get("claims") or []), None)
    async with Client(server()) as mcp:
        if log.events is not None:
            log.events.fetch = lambda: trace.claims_of(mcp)
            if reviewed:
                log.events.emit("Person", "person", "Review the plan", story=None, summary=(
                    f"The analyst reviewed the plan and approved {len(order)} stor{'y' if len(order) == 1 else 'ies'}."))
        with span("1_load_and_pin", inputs={"question": question}, model=spec, config_version=config_version()) as sp:
            args = {"comparison": plan["comparison"]} if plan.get("comparison") else {}
            if plan.get("definition"):
                args["definition"] = plan["definition"]
            pinned = await _call(mcp, "open_run", question=question, **args)
            sections = json.loads(await _call(mcp, "brief_sections"))
            finish(sp, {"run_context": pinned})
        await trace.note(log, "Pin the data and period", pinned, tool="open_run")
        await trace.note(log, "Build the memo's code sections", json.dumps(sections), tool="brief_sections",
                         summary="Code built the title, numbers, limits and appendix sections.")
        with span("4a_investigation", inputs={"order": order}) as sp:
            stories, notes = (await investigate(cfg, spec, mcp, plan, order, log)) if plan["state"] == "TRIAGE_REVIEW" else ([], [])
            finish(sp, {"notes": notes, "tool_sequence": log.tools})
        competitor = any(s["id"].startswith("competitor:") for s in stories)
        close = json.loads(await _call(mcp, "memo_close", competitor=competitor))  # §1 and §5, by code
        dropped_line = await _call(mcp, "dropped_line")
        await trace.note(log, "Build the bottom line and next checks", json.dumps(close) + dropped_line, tool="memo_close",
                         summary="Code wrote the bottom line, the next checks and the dropped-territories line.")
        run = json.loads(await _call(mcp, "export_run"))
    claims = run["claims"]
    answer_text, sentences, chart_lines, revised, dropped = await _write(cfg, spec, question, sections, close, stories, claims,
                                                            run["evidence"], log, plan.get("definition"))
    template, memo_sections = write.assemble(sections, close, stories, answer_text, sentences,
                                             _left_out(plan, order), dropped_line, chart_lines)
    if (bad := digits_outside_tokens(template)):  # code sections are clean; this guards the assembly itself
        raise AssertionError(f"digit outside a claim token: {bad[:3]}")
    text, used, citations, index = write.render(template, claims)
    await trace.note(log, "Assemble the memo", template, summary="Code assembled the memo from the sections, the writer's sentences and claim tokens.")
    keep = {c["evidence_id"] for c in used}
    record = planmod.record(plan, order, reviewed)
    flow_record = dict(record, calls=[dict(c, outcome="investigated") if c["outcome"] == "restored" else c for c in record["calls"]])
    flow = write.flow(stage_flow(plan, flow_record, verified=True), plan, record, log.tools, revised, spec)
    capped = next((n["capped"] for n in notes if n["capped"]), None)
    envelope = {
        "system": f"{NAME}:{spec}", "answer": text, "claims": used, "comparison": plan.get("comparison"),
        "definition": plan.get("definition"),
        "evidence": [e for e in run["evidence"] if e["id"] in keep],
        "abstained": bool(run["abstained"]), "citations": citations,
        "sections": memo_sections_rendered(memo_sections, claims, index),
        "trajectory": {"tools": log.tools, "llm_calls": log.llm_calls, "tokens": log.tokens, "capped": capped,
                       "revised": revised, "dropped_pieces": dropped, "stories": run["stories"], "notes": notes,
                       "manager_order": plan.get("manager_order"), "flagged": plan.get("flagged"),
                       "would_pause": record["would_pause"], "seconds": round(time.time() - started, 1),
                       "config_version": config_version(), "model": spec},
    }
    return trace.attach({"envelope": envelope, "triage": record, "flow": flow}, log, len(used), index)


def _release_bounds() -> tuple[str, str, list[str]]:
    """The release's first and latest week and its territory IDs, for the scope reader."""
    from pharmagentics.tools import DEFAULT_DB, Registry
    from pharmagentics.tools.queries import TERRITORY_NAMES

    reg = Registry(DEFAULT_DB)
    try:
        first, latest = reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
    finally:
        reg.close()
    return first, latest, [t for t in TERRITORY_NAMES if t != "NATIONAL"]


async def _scope_proposal(question: str, spec: str, log: RunLog) -> dict | None:
    """The scope the model reads from the question text (brief-008 FR-017), recorded for scoring only: the brief
    has already run on the prefix scope and nothing here changes it. One reader call; any failure records nothing."""
    try:
        first, latest, territories = _release_bounds()
        log.llm_calls += 1  # the reader is one model call, made even when its answer is unusable
        return await asyncio.to_thread(reader.scope_proposal, question, spec=spec, first=first, latest=latest,
                                       territories=territories)
    except Exception:  # noqa: BLE001 - no usable reading: no scope_proposal, and the scorer says so
        return None


async def _answer(question: str, model: str | None, comparison: Comparison | None = None,
                  definition: Definition | dict | None = None) -> dict:
    cfg = load_config()
    spec = model_spec(model or cfg.get("model"))
    log = RunLog()
    try:
        plan = await _triage(question, spec, log, comparison, definition)
    except ValueError:  # outside the release: the scripted engine says so, with no model
        if comparison is not None or (definition is not None and Definition.coerce(definition, None).comparison is not None):
            raise
        return dict(scripted.answer(question, **_options(None, definition)), system=f"{NAME}:{spec}")
    result = await _run(question, plan, plan.get("manager_order", []), spec, reviewed=False, log=log)
    envelope = result["envelope"]
    if load_config().get("scope_proposal", True) and (proposal := await _scope_proposal(question, spec, log)):
        envelope["trajectory"]["scope_proposal"] = proposal
    if isinstance(envelope.get("trajectory"), dict):
        envelope["trajectory"]["llm_calls"] = log.llm_calls  # the reader's call is counted
    return envelope
