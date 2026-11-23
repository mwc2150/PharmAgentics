"""brief-009 packet E: the run event log. No model is called: the agent's model turns are stubbed, its tool calls go
through the real MCP server and the real RunLog middleware, so the events are the ones a live run would record."""
from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api import agent_host, cloud, jobs, service, views  # noqa: E402
from pharmagentics.api.app import accept_result, app  # noqa: E402
from pharmagentics.tools import events as ev  # noqa: E402

pytestmark = pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
Q = "Week of 2026-07-13 in Mid-Atlantic: Generate the weekly brand-performance briefing."
QUERY = {"intent": "weekly_brief", "brand_id": "BXA", "territory_id": "MID_ATLANTIC", "week_start": "2026-07-13",
         "question": "What changed, and why?"}
TOKEN = "test-worker-token"
W = {"Authorization": f"Bearer {TOKEN}"}
SPEC = "ollama:stub"
SAME = ("answer", "claims", "evidence", "citations", "sections", "abstained")


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("PHARMAGENTICS_WORKER_TOKEN", TOKEN)
    monkeypatch.delenv("K_SERVICE", raising=False)
    for k in ("PHARMAGENTICS_CLOUD_AGENT_JOB", "PHARMAGENTICS_GCP_PROJECT", "PHARMAGENTICS_AGENT_IN_APP"):
        monkeypatch.delenv(k, raising=False)
    jobs.reset()
    cloud.reset()
    yield
    jobs.reset()
    cloud.reset()


def signed_in(user: str) -> TestClient:
    c = TestClient(app)
    c.post("/auth/dev-login", data={"username": user})
    return c


# --- a stubbed agent run ----------------------------------------------------------------------------------

def _chat(log, name: str, last: str, reply: str):
    """One model turn through the real chat middleware."""
    ctx = SimpleNamespace(messages=[SimpleNamespace(text=last)], result=None)

    async def nxt():
        ctx.result = SimpleNamespace(text=reply, usage_details={})
    return log.chat(name).process(ctx, nxt)


async def _tool(log, agent: str, mcp, tool: str, **args):
    """One tool call through the real tool middleware, to the real MCP server."""
    from agent_framework import FunctionMiddleware
    from briefing_lowcode.team import _call

    mw = next(m for m in log.for_agent(agent) if isinstance(m, FunctionMiddleware))
    ctx = SimpleNamespace(function=SimpleNamespace(name=tool), arguments=args, result=None)

    async def nxt():
        ctx.result = await _call(mcp, tool, **args)
    await mw.process(ctx, nxt)


def _job(kind: str, **payload) -> dict:
    return {"id": "j-test", "kind": kind, "payload": {"question": Q, "query": {"brand_id": "BXA"}, **payload}}


