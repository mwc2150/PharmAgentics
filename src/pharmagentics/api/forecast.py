"""Forecast-Explanation lane: the API (core-007 User Story 8; owners Alvin and Sienna).

Who may do what (the personas do not assume the Brand Manager operates the agent):

- The Commercial Analyst (CA) runs the agent, reads the full run (seven stages, report, evidence), may
  preview the leadership view, and submits a run for approval.
- The Brand Manager (BM) cannot run or submit. BM reads the leadership view (an executive summary with no evidence
  or trace) of submitted runs and approves, rejects or returns them, with a note for a rejection or a return.
- Nothing is approved by the system. A run is ``not_submitted`` until the CA submits it.

The engine and model are fixed by the server (FEAGENT_MODE, default "stub", which uses no language model); a caller
cannot choose them. Set lanes.forecast.available to true in roles.json when the UI is ready to open the Forecast
section; these routes work for the Forecast roles regardless of that flag.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool

from . import brand_access, forecast_store, rbac, service, store, views
from .schemas import ForecastAsk, ForecastFollowup, ForecastReview, ForecastRunRequest

log = logging.getLogger("pharmagentics.forecast")
router = APIRouter(prefix="/api/forecast", tags=["forecast"])

ENGINE_DIR = Path(__file__).resolve().parents[3] / "agents" / "forecast-explanation"
MODES = {"stub", "auto", "ollama"}  # stub: no language model; ollama: a local model; auto: local model, else stub
Forecast = Depends(rbac.require_forecast)


def engine_mode() -> str:
    mode = os.environ.get("FEAGENT_MODE", "stub")
    return mode if mode in MODES else "stub"


def _pipeline():
    if not ENGINE_DIR.is_dir():
        raise HTTPException(status_code=503, detail="The Forecast engine is not installed on this server.")
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    from feagent import pipeline

    return pipeline


def _write(report: dict) -> dict:
    """The writer for a verified report. Needs the engine on the path; a test replaces this function."""
    _pipeline()
    from feagent import writer

    return writer.write_report(report)


FALLBACK = {"narrative": None, "report_model": "none", "writer_status": "fallback_stub",
            "writer_attempts": [{"model": "none", "outcome": "error"}]}


def _safe_write(report: dict) -> dict:
    try:
        return _write(report)
    except Exception:  # noqa: BLE001 - whatever goes wrong with the prose, the scripted report stands
        log.exception("report writer failed")
        return dict(FALLBACK)


def _write_and_store(run_id: str, report: dict) -> None:
    """Runs after the response has been sent: the caller never waits for a model."""
    forecast_store.set_writer(run_id, _safe_write(report))


def _calls_a_model(report: dict) -> bool:
    try:
        _pipeline()
        from feagent import writer

        return writer.needs_model(report)
    except HTTPException:
        return False


def _writer_info() -> dict:
    try:
        _pipeline()
        from feagent import writer

        return writer.describe()
    except HTTPException:
        return {"enabled": False, "primary": None, "fallback": None}


# ---- the question-driven agent (fcst-001) ------------------------------------------------------------------

def _agent():
    if not (ENGINE_DIR / "forecast_agent").is_dir():
        raise HTTPException(status_code=503, detail="The Forecast agent is not installed on this server.")
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    import forecast_agent

    return forecast_agent


DEFAULT_LOCAL_MODEL = "qwen3:4b-instruct-2507-q4_K_M"
_OLLAMA_SEEN: dict = {"at": 0.0, "up": False}


def _ollama_up() -> bool:
    """Whether a local Ollama answers at OLLAMA_HOST (cached for a minute, so a request never waits on it)."""
    import time
    import urllib.request

    if time.time() - _OLLAMA_SEEN["at"] < 60:
        return _OLLAMA_SEEN["up"]
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    host = host if host.startswith("http") else "http://" + host
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=1.5) as r:
            up = r.status == 200
    except Exception:  # noqa: BLE001 - no local model server
        up = False
    _OLLAMA_SEEN.update(at=time.time(), up=up)
    return up


def question_model() -> str | None:
    """The language model for the Forecast lane (reading questions, wording, charts, follow-ups, reports), or None for
    code only. FORECAST_AGENT_MODEL wins (`rules` means none). Otherwise local Qwen 3 4B on Ollama (OLLAMA_MODEL) when
    Ollama answers: the team's one model until the designs are set. A hosted model (e.g. Haiku) is used only when
    FORECAST_AGENT_MODEL names it, so a key in the environment never switches the model by itself."""
    from pharmagentics.llm import load_env

    load_env()
    spec = os.environ.get("FORECAST_AGENT_MODEL", "").strip()
    if spec:
        return None if spec in ("rules", "none") else spec
    if _ollama_up():
        return "ollama:" + (os.environ.get("OLLAMA_MODEL") or DEFAULT_LOCAL_MODEL)
    return None


def investigator_mode() -> str:
    """Who investigates (step 6): the rules by default; FORECAST_INVESTIGATOR=model makes the model the investigator
    (the comparison arm, for trials only)."""
    return "model" if os.environ.get("FORECAST_INVESTIGATOR", "rules").strip() == "model" and question_model() else "rules"


def drill_mode() -> str:
    """Who splits an unexplained gap: the rules by default; FORECAST_DRILL=model lets the model pick the splits."""
    return "model" if os.environ.get("FORECAST_DRILL", "rules").strip() == "model" and question_model() else "rules"


def _weeks(ask: ForecastAsk) -> list[str] | None:
    if not ask.week_from:
        return None
    return _week_list(ask.week_from, ask.week_to)


def _week_list(first: date, last: date | None) -> list[str]:
    """Every Monday week from the week holding `first` to the week holding `last` (default: just the first)."""
    start = first - timedelta(days=first.weekday())
    end = last or first
    end = end - timedelta(days=end.weekday())
    if end < start:
        raise HTTPException(status_code=422, detail="The last week comes before the first.")
    out, d = [], start
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=7)
    return out


def _scope_card(ask: ForecastAsk, model: str | None) -> dict:
    """Step 1: the model reads the question when one is configured (code checks every field); else the keyword rules."""
    agent = _agent()
    first, latest = agent.context(service.DB)
    weeks = _weeks(ask)
    if weeks:
        weeks = [w for w in weeks if first <= w <= latest]
    from forecast_agent.scope import parse_scope

    if model and not weeks and not ask.territory_id:
        from forecast_agent.reader import read_scope

        scope, read_by = read_scope(ask.question, first, latest, model)
    else:
        scope, read_by = parse_scope(ask.question, first, latest, territory=ask.territory_id, weeks=weeks), "rules"
    return {**scope.card(), "read_by": read_by}


@router.post("/scope")
def scope(ask: ForecastAsk, response: Response, who=Forecast) -> dict:
    """How the agent reads a question, before anything runs: the analyst confirms or edits it."""
    _no_store(response)
    rbac.allow(who[1], "run")
    if not service.DB.is_file():
        raise HTTPException(status_code=503, detail="DuckDB has not been built. Run the data loader first.")
    model = question_model()
    return {**_scope_card(ask, model), "engine": model or "rules", "investigator": investigator_mode()}


def _result(rid: str, out: dict, model: str | None) -> dict:
    report = out.get("report") or {}
    if report.get("out_of_scope"):
        report = {**forecast_store.PLACEHOLDER, **report, "headline": report["out_of_scope"], "abstained": True,
                  "sections": [{"id": "scope", "title": "Out of scope", "text": report["out_of_scope"]}]}
    return {"run_id": rid, "lane": "forecast", "engine": model or "rules", "dataset_release": report.get("data_version"),
            "workflow_status": "Processing Complete — Pending Human Approval", "report": report,
            "answer": out["answer"], "evidence": out.get("evidence", []), "claims": out.get("claims", []),
            "trajectory": out.get("trajectory")}


def _investigate(rid: str, ask: ForecastAsk, weeks: list[str] | None, model: str | None) -> None:
    """Runs in a background thread. Steps land on the run as they happen, so the UI can show them."""
    agent = _agent()
    steps: list[dict] = []

    def on_step(step: dict) -> None:
        steps.append({k: step[k] for k in ("tool", "args")} | {"result": step["result"][:240]})
        forecast_store.update(rid, progress=list(steps))

    with forecast_store.held(rid):
        try:
            out = agent.answer(ask.question, model=model, db=service.DB, territory=ask.territory_id, weeks=weeks,
                               on_step=on_step, intent=ask.intent, investigator=investigator_mode(), drill=drill_mode())
            forecast_store.update(rid, result=_result(rid, out, model), job_status="done", progress=list(steps))
        except Exception as exc:  # noqa: BLE001 - the run records the failure; the request has already returned
            log.exception("forecast question failed")
            forecast_store.update(rid, job_status="failed", job_error=f"{type(exc).__name__}: {str(exc)[:200]}")


@router.post("/ask")
def ask(payload: ForecastAsk, response: Response, who=Forecast) -> dict:
    """Start an investigation of a question. It answers at once with a running run; poll GET /runs/{id}."""
    _no_store(response)
    p, role = who
    rbac.allow(role, "run")
    view = rbac.view_for(role, payload.view)
    if not service.DB.is_file():
        raise HTTPException(status_code=503, detail="DuckDB has not been built. Run the data loader first.")
    model = question_model()
    weeks = _weeks(payload)
    from pharmagentics.tools import Registry
    from pharmagentics.tools.registry import data_version

    reg = Registry(service.DB)
    try:
        version = data_version(reg.con)
    finally:
        reg.close()
    rid = forecast_store.question_id(payload.question + f"|{payload.intent}", payload.territory_id, weeks,
                                     f"{model or 'rules'}|{investigator_mode()}", version)
    with forecast_store.LOCK:  # two quick clicks start one investigation, not two
        existing = forecast_store.get(rid)  # a run lost to a restart reads as failed here, so it starts again
        if existing and existing.get("job_status") in ("running", "done"):
            return views.forecast_record(existing, view)
        request = {"question": payload.question, "territory_id": payload.territory_id, "weeks": weeks and [weeks[0], weeks[-1]]}
        record = forecast_store.start_question(rid, request, rbac.pseudonym(p.sub),
                                               "rules" if investigator_mode() == "rules" else f"agent ({model})")
        forecast_store.hold(rid)
    threading.Thread(target=_investigate, args=(rid, payload, weeks, model), daemon=True, name=f"forecast-{rid}").start()
    store.record_event("forecast_ask", **_who(p, role), forecast_run_id=rid, view=view, engine=model or "rules")
    return views.forecast_record(record, view)


DRIVERS_SNAPSHOT = Path(__file__).with_name("forecast_drivers.json")


@router.get("/drivers")
def drivers(response: Response, who=Forecast) -> dict:
    """Driver recovery on the draft probes, per system: the board of hits and misses (exported by `eval drivers`)."""
    _no_store(response)
    rbac.allow(who[1], "read")
    if not DRIVERS_SNAPSHOT.is_file():
        return {"labels": "draft", "systems": {}}
    import json

    return json.loads(DRIVERS_SNAPSHOT.read_text(encoding="utf-8"))


_FOLLOWUP_LOCK = forecast_store.LOCK  # follow-ups and pins change the run's document: one lock for every change
TERRITORY_IDS = {"NEW_ENGLAND", "MID_ATLANTIC", "GREAT_LAKES", "SOUTHEAST", "SOUTH_CENTRAL", "MOUNTAIN", "PACIFIC", "NORTHWEST"}


def _set_followup(rid: str, fid: str, **fields) -> None:
    def change(record: dict) -> None:
        for f in record.get("followups", []):
            if f["id"] == fid:
                f.update(fields)

    forecast_store.mutate(rid, change)


def _cut_id(value) -> str | None:
    """A territory id or NATIONAL from what a model or the rules picked (an id or a name); None if it is neither."""
    from pharmagentics.tools.queries import TERRITORY_NAMES

    text = str(value or "").strip()
    key = text.upper().replace(" ", "_").replace("-", "_")
    if key in TERRITORY_NAMES:
        return key
    return next((tid for tid, label in TERRITORY_NAMES.items() if label.lower() == text.lower()), None)


class _NoRerun(Exception):
    """A rerun scope that cannot be used; the message is the follow-up's answer."""


