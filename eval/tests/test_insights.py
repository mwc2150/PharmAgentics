"""Insights on a tiny MLflow-shaped SQLite store built in the test: stuck, fallen, engine, spread, read-only."""
import sqlite3

import pytest

from eval.harness.insights import build, render_md

Q_DOLLAR = "Week of 2026-05-04 in New England: Where should the next dollar go?"
Q_CONF = "Week of 2026-05-04 in New England: How confident is the estimate?"
Q_BRIEF = "Week of 2026-06-08 in Pacific: Brief me on Pacific this week."
PAIRS = [("C-1", Q_DOLLAR), ("C-2", Q_CONF), ("C-3", Q_BRIEF)]

SCHEMA = """
create table experiments (experiment_id integer, name text);
insert into experiments values (1, 'pharmagentics-golden'), (2, 'pharmagentics-forecast-drivers');
create table runs (run_uuid text, name text, start_time integer, lifecycle_stage text, status text default 'FINISHED',
                   experiment_id integer default 1);
create table params (key text, value text, run_uuid text);
create table tags (key text, value text, run_uuid text);
create table trace_info (request_id text, request_preview text);
create table trace_request_metadata (key text, value text, request_id text);
create table assessments (trace_id text, name text, assessment_type text, value text, valid integer, rationale text);
"""


def _question(q):
    return '{"question": "%s"}' % q


def _store(path, parents, experiment_id=1):
    """parents: {run_id: (system, golden, start, [(question, {scorer: value_text})...])} ; each parent gets one child."""
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    n = 0
    for run_id, (system, golden, start, traces) in parents.items():
        con.execute("insert into runs (run_uuid, name, start_time, lifecycle_stage, experiment_id) values (?,?,?,?,?)",
                    (run_id, "name", start, "active", experiment_id))
        con.execute("insert into params values ('system', ?, ?)", (system, run_id))
        con.execute("insert into params values ('golden_version', ?, ?)", (golden, run_id))
        child = f"child-{run_id}"
        con.execute("insert into runs (run_uuid, name, start_time, lifecycle_stage, experiment_id) values (?,?,?,?,?)",
                    (child, "child", start, "active", experiment_id))
        con.execute("insert into tags values ('mlflow.parentRunId', ?, ?)", (run_id, child))
        for question, scores in traces:
            n += 1
            tid = f"tr-{n}"
            con.execute("insert into trace_info values (?,?)", (tid, _question(question)))
            con.execute("insert into trace_request_metadata values ('mlflow.sourceRun', ?, ?)", (child, tid))
            con.execute("insert into assessments (trace_id, name, assessment_type, value, valid) values (?,'case_id','expectation','\"X\"',1)", (tid,))
            for name, value in scores.items():  # a value is "0.5" or ("0.5", rationale); None leaves the score out
                if value is None:
                    continue
                value, why = value if isinstance(value, tuple) else (value, None)
                con.execute("insert into assessments (trace_id, name, assessment_type, value, valid, rationale) values (?,?,'feedback',?,1,?)",
                            (tid, name, value, why))
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


def test_a_run_in_another_experiment_is_ignored(tmp_path):
    path = tmp_path / "mixed.db"
    _store(str(path), {"P1": ("briefing_scripted", "g1", 1000, [(Q_DOLLAR, {"golden_number_recall": "1.0"})])})
    other = tmp_path / "other.db"
    _store(str(other), {"D1": ("forecast_drivers", "g1", 2000, [(Q_DOLLAR, {"golden_number_recall": "0.0"})])}, experiment_id=2)
    con = sqlite3.connect(str(path))
    con.execute("attach database ? as o", (str(other),))
    con.execute("insert into runs select * from o.runs")
    for t in ("params", "tags", "trace_info", "trace_request_metadata", "assessments"):
        con.execute(f"insert into {t} select * from o.{t}")
    con.commit()
    con.execute("detach database o")
    con.close()
    out = build([path], PAIRS)
    assert list(out["systems"]) == ["briefing_scripted"]


def test_lower_is_better_scorers_are_not_stuck_or_spread_and_a_rise_is_a_fall(tmp_path):
    path = tmp_path / "low.db"
    _store(str(path), {
        "P1": ("briefing_scripted", "g1", 1000, [(Q_DOLLAR, {"false_drivers": "2.0"}), (Q_CONF, {"false_drivers": "0.0"}),
                                                   (Q_BRIEF, {"false_drivers": "0.0"}), (Q_BRIEF, {"false_drivers": "3.0"})]),
        "P2": ("briefing_scripted", "g1", 2000, [(Q_DOLLAR, {"false_drivers": "0.0"}), (Q_CONF, {"false_drivers": "1.0"}),
                                                   (Q_BRIEF, {"false_drivers": "0.0"}), (Q_BRIEF, {"false_drivers": "3.0"})])})
    d = build([path], PAIRS)
    assert d["stuck"] == [] and d["rerun_spread"] == []  # 0 false drivers is good, not stuck
    fallen = {(r["case"], r["previous"], r["latest"]) for r in d["fallen"]}
    assert fallen == {("C-2", 0.0, 1.0)}  # 2 -> 0 is better; 0 -> 1 is worse


def test_numbers_lost_compares_latest_agent_with_latest_scripted_on_the_same_golden(tmp_path):
    scripted, agent, other = tmp_path / "s.db", tmp_path / "a.db", tmp_path / "o.db"
    _store(str(scripted), {"S1": ("briefing_scripted", "g1", 1000, [
        (Q_DOLLAR, {"key_fact_recall": "1.0"}), (Q_CONF, {"key_fact_recall": "0.5"}), (Q_BRIEF, {"key_fact_recall": "0.5"})])})
    _store(str(agent), {"A1": ("briefing_agent:m", "g1", 2000, [
        (Q_DOLLAR, {"key_fact_recall": "0.25"}), (Q_CONF, {"key_fact_recall": "0.75"}), (Q_BRIEF, {"golden_number_recall": "1.0"})])})
    _store(str(other), {"L1": ("briefing_lowcode:q", "g2", 3000, [(Q_DOLLAR, {"key_fact_recall": "0.0"})])})
    d = build([scripted, agent, other], PAIRS)
    assert d["numbers_lost"] == [  # C-3 has no agent key_fact_recall; the low-code run is on another golden
        {"system": "briefing_agent:m", "case": "C-1", "scripted": 1.0, "agent": 0.25, "lost": 0.75},
        {"system": "briefing_agent:m", "case": "C-2", "scripted": 0.5, "agent": 0.75, "lost": -0.25}]
    assert d["numbers_lost_mean"] == {"briefing_agent:m": 0.25}
    section = render_md(d).split("## Numbers lost by the agent")[1].split("\n## ")[0]
    assert "C-1" in section and "C-2" not in section  # only rows with lost > 0
    assert "+0.250" in section


def test_kinds_group_the_matrix_and_leave_out_run_counters(stores):
    d = build(stores, PAIRS)
    assert set(d["kinds"]) == {"code", "agent", "safety"}
    assert "golden_number_recall" in d["kinds"]["code"] and "claims_reconcile" in d["kinds"]["code"]
    assert not {"seconds", "llm_calls", "tool_calls", "hit_cap"} & {k for ks in d["kinds"].values() for k in ks}
    assert "briefing_scripted: Code checks" in render_md(d)
