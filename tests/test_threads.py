"""brief-006 slice 3: threads of follow-ups (FR-008, FR-009, FR-012; ADR 0002). Dev identities, real scripted engine."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import service, store, threads
from pharmagentics.api.app import app

needs_db = pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
SCOPE = {"intent": "weekly_brief", "brand_id": "BXA", "territory_id": "PACIFIC", "week_start": "2026-06-08",
         "question": "Generate the weekly brand-performance briefing."}


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.setattr(threads, "_purged", True)


def signed_in(user: str) -> TestClient:
    c = TestClient(app)
    c.post("/auth/dev-login", data={"username": user}, follow_redirects=False)
    return c


@pytest.fixture
def brief_id():
    return signed_in("dev-analyst").post("/api/briefing/query", json=SCOPE).json()["brief_id"]


@needs_db
def test_ask_save_share_and_continue(brief_id):
    a, b = signed_in("dev-analyst"), signed_in("dev-tester")
    empty = a.get(f"/api/briefing/{brief_id}/thread").json()
    assert empty["turns"] == [] and empty["suggestions"]["3.1"]
    t = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "What did the checks find?", "section": "3.1"}).json()
    assert t["turns"][0]["cited"] == ["3.1"] and t["turns"][0]["engine"] == "scripted" and not t["saved"]
    assert b.get(f"/api/briefing/{brief_id}/thread").json()["turns"] == []  # one thread per analyst
    assert b.get(f"/api/briefing/{brief_id}/thread/shared/{t['owner']}").status_code == 404  # unsaved: not shared
    saved = a.post(f"/api/briefing/{brief_id}/thread/save").json()
    assert saved["saved"] and saved["share_path"].endswith(t["owner"])
    seen = b.get(saved["share_path"]).json()
    assert seen["mine"] is False and len(seen["turns"]) == 1
    mine = b.post(f"/api/briefing/{brief_id}/thread/continue/{t['owner']}").json()
    assert mine["mine"] and mine["shared_from"] == t["owner"] and len(mine["turns"]) == 1 and not mine["saved"]


@needs_db
def test_leaders_never_reach_a_thread(brief_id):
    a, d = signed_in("dev-analyst"), signed_in("dev-director")
    a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the bottom line"})
    owner = a.post(f"/api/briefing/{brief_id}/thread/save").json()["owner"]
    for path in ("", "/shared/" + owner):
        assert d.get(f"/api/briefing/{brief_id}/thread{path}").status_code in (403, 404)
    assert d.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "x"}).status_code in (403, 404)


def _agent(monkeypatch, calls: list):
    """A configured model whose agent turn is replaced: one answer built from a claim token, no model call."""
    monkeypatch.setattr(threads.agent_host, "model", lambda: "anthropic:test")

    def answer(result, question, section):
        calls.append(question)
        claim = {"token": "{c1}", "value": "12.5%", "evidence_id": "fe1"}
        return {"answer": "NBRx moved 12.5% (§3.1).", "claims": [claim], "evidence": [{"id": "fe1", "tool": "split_change"}],
                "cited": ["3.1"], "kind": "agent", "engine": "agent", "offer": None}
    monkeypatch.setattr(threads, "_agent_answer", answer)


@needs_db
def test_free_text_goes_to_the_agent_and_chips_stay_scripted(brief_id, monkeypatch):
    calls: list = []
    _agent(monkeypatch, calls)
    a = signed_in("dev-analyst")
    free = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "How did NBRx move in the Pacific?", "section": "3.1"}).json()
    assert calls == ["How did NBRx move in the Pacific?"]
    turn = free["turns"][0]
    assert turn["engine"] == "agent" and turn["claims"][0]["value"] == "12.5%"
    assert {c["evidence_id"] for c in turn["claims"]} <= {e["id"] for e in turn["evidence"]}  # every number has its query
    chip = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "What did the checks find?", "section": "3.1"}).json()
    assert len(calls) == 1 and chip["turns"][1]["engine"] == "scripted"  # the chip never reached the agent
    assert chip["used_turns"] == 1 and len(chip["turns"]) == 2 and chip["free_text"] is True


@needs_db
def test_chips_work_without_a_model_and_do_not_count(brief_id, monkeypatch):
    monkeypatch.setattr(threads.agent_host, "model", lambda: None)
    a = signed_in("dev-analyst")
    for _ in range(3):
        t = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the next checks", "section": "5"}).json()
    assert t["used_turns"] == 0 and len(t["turns"]) == 3 and all(x["engine"] == "scripted" for x in t["turns"])
    refused = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the numbers please"})
    assert refused.status_code == 409 and "Pick a suggested question" in refused.json()["detail"]
    assert len(a.get(f"/api/briefing/{brief_id}/thread").json()["turns"]) == 3  # the refusal used nothing up


@needs_db
def test_the_client_cannot_dodge_the_quota_by_naming_an_engine(brief_id, monkeypatch):
    calls: list = []
    _agent(monkeypatch, calls)
    a = signed_in("dev-analyst")
    t = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Anything new this week?", "engine": "scripted"}).json()
    assert calls and t["turns"][0]["engine"] == "agent" and t["used_turns"] == 1


@needs_db
def test_a_thread_holds_twenty_free_text_follow_ups(brief_id, monkeypatch):
    calls: list = []
    _agent(monkeypatch, calls)
    monkeypatch.setattr(threads, "MAX_TURNS", 3)
    a = signed_in("dev-analyst")
    for _ in range(2):  # chips in between never use a slot
        assert a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the next checks", "section": "5"}).status_code == 200
    for i in range(3):
        assert a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": f"Free question {i}"}).status_code == 200
    full = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "One more"})
    assert full.status_code == 409 and "full" in full.json()["detail"] and len(calls) == 3
    chip = a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the next checks", "section": "5"})
    assert chip.status_code == 200 and chip.json()["used_turns"] == 3  # a full thread still answers chips


@needs_db
def test_every_turn_event_records_its_engine(brief_id, monkeypatch):
    _agent(monkeypatch, [])
    a = signed_in("dev-analyst")
    a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "What did the checks find?", "section": "3.1"})
    a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "A free question"})
    events = [json.loads(store.backend().read(k)) for k in store.backend().keys("events/")]
    assert sorted(e["engine"] for e in events if e["kind"] == "follow_up") == ["agent", "scripted"]


def test_agent_replies_are_checked_for_typed_numbers():
    import sys
    sys.path.insert(0, str(threads.agent_host.AGENTS_DIR))
    from briefing_agent.followup import _problems
    assert _problems("NBRx rose by {c1} (§3.1).", 1) == []
    assert _problems("NBRx rose 12.5% (§3.1).", 1)  # a typed number is refused
    assert _problems("NBRx rose by {c2}.", 1)  # a token no tool produced is refused


@needs_db
def test_unsaved_threads_go_after_thirty_days_saved_ones_stay(brief_id):
    a = signed_in("dev-analyst")
    a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the bottom line"})
    later = datetime.now(timezone.utc) + timedelta(days=31)
    assert threads.purge(now=later) == 1
    a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the bottom line"})
    a.post(f"/api/briefing/{brief_id}/thread/save")
    assert threads.purge(now=later) == 0


@needs_db
def test_a_vote_on_a_follow_up_records_that_turn(brief_id):
    a = signed_in("dev-analyst")
    a.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the next checks", "section": "5"})
    r = a.post("/api/feedback/vote", json={"lane": "briefing", "ref": f"{brief_id}:t1", "view": "analyst", "vote": "up"})
    assert r.status_code in (200, 201), r.text
    keys = store.backend().keys("")
    vote = next(k for k in keys if "/t1/" in k)
    assert json.loads(store.backend().read(vote))["vote"] == "up"
    assert a.post("/api/feedback/vote", json={"lane": "briefing", "ref": f"{brief_id}:t9", "view": "analyst",
                                              "vote": "up"}).status_code == 404


@needs_db
def test_the_insights_manager_asks_follow_ups_on_a_brief_sent_for_sign_off(brief_id):
    """Michael, 2026-11-27 (#6): P2 reads the analyst view, so P2 can ask; the thread is P2's own, not the analyst's.
    A draft the analyst has not sent stays out of reach (404), like the brief itself."""
    a, i = signed_in("dev-analyst"), signed_in("dev-insights")
    assert i.get(f"/api/briefing/{brief_id}/thread").status_code == 404  # still a draft
    assert a.post(f"/api/briefing/{brief_id}/review", json={"decision": "sent"}).status_code == 200
    t = i.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the bottom line"})
    assert t.status_code == 200 and t.json()["mine"] and len(t.json()["turns"]) == 1
    assert a.get(f"/api/briefing/{brief_id}/thread").json()["turns"] == []  # one thread per reader
    r = i.post("/api/feedback/vote", json={"lane": "briefing", "ref": f"{brief_id}:t1", "view": "analyst", "vote": "down"})
    assert r.status_code in (200, 201), r.text  # P2 can vote on P2's own follow-up answer


@needs_db
def test_the_marketer_never_reaches_a_thread(brief_id):
    from signoff_helpers import approve
    approve(signed_in("dev-analyst"), brief_id)
    m = signed_in("dev-marketer")
    assert m.get(f"/api/briefing/{brief_id}/thread").status_code == 404
    assert m.post(f"/api/briefing/{brief_id}/thread/ask", json={"question": "Restate the bottom line"}).status_code == 404