def _rerun_scope(plan: dict, report: dict, first: str, latest: str) -> tuple[str, list[str] | None, list[str]]:
    """Check a rerun's territory, weeks and dropped controls before anything runs. They may come from a model, and
    the engine puts them into SQL, so only known territories and Monday weeks inside the release get through."""
    scope = report.get("scope") or {}
    territory = report["territory_id"]
    if plan.get("territory"):
        territory = _cut_id(plan["territory"])
        if territory is None:
            raise _NoRerun(f"I don't know the territory {str(plan['territory'])[:40]!r}. Name one of: "
                           + ", ".join(sorted(TERRITORY_IDS)) + ", or national.")
    weeks = scope.get("weeks")
    if plan.get("weeks"):
        try:
            asked = [date.fromisoformat(str(w)) for w in plan["weeks"] if w]
        except ValueError:
            raise _NoRerun("Give the weeks as dates, for example 2026-08-24.") from None
        if not asked:
            raise _NoRerun("Give the weeks as dates, for example 2026-08-24.")
        if asked[-1] < asked[0]:
            raise _NoRerun("The last week comes before the first.")
        weeks = [w for w in _week_list(asked[0], asked[-1]) if first <= w <= latest]
        if not weeks:
            raise _NoRerun(f"That period is outside the release, which runs from {first} to {latest}.")
    drop = sorted({t for t in (_cut_id(x) for x in plan.get("drop_controls") or []) if t in TERRITORY_IDS})
    return territory, weeks, drop


