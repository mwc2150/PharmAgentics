"""Briefing lane, scripted baseline (Evaluation Pack §6): a fixed pipeline with a fixed order of
checks and a templated brief. No model. Stages follow the System Architecture spine:

1 load and pin -> 2 validation gate -> 3a competitive intelligence -> 4a fixed-order investigation
-> 5 template narrative (claim tokens) -> 6 verification (no digit outside a claim token).

The stage steps live in `pharmagentics.tools.stages`, shared with the MCP tools the low-code agent
calls, so this pipeline stays the manager-off ablation: same tools, fixed order.

brief-002 Phase A splits the run at the end of stage 3. `answer(question)` runs straight through
with the default triage, exactly as before (the eval entry point). `triage(question)` stops after
stage 3 and returns the triage plan for P1; `run_with_plan(question, decision)` runs stages 4 to 6
on the stories P1 approved, in P1's order.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pharmagentics.tools import DEFAULT_DB, Registry
from pharmagentics.tools import charts, memo, projection, promotion, stages
from pharmagentics.tools.checks import confidence
from pharmagentics.tools.lag_checks import run_checks
from pharmagentics.tools.queries import name
from pharmagentics.tools.registry import digits_outside_tokens
from pharmagentics.tools.window import Comparison
from pharmagentics.tracing import finish, span

MAX_STORIES = 4
COMPETITOR = "competitor:BXE"


class StalePlan(ValueError):
    """The decision's plan_id no longer matches the plan code builds now."""


@dataclass
class Front:
    """What stages 1 to 3 produced: the period, their lines (the triage context), the memo pieces and the screen."""
    p: stages.Period
    out: list[str]
    found: list[dict]
    quiet: list[str]
    health: str = ""
    restated: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)
    proj: projection.Projection | None = None
    facts: dict = field(default_factory=dict)  # stage 3's claims by name, for the memo's blocks (brief-008)


def answer(question: str, db=DEFAULT_DB, brand_id: str = "BXA", *, comparison: Comparison | None = None) -> dict:
    reg = Registry(db)
    try:
        return _brief(reg, question, brand_id=brand_id, comparison=comparison)
    finally:
        reg.close()


def scope(question: str, db=DEFAULT_DB, brand_id: str = "BXA", *, comparison: Comparison | None = None) -> dict:
    """The brief's scope as the API stores it (brand, territory, week): what a follow-up is in or out of."""
    reg = Registry(db)
    try:
        p = stages.resolve(reg, question, brand_id, comparison=comparison)
    finally:
        reg.close()
    return {"brand_id": p.brand_id, "territory_id": p.focus or "NATIONAL", "week_start": p.requested[-1] if p.requested else "",
            "comparison": comparison.model_dump(mode="json") if comparison is not None else None}


def triage(question: str, db=DEFAULT_DB, brand_id: str = "BXA", *, comparison: Comparison | None = None) -> dict:
    """Stages 1 to 3, then the code triage plan for P1 (brief-002 US8). Its claims are its own run's."""
    from .triage import build_plan

    reg = Registry(db)
    try:
        f = _front(reg, question, brand_id, comparison=comparison)
        if f is None:
            raise ValueError("That period is outside the release.")
        return build_plan(reg, f)
    finally:
        reg.close()


def run_with_plan(question: str, decision: dict, db=DEFAULT_DB, brand_id: str = "BXA", *, comparison: Comparison | None = None) -> dict:
    """Stages 4 to 6 on P1's decision: {plan_id, stories: [ids in order]}. Returns the envelope, the
    triage record (who made each call) and the stage flow."""
    from .triage import stage_flow, triage_record

    plan = triage(question, db, brand_id, comparison=comparison)
    if decision.get("plan_id") != plan["plan_id"]:
        raise StalePlan("The triage plan changed; review it again.")
    allowed = [c["id"] for c in plan["stories"] if c["proposed"] == "investigate"]
    order = list(decision.get("stories", []))
    bad = [s for s in order if s not in allowed] or [s for s in set(order) if order.count(s) > 1]
    if bad:
        raise ValueError(f"Not a story this plan proposes for investigation: {', '.join(sorted(set(bad)))}")
    titles = {c["id"]: c["title"] for c in plan["stories"]}
    left_out = [titles[s] for s in allowed if s not in order]
    reg = Registry(db)
    try:
        envelope = _brief(reg, question, order=order, left_out=left_out, brand_id=brand_id, comparison=comparison)
    finally:
        reg.close()
    record = triage_record(plan, order)
    return {"envelope": envelope, "triage": record, "flow": stage_flow(plan, record, verified=True)}


