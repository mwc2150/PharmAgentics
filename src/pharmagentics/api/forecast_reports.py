"""Forecast reports (fcst-002). A report starts from a finished question run. Its contents are that run's pins: the
investigation itself, always, and the follow-ups the analyst pinned on the run page (more runs may be added). The
report is drafted from all pinned content and redrafted when the pins change; the model revises it on instruction
(code checks every version, and every pinned item must appear); the Brand Manager reviews a submitted version.

Stored as JSON documents under forecast_reports/ on the app's store, like the runs. Each version keeps a copy of
the findings it used, so an old version always renders the same. The working thread (runs, follow-ups) is never
part of what a leader sees; only the submitted report is (the Briefing lane's ADR 0002 makes the same split).
"""
from __future__ import annotations

import json
import logging
import re
import threading
import uuid

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from . import forecast_store, rbac, store
from .store import _dump, backend, now

log = logging.getLogger("pharmagentics.forecast.reports")
router = APIRouter(prefix="/reports")
_LOCK = threading.RLock()
ID = re.compile(r"^r-[0-9a-f]{12}$")
EDITABLE = {forecast_store.NOT_SUBMITTED, forecast_store.RETURNED}


class NewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    title: str | None = Field(default=None, max_length=120)


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str | None = Field(default=None, max_length=500)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approved|rejected|returned)$")
    note: str | None = Field(default=None, max_length=500)


# ---- store ------------------------------------------------------------------------------------------------------

def _key(rid: str) -> str:
    if not ID.match(rid):
        raise KeyError(rid)
    return f"forecast_reports/{rid}.json"


def get(rid: str) -> dict | None:
    try:
        text = backend().read(_key(rid))
    except KeyError:
        return None
    return json.loads(text) if text else None


def put(record: dict) -> dict:
    backend().write(_key(record["id"]), _dump(record))
    return record


def all_reports() -> list[dict]:
    out = []
    for key in backend().keys("forecast_reports/"):
        text = backend().read(key)
        if text:
            out.append(json.loads(text))
    return sorted(out, key=lambda r: r["created_at"], reverse=True)


# ---- helpers ----------------------------------------------------------------------------------------------------

def _engine():
    from .forecast import _agent

    _agent()
    from forecast_agent import report as engine

    return engine


def _model() -> str | None:
    from .forecast import question_model

    return question_model()


def _record(rid: str) -> dict:
    r = get(rid)
    if r is None:
        raise HTTPException(status_code=404, detail="No such report.")
    return r


def _editable(r: dict) -> None:
    if r["review_status"] not in EDITABLE:
        raise HTTPException(status_code=409, detail=f"A report that is {r['review_status']} cannot be changed.")
    if r["job"]["status"] == "drafting":
        raise HTTPException(status_code=409, detail="The report is being drafted; wait for it to finish.")


def _finding(fid: str, run_id: str, followup_id: str | None) -> dict:
    engine = _engine()
    run = forecast_store.get(run_id)
    if run is None or run.get("kind") != "question" or run.get("job_status") != "done":
        raise HTTPException(status_code=409, detail="Only a finished question run can be pinned.")
    report = run["result"]["report"]
    if report.get("out_of_scope"):
        raise HTTPException(status_code=409, detail="An out-of-scope answer has nothing to pin.")
    if not followup_id:
        return engine.finding_from_run(fid, run_id, report)
    f = next((x for x in run.get("followups", []) if x["id"] == followup_id), None)
    if f is None or f["status"] != "done":
        raise HTTPException(status_code=409, detail="Only a finished follow-up can be pinned.")
    if f["op"] == "rerun" and f.get("child_run_id"):
        child = forecast_store.get(f["child_run_id"])
        finding = engine.finding_from_run(fid, f["child_run_id"], child["result"]["report"],
                                          title=f"Rerun: {f['question']}" if not re.search(r"\d", f["question"]) else None)
        return {**finding, "kind": "rerun", "question": f["question"],
                "source": {"run_id": run_id, "followup_id": followup_id, "child_run_id": f["child_run_id"]}}
    if f["op"] == "weekly" and f.get("table"):
        return engine.finding_from_weekly(fid, run_id, f, report)
    if f["op"] == "explain":
        return engine.finding_from_explain(fid, run_id, f, report)
    if f["op"] == "drill" and f.get("splits"):
        return engine.finding_from_drill(fid, run_id, f, report)
    if f["op"] == "chart" and f.get("chart"):
        return engine.finding_from_chart(fid, run_id, f, report)
    raise HTTPException(status_code=409, detail="This follow-up has nothing to pin.")