def _run_followup(rid: str, fid: str, question: str, model: str | None, by: str) -> None:
    """Runs in a background thread: route the follow-up to one operation and run it in code."""
    with forecast_store.held(f"{rid}/{fid}"):
        _follow_up(rid, fid, question, model, by)


def _follow_up(rid: str, fid: str, question: str, model: str | None, by: str) -> None:
    agent = _agent()
    from forecast_agent import followup

    try:
        parent = forecast_store.get(rid)
        report = parent["result"]["report"]
        first, latest = agent.context(service.DB)
        plan = (followup.route_with_model(question, report, model) if model else None) or \
            followup.route(question, report, first, latest)
        op = plan["op"]
        if op == "rerun":
            try:
                territory, weeks, drop = _rerun_scope(plan, report, first, latest)
            except _NoRerun as why:
                _set_followup(rid, fid, status="done", op="help", answer=str(why))
                return
            out = agent.answer(report["question"], model=model, db=service.DB, territory=territory, weeks=weeks,
                               drop_controls=drop, intent=report.get("intent"), investigator=investigator_mode(), drill=drill_mode())
            child_q = report["question"] + f" [follow-up: {question}]"
            cid = forecast_store.question_id(child_q, territory, weeks, model or "rules", "followup")
            forecast_store.start_question(cid, {"question": child_q, "territory_id": territory,
                                                "weeks": weeks and [weeks[0], weeks[-1]], "parent": rid}, by, model or "rules")
            forecast_store.update(cid, result=_result(cid, out, model), job_status="done")
            child = out.get("report") or {}
            text = child.get("summary") or child.get("headline") or out["answer"].split("\n")[0]
            _set_followup(rid, fid, status="done", op="rerun", answer=text, child_run_id=cid)
        elif op == "drill":
            terr = _cut_id(plan.get("territory"))
            out = followup.drill(report, terr if terr in TERRITORY_IDS else None,
                                 model if drill_mode() == "model" else None, db=service.DB)
            _set_followup(rid, fid, status="done", op="drill", answer=out["answer"], chart=out.get("chart"),
                          splits=out.get("splits"), territory=out.get("territory"))
        elif op == "chart":
            kind = plan.get("kind")
            spec = (report.get("charts") or {}).get(kind) if kind else None
            if spec:
                _set_followup(rid, fid, status="done", op="chart", answer=f"Chart: {spec['title']}.", chart={"id": kind, **spec})
            else:
                offered = ", ".join(report.get("charts") or {}) or "none"
                _set_followup(rid, fid, status="done", op="help",
                              answer=f"That chart is not available for this answer. Charts it offers: {offered}.")
        elif op == "explain":
            _set_followup(rid, fid, status="done", op="explain", answer=followup.explain(plan.get("topic") or question, report))
        elif op == "weekly":
            out = followup.weekly(report, db=service.DB)
            _set_followup(rid, fid, status="done", op="weekly", answer=out["answer"], evidence=len(out["evidence"]),
                          table=out["table"])
        else:
            _set_followup(rid, fid, status="done", op="help", answer=followup.HELP)
    except Exception as exc:  # noqa: BLE001 - recorded on the follow-up; the request has already returned
        log.exception("forecast follow-up failed")
        _set_followup(rid, fid, status="failed", answer=f"The follow-up failed: {type(exc).__name__}.")


