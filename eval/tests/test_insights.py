"""Insights on a tiny MLflow-shaped SQLite store built in the test: stuck, fallen, engine, spread, read-only."""
import sqlite3

import pytest

from eval.harness.insights import build, render_md

Q_DOLLAR = "Week of 2026-05-04 in New England: Where should the next dollar go?"
Q_CONF = "Week of 2026-05-04 in New England: How confident is the estimate?"
Q_BRIEF = "Week of 2026-06-08 in Pacific: Brief me on Pacific this week."
PAIRS = [("C-1", Q_DOLLAR), ("C-2", Q_CONF), ("C-3", Q_BRIEF)]

SCHEMA = """
create table runs (run_uuid text, name text, start_time integer, lifecycle_stage text, status text default 'FINISHED');
create table params (key text, value text, run_uuid text);
create table tags (key text, value text, run_uuid text);
create table trace_info (request_id text, request_preview text);
create table trace_request_metadata (key text, value text, request_id text);
create table assessments (trace_id text, name text, assessment_type text, value text, valid integer);
"""


def _question(q):
    return '{"question": "%s"}' % q


def _store(path, parents):
    """parents: {run_id: (system, golden, start, [(question, {scorer: value_text})...])} ; each parent gets one child."""
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    n = 0
    for run_id, (system, golden, start, traces) in parents.items():
        con.execute("insert into runs (run_uuid, name, start_time, lifecycle_stage) values (?,?,?,?)", (run_id, "name", start, "active"))
        con.execute("insert into params values ('system', ?, ?)", (system, run_id))
        con.execute("insert into params values ('golden_version', ?, ?)", (golden, run_id))
        child = f"child-{run_id}"
        con.execute("insert into runs (run_uuid, name, start_time, lifecycle_stage) values (?,?,?,?)", (child, "child", start, "active"))
        con.execute("insert into tags values ('mlflow.parentRunId', ?, ?)", (run_id, child))
        for question, scores in traces:
            n += 1
            tid = f"tr-{n}"
            con.execute("insert into trace_info values (?,?)", (tid, _question(question)))
            con.execute("insert into trace_request_metadata values ('mlflow.sourceRun', ?, ?)", (child, tid))
            con.execute("insert into assessments values (?,'case_id','expectation','\"X\"',1)", (tid,))
            for name, value in scores.items():
                con.execute("insert into assessments values (?,?,'feedback',?,1)", (tid, name, value))
    con.commit()
    con.close()


@pytest.fixture
def stores(tmp_path):
    scripted = tmp_path / "scripted.db"
    agent = tmp_path / "agent.db"
    _store(str(scripted), {
        # P1 and P2: golden_number_recall is 0 for C-1 in both runs (stuck); C-2 falls from 1.0 to 0.5 (fallen).
        # P2 reruns C-3 with 1.0 and 0.0 (spread).
        "P1": ("briefing_scripted", "g1", 1000, [
            (Q_DOLLAR, {"golden_number_recall": "0.0", "claims_reconcile": "1.0"}),
            (Q_CONF, {"golden_number_recall": "1.0"}),
            (Q_BRIEF, {"golden_number_recall": "0.5"}),
        ]),
        "P2": ("briefing_scripted", "g1", 2000, [
            (Q_DOLLAR, {"golden_number_recall": "0.0", "claims_reconcile": "1.0"}),
            (Q_CONF, {"golden_number_recall": "0.5"}),
            (Q_BRIEF, {"golden_number_recall": "1.0"}),
            (Q_BRIEF, {"golden_number_recall": "0.0"}),
        ]),
    })
    _store(str(agent), {
        # Agent runs: A1 on golden g1; A2 on golden g2 (a golden-version break, so no fallen check for this system).
        "A1": ("briefing_agent:m", "g1", 1500, [(Q_BRIEF, {"golden_number_recall": "0.5"})]),
        "A2": ("briefing_agent:m", "g2", 3000, [(Q_BRIEF, {"golden_number_recall": "0.75"}),
                                                  (Q_CONF, {"golden_number_recall": "0.25"})]),
    })
    return [scripted, agent]


def test_stuck_fallen_engine_spread_and_breaks(stores):
    d = build(stores, PAIRS, last=5)

    stuck = {(r["system"], r["case"], r["scorer"]) for r in d["stuck"]}
    assert ("briefing_scripted", "C-1", "golden_number_recall") in stuck
    assert ("briefing_scripted", "C-2", "golden_number_recall") not in stuck

    fallen = {(r["system"], r["case"], r["scorer"]) for r in d["fallen"]}
    assert ("briefing_scripted", "C-2", "golden_number_recall") in fallen
    assert ("briefing_scripted", "C-3", "golden_number_recall") not in fallen
    assert not any(r["system"] == "briefing_agent:m" for r in d["fallen"])  # golden break: not comparable

    assert d["golden_breaks"] == [{"system": "briefing_agent:m", "from_run": "A1", "to_run": "A2",
                                   "from_golden": "g1", "to_golden": "g2", "comparable": False}]

    spread = {(r["run_id"], r["case"]) for r in d["rerun_spread"]}
    assert ("P2", "C-3") in spread
    assert ("P1", "C-3") not in spread

    pair = d["engine"][0]
    assert pair["scripted"] == "briefing_scripted" and pair["agent"] == "briefing_agent:m"
    assert pair["same_golden"] is False
    c3 = pair["cases"]["C-3"]["golden_number_recall"]
    assert c3["scripted"] == 0.5 and c3["agent"] == 0.75 and c3["delta"] == 0.25
    assert "C-2" in pair["cases"] and "C-1" not in pair["cases"]  # the agent never answered C-1

    assert d["systems"]["briefing_scripted"]["runs"][-1]["run_id"] == "P2"
    assert d["matrix"]["briefing_scripted"]["C-3"]["golden_number_recall"] == [0.5, 0.5]
    assert d["std"]["briefing_scripted"]["C-3"]["golden_number_recall"][1] == 0.5
    assert d["unmapped_traces"] == 0


def test_system_filter_and_last(stores):
    d = build(stores, PAIRS, system="briefing_scripted", last=1)
    assert list(d["systems"]) == ["briefing_scripted"]
    assert [r["run_id"] for r in d["systems"]["briefing_scripted"]["runs"]] == ["P2"]
    assert d["engine"] == []


def test_markdown_renders(stores):
    text = render_md(build(stores, PAIRS))
    assert "Stuck" in text and "Fallen" in text and "Engine comparison" in text
    assert "NOT COMPARABLE" in text  # the engine pair is on different goldens
    assert "golden_number_recall" in text


def test_store_is_opened_read_only(stores):
    from eval.harness.insights import _connect

    con = _connect(stores[0])
    with pytest.raises(sqlite3.OperationalError):
        con.execute("insert into runs values ('x','x',0,'active')")
    con.close()


def test_a_run_still_going_is_left_out(tmp_path):
    path = tmp_path / "running.db"
    _store(str(path), {"P1": ("briefing_scripted", "g1", 1000, [(Q_DOLLAR, {"golden_number_recall": "1.0"})]),
                       "P2": ("briefing_scripted", "g1", 2000, [(Q_DOLLAR, {"golden_number_recall": "0.0"})])})
    con = sqlite3.connect(str(path))
    con.execute("update runs set status = 'RUNNING' where run_uuid in ('P2', 'child-P2')")
    con.commit()
    con.close()
    out = build([path], PAIRS)
    assert [r["run_id"] for r in out["systems"]["briefing_scripted"]["runs"]] == ["P1"]
