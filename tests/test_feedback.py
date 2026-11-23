"""core-008 UAT feedback: the session pulse, the platform questionnaire, UMUX-Lite and legacy SUS scoring, the report maths and the workbook.

Uses the stand-in identities (PHARMAGENTICS_AUTH=dev) and a temporary state folder. No model, no database.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import auth, feedback, rbac, store
from pharmagentics.api.app import app

ALL_USERS = ("dev-analyst", "dev-director", "dev-forecast-analyst", "dev-forecast-manager")
Q = feedback.questionnaire()
UMUX = Q["scoring"]["umux_lite"]
SUS = [f"sus{n}" for n in range(1, 11)]


def _legacy_questionnaire() -> dict:
    """Questionnaire version 1 (ten SUS statements, a choice, a multi and three text questions): responses to it must still load."""
    q = deepcopy(Q)
    q["version"], q["scoring"] = 1, {"sus": SUS}
    q["sections"].insert(0, {"id": "usability", "title": "Using PharmAgentics", "items": [
        {"id": sid, "type": "agree5", "reverse": n % 2 == 1, "text": f"SUS statement {n + 1}."} for n, sid in enumerate(SUS)]})
    q["sections"].append({"id": "legacy", "title": "More", "items": [
        {"id": "o_used", "type": "multi", "text": "Which parts did you use?", "options": [{"value": "briefing", "label": "Weekly briefing"}, {"value": "agent", "label": "Agent team"}]},
        {"id": "o_freq", "type": "choice", "text": "How often?", "options": [{"value": "weekly", "label": "Every week"}, {"value": "never", "label": "Not at all"}]},
        {"id": "x_best", "type": "text", "max": 1000, "text": "What worked best?"}]})
    return q


V1 = _legacy_questionnaire()
ROUTES = [("get", "/api/feedback/status"), ("post", "/api/feedback/pulse"), ("get", "/api/feedback/questionnaire"),
          ("get", "/api/feedback/survey"), ("post", "/api/feedback/survey")]


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("PHARMAGENTICS_STATE_BUCKET", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)


def signed_in(user: str) -> TestClient:
    c = TestClient(app)
    assert c.post("/auth/dev-login", data={"username": user}, follow_redirects=False).status_code == 303
    return c


def stored(tmp_path: Path, prefix: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in (tmp_path / prefix).rglob("*.json")]


def sus_answers(odd: int, even: int) -> dict:
    return {sid: (odd if n % 2 == 0 else even) for n, sid in enumerate(SUS)}


# --- who may use it -------------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", ROUTES)
def test_signed_out_users_get_nothing(method, path):
    assert getattr(TestClient(app), method)(path).status_code == 401


@pytest.mark.parametrize("method,path", ROUTES)
def test_an_account_with_no_role_gets_nothing(method, path):
    assert getattr(signed_in("dev-norole"), method)(path).status_code == 403


@pytest.mark.parametrize("user", ALL_USERS)
def test_every_persona_can_rate_and_answer(user):
    c = signed_in(user)
    assert c.post("/api/feedback/pulse", json={"rating": "good"}).status_code == 200
    assert c.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"o_change": "Clear."}}).status_code == 200


# --- the session pulse ----------------------------------------------------------------------------

def test_pulse_is_stored_without_any_personal_detail(tmp_path):
    c = signed_in("dev-analyst")
    r = c.post("/api/feedback/pulse", json={"rating": "bad", "comment": "  Slow after I clicked approve.  ", "where": "briefing", "ref": "b-0123456789ab"})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    (doc,) = stored(tmp_path, "feedback/pulse")
    assert doc["rating"] == "bad" and doc["comment"] == "Slow after I clicked approve." and doc["where"] == "briefing"
    assert doc["user"] == rbac.pseudonym("dev-analyst") and doc["personas"] == ["P1"] and doc["roles"] == ["briefing-analyst"]
    text = json.dumps(doc)
    assert "dev-analyst" not in text and auth.DEV_USERS["dev-analyst"][0] not in text  # no sign-in name, no display name


def test_the_last_rating_of_a_session_is_the_session_rating():
    c = signed_in("dev-director")
    assert c.get("/api/feedback/status").json()["pulse"] is None
    c.post("/api/feedback/pulse", json={"rating": "bad"})
    c.post("/api/feedback/pulse", json={"rating": "good", "comment": "It got better."})
    assert c.get("/api/feedback/status").json()["pulse"]["rating"] == "good"
    c.post("/auth/dev-login", data={"username": "dev-director"})  # a new sign-in is a new session
    assert c.get("/api/feedback/status").json()["pulse"] is None


@pytest.mark.parametrize("body", [
    {"rating": "great"}, {"rating": "good", "comment": "x" * 301}, {"rating": "good", "where": "mars"},
    {"rating": "good", "ref": "has spaces"}, {"rating": "good", "extra": 1}, {}, {"rating": 3},
])
def test_pulse_refuses_bad_input(body):
    assert signed_in("dev-analyst").post("/api/feedback/pulse", json=body).status_code == 422


def test_blank_comment_is_stored_as_none(tmp_path):
    signed_in("dev-analyst").post("/api/feedback/pulse", json={"rating": "fine", "comment": "   "})
    assert stored(tmp_path, "feedback/pulse")[0]["comment"] is None


def test_a_failed_save_is_reported_not_swallowed():
    class Broken:
        def write(self, key, text):
            raise OSError("bucket unreachable")

        def read(self, key):
            return None

    c = signed_in("dev-analyst")
    with patch.object(store, "backend", return_value=Broken()):
        assert c.post("/api/feedback/pulse", json={"rating": "good"}).status_code == 503
        assert c.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"o_change": "ok"}}).status_code == 503
    assert c.get("/api/feedback/status").json()["pulse"] is None  # a rating that was not saved is not remembered


# --- the questionnaire ----------------------------------------------------------------------------

def test_questionnaire_is_served_without_its_editing_notes():
    body = signed_in("dev-forecast-manager").get("/api/feedback/questionnaire").json()
    assert body["version"] == Q["version"] and "_comment" not in body and len(feedback.items(body)) == 5


def test_the_shipped_questionnaire_is_five_optional_items_scored_by_umux_lite():
    feedback.check_questionnaire(Q)
    assert Q["version"] == 2 and [i["id"] for i in feedback.items(Q)] == ["umux_needs", "umux_easy", "t_trace", "o_nps", "o_change"]
    assert UMUX == ["umux_needs", "umux_easy"] and "sus" not in Q["scoring"]


def test_the_legacy_questionnaire_is_still_valid_and_sus_is_the_standard_ten():
    feedback.check_questionnaire(V1)
    by_id = {i["id"]: i for i in feedback.items(V1)}
    # Odd statements are worded positively, even ones negatively: the scoring below relies on that order.
    assert [bool(by_id[s].get("reverse")) for s in SUS] == [False, True] * 5


def test_check_questionnaire_rejects_a_bad_edit():
    for mutate, why in [
        (lambda q: q["sections"][0]["items"].append(dict(q["sections"][0]["items"][0])), "unique"),
        (lambda q: q["sections"][0]["items"][0].update(type="emoji"), "unknown type"),
        (lambda q: q.update(version=0), "version"),
        (lambda q: q["sections"][2]["items"][1].update(type="choice"), "options"),
        (lambda q: q["scoring"]["umux_lite"].__setitem__(0, "o_nps"), "UMUX-Lite item must be agree5"),
        (lambda q: q["scoring"]["umux_lite"].append("t_trace"), "UMUX-Lite needs two"),
        (lambda q: q["scoring"].__setitem__("sus", ["umux_needs"]), "SUS needs ten"),
    ]:
        q = deepcopy(Q)
        mutate(q)
        with pytest.raises(ValueError):
            feedback.check_questionnaire(q)


# --- SUS, by code ---------------------------------------------------------------------------------

@pytest.mark.parametrize("odd,even,expected", [(5, 1, 100.0), (3, 3, 50.0), (1, 5, 0.0), (4, 2, 75.0), (5, 5, 50.0), (2, 2, 50.0), (2, 4, 25.0)])
def test_sus_score_matches_hand_computed_values(odd, even, expected):
    assert feedback.sus_score(V1, sus_answers(odd, even)) == expected


def test_sus_needs_all_ten_statements():
    answers = sus_answers(5, 1)
    answers.pop("sus7")
    assert feedback.sus_score(V1, answers) is None


# --- UMUX-Lite, by code ---------------------------------------------------------------------------

@pytest.mark.parametrize("a,b,raw,sus_equivalent", [(5, 5, 100.0, 87.9), (1, 1, 0.0, 22.9), (3, 3, 50.0, 55.4), (5, 3, 75.0, 71.65), (4, 2, 50.0, 55.4)])
def test_umux_lite_matches_hand_computed_values(a, b, raw, sus_equivalent):
    # raw = ((a - 1) + (b - 1)) / 8 * 100; SUS-equivalent = 0.65 * raw + 22.9 (Lewis et al. 2013)
    got = feedback.umux_lite(Q, {"umux_needs": a, "umux_easy": b})
    assert got["raw"] == raw and got["sus_equivalent"] == pytest.approx(sus_equivalent)


def test_umux_lite_needs_both_items():
    assert feedback.umux_lite(Q, {"umux_needs": 5}) is None
    assert feedback.umux_lite(V1, {"umux_needs": 5, "umux_easy": 5}) is None  # a questionnaire without the item pair


# --- submitting the questionnaire -----------------------------------------------------------------

def test_survey_is_stored_scored_and_replaced_on_resubmit(tmp_path):
    c = signed_in("dev-analyst")
    answers = {"umux_needs": 5, "umux_easy": 4, "t_trace": 4, "o_nps": 9, "o_change": "  Faster agent runs. "}
    r = c.post("/api/feedback/survey", json={"version": Q["version"], "answers": answers})
    assert r.status_code == 200 and r.json()["answered"] == 5
    (doc,) = stored(tmp_path, "feedback/survey")
    assert doc["umux"]["raw"] == 87.5 and doc["umux"]["sus_equivalent"] == pytest.approx(79.775) and doc["sus"] is None and doc["updates"] == 0
    assert doc["answers"]["o_change"] == "Faster agent runs." and doc["personas"] == ["P1"] and doc["version"] == 2
    assert "dev-analyst" not in json.dumps(doc)
    c.post("/api/feedback/survey", json={"version": Q["version"], "answers": {**answers, "o_nps": 3}})
    (doc,) = stored(tmp_path, "feedback/survey")  # one document per participant
    assert doc["answers"]["o_nps"] == 3 and doc["updates"] == 1
    assert c.get("/api/feedback/status").json()["survey"] == {"submitted_at": doc["ts"], "version": Q["version"]}


def test_a_partial_survey_has_no_umux_score(tmp_path):
    signed_in("dev-director").post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 4, "t_trace": 5}})
    assert stored(tmp_path, "feedback/survey")[0]["umux"] is None


def test_participants_only_ever_see_their_own_answers():
    a, d = signed_in("dev-analyst"), signed_in("dev-director")
    a.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"o_change": "The citations."}})
    assert a.get("/api/feedback/survey").json()["answers"] == {"o_change": "The citations."}
    assert d.get("/api/feedback/survey").json() == {"version": None, "answers": {}, "submitted_at": None}


@pytest.mark.parametrize("answers", [
    {}, {"nope": 1}, {"sus1": 4}, {"umux_needs": 0}, {"umux_needs": 6}, {"umux_easy": "4"}, {"t_trace": True}, {"t_trace": 3.5},
    {"o_nps": 11}, {"o_nps": -1}, {"o_change": 5}, {"o_change": "x" * 1001},
])
def test_survey_refuses_bad_answers(answers):
    assert signed_in("dev-analyst").post("/api/feedback/survey", json={"version": Q["version"], "answers": answers}).status_code == 422


def test_survey_refuses_an_old_questionnaire_version():
    r = signed_in("dev-analyst").post("/api/feedback/survey", json={"version": Q["version"] + 1, "answers": {"umux_needs": 4}})
    assert r.status_code == 409 and "changed" in r.json()["detail"]


def test_blank_text_is_dropped():
    assert feedback.validate_answers(Q, {"o_change": "   ", "umux_needs": 4}) == {"umux_needs": 4}


def test_choices_are_checked_and_empty_ones_dropped():
    assert feedback.validate_answers(V1, {"o_used": [], "o_freq": "weekly", "sus1": 4}) == {"o_freq": "weekly", "sus1": 4}
    for bad in ({"o_freq": "daily"}, {"o_freq": ["weekly"]}, {"o_used": "briefing"}, {"o_used": ["briefing", "telepathy"]}):
        with pytest.raises(Exception):
            feedback.validate_answers(V1, bad)


# --- the report -----------------------------------------------------------------------------------

def pulse(session, ts, rating, persona="P1", comment=None, where="briefing"):
    return {"session": session, "ts": ts, "rating": rating, "personas": [persona], "comment": comment, "where": where}


def survey(persona, odd, even, nps, ts="2026-11-14T10:00:00.000+00:00", **extra):
    """A stored version 1 response (SUS)."""
    answers = {**sus_answers(odd, even), "o_nps": nps, **extra}
    return {"ts": ts, "version": 1, "personas": [persona], "answers": answers, "sus": feedback.sus_score(V1, answers)}


def survey2(persona, needs, easy, nps, ts="2026-11-14T10:00:00.000+00:00", user="u-aaaaaaaaaaaa", roles=("briefing-analyst",), **extra):
    """A stored version 2 response (UMUX-Lite)."""
    answers = {k: v for k, v in {"umux_needs": needs, "umux_easy": easy, "o_nps": nps, **extra}.items() if v is not None}
    return {"kind": "survey", "ts": ts, "version": 2, "user": user, "personas": [persona], "roles": list(roles), "answers": answers,
            "sus": None, "umux": feedback.umux_lite(Q, answers)}


def test_summary_counts_the_last_rating_of_each_session():
    pulses = [pulse("s1", "2026-11-14T09:00", "bad"), pulse("s1", "2026-11-14T09:30", "good", comment="Fixed itself."),
              pulse("s2", "2026-11-14T09:10", "fine", persona="P3"), pulse("s3", "2026-11-14T09:20", "bad", persona="P3", comment="Too slow.")]
    s = feedback.summarize(pulses, [], Q)["pulse"]
    assert s["submissions"] == 4 and s["sessions"] == 3
    assert s["by_rating"] == {"good": 1, "fine": 1, "bad": 1}
    assert s["by_role"] == {"P1": {"good": 1, "fine": 0, "bad": 0}, "P3": {"good": 0, "fine": 1, "bad": 1}}
    assert [c["comment"] for c in s["comments"]] == ["Fixed itself.", "Too slow."]


def test_summary_survey_numbers():
    surveys = [survey("P1", 5, 1, 10, x_best="Speed."), survey("P3", 3, 3, 8, o_used=["briefing"]), survey("P1", 4, 2, 5, o_used=["briefing", "agent"])]
    out = feedback.summarize([], surveys, V1)["survey"]
    assert out["responses"] == 3 and out["sus"] == {"n": 3, "mean": 75.0, "median": 75.0, "min": 50.0, "max": 100.0}
    assert out["umux"] is None and out["legacy_sus_responses"] == 3
    rows = {r["id"]: r for r in out["items"]}
    assert rows["sus1"]["mean"] == 4.0 and rows["sus1"]["counts"] == {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1}
    assert rows["sus2"]["reverse"] is True
    assert (rows["o_nps"]["promoters"], rows["o_nps"]["passives"], rows["o_nps"]["detractors"], rows["o_nps"]["nps"]) == (1, 1, 1, 0)
    assert rows["o_used"]["counts"] == {"Weekly briefing": 2, "Agent team": 1}
    assert rows["x_best"]["answers"] == [{"role": "P1", "text": "Speed."}]


def test_summary_mixes_legacy_sus_and_umux_lite():
    surveys = [survey("P1", 5, 1, 10), survey2("P3", 5, 3, 9, t_trace=4), survey2("CA", 3, 3, 6), survey2("BM", 4, None, 8)]
    out = feedback.summarize([], surveys, Q)["survey"]
    assert out["responses"] == 4 and out["versions"] == {1: 1, 2: 3} and out["legacy_sus_responses"] == 1
    assert out["sus"]["mean"] == 100.0  # the legacy response keeps its SUS
    # only the two respondents who answered both UMUX-Lite items count: raw 75 and 50
    assert out["umux"] == {"n": 2, "raw_mean": 62.5, "sus_equivalent_mean": pytest.approx(63.5, abs=0.1)}
    rows = {r["id"]: r for r in out["items"]}
    assert rows["umux_needs"]["n"] == 3 and rows["o_nps"]["n"] == 4 and rows["t_trace"]["n"] == 1


def test_markdown_reports_sus_only_when_a_legacy_response_exists():
    v2_only = feedback.to_markdown(feedback.summarize([], [survey2("P1", 4, 4, 9)], Q), Q)
    assert "UMUX-Lite:** 75.0 of 100 (SUS-equivalent 71.7" in v2_only and "System Usability Scale" not in v2_only
    mixed = feedback.to_markdown(feedback.summarize([], [survey("P1", 5, 1, 10), survey2("P1", 4, 4, 9)], Q), Q)
    assert "System Usability Scale (questionnaire version 1):** mean 100.0" in mixed and "UMUX-Lite:**" in mixed


def test_markdown_report_reads_well_and_handles_no_data():
    empty = feedback.to_markdown(feedback.summarize([], [], Q), Q)
    assert "No session ratings yet." in empty and "No questionnaire responses yet." in empty
    full = feedback.to_markdown(feedback.summarize([pulse("s1", "2026-11-14T09:00", "good", comment="Nice.")], [survey("P1", 5, 1, 10)], Q), Q)
    assert "| Good | 1 |" in full and "mean 100.0" in full and "net promoter score 100" in full and "Nice." in full


def test_report_script_reads_a_state_folder(tmp_path):
    import importlib.util

    c = signed_in("dev-analyst")
    c.post("/api/feedback/pulse", json={"rating": "fine", "comment": "OK overall"})
    c.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 4, "umux_easy": 4, "o_change": "Evidence."}})
    spec = importlib.util.spec_from_file_location("feedback_report", Path(__file__).resolve().parents[1] / "deploy" / "feedback_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out, csv_dir = tmp_path / "report.md", tmp_path / "csv"
    assert mod.main(["--state-dir", str(tmp_path), "--out", str(out), "--csv", str(csv_dir)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "OK overall" in text and "75.0 of 100" in text and "Evidence." in text
    assert (csv_dir / "pulses.csv").read_text(encoding="utf-8-sig").splitlines()[1].split(",")[3] == "fine"
    header = (csv_dir / "survey.csv").read_text(encoding="utf-8-sig").splitlines()[0].split(",")
    assert header[:5] == ["user", "ts", "version", "personas", "sus"] and "o_change" in header


def test_persona_table_follows_the_natural_order():
    pulses = [pulse("s1", "2026-11-14T09:00", "good", persona="BM"), pulse("s2", "2026-11-14T09:01", "fine", persona="P3"),
              pulse("s3", "2026-11-14T09:02", "bad", persona="CA"), pulse("s4", "2026-11-14T09:03", "good", persona="P1")]
    pulses.append({**pulse("s5", "2026-11-14T09:04", "fine"), "personas": ["P1", "CA"]})  # a mentor login holding two personas
    text = feedback.to_markdown(feedback.summarize(pulses, [], Q), Q)
    rows = [line.split("|")[1].strip() for line in text.splitlines() if line.startswith("| ") and line.split("|")[1].strip() in {"P1", "P3", "CA", "BM", "P1/CA"}]
    assert rows == ["P1", "P3", "CA", "BM", "P1/CA"]


# --- the workbook ---------------------------------------------------------------------------------

def _report_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("feedback_report", Path(__file__).resolve().parents[1] / "deploy" / "feedback_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_workbook_has_the_five_sheets_and_pseudonymous_rows(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    c, tester_client = signed_in("dev-analyst"), signed_in("dev-tester")
    c.post("/api/feedback/pulse", json={"rating": "good", "comment": "Quick."})
    c.post("/api/feedback/comment", json={"text": "Add a glossary.", "topic": "design"})
    c.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 5, "umux_easy": 4, "t_trace": 3, "o_nps": 9, "o_change": "Faster."}})
    tester_client.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 1, "umux_easy": 1, "o_change": "Test run."}})
    out = tmp_path / "out" / "class.xlsx"
    assert _report_module().main(["--state-dir", str(tmp_path), "--out", str(tmp_path / "r.md"), "--xlsx", str(out)]) == 0
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == ["Summary", "Questionnaire", "Answer votes", "Session ratings", "Comments"]
    sheet = wb["Questionnaire"]
    header = [cell.value for cell in sheet[1]]
    assert sheet.max_row == 2 and sheet.freeze_panes == "A2" and sheet["A1"].font.bold  # the tester login's response is left out
    row = dict(zip(header, [cell.value for cell in sheet[2]]))
    assert row["User (pseudonymous)"] == rbac.pseudonym("dev-analyst") and row["Role"] == "Commercial Analyst"
    assert row["What one thing would you change?"] == "Faster." and row["PharmAgentics is easy to use."] == 4
    assert row["UMUX-Lite (0-100)"] == 87.5 and row["Questionnaire version"] == 2
    summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=2)}
    assert summary["Questionnaire responses"] == 1 and summary["Net promoter score (-100 to 100)"] == 100
    assert wb["Session ratings"]["E2"].value == "good" and wb["Comments"]["E2"].value == "Add a glossary."
    everything = " ".join(str(cell.value) for ws in wb for r in ws.iter_rows() for cell in r if cell.value is not None)
    assert "dev-analyst" not in everything and auth.DEV_USERS["dev-analyst"][0] not in everything


def test_workbook_keeps_a_legacy_response_with_its_sus_score(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    out = tmp_path / "legacy.xlsx"
    doc = {**survey("P1", 5, 1, 10, x_best="Citations."), "user": "u-bbbbbbbbbbbb", "roles": ["briefing-analyst"]}
    _report_module().write_xlsx(out, Q, [], [doc, survey2("P3", 4, 4, 8)], [], [])
    wb = openpyxl.load_workbook(out)
    header = [cell.value for cell in wb["Questionnaire"][1]]
    old = dict(zip(header, [cell.value for cell in wb["Questionnaire"][2]]))
    assert old["SUS (version 1)"] == 100.0 and "x_best: Citations." in old["Answers to earlier questionnaire versions"]
    summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=2)}
    assert summary["SUS from questionnaire version 1 (mean, 0 to 100)"] == 100.0 and summary["Responses by questionnaire version"] == "v1: 1, v2: 1"


def test_workbook_stores_text_never_a_formula_and_drops_characters_excel_refuses(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    out = tmp_path / "unsafe.xlsx"
    note = {"ts": "2026-11-14T10:00:00.000+00:00", "user": "u-cccccccccccc", "roles": ["briefing-director"], "topic": "other",
            "text": '=HYPERLINK("http://example.invalid","click") pasted'}
    _report_module().write_xlsx(out, Q, [], [survey2("P1", 4, 4, 8, o_change="=1+1")], [], [note])
    wb = openpyxl.load_workbook(out)
    cell = wb["Comments"]["E2"]
    assert cell.data_type == "s" and cell.value == '=HYPERLINK("http://example.invalid","click") pasted'
    header = [c.value for c in wb["Questionnaire"][1]]
    change = wb["Questionnaire"].cell(row=2, column=header.index("What one thing would you change?") + 1)
    assert change.data_type == "s" and change.value == "=1+1"


def test_updating_from_an_older_questionnaire_keeps_the_older_answers(tmp_path):
    user = rbac.pseudonym("dev-analyst")
    old = {**survey("P1", 5, 1, 10, x_fix="The export."), "kind": "survey", "user": user, "roles": ["briefing-analyst"], "updates": 0}
    store.backend().write(feedback._survey_key(user), json.dumps(old))
    r = signed_in("dev-analyst").post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 4, "umux_easy": 4}})
    assert r.status_code == 200
    (doc,) = stored(tmp_path, "feedback/survey")
    assert doc["version"] == 2 and doc["previous"]["version"] == 1 and doc["previous"]["answers"]["x_fix"] == "The export."
    assert doc["sus"] == 100.0 and doc["umux"]["raw"] == 75.0  # the version 1 SUS still counts in the version 1 figure
    summary = feedback.summarize([], [doc], Q)
    summary["surveys"] = [doc]
    assert "x_fix: The export." in feedback.to_markdown(summary, Q)


# --- the tester admin's read-only panel -----------------------------------------------------------

def test_responses_endpoint_is_for_the_tester_admin_only():
    assert TestClient(app).get("/api/feedback/responses").status_code == 401
    for user in ALL_USERS:
        assert signed_in(user).get("/api/feedback/responses").status_code == 403


def test_responses_endpoint_returns_pseudonymous_rows_without_test_submissions(tmp_path):
    signed_in("dev-analyst").post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 4, "umux_easy": 4, "o_nps": 10, "o_change": "More weeks."}})
    signed_in("dev-director").post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 2, "o_nps": 3}})
    t = signed_in("dev-tester")
    t.post("/api/feedback/survey", json={"version": Q["version"], "answers": {"umux_needs": 1, "umux_easy": 1}})
    r = t.get("/api/feedback/responses")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["responses"] == 2 and body["questionnaire_version"] == 2
    assert body["umux"]["n"] == 1 and body["umux"]["raw_mean"] == 75.0 and body["nps"]["nps"] == 0
    assert sorted(x["role"] for x in body["rows"]) == ["Brand Director", "Commercial Analyst"]
    assert {x["user"] for x in body["rows"]} == {rbac.pseudonym("dev-analyst"), rbac.pseudonym("dev-director")}
    text = json.dumps(body)
    assert "dev-analyst" not in text and auth.DEV_USERS["dev-analyst"][0] not in text