PINNABLE = {"rerun", "weekly", "explain", "chart", "drill"}


@router.post("/runs/{run_id}/pins/{followup_id}")
def pin_followup(run_id: str, followup_id: str, response: Response, who=Forecast) -> dict:
    """Pin a follow-up for the run's report (the investigation itself is always included)."""
    _no_store(response)
    _p, role = who
    rbac.allow(role, "run")
    with _FOLLOWUP_LOCK:
        record = _record(run_id)
        f = next((x for x in record.get("followups", []) if x["id"] == followup_id), None)
        if f is None or f["status"] != "done" or f.get("op") not in PINNABLE:
            raise HTTPException(status_code=409, detail="Only a finished follow-up with content can be pinned.")
        pins = record.get("pins", [])
        if followup_id not in pins:
            pins.append(followup_id)
        record = forecast_store.update(run_id, pins=pins)
    return views.forecast_record(record, rbac.view_for(role, "analyst"))


@router.delete("/runs/{run_id}/pins/{followup_id}")
def unpin_followup(run_id: str, followup_id: str, response: Response, who=Forecast) -> dict:
    _no_store(response)
    _p, role = who
    rbac.allow(role, "run")
    with _FOLLOWUP_LOCK:
        record = _record(run_id)
        record = forecast_store.update(run_id, pins=[x for x in record.get("pins", []) if x != followup_id])
    return views.forecast_record(record, rbac.view_for(role, "analyst"))