def story_id(s: dict) -> str:
    return f"plan:{s['plan']}" if s["kind"] == "plan" else f"territory:{s['territory']}"


def default_order(found: list[dict]) -> list[str]:
    return [story_id(s) for s in found[:MAX_STORIES]] + [COMPETITOR]


def _front(reg: Registry, question: str, brand_id: str = "BXA", *, comparison: Comparison | None = None) -> Front | None:
    p = stages.resolve(reg, question, brand_id, comparison=comparison)
    if not p.requested:
        return None
    out: list[str] = []

    with span("1_load_and_pin", inputs={"question": question}, data_version=reg.data_version) as sp:
        out.append(f"Brief for {stages.describe(p)}. "
                   f"Data version {reg.data_version}. Product: {p.brand_id}. Territory questions use only cuts that pass the feed gate.")
        if p.note:
            out.append(p.note)
        finish(sp, {"weeks": p.requested, "baseline_weeks": p.baseline, "baseline_source": p.baseline_source,
                    "territory": p.focus, "data_version": reg.data_version})
    if p.promotion_review:
        return Front(p, out, [], [])

    with span("2_validation_gate") as sp:
        health = stages.data_health(reg, p)
        restated = stages.restatements(reg, p)  # EV-1.2
        out += [health] + restated
        finish(sp, {"like_for_like_territories": p.ok})

    with span("3a_competitive_intelligence") as sp:
        if p.calendar_note:
            out.append(p.calendar_note)
        facts: dict = {}
        kpis = stages.kpis(reg, p, facts)
        out += kpis
        proj = projection.build(reg, p)  # a level for the memo; never a story (ADR 0001)
        found, quiet = ([], []) if p.calendar else stages.screen(reg, p)
        finish(sp, {"calendar_mode": bool(p.calendar), "candidates": [f["territory"] for f in found],
                    "projected": proj.territories("projected"), "estimated": proj.territories("estimated")})
    return Front(p, out, found, quiet, health, restated, kpis, proj, facts)


