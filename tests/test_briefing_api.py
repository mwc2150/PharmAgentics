"""New API tests: validation, HTTP contract, evidence linkage, CORS and error paths.

These tests mock the engine only at the API boundary so they run quickly without
starting an LLM. Do not confuse these with the repo's real pipeline/eval tests.
"""
from __future__ import annotations

import sys
import types
from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api.app import app
from pharmagentics.api import service
from pharmagentics.api.schemas import BriefingQuery, ReleaseContext

CLIENT = TestClient(app)


@pytest.fixture(autouse=True)
def _signed_in_analyst(monkeypatch, tmp_path):
    """core-007: every data route needs a signed-in role. Sign in as the stand-in Commercial Analyst."""
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    CLIENT.cookies.clear()
    assert CLIENT.post("/auth/dev-login", data={"username": "dev-analyst"}, follow_redirects=False).status_code == 303


VALID = {
    "intent": "weekly_brief",
    "brand_id": "BXA",
    "territory_id": "PACIFIC",
    "week_start": "2026-06-08",
    "question": "What changed for BXA in Pacific?",
}


def sample_result():
    return {
        "status": "draft_requires_review", "review_status": "not_submitted",
        "engine": "scripted", "system": "briefing_scripted",
        "question": "Week of 2026-06-08 in Pacific: What changed?",
        "brand_id": "BXA", "territory_id": "PACIFIC",
        "week_start": "2026-06-08", "answer": "TRx is 464.",
        "claims": [{"value": "464", "evidence_id": "e1"}],
        "evidence": [{"id": "e1", "tool": "get_metric", "params": {},
                     "query": "select 464 from reporting.v_weekly_rx_kpis",
                     "result": 464, "data_version": "vtest"}],
        "data_version": "vtest", "abstained": False,
    }


def test_success_contract_and_no_store():
    with patch.object(service, "run_briefing", return_value=service.BriefingResult.model_validate(sample_result())) as runner:
        response = CLIENT.post("/api/briefing/query", json=VALID)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["claims"][0]["evidence_id"] == response.json()["evidence"][0]["id"]
    runner.assert_called_once()
    assert runner.call_args.args[0].territory_id == "PACIFIC"
    assert response.json()["view"] == "analyst" and response.json()["review_status"] == "pending"


@pytest.mark.parametrize("changes", [
    {"brand_id": "BXD"}, {"territory_id": "BROOKLYN"},
    {"intent": "arbitrary_sql"}, {"week_start": "2026-06-09"},
    {"query": "select * from raw.rx_weekly"},
    {"question": "x"},
])
def test_rejects_invalid_requests(changes):
    response = CLIENT.post("/api/briefing/query", json={**VALID, **changes})
    assert response.status_code == 422


def test_missing_database_returns_503():
    with patch.object(service, "run_briefing", side_effect=service.MissingDatabase("build DuckDB first")):
        response = CLIENT.post("/api/briefing/query", json=VALID)
    assert response.status_code == 503
    assert "DuckDB" in response.json()["detail"]


def test_out_of_release_returns_400():
    with patch.object(service, "run_briefing", side_effect=service.OutsideRelease("outside release")):
        response = CLIENT.post("/api/briefing/query", json=VALID)
    assert response.status_code == 400


def test_invalid_comparison_is_rejected_before_brief_or_worker_submission():
    context = ReleaseContext(first_week=date(2026, 6, 1), latest_week=date(2026, 6, 8),
                             territory_ids=["PACIFIC"], available_weeks=[date(2026, 6, 1), date(2026, 6, 8)])
    request = {**VALID, "comparison": {"kind": "last_year"}}
    with patch.object(service, "release_context", return_value=context):
        for url, body in (("/api/briefing/triage", request), ("/api/briefing/query", request),
                          ("/api/agent/jobs", {"kind": "triage", "query": request})):
            response = CLIENT.post(url, json=body)
            assert response.status_code == 400, response.text
            assert "outside the data release" in response.json()["detail"]


def test_leader_cannot_request_a_comparison():
    with TestClient(app) as director:
        director.post("/auth/dev-login", data={"username": "dev-director"}, follow_redirects=False)
        response = director.post("/api/briefing/query", json={**VALID, "comparison": {"kind": "previous", "weeks": 1}})
    assert response.status_code == 403


def test_multibrand_scripted_request_passes_its_brand_and_window():
    choices = [date(2026, 6, 1), date(2026, 6, 8)]
    context = ReleaseContext(first_week=choices[0], latest_week=choices[-1],
                             territory_ids=["PACIFIC"], available_weeks=choices,
                             product_ids=["BXA", "BXC"])
    request = BriefingQuery.model_validate({**VALID, "brand_id": "BXC",
                                           "comparison": {"kind": "previous", "weeks": 1}})
    package = types.ModuleType("briefing_baseline")
    package.__path__ = []
    pipeline = types.ModuleType("briefing_baseline.pipeline")

    def answer(question, db, brand_id, *, comparison):
        assert brand_id == "BXC" and comparison == request.comparison
        return {"system": "briefing_scripted", "answer": "Lipidara", "brand_id": brand_id}

    pipeline.answer = answer
    with patch.object(service, "release_context", return_value=context), patch.dict(
        sys.modules, {"briefing_baseline": package, "briefing_baseline.pipeline": pipeline}
    ):
        result = service.run_briefing(request)
        assert result.brand_id == "BXC" and result.comparison == request.comparison
        analyst = TestClient(app)
        analyst.post("/auth/dev-login", data={"username": "dev-analyst-multibrand"}, follow_redirects=False)
        response = analyst.post("/api/briefing/query",
                                json={**VALID, "brand_id": "BXC", "intent": "promotion_review"})
        assert response.status_code == 400
        assert "available for BXA" in response.json()["detail"]


