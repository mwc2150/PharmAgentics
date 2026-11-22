"""Forecast lane API: access by role, the two views, fixed engine, validation, and the three ready-made cases.

These run the scripted engine (no language model) on the repo's own data/agent_visible, so they need no network.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import forecast, forecast_store, service
from pharmagentics.api.app import app

CLIENT = TestClient(app)
NATIONAL = {"territory_id": "NATIONAL", "week_start": "2026-08-24"}
NEW_ENGLAND = {"territory_id": "NEW_ENGLAND", "week_start": "2026-05-04"}
MID_ATLANTIC = {"territory_id": "MID_ATLANTIC", "week_start": "2025-08-04", "window_weeks": 13}


@pytest.fixture(autouse=True)
def _dev_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("FEAGENT_MODE", raising=False)
    monkeypatch.setenv("FEAGENT_WRITER", "off")  # no model call in these tests; the writer has its own tests
    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")  # never the local Qwen, even when Ollama is running
    CLIENT.cookies.clear()


def sign_in(user: str) -> None:
    CLIENT.cookies.clear()
    assert CLIENT.post("/auth/dev-login", data={"username": user}, follow_redirects=False).status_code == 303


def test_runs_need_a_signed_in_forecast_role():
    assert CLIENT.post("/api/forecast/runs", json=NATIONAL).status_code == 401
    sign_in("dev-analyst")  # a Briefing role holds no Forecast role
    assert CLIENT.post("/api/forecast/runs", json=NATIONAL).status_code == 403
    assert CLIENT.get("/api/forecast/cases").status_code == 403


def test_the_analyst_gets_the_full_run():
    sign_in("dev-forecast-analyst")
    res = CLIENT.post("/api/forecast/runs", json=NATIONAL)
    assert res.status_code == 200
    body = res.json()
    assert body["view"] == "analyst" and body["lane"] == "forecast"
    assert len(body["stages"]) == 7 and body["stages"][6]["status"] == "PENDING"
    report = body["report"]
    assert report["variance_trx"] == -1036 and report["investigator_mode"] == "stub"
    promotion = next(d for d in report["drivers"] if d["driver"] == "promotion")
    assert abs(promotion["impact_trx"] + 211.8) < 0.1 and promotion["evidence_ids"]
    assert res.headers["cache-control"] == "no-store"


def test_the_leadership_view_has_no_evidence_or_trace():
    sign_in("dev-forecast-analyst")
    body = CLIENT.post("/api/forecast/runs", json={**NATIONAL, "view": "leadership"}).json()
    assert body["view"] == "leadership"
    assert "stages" not in body and "pin" not in body and "fingerprint" not in body
    report = body["report"]
    assert report["variance_trx"] == -1036 and report["verification"] == {"verdict": "WARN"}
    assert "evidence" not in report and "investigator_mode" not in report
    assert all(set(d) == {"driver", "impact_trx", "confidence"} for d in report["drivers"])
    assert "evidence_ids" not in str(body)


def test_the_brand_manager_cannot_start_a_run_or_list_the_cards():
    sign_in("dev-forecast-manager")
    assert CLIENT.post("/api/forecast/runs", json=NATIONAL).status_code == 403
    assert CLIENT.get("/api/forecast/cases").status_code == 403
    status = CLIENT.get("/api/forecast/status").json()
    assert status["persona"] == "BM" and status["views"] == ["leadership"] and status["actions"] == ["read", "review"]


def test_an_analyst_can_preview_the_leadership_view_but_a_manager_cannot_open_the_analyst_view():
    sign_in("dev-forecast-analyst")
    preview = CLIENT.post("/api/forecast/runs", json={**NATIONAL, "view": "leadership"}).json()
    assert preview["view"] == "leadership" and "stages" not in preview


def test_opening_a_saved_run_in_both_views_keeps_the_same_run_and_review_state():
    sign_in("dev-forecast-analyst")
    created = CLIENT.post("/api/forecast/runs", json=NATIONAL).json()
    run_id = created["forecast_run_id"]
    path = f"/api/forecast/runs/{run_id}"

    preview_response = CLIENT.get(path, params={"view": "leadership"})
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["view"] == "leadership" and preview["forecast_run_id"] == run_id
    assert preview["review_status"] == created["review_status"] == "not_submitted"
    assert preview["report"]["variance_trx"] == created["report"]["variance_trx"]
    assert "stages" not in preview and "history" not in preview and "pin" not in preview
    assert "evidence" not in preview["report"]
    assert all("evidence_ids" not in d for d in preview["report"]["drivers"])

    for params in ({"view": "analyst"}, {}):
        response = CLIENT.get(path, params=params)
        assert response.status_code == 200
        analyst = response.json()
        assert analyst["view"] == "analyst" and analyst["forecast_run_id"] == run_id
        assert analyst["review_status"] == "not_submitted" and len(analyst["stages"]) == 7


def test_a_provisional_actual_pauses_attribution():
    sign_in("dev-forecast-analyst")
    body = CLIENT.post("/api/forecast/runs", json=NEW_ENGLAND).json()
    assert body["report"]["abstained"] is True and body["report"]["drivers"] == []
    assert body["report"]["variance_trx"] == -173
    assert body["stages"][1]["status"] == "FLAG" and body["stages"][3]["status"] == "ABSTAINED"


def test_a_thirteen_week_window_explains_the_window_not_the_first_week():
    sign_in("dev-forecast-analyst")
    report = CLIENT.post("/api/forecast/runs", json=MID_ATLANTIC).json()["report"]
    assert report["window_weeks"] == 13 and report["variance_trx"] == -730


def test_bad_input_is_refused_with_a_message():
    sign_in("dev-forecast-analyst")
    assert CLIENT.post("/api/forecast/runs", json={**NATIONAL, "territory_id": "ATLANTIS"}).status_code == 422
    assert CLIENT.post("/api/forecast/runs", json={**NATIONAL, "window_weeks": 99}).status_code == 422
    assert CLIENT.post("/api/forecast/runs", json={**NATIONAL, "mode": "ollama"}).status_code == 422  # not the caller's choice
    res = CLIENT.post("/api/forecast/runs", json={**NATIONAL, "week_start": "1999-01-04"})
    assert res.status_code == 400 and res.json()["detail"]


def test_the_engine_is_fixed_by_the_server_and_an_unknown_setting_means_stub(monkeypatch):
    monkeypatch.setenv("FEAGENT_MODE", "not-a-mode")
    assert forecast.engine_mode() == "stub"
    monkeypatch.setenv("FEAGENT_MODE", "ollama")
    assert forecast.engine_mode() == "ollama"
    monkeypatch.delenv("FEAGENT_MODE")
    assert forecast.engine_mode() == "stub"
    sign_in("dev-forecast-analyst")
    assert CLIENT.get("/api/forecast/status").json()["engine"] == "stub"


def test_cases_list_the_three_ready_made_requests():
    sign_in("dev-forecast-analyst")
    cases = CLIENT.get("/api/forecast/cases").json()["cases"]
    assert [c["request"]["territory_id"] for c in cases] == ["NEW_ENGLAND", "NATIONAL", "MID_ATLANTIC"]
    assert cases[2]["request"]["window_weeks"] == 13
    for case in cases:
        assert CLIENT.post("/api/forecast/runs", json=case["request"]).status_code == 200


def test_the_first_weeks_of_the_release_run_without_a_baseline_week():
    sign_in("dev-forecast-analyst")
    for week in ("2024-10-14", "2024-10-21"):  # the comparison week two weeks earlier has no forecast row
        res = CLIENT.post("/api/forecast/runs", json={"territory_id": "NATIONAL", "week_start": week})
        assert res.status_code == 200, res.text
        deltas = next(e for e in res.json()["report"]["evidence"] if e["name"] == "get_region_deltas")["payload"]
        assert all(r["baseline_actual"] is None and r["delta_vs_baseline"] is None for r in deltas["regions"])


@pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
def test_context_exposes_the_governed_forecast_scope():
    sign_in("dev-forecast-analyst")
    body = CLIENT.get("/api/forecast/context").json()
    assert body["metric"] == "TRx" and "NATIONAL" in body["territory_ids"]
    assert body["latest_week"] in body["available_weeks"]
    sign_in("dev-forecast-manager")
    assert CLIENT.get("/api/forecast/context").status_code == 403


def test_the_lane_is_open_to_the_ui():
    sign_in("dev-forecast-analyst")
    status = CLIENT.get("/api/forecast/status").json()
    assert status["available"] is True and status["actions"] == ["run", "read"]


# ---- the question-driven agent (fcst-001) ---------------------------------------------------------------------------

def _wait(run_id: str) -> dict:
    import time

    for _ in range(100):
        body = CLIENT.get(f"/api/forecast/runs/{run_id}").json()
        if body["job_status"] != "running":
            return body
        time.sleep(0.1)
    raise AssertionError("the investigation did not finish")


def test_a_question_is_read_into_a_scope_before_it_runs(monkeypatch):
    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    card = CLIENT.post("/api/forecast/scope", json={"question": "Top 5 largest gaps in the last 3 months"}).json()
    assert card["intent"] == "screen" and card["territory"] == "NATIONAL" and card["engine"] == "rules"
    assert CLIENT.post("/api/forecast/scope", json={"question": "hi", "engine": "x"}).status_code == 422


def test_a_question_runs_in_the_background_and_leaders_see_no_trace(monkeypatch):
    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    started = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()
    assert started["kind"] == "question"
    done = _wait(started["forecast_run_id"])
    assert done["job_status"] == "done" and done["report"]["variance_trx"] == -1036
    assert done["report"]["decisions"] and done["report"]["comparisons"]
    assert CLIENT.post(f"/api/forecast/runs/{started['forecast_run_id']}/submit").status_code == 409  # submitted via its report
    forecast_store.update(started["forecast_run_id"], review_status="pending_review")  # as a leader would see a shared run
    sign_in("dev-forecast-manager")
    lead = CLIENT.get(f"/api/forecast/runs/{started['forecast_run_id']}").json()
    assert lead["view"] == "leadership" and "progress" not in lead
    for hidden in ("decisions", "comparisons", "candidates", "screen", "sections_all"):
        assert hidden not in lead["report"]
    assert {s["id"] for s in lead["report"]["sections"]} <= {"summary", "miss", "where", "screen", "attribution", "unknowns", "checks", "assumptions"}
    assert CLIENT.post("/api/forecast/ask", json={"question": "Top 5 largest gaps"}).status_code == 403


def test_a_scope_edit_overrides_the_parsed_weeks(monkeypatch):
    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    started = CLIENT.post("/api/forecast/ask", json={"question": "Why did we miss?", "territory_id": "PACIFIC",
                                                     "week_from": "2026-06-01", "week_to": "2026-06-29"}).json()
    report = _wait(started["forecast_run_id"])["report"]
    assert report["territory_id"] == "PACIFIC" and report["window_weeks"] == 5
    assert any(d["driver"] == "supply" for d in report["drivers"])


def test_follow_ups_rerun_explain_and_break_down(monkeypatch):
    import time

    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()["forecast_run_id"]
    _wait(rid)
    for q in ("Drop South Central from the controls and rerun", "Why not supply?", "Show it week by week"):
        assert CLIENT.post(f"/api/forecast/runs/{rid}/followups", json={"question": q}).status_code == 200
    for _ in range(100):
        body = CLIENT.get(f"/api/forecast/runs/{rid}").json()
        if all(f["status"] != "running" for f in body["followups"]):
            break
        time.sleep(0.1)
    rerun, why, weekly = body["followups"]
    assert rerun["op"] == "rerun" and rerun["child_run_id"]
    child = CLIENT.get(f"/api/forecast/runs/{rerun['child_run_id']}").json()
    promo = next(d for d in child["report"]["drivers"] if d["driver"] == "promotion")
    assert promo["impact_trx"] == -204 and child["report"]["residual_trx"] == -145 and child["parent_run_id"] == rid
    assert why["op"] == "explain" and "supply" in why["answer"]
    assert weekly["op"] == "weekly" and "-1,036" in weekly["answer"]
    sign_in("dev-forecast-manager")
    assert CLIENT.post(f"/api/forecast/runs/{rid}/followups", json={"question": "Why?"}).status_code == 403


def test_the_driver_board_is_readable_by_both_forecast_roles():
    for user in ("dev-forecast-analyst", "dev-forecast-manager"):
        sign_in(user)
        body = CLIENT.get("/api/forecast/drivers").json()
        assert body["labels"] == "draft" and isinstance(body["systems"], dict)


def test_the_scope_card_says_who_read_it_and_the_confirmed_intent_is_used(monkeypatch):
    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    card = CLIENT.post("/api/forecast/scope", json={"question": "Week of 2026-08-24: Where is the miss?"}).json()
    assert card["read_by"] == "rules" and card["investigator"] == "rules" and card["intent"] == "where"
    started = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: Where is the miss?", "territory_id": "NATIONAL",
                                                     "week_from": "2026-08-24", "week_to": "2026-08-24", "intent": "attribution"}).json()
    report = _wait(started["forecast_run_id"])["report"]
    assert report["intent"] == "attribution" and report["scope_read_by"] == "confirmed"
    assert CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24", "intent": "guess"}).status_code == 422


def test_a_report_is_drafted_from_the_runs_pins_and_follows_them(monkeypatch):
    import time

    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    a = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()["forecast_run_id"]
    _wait(a)
    CLIENT.post(f"/api/forecast/runs/{a}/followups", json={"question": "Show it week by week"})
    for _ in range(100):
        if CLIENT.get(f"/api/forecast/runs/{a}").json()["followups"][0]["status"] != "running":
            break
        time.sleep(0.1)

    def settled(rid):
        for _ in range(100):
            body = CLIENT.get(f"/api/forecast/reports/{rid}").json()
            if body["job"]["status"] != "drafting":
                return body
            time.sleep(0.1)
        raise AssertionError("the draft did not finish")

    rid = CLIENT.post("/api/forecast/reports", json={"run_id": a}).json()["id"]
    first = settled(rid)
    assert [f["kind"] for f in first["findings"]] == ["run"] and first["version"] == 1 and not first["stale"]
    assert CLIENT.post("/api/forecast/reports", json={"run_id": a}).json()["id"] == rid  # one open report per run
    assert CLIENT.get(f"/api/forecast/runs/{a}").json()["report_id"] == rid

    assert CLIENT.post(f"/api/forecast/runs/{a}/pins/q1").json()["pins"] == ["q1"]  # pinned on the run page
    changed = CLIENT.get(f"/api/forecast/reports/{rid}").json()
    assert changed["stale"] and [f["kind"] for f in changed["findings"]] == ["run", "weekly"]
    assert CLIENT.post(f"/api/forecast/reports/{rid}/submit").status_code == 409  # not drafted from the pins yet
    CLIENT.post(f"/api/forecast/reports/{rid}/draft", json={})
    second = settled(rid)
    assert second["version"] == 2 and not second["stale"] and any(k.endswith(" weekly") for k in second["charts"])
    assert second["kpis"] and "Executive summary" in [s["title"] for s in second["sections"]]

    CLIENT.delete(f"/api/forecast/runs/{a}/pins/q1")
    CLIENT.post(f"/api/forecast/reports/{rid}/draft", json={})
    third = settled(rid)
    assert not any(k.endswith(" weekly") and k.startswith("F2") for k in third["charts"])
    assert CLIENT.post(f"/api/forecast/reports/{rid}/draft", json={"instruction": "shorter"}).status_code == 409  # no model
    assert CLIENT.post(f"/api/forecast/reports/{rid}/submit").json()["review_status"] == "pending_review"
    assert CLIENT.post(f"/api/forecast/reports/{rid}/draft", json={}).status_code == 409  # locked once submitted

    sign_in("dev-forecast-manager")
    lead = CLIENT.get(f"/api/forecast/reports/{rid}").json()
    assert "findings" not in lead and "versions" not in lead and "history" not in lead and lead["sections"]
    assert CLIENT.post(f"/api/forecast/reports/{rid}/review", json={"decision": "returned"}).status_code == 422
    assert CLIENT.post(f"/api/forecast/reports/{rid}/review", json={"decision": "approved"}).json()["review_status"] == "approved"
    assert CLIENT.post("/api/forecast/reports", json={"run_id": a}).status_code == 403
    assert CLIENT.post(f"/api/forecast/runs/{a}/pins/q1").status_code == 403

def test_chart_follow_ups_and_leaders_see_chart_data_without_evidence_ids(monkeypatch):
    import time

    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Mar to Oct 2026: Should any forecast assumptions be reviewed?"}).json()["forecast_run_id"]
    _wait(rid)
    for q in ("Plot it by week", "Plot it by quarter of the moon"):
        CLIENT.post(f"/api/forecast/runs/{rid}/followups", json={"question": q})
    for _ in range(100):
        body = CLIENT.get(f"/api/forecast/runs/{rid}").json()
        if all(f["status"] != "running" for f in body["followups"]):
            break
        time.sleep(0.1)
    weekly, other = body["followups"]
    assert weekly["op"] == "chart" and weekly["chart"]["id"] == "weekly" and weekly["chart"]["rows"]
    assert other["op"] == "chart"
    forecast_store.update(rid, review_status="pending_review")
    sign_in("dev-forecast-manager")
    lead = CLIENT.get(f"/api/forecast/runs/{rid}").json()["report"]
    assert lead["charts_shown"] == ["trend"] and set(lead["charts"]) == {"trend"}
    assert "evidence" not in lead["charts"]["trend"]


def test_a_split_follow_up_locates_the_gap_and_can_be_pinned(monkeypatch):
    import time

    monkeypatch.setenv("FORECAST_AGENT_MODEL", "rules")
    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Weeks of 2026-08-31 to 2026-09-28: Where is the miss concentrated?"}).json()["forecast_run_id"]
    _wait(rid)
    CLIENT.post(f"/api/forecast/runs/{rid}/followups", json={"question": "Split the South Central gap by plan and specialty"})
    for _ in range(100):
        f = CLIENT.get(f"/api/forecast/runs/{rid}").json()["followups"][0]
        if f["status"] != "running":
            break
        time.sleep(0.1)
    assert f["op"] == "drill" and "concentrated in Commercial" in f["answer"] and f["chart"]["rows"]
    CLIENT.post(f"/api/forecast/runs/{rid}/pins/{f['id']}")
    rep = CLIENT.post("/api/forecast/reports", json={"run_id": rid}).json()["id"]
    assert [x["kind"] for x in CLIENT.get(f"/api/forecast/reports/{rep}").json()["findings"]] == ["run", "drill"]


def test_the_forecast_model_is_local_qwen_unless_named(monkeypatch):
    monkeypatch.delenv("FORECAST_AGENT_MODEL", raising=False)
    monkeypatch.setenv("PHARMAGENTICS_AGENT_MODEL", "anthropic:claude-haiku-5-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-key")
    monkeypatch.setattr(forecast, "_ollama_up", lambda: True)
    assert forecast.question_model() == "ollama:qwen3:4b-instruct-2507-q4_K_M"  # a key alone never switches the model
    monkeypatch.setattr(forecast, "_ollama_up", lambda: False)
    assert forecast.question_model() is None  # no local model: code only
    monkeypatch.setenv("FORECAST_AGENT_MODEL", "anthropic:claude-haiku-5-5")
    assert forecast.question_model() == "anthropic:claude-haiku-5-5"  # only when named


# ---- review 2026-11-22: follow-up scopes are checked, and lost background work can be retried ----------------------

def _followups_done(rid: str) -> list[dict]:
    import time

    for _ in range(100):
        body = CLIENT.get(f"/api/forecast/runs/{rid}").json()
        if all(f["status"] != "running" for f in body["followups"]):
            return body["followups"]
        time.sleep(0.1)
    raise AssertionError("the follow-up did not finish")


@pytest.mark.parametrize("plan, says", [
    ({"op": "rerun", "territory": "Atlantis", "weeks": None, "drop_controls": []}, "don't know the territory"),
    ({"op": "rerun", "territory": None, "weeks": ["2031-01-06", "2031-02-03"], "drop_controls": []}, "outside the release"),
    ({"op": "rerun", "territory": None, "weeks": ["last spring", None], "drop_controls": []}, "as dates"),
    ({"op": "rerun", "territory": None, "weeks": ["2026-03-30", "2026-03-02"], "drop_controls": []}, "comes before"),
])
def test_a_rerun_follow_up_with_a_scope_the_release_lacks_runs_nothing(monkeypatch, plan, says):
    """A model picks the rerun's scope: a territory or weeks the release lacks get an answer, not a run on zero rows."""
    from forecast_agent import followup

    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()["forecast_run_id"]
    _wait(rid)
    monkeypatch.setattr(followup, "route", lambda *a, **k: dict(plan))
    assert CLIENT.post(f"/api/forecast/runs/{rid}/followups", json={"question": "rerun it"}).status_code == 200
    (f,) = _followups_done(rid)
    assert f["status"] == "done" and f["op"] == "help" and says in f["answer"] and not f["child_run_id"]