def pins_of(run: dict) -> list[str]:
    """A run's pinned content: the investigation ("main") and the pinned follow-ups that are still done."""
    done = {f["id"] for f in run.get("followups", []) if f["status"] == "done"}
    return ["main"] + [p for p in run.get("pins", []) if p in done]


def collect(r: dict) -> tuple[list[dict], list[str]]:
    """The report's findings from its runs' current pins, with stable ids, and the pins' signature."""
    findings, keys = [], []
    for run_id in r["runs"]:
        run = forecast_store.get(run_id)
        if run is None or run.get("job_status") != "done":
            continue
        for key in pins_of(run):
            k = f"{run_id}|{key}"
            if k not in r["fids"]:
                r["fids"][k] = f"F{len(r['fids']) + 1}"
            try:
                findings.append(_finding(r["fids"][k], run_id, None if key == "main" else key))
                keys.append(k)
            except HTTPException:
                continue  # a pin with nothing to show (e.g. a help answer) is left out
    return findings, sorted(keys)


def _version(r: dict, template: str, author: str, by: str, instruction: str | None) -> None:
    engine = _engine()
    used = ({fid for fid, _ in engine.TOKEN.findall(template)} | set(engine.TABLE.findall(template))
            | {fid for fid, _ in engine.CHART.findall(template)} | set(engine.KPIS.findall(template))
            | {fid for fid, _ in engine.BLOCK.findall(template)})
    findings = {f["id"]: f for f in r["findings"] if f["id"] in used}
    r["versions"].append({"n": len(r["versions"]) + 1, "at": now(), "by": by, "author": author,
                          "instruction": instruction, "template": template, "findings": findings})
    r["current"] = len(r["versions"])
    r["stale"] = False


def _draft_job(rid: str, instruction: str | None, model: str | None, by: str) -> None:
    """Runs in a background thread: a new version from the model (checked), or the code draft."""
    engine = _engine()
    try:
        with _LOCK:
            r = get(rid)
            findings, signature = collect(r)
            put(r)
        current = (r["versions"][r["current"] - 1].get("prose") if r["current"] else None) or None
        if current and instruction is None and signature != r.get("signature"):
            instruction = ("The pinned findings changed. Update the prose to fit them; keep everything else as it is.")
        prose, refused = None, []
        if not findings:
            text, problems = None, ["nothing is pinned"]
        elif model:
            text, prose, refused = engine.model_draft(findings, model, instruction, current, r["title"])
            problems = engine.check(text, {f["id"]: f for f in findings})
            if problems:  # code's layout and prose are the safe floor
                prose = engine.code_prose(findings)
                text, refused = engine.layout(findings, prose, r["title"]), refused + problems
        else:
            prose = engine.code_prose(findings)
            text, problems = engine.layout(findings, prose, r["title"]), []
        with _LOCK:
            r = get(rid)
            r["findings"] = findings
            if text:
                _version(r, text, "model" if model and not problems else "code", by, instruction)
                r["versions"][-1]["prose"] = prose
                r["signature"] = signature
                r["job"] = {"status": "idle", "message": ("Some paragraphs kept code's wording: " + "; ".join(refused[:3]) + ".")
                            if refused else None}
            else:
                r["job"] = {"status": "failed", "message": "The change was not applied: " + "; ".join(problems[:4]) + "."}
            r["history"].append({"at": now(), "by": by, "action": "draft" if text else "draft_refused",
                                 "note": instruction})
            put(r)
    except Exception as exc:  # noqa: BLE001 - recorded on the report
        log.exception("forecast report draft failed")
        with _LOCK:
            r = get(rid)
            if r:
                r["job"] = {"status": "failed", "message": f"Drafting failed ({type(exc).__name__})."}
                put(r)


def _start_draft(r: dict, instruction: str | None, by: str) -> None:
    model = _model()
    if instruction and not model:
        raise HTTPException(status_code=409, detail="Revising by instruction needs a language model on the server.")
    r["job"] = {"status": "drafting", "message": None, "started_at": now(),
                "step": "The model is writing the prose for each section" if model else "Code is assembling the report"}
    put(r)
    threading.Thread(target=_draft_job, args=(r["id"], instruction, model, by), daemon=True,
                     name=f"forecast-report-{r['id']}").start()


