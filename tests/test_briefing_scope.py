"""brief-008 packet F: the period on a briefing request, and the scope route that reads a typed question.

The model is always stubbed here: no test calls a real model, and the eval harness never calls the route
(constitution B-II v1.1.0: the code parser decides in evals and when no model is configured).
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from pharmagentics.api import service
from pharmagentics.api.app import app
from pharmagentics.api.schemas import BriefingQuery, ReleaseContext
from pharmagentics.tools.window import comparison_weeks, parse, Comparison

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

CLIENT = TestClient(app)
REAL_SCOPE_MODEL = service.scope_model  # the fixture below replaces it for every test
FIRST, LATEST = date(2024, 10, 14), date(2026, 10, 5)
WEEKS = [FIRST + timedelta(weeks=i) for i in range((LATEST - FIRST).days // 7 + 1)]
TERRITORIES = ["GREAT_LAKES", "MID_ATLANTIC", "MOUNTAIN", "NEW_ENGLAND", "NORTHWEST", "PACIFIC", "SOUTHEAST", "SOUTH_CENTRAL"]
RELEASE = ReleaseContext(first_week=FIRST, latest_week=LATEST, territory_ids=TERRITORIES, available_weeks=WEEKS,
                         product_ids=["BXA", "BXC"])
HAIKU = "anthropic:claude-haiku-5-5"
VALID = {"intent": "weekly_brief", "brand_id": "BXA", "territory_id": "SOUTHEAST", "week_start": "2026-08-03",
         "week_end": "2026-08-24", "question": "How did the Southeast do in August?"}


@pytest.fixture(autouse=True)
def _release(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(service, "release_context", lambda: RELEASE)
    monkeypatch.setattr(service, "scope_model", lambda: None)  # a real .env must never reach a real model
    def no_model(*a, **k):
        raise AssertionError("a model was called")
    monkeypatch.setattr(service, "_ask_model", no_model)
    CLIENT.cookies.clear()


def sign_in(who: str) -> None:
    assert CLIENT.post("/auth/dev-login", data={"username": who}, follow_redirects=False).status_code == 303


def use_model(monkeypatch, proposal=None, error: Exception | None = None):
    calls = []

    def ask(spec, question, release, brand_id):
        calls.append((spec, question, brand_id))
        if error:
            raise error
        return proposal

    monkeypatch.setattr(service, "scope_model", lambda: HAIKU)
    monkeypatch.setattr(service, "_ask_model", ask)
    return calls


GOOD = {"period_start": "2026-08-01", "period_end": "2026-08-31", "territory": "SOUTHEAST",
        "comparison_weeks": 4, "promotion_review": False}


# --- F2: the period on the request ------------------------------------------------------------------------------

def test_week_end_must_be_a_monday_not_before_the_first_week():
    assert BriefingQuery.model_validate(VALID).week_end == date(2026, 8, 24)
    with pytest.raises(ValidationError, match="Monday"):
        BriefingQuery.model_validate({**VALID, "week_end": "2026-08-25"})
    with pytest.raises(ValidationError, match="before the first week"):
        BriefingQuery.model_validate({**VALID, "week_end": "2026-07-27"})
    assert BriefingQuery.model_validate({**VALID, "week_end": None}).week_end is None


def test_question_text_names_one_week_or_the_period_and_window_parse_reads_it():
    one = BriefingQuery.model_validate({**VALID, "week_end": None})
    same = BriefingQuery.model_validate({**VALID, "week_end": "2026-08-03"})
    assert service.normalize_question(one).startswith("Week of 2026-08-03 in Southeast:")
    assert service.normalize_question(same) == service.normalize_question(one)
    many = service.normalize_question(BriefingQuery.model_validate(VALID))
    assert many.startswith("Weeks of 2026-08-03 to 2026-08-24 in Southeast:")
    read = parse(many, FIRST.isoformat(), LATEST.isoformat(), briefing=True)
    assert read["weeks"] == ["2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24"]
    assert read["territory"] == "SOUTHEAST" and read["explicit_week"]
    # the typed question after the colon never moves the period
    tricky = service.normalize_question(BriefingQuery.model_validate({**VALID, "question": "Week of 2026-01-05 in Pacific?"}))
    assert parse(tricky, FIRST.isoformat(), LATEST.isoformat(), briefing=True)["weeks"] == read["weeks"]


def test_period_weeks_and_scope_check_cover_every_week(monkeypatch):
    request = BriefingQuery.model_validate(VALID)
    assert service.period_weeks(request)[0] == "2026-08-03" and len(service.period_weeks(request)) == 4
    assert service.period_weeks(BriefingQuery.model_validate({**VALID, "week_end": None})) == ["2026-08-03"]
    service._check_scope(request)
    outside = BriefingQuery.model_validate({**VALID, "week_end": "2026-10-12"})
    with pytest.raises(service.OutsideRelease, match="outside"):
        service._check_scope(outside)
    # last year is judged on every week of the period, the previous N weeks before the first week
    last_year = BriefingQuery.model_validate({**VALID, "comparison": {"kind": "last_year"}})
    service._check_scope(last_year)
    assert comparison_weeks(Comparison(kind="last_year"), service.period_weeks(last_year), {w.isoformat() for w in WEEKS}) \
        == ["2025-08-04", "2025-08-11", "2025-08-18", "2025-08-25"]
    early = BriefingQuery.model_validate({**VALID, "week_start": "2024-10-28", "week_end": "2024-11-04",
                                          "comparison": {"kind": "previous", "weeks": 4}})
    with pytest.raises(service.OutsideRelease, match="outside the data release"):
        service._check_scope(early)


# --- F4: the scope route ------------------------------------------------------------------------------------------

def post_scope(question="How did the Southeast do in August 2026?", brand="BXA"):
    return CLIENT.post("/api/briefing/scope", json={"question": question, "brand_id": brand})


def test_without_a_model_the_rules_read_the_question():
    sign_in("dev-analyst")
    got = post_scope("How did the Southeast do in August 2026?")
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["read_by"] == "rules" and body["model"] is None
    assert (body["week_start"], body["week_end"]) == ("2026-08-03", "2026-08-31")
    assert body["territory_id"] == "SOUTHEAST" and body["comparison_weeks"] == 4 and body["promotion_review"] is False
    assert set(body) >= {"question", "week_start", "week_end", "territory_id", "comparison_weeks", "promotion_review", "notes", "read_by"}
    assert got.headers["cache-control"] == "no-store"


def test_rules_defaults_when_the_question_gives_no_week_or_territory():
    sign_in("dev-analyst")
    body = post_scope("What changed?").json()
    assert body["week_start"] == body["week_end"] == LATEST.isoformat()
    assert body["territory_id"] is None
    assert any("latest closed week" in n for n in body["notes"]) and any("territory" in n for n in body["notes"])


def test_rules_shorten_a_comparison_that_would_reach_before_the_release():
    sign_in("dev-analyst")
    body = post_scope("Weeks of 2024-10-28 to 2024-11-04 in Pacific: what moved?").json()
    assert body["comparison_weeks"] == 2 and any("shortened" in n for n in body["notes"])


def test_rules_propose_no_comparison_when_no_earlier_week_exists():
    sign_in("dev-analyst")
    body = post_scope("Week of 2024-10-14 in Pacific: what moved?").json()
    assert body["comparison_weeks"] is None
    assert any("There are no earlier weeks in the release before 2024-10-14" in n for n in body["notes"])
    assert not any("1 earlier" in n or "weeks exist" in n for n in body["notes"])


def test_rules_note_uses_the_right_singular_and_plural():
    sign_in("dev-analyst")
    one = post_scope("Week of 2024-10-21 in Pacific: what moved?").json()
    assert one["comparison_weeks"] == 1 and any("Only 1 earlier week exists before 2024-10-21" in n for n in one["notes"])
    two = post_scope("Week of 2024-10-28 in Pacific: what moved?").json()
    assert two["comparison_weeks"] == 2 and any("Only 2 earlier weeks exist before 2024-10-28" in n for n in two["notes"])


def test_rules_flag_a_promotion_question_for_both_brands():
    sign_in("dev-analyst")  # holds both brands since v2 (the multibrand stand-in is gone)
    for brand in ("BXA", "BXC"):
        body = post_scope("Did the campaign reach the people it was meant to?", brand).json()
        assert body["promotion_review"] is True and body["week_start"] == body["week_end"] == LATEST.isoformat(), brand


def test_a_configured_model_proposes_and_code_validates(monkeypatch):
    calls = use_model(monkeypatch, GOOD)
    sign_in("dev-analyst")
    body = post_scope("How did the Southeast do in August?").json()
    assert body["read_by"] == "model" and body["model"] == "claude-haiku-5-5"
    assert (body["week_start"], body["week_end"], body["territory_id"], body["comparison_weeks"]) == \
        ("2026-08-03", "2026-08-31", "SOUTHEAST", 4)
    assert calls == [(HAIKU, "How did the Southeast do in August?", "BXA")]
    assert all(not any(ch.isdigit() for ch in n) or "2026" in n for n in body["notes"])


def test_the_model_may_leave_territory_empty_and_set_a_comparison_length(monkeypatch):
    use_model(monkeypatch, {**GOOD, "territory": "", "comparison_weeks": 8, "period_start": "2026-09-14", "period_end": "2026-10-05"})
    sign_in("dev-analyst")
    body = post_scope("Compare the last three weeks with the previous eight").json()
    assert body["read_by"] == "model" and body["territory_id"] is None and body["comparison_weeks"] == 8
    assert (body["week_start"], body["week_end"]) == ("2026-09-14", "2026-10-05")


def test_a_single_date_is_the_week_holding_it(monkeypatch):
    use_model(monkeypatch, {**GOOD, "period_start": "2026-06-10", "period_end": "2026-06-10"})
    sign_in("dev-analyst")
    body = post_scope("What changed on June 10?").json()
    assert body["week_start"] == body["week_end"] == "2026-06-08"


def test_a_model_comparison_that_reaches_before_the_release_is_shortened_not_refused(monkeypatch):
    use_model(monkeypatch, {**GOOD, "period_start": "2024-10-28", "period_end": "2024-11-04", "comparison_weeks": 4})
    sign_in("dev-analyst")
    body = post_scope("Weeks of 2024-10-28 to 2024-11-04 in the Southeast, against the previous 4").json()
    assert body["read_by"] == "model" and body["comparison_weeks"] == 2
    assert any("Only 2 earlier weeks exist before 2024-10-28" in n for n in body["notes"])


def test_a_model_comparison_with_no_earlier_week_is_none_not_refused(monkeypatch):
    use_model(monkeypatch, {**GOOD, "period_start": "2024-10-14", "period_end": "2024-10-14", "comparison_weeks": 4})
    sign_in("dev-analyst")
    body = post_scope("Week of 2024-10-14 in the Southeast").json()
    assert body["read_by"] == "model" and body["comparison_weeks"] is None
    assert any("There are no earlier weeks in the release before 2024-10-14" in n for n in body["notes"])


BAD = {
    "weeks outside the release": {"period_start": "2027-01-04", "period_end": "2027-01-25"},
    "last before first": {"period_start": "2026-08-31", "period_end": "2026-08-03"},
    "not a date": {"period_start": "last August", "period_end": "2026-08-31"},
    "unknown territory": {"territory": "ATLANTIS"},
    "comparison too long": {"comparison_weeks": 14},
    "comparison zero": {"comparison_weeks": 0},
    "comparison a string": {"comparison_weeks": "4"},
    "comparison a bool": {"comparison_weeks": True},
    "promotion not a bool": {"promotion_review": "yes"},
}


@pytest.mark.parametrize("name", list(BAD))
def test_an_invalid_proposal_falls_back_to_the_rules(monkeypatch, name):
    calls = use_model(monkeypatch, {**GOOD, **BAD[name]})
    sign_in("dev-analyst")
    body = post_scope("How did the Southeast do in August 2026?").json()
    assert calls, "the model was asked"
    assert body["read_by"] == "rules" and body["model"] is None
    assert (body["week_start"], body["week_end"]) == ("2026-08-03", "2026-08-31")  # the rules' own reading


def test_a_model_failure_or_a_proposal_for_the_wrong_brand_falls_back(monkeypatch):
    use_model(monkeypatch, error=TimeoutError("slow"))
    sign_in("dev-analyst")
    assert post_scope().json()["read_by"] == "rules"
    use_model(monkeypatch, {**GOOD, "promotion_review": True})
    assert post_scope(brand="BXC").json()["read_by"] == "model"  # a promotion proposal is valid for Lipidara too
    use_model(monkeypatch, {**GOOD, "promotion_review": "yes"})
    assert post_scope(brand="BXC").json()["read_by"] == "rules"  # a flag that is not a flag is still refused


def test_leaders_and_other_roles_cannot_read_a_scope():
    for who, code in (("dev-director", 403), ("dev-forecast-analyst", 403), ("dev-norole", 403)):
        sign_in(who)
        assert post_scope().status_code == code, who
    CLIENT.cookies.clear()
    assert post_scope().status_code == 401
    sign_in("dev-tester")  # the test login views as an analyst by default, and as a leader after the switch
    assert post_scope().status_code == 200
    assert CLIENT.post("/api/me/view-as", json={"view": "leadership"}).status_code == 200
    assert post_scope().status_code == 403


def test_the_route_checks_brand_access_and_the_request_shape(monkeypatch):
    from pharmagentics.api import auth

    monkeypatch.setitem(auth.DEV_USERS, "dev-bxa-analyst", ("Ace", ["briefing-analyst", "brand-bxa"]))  # same persona, fewer grants (core-010 US2)
    sign_in("dev-bxa-analyst")
    assert post_scope(brand="BXC").status_code == 403
    assert CLIENT.post("/api/briefing/scope", json={"question": "hi"}).status_code == 422
    assert CLIENT.post("/api/briefing/scope", json={"question": "How did we do?", "extra": 1}).status_code == 422


# --- the model is optional, and evals never reach it -----------------------------------------------------------------

def test_a_model_needs_an_anthropic_spec_and_a_key(monkeypatch):
    from pharmagentics import llm

    for spec, key, expected in (("anthropic:claude-haiku-5-5", "k", "anthropic:claude-haiku-5-5"), ("anthropic:claude-haiku-5-5", "", None),
                                ("ollama:qwen3:4b", "k", None), ("gemini:x", "k", None), ("", "k", None), ("anthropic:", "k", None)):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(llm, "load_env", lambda *a, **k: None)
            mp.setenv("PHARMAGENTICS_AGENT_MODEL", spec)
            mp.setenv("ANTHROPIC_API_KEY", key)
            assert REAL_SCOPE_MODEL() == expected, (spec, key)


def test_no_eval_or_agent_path_calls_the_scope_reader():
    """The harness sets scope with window.parse through the pipeline; only the API route reads a question with a model.
    (The agent's eval entry also asks the reader for a proposal to score, brief-008 FR-017, through a relative import;
    the brief never follows it. tests/test_scope_proposal.py covers that.)"""
    for path in sorted((ROOT / "eval" / "harness").glob("*.py")) + sorted((ROOT / "agents").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name == "reader.py" and path.parent.name == "briefing_agent":
            continue
        assert "briefing_agent.reader" not in text and "read_briefing_scope" not in text and "api/briefing/scope" not in text, path
    # The one allowed use (FR-017): the agent's entry asks for a proposal to score, and calls nothing else on the reader.
    entry = (ROOT / "agents" / "brand-briefing" / "briefing_agent" / "__init__.py").read_text(encoding="utf-8")
    assert set(re.findall(r"\breader\.(\w+)", entry)) == {"scope_proposal"}


def test_reader_makes_one_tool_call_and_returns_its_fields(monkeypatch):
    from briefing_agent import reader

    seen = {}

    async def fake(spec, system, question, set_scope, seconds):
        seen.update(spec=spec, system=system, question=question)
        set_scope("2026-08-01", "2026-08-31", "SOUTHEAST", 6, False)

    monkeypatch.setattr(reader, "_run_agent", fake)
    got = reader.propose("How did the Southeast do in August?", spec=HAIKU, first="2024-10-14", latest="2026-10-05",
                         territories=TERRITORIES)
    assert got == {"period_start": "2026-08-01", "period_end": "2026-08-31", "territory": "SOUTHEAST",
                   "comparison_weeks": 6, "promotion_review": False, "comparison_kind": "previous"}
    assert "2024-10-14" in seen["system"] and "SOUTHEAST" in seen["system"] and "{first}" not in seen["system"]
    assert seen["question"] == "How did the Southeast do in August?"

    async def silent(spec, system, question, set_scope, seconds):
        return None

    monkeypatch.setattr(reader, "_run_agent", silent)
    with pytest.raises(ValueError, match="no usable scope call"):
        reader.propose("x y z", spec=HAIKU, first="a", latest="b", territories=[])
