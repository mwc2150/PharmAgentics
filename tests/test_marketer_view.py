"""The Marketer (P4) view: the leadership cut plus, on each territory story, the promotion read, and once the budget note.

Real scripted briefs through the API on the local database (no model). The promotion object is an allow-list: no evidence,
no query text, no claim token, no held-level territory list, no method or threshold.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.api import service, store, views  # noqa: E402
from pharmagentics.api.app import app  # noqa: E402

from signoff_helpers import approve, sign_in  # noqa: E402

pytestmark = pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")

SUPPORTED = {"territory_id": "SOUTHEAST", "week_start": "2026-08-24", "question": "How did BXA TRx move, and why?",
             "comparison": {"kind": "custom", "start": "2026-07-06", "end": "2026-07-27"}}
NOT_TESTABLE = {"territory_id": "GREAT_LAKES", "week_start": "2025-03-03", "question": "What moved?"}
WITHIN_RANGE = {"territory_id": "SOUTHEAST", "week_start": "2026-10-05", "question": "What moved?"}
FORBIDDEN = ("{c", "evidence", "query", "sql", "held_level", "method", "threshold", "claims")
BAD_WORDS = ("roi", "return on investment", "attribution", "caused", "surveillance")


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("PHARMAGENTICS_STATE_BUCKET", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)


def made(analyst: TestClient, query: dict) -> str:
    response = analyst.post("/api/briefing/query", json={"intent": "weekly_brief", "brand_id": "BXA", **query})
    assert response.status_code == 200, response.text
    return response.json()["brief_id"]


@pytest.fixture
def briefs():
    analyst, insights = sign_in("dev-analyst"), sign_in("dev-insights")
    ids = {name: made(analyst, q) for name, q in (("supported", SUPPORTED), ("not_testable", NOT_TESTABLE), ("within_range", WITHIN_RANGE))}
    for brief_id in ids.values():
        approve(analyst, brief_id, insights)
    return ids


def story(payload: dict) -> dict:
    return next(s for s in payload["sections"] if s["number"] == "3.1")


def test_the_marketer_gets_the_promotion_read_on_each_story_and_nothing_from_the_evidence(briefs):
    marketer = sign_in("dev-marketer")
    for name, brief_id in briefs.items():
        payload = marketer.get(f"/api/briefing/{brief_id}?view=leadership").json()
        promo = story(payload)["promotion"]
        assert promo["verdict"] == {"supported": "supported", "not_testable": "not_testable", "within_range": "within_range"}[name]
        assert promo["lag_label"] and promo["recheck"]
        assert promo["new_patients"]["measure"] == "NBRx" and promo["trx"]["measure"] == "TRx"
        assert [c["channel"] for c in promo["channels"]] == ["rep calls", "digital impressions", "samples", "speaker programs"]
        for measure in (promo["new_patients"], promo["trx"], *promo["channels"]):
            assert measure["before"] and measure["after"] and measure["direction"]
        text = json.dumps(payload).lower()
        for word in FORBIDDEN + BAD_WORDS:
            if word in ("roi",):
                continue  # checked as a word below, not as a substring ("heroic")
            assert word not in text, (name, word)
        assert " roi" not in text and "roi " not in text
        assert not {"claims", "evidence", "events", "answer"} & set(payload)


def test_the_effect_is_in_the_supported_story_only_and_is_a_range_across_territories(briefs):
    marketer = sign_in("dev-marketer")
    supported = story(marketer.get(f"/api/briefing/{briefs['supported']}?view=leadership").json())["promotion"]
    assert supported["effect"]["word"] == "fewer" and supported["effect"]["territories"]
    assert set(supported["effect"]) == {"low", "high", "word", "territories", "phrase"}
    assert supported["effect"]["phrase"] == f"{supported['effect']['low']} to {supported['effect']['high']} fewer TRx a week"
    for name in ("not_testable", "within_range"):
        assert "effect" not in story(marketer.get(f"/api/briefing/{briefs[name]}?view=leadership").json())["promotion"]


def test_the_marketer_gets_the_budget_note_once_and_the_director_does_not(briefs):
    payload = sign_in("dev-marketer").get(f"/api/briefing/{briefs['supported']}?view=leadership").json()
    assert payload["budget_note"] == views.BUDGET_NOTE and json.dumps(payload).count(views.BUDGET_NOTE) == 1
    assert views.BUDGET_NOTE.startswith("Where the next dollar should go is outside this brief: it has no spend data")
    director = sign_in("dev-director").get(f"/api/briefing/{briefs['supported']}?view=leadership").json()
    assert "budget_note" not in director and not any("promotion" in s for s in director["sections"])


def test_the_directors_response_is_exactly_the_leadership_cut(briefs):
    director = sign_in("dev-director")
    for brief_id in briefs.values():
        assert director.get(f"/api/briefing/{brief_id}?view=leadership").json() == views.leadership(store.get_brief(brief_id))
        assert all("promotion" not in s for s in director.get(f"/api/briefing/{brief_id}?view=leadership").json()["sections"])


def test_the_tester_in_the_marketer_view_gets_what_the_marketer_gets(briefs):
    tester = sign_in("dev-tester")
    assert tester.post("/api/me/view-as", json={"view": "marketer"}).status_code == 200
    marketer = sign_in("dev-marketer")
    for brief_id in briefs.values():
        assert tester.get(f"/api/briefing/{brief_id}?view=leadership").json() == marketer.get(f"/api/briefing/{brief_id}?view=leadership").json()


def test_a_story_with_no_promotion_check_carries_no_promotion_object():
    record = {"result": {"answer": "x", "sections": [{"number": "3.1", "title": "t", "text": "x", "prose": "", "card": {"headline": "h", "confidence": "High", "drivers_checked": [], "cut": True}}]},
              "brief_id": "b", "review_state": "draft"}
    out = views.leader_payload(record, "P4")
    assert "promotion" not in out["sections"][0] and out["budget_note"] == views.BUDGET_NOTE
