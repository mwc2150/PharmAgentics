"""Telemetry: golden-set snapshot per lane, live-use aggregates, and test-login traffic left out."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import feedback, jobs, rbac, store, telemetry
from pharmagentics.api.app import app

SNAPSHOT_FIELDS = {"run_id", "started", "minutes", "system", "model", "lane", "control", "cases", "reruns", "judge",
                   "code_version", "data_version", "metrics", "judge_metrics"}


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("PHARMAGENTICS_STATE_BUCKET", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    telemetry.reset()
    jobs.reset()
    yield
    telemetry.reset()
    jobs.reset()


def signed_in(user: str) -> TestClient:
    c = TestClient(app)
    assert c.post("/auth/dev-login", data={"username": user}, follow_redirects=False).status_code == 303
    return c


def event(kind: str, ts: str, user: str, **fields) -> dict:
    return {"kind": kind, "ts": ts, "user": user, **fields}


def test_for_lanes_keeps_own_lane_and_cross_lane_runs():
    snap = {"latest": [{"lane": "briefing"}, {"lane": "forecast"}, {"lane": "all"}], "runs": [{"lane": "forecast"}]}
    out = telemetry.for_lanes(snap, {"briefing"})
    assert [r["lane"] for r in out["latest"]] == ["briefing", "all"] and out["runs"] == []


def test_bundled_snapshot_holds_scores_only():
    for r in json.loads(telemetry.FILE.read_text(encoding="utf-8"))["runs"]:
        assert set(r) <= SNAPSHOT_FIELDS
        assert all(isinstance(v, (int, float)) for v in {**r["metrics"], **r["judge_metrics"]}.values())


@pytest.mark.parametrize("values, q, expected", [([5], 0.5, 5), ([1, 2, 3, 4], 0.5, 2), ([1, 2, 3, 4], 0.95, 4),
                                                ([*range(1, 101)], 0.95, 95), ([], 0.5, None)])
def test_percentile_is_nearest_rank(values, q, expected):
    assert telemetry._percentile(values, q) == expected


def test_bucket_copy_wins_over_bundled_copy():
    store.backend().write(telemetry.BUCKET_KEY, json.dumps({**telemetry.EMPTY, "exported": "2026-11-20T00:00+00:00"}))
    assert telemetry.snapshot()["exported"] == "2026-11-20T00:00+00:00"


def test_usage_counts_the_shared_tester_login_and_says_how_much_came_from_it():
    events = [
        event("requested", "2026-11-17T10:00:00+00:00", "u-p1", engine="scripted", latency_ms=1000),
        event("requested", "2026-11-18T10:00:00+00:00", "u-p1", engine="scripted", latency_ms=3000),
        event("reviewed", "2026-11-18T11:00:00+00:00", "u-p1", decision="approved"),
        event("agent_job", "2026-11-18T12:00:00+00:00", "u-test", test=True),
        event("requested", "2026-11-18T12:01:00+00:00", "u-test", engine="agent"),
        event("forecast_run", "2026-11-19T09:00:00+00:00", "u-ca"),
    ]
    job_docs = [
        {"by": "u-p1", "kind": "brief", "status": "done", "created_at": "2026-11-18T10:00:00+00:00", "finished_at": "2026-11-18T10:01:00+00:00"},
        {"by": "u-test", "kind": "brief", "status": "done", "created_at": "2026-11-18T12:00:00+00:00", "finished_at": "2026-11-18T12:30:00+00:00"},
    ]
    pulses = [{"session": "s1", "user": "u-test", "rating": "bad", "ts": "2026-11-18T12:02:00+00:00", "where": "briefing", "test": True}]
    u = telemetry.summarize_usage(events, job_docs, pulses, [], [], feedback.questionnaire())
    b = u["lanes"]["briefing"]
    assert b["requests"] == 3 and b["engines"] == {"scripted": 2, "agent": 1}  # the class uses the tester login
    assert b["decisions"] == {"approved": 1}
    assert b["scripted_ms"] == {"n": 2, "p50": 1000, "p95": 3000}
    assert b["agent_jobs"] == {"brief done": 2} and b["agent_seconds"]["n"] == 2
    assert b["weekly"] == {"2026-11-16": 3}
    assert u["lanes"]["forecast"]["requests"] == 1
    assert "participants" not in u and u["tester_records"] == 4 and u["sessions"]["bad"] == 1


def test_review_outcomes_count_briefs_not_approval_events():
    """UAT review 6.2: three approval events on one brief are one brief, and under ten briefs there is no rate."""
    ev = [event("reviewed", f"2026-11-18T11:0{i}:00+00:00", "u-p1", decision="approved", brief_id="b1") for i in range(3)]
    one = telemetry.review_outcomes(ev)
    assert one == {"briefs": 1, "approved": 1, "rejected": 0, "min_briefs": 10, "enough": False, "approved_pct": None, "label": "too few to rate"}
    ev += [event("reviewed", "2026-11-18T12:00:00+00:00", "u-p1", decision="rejected", brief_id="b1")]  # a later change of mind stands
    assert telemetry.review_outcomes(ev)["approved"] == 0 and telemetry.review_outcomes(ev)["rejected"] == 1
    many = [event("reviewed", f"2026-11-19T10:{i:02d}:00+00:00", "u-p1", decision="approved" if i < 7 else "rejected", brief_id=f"b{i}")
            for i in range(10)]
    ten = telemetry.review_outcomes(many)
    assert (ten["briefs"], ten["approved"], ten["rejected"], ten["enough"], ten["approved_pct"], ten["label"]) == (10, 7, 3, True, 70, None)
    assert telemetry.review_outcomes([event("reviewed", "2026-11-19T10:00:00+00:00", "u-p1", decision="approved")])["briefs"] == 0


def test_usage_carries_the_review_outcomes_for_the_briefing_lane_only():
    ev = [event("reviewed", "2026-11-18T11:00:00+00:00", "u-p1", decision="approved", brief_id="b1"),
          event("reviewed", "2026-11-18T11:05:00+00:00", "u-p1", decision="approved", brief_id="b1")]
    lanes = telemetry.summarize_usage(ev, [], [], [], [], feedback.questionnaire())["lanes"]
    assert lanes["briefing"]["decisions"] == {"approved": 2}  # event counts stay as they were
    assert lanes["briefing"]["review"]["briefs"] == 1 and lanes["briefing"]["review"]["label"] == "too few to rate"
    assert "review" not in lanes["forecast"]


def test_usage_endpoint_shows_only_the_signed_in_lanes_and_no_person():
    p1 = rbac.pseudonym("dev-analyst")
    store.record_event("requested", user=p1, role="briefing-analyst", persona="P1", engine="scripted", latency_ms=800)
    store.record_event("forecast_run", user=rbac.pseudonym("dev-forecast-analyst"), role="forecast-analyst", persona="CA")
    assert signed_in("dev-tester").post("/api/feedback/pulse", json={"rating": "bad", "where": "briefing"}).status_code == 200

    insights = signed_in("dev-insights").get("/api/telemetry/usage")
    assert insights.status_code == 200 and insights.headers["cache-control"] == "no-store"
    body = insights.json()
    assert set(body["lanes"]) == {"briefing"} and body["lanes"]["briefing"]["requests"] == 1
    assert body["sessions"] == {**{r: 0 for r in feedback.RATINGS}, "bad": 1}  # the shared tester login counts
    assert p1 not in json.dumps(body)

    assert set(signed_in("dev-forecast-analyst").get("/api/telemetry/usage").json()["lanes"]) == {"forecast"}
    assert signed_in("dev-norole").get("/api/telemetry/usage").status_code == 403
    assert TestClient(app).get("/api/telemetry/usage").status_code == 401


@pytest.mark.parametrize("user,code", [("dev-analyst", 200), ("dev-insights", 200), ("dev-forecast-analyst", 200), ("dev-tester", 200),
                                       ("dev-forecast-manager", 200), ("dev-director", 403), ("dev-marketer", 403), ("dev-norole", 403)])
def test_the_evaluation_page_is_closed_to_the_briefing_leaders_only(user, code):
    """Michael, 2026-11-27 (Q17): not the Director or the Marketer; the server refuses, not just the nav. The Forecast
    lane's access is unchanged (BM keeps the page; Forecast is Alvin and Sienna's)."""
    c = signed_in(user)
    assert c.get("/api/telemetry").status_code == code and c.get("/api/telemetry/usage").status_code == code
    if user != "dev-norole":
        assert c.get("/api/me").json()["evaluation"] is (code == 200)


def test_the_tester_keeps_the_page_in_every_view_and_loses_it_never():
    c = signed_in("dev-tester")
    for view in ("analyst", "insights", "leadership", "marketer"):
        assert c.post("/api/me/view-as", json={"view": view}).json()["evaluation"] is True
        assert c.get("/api/telemetry").status_code == 200, view


def test_review_outcomes_count_a_brief_once_by_its_latest_decision_and_leave_waiting_ones_out():
    def ev(i, brief, decision):
        return {"kind": "reviewed", "ts": f"2026-11-27T10:{i:02d}:00+00:00", "brief_id": brief, "decision": decision}
    events = [ev(0, "b1", "sent"), ev(1, "b1", "returned"), ev(2, "b1", "sent"), ev(3, "b1", "signed_off"),  # returned, then signed off: approved once
              ev(4, "b2", "sent"), ev(5, "b2", "returned"),                                             # returned: rejected
              ev(6, "b3", "sent"),                                                                        # waiting: not counted
              ev(7, "b4", "rejected"),                                                                    # the analyst's own rejection
              ev(8, "b5", "approved")]                                                                    # approved before sign-off existed
    out = telemetry.review_outcomes(events)
    assert (out["briefs"], out["approved"], out["rejected"]) == (4, 2, 2)


def test_eval_endpoint_filters_runs_by_lane():
    store.backend().write(telemetry.BUCKET_KEY, json.dumps({**telemetry.EMPTY, "latest": [
        {"lane": "briefing", "system": "a"}, {"lane": "forecast", "system": "b"}, {"lane": "all", "system": "c"}]}))
    latest = signed_in("dev-forecast-analyst").get("/api/telemetry").json()["latest"]
    assert [r["system"] for r in latest] == ["b", "c"]


CASES = {"generated": "2026-11-22T10:00:00+00:00", "systems": [
    {"system": "briefing_scripted", "lane": "briefing", "rows": [{"case": "P1-Q1", "story": "US-1", "scores": {"claims_reconcile": 1.0}}]},
    {"system": "forecast_scripted", "lane": "forecast", "rows": [{"case": "BM-Q1", "story": "FE-1", "scores": {"claims_reconcile": None}}]}]}


def _with_cases():
    store.backend().write(telemetry.BUCKET_KEY, json.dumps({**telemetry.EMPTY, "cases": CASES}))


def test_cases_go_to_analysts_in_their_lane_and_to_the_tester_only():
    _with_cases()
    briefing = signed_in("dev-analyst").get("/api/telemetry").json()
    assert [s["lane"] for s in briefing["cases"]["systems"]] == ["briefing"]
    assert [s["lane"] for s in signed_in("dev-forecast-analyst").get("/api/telemetry").json()["cases"]["systems"]] == ["forecast"]
    tester = signed_in("dev-tester").get("/api/telemetry").json()
    assert {s["lane"] for s in tester["cases"]["systems"]} == {"briefing", "forecast"}


def test_leadership_roles_get_no_cases_block():
    _with_cases()
    for user in ("dev-director", "dev-forecast-manager"):
        body = signed_in(user).get("/api/telemetry").json()
        assert "cases" not in body and "P1-Q1" not in json.dumps(body) and "BM-Q1" not in json.dumps(body)


def test_the_tester_keeps_the_per_case_table_in_the_leadership_view():
    _with_cases()
    c = signed_in("dev-tester")
    assert c.post("/api/me/view-as", json={"view": "leadership"}).status_code == 200
    assert {s["lane"] for s in c.get("/api/telemetry").json()["cases"]["systems"]} == {"briefing", "forecast"}


def test_for_lanes_drops_cases_without_case_lanes():
    out = telemetry.for_lanes({"latest": [], "runs": [], "cases": CASES}, {"briefing"})
    assert "cases" not in out