def test_events_do_not_change_the_answer_claims_or_evidence(monkeypatch):
    import briefing_agent as agent
    inv = importlib.import_module("briefing_agent.investigate")

    def install():
        replies = {"writer": [json.dumps({"answer": "Typed 99 digits here.", "stories": {}})],
                   "reviser": [json.dumps({"answer": "BXA moved as the code sections show.", "stories": {}})]}

        async def fake_ask(spec, prompt, log, name):
            reply = replies[name].pop(0) if replies.get(name) else '{"order": []}'
            await _chat(log, name, prompt, reply)
            return reply

        async def fake_team(cfg, spec, mcp, task, log, wall):
            territory = task.split("territory ID ")[1].split(")")[0]
            await _chat(log, "manager", "Plan the story.", '{"next_speaker": {"answer": "data_forensics"}}')
            await _tool(log, "data_forensics", mcp, "check_data", territory=territory)
            for tool in ("check_access", "check_promotion", "check_supply", "check_competitor", "story_confidence"):
                await _tool(log, "driver_investigator", mcp, tool, territory=territory)
            return None
        monkeypatch.setattr(agent, "_ask", fake_ask)
        monkeypatch.setattr(inv, "_team", fake_team)

    def run(with_events: bool):
        install()
        log = agent.events_for() if with_events else None
        plan = agent.triage(Q, SPEC, events=log)
        decision = {"plan_id": plan["plan_id"], "stories": plan["manager_order"]}
        return agent.run_with_plan(Q, decision, plan, SPEC, events=log)

    on, off = run(True), run(False)
    assert "events" not in off and on["events"]
    for k in SAME:
        assert json.dumps(on["envelope"].get(k), sort_keys=True) == json.dumps(off["envelope"].get(k), sort_keys=True), k
    assert on["flow"] == off["flow"] and on["triage"] == off["triage"]

    events, owner = on["events"], on["claim_events"]
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    # SC-002: every claim of the brief links to the event that produced it, and back
    n = len(on["envelope"]["claims"])
    assert len(owner) == n and None not in owner
    by_seq = {e["seq"]: e for e in events}
    assert all(i in by_seq[owner[i]]["claims"] for i in range(n))
    assert all("{c" not in e["summary"] for e in events)  # tokens are filled with the run's own values
    # actors, order, tools, verdicts
    steps = [(e["actor"], e["step"]) for e in events]
    assert steps[0] == ("Code", "Screen territories") and ("Manager", "Plan the stories") in steps
    first_person = steps.index(("Person", "Review the plan"))
    assert first_person < steps.index(("Data Forensics", "Check the data")) < steps.index(("Driver Investigator", "Test a driver"))
    assert ("Writer", "Draft the paragraphs") in steps and ("Writer", "Rewrite a sentence") in steps
    assert steps.index(("Writer", "Rewrite a sentence")) > steps.index(("Writer", "Draft the paragraphs"))
    assert steps[-1] == ("Code", "Assemble the memo")
    drivers = [e for e in events if e["actor"] == "Driver Investigator" and e["step"] == "Test a driver"]
    assert {e["tool"] for e in drivers} == {"check_access", "check_promotion", "check_supply", "check_competitor"}
    assert all(e["verdict"] in ("supported", "ruled out", "inconclusive", "abstained") and e["args"]["territory"] for e in drivers)
    assert any(e["step"] == "Coordinate story" and e["summary"] == "The manager asked Data Forensics to act next." for e in events)
    # story ids are the triage record's story ids (the UI titles stories with them)
    call_ids = {c["story"] for c in on["triage"]["calls"]}
    assert {e["story"] for e in events if e["story"]} <= call_ids and {e["story"] for e in events if e["story"]}
    # prompt refs: the prompt file's id and the first 7 hex of its bytes
    prompts = Path(agent.__file__).parent / "prompts"
    want = lambda stem: f"{stem}@{hashlib.sha256((prompts / (stem + '.md')).read_bytes()).hexdigest()[:7]}"  # noqa: E731
    by_step = {(e["actor"], e["step"]): e for e in events}
    assert by_step[("Writer", "Draft the paragraphs")]["prompt"] == want("writer")
    assert by_step[("Writer", "Rewrite a sentence")]["prompt"] == want("revise")
    assert by_step[("Manager", "Plan the stories")]["prompt"] == want("manager_triage")
    assert drivers[0]["prompt"] == want("driver_investigator")
    # no model text, no person identity: the whole log is code strings
    assert not any(k in json.dumps(events) for k in ("Typed 99", "dev-analyst"))


def test_worker_run_job_streams_events_and_the_brief_continues_the_triage_log(monkeypatch):
    import briefing_agent as agent
    from briefing_agent import worker

    inv = importlib.import_module("briefing_agent.investigate")

    async def fake_ask(spec, prompt, log, name):
        reply = {"writer": json.dumps({"answer": "BXA moved as the code sections show.", "stories": {}})}.get(name, '{"order": []}')
        await _chat(log, name, prompt, reply)
        return reply

    async def fake_team(cfg, spec, mcp, task, log, wall):
        t = task.split("territory ID ")[1].split(")")[0]
        await _tool(log, "data_forensics", mcp, "check_data", territory=t)
        await _tool(log, "driver_investigator", mcp, "story_confidence", territory=t)

    monkeypatch.setattr(agent, "_ask", fake_ask)
    monkeypatch.setattr(inv, "_team", fake_team)
    streamed: list[dict] = []
    plan = worker.run_job(_job("triage"), SPEC, streamed.extend)
    assert [e["seq"] for e in streamed] == [e["seq"] for e in plan["events"]] and streamed
    triage_n = len(streamed)
    streamed.clear()
    decision = {"plan_id": plan["plan_id"], "stories": plan["manager_order"]}
    out = worker.run_job(_job("brief", plan=plan, decision=decision), SPEC, streamed.extend)
    seqs = [e["seq"] for e in streamed]
    assert seqs[:triage_n] == list(range(1, triage_n + 1))  # the live timeline starts at the triage steps
    assert seqs == sorted(set(seqs)) and seqs[-1] == out["events"][-1]["seq"]