@router.post("/runs/{run_id}/followups")
def ask_followup(run_id: str, payload: ForecastFollowup, response: Response, who=Forecast) -> dict:
    """A follow-up on a finished question run (analyst only). It answers at once; poll GET /runs/{id}."""
    _no_store(response)
    p, role = who
    rbac.allow(role, "run")
    record = _record(run_id)
    if record.get("kind") != "question" or record.get("job_status") != "done":
        raise HTTPException(status_code=409, detail="Follow-ups need a finished question run.")
    model = question_model()
    with _FOLLOWUP_LOCK:
        record = forecast_store.get(run_id)
        followups = record.get("followups", [])
        if len(followups) >= 20:
            raise HTTPException(status_code=409, detail="This run already has twenty follow-ups; ask a new question.")
        fid = f"q{len(followups) + 1}"
        followups.append({"id": fid, "question": " ".join(payload.question.split()), "status": "running", "op": None,
                          "answer": None, "child_run_id": None, "started_at": forecast_store.now()})
        record = forecast_store.update(run_id, followups=followups)
        forecast_store.hold(f"{run_id}/{fid}")
    threading.Thread(target=_run_followup, args=(run_id, fid, payload.question, model, rbac.pseudonym(p.sub)),
                     daemon=True, name=f"forecast-followup-{run_id}-{fid}").start()
    store.record_event("forecast_followup", **_who(p, role), forecast_run_id=run_id, engine=model or "rules")
    return views.forecast_record(record, rbac.view_for(role, "analyst"))


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/status")
def status(response: Response, p: rbac.Principal = Depends(rbac.require_user)) -> dict:
    _no_store(response)
    brand_access.require_brand(p, "BXA")
    role = p.role("forecast")
    return {
        "lane": "forecast", "available": rbac.lane_available("forecast"), "engine": engine_mode(),
        "question_engine": question_model() or "rules", "investigator": investigator_mode(),
        "role": role.name if role else None, "persona": role.persona if role else None,
        "label": role.label if role else None, "views": list(role.views) if role else [], "writer": _writer_info(),
        "actions": list(role.actions) if role else [],
        "planned": {
            "analyst": "Forecast against actual by territory and week, the drivers of the gap with evidence, "
                       "and what to revise (Commercial Analyst, CA).",
            "leadership": "An executive summary of the forecast gap and dynamic projections, with no evidence "
                          "or trace (Brand Manager, BM).",
        },
    }


