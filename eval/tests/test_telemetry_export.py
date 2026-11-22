"""The per-case block of the telemetry export: ids, labels, scores and marks only (core-011 FR-009)."""
import json

from eval.harness.telemetry_export import _labels, cases_block, export

LABELS = {
    "C-1": {"lane": "briefing", "story": "US-1", "persona": "P1 Commercial Analyst"},
    "C-2": {"lane": "briefing", "story": "US-2", "persona": "P1 Commercial Analyst"},
    "F-1": {"lane": "forecast", "story": "FE-1", "persona": "CA Commercial Analyst"},
}
INSIGHTS = {
    "generated": "2026-11-22T10:00:00+00:00",
    "systems": {
        "briefing_scripted": {"runs": [{"run_id": "aaaaaaaa11", "started": "2026-11-20T10:00+00:00", "golden_version": "g1"},
                                       {"run_id": "bbbbbbbb22", "started": "2026-11-21T10:00+00:00", "golden_version": "g1"}],
                              "scorers": ["claims_reconcile", "golden_number_recall", "ragas_faithfulness"]},
        "reference": {"runs": [{"run_id": "cccccccc33", "started": "2026-11-21T11:00+00:00", "golden_version": "g1"}],
                      "scorers": ["claims_reconcile"]},
    },
    "matrix": {
        "briefing_scripted": {"C-1": {"claims_reconcile": [1.0, 1.0], "golden_number_recall": [0.0, 0.0]},
                              "C-2": {"claims_reconcile": [1.0, 0.5], "golden_number_recall": [0.5, None]},
                              "ZZ-9": {"claims_reconcile": [1.0, 1.0]}},
        "reference": {"C-1": {"claims_reconcile": [1.0]}, "F-1": {"claims_reconcile": [1.0]}},
    },
    "stuck": [{"system": "briefing_scripted", "story": "US-1", "case": "C-1", "scorer": "golden_number_recall", "runs": 2}],
    "fallen": [{"system": "briefing_scripted", "story": "US-2", "case": "C-2", "scorer": "claims_reconcile",
                "previous": 1.0, "latest": 0.5, "drop": 0.5, "previous_run": "a", "latest_run": "b"}],
}


def _system(block, name, lane="briefing"):
    return next(s for s in block["systems"] if s["system"] == name and s["lane"] == lane)


def test_block_holds_latest_scores_and_marks_per_case():
    s = _system(cases_block(INSIGHTS, LABELS), "briefing_scripted")
    assert s["run_id"] == "bbbbbbbb" and not s["control"]
    assert s["scorers"] == ["claims_reconcile", "golden_number_recall"] and s["report_only"] == []
    c1, c2 = s["rows"]
    assert c1 == {"case": "C-1", "story": "US-1", "persona": "P1 Commercial Analyst",
                  "scores": {"claims_reconcile": 1.0, "golden_number_recall": 0.0},
                  "stuck": ["golden_number_recall"], "fallen": []}
    assert c2["scores"] == {"claims_reconcile": 0.5, "golden_number_recall": None}  # not scored stays null
    assert c2["fallen"] == [{"scorer": "claims_reconcile", "previous": 1.0, "latest": 0.5}]
    assert [r["case"] for r in s["rows"]] == ["C-1", "C-2"]  # a case with no golden label is left out


def test_controls_are_flagged_and_split_by_lane():
    block = cases_block(INSIGHTS, LABELS)
    assert _system(block, "reference")["control"] and _system(block, "reference", "forecast")["rows"][0]["case"] == "F-1"


def test_judge_scorers_are_marked_report_only():
    insights = {**INSIGHTS, "matrix": {"briefing_scripted": {"C-1": {"ragas_faithfulness": [0.9]}}}}
    s = _system(cases_block(insights, LABELS), "briefing_scripted")
    assert s["report_only"] == ["ragas_faithfulness"]


def test_block_carries_no_golden_text():
    block = cases_block(INSIGHTS, _labels() | LABELS)
    allowed_row = {"case", "story", "persona", "scores", "stuck", "fallen"}
    for s in block["systems"]:
        assert set(s) == {"system", "lane", "control", "run_id", "started", "golden_version", "scorers", "report_only", "rows"}
        assert all(set(r) == allowed_row for r in s["rows"])
    # Nothing from a real golden case beyond its id, story id and persona label reaches the block.
    from eval.harness.cases import load_cases

    text = json.dumps(block)
    for c in load_cases():
        assert c.question not in text and c.given not in text and c.story_text not in text


def test_export_writes_cases_when_insights_are_given(tmp_path, monkeypatch):
    monkeypatch.setattr("eval.harness.telemetry_export._labels", lambda: LABELS)
    out = tmp_path / "t.json"
    snap = export(out, uri=f"sqlite:///{(tmp_path / 'none.db').as_posix()}", insights=INSIGHTS)
    assert json.loads(out.read_text(encoding="utf-8"))["cases"] == snap["cases"]
    assert {s["system"] for s in snap["cases"]["systems"]} == {"briefing_scripted", "reference"}
