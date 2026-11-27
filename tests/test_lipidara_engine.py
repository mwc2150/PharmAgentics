"""Lipidara (BXC) has the Briefing functionality Cardiovela (BXA) has: the lag-tested driver checks, the promotion
lapse rule and review, the question reader and the agent engine, each on the brand's own rows (core-010 v2).

No model is called. The agent's model turns are stubbed; its tool calls go through the real MCP session.
"""
from __future__ import annotations

import re

import json
import shutil
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api import service  # noqa: E402
from pharmagentics.mcp_server import RunSession  # noqa: E402
from pharmagentics.tools import Registry, memo, promotion, stages  # noqa: E402
from pharmagentics.tools.brands import BRIEFING_ENGINES  # noqa: E402
from pharmagentics.tools.lag_checks import run_checks  # noqa: E402

needs_db = pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
Q = "Week of 2026-10-05 in Southeast: What moved?"
DRIVERS = ["data", "access", "promotion", "supply", "competitor"]


def _checks(brand: str, question: str = Q):
    reg = Registry(service.DB)
    try:
        p = stages.resolve(reg, question, brand)
        checks = run_checks(reg, "SOUTHEAST", p.weeks, p.baseline, brand_id=brand)
        for c in checks:
            c.text = reg.render(c.text)  # the claim tokens filled, so two runs' texts can be compared
        return checks, reg.evidence
    finally:
        reg.close()


@pytest.fixture(scope="module")
def planted_db(tmp_path_factory):
    """A copy of the release with a promotion lapse planted in Lipidara's Pacific calls (Aug 3 to Sep 14), so the
    lapse rule has something to find. Cardiovela's rows are untouched."""
    path = tmp_path_factory.mktemp("bxc") / "release.duckdb"
    shutil.copy(service.DB, path)
    with duckdb.connect(str(path)) as con:
        con.execute("update raw.promo_activity set rep_calls_aggregated = 5 where product_id = 'BXC' and territory_id = 'PACIFIC' "
                    "and week_start between date '2026-08-03' and date '2026-09-14'")
    return path


# --- the engine list -------------------------------------------------------------------------------------------

def test_both_brands_list_both_engines():
    assert BRIEFING_ENGINES["BXA"] == BRIEFING_ENGINES["BXC"] == ("scripted", "agent")


# --- driver checks: the same lag-tested checks, on the brand's own rows ----------------------------------------

@needs_db
def test_bxc_gets_the_lag_checks_in_the_same_order_and_never_reads_bxa_rows():
    bxa, _ = _checks("BXA")
    bxc, evidence = _checks("BXC")
    assert [c.driver for c in bxc] == [c.driver for c in bxa] == DRIVERS
    assert "BXA" not in " ".join(c.text for c in bxc)
    assert not [e for e in evidence if "'BXA'" in (e.get("query") or "")], "a BXC check read BXA rows"
    assert any("product_id = 'BXC'" in (e.get("query") or "") for e in evidence)
    # the lag-tested wording is the lag checks', not the cruder brand checks'
    text = " ".join(c.text for c in bxc)
    assert "No tested lag lines up with TRx" in text and "in the tested months" in text


@needs_db
def test_the_assumptions_drivers_line_applies_to_bxc():
    from briefing_baseline.pipeline import answer

    for brand in ("BXA", "BXC"):
        text = answer(Q, brand_id=brand)["answer"]
        assert "- Drivers: the checks evaluate the same week and delays of one and two weeks." in text, brand
        assert "Metacora's local share: 2026-07-06 to 2026-09-28." in text, brand


# --- promotion: the lapse rule and the review on the brand's own promo rows -----------------------------------

@needs_db
def test_the_lapse_rule_reads_each_brands_own_rows(planted_db):
    reg = Registry(planted_db)
    try:
        assert [(e.territory, e.start, e.end) for e in promotion.lapses(reg, None, "BXC")] == [("PACIFIC", "2026-08-03", "2026-09-14")]
        assert [e.territory for e in promotion.lapses(reg, None)] == ["GREAT_LAKES", "SOUTHEAST"]  # Cardiovela's, as before
        assert [e.territory for e in promotion.lapses(reg, None, "BXA")] == ["GREAT_LAKES", "SOUTHEAST"]
    finally:
        reg.close()


@needs_db
def test_a_lapse_in_the_comparison_is_named_for_bxc(planted_db):
    from briefing_baseline.pipeline import answer

    text = answer("Week of 2026-10-05 in Pacific: What moved?", db=planted_db, brand_id="BXC")["answer"]  # TRx up, calls back up
    # Recovery is named either way: as the verdict, or, when Pacific moved within its normal range and nothing is
    # credited (brief-011 I6), as the context the calls came back from.
    assert re.search(r"(recovery|came back) after the promotion lapse of 2026-08-03 to 2026-09-14", text)
    assert "BXA" not in text


