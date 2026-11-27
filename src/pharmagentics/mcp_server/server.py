"""The MCP server and its per-run session.

One session is one run: `open_run` pins the question's period and one data version, the agent tools
add evidence items and claim tokens to the session's Registry, and `export_run` hands them back to the
caller (code, never the model). Admin tools are for the caller; agents get `AGENT_TOOLS` only.

Every number in a tool's text is a claim token such as {c7}; the model writes tokens and code fills them
(B-III). With `legend=True` a legend after the text also gives each token's value, for models that reason
about size; it is off by default because a small model copies the legend's values into its prose.
Verdicts and confidence are computed by code; the model chooses which tools to call and in what order.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from pharmagentics.tools import DEFAULT_DB, Registry
from pharmagentics.tools import queries as q
from pharmagentics.tools import charts, continuing, memo, projection, promotion, splits, stages
from pharmagentics.tools.brands import PRODUCTS
from pharmagentics.tools.checks import (DRIVERS, OWNER, Check, check_competitor, check_data,
                                        confidence, context_baseline)
from pharmagentics.tools.lag_checks import check_access, check_promotion, check_supply
from pharmagentics.tools.definition import Definition, words as definition_words
from pharmagentics.tools.window import Comparison

ADMIN_TOOLS = ("open_run", "export_run", "brief_sections", "story_section", "competitor_section", "dropped_line",
               "memo_close", "promotion_review")
_ORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
AGENT_TOOLS = {
    # Briefing Data Forensics: is the data wrong, and what is the like-for-like change?
    "data_forensics": ("feed_health", "restatements", "national_kpis", "check_data"),
    # Briefing Driver Investigator: where did it move, and why?
    "driver_investigator": ("screen_territories", "territory_change", "check_access", "check_promotion",
                            "check_supply", "check_competitor", "competitor_status", "story_confidence"),
    # Follow-ups (brief-006 slice 4): a new governed query an analyst may ask for.
    "follow_up": ("split_change",),
}
_TERRITORIES = {k: v for k, v in q.TERRITORY_NAMES.items() if k != "NATIONAL"}
_TOKEN = re.compile(r"\{c(\d+)\}")


class RunSession:
    """State for one run: the Registry (pinned data version, evidence, claims), the period, driver verdicts."""

    def __init__(self, db=DEFAULT_DB, legend: bool = False, no_repeat: bool | None = None):
        self.db = db
        self.legend = legend
        # Build 3's no-repeat ledger (brief-002 FR-016): off unless asked, so builds 1 and 2 are unchanged.
        self.no_repeat = os.environ.get("PHARMAGENTICS_MCP_NO_REPEAT") == "1" if no_repeat is None else no_repeat
        # A follow-up session (brief-006): driver checks report their verdict only, without the investigation's
        # story-so-far status, which a lone check would show as "Low, no driver yet" against a finished brief.
        self.follow_up = os.environ.get("PHARMAGENTICS_MCP_FOLLOW_UP") == "1"
        self.seen: dict[tuple[str, str], str] = {}
        self.reg: Registry | None = None
        self.p: stages.Period | None = None
        self.checks: dict[str, dict[str, Check]] = {}
        self.stories: dict[str, dict] = {}
        self.calls: list[dict] = []
        self.proj: projection.Projection | None = None  # set by brief_sections, read by memo_close
        self.restated = False
        self.facts: dict = {}  # stage 3 claims by name, kept for the memo's blocks (brief-008)
        self.story_facts: dict[str, dict] = {}  # territory -> the story head's claims, for its card
        self.story_detail: dict[str, list[str]] = {}  # territory -> readable splits, for its folded detail
        self.competitor_facts: dict = {}

    # admin -------------------------------------------------------------------------------------
    def open_run(self, question: str, comparison: Comparison | None = None, definition: Definition | None = None,
                 brand_id: str = "BXA") -> str:
        """Pin the period under the brief definition (brief-010) for one brand (core-010): every tool of the run
        computes under both. An unknown or unsupported brand raises before any data is read."""
        self.close()
        self.reg = Registry(self.db)
        self.p = stages.resolve(self.reg, question, brand_id, comparison=comparison, definition=definition)
        self.checks, self.stories, self.calls, self.seen = {}, {}, [], {}
        self.story_facts, self.story_detail, self.competitor_facts = {}, {}, {}
        if not self.p.requested:
            return stages.outside_release(self.p)
        lines = [f"Period: {stages.describe(self.p)}. Comparison: {memo.comparison_text(self.p)}. Source: {self.p.baseline_source}.",
                 f"Data version {self.reg.data_version}. Product: {self.p.brand_id} ({PRODUCTS[self.p.brand_id]})."]
        if self.p.note:
            lines.append(self.p.note)
        if not self.p.definition.is_pre_selected:
            lines.append("Brief definition: " + " ".join(definition_words(self.p.definition)))
        if self.p.focus:
            lines.append(f"The question names {q.name(self.p.focus)} ({self.p.focus}).")
        return "\n".join(lines)

    def export_run(self) -> dict:
        reg = self._reg()
        return {"data_version": reg.data_version, "claims": reg.claims, "evidence": reg.evidence,
                "abstained": any(st["confidence"] == "Low" for st in self.stories.values()),
                "stories": self.stories, "calls": self.calls}

    def close(self) -> None:
        if self.reg is not None:
            self.reg.close()
            self.reg = None

    # helpers -----------------------------------------------------------------------------------
    def _reg(self) -> Registry:
        if self.reg is None or self.p is None:
            raise ToolError("no run is open; the caller must call open_run first")
        return self.reg

    def _log(self, tool: str, **args) -> None:
        self._reg()
        self.calls.append({"tool": tool, "args": args})

    def _out(self, text: str) -> str:
        """A tool's text, with the legend of token values when the session has it on."""
        reg = self._reg()
        seen = sorted({int(n) for n in _TOKEN.findall(text)})
        if not seen or not self.legend:
            return text
        legend = "; ".join(f"{{c{n}}} = {reg.claims[n - 1]['value']}" for n in seen)
        return f"{text}\n\nToken values, for your reasoning only. Write the token, never the value: {legend}"

    def _territory(self, territory: str) -> str | None:
        key = re.sub(r"[\s\-]+", "_", (territory or "").strip()).upper()
        if key in _TERRITORIES:
            return key
        by_name = {v.upper(): k for k, v in _TERRITORIES.items()}
        return by_name.get((territory or "").strip().upper())

    def _bad_territory(self, territory: str) -> str:
        return f"Unknown territory {territory!r}. Use one of: {', '.join(_TERRITORIES)}."

    def _withheld(self, t: str) -> str | None:
        if t not in self.p.ok:
            return (f"{q.name(t)} has cuts that fail the feed gate in these weeks, so no like-for-like test is given "
                    f"for it. Use check_data on it, and report it as withheld.")
        return None

    # Data Forensics ----------------------------------------------------------------------------
    def feed_health(self) -> str:
        self._log("feed_health")
        p = self.p
        lines = [stages.data_health(self.reg, p)]
        lines.append(f"Like-for-like territories (every week passes the gate): {', '.join(p.ok) or 'none'}.")
        withheld = [t for t in p.terrs if t not in p.ok]
        if withheld:
            lines.append(f"Not like for like in these weeks: {', '.join(withheld)}.")
        if p.focus in p.terrs and p.focus not in p.ok:
            lines.append(f"{q.name(p.focus)} has withheld cuts in these weeks, so no like-for-like story is given for it.")
        return self._out("\n".join(lines))

    def restatements(self) -> str:
        self._log("restatements")
        lines = stages.restatements(self.reg, self.p)
        return self._out("\n".join(lines) if lines else f"No {self.p.brand_id} restatement touches these weeks.")

    def national_kpis(self) -> str:
        self._log("national_kpis")
        lines = ([self.p.calendar_note] if self.p.calendar_note else []) + stages.kpis(self.reg, self.p)
        if self.p.calendar:
            lines.append("No story is opened for a calendar week. Expect a rebound in the next regular week.")
        return self._out("\n".join(lines))

    def check_data(self, territory: str) -> str:
        self._log("check_data", territory=territory)
        t = self._territory(territory)
        if t is None:
            return self._bad_territory(territory)
        if (again := self._repeat("check_data", t)):
            return again
        return self._remember("check_data", t, self._record(t, check_data(self.reg, t, self.p.weeks, self.p.baseline)))

    def _repeat(self, tool: str, t: str) -> str | None:
        if self.no_repeat and (tool, t) in self.seen:
            return (f"Already tested: {tool} for {q.name(t)} ran in this run. Do not repeat it; test a driver not "
                    f"tested yet, or close the story with story_confidence. The earlier result:\n{self.seen[(tool, t)]}")
        return None

    def _remember(self, tool: str, t: str, text: str) -> str:
        self.seen[(tool, t)] = text
        return text

    # Driver Investigator -----------------------------------------------------------------------
    def screen_territories(self) -> str:
        self._log("screen_territories")
        p = self.p
        if p.calendar:
            return "Calendar mode: most of these weeks are holiday or plan-year-reset weeks, so no territory story is opened."
        if not p.has("territory"):
            return "This brief's levels leave out territories, so no territory story is opened."
        found, quiet = stages.screen(self.reg, p)
        if not found:
            return "No territory moved beyond its normal range against its peers. Routine week: no story to investigate."
        lines = ["Territories with a material change, largest impact first:"]
        for s in found:
            why = f"{p.brand_id} volume on plan {s['plan']} changed after an access change" if s["kind"] == "plan" else "beyond its normal range and its peers"
            lines.append(f"- {s['territory']} ({q.name(s['territory'])}): {why}.")
        if quiet:
            lines.append(f"Considered and dropped: {stages.dropped_count(self.reg, p, quiet)} territories moved within their normal range.")
        lines.append("Next: territory_change, then every check_*, then story_confidence, for each territory above.")
        return self._out("\n".join(lines))

    def territory_change(self, territory: str) -> str:
        self._log("territory_change", territory=territory)
        t = self._territory(territory)
        if t is None:
            return self._bad_territory(territory)
        return self._withheld(t) or self._out(stages.territory_change(self.reg, self.p, t))

    def _driver(self, name: str, territory: str, fn, reference: bool) -> str:
        self._log(name, territory=territory)
        t = self._territory(territory)
        if t is None:
            return self._bad_territory(territory)
        if (msg := self._withheld(t)):
            return msg
        if (again := self._repeat(name, t)):
            return again
        B = context_baseline(self.p.weeks, self.p.baseline) if reference and self.p.comparison is None else self.p.baseline
        brand = self.p.brand_id
        if fn is check_promotion:  # the stated comparison weeks, as the scripted brief (assumptions first)
            return self._remember(name, t, self._record(t, check_promotion(self.reg, t, self.p.weeks, self.p.baseline, brand)))
        if fn is check_competitor and self.p.comparison is not None:
            return self._remember(name, t, self._record(
                t, check_competitor(self.reg, t, self.p.weeks, B, brand, exact_comparison=True, pct_format="pct")))
        if fn is check_competitor:  # the shared check; the brief's percentages print the Briefing way (FR-016)
            return self._remember(name, t, self._record(t, fn(self.reg, t, self.p.weeks, B, brand, pct_format="pct")))
        if fn is check_access:
            return self._remember(name, t, self._record(t, fn(self.reg, t, self.p.weeks, B, brand_id=brand)))
        return self._remember(name, t, self._record(t, fn(self.reg, t, self.p.weeks, B, brand)))

    # Admin: the brief's code-built sections (build 3, brief-002 FR-026) --------------------------
    def brief_sections(self) -> dict:
        """The memo's code sections that stages 1 to 3 settle (brief-003): §2, §4 and §6, plus the title. Claims
        come from this run's Registry, through the same builders as the scripted brief (tools/memo.py)."""
        reg, p = self._reg(), self.p
        health = stages.data_health(reg, p)
        restated_facts: list[dict] = []
        restated = stages.restatements(reg, p, restated_facts)
        facts: dict = {}
        stages.kpis(reg, p, facts)
        self.proj, self.restated, self.facts = projection.build(reg, p), bool(restated), facts
        nums, lim = memo.numbers(self.proj, facts, restated, p), memo.limits(p, self.proj, health, reg)
        return {"title": memo.title_lines(p), "numbers": nums["lines"], "limits": lim["lines"],
                "appendix": memo.appendix(reg, p=p, proj=self.proj, restated=bool(restated)), "calendar": bool(p.calendar),
                "comparison_phrase": memo.comparison_phrase(p), "comparison_weeks": list(p.baseline or []),
                "territory_table": nums["territory_table"], "details": {"2": nums["detail"], "4": lim["detail"]},
                "data_artifact_stories": [asdict(b) for b in [memo.data_artifact_block(facts)] if b],  # brief-010 FR-011
                "restatement_stories": [asdict(b) for b in [memo.restatement_block(restated_facts)] if b],  # brief-010 FR-005
                "promotion_stories": [asdict(story) for story in promotion.story_blocks(reg, p)]}

    def memo_close(self, competitor: bool, cuts: list[str] | None = None, running: list[str] | None = None) -> dict:
        """§1 and §5 once the stories are closed (contracts/mcp-admin-tools.md): the bottom line in FR-021 order
        with the number least sure of, and the next checks. `cuts` are the plan ids of the plan cut cards the brief
        keeps (brief-010 FR-007): code builds each from the plan's own figures and its territory's checks. `running` are
        the territories of the continuing cards the brief keeps (FR-012): events that began before the comparison weeks."""
        reg, p = self._reg(), self.p
        if self.proj is None:
            raise ToolError("brief_sections must run before memo_close")
        told = [{"territory": t, "confidence": st["confidence"],
                 "drivers": [d for d, v in st["verdicts"].items() if v == "supported"],
                 "lags": {d: c.detail["lag"] for d, c in self.checks.get(t, {}).items() if c.detail and "lag" in c.detail}}
                for t, st in self.stories.items() if st["closed"]]
        story_charts = {}
        for s in told:  # brief-003 FR-024: same builders as the scripted brief
            access = self.checks.get(s["territory"], {}).get("access")
            plan = (access.detail or {}).get("plan") if access else None
            drivers = s["drivers"] if s["confidence"] != "Low" else []
            story_charts[s["territory"]] = charts.story(reg, p, s["territory"], drivers, plan)
        investigated = list(told)  # the story territories the checks ran on, before any continuing card joins `told`
        running_stories, running_details, running_cards = [], {}, {}
        if running:  # brief-010 FR-012: a continuing card joins §1 and §5 like a territory story
            covered = {s["territory"] for s in told} | {splits.plan_territory(reg, plan) for plan in (cuts or [])}
            for event in continuing.screen(reg, p, covered, set(cuts or []), most=None):  # every running event: the kept ones are picked by territory, never re-ranked out
                if event["territory"] in running:
                    block, info = continuing.block(reg, p, event)
                    running_cards[block.id], running_details[block.id] = block.card, block.detail
                    running_stories.append({"id": block.id, "territory": event["territory"], "title": block.title,
                                            "section": "\n".join(block.lines)})
                    told.append(info)
        top: dict = {}
        bottom = memo.bottom_line(reg, p, self.proj, told, self.restated, facts=top)
        cards = {s["territory"]: memo.story_card(q.name(s["territory"]), self.story_facts[s["territory"]], s["confidence"],
                                                 list(self.checks.get(s["territory"], {})), territory=s["territory"],
                                                 checks=list(self.checks.get(s["territory"], {}).values()), measure=p.col)
                 for s in told if s["territory"] in self.story_facts}
        national_story = None  # packet NC: every brief has one national card; the competitor story's, else a block of its own
        if p.has("national"):
            comp = self.competitor_facts if competitor and self.competitor_facts else None
            reading = stages.national_reading(reg, p, [self.checks.get(s["territory"], {}) for s in investigated], comp, self.facts.get("avg"),
                                              data_artifact=bool(self.facts.get("data_artifact")))
            if comp:
                cards["competitor"] = memo.competitor_card(p, reading or comp)
            elif reading:
                national_story = asdict(memo.national_block(p, reading))
        cut_stories, cut_details = [], {}
        for plan in dict.fromkeys(cuts or []):
            t = splits.plan_territory(reg, plan)
            if t is None or t not in p.ok or not p.has("plan"):
                continue
            block = memo.cut_block(reg, p, {"territory": t, "plan": plan}, list(self.checks.get(t, {}).values()) or None)
            cards[block.id], cut_details[block.id] = block.card, block.detail
            cut_stories.append({"id": block.id, "territory": t, "title": block.title, "section": "\n".join(block.lines)})
        return {"bottom_line": bottom, "kpis": memo.kpis(p, self.proj, top), "details": {"1": memo.bottom_detail(top)},
                "story_cards": {**cards, **running_cards},
                "story_details": {**{s["territory"]: self.story_detail.get(s["territory"], []) for s in told}, **cut_details, **running_details},
                "cut_stories": cut_stories, "continuing_stories": running_stories, "national_story": national_story,
                "next_checks": memo.next_checks(p, told, competitor),
                "driver_timing": memo.driver_timing(told),
                "charts": {**({"2": charts.trend(reg, p)} if p.has("national") else {}), "4": charts.coverage(reg, p), "stories": story_charts,
                           "competitor": charts.competitor(reg, p) if competitor else None}}

    def story_section(self, territory: str, n: int) -> str:
        """One story as the agents left it: head, the checks they ran in the order run, the closing confidence."""
        t = self._territory(territory)
        if t is None:
            raise ToolError(self._bad_territory(territory))
        if self.p.promotion and t == self.p.focus and "promotion" not in self.checks.get(t, {}):
            self.check_promotion(t)
        facts: dict = {}
        head = f"Story {_ORD.get(n, str(n))}: {stages.territory_change(self._reg(), self.p, t, facts)}"
        self.story_facts[t] = facts
        done = list(self.checks.get(t, {}).values())
        movers = splits.segment_line(self._reg(), self.p, t)  # brief-010 FR-003
        lines = [head] + ([movers] if movers else []) + (["Checked, in this order:"] + [f"- {c.text}" for c in done] if done else ["No driver was tested before the cap."])
        lines.append(memo.without_next(self._status(t, closing=True)))  # its next check goes to §5
        self.story_detail[t] = memo.story_detail(self._reg(), self.p, t)  # folded, not in the story's text
        return "\n".join(lines)

    def competitor_section(self, lead: str) -> str:
        self._reg()
        if not self.p.has("national"):  # the competitor story is a national story
            return ""
        facts: dict = {}
        text = stages.competitor_status(self._reg(), self.p, lead=lead, facts=facts) or ""
        self.competitor_facts = facts
        return text

    def dropped_line(self) -> str:
        reg, p = self._reg(), self.p
        if p.calendar:
            return ""
        _found, quiet = stages.screen(reg, p)
        return stages.dropped_line(reg, p, quiet) if quiet else ""

    def _record(self, t: str, check: Check) -> str:
        self.checks.setdefault(t, {})[check.driver] = check
        if self.follow_up:
            return self._out(f"{q.name(t)}. {check.text}")
        return self._out(f"{q.name(t)}. {check.text}\n{self._status(t, closing=False)}")

    def split_change(self, territory: str, by: str) -> str:
        """A territory's change split by plan, specialty or channel: each cut's weekly brand TRx in the period
        against the weeks before, the largest moves first, small cells marked noisy (brief-003 FR-015)."""
        self._log("split_change", territory=territory, by=by)
        t = self._territory(territory)
        if t is None:
            return self._bad_territory(territory)
        if by not in splits.SPLITS:
            return f"Unknown split {by!r}. Use one of: {', '.join(splits.SPLITS)}."
        if (withheld := self._withheld(t)):
            return withheld
        return self._out("\n".join(splits.split_change(self._reg(), self.p, t, by)))

    def check_access(self, territory: str) -> str:
        return self._driver("check_access", territory, check_access, reference=False)

    def check_promotion(self, territory: str) -> str:
        return self._driver("check_promotion", territory, check_promotion, reference=True)

    def check_supply(self, territory: str) -> str:
        return self._driver("check_supply", territory, check_supply, reference=False)

    def check_competitor(self, territory: str) -> str:
        return self._driver("check_competitor", territory, check_competitor, reference=True)

    def competitor_status(self) -> str:
        self._log("competitor_status")
        if not self.p.has("national"):
            return "This brief's levels leave out national figures, so the competitor story is not part of it."
        text = stages.competitor_status(self.reg, self.p)
        return self._out(text) if text else "Metacora is not a story in these weeks: not launched yet, or still a small share of the basket."

    def story_confidence(self, territory: str) -> str:
        self._log("story_confidence", territory=territory)
        t = self._territory(territory)
        if t is None:
            return self._bad_territory(territory)
        return self._status(t, closing=True)

    def _status(self, t: str, closing: bool) -> str:
        """Confidence by code from the checks run so far (Briefing scale); every driver check reports it."""
        done = self.checks.get(t, {})
        missing = [d for d in DRIVERS if d not in done]
        level, lead = confidence(list(done.values()))
        if missing and level == "High":
            level = "Medium"  # an untested driver is an alternative still open
        supported = [c for c in done.values() if c.verdict == "supported"]
        self.stories[t] = {"confidence": level, "lead": None if level == "Low" else lead, "not_tested": missing,
                           "verdicts": {d: c.verdict for d, c in done.items()}, "closed": closing}
        if not closing:
            return (f"Story so far for {q.name(t)}: confidence {level}"
                    + (f", candidate drivers: {lead}" if level != "Low" else ", no driver supported yet")
                    + (f". Not tested yet: {', '.join(missing)}." if missing else ". Every driver is tested.")
                    + " Close the story with story_confidence.")
        if level == "Low":
            text = (f"Confidence for {q.name(t)}: Low. Unresolved, investigate next. No driver is named. "
                    f"Next: split {q.name(t)} by plan and specialty, and ask sales leadership for local context.")
        else:
            verb = "Leading driver" if level == "High" else "Candidate drivers"
            text = f"Confidence for {q.name(t)}: {level}. {verb}: {lead}. Next: involve {', '.join(OWNER[c.driver] for c in supported)}."
        if missing:
            text += f" Not tested: {', '.join(missing)}."
        return text