@router.get("/cases")
def cases(response: Response, who=Forecast) -> dict:
    """The three ready-made cards: the request body to POST to /api/forecast/runs for each."""
    _no_store(response)
    rbac.allow(who[1], "run")
    out = []
    for case in _pipeline().FORECAST_LANE_CASES:
        req = case["request"]
        out.append({
            "case_id": case["case_id"], "tag": case["tag"], "label": case["label"],
            "request": {"territory_id": req["territory_id"], "week_start": req["week_start"],
                        "window_weeks": req.get("window_weeks", 1)},
        })
    return {"lane": "forecast", "cases": out}


@router.get("/context")
async def context(response: Response, who=Forecast) -> dict:
    """The governed scope choices for a manual Forecast run."""
    _no_store(response)
    rbac.allow(who[1], "run")
    try:
        release = await run_in_threadpool(service.release_context)
    except service.MissingDatabase as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    # The Briefing release lists the eight territories; Forecast also runs the national total, first.
    return {"territory_ids": ["NATIONAL", *release.territory_ids], "available_weeks": [d.isoformat() for d in release.available_weeks],
            "latest_week": release.latest_week.isoformat(), "metric": "TRx", "brand": "BXA Cardiovela"}


def _who(p: rbac.Principal, role: rbac.Role) -> dict:
    return {"user": rbac.pseudonym(p.sub), "role": role.name, "persona": role.persona, **p.tag()}


def _record(run_id: str) -> dict:
    record = forecast_store.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such Forecast run.")
    return record


def _visible(role: rbac.Role, record: dict) -> bool:
    """The CA sees every run. A reader without the run action sees only what has been submitted."""
    return "run" in role.actions or record["review_status"] != forecast_store.NOT_SUBMITTED