def _brief(reg: Registry, question: str, order: list[str] | None = None, left_out: list[str] = (),
           brand_id: str = "BXA", *, comparison: Comparison | None = None) -> dict:
    f = _front(reg, question, brand_id, comparison=comparison)
    if f is None:
        return _envelope(reg, stages.outside_release(stages.resolve(reg, question, brand_id=brand_id)), False, brand_id)
    p = f.p
    if p.promotion_review:
        return dict(promotion.render_review(reg, p), system="briefing_scripted", brand_id=p.brand_id)
    abstained, competitor = False, False
    blocks: list[memo.StoryBlock] = []
    told: list[dict] = []  # territory stories for §1 and §5: {territory, confidence, drivers}
    notes: list[str] = []
    dropped: list[str] = []  # folded under §3's detail

    with span("4a_investigation") as sp:
        if p.calendar:
            notes.append("No story is opened for a calendar week. Expect a rebound in the next regular week.")
        else:
            by_id = {story_id(s): s for s in f.found}
            for sid in (default_order(f.found) if order is None else order):
                if sid == COMPETITOR:
                    comp_facts: dict = {}
                    comp = stages.competitor_status(reg, p, lead=f"Story {_ord(len(blocks) + 1)}: competitor Metacora", facts=comp_facts)
                    if comp:
                        blocks.append(memo.StoryBlock(COMPETITOR, "Competitor Metacora", [memo.without_next(comp)],
                                                      chart=charts.competitor(reg, p), card=memo.competitor_card(p, comp_facts)))
                        competitor = True
                    continue
                s = by_id[sid]
                with span(f"story_{len(blocks) + 1}_{s['territory']}", inputs={"territory": s["territory"], "kind": s["kind"]}) as story_sp:
                    block, info = _story(reg, len(blocks) + 1, s, p)
                    finish(story_sp, {"abstained": info["confidence"] == "Low"})
                blocks.append(block)
                told.append(info)
                abstained |= info["confidence"] == "Low"
            if left_out:
                notes.append(f"Left out of this brief by the analyst: {', '.join(left_out)}.")
            if not blocks and not left_out:
                notes.append("Routine week. No material change was found, and territory swings stayed in their normal range.")
            elif f.quiet:
                dropped.append(stages.dropped_line(reg, p, f.quiet))
        finish(sp, {"abstained": abstained})

    with span("5_narrative") as sp:
        blocks.extend(promotion.story_blocks(reg, p))
        top: dict = {}
        bottom = memo.bottom_line(reg, p, f.proj, told, restated=bool(f.restated), facts=top)
        nums = memo.numbers(f.proj, f.facts, f.restated, p)
        lim = memo.limits(p, f.proj, f.health, reg)
        parts = memo.MemoParts(
            title=memo.title_lines(p),
            bottom_line=bottom, numbers=nums["lines"], limits=lim["lines"],
            next_checks=memo.next_checks(p, told, competitor),
            appendix=memo.appendix(reg, p=p, proj=f.proj) + memo.driver_timing(told),
            stories=blocks, story_notes=notes,
            charts={"2": charts.trend(reg, p), "4": charts.coverage(reg, p)},  # brief-003 FR-024
            kpis=memo.kpis(p, f.proj, top), territory_table=nums["territory_table"],
            details={"1": memo.bottom_detail(top), "2": nums["detail"], "3": dropped, "4": lim["detail"]})
        template, sections = memo.compose(parts)
        finish(sp, {"template_chars": len(template), "claims": len(reg.claims), "sections": [s["number"] for s in sections]})

    with span("6_verification") as sp:
        bad = digits_outside_tokens(template)
        finish(sp, {"digits_outside_tokens": bad})
        if bad:
            raise AssertionError(f"digit outside a claim token: {bad[:3]}")
    text, spans = reg.render_cited(template)
    return dict(_envelope(reg, text, abstained, p.brand_id), citations=spans,  # citations: where each claim sits (UI only)
                sections=memo.render_sections(sections, reg.claims))


def _story(reg, n, s, p) -> tuple[memo.StoryBlock, dict]:
    """One story: head, the checks in order, the closing confidence. Its next check goes to §5."""
    t = s["territory"]
    checks = run_checks(reg, t, p.weeks, p.baseline, brand_id=p.brand_id, use_selected_baseline=p.comparison is not None)
    level, lead = confidence(checks)
    facts: dict = {}
    head = f"Story {_ord(n)}: {stages.territory_change(reg, p, t, facts)}"
    lines = [head, "Checked, in this order:"] + [f"- {c.text}" for c in checks]
    supported = [c.driver for c in checks if c.verdict == "supported"]
    lags = {c.driver: c.detail["lag"] for c in checks if c.detail and "lag" in c.detail}
    if level == "Low":
        lines.append(f"Confidence: {level}. Unresolved, investigate next. No driver is named.")
    else:
        verb = "Leading driver" if level == "High" else "Candidate drivers"
        lines.append(f"Confidence: {level}. {verb}: {lead}.")
    plan = next((c.detail["plan"] for c in checks if c.driver == "access" and c.detail), None)
    chart = charts.story(reg, p, t, supported if level != "Low" else [], plan)
    detail = memo.story_detail(reg, p, t)
    block = memo.StoryBlock(story_id(s), name(t), lines, chart=chart, detail=detail,
                            card=memo.story_card(name(t), facts, level, [c.driver for c in checks], territory=t, checks=checks))
    return block, {
        "territory": t, "confidence": level, "drivers": supported, "lags": lags}


def _ord(n: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[n]


def _envelope(reg: Registry, text: str, abstained: bool, brand_id: str = "BXA") -> dict:
    return {"brand_id": brand_id, "system": "briefing_scripted", "answer": text, "claims": reg.claims, "evidence": reg.evidence, "abstained": abstained}
