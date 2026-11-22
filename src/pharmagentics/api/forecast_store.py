"""Forecast runs and their review state as small JSON documents (forecast_runs/<id>.json), on the same two
backends as the Briefing store (a local folder, or the Cloud Storage bucket on Cloud Run).

A run starts as ``not_submitted``. The Commercial Analyst submits it (``pending_review``); the Brand
Manager approves, rejects or returns it. Nothing is ever approved by the system. Each step is kept in
``history`` with a pseudonym, never a name, so a later evaluation log can read it.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from .store import _dump, backend, now

NOT_SUBMITTED, PENDING, APPROVED, REJECTED, RETURNED = "not_submitted", "pending_review", "approved", "rejected", "returned"
ID = re.compile(r"^f-[0-9a-f]{12}$")

# Every read-modify-write of a run holds this lock, so a background step (progress, the writer's prose, a follow-up)
# never overwrites a review saved in between. The app runs as one process (Cloud Run max-instances=1), so an
# in-process lock is enough; a second instance would need the bucket's generation preconditions.
LOCK = threading.RLock()

# Background work in this process: run ids (and "run/followup" or "report/<id>" keys) whose thread is still going.
# A run marked running that no thread here holds was lost to a restart (Cloud Run scales to zero and kills threads).
_LIVE: set[str] = set()
LOST_GRACE_SECONDS = 120  # not held here and silent this long: lost (the grace covers a deploy's brief overlap)
LOST_MAX_SECONDS = 3600   # silent this long: lost, whatever this process thinks
LOST_RUN = "The investigation stopped before it finished (the server restarted). Ask the question again."
LOST_FOLLOWUP = "The follow-up stopped before it finished (the server restarted). Ask it again."


def hold(key: str) -> None:
    """Mark background work as live; call before its thread starts."""
    _LIVE.add(key)


def release(key: str) -> None:
    _LIVE.discard(key)


@contextmanager
def held(key: str):
    """For the background thread: the work stays live until the thread ends, however it ends."""
    _LIVE.add(key)
    try:
        yield
    finally:
        _LIVE.discard(key)


def _age(at: str | None) -> float:
    if not at:
        return float("inf")
    return (datetime.now(timezone.utc) - datetime.fromisoformat(at)).total_seconds()


def lost(key: str, last_at: str | None) -> bool:
    """Whether background work marked as running was lost (its thread is gone)."""
    age = _age(last_at)
    return age > LOST_MAX_SECONDS or (key not in _LIVE and age > LOST_GRACE_SECONDS)


def _expire(record: dict) -> bool:
    """Mark a lost investigation or follow-up as failed, so it can be asked again. True if anything changed."""
    rid, changed = record["run_id"], False
    if record.get("job_status") == "running" and lost(rid, record.get("updated_at") or record.get("created_at")):
        record.update(job_status="failed", job_error=LOST_RUN)
        changed = True
    for f in record.get("followups") or []:
        if f.get("status") == "running" and lost(f"{rid}/{f['id']}", f.get("started_at") or record.get("updated_at")):
            f.update(status="failed", answer=LOST_FOLLOWUP)
            changed = True
    return changed


def run_id(request: dict, result: dict) -> str:
    """The same request on the same data release and engine gives the same id, so a rerun keeps its review."""
    key = "|".join(str(x) for x in (request["territory_id"], request["week_start"], request["window_weeks"],
                                    result.get("dataset_release"), result["report"].get("investigator_mode")))
    return "f-" + hashlib.sha256(key.encode()).hexdigest()[:12]


def _same_answer(a: dict, b: dict) -> bool:
    def key(result: dict) -> tuple:
        r = result["report"]
        return (r["variance_trx"], r["abstained"], (r.get("verification") or {}).get("verdict"),
                tuple((d["driver"], round(d["impact_trx"], 3)) for d in r["drivers"]))
    return key(a) == key(b)


def _key(rid: str) -> str:
    if not ID.match(rid):
        raise KeyError(rid)
    return f"forecast_runs/{rid}.json"


def _read(rid: str) -> dict | None:
    try:
        text = backend().read(_key(rid))
    except KeyError:
        return None
    return json.loads(text) if text else None


def get(rid: str) -> dict | None:
    """A run, with any investigation or follow-up lost to a restart marked as failed (and saved so)."""
    with LOCK:
        record = _read(rid)
        if record is not None and _expire(record):
            _put(record)
        return record


def _put(record: dict) -> dict:
    record["updated_at"] = now()
    backend().write(_key(record["run_id"]), _dump(record))
    return record


def mutate(rid: str, change) -> dict | None:
    """Read a run, apply `change(record)` and save it, all under the lock. None if there is no such run."""
    with LOCK:
        record = get(rid)
        if record is None:
            return None
        change(record)
        return _put(record)


PENDING_WRITER_SECONDS = 300  # a writer still "pending" after this long was lost (a restart); try again


def pending_writer() -> dict:
    return {"narrative": None, "report_model": "none", "writer_status": "pending", "writer_attempts": [],
            "writer_started_at": now()}


def _stale(started_at: str | None) -> bool:
    if not started_at:
        return True
    from datetime import datetime, timezone
    return (datetime.now(timezone.utc) - datetime.fromisoformat(started_at)).total_seconds() > PENDING_WRITER_SECONDS


def needs_writer(request: dict, result: dict) -> bool:
    """Whether the report writer should run for this answer. A rerun of an answer that already has prose, or that
    was correctly left without (an attribution paused), spends nothing; one that fell back is tried again, and
    one still being written is left alone."""
    existing = get(run_id(request, result))
    if existing is None or not _same_answer(existing["result"], result):
        return True
    status = existing.get("writer_status")
    if status == "pending":
        return _stale(existing.get("writer_started_at"))
    outcomes = [a.get("outcome") for a in existing.get("writer_attempts") or []]
    return status in (None, "fallback_stub") or outcomes == ["disabled"]


def set_writer(rid: str, writer: dict) -> None:
    """Store the finished prose on a run. Re-reads the run first, so a review made meanwhile is kept."""
    def change(record: dict) -> None:
        record.update(narrative=writer["narrative"], report_model=writer["report_model"],
                      writer_status=writer["writer_status"], writer_attempts=writer["writer_attempts"])
        record.pop("writer_started_at", None)

    mutate(rid, change)


def save(request: dict, result: dict, by: str, writer: dict | None = None) -> dict:
    with LOCK:
        rid = run_id(request, result)
        existing = get(rid)
        if existing and _same_answer(existing["result"], result):
            if writer is not None:  # the answer is unchanged; keep its review state and refresh the prose
                existing.update(writer)
                return _put(existing)
            return existing
        writer = writer or {"narrative": None, "report_model": "none", "writer_status": "skipped", "writer_attempts": []}
        record = {"run_id": rid, "created_at": now(), "created_by": by, "request": request, "result": result,
                  "review_status": NOT_SUBMITTED, "submitted_by": None, "submitted_at": None,
                  "reviewed_by": None, "reviewed_at": None, "review_decision": None, "review_note": None, "history": [],
                  **writer}
        return _put(record)


def _log(record: dict, action: str, by: str, role: str, note: str | None) -> None:
    record["history"].append({"at": now(), "by": by, "role": role, "action": action, "note": note})


def question_id(question: str, territory: str | None, weeks: list[str] | None, engine: str, data_version: str) -> str:
    """The same question and scope on the same data release and engine gives the same run, so a rerun keeps its review."""
    key = "|".join(str(x) for x in (" ".join(question.lower().split()), territory, weeks and (weeks[0], weeks[-1]), engine, data_version))
    return "f-" + hashlib.sha256(key.encode()).hexdigest()[:12]


PLACEHOLDER = {"headline": "Investigating…", "drivers": [], "caveats": [], "what_to_check": [], "variance_trx": None,
               "abstained": False, "residual_trx": None, "forecast_trx": None, "actual_trx": None, "variance_pct": None}


def start_question(rid: str, request: dict, by: str, engine: str) -> dict:
    """A question run starts as `running`; the engine fills `result` in the background."""
    with LOCK:
        record = {"run_id": rid, "kind": "question", "created_at": now(), "created_by": by, "request": request,
                  "result": {"run_id": rid, "lane": "forecast", "engine": engine, "workflow_status": "Investigating",
                             "report": {**PLACEHOLDER, "question": request["question"], "investigator_mode": engine}},
                  "job_status": "running", "job_error": None, "progress": [],
                  "review_status": NOT_SUBMITTED, "submitted_by": None, "submitted_at": None, "reviewed_by": None,
                  "reviewed_at": None, "review_decision": None, "review_note": None, "history": [],
                  "narrative": None, "report_model": "none", "writer_status": "skipped", "writer_attempts": []}
        return _put(record)


def update(rid: str, **fields) -> dict | None:
    """Change a run's fields. Re-reads the run first, so a review made meanwhile is kept."""
    return mutate(rid, lambda record: record.update(fields))