def view(r: dict, analyst: bool) -> dict:
    """The analyst sees the contents (pinned items), versions and history; a leader sees the current version only."""
    engine = _engine()
    if analyst:
        findings, signature = collect(r)
        r["findings"], r["stale"] = findings, bool(r["current"]) and signature != r.get("signature")
    current = r["versions"][r["current"] - 1] if r["current"] else None
    title, secs = (engine.sections(engine.render(current["template"], current["findings"])) if current else (r["title"], []))
    out = {"id": r["id"], "title": title, "review_status": r["review_status"], "review_note": r["review_note"],
           "reviewed_at": r["reviewed_at"], "submitted_at": r["submitted_at"], "version": r["current"],
           "sections": secs, "author": current["author"] if current else None,
           "charts": engine.charts_used(current["template"], current["findings"]) if current else {},
           "kpis": engine.kpis_used(current["template"], current["findings"]) if current else {},
           "blocks": engine.blocks_used(current["template"], current["findings"]) if current else {},
           "sources": [{"id": f["id"], "scope": f["scope"]} for f in (current["findings"].values() if current else [])]}
    if not analyst:
        return out
    return {**out, "job": r["job"], "stale": r["stale"], "created_at": r["created_at"], "history": r["history"],
            "model": _model(), "runs": [{"run_id": x, "question": ((forecast_store.get(x) or {}).get("request") or {}).get("question")}
                                        for x in r["runs"]],
            "findings": [{k: f[k] for k in ("id", "kind", "title", "scope", "question", "source")} for f in r["findings"]],
            "versions": [{k: v[k] for k in ("n", "at", "author", "instruction")} for v in r["versions"]]}


def _who(p: rbac.Principal, role: rbac.Role) -> dict:
    return {"user": rbac.pseudonym(p.sub), "role": role.name, "persona": role.persona, **p.tag()}


# ---- routes -----------------------------------------------------------------------------------------------------