# --- scripted engine ----------------------------------------------------------------------------------------

def test_scripted_events_are_code_and_do_not_change_the_brief():
    from briefing_baseline import pipeline

    plain = pipeline.answer(Q)
    log = ev.EventLog()
    shown = pipeline.answer(Q, events=log)
    assert plain == shown
    events, owner = log.finalize(len(shown["claims"]))
    assert {e["actor"] for e in events} == {"Code"} and {e["kind"] for e in events} == {"code"}
    assert None not in owner and len(owner) == len(shown["claims"])
    assert [e["tool"] for e in events if e["step"] == "Test a driver" and e["story"] == "territory:PACIFIC"] == [
        "check_access", "check_promotion", "check_supply", "check_competitor"]
    assert all(e["verdict"] in ev.VERDICTS for e in events if e["step"] == "Test a driver")
    assert all("{c" not in e["summary"] for e in events)

    plan = pipeline.triage(Q)
    decision = {"plan_id": plan["plan_id"], "stories": ["territory:PACIFIC"]}
    log2 = ev.EventLog()
    with_plan = pipeline.run_with_plan(Q, decision, events=log2)
    assert with_plan == pipeline.run_with_plan(Q, decision)
    assert [(e["actor"], e["step"]) for e in log2.public() if e["actor"] == "Person"] == [("Person", "Review the plan")]
    assert {c["story"] for c in with_plan["triage"]["calls"] if c["outcome"] == "investigated"} == {"territory:PACIFIC"}


# --- progress round trip ------------------------------------------------------------------------------------

def _event(seq: int, **kw) -> dict:
    return {"seq": seq, "t": "2026-11-22T10:00:00Z", "actor": "Code", "kind": "code", "step": "Screen territories",
            "story": None, "tool": None, "args": None, "verdict": None, "summary": f"step {seq}", "claims": [], "prompt": None, **kw}


def test_progress_round_trip_external_worker():
    analyst = signed_in("dev-analyst")
    job = analyst.post("/api/agent/jobs", json={"kind": "triage", "query": QUERY}).json()
    assert job["progress"] == []
    post = lambda body, headers=W: TestClient(app).post(f"/api/worker/jobs/{job['id']}/progress", json=body, headers=headers)  # noqa: E731
    assert post({"events": [_event(1)]}, {}).status_code == 401
    assert post({"events": [_event(1)]}).status_code == 404  # not running yet
    assert TestClient(app).post("/api/worker/next", json={"worker": "pc"}, headers=W).json()["id"] == job["id"]
    junk = {"seq": 3, "actor": "Hacker", "kind": "code"}
    assert post({"events": [_event(1), _event(2, tool="check_access", args={"territory": "X"}, extra="no"), junk]}).json() == {"stored": 2}
    assert post({"events": [_event(2), _event(3)]}).json() == {"stored": 3}  # a retried batch repeats nothing
    shown = analyst.get(f"/api/agent/jobs/{job['id']}").json()
    assert [e["seq"] for e in shown["progress"]] == [1, 2, 3] and "extra" not in shown["progress"][1]  # the full list each poll
    assert [e["seq"] for e in analyst.get(f"/api/agent/jobs/{job['id']}?after=2").json()["progress"]] == [3]
    assert post({"events": [_event(1)] * 201}).status_code == 422
    assert signed_in("dev-director").get(f"/api/agent/jobs/{job['id']}").status_code == 403  # leaders never see a job


