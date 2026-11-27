"""brief-005: the two-step sign-off. The review states, who may do what from which state, who may see which brief.

The state machine is tested exhaustively: every (stored shape, role, action) is driven through the real API against a brief
seeded in that state, and compared with an explicit table written here (not read from signoff.py). Stored shapes include the
records written before sign-off existed (pending, approved, rejected), which are read as draft, signed off and rejected.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import rbac, service, signoff, store, views
from pharmagentics.api.app import app
from pharmagentics.api.schemas import BriefingResult

VALID = {"intent": "weekly_brief", "brand_id": "BXA", "territory_id": "PACIFIC", "week_start": "2026-06-08",
         "question": "Generate the weekly brand-performance briefing."}
ANSWER = "Brief for week of 2026-06-08. BXA TRx averaged 464 a week (down 31.2%).\nChecked, in this order:\n- Supply: supported."


def result(answer: str = ANSWER) -> dict:
    return {"system": "briefing_scripted", "engine": "scripted", "question": VALID["question"], "brand_id": "BXA", "territory_id": "PACIFIC",
            "week_start": "2026-06-08", "answer": answer, "data_version": "vtest", "abstained": False,
            "claims": [{"value": "464", "evidence_id": "e1"}, {"value": "31.2%", "evidence_id": "e2"}],
            "evidence": [{"id": "e1", "tool": "get_metric", "query": "select sum(trx) from reporting.v_weekly_rx_kpis", "result": 464, "data_version": "vtest"},
                         {"id": "e2", "tool": "get_change", "query": "select 1 from reporting.v_weekly_rx_kpis", "result": 31.2, "data_version": "vtest"}]}


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("PHARMAGENTICS_STATE_BUCKET", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)


def signed_in(username: str, view: str | None = None) -> TestClient:
    client = TestClient(app)
    assert client.post("/auth/dev-login", data={"username": username}, follow_redirects=False).status_code == 303
    if view:
        assert client.post("/api/me/view-as", json={"view": view}).status_code == 200
    return client


def run(analyst: TestClient, answer: str = ANSWER) -> dict:
    with patch.object(service, "run_briefing", return_value=BriefingResult.model_validate(result(answer))):
        response = analyst.post("/api/briefing/query", json=VALID)
    assert response.status_code == 200, response.text
    return response.json()


def leaks(body) -> list[str]:
    text = json.dumps(body).lower()
    return [k for k in ('"claims"', '"evidence"', '"answer"', '"query"', "select ", "reporting.v_", "checked, in this order", "review_trail", "flags")
            if k in text]


# --- the state machine, exhaustively --------------------------------------------------------------------------

STATES = ("draft", "sent", "signed_off", "returned", "rejected")
ACTIONS = ("read", "send", "reject", "sign_off", "return")
NEW_STATE = {"send": "sent", "reject": "rejected", "sign_off": "signed_off", "return": "returned"}

# Every stored shape and the state it is read as. The three legacy shapes are briefs saved before sign-off existed.
SHAPES = {
    "draft": ("draft", {"review_state": "draft", "review_status": "pending"}),
    "sent": ("sent", {"review_state": "sent", "review_status": "pending"}),
    "signed_off": ("signed_off", {"review_state": "signed_off", "review_status": "approved", "signed_off_at": "2026-11-27T10:00:00+00:00"}),
    "returned": ("returned", {"review_state": "returned", "review_status": "pending"}),
    "rejected": ("rejected", {"review_state": "rejected", "review_status": "rejected"}),
    "legacy pending": ("draft", {"review_status": "pending"}),
    "legacy approved": ("signed_off", {"review_status": "approved", "reviewed_at": "2026-11-20T10:00:00+00:00", "reviewed_by": "u-old"}),
    "legacy rejected": ("rejected", {"review_status": "rejected", "reviewed_at": "2026-11-20T10:00:00+00:00", "review_reason": "Wrong week."}),
}

# P1 may read everything, send from draft, returned or rejected, reject until sign-off. P2 sees only what was sent on to it, and
# signs off or returns a sent brief. P3 and P4 read signed-off briefs and do nothing else. Written out by hand on purpose.
EXPECTED = {
    "P1": {"read": dict.fromkeys(STATES, 200),
           "send": {"draft": 200, "sent": 409, "signed_off": 409, "returned": 200, "rejected": 200},
           "reject": {"draft": 200, "sent": 200, "signed_off": 409, "returned": 200, "rejected": 409},
           "sign_off": dict.fromkeys(STATES, 403), "return": dict.fromkeys(STATES, 403)},
    "P2": {"read": {"draft": 404, "sent": 200, "signed_off": 200, "returned": 200, "rejected": 404},
           "send": dict.fromkeys(STATES, 403), "reject": dict.fromkeys(STATES, 403),
           "sign_off": {"draft": 404, "sent": 200, "signed_off": 409, "returned": 409, "rejected": 404},
           "return": {"draft": 404, "sent": 200, "signed_off": 409, "returned": 409, "rejected": 404}},
    "P3": {"read": {**dict.fromkeys(STATES, 404), "signed_off": 200}, **{a: dict.fromkeys(STATES, 403) for a in ACTIONS[1:]}},
    "P4": {"read": {**dict.fromkeys(STATES, 404), "signed_off": 200}, **{a: dict.fromkeys(STATES, 403) for a in ACTIONS[1:]}},
}
ACTORS = [("P1", "dev-analyst", None), ("P2", "dev-insights", None), ("P3", "dev-director", None), ("P4", "dev-marketer", None),
          ("P1", "dev-tester", "analyst"), ("P2", "dev-tester", "insights"), ("P3", "dev-tester", "leadership"), ("P4", "dev-tester", "marketer")]


def seed(shape: str) -> str:
    """A saved brief in the stored shape asked for, written straight to the store."""
    bid = store.save_brief(result(), by="u-seed")["brief_id"]
    record = store.get_brief(bid)
    for key in ("review_state", "review_status", "reviewed_at", "reviewed_by", "review_reason", "signed_off_at", "review_trail"):
        record.pop(key, None)
    record.update(SHAPES[shape][1])
    store.backend().write(f"briefs/{bid}.json", json.dumps(record))
    return bid


def act(client: TestClient, persona: str, action: str, bid: str):
    if action == "read":
        return client.get(f"/api/briefing/{bid}", params={"view": "analyst" if persona in ("P1", "P2") else "leadership"})
    if action == "send":
        return client.post(f"/api/briefing/{bid}/review", json={"decision": "sent"})
    if action == "reject":
        return client.post(f"/api/briefing/{bid}/review", json={"decision": "rejected", "reason": "Wrong week."})
    if action == "sign_off":
        return client.post(f"/api/briefing/{bid}/signoff", json={"decision": "signed_off"})
    return client.post(f"/api/briefing/{bid}/signoff", json={"decision": "returned", "comment": "Check the supply driver."})


@pytest.mark.parametrize("persona,user,view", ACTORS, ids=[f"{p}:{u}{':' + v if v else ''}" for p, u, v in ACTORS])
def test_every_state_role_and_action_gives_the_expected_answer(persona, user, view):
    client = signed_in(user, view)
    for shape, (state, _) in SHAPES.items():
        for action in ACTIONS:
            bid = seed(shape)
            response = act(client, persona, action, bid)
            want = EXPECTED[persona][action][state]
            assert response.status_code == want, (persona, shape, action, response.text)
            after = signoff.state_of(store.get_brief(bid))
            assert after == (NEW_STATE[action] if want == 200 and action != "read" else state), (persona, shape, action)
            if want == 200 and action == "read":
                body = response.json()
                assert body["review_status"] == state  # the API always speaks the new vocabulary, even for a legacy record
                assert (persona in ("P3", "P4")) == (body["view"] == "leadership")
                assert (persona in ("P3", "P4")) == (leaks(body) == [] and "review_trail" not in body)


def test_the_table_has_a_row_for_every_role_with_a_briefing_login():
    briefing = {r.persona: r for r in rbac.roles().values() if r.lane == "briefing"}
    assert set(EXPECTED) == set(briefing) == {"P1", "P2", "P3", "P4"}
    for persona, role in briefing.items():  # the table above agrees with roles.json, not only with signoff.py
        for action in ACTIONS:
            for state in STATES:
                assert signoff.outcome(role.actions, role.states, state, action) == EXPECTED[persona][action][state], (persona, action, state)


def test_the_forecast_roles_and_users_without_a_role_do_none_of_it():
    bid = seed("sent")
    for user in ("dev-forecast-analyst", "dev-forecast-manager", "dev-norole"):
        client = signed_in(user)
        for action in ACTIONS:
            assert act(client, "P1", action, bid).status_code == 403, (user, action)
    assert TestClient(app).post(f"/api/briefing/{bid}/signoff", json={"decision": "signed_off"}).status_code == 401


def test_an_unknown_brief_and_an_ungranted_brand_are_404_for_every_briefing_role():
    for user in ("dev-analyst", "dev-insights"):
        assert signed_in(user).post("/api/briefing/b-000000000000/signoff", json={"decision": "signed_off"}).status_code in (403, 404)
    assert signed_in("dev-insights").post("/api/briefing/b-000000000000/signoff", json={"decision": "signed_off"}).status_code == 404
    assert signed_in("dev-analyst").post("/api/briefing/b-000000000000/review", json={"decision": "sent"}).status_code == 404


# --- the whole round trip --------------------------------------------------------------------------------------

def test_send_flag_return_rerun_resend_sign_off_and_the_leaders_read_it():
    p1, p2 = signed_in("dev-analyst"), signed_in("dev-insights")
    p3, p4 = signed_in("dev-director"), signed_in("dev-marketer")
    brief = run(p1)
    bid = brief["brief_id"]
    assert brief["review_status"] == "draft" and brief["review_trail"] == [] and brief["returned"] is None

    with patch.object(service, "current_data_version", return_value="vtest"):
        sent = p1.post(f"/api/briefing/{bid}/review", json={"decision": "sent"}).json()
        assert sent["review_status"] == "sent"
        queue = p2.get("/api/briefing/queue").json()
        assert [(r["brief_id"], r["review_status"]) for r in queue] == [(bid, "sent")]
        assert [r["review_status"] for r in p1.get("/api/briefing/queue").json()] == ["sent"]
        for leader in (p3, p4):
            assert leader.get("/api/briefing/published").json() == [] and leader.get(f"/api/briefing/{bid}").status_code == 404
            assert leader.get("/api/briefing/queue").status_code == 403

        # P2 reads the full analyst view, read-only: evidence and SQL, but no way to run, send or reject
        seen = p2.get(f"/api/briefing/{bid}").json()
        assert seen["view"] == "analyst" and seen["claims"] and seen["evidence"][0]["query"]
        assert p2.post("/api/briefing/query", json=VALID).status_code == 403
        assert p2.post(f"/api/briefing/{bid}/review", json={"decision": "sent"}).status_code == 403

        # returning needs a comment; a flag must name a claim of the brief, once
        back = f"/api/briefing/{bid}/signoff"
        assert p2.post(back, json={"decision": "returned"}).status_code == 422
        assert p2.post(back, json={"decision": "returned", "comment": "   "}).status_code == 422
        assert p2.post(back, json={"decision": "returned", "comment": "x", "flags": [{"claim": 2}]}).status_code == 422
        assert p2.post(back, json={"decision": "returned", "comment": "x", "flags": [{"claim": 0}, {"claim": 0}]}).status_code == 422
        assert p2.post(back, json={"decision": "signed_off", "flags": [{"claim": 0}]}).status_code == 422
        assert signoff.state_of(store.get_brief(bid)) == "sent"
        returned = p2.post(back, json={"decision": "returned", "comment": "The decline is not 31.2%; recheck the comparison.",
                                       "flags": [{"claim": 1, "note": "Looks like a different base."}, {"claim": 0}]})
        assert returned.status_code == 200 and returned.json()["review_status"] == "returned"
        assert p3.get(f"/api/briefing/{bid}").status_code == 404 and p4.get(f"/api/briefing/{bid}").status_code == 404

        # P1 sees the comment and the flags on the returned brief, with the numbers they point at
        mine = p1.get(f"/api/briefing/{bid}").json()
        note = mine["returned"]
        assert note["comment"].startswith("The decline is not 31.2%")
        assert [(f["claim"], f["value"], f["evidence_id"], f["note"]) for f in note["flags"]] == [(1, "31.2%", "e2", "Looks like a different base."), (0, "464", "e1", None)]
        assert [r["review_status"] for r in p1.get("/api/briefing/queue").json()] == ["returned"]

        # P1 reruns with the same definition: the same brief, still returned, and sends it again
        again = run(p1)
        assert again["brief_id"] == bid and again["review_status"] == "returned" and again["returned"] == note
        assert p1.post(f"/api/briefing/{bid}/review", json={"decision": "sent"}).json()["review_status"] == "sent"
        assert p2.post(back, json={"decision": "signed_off", "comment": "Fixed."}).json()["review_status"] == "signed_off"

        # signed off: it reaches P3 and P4, without evidence, and is frozen
        for leader in (p3, p4):
            listed = leader.get("/api/briefing/published").json()
            assert [b["brief_id"] for b in listed] == [bid] and listed[0]["reviewed_at"]
            body = leader.get(f"/api/briefing/{bid}").json()
            assert body["view"] == "leadership" and body["review_status"] == "signed_off" and leaks(body) == []
        assert p3.get(f"/api/briefing/{bid}").json() == p4.get(f"/api/briefing/{bid}").json()  # for now P4 reads what P3 reads
        assert p1.post(f"/api/briefing/{bid}/review", json={"decision": "rejected", "reason": "too late"}).status_code == 409
        assert p2.post(back, json={"decision": "returned", "comment": "too late"}).status_code == 409
        assert [r["review_status"] for r in p2.get("/api/briefing/queue").json()] == ["signed_off"]
        assert p1.get("/api/briefing/queue").json() == []

    # the audit trail: every step, in order, with the comment and the flags kept
    trail = store.get_brief(bid)["review_trail"]
    assert [(e["persona"], e["action"], e["from"], e["to"]) for e in trail] == [
        ("P1", "sent", "draft", "sent"), ("P2", "returned", "sent", "returned"), ("P1", "sent", "returned", "sent"), ("P2", "signed_off", "sent", "signed_off")]
    assert trail[1]["comment"].startswith("The decline") and len(trail[1]["flags"]) == 2 and trail[3]["comment"] == "Fixed."
    assert p1.get(f"/api/briefing/{bid}").json()["review_trail"] == trail and p2.get(f"/api/briefing/{bid}").json()["review_trail"] == trail

    # every transition is a UAT event, pseudonymous, with the persona that made it
    events = [json.loads(store.backend().read(k)) for k in store.backend().keys("events/")]
    steps = sorted((e["ts"], e["persona"], e["decision"], e["state"]) for e in events if e["kind"] == "reviewed")
    assert [(p, d, s) for _, p, d, s in steps] == [("P1", "sent", "sent"), ("P2", "returned", "returned"), ("P1", "sent", "sent"), ("P2", "signed_off", "signed_off")]
    returned_event = next(e for e in events if e.get("decision") == "returned")
    assert returned_event["flags"] == 2 and returned_event["user"] == rbac.pseudonym("dev-insights") and "dev-insights" not in json.dumps(events)


def test_a_rerun_with_a_changed_answer_starts_a_new_draft_and_keeps_what_was_said():
    p1, p2 = signed_in("dev-analyst"), signed_in("dev-insights")
    bid = run(p1)["brief_id"]
    p1.post(f"/api/briefing/{bid}/review", json={"decision": "sent"})
    p2.post(f"/api/briefing/{bid}/signoff", json={"decision": "returned", "comment": "Wrong base.", "flags": [{"claim": 0, "note": "No."}]})
    changed = run(p1, ANSWER.replace("464", "465"))
    assert changed["brief_id"] == bid and changed["review_status"] == "draft"  # the same definition, new text: a new draft for P1
    assert [(e["persona"], e["action"]) for e in changed["review_trail"]] == [("P1", "sent"), ("P2", "returned"), ("P1", "rerun")]
    assert changed["review_trail"][1]["flags"][0]["note"] == "No." and changed["returned"] is None
    assert p2.get(f"/api/briefing/{bid}").status_code == 404  # drafts are P1's


def test_a_signed_off_brief_is_frozen_against_a_rerun():
    p1 = signed_in("dev-analyst")
    bid = run(p1)["brief_id"]
    from signoff_helpers import approve

    approve(p1, bid)
    before = store.backend().read(f"briefs/{bid}.json")
    rerun = run(p1, ANSWER.replace("464", "465"))
    assert rerun["review_status"] == "signed_off" and "464" in rerun["answer"] and "465" not in rerun["answer"]
    assert store.backend().read(f"briefs/{bid}.json") == before


def test_a_brief_approved_before_sign_off_existed_counts_as_signed_off_and_is_never_rewritten():
    bid = seed("legacy approved")
    path = f"briefs/{bid}.json"
    before = store.backend().read(path)
    with patch.object(service, "current_data_version", return_value="vtest"):
        for user in ("dev-director", "dev-marketer", "dev-insights"):
            client = signed_in(user)
            assert [b["brief_id"] for b in client.get("/api/briefing/published").json()] == [bid], user
            assert client.get(f"/api/briefing/{bid}").status_code == 200
        body = signed_in("dev-director").get(f"/api/briefing/{bid}").json()
        assert body["review_status"] == "signed_off" and body["reviewed_at"] == "2026-11-20T10:00:00+00:00"
        mine = signed_in("dev-analyst").get(f"/api/briefing/{bid}").json()
        assert mine["review_trail"][0]["legacy"] is True and mine["returned"] is None
    assert store.backend().read(path) == before  # reads and lists never rewrite stored history
    assert views.process_summary(store.get_brief(bid)) is not None and "signed off by the Insights Manager" not in (views.process_summary(store.get_brief(bid)) or "")


def test_a_legacy_rejection_keeps_its_reason_in_the_trail_when_the_analyst_sends_it_again():
    bid = seed("legacy rejected")
    p1 = signed_in("dev-analyst")
    assert p1.post(f"/api/briefing/{bid}/review", json={"decision": "sent"}).status_code == 200
    trail = store.get_brief(bid)["review_trail"]
    assert [(e["action"], e.get("comment")) for e in trail] == [("rejected", "Wrong week."), ("sent", None)]


def test_a_rejection_needs_a_reason_and_a_return_needs_a_comment():
    p1, p2 = signed_in("dev-analyst"), signed_in("dev-insights")
    bid = seed("sent")
    assert p1.post(f"/api/briefing/{bid}/review", json={"decision": "rejected"}).status_code == 422
    assert p2.post(f"/api/briefing/{bid}/signoff", json={"decision": "returned"}).status_code == 422
    assert signoff.state_of(store.get_brief(bid)) == "sent"


def test_the_one_old_decision_word_is_gone():
    bid = seed("draft")
    assert signed_in("dev-analyst").post(f"/api/briefing/{bid}/review", json={"decision": "approved"}).status_code == 422


# --- the leader payload and the seam for the Marketer -------------------------------------------------------------

def test_leader_payload_is_one_function_per_persona_and_never_carries_evidence():
    bid = seed("signed_off")
    record = store.get_brief(bid)
    for persona in ("P1", "P2", "P3", "P4"):
        payload = views.leader_payload(record, persona)
        assert payload["view"] == "leadership" and leaks(payload) == []
        assert set(payload) == set(views.LEADERSHIP_FIELDS) | {"view", "summary", "sections", "process_summary"}
    assert views.leader_payload(record, "P3") == views.leader_payload(record, "P4")  # the seam: no marketer content yet


# --- the test login --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("view,persona,views_,lanes", [
    ("analyst", "P1", ["analyst", "leadership"], ["briefing", "forecast"]),
    ("insights", "P2", ["analyst", "leadership"], ["briefing"]),
    ("leadership", "P3", ["leadership"], ["briefing", "forecast"]),
    ("marketer", "P4", ["leadership"], ["briefing"]),
])
def test_the_test_login_switches_between_all_four_briefing_personas(view, persona, views_, lanes):
    c = signed_in("dev-tester")
    me = c.post("/api/me/view-as", json={"view": view}).json()
    assert me["view_as"] == view and me["tester"] is True and list(me["lanes"]) == lanes
    assert me["lanes"]["briefing"]["persona"] == persona and me["lanes"]["briefing"]["views"] == views_
    assert c.get("/api/me").json()["view_as"] == view  # kept in the session
    forecast = c.get("/api/forecast/runs").status_code
    assert (forecast == 200) == ("forecast" in lanes) and (forecast == 403) == ("forecast" not in lanes)


def test_only_the_test_login_switches_and_only_to_a_known_view():
    assert signed_in("dev-insights").post("/api/me/view-as", json={"view": "analyst"}).status_code == 403
    assert signed_in("dev-tester").post("/api/me/view-as", json={"view": "director"}).status_code == 422


def test_the_two_new_logins_have_both_brands_and_their_own_roles():
    for user, role, persona in (("dev-insights", "briefing-insights", "P2"), ("dev-marketer", "briefing-marketer", "P4")):
        me = signed_in(user).get("/api/me").json()
        assert me["brand_ids"] == ["BXA", "BXC"] and me["lanes"]["briefing"]["role"] == role and me["lanes"]["briefing"]["persona"] == persona
        assert list(me["lanes"]) == ["briefing"]