@needs_db
def test_the_promotion_review_runs_for_bxc_on_bxc_rows(planted_db):
    from briefing_baseline.pipeline import answer

    out = answer("Promotion review in National: Did the campaign reach the people it was meant to?", db=planted_db, brand_id="BXC")
    text = out["answer"]
    assert out["brand_id"] == "BXC" and text.startswith("# BXC Promotion review")
    assert "From 2026-08-03 to 2026-09-14, aggregated calls in Pacific averaged" in text and "BXC TRx averaged" in text
    assert "BXA" not in text
    assert not [e for e in out["evidence"] if "'BXA'" in (e.get("query") or "")], "the review read BXA rows"
    own = answer("Promotion review in National: Did the campaign reach the people it was meant to?", brand_id="BXA")["answer"]
    assert own.startswith("# BXA Promotion review") and "aggregated calls in Great Lakes averaged" in own


@needs_db
def test_the_release_wide_review_without_a_lapse_says_so_for_bxc():
    from briefing_baseline.pipeline import answer

    text = answer("Promotion review in National: Did the campaign reach the people it was meant to?", brand_id="BXC")["answer"]
    assert "No territory had a coverage lapse of three weeks or more in this scope." in text


# --- the question reader ---------------------------------------------------------------------------------------

@needs_db
def test_the_question_reader_reads_a_promotion_question_for_bxc():
    reg = Registry(service.DB)
    try:
        for brand in ("BXA", "BXC"):
            p = stages.resolve(reg, "Did the campaign reach the people it was meant to?", brand)
            assert p.promotion_review and p.brand_id == brand, brand
    finally:
        reg.close()


# --- the agent engine, offline ---------------------------------------------------------------------------------

@needs_db
def test_the_mcp_session_opens_a_run_for_the_named_brand():
    s = RunSession()
    try:
        opened = s.open_run(Q, brand_id="BXC")
        assert "Product: BXC (Lipidara)" in opened and s.p.brand_id == "BXC"
        for tool in (s.check_data, s.check_access, s.check_promotion, s.check_supply, s.check_competitor):
            assert "BXA" not in tool("SOUTHEAST")
        assert "BXA" not in s.restatements() and "BXA" not in s.territory_change("SOUTHEAST")
        assert not [e for e in s.reg.evidence if "'BXA'" in (e.get("query") or "")]
        assert "Product: BXA (Cardiovela)" in s.open_run(Q)  # the default is still Cardiovela
        with pytest.raises(ValueError):
            s.open_run(Q, brand_id="BXD")  # no Briefing workflow for Vascriva
    finally:
        s.close()


@needs_db
def test_the_agents_checks_equal_the_scripted_checks_for_bxc():
    """I5 for Lipidara: the MCP tools call the same checks, so their text is the scripted brief's."""
    scripted, _ = _checks("BXC")
    s = RunSession()
    try:
        s.open_run(Q, brand_id="BXC")
        for tool in (s.check_data, s.check_access, s.check_promotion, s.check_supply, s.check_competitor):
            tool("SOUTHEAST")
        assert {d: s.reg.render(c.text) for d, c in s.checks["SOUTHEAST"].items()} == {c.driver: c.text for c in scripted}
    finally:
        s.close()


def test_the_prompts_name_the_brand_of_the_run():
    from briefing_agent import followup
    from briefing_agent.investigate import story_task
    from briefing_agent.scope import out_of_scope

    here = ROOT / "agents" / "brand-briefing" / "briefing_agent" / "prompts"
    manager = (here / "manager.md").read_text(encoding="utf-8")
    triage = (here / "manager_triage.md").read_text(encoding="utf-8")
    writer = (here / "writer.md").read_text(encoding="utf-8")
    for text in (manager, triage, writer):
        assert "BXA" not in text and "{brand}" in text  # the brand comes from the run, never from the prompt
    assert "fictional brand BXC" in manager.replace("{brand}", "BXC")
    assert "BXA" not in story_task({"title": "t", "territory": "SOUTHEAST"}, ["data"], None, "BXC")
    assert "weekly BXC brief" in story_task({"title": "t", "territory": "SOUTHEAST"}, ["data"], None, "BXC")
    assert "BXA" not in followup.PROMPT and "what BXC did" in out_of_scope("Where should the next dollar go?", "BXC")