def test_a_rerun_follow_up_reads_a_territory_name_and_snaps_weeks_to_mondays(monkeypatch):
    from forecast_agent import followup

    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()["forecast_run_id"]
    _wait(rid)
    monkeypatch.setattr(followup, "route", lambda *a, **k: {"op": "rerun", "territory": "Pacific",
                                                             "weeks": ["2026-06-03", "2026-06-03"], "drop_controls": ["Mountain"]})
    CLIENT.post(f"/api/forecast/runs/{rid}/followups", json={"question": "rerun it"})
    (f,) = _followups_done(rid)
    child = CLIENT.get(f"/api/forecast/runs/{f['child_run_id']}").json()["report"]
    assert child["territory_id"] == "PACIFIC" and child["scope"]["weeks"] == ["2026-06-01"]


def _lost(record: dict, age_seconds: int) -> None:
    """Store a record as a restarted server would find it: nothing in this process works on it, last saved long ago."""
    from datetime import datetime, timedelta, timezone

    from pharmagentics.api.store import _dump, backend

    record["updated_at"] = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()
    backend().write(f"forecast_runs/{record['run_id']}.json", _dump(record))


def test_an_investigation_lost_to_a_restart_shows_as_failed_and_runs_again():
    sign_in("dev-forecast-analyst")
    q = {"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}
    rid = CLIENT.post("/api/forecast/ask", json=q).json()["forecast_run_id"]
    _wait(rid)
    record = forecast_store.get(rid)
    record.update(job_status="running")
    _lost(record, forecast_store.LOST_GRACE_SECONDS + 60)
    body = CLIENT.get(f"/api/forecast/runs/{rid}").json()
    assert body["job_status"] == "failed" and "restarted" in body["job_error"]
    assert CLIENT.post("/api/forecast/ask", json=q).json()["job_status"] == "running"  # asked again, it starts again
    assert _wait(rid)["job_status"] == "done"


def test_a_running_investigation_this_process_holds_is_not_failed():
    record = {"run_id": "f-0123456789ab", "kind": "question", "created_at": forecast_store.now(), "job_status": "running",
              "review_status": "not_submitted"}
    forecast_store.hold("f-0123456789ab")
    try:
        _lost(record, forecast_store.LOST_GRACE_SECONDS + 60)
        assert forecast_store.get("f-0123456789ab")["job_status"] == "running"
    finally:
        forecast_store.release("f-0123456789ab")
    assert forecast_store.get("f-0123456789ab")["job_status"] == "failed"


def test_a_follow_up_lost_to_a_restart_shows_as_failed():
    from datetime import datetime, timedelta, timezone

    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()["forecast_run_id"]
    _wait(rid)
    record = forecast_store.get(rid)
    old = (datetime.now(timezone.utc) - timedelta(seconds=forecast_store.LOST_GRACE_SECONDS + 60)).isoformat()
    record["followups"] = [{"id": "q1", "question": "why?", "status": "running", "op": None, "answer": None,
                            "child_run_id": None, "started_at": old}]
    _lost(record, 0)
    (f,) = CLIENT.get(f"/api/forecast/runs/{rid}").json()["followups"]
    assert f["status"] == "failed" and "restarted" in f["answer"]


def test_a_report_draft_lost_to_a_restart_unlocks_the_report():
    from datetime import datetime, timedelta, timezone

    from pharmagentics.api import forecast_reports

    sign_in("dev-forecast-analyst")
    rid = CLIENT.post("/api/forecast/ask", json={"question": "Week of 2026-08-24: How much of the miss does each driver explain?"}).json()["forecast_run_id"]
    _wait(rid)
    report = CLIENT.post("/api/forecast/reports", json={"run_id": rid}).json()
    for _ in range(100):
        r = forecast_reports.get(report["id"])
        if r["job"]["status"] != "drafting":
            break
        import time
        time.sleep(0.1)
    old = (datetime.now(timezone.utc) - timedelta(seconds=forecast_store.LOST_GRACE_SECONDS + 60)).isoformat()
    r["job"] = {"status": "drafting", "message": None, "started_at": old}
    forecast_reports.put(r)
    body = CLIENT.get(f"/api/forecast/reports/{report['id']}").json()
    assert body["job"]["status"] == "failed" and "restarted" in body["job"]["message"]
    assert CLIENT.post(f"/api/forecast/reports/{report['id']}/draft", json={}).status_code == 200


def test_a_review_saved_while_the_writer_runs_is_kept():
    """set_writer and review both read, change and save the run under one lock."""
    import threading

    sign_in("dev-forecast-analyst")
    run = CLIENT.post("/api/forecast/runs", json=NATIONAL).json()
    rid = run["forecast_run_id"]
    forecast_store.submit(rid, "u-a", "forecast-analyst")
    writer = {"narrative": {"summary": "x"}, "report_model": "m", "writer_status": "ok", "writer_attempts": []}
    threads = [threading.Thread(target=forecast_store.set_writer, args=(rid, writer)) for _ in range(20)]
    threads.append(threading.Thread(target=forecast_store.review, args=(rid, "approved", None, "u-b", "forecast-manager")))
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    record = forecast_store.get(rid)
    assert record["review_status"] == "approved" and record["writer_status"] == "ok"