def test_a_changed_window_gets_a_new_saved_brief_for_each_brand():
    from pharmagentics.api.store import brief_id

    base = sample_result()
    first = {"kind": "previous", "weeks": 1}
    second = {"kind": "previous", "weeks": 2}
    ids = {brief_id({**base, "brand_id": brand, "comparison": choice})
           for brand in ("BXA", "BXC") for choice in (None, first, second)}
    assert len(ids) == 6
    assert brief_id(base) == brief_id({**base, "comparison": None})


def test_worker_cannot_submit_a_default_result_for_an_explicit_window():
    request = BriefingQuery.model_validate({**VALID, "comparison": {"kind": "previous", "weeks": 2}})
    with pytest.raises(RuntimeError, match="different comparison window"):
        service._matching_comparison(request.comparison, {})
    service._matching_comparison(request.comparison, {"comparison": {"kind": "previous", "weeks": 2}})


def test_no_server_traceback_leaks_to_browser():
    with patch.object(service, "run_briefing", side_effect=RuntimeError("private detail")):
        response = CLIENT.post("/api/briefing/query", json=VALID)
    assert response.status_code == 500
    assert "private detail" not in response.text


def test_context_contract():
    context = ReleaseContext(first_week=date(2024, 10, 14), latest_week=date(2026, 10, 5),
                             territory_ids=["PACIFIC", "GREAT_LAKES"],
                             available_weeks=[date(2024, 10, 14), date(2026, 10, 5)])
    with patch.object(service, "release_context", return_value=context):
        response = CLIENT.get("/api/briefing/context")
    assert response.status_code == 200
    assert response.json()["latest_week"] == "2026-10-05"
    assert response.json()["available_weeks"] == ["2024-10-14", "2026-10-05"]
    assert response.json()["supported_intents"] == ["weekly_brief"]
    assert response.json()["engine"] == "scripted"


def test_question_normalization_keeps_week_and_territory_before_colon():
    request = BriefingQuery.model_validate(VALID)
    q = service.normalize_question(request)
    assert q.split(":")[0] == "Week of 2026-06-08 in Pacific"


def test_question_normalization_names_a_multi_week_period_before_the_colon():
    request = BriefingQuery.model_validate({**VALID, "week_end": "2026-06-22"})
    assert service.normalize_question(request).split(":")[0] == "Weeks of 2026-06-08 to 2026-06-22 in Pacific"
    one_week = BriefingQuery.model_validate({**VALID, "week_end": "2026-06-08"})
    assert service.normalize_question(one_week).split(":")[0] == "Week of 2026-06-08 in Pacific"


def test_the_period_must_end_on_a_monday_after_it_starts():
    assert CLIENT.post("/api/briefing/query", json={**VALID, "week_end": "2026-06-10"}).status_code == 422
    assert CLIENT.post("/api/briefing/query", json={**VALID, "week_end": "2026-06-01"}).status_code == 422


def test_a_multi_week_period_reaches_the_engine_and_the_result():
    output = {"system": "briefing_scripted", "answer": "TRx 464.", "claims": [{"value": "464", "evidence_id": "e1"}],
              "evidence": [{"id": "e1", "tool": "get_metric", "params": {}, "query": "select 1", "result": 464, "data_version": "r1"}],
              "abstained": False}
    seen = {}

    def fake_answer(question, db, brand_id, **options):
        seen.update(question=question, options=options)
        return output

    pkg = types.ModuleType("briefing_baseline")
    pkg.__path__ = []
    pipeline = types.ModuleType("briefing_baseline.pipeline")
    pipeline.answer = fake_answer
    bounds = ReleaseContext(first_week=date(2024, 10, 14), latest_week=date(2026, 10, 5), territory_ids=["PACIFIC"],
                            available_weeks=[date(2026, 5, 11), date(2026, 5, 18), date(2026, 5, 25), date(2026, 6, 1),
                                             date(2026, 6, 8), date(2026, 6, 15), date(2026, 6, 22)])
    request = BriefingQuery.model_validate({**VALID, "week_end": "2026-06-22", "comparison": {"kind": "previous", "weeks": 4}})
    with patch.object(service, "release_context", return_value=bounds), patch.dict(
        sys.modules, {"briefing_baseline": pkg, "briefing_baseline.pipeline": pipeline}
    ):
        actual = service.run_briefing(request)
    assert seen["question"].startswith("Weeks of 2026-06-08 to 2026-06-22 in Pacific:")
    assert seen["options"] == {"comparison": request.comparison}
    assert (actual.week_start, actual.week_end) == (date(2026, 6, 8), date(2026, 6, 22))
    assert actual.question == seen["question"]


