"""brief-009 T4: GET /api/briefing/agents. Everyone with a Briefing role sees the actors and the flow; only the analyst view
reads the prompts, verbatim from the repository."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import agents_info, telemetry
from pharmagentics.api.app import app

PROMPTS = agents_info.AGENT_DIR / "prompts"
STEPS = {pid: label for a in agents_info.ACTORS for pid, label in a["steps"]}


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("K_SERVICE", raising=False)
    monkeypatch.delenv("PHARMAGENTICS_AGENT_MODEL", raising=False)


def signed_in(username: str) -> TestClient:
    c = TestClient(app)
    assert c.post("/auth/dev-login", data={"username": username}, follow_redirects=False).status_code == 303
    return c


def test_the_analyst_reads_each_prompt_verbatim():
    r = signed_in("dev-analyst").get("/api/briefing/agents")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["prompts_shown"] is True
    assert [a["id"] for a in body["actors"]] == ["manager", "data_forensics", "driver_investigator", "writer"]
    assert {a["id"]: a["kind"] for a in body["actors"]}["writer"] == "llm"  # an LLM step, not an agent
    shown = {p["id"]: p for a in body["actors"] for p in a["prompts"]}
    assert set(shown) == set(STEPS) == {"manager_triage", "manager", "story_done", "data_forensics", "driver_investigator", "writer", "revise"}
    for pid, p in shown.items():
        assert p["text"] == (PROMPTS / f"{pid}.md").read_text(encoding="utf-8")
        assert p["ref"] == f"{pid}@{p['hash']}" and len(p["hash"]) == 7


@pytest.mark.parametrize("user", ["dev-director", "dev-marketer"])
def test_a_leader_gets_the_actors_and_no_prompt(user):
    r = signed_in(user).get("/api/briefing/agents")
    assert r.status_code == 200
    body = r.json()
    assert body["prompts_shown"] is False and len(body["actors"]) == 4 and body["flow"]
    assert all("prompts" not in a for a in body["actors"])
    for f in PROMPTS.glob("*.md"):  # no line of any prompt leaves the server
        for line in f.read_text(encoding="utf-8").splitlines():
            if len(line.strip()) > 40:
                assert line.strip() not in r.text, (f.name, line)


def test_the_test_login_follows_the_view_it_is_in():
    c = signed_in("dev-tester")
    assert c.get("/api/briefing/agents").json()["prompts_shown"] is True
    assert c.post("/api/me/view-as", json={"view": "leadership"}).status_code == 200
    body = c.get("/api/briefing/agents").json()
    assert body["prompts_shown"] is False and all("prompts" not in a for a in body["actors"])
    assert c.post("/api/me/view-as", json={"view": "analyst"}).status_code == 200
    assert c.get("/api/briefing/agents").json()["prompts_shown"] is True


def test_sign_in_and_a_briefing_role_are_required():
    assert TestClient(app).get("/api/briefing/agents").status_code == 401
    assert signed_in("dev-norole").get("/api/briefing/agents").status_code == 403
    assert signed_in("dev-forecast-analyst").get("/api/briefing/agents").status_code == 403


def test_the_tool_lists_match_the_governed_tool_groups():
    pytest.importorskip("mcp")
    from pharmagentics.mcp_server import AGENT_TOOLS

    shown = {a["id"]: [t for t in a["tools"]] for a in agents_info.ACTORS}
    assert set(shown["data_forensics"]) == set(AGENT_TOOLS["data_forensics"])
    assert set(shown["driver_investigator"]) == set(AGENT_TOOLS["driver_investigator"])
    assert all(t in agents_info.TOOLS for tools in shown.values() for t in tools)


def test_the_comparison_reads_the_latest_scripted_and_agent_runs(monkeypatch):
    def run(system, started, **metrics):
        return {"run_id": system[:4] + started[-2:], "started": started, "system": system, "lane": "briefing", "control": False,
                "cases": 32, "model": "anthropic:claude-haiku-5-5" if system == "briefing_agent" else None, "metrics": metrics}
    snap = {"latest": [run("briefing_agent", "2026-11-22T20:54", key_fact_recall=0.7, latency_brief_p50=81.7, llm_calls=10.6),
                       run("briefing_scripted", "2026-11-22T20:43", key_fact_recall=0.71, latency_brief_p50=17.7),
                       run("forecast_scripted", "2026-11-22T21:00", key_fact_recall=0.1)]}
    monkeypatch.setattr(telemetry, "snapshot", lambda: snap)
    body = signed_in("dev-director").get("/api/briefing/agents").json()
    cmp = body["comparison"]
    assert cmp["available"] and cmp["scripted"]["started"] == "2026-11-22T20:43" and cmp["agent"]["started"] == "2026-11-22T20:54"
    rows = {r["label"]: r for r in cmp["rows"]}
    assert rows["Key facts found"]["scripted"] == 0.71 and rows["Key facts found"]["agent"] == 0.7
    assert rows["Model calls a brief"]["scripted"] is None and rows["Model calls a brief"]["agent"] == 10.6
    assert rows["Cost a brief"]["agent"] is None and "Not recorded" in rows["Cost a brief"]["note"]
    assert body["model"] == {"spec": "anthropic:claude-haiku-5-5", "source": "evaluation"}


def test_without_both_runs_the_comparison_says_so(monkeypatch):
    monkeypatch.setattr(telemetry, "snapshot", lambda: {"latest": [], "runs": []})
    body = signed_in("dev-analyst").get("/api/briefing/agents").json()
    assert body["comparison"]["available"] is False and body["comparison"]["rows"] == []
    assert body["model"] == {"spec": None, "source": None}


def test_the_route_is_not_taken_for_a_brief_id():
    """/api/briefing/agents must win over /api/briefing/{brief_id}."""
    assert "actors" in signed_in("dev-analyst").get("/api/briefing/agents").json()