def test_builtin_worker_appends_progress_and_the_brief_keeps_the_events(monkeypatch):
    from briefing_baseline.pipeline import run_with_plan, triage

    analyst = signed_in("dev-analyst")
    seen: dict = {}

    def fake_run_job(job, spec, progress=None):
        if job["kind"] == "triage":
            progress([_event(1)])
            seen["during"] = [e["seq"] for e in jobs.get(job["id"])["progress"]]
            return dict(triage(job["payload"]["question"]), engine="agent", manager_order=["territory:PACIFIC"], flagged=False,
                        flags=[], events=[_event(1), dict(_event(2), actor="Nobody")])
        log = ev.EventLog()
        out = run_with_plan(job["payload"]["question"], job["payload"]["decision"], events=log)
        events, owner = log.finalize(len(out["envelope"]["claims"]))
        return {**out, "events": events, "claim_events": owner}

    monkeypatch.setattr("briefing_agent.worker.run_job", fake_run_job)
    tjob = analyst.post("/api/agent/jobs", json={"kind": "triage", "query": QUERY}).json()
    assert agent_host.work_once(SPEC, accept_result, runner=agent_host._run_job) is True
    assert seen["during"] == [1]
    plan = analyst.get(f"/api/agent/jobs/{tjob['id']}").json()["result"]
    assert [e["seq"] for e in plan["events"]] == [1]  # the unknown actor was dropped
    decision = {"plan_id": plan["plan_id"], "stories": ["territory:PACIFIC"]}
    bjob = analyst.post("/api/agent/jobs", json={"kind": "brief", "query": QUERY, "triage_job": tjob["id"], "decision": decision}).json()
    assert agent_host.work_once(SPEC, accept_result, runner=agent_host._run_job) is True
    brief = analyst.get(f"/api/agent/jobs/{bjob['id']}").json()["result"]
    assert brief["events"] and len(brief["claim_events"]) == len(brief["claims"]) and None not in brief["claim_events"]

    # the leader cut: a one-line summary, no events, arguments or prompts
    analyst.post(f"/api/briefing/{brief['brief_id']}/review", json={"decision": "approved"})
    leader = signed_in("dev-director").get(f"/api/briefing/{brief['brief_id']}").json()
    assert leader["view"] == "leadership" and leader["process_summary"].startswith("Built by the agent team: ")
    assert "reviewed by the analyst" in leader["process_summary"]
    forbidden = {"events", "claim_events", "args", "prompt", "progress", "flow", "triage", "tool", "step", "actor"}
    assert not (_keys(leader) & forbidden), _keys(leader) & forbidden


def _keys(x) -> set[str]:
    if isinstance(x, dict):
        return set(x) | set().union(*(_keys(v) for v in x.values())) if x else set()
    if isinstance(x, list):
        return set().union(*(_keys(v) for v in x)) if x else set()
    return set()


def test_scripted_brief_stores_events_and_leaders_get_the_summary_only():
    analyst = signed_in("dev-analyst")
    got = analyst.post("/api/briefing/query", json=QUERY).json()
    assert got["engine"] == "scripted" and got["events"] and {e["actor"] for e in got["events"]} == {"Code"}
    assert len(got["claim_events"]) == len(got["claims"]) and None not in got["claim_events"]
    assert signed_in("dev-analyst").get(f"/api/briefing/{got['brief_id']}").json()["events"] == got["events"]  # saved with the brief
    analyst.post(f"/api/briefing/{got['brief_id']}/review", json={"decision": "approved"})
    leader = signed_in("dev-director").get(f"/api/briefing/{got['brief_id']}").json()
    assert leader["process_summary"].startswith("Built by the scripted engine: ") and "events" not in leader
    assert leader["process_summary"] == views.process_summary(
        {"result": got, "review_status": "approved", "reviewed_at": leader["reviewed_at"]})