@needs_db
def test_the_agent_runs_a_bxc_brief_end_to_end_with_a_stubbed_model(monkeypatch):
    """A stubbed model, the real MCP session and the real memo builders: the brief is Lipidara's from the plan to the
    envelope, its numbers are claim tokens, and no BXA row or word reaches it."""
    import importlib

    import briefing_agent as agent
    from briefing_lowcode.team import _call  # noqa: F401
    inv = importlib.import_module("briefing_agent.investigate")
    seen = {}

    async def fake_ask(spec, prompt, log, name):
        seen.setdefault(name, prompt)
        return json.dumps({"answer": "The brief is as the code sections show.", "stories": {}}) if name == "writer" else '{"order": []}'

    async def fake_team(cfg, spec, mcp, task, log, wall, brand_id="BXA"):
        seen["task"], seen["team_brand"] = task, brand_id
        t = task.split("territory ID ")[1].split(")")[0]
        for tool in ("check_data", "check_access", "check_promotion", "check_supply", "check_competitor", "story_confidence"):
            await _call(mcp, tool, territory=t)

    monkeypatch.setattr(agent, "_ask", fake_ask)
    monkeypatch.setattr(inv, "_team", fake_team)
    plan = agent.triage("Week of 2026-07-13 in Mid-Atlantic: Generate the weekly brand-performance briefing.", "ollama:stub", brand_id="BXC")
    assert plan["brand_id"] == "BXC" and plan["engine"] == "agent"
    decision = {"plan_id": plan["plan_id"], "stories": plan["manager_order"]}
    out = agent.run_with_plan("Week of 2026-07-13 in Mid-Atlantic: Generate the weekly brand-performance briefing.", decision, plan, "ollama:stub")
    env = out["envelope"]
    assert env["brand_id"] == "BXC" and "Product: BXC (Lipidara)" in env["answer"]
    assert "BXA" not in env["answer"] and not [e for e in env["evidence"] if "'BXA'" in (e.get("query") or "")]
    assert "fictional brand BXC" in seen["writer"] and "BXA" not in seen["writer"]
    assert seen["team_brand"] == "BXC" and "weekly BXC brief" in seen["task"]
    # the envelope passes the app's own admission checks for a BXC agent brief
    service._matching_brand("BXC", env)


@needs_db
def test_the_agent_answer_for_a_brand_goes_through_the_same_entry_the_harness_calls(monkeypatch):
    import briefing_agent as agent

    async def triage(question, spec, log, comparison=None, definition=None, brand_id="BXA"):
        seen["triage"] = brand_id
        return {"manager_order": [], "brand_id": brand_id}

    async def run(question, plan, order, spec, reviewed, log):
        seen["run"] = plan["brand_id"]
        return {"envelope": {"answer": "brief", "brand_id": plan["brand_id"], "trajectory": {"llm_calls": 0}}}

    async def proposal(question, spec, log, brand_id="BXA"):
        seen["reader"] = brand_id
        return None

    seen: dict = {}
    monkeypatch.setattr(agent, "_triage", triage)
    monkeypatch.setattr(agent, "_run", run)
    monkeypatch.setattr(agent, "_scope_proposal", proposal)
    assert agent.answer("q", "ollama:x", brand_id="BXC")["brand_id"] == "BXC"
    assert seen == {"triage": "BXC", "run": "BXC", "reader": "BXC"}


def test_the_worker_runs_a_bxc_job_and_refuses_a_brand_with_no_agent(monkeypatch):
    import briefing_agent as agent
    from briefing_agent.worker import run_job

    got = {}

    def triage(question, model, *, events=None, brand_id="BXA", **options):
        got.update(brand_id=brand_id, model=model)
        return {"plan_id": "t-x", "brand_id": brand_id}

    monkeypatch.setattr(agent, "triage", triage)
    out = run_job({"id": "j", "kind": "triage", "payload": {"question": "q", "query": {"brand_id": "BXC"}}}, "ollama:stub")
    assert got == {"brand_id": "BXC", "model": "ollama:stub"} and out["brand_id"] == "BXC"
    with pytest.raises(ValueError, match="does not support"):
        run_job({"id": "j", "kind": "triage", "payload": {"question": "q", "query": {"brand_id": "BXD"}}}, None)


def test_the_followup_prompt_is_filled_with_the_briefs_brand():
    from briefing_agent import followup

    prompt = followup.PROMPT.format(brand="BXC", scope="BXC, Southeast, week of 2026-10-05", sections="", about="", question="q")
    assert "fictional brand BXC" in prompt and "BXA" not in prompt