def submit(rid: str, by: str, role: str) -> dict:
    with LOCK:
        record = get(rid)
        if record is None:
            raise KeyError(rid)
        if record.get("job_status") in ("running", "failed"):
            raise ValueError("Only a finished investigation can be submitted.")
        if record["review_status"] not in (NOT_SUBMITTED, RETURNED):
            raise ValueError(f"A run that is {record['review_status']} cannot be submitted.")
        record.update(review_status=PENDING, submitted_by=by, submitted_at=now(), reviewed_by=None, reviewed_at=None,
                      review_decision=None, review_note=None)
        _log(record, "submitted", by, role, None)
        return _put(record)


def review(rid: str, decision: str, note: str | None, by: str, role: str) -> dict:
    with LOCK:
        record = get(rid)
        if record is None:
            raise KeyError(rid)
        if record["review_status"] != PENDING:
            raise ValueError(f"Only a submitted run can be reviewed; this one is {record['review_status']}.")
        record.update(review_status=decision, reviewed_by=by, reviewed_at=now(), review_decision=decision, review_note=note)
        _log(record, decision, by, role, note)
        return _put(record)


def all_runs() -> list[dict]:
    store = backend()
    out = []
    for key in store.keys("forecast_runs/"):
        text = store.read(key)
        if text:
            record = json.loads(text)
            if _expire(record):  # a run lost to a restart shows as failed in the list too
                with LOCK:
                    record = get(record["run_id"]) or record
            out.append(record)
    return sorted(out, key=lambda r: r["created_at"], reverse=True)