def test_service_calls_existing_engine_and_preserves_evidence():
    """Tests service adapter without copying or executing pipeline implementation."""
    output = {
        "system": "briefing_scripted", "answer": "TRx 464.",
        "claims": [{"value": "464", "evidence_id": "e1"}],
        "evidence": [{"id": "e1", "tool": "get_metric", "params": {}, "query": "select ...",
                      "result": 464, "data_version": "release1"}],
        "abstained": False,
    }
    pkg = types.ModuleType("briefing_baseline")
    pkg.__path__ = []
    pipeline = types.ModuleType("briefing_baseline.pipeline")
    seen = {}

    def fake_answer(question, db, brand_id):
        seen.update(question=question, db=db, brand_id=brand_id)
        return output

    pipeline.answer = fake_answer
    bounds = ReleaseContext(first_week=date(2024, 10, 14), latest_week=date(2026, 10, 5),
                            territory_ids=["PACIFIC", "GREAT_LAKES"], available_weeks=[date(2026, 6, 8)])
    with patch.object(service, "release_context", return_value=bounds), patch.dict(
        sys.modules, {"briefing_baseline": pkg, "briefing_baseline.pipeline": pipeline}
    ):
        actual = service.run_briefing(BriefingQuery.model_validate(VALID))
    assert actual.answer == output["answer"]
    assert actual.data_version == "release1"
    assert seen["db"] == service.DB
    assert seen["brand_id"] == "BXA"
    assert seen["question"].startswith("Week of 2026-06-08 in Pacific:")


def test_service_refuses_orphan_claim():
    output = {
        "system": "briefing_scripted", "answer": "TRx 464.",
        "claims": [{"value": "464", "evidence_id": "missing"}],
        "evidence": [], "abstained": False,
    }
    pkg = types.ModuleType("briefing_baseline")
    pkg.__path__ = []
    pipeline = types.ModuleType("briefing_baseline.pipeline")
    pipeline.answer = lambda *args, **kw: output
    bounds = ReleaseContext(first_week=date(2024, 10, 14), latest_week=date(2026, 10, 5),
                            territory_ids=["PACIFIC", "GREAT_LAKES"], available_weeks=[date(2026, 6, 8)])
    with patch.object(service, "release_context", return_value=bounds), patch.dict(
        sys.modules, {"briefing_baseline": pkg, "briefing_baseline.pipeline": pipeline}
    ):
        with pytest.raises(RuntimeError, match="untraceable"):
            service.run_briefing(BriefingQuery.model_validate(VALID))


def test_cors_preflight_from_allowed_local_ui():
    response = CLIENT.options("/api/briefing/query", headers={
        "Origin": "http://localhost:5500",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5500"


def test_context_queries_release_instead_of_hardcoding_choices():
    """Choices come from the database, not from static frontend fixtures."""
    class DbStub:
        def is_file(self): return True
    class RegistryStub:
        def __init__(self, db): self.db = db
        def rows(self, sql):
            if "raw.calendar" in sql:
                return [("2026-06-01",), ("2026-06-08",)]
            if "raw.dim_territory" in sql:
                return [("PACIFIC",), ("MOUNTAIN",), ("UNSUPPORTED_TEST_ID",)]
            if "raw.dim_product" in sql:
                return [("BXA",), ("BXC",)]
            raise AssertionError(f"Unexpected SQL: {sql}")
        def close(self): pass
    tools = types.ModuleType("pharmagentics.tools")
    tools.Registry = RegistryStub
    with patch.object(service, "DB", DbStub()), patch.dict(sys.modules, {"pharmagentics.tools": tools}):
        actual = service.release_context()
    assert actual.available_weeks == [date(2026, 6, 1), date(2026, 6, 8)]
    assert actual.latest_week == date(2026, 6, 8)
    assert actual.territory_ids == ["PACIFIC", "MOUNTAIN"]
    assert actual.product_ids == ["BXA", "BXC"]
    assert actual.supported_intents == ["weekly_brief"]


def test_nonrelease_week_is_refused_before_engine_is_called():
    bounds = ReleaseContext(first_week=date(2026, 6, 1), latest_week=date(2026, 6, 15),
                            territory_ids=["PACIFIC"], available_weeks=[date(2026, 6, 1), date(2026, 6, 15)])
    with patch.object(service, "release_context", return_value=bounds):
        with pytest.raises(service.OutsideRelease):
            service.run_briefing(BriefingQuery.model_validate(VALID))


@pytest.mark.skipif(not service.DB.is_file(), reason="Build local/pharmagentics.duckdb first")
def test_the_default_comparison_runs_for_the_releases_first_week():
    """brief-008 review: the form sends no comparison, so a brief for a week with no earlier week must still run
    (the server shortens its default baseline), and the result records no explicit comparison."""
    response = CLIENT.post("/api/briefing/query", json={**VALID, "week_start": "2024-10-14", "question": "What changed?"})
    assert response.status_code == 200, response.text
    assert response.json().get("comparison") is None