def routes(Forecast) -> None:
    @router.post("")
    def create(payload: NewReport, response: Response, who=Forecast) -> dict:
        """A report from a finished question run: its pins are the contents. A run has one open report."""
        response.headers["Cache-Control"] = "no-store"
        p, role = who
        rbac.allow(role, "run")
        by = rbac.pseudonym(p.sub)
        with _LOCK:
            run = forecast_store.get(payload.run_id)
            if run is None or run.get("kind") != "question" or run.get("job_status") != "done":
                raise HTTPException(status_code=409, detail="A report starts from a finished question run.")
            existing = get(run["report_id"]) if run.get("report_id") else None
            if existing and existing["review_status"] in EDITABLE:
                return view(existing, True)
            scope = (run["result"]["report"].get("scope") or {})
            title = payload.title or (f"Cardiovela forecast performance: {scope.get('territory_name', 'National')}, {scope.get('period', '')}"
                                      if scope.get("period") else "Cardiovela forecast performance")[:120]
            r = {"id": "r-" + uuid.uuid4().hex[:12], "title": title.strip(), "created_at": now(), "created_by": by,
                 "runs": [payload.run_id], "fids": {}, "findings": [], "signature": None, "versions": [], "current": None,
                 "stale": False, "job": {"status": "idle", "message": None}, "review_status": forecast_store.NOT_SUBMITTED,
                 "submitted_by": None, "submitted_at": None, "reviewed_by": None, "reviewed_at": None, "review_note": None,
                 "history": [{"at": now(), "by": by, "action": "created", "note": None}]}
            put(r)
            forecast_store.update(payload.run_id, report_id=r["id"])
            _start_draft(r, None, by)
        store.record_event("forecast_report_created", **_who(p, role), report_id=r["id"])
        return view(get(r["id"]), True)

    @router.post("/{rid}/runs")
    def add_run(rid: str, payload: Source, response: Response, who=Forecast) -> dict:
        """Add another run's pinned content to the report."""
        response.headers["Cache-Control"] = "no-store"
        _p, role = who
        rbac.allow(role, "run")
        with _LOCK:
            r = _record(rid)
            _editable(r)
            run = forecast_store.get(payload.run_id)
            if run is None or run.get("kind") != "question" or run.get("job_status") != "done":
                raise HTTPException(status_code=409, detail="Only a finished question run can be added.")
            if payload.run_id not in r["runs"]:
                r["runs"].append(payload.run_id)
            put(r)
        return view(r, True)

    @router.delete("/{rid}/runs/{run_id}")
    def remove_run(rid: str, run_id: str, response: Response, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        _p, role = who
        rbac.allow(role, "run")
        with _LOCK:
            r = _record(rid)
            _editable(r)
            if run_id == r["runs"][0]:
                raise HTTPException(status_code=409, detail="The run the report started from stays in it.")
            r["runs"] = [x for x in r["runs"] if x != run_id]
            put(r)
        return view(r, True)

    @router.get("")
    def list_reports(response: Response, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        _p, role = who
        rbac.allow(role, "read")
        analyst = "run" in role.actions
        rows = [r for r in all_reports() if analyst or r["review_status"] != forecast_store.NOT_SUBMITTED]
        return {"reports": [{"id": r["id"], "title": view(r, False)["title"], "review_status": r["review_status"],
                             "created_at": r["created_at"], "findings": len(r["findings"]), "version": r["current"]}
                            for r in rows]}

    @router.get("/{rid}")
    def open_report(rid: str, response: Response, view_as: str | None = None, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        _p, role = who
        rbac.allow(role, "read")
        r = _record(rid)
        analyst = "run" in role.actions and view_as != "leadership"
        if "run" not in role.actions and r["review_status"] == forecast_store.NOT_SUBMITTED:
            raise HTTPException(status_code=404, detail="No such report.")
        return view(r, analyst)

    @router.post("/{rid}/draft")
    def draft(rid: str, payload: Draft, response: Response, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        p, role = who
        rbac.allow(role, "run")
        with _LOCK:
            r = _record(rid)
            _editable(r)
            instruction = " ".join((payload.instruction or "").split()) or None
            _start_draft(r, instruction, rbac.pseudonym(p.sub))
        return view(get(rid), True)

    @router.post("/{rid}/versions/{n}/restore")
    def restore(rid: str, n: int, response: Response, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        p, role = who
        rbac.allow(role, "run")
        with _LOCK:
            r = _record(rid)
            _editable(r)
            if not 1 <= n <= len(r["versions"]):
                raise HTTPException(status_code=404, detail="No such version.")
            old = r["versions"][n - 1]
            r["versions"].append({**old, "n": len(r["versions"]) + 1, "at": now(), "by": rbac.pseudonym(p.sub),
                                  "author": old["author"], "instruction": "restored an earlier version"})
            r["current"] = len(r["versions"])
            put(r)
        return view(r, True)

    @router.post("/{rid}/submit")
    def submit(rid: str, response: Response, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        p, role = who
        rbac.allow(role, "run")
        with _LOCK:
            r = _record(rid)
            _editable(r)
            findings, signature = collect(r)
            if not r["current"] or signature != r.get("signature"):
                raise HTTPException(status_code=409, detail="The pinned content changed; let the report update before submitting.")
            by = rbac.pseudonym(p.sub)
            r.update(review_status=forecast_store.PENDING, submitted_by=by, submitted_at=now(), reviewed_by=None,
                     reviewed_at=None, review_note=None)
            r["history"].append({"at": now(), "by": by, "action": "submitted", "note": f"version {r['current']}"})
            put(r)
        store.record_event("forecast_report_submitted", **_who(p, role), report_id=rid)
        return view(r, True)

    @router.post("/{rid}/review")
    def review(rid: str, decision: Review, response: Response, who=Forecast) -> dict:
        response.headers["Cache-Control"] = "no-store"
        p, role = who
        rbac.allow(role, "review")
        note = (decision.note or "").strip() or None
        if decision.decision in ("rejected", "returned") and not note:
            raise HTTPException(status_code=422, detail="A rejection or a return needs a note.")
        with _LOCK:
            r = _record(rid)
            if r["review_status"] != forecast_store.PENDING:
                raise HTTPException(status_code=409, detail="Only a submitted report can be reviewed.")
            by = rbac.pseudonym(p.sub)
            r.update(review_status=decision.decision, reviewed_by=by, reviewed_at=now(), review_note=note)
            r["history"].append({"at": now(), "by": by, "action": decision.decision, "note": note})
            put(r)
        store.record_event("forecast_report_reviewed", **_who(p, role), report_id=rid, decision=decision.decision)
        return view(r, False)