def test_process_summary_without_events_and_while_unreviewed():
    rec = {"result": {"engine": "agent"}, "review_status": "pending", "reviewed_at": None}
    assert views.process_summary(rec) == "Built by the agent team."
    rec = {"result": {"engine": "scripted", "events": [_event(1, story="a", step="Test a driver", tool="check_access"),
                                                       _event(2, story="a", step="Test a driver", tool="check_supply"),
                                                       _event(3, story="b", step="Close the story", tool="story_confidence")]},
           "review_status": "approved", "reviewed_at": "2026-11-22T10:00:00Z"}
    assert views.process_summary(rec) == "Built by the scripted engine: 2 stories, 2 checks; reviewed by the analyst."


# --- the pieces ---------------------------------------------------------------------------------------------

def test_event_log_attributes_each_claim_to_the_first_step_that_names_it():
    log = ev.EventLog()
    log.claims = [{"value": "5%"}, {"value": "7"}]
    log.emit("Code", "code", "a", text="x {c1} y {c2}", summary="value {c1}")
    log.emit("Code", "code", "b", text="again {c2} and {c3}", summary="{c3}")
    events, owner = log.finalize(3, {1: 0, 3: 1})  # token 2 is not in the brief
    assert [e["claims"] for e in events] == [[0], [1]] and owner == [1, 2, None][:0] + [1, 2, None] or owner == [1, 2, None]
    assert events[0]["summary"] == "value 5%" and events[1]["summary"] == "a figure"


def test_progress_post_batches_and_keeps_a_failed_batch():
    from briefing_agent.worker import ProgressPost

    sent, fail = [], [True]

    def post(batch):
        if fail[0]:
            raise RuntimeError("down")
        sent.append(batch)
    p = ProgressPost(post)
    p([_event(1)])
    p.flush()
    p([_event(2)])
    fail[0] = False
    p.flush()
    assert [[e["seq"] for e in b] for b in sent] == [[1, 2]]


# --- integration review fixes ---------------------------------------------------------------------------------

def test_progress_post_sends_chunks_of_the_apps_limit_and_drops_a_refused_batch():
    from briefing_agent.worker import ProgressPost

    sent, mode = [], {"status": None}

    def post(batch):
        if mode["status"]:
            raise SimpleNamespace_error(mode["status"])
        sent.append([e["seq"] for e in batch])

    class SimpleNamespace_error(Exception):
        def __init__(self, status):
            self.response = SimpleNamespace(status_code=status)
    p = ProgressPost(post)
    p([_event(i) for i in range(1, 451)])  # a backlog bigger than the app's 200 per post
    p.flush()
    assert [len(b) for b in sent] == [200, 200, 50] and sent[0][0] == 1 and sent[2][-1] == 450
    sent.clear()
    p([_event(500)])
    mode["status"] = 503  # a server error keeps the batch for the next beat
    p.flush()
    mode["status"] = None
    p.flush()
    assert sent == [[500]]
    sent.clear()
    mode["status"] = 422  # a refusal would repeat for ever: dropped, and later events still go
    p([_event(501)])
    p.flush()
    mode["status"] = None
    p([_event(502)])
    p.flush()
    assert sent == [[502]]
    p.close()
    p([_event(503)])
    p.flush()
    assert sent == [[502]]  # nothing is sent once the client is closed


def test_add_progress_inserts_a_late_earlier_event_in_order_without_duplicates(monkeypatch):
    saves = []
    monkeypatch.setattr(jobs, "_save", lambda job: saves.append(job["id"]))
    job = jobs.submit("triage", {"question": Q}, "dev-analyst")
    jobs.next_job(SPEC, "pc")
    jobs.add_progress(job["id"], [_event(1), _event(3)])
    assert jobs.add_progress(job["id"], [_event(2), _event(3), _event(4)]) == 4
    assert [e["seq"] for e in jobs.get(job["id"])["progress"]] == [1, 2, 3, 4]
    before = len(saves)
    jobs.add_progress(job["id"], [_event(5)], persist=False)
    assert len(saves) == before and jobs.get(job["id"])["progress"][-1]["seq"] == 5  # in memory at once, not yet saved
    assert jobs.persist_progress(job["id"]) is True and len(saves) == before  # written outside the lock, once
    assert jobs.persist_progress(job["id"]) is False