def build_server(db=DEFAULT_DB, legend: bool = False) -> MCPServer:
    """A fresh server with one session. Over stdio, one process serves one run at a time."""
    s = RunSession(db, legend=legend)
    server = MCPServer(
        name="pharmagentics",
        instructions=("Governed, read-only tools over the PharmAgentics synthetic data (the product the run opens with, BXA Cardiovela unless open_run names another). "
                      "The caller opens a run first. Numbers come back as claim tokens like {c7}: write the token, "
                      "never the number; code fills it in."),
    )
    text = dict(structured_output=False)

    @server.tool(**text)
    async def open_run(question: str, comparison: Comparison | None = None, definition: Definition | None = None,
                       brand_id: str = "BXA") -> str:
        """Admin: start a run for one question and one brand under a brief definition. Pins the period and the data version. Callers only, not agents."""
        return s.open_run(question, comparison, definition, brand_id)

    @server.tool(**text)
    async def export_run() -> str:
        """Admin: the run's claims, evidence items and verdicts as JSON. Callers only, not agents."""
        return json.dumps(s.export_run(), default=str)

    @server.tool(**text)
    async def brief_sections() -> str:
        """Admin: the memo's code-built title, numbers, limits and appendix as JSON. Callers only."""
        return json.dumps(s.brief_sections())

    @server.tool(**text)
    async def promotion_review() -> str:
        """Admin: render the code-built review for a run pinned to release-wide promotion."""
        reg = s._reg()
        if not s.p.promotion_review:
            raise ToolError("This run is pinned to a dated briefing.")
        return json.dumps(promotion.render_review(reg, s.p), default=str)

    @server.tool(**text)
    async def memo_close(competitor: bool, cuts: list[str] | None = None, running: list[str] | None = None) -> str:
        """Admin: the memo's bottom line and next checks as JSON, after the stories close, with the plan cut cards
        (by plan id) and the continuing cards (by territory) the brief keeps. Callers only."""
        return json.dumps(s.memo_close(competitor, cuts, running))

    @server.tool(**text)
    async def story_section(territory: str, n: int) -> str:
        """Admin: one story as the agents left it (head, checks run, confidence). Callers only."""
        return s.story_section(territory, n)

    @server.tool(**text)
    async def competitor_section(lead: str) -> str:
        """Admin: the Metacora story line, by code. Callers only."""
        return s.competitor_section(lead)

    @server.tool(**text)
    async def dropped_line() -> str:
        """Admin: the 'considered and dropped' line, by code. Callers only."""
        return s.dropped_line()

    @server.tool(**text)
    async def feed_health() -> str:
        """Which territory-week cuts pass the feed gate for the run's weeks, why any are withheld, and the like-for-like territories. Call this first."""
        return s.feed_health()

    @server.tool(**text)
    async def restatements() -> str:
        """The brand's restatements touching the run's weeks: old and new values. Quote the new value with the note."""
        return s.restatements()

    @server.tool(**text)
    async def national_kpis() -> str:
        """National TRx of the run's brand: like for like against the weeks before, week over week for a one-week period, a headline total distorted by withheld cuts, and calendar effects."""
        return s.national_kpis()

    @server.tool(**text)
    async def check_data(territory: str) -> str:
        """Data-artifact check for one territory: do its cuts in these weeks pass the feed gate? Verdict by code."""
        return s.check_data(territory)

    @server.tool(**text)
    async def screen_territories() -> str:
        """Competitive intelligence: territories whose change in the run's brand is beyond their normal range and their peers', largest impact first."""
        return s.screen_territories()

    @server.tool(**text)
    async def territory_change(territory: str) -> str:
        """One territory's TRx for the run's brand in the run's weeks against the weeks before, and the other territories' change."""
        return s.territory_change(territory)

    @server.tool(**text)
    async def check_access(territory: str) -> str:
        """Driver check: did a payer plan in this territory change the brand's tier, prior authorization, step therapy or coverage? Verdict by code."""
        return s.check_access(territory)

    @server.tool(**text)
    async def check_promotion(territory: str) -> str:
        """Driver check: did aggregated rep calls in this territory change? Supported only as an association. Verdict by code."""
        return s.check_promotion(territory)

    @server.tool(**text)
    async def check_supply(territory: str) -> str:
        """Driver check: was the brand's inventory fill low or backordered in this territory? Verdict by code."""
        return s.check_supply(territory)

    @server.tool(**text)
    async def check_competitor(territory: str) -> str:
        """Driver check: was competitor Metacora stronger in this territory than elsewhere before the change? Verdict by code."""
        return s.check_competitor(territory)

    @server.tool(**text)
    async def competitor_status() -> str:
        """Metacora (competitor, launched 2026-03-02) as a continuing national story: weeks since launch, direction, basket shares."""
        return s.competitor_status()

    @server.tool(**text)
    async def split_change(territory: str, by: Literal["plan", "specialty", "channel"]) -> str:
        """A territory's change split by "plan", "specialty" or "channel": each cut's weekly TRx for the run's brand in these weeks against the weeks before, largest moves first; small cells are marked noisy."""
        return s.split_change(territory, by)

    @server.tool(**text)
    async def story_confidence(territory: str) -> str:
        """Close a territory story: confidence (High, Medium or Low), leading driver and who to involve, computed by code from the checks run so far."""
        return s.story_confidence(territory)

    return server