@router.post("/runs")
async def run(payload: ForecastRunRequest, response: Response, background: BackgroundTasks, who=Forecast) -> dict:
    _no_store(response)
    p, role = who
    rbac.allow(role, "run")
    view = rbac.view_for(role, payload.view)
    pipeline = _pipeline()
    request = {"territory_id": payload.territory_id, "week_start": payload.week_start.isoformat(),
               "window_weeks": payload.window_weeks}
    body = {
        "request_id": f"fcst_{payload.territory_id}_{payload.week_start.isoformat()}_{payload.window_weeks}w",
        "source": "manual", "brand": "BXA Cardiovela", "metric": "TRx", **request,
    }
    try:
        result = await run_in_threadpool(pipeline.run_forecast_pipeline, body, engine_mode())
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        log.exception("forecast run failed")
        raise HTTPException(status_code=500, detail="The Forecast run failed.") from None
    # After stage 6: prose for the verified report. It never changes the numbers or fails the run, and when a
    # model is needed it is written after this response, so the run comes back at once (writer_status "pending").
    writer, later = None, False
    if forecast_store.needs_writer(request, result):
        later = _calls_a_model(result["report"])
        writer = forecast_store.pending_writer() if later else _safe_write(result["report"])
    record = forecast_store.save(request, result, by=rbac.pseudonym(p.sub), writer=writer)
    if later:
        background.add_task(_write_and_store, record["run_id"], result["report"])
    store.record_event("forecast_run", **_who(p, role), forecast_run_id=record["run_id"], view=view)
    return views.forecast_record(record, view)


@router.get("/runs")
def list_runs(response: Response, status: str | None = None, who=Forecast) -> dict:
    _no_store(response)
    _p, role = who
    rbac.allow(role, "read")
    rows = [views.forecast_summary(r) for r in forecast_store.all_runs() if _visible(role, r)]
    if status:
        rows = [r for r in rows if r["review_status"] == status]
    return {"lane": "forecast", "runs": rows}


@router.get("/runs/{run_id}")
def open_run(run_id: str, response: Response, view: str | None = None, who=Forecast) -> dict:
    _no_store(response)
    p, role = who
    rbac.allow(role, "read")
    record = _record(run_id)
    if not _visible(role, record):
        raise HTTPException(status_code=404, detail="No such Forecast run.")
    chosen = rbac.view_for(role, view)
    store.record_event("forecast_opened", **_who(p, role), forecast_run_id=run_id, view=chosen)
    return views.forecast_record(record, chosen)


@router.post("/runs/{run_id}/submit")
def submit(run_id: str, response: Response, who=Forecast) -> dict:
    """The CA sends a run to the Brand Manager for approval."""
    _no_store(response)
    p, role = who
    rbac.allow(role, "run")
    if _record(run_id).get("kind") == "question":
        raise HTTPException(status_code=409, detail="A question is submitted through its report: create the report and submit that.")
    try:
        record = forecast_store.submit(run_id, rbac.pseudonym(p.sub), role.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.record_event("forecast_submitted", **_who(p, role), forecast_run_id=run_id)
    return views.forecast_record(record, rbac.view_for(role, None))


@router.post("/runs/{run_id}/review")
def review(run_id: str, decision: ForecastReview, response: Response, who=Forecast) -> dict:
    """The Brand Manager approves, rejects or returns a submitted run."""
    _no_store(response)
    p, role = who
    rbac.allow(role, "review")
    _record(run_id)
    if decision.decision in ("rejected", "returned") and not decision.note:
        word = "rejection" if decision.decision == "rejected" else "return"
        raise HTTPException(status_code=422, detail=f"A {word} needs a note.")
    try:
        record = forecast_store.review(run_id, decision.decision, decision.note, rbac.pseudonym(p.sub), role.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.record_event("forecast_reviewed", **_who(p, role), forecast_run_id=run_id, decision=decision.decision, note=decision.note)
    return views.forecast_record(record, rbac.view_for(role, None))


# Reports: pinned findings drafted into one reviewed report (fcst-002).
from . import forecast_reports  # noqa: E402

forecast_reports.routes(Forecast)
router.include_router(forecast_reports.router)
