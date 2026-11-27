"""The agent team, described for the "How it works" tab (brief-009 FR-006).

`GET /api/briefing/agents` returns the flow from question to brief, the four actors (Manager, Data Forensics, Driver
Investigator and the Writer step) with job, tools and where their output lands, and the latest scripted-versus-agent
comparison from the telemetry the Evaluation page already reads. Everyone with a Briefing role gets all of that.
Only a role that holds the analyst view (the Commercial Analyst, and the test login while it views as the analyst)
also gets each prompt verbatim from the repository; a leadership role never does. Nothing here reads `eval/` or the
golden cases: the comparison is the aggregate snapshot that is already public to every signed-in role.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Response

from . import rbac, telemetry

logger = logging.getLogger(__name__)
AGENT_DIR = Path(__file__).resolve().parents[3] / "agents" / "brand-briefing" / "briefing_agent"

router = APIRouter(prefix="/api/briefing", tags=["briefing"])

# Plain-words line for every governed tool an agent can call (pharmagentics.mcp_server.AGENT_TOOLS; a test keeps the two in step).
TOOLS = {
    "check_data": "Verdict on whether a territory's data can be trusted",
    "feed_health": "Which territory-weeks pass the feed gate, and why others are withheld",
    "restatements": "Past figures that were restated",
    "national_kpis": "The like-for-like national change",
    "screen_territories": "Which territories moved beyond their normal range",
    "territory_change": "How far one territory moved, and against what",
    "check_access": "Tests payer access as the driver, verdict by code",
    "check_promotion": "Tests promotion after the controls (access, competitor, calendar), against territories without a promotion change; verdict by code",
    "check_supply": "Tests supply as the driver, verdict by code",
    "check_competitor": "Tests the competitor as the driver, verdict by code",
    "competitor_status": "Competitive intelligence on Metacora, a continuing story",
    "story_confidence": "The story's confidence, computed by code",
}

ACTORS = [
    {"id": "manager", "name": "Manager", "kind": "agent",
     "job": "Plans which stories to investigate and in what order, then keeps each story on track until it is closed.",
     "tools": [],
     "tools_note": "No data tools of its own. It reads the code's screening of the territories and asks the two specialists.",
     "lands": "The order of the stories in section 3, and which drivers each story tests. It never writes a number.",
     "steps": [("manager_triage", "Plan the stories"), ("manager", "Coordinate a story"), ("story_done", "Is the story done?")]},
    {"id": "data_forensics", "name": "Data Forensics", "kind": "agent",
     "job": "Checks whether a story's data can be trusted before anyone explains it. A change on withheld or wrong data is a data artifact, not a business story.",
     "tools": ["check_data", "feed_health", "restatements", "national_kpis"],
     "lands": "The data-health lines and the first check in every story card.",
     "steps": [("data_forensics", "Check the data")]},
    {"id": "driver_investigator", "name": "Driver Investigator", "kind": "agent",
     "job": "Tests why a territory moved: access, promotion, supply and competitor, each with a verdict by code, then closes the story.",
     "tools": ["screen_territories", "territory_change", "check_access", "check_promotion", "check_supply",
               "check_competitor", "competitor_status", "story_confidence"],
     "lands": "The drivers checked, the verdicts and the confidence on each story card.",
     "steps": [("driver_investigator", "Test a driver")]},
    {"id": "writer", "name": "Writer", "kind": "llm",
     "job": "Writes the plain-language paragraphs from sections that code has already built. It is a model step, not an agent: it decides nothing and calls no tools.",
     "tools": [],
     "tools_note": "No tools. It may only copy claim tokens that code supplies; a sentence that breaks a rule is rewritten once.",
     "lands": "The closing paragraph of the bottom line, one paragraph on each story card, and the chart explanations.",
     "steps": [("writer", "Draft the paragraphs"), ("revise", "Rewrite a sentence")]},
]

FLOW = [
    {"n": 1, "actor": "Code", "kind": "code", "title": "Check the data and screen the territories",
     "note": "Applies the feed gate, finds the territories that moved beyond their normal range and proposes the stories."},
    {"n": 2, "actor": "Manager", "kind": "agent", "title": "Plan the stories",
     "note": "Keeps, drops or reorders the proposed stories and picks the drivers to test first."},
    {"n": 3, "actor": "Person", "kind": "person", "title": "You review the plan",
     "note": "Nothing is investigated until you approve the stories."},
    {"n": 4, "actor": "Data Forensics, Driver Investigator", "kind": "agent", "title": "Investigate each story",
     "note": "Data Forensics checks the data, then the Driver Investigator tests the drivers one by one. The Manager decides when the story is done. Every verdict comes from code."},
    {"n": 5, "actor": "Code", "kind": "code", "title": "Build the memo",
     "note": "Builds every section, table and chart. Every number is a claim token that code fills from a governed query."},
    {"n": 6, "actor": "Writer", "kind": "llm", "title": "Draft the paragraphs",
     "note": "Words the closing paragraph and one paragraph for each story. Code checks every sentence and sends back any that break a rule."},
    {"n": 7, "actor": "Person", "kind": "person", "title": "You review and approve",
     "note": "The Brand Director sees an executive summary only after you approve."},
]

ENGINES = {
    "scripted": "The scripted engine runs the same checks in a fixed order. Code does every step and no model is called. It shows the same timeline, with Code as the actor.",
    "agent": "The agent team lets a model choose which stories to keep, which checks to run and in what order, within caps on rounds and time. Verdicts, confidence and every number still come from code.",
}

# (group, label, metric, unit). The comparison reads these from the latest scripted and agent runs.
COMPARE = [
    ("What it finds", "Key facts found", "key_fact_recall", "share"),
    ("What it finds", "Findings found", "finding_recall", "share"),
    ("Checks that must hold", "Numbers traced to a source", "numbers_traced", "share"),
    ("Checks that must hold", "Claims match their evidence", "claims_reconcile", "share"),
    ("Checks that must hold", "Links resolve", "links_resolve", "share"),
    ("Checks that must hold", "Governed terms", "governed_terms", "share"),
    ("Checks that must hold", "No banned phrases", "must_not_say", "share"),
    ("Checks that must hold", "No individual rep named", "no_individual_rep", "share"),
    ("Time and effort", "Time a brief, typical", "latency_brief_p50", "seconds"),
    ("Time and effort", "Time a brief, slowest 5 in 100", "latency_brief_p95", "seconds"),
    ("Time and effort", "Model calls a brief", "llm_calls", "count"),
    ("Time and effort", "Tool calls a brief", "tool_calls", "count"),
]


def _prompt(step_id: str, step: str, with_text: bool) -> dict:
    path = AGENT_DIR / "prompts" / f"{step_id}.md"
    raw = path.read_bytes()
    out = {"id": step_id, "step": step, "file": f"{step_id}.md", "hash": hashlib.sha256(raw).hexdigest()[:7]}
    out["ref"] = f"{step_id}@{out['hash']}"
    if with_text:
        out["text"] = raw.decode("utf-8")
    return out


def _limits() -> dict | None:
    try:
        cfg = yaml.safe_load((AGENT_DIR / "agent.yaml").read_text(encoding="utf-8"))
        return {"rounds_a_story": cfg["caps"]["max_round_count"], "seconds_a_story": cfg["story_wall_seconds"],
                "seconds_a_run": cfg["run_wall_seconds"]}
    except (OSError, KeyError, TypeError, ValueError):
        logger.warning("Agent limits not read from agent.yaml")
        return None


def sees_prompts(role: rbac.Role) -> bool:
    """The analyst view (and the test login while it views as the analyst) may read the prompts; leadership never."""
    return rbac.ANALYST in role.views


def actors(with_prompts: bool) -> list[dict]:
    out = []
    for a in ACTORS:
        card = {k: v for k, v in a.items() if k not in ("steps", "tools")}
        card["tools"] = [{"name": t, "does": TOOLS[t]} for t in a["tools"]]
        card["steps"] = [label for _, label in a["steps"]]
        if with_prompts:
            card["prompts"] = [_prompt(pid, label, True) for pid, label in a["steps"]]
        out.append(card)
    return out


def comparison(snap: dict) -> dict:
    """The latest scripted and agent runs side by side, from the aggregate snapshot the Evaluation page reads."""
    def latest(system: str) -> dict | None:
        runs = [r for r in snap.get("latest", []) if r.get("system") == system and r.get("lane") == "briefing" and not r.get("control")]
        return max(runs, key=lambda r: r.get("started", ""), default=None)

    scripted, agent = latest("briefing_scripted"), latest("briefing_agent")
    if scripted is None or agent is None:
        return {"available": False, "note": "No scripted and agent run has been scored together yet.", "rows": []}
    def run(r: dict) -> dict:
        return {k: r.get(k) for k in ("run_id", "started", "cases", "model")}
    rows = [{"group": g, "label": label, "unit": unit, "scripted": scripted.get("metrics", {}).get(m),
             "agent": agent.get("metrics", {}).get(m)} for g, label, m, unit in COMPARE]
    # The agent's estimated model cost an answer (eval/harness/cost.py, from its token counts); the scripted engine
    # calls no model, so it costs nothing.
    cost = agent.get("metrics", {}).get("cost_usd_brief")
    rows.append({"group": "Time and effort", "label": "Cost a brief", "unit": "cost", "scripted": 0.0, "agent": cost,
                 "note": "Estimated from the tokens the model read and wrote, at list prices." if cost is not None
                 else "Not recorded in this agent run."})
    return {"available": True, "scripted": run(scripted), "agent": run(agent), "rows": rows,
            "note": "Scores on the same golden questions. Run-level figures only."}


def driving_model(snap: dict) -> dict:
    from . import agent_host

    spec = agent_host.model()
    if spec:
        return {"spec": spec, "source": "app"}
    runs = [r for r in snap.get("latest", []) if r.get("system") == "briefing_agent" and r.get("model")]
    if runs:
        return {"spec": max(runs, key=lambda r: r.get("started", ""))["model"], "source": "evaluation"}
    return {"spec": None, "source": None}


@router.get("/agents")
def agents(response: Response, who: tuple[rbac.Principal, rbac.Role] = Depends(rbac.require_briefing)) -> dict:
    _, role = who
    rbac.allow(role, "read")
    response.headers["Cache-Control"] = "no-store"
    snap = telemetry.snapshot()
    return {"model": driving_model(snap), "limits": _limits(), "engines": ENGINES, "flow": FLOW,
            "actors": actors(sees_prompts(role)), "comparison": comparison(snap), "prompts_shown": sees_prompts(role)}