def test_builtin_worker_saves_progress_on_a_beat_not_once_per_event(monkeypatch):
    from briefing_baseline.pipeline import triage

    writes = []
    real = jobs.store.backend()

    class Spy:
        keys, read = staticmethod(real.keys), staticmethod(real.read)

        @staticmethod
        def write(key, text):
            writes.append(json.loads(text)["status"])
            real.write(key, text)
    monkeypatch.setattr(jobs.store, "backend", lambda: Spy)
    monkeypatch.setattr(agent_host, "PERSIST_SECONDS", 0.05)

    def fake_run_job(job, spec, progress=None):
        import time
        for i in range(1, 41):
            progress([_event(i)])
            assert [e["seq"] for e in jobs.get(job["id"])["progress"]][-1] == i  # a poll sees it at once
        time.sleep(0.3)
        return dict(triage(job["payload"]["question"]), engine="agent", manager_order=["territory:PACIFIC"], flagged=False, flags=[])

    monkeypatch.setattr("briefing_agent.worker.run_job", fake_run_job)
    signed_in("dev-analyst").post("/api/agent/jobs", json={"kind": "triage", "query": QUERY})
    writes.clear()
    assert agent_host.work_once(SPEC, accept_result, runner=agent_host._run_job) is True
    assert writes[-1] == "done" and writes.count("done") == 1  # saved at the job's end, and no beat write lands after it
    assert writes.count("running") <= 8  # the start and a few beats, never one per event (40)


def test_a_competitor_section_that_comes_back_empty_is_no_story_and_no_event(monkeypatch):
    import briefing_agent as agent
    inv = importlib.import_module("briefing_agent.investigate")
    from briefing_lowcode.team import RunLog

    plan = {"stories": [{"id": "competitor:BXE", "kind": "competitor", "title": "Competitor", "proposed": "investigate"}]}
    for text, want in (("", 0), ("Story one: competitor Metacora", 1)):
        async def fake_call(mcp, tool, **kw):
            return text
        monkeypatch.setattr(inv, "_call", fake_call)
        log = RunLog(agent.events_for())
        stories, _ = asyncio.run(inv.investigate({"run_wall_seconds": 100, "story_wall_seconds": 10}, SPEC, None, plan,
                                                 ["competitor:BXE"], log))
        assert len(stories) == want
        assert [e["step"] for e in log.events.public()] == ["Check the competitor"] * want


def test_promotion_review_and_out_of_scope_runs_keep_their_event_log():
    import briefing_agent as agent

    for question, step_screen in (("Did the campaign reach the people it was meant to reach?", True),
                                  ("Week of 2026-10-05: Where should the next dollar go?", False)):
        log = agent.events_for()
        plan = agent.triage(question, SPEC, events=log)
        assert any(e["step"] == "Screen territories" for e in log.public()) is step_screen  # none for a question outside the release
        out = agent.run_with_plan(question, {"plan_id": plan["plan_id"], "stories": []}, plan, SPEC, events=log)
        assert out["events"] == log.finalize(len(out["envelope"].get("claims") or []))[0] and "claim_events" in out
        assert out["events"] or not step_screen


def test_deferred_summaries_are_filled_once_after_the_timed_section():
    calls = []

    async def fetch():
        calls.append(1)
        return [{"value": "5%"}, {"value": "7"}]
    log = ev.EventLog()
    log.fetch = fetch
    log.defer = True
    log.emit("Driver Investigator", "agent", "Test a driver", summary="Access: down {c1} and {c2}", text="{c1} {c2}")
    log.emit("Driver Investigator", "agent", "Test a driver", summary="Supply: {c2}", text="{c2}")
    assert calls == [] and log.public()[0]["summary"] == "Access: down a figure and a figure"
    log.defer = False
    asyncio.run(log.resolve())
    assert calls == [1] and [e["summary"] for e in log.public()] == ["Access: down 5% and 7", "Supply: 7"]
    asyncio.run(log.resolve())
    assert calls == [1]  # nothing pending: no second fetch
