"""The question-driven Forecast engine (fcst-001): scope, discovery, comparisons, rules policy, writer invariants,
guardrails on the investigator's tools, and the model fallback. No model and no network: the rules policy runs."""
from __future__ import annotations

import re

import pytest

from pharmagentics.tools import DEFAULT_DB, Registry

from forecast_agent import answer
from forecast_agent.engine import Case, Refused
from forecast_agent.scope import intent_of, parse_scope

pytestmark = pytest.mark.skipif(not DEFAULT_DB.is_file(), reason="DuckDB not built; run the data loader")
FIRST, LATEST = "2024-10-14", "2026-10-05"


def case(question: str) -> Case:
    reg = Registry(DEFAULT_DB)
    return Case(reg, parse_scope(question, FIRST, LATEST))


@pytest.mark.parametrize("question,intent", [
    ("Week of 2026-05-04, New England: Is the deviation reliable, or a data issue?", "reliability"),
    ("Week of 2026-08-24: Which regions or segments drive the miss?", "where"),
    ("Week of 2026-08-24: How much of the miss does each driver explain?", "attribution"),
    ("Mar to Sep 2026: What are the most plausible commercial drivers?", "drivers"),
    ("Mar to Oct 2026: Should any forecast assumptions be reviewed?", "assumptions"),
    ("Top 5 largest gaps in the last 3 months", "screen"),
    ("Week of 2026-08-24: Is the explanation auditable and reconciled?", "audit"),
])
def test_intent(question, intent):
    assert intent_of(question) == intent


def test_relative_period_counts_back_from_the_latest_week():
    s = parse_scope("Top 5 largest gaps in the last 3 months", FIRST, LATEST)
    assert s.weeks[-1] == LATEST and len(s.weeks) == 13 and s.territory == "NATIONAL"


@pytest.mark.parametrize("question", ["What is the forecast miss for Metacora?",
                                      "Should we cut the budget for the Southeast?"])
def test_out_of_scope_questions_run_nothing(question):
    out = answer(question)
    assert out["abstained"] and not out["claims"] and out["report"]["out_of_scope"]


def test_national_week_reproduces_the_story_split():
    out = answer("Week of 2026-08-24: How much of the miss does each driver explain?")
    r = out["report"]
    assert r["variance_trx"] == -1036 and r["bias_trx"] == -32
    by = {d["driver"]: d for d in r["drivers"]}
    assert by["competitor"]["impact_trx"] == -655 and by["competitor"]["confidence"] == "medium"
    assert by["promotion"]["territory"] == "SOUTHEAST" and -230 < by["promotion"]["impact_trx"] < -195
    assert r["bias_trx"] + sum(d["impact_trx"] for d in r["drivers"]) + r["residual_trx"] == pytest.approx(-1036, abs=1)
    assert r["verification"]["verdict"] == "PASS"


def test_every_digit_in_an_answer_is_a_claim_value_or_a_date():
    out = answer("Mar to Sep 2026: What are the most plausible commercial drivers?")
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b|\b\w*[A-Za-z_]\w*\d\w*\b", " ", out["answer"])  # dates and identifiers
    for c in sorted(out["claims"], key=lambda c: -len(c["value"])):
        text = text.replace(c["value"], " ")
    assert not re.findall(r"\d", text)


def test_discovery_finds_the_episodes_without_a_calendar():
    c = case("Mar to Sep 2026: What are the most plausible commercial drivers?")
    found = {(e.driver, e.territory) for e in c.discover()}
    assert {("promotion", "GREAT_LAKES"), ("promotion", "SOUTHEAST"), ("supply", "PACIFIC"), ("competitor", "ALL")} <= found


def test_a_long_period_sets_aside_provisional_weeks_instead_of_abstaining():
    out = answer("Mar to Sep 2026: What are the most plausible commercial drivers?")
    r = out["report"]
    assert not r["abstained"] and set(r["set_aside_weeks"]) == {"2026-05-04", "2026-07-06"}
    assert {d["driver"] for d in r["drivers"]} == {"promotion", "supply", "competitor"}
    assert any(d["action"] == "set_aside_weeks" and d["by"] == "code" for d in r["decisions"])


def test_a_provisional_week_is_never_attributed():
    out = answer("Week of 2026-05-04, New England: Is the deviation reliable, or a data issue?")
    assert out["abstained"] and not out["report"]["drivers"] and "provisional" in out["answer"]


def test_mid_atlantic_access_is_quantified_against_clean_controls():
    out = answer("Weeks of 2025-08-04 to 2025-10-27, Mid-Atlantic: How much can credibly be attributed to each driver?")
    access = next(d for d in out["report"]["drivers"] if d["driver"] == "access")
    assert access["impact_trx"] == -693 and len(access["controls"]) == 7


def test_an_easing_that_reverses_a_restriction_is_not_a_new_episode():
    c = case("Mar to Sep 2026: What are the most plausible commercial drivers?")
    assert not [e for e in c.discover() if e.driver == "access"]


def test_tools_refuse_what_the_rules_do_not_allow():
    c = case("Week of 2026-08-24: How much of the miss does each driver explain?")
    eps = {e.driver: e for e in c.discover()}
    se = eps["promotion"]
    with pytest.raises(Refused, match="Unknown episode"):
        c.compare("E99")
    with pytest.raises(Refused, match="at least four"):
        c.compare(se.id, ["NEW_ENGLAND", "MID_ATLANTIC", "GREAT_LAKES", "SOUTH_CENTRAL"])
    with pytest.raises(Refused, match="call compare first"):
        c.accept(se.id, "K9", "a reason in words", "agent")
    k = c.compare(se.id)
    with pytest.raises(Refused, match="digits"):
        c.accept(se.id, k.id, "it fell by 60 percent", "agent")
    c.accept(se.id, k.id, "it fell well behind clean controls", "agent")
    assert c.accepted()[0][0].id == se.id


def test_a_dropped_control_changes_the_estimate_and_is_recorded():
    c = case("Week of 2026-08-24: How much of the miss does each driver explain?")
    se = next(e for e in c.discover() if e.driver == "promotion")
    default, dropped = c.compare(se.id), c.compare(se.id, ["SOUTH_CENTRAL"])
    assert "SOUTH_CENTRAL" not in dropped.controls and round(dropped.effect) == -204 and round(default.effect) == -213


@pytest.fixture
def no_language_model(monkeypatch):
    """Reading and writing without a model server: the reader and the writer report a model error."""
    import forecast_agent.prose as prose
    import forecast_agent.reader as reader
    from forecast_agent.scope import parse_scope as rules

    monkeypatch.setattr(reader, "read_scope", lambda q, f, l, spec: (rules(q, f, l), "rules"))
    monkeypatch.setattr(prose, "write_summary", lambda w, parts, spec: (None, "model_error"))


def test_a_failed_model_falls_back_to_the_rules(monkeypatch, no_language_model):
    import forecast_agent.agent as agent

    def broken(spec):
        raise RuntimeError("no model server")

    monkeypatch.setattr(agent, "chat_client", broken)
    out = answer("Week of 2026-08-24: How much of the miss does each driver explain?", model="ollama:none",
                 investigator="model")
    assert out["trajectory"]["fallback"] and "rules fallback" in out["report"]["investigator_mode"]
    assert {d["driver"] for d in out["report"]["drivers"]} == {"competitor", "promotion"}


def test_candidates_a_model_leaves_open_are_decided_by_the_rules_and_labelled(monkeypatch, no_language_model):
    import forecast_agent.agent as agent

    class Silent:  # a model that answers without calling any tool
        def __init__(self, *a, **k):
            pass

        async def run(self, *a, **k):
            return None

    monkeypatch.setattr(agent, "Agent", Silent)
    monkeypatch.setattr(agent, "chat_client", lambda spec: None)
    monkeypatch.setattr(agent, "options", lambda spec, *a: {})
    out = answer("Week of 2026-08-24: How much of the miss does each driver explain?", model="ollama:none",
                 investigator="model")
    assert out["trajectory"]["left_undecided"] == 2 and not out["trajectory"]["fallback"]
    assert {d["by"] for d in out["report"]["decisions"]} == {"rules (agent left it undecided)"}
    assert {d["driver"] for d in out["report"]["drivers"]} == {"competitor", "promotion"}


def test_with_a_model_the_rules_still_investigate_by_default(no_language_model):
    out = answer("Week of 2026-08-24: How much of the miss does each driver explain?", model="ollama:none")
    assert out["report"]["investigator_mode"] == "rules" and out["trajectory"]["investigator"] == "rules"
    assert out["report"]["summary_by"] == "code" and out["trajectory"]["writer_status"] == "model_error"


def test_a_model_written_summary_is_kept_when_the_check_accepts_it(monkeypatch, no_language_model):
    """Regression: a function-local `import re` in compose() made `re` unbound here, so every accepted model summary
    on a non-screen question failed the run with UnboundLocalError."""
    import forecast_agent.prose as prose

    monkeypatch.setattr(prose, "write_summary", lambda w, parts, spec: ("The verified drivers explain most of the miss.", "ok"))
    out = answer("Week of 2026-08-24: How much of the miss does each driver explain?", model="ollama:none")
    assert out["report"]["summary_by"] == "model" and out["trajectory"]["writer_status"] == "ok"


def test_a_confirmed_scope_skips_reading(no_language_model):
    out = answer("Why did we miss?", model="ollama:none", territory="PACIFIC", weeks=["2026-06-01", "2026-06-08"],
                 intent="drivers")
    r = out["report"]
    assert r["scope_read_by"] == "confirmed" and r["intent"] == "drivers" and r["territory_id"] == "PACIFIC"


@pytest.mark.parametrize("start,end,weeks", [
    ("2026-08-24", "2026-08-24", ["2026-08-24"]),
    ("2026-05-06", "2026-05-06", ["2026-05-04"]),
    ("2026-08-01", "2026-08-31", ["2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31"]),
    ("2027-01-01", "2027-02-01", []),
])
def test_the_reader_turns_calendar_dates_into_release_weeks(start, end, weeks):
    from forecast_agent.reader import _period
    assert _period(start, end, FIRST, LATEST) == weeks


def test_the_summary_check_refuses_what_a_model_must_not_write():
    from forecast_agent.prose import check
    tokens = [{"token": "{c1}", "means": "miss"}, {"token": "{c2}", "means": "residual"}]
    allowed = {"drivers": {"promotion"}, "territories": {"NATIONAL", "SOUTHEAST"}, "residual": "{c2}"}
    ok = "Cardiovela missed by {c1}, mostly from the Southeast rep coverage lapse; {c2} is not explained yet."
    assert check(ok, tokens, allowed) is None
    assert check(ok.replace("{c1}", "about 1,000"), tokens, allowed) == "digit_outside_token"
    assert check(ok + " Also {c9}.", tokens, allowed) == "unknown_token"
    assert check("Cardiovela missed by {c1} in the Southeast.", tokens, allowed) == "residual_missing"
    assert check(ok + " We should cut the budget there.", tokens, allowed) == "commercial_action"
    assert check(ok + " Supply was tight too.", tokens, allowed) == "new_driver"
    assert check(ok + " Pacific also fell.", tokens, allowed) == "new_territory"


# ---- reports (fcst-002) ----------------------------------------------------------------------------------------

def _f1():
    from forecast_agent.report import finding_from_run
    return finding_from_run("F1", "f-test", answer("Week of 2026-08-24: How much of the miss does each driver explain?")["report"])


def test_a_code_draft_renders_code_numbers_and_passes_its_checks():
    from forecast_agent.report import blocks_used, check, code_draft, kpis_used, render
    f1 = _f1()
    t = code_draft([f1], "National miss")
    assert check(t, {"F1": f1}, require_all=True) == []
    for heading in ("## Executive summary", "## How much each driver explains", "## Conclusions and next steps", "## About this report"):
        assert heading in t  # a report: summary, a chapter per finding, conclusions
    assert "[[kpis F1]]" in t and "[[block F1 attribution]]" in t and "[[chart F1 waterfall]]" in t
    assert kpis_used(t, {"F1": f1})["F1"]["miss"] == -1036
    assert "-655" in blocks_used(t, {"F1": f1})["F1 attribution"]["text"]  # the investigation's verified passage
    assert "The miss splits into" in render(t, {"F1": f1})

@pytest.mark.parametrize("bad,why", [
    ("# T\n## A\nThe miss was about 1,000 TRx.", "outside a token"),
    ("# T\n## A\nMetacora {F1:d1}, medium. Residual {F1:missing}.", "not a token"),
    ("# T\n## A\nMetacora {F1:d1}, medium.", "without its unexplained residual"),
    ("# T\n## A\nMetacora {F1:d1}. Residual {F1:residual}.", "needs its own confidence"),
    ("# T\n### M\n- {F1:d1}\n- Confidence: medium\n### S\n- {F1:d2}\n- Confidence: high\nResidual {F1:residual}.", "needs its own confidence"),
    ("# T\n## A\nMetacora {F1:d1}, medium, is confirmed. Residual {F1:residual}.", "overstates"),
    ("# T\n## A\nSupply shortfalls hurt too. Residual {F1:residual}.", "supply driver"),
    ("# T\n## A\nOn the week {F1:miss}, Pacific also fell. Residual {F1:residual}.", "Pacific"),
    ("# T\n## A\nWe should cut the budget. Residual {F1:residual}.", "commercial action"),
])
def test_report_checks_refuse_what_a_model_must_not_write(bad, why):
    from forecast_agent.report import check, finding_from_run
    f1 = _f1()
    if why == "Pacific":  # a finding that covers no Pacific comparison or ranking (the provisional New England week)
        r = answer("Week of 2026-05-04, New England: Is the deviation reliable, or a data issue?")["report"]
        f1 = finding_from_run("F1", "x", {**r, "screen": []})
    assert any(why in p for p in check(bad, {"F1": f1}))


def test_a_percent_sign_after_a_percent_token_is_not_doubled():
    from forecast_agent.report import render
    assert render("{F1:miss_pct}% and {F1:miss_pct} percent", {"F1": _f1()}) == "20.2% and 20.2%"


# ---- charts (fcst-002) -----------------------------------------------------------------------------------------

def test_the_waterfall_reconciles_from_forecast_to_actual():
    r = answer("Week of 2026-08-24: How much of the miss does each driver explain?")["report"]
    steps = r["charts"]["waterfall"]["steps"]
    first, last = steps[0]["value"], steps[-1]["value"]
    assert first == r["forecast_trx"] and last == r["actual_trx"]
    assert first + sum(s["value"] for s in steps[1:-1]) == pytest.approx(last, abs=2)
    assert r["charts_shown"] == ["waterfall"] and r["charts_by"] == "code"


@pytest.mark.parametrize("question,shown", [
    ("Top 5 largest gaps in the last 3 months", ["territories"]),
    ("Mar to Oct 2026: Should any forecast assumptions be reviewed?", ["trend"]),
    ("Week of 2026-05-04, New England: Is the deviation reliable, or a data issue?", []),
])
def test_code_shows_a_default_chart_per_question_type(question, shown):
    assert answer(question)["report"]["charts_shown"] == shown


def test_a_report_chart_marker_must_name_a_chart_its_finding_has():
    from forecast_agent.report import check, code_draft
    f1 = _f1()
    t = code_draft([f1], "T")
    assert "[[chart F1 waterfall]]" in t and check(t, {"F1": f1}) == []
    assert any("not a chart" in p for p in check(t + "\n[[chart F1 trend]]", {"F1": f1}))


def test_a_chart_follow_up_names_its_chart_or_says_which_are_offered():
    from forecast_agent.followup import route
    r = answer("Week of 2026-08-24: How much of the miss does each driver explain?")["report"]
    assert route("Can you plot that by territory?", r, FIRST, LATEST) == {"op": "chart", "kind": "territories"}
    assert route("plot it by week", r, FIRST, LATEST) == {"op": "chart", "kind": "weekly"}  # not offered: the reply says so


# ---- where an unexplained gap sits (fcst-002) ------------------------------------------------------------------

def test_south_central_september_sits_in_one_commercial_plan_and_is_broad_by_specialty():
    c = case("Weeks of 2026-08-31 to 2026-09-28, South Central: What portion remains unexplained?")
    ch, sp = c.split("SOUTH_CENTRAL", "channel"), c.split("SOUTH_CENTRAL", "specialty")
    assert ch["verdict"] == "concentrated" and ch["top"] == "COMMERCIAL"
    assert sp["verdict"] == "broad"
    plans = c.split("SOUTH_CENTRAL", "plan", "COMMERCIAL")
    assert plans["verdict"] == "concentrated" and plans["top"] == "SYN_SOUTH_CENTRAL_COMMERCIAL_1"


@pytest.mark.parametrize("question,terr", [
    ("Weeks of 2026-02-02 to 2026-02-23, Great Lakes: why?", "GREAT_LAKES"),
    ("Weeks of 2026-08-03 to 2026-08-31, Southeast: why?", "SOUTHEAST"),
])
def test_the_promotion_lapses_hit_broadly_as_the_user_stories_say(question, terr):
    c = case(question)
    assert c.split(terr, "channel")["verdict"] == "broad" and c.split(terr, "specialty")["verdict"] == "broad"


def test_an_unexplained_gap_gets_its_split_section_check_and_chart():
    r = answer("Weeks of 2026-08-31 to 2026-09-28, South Central: What portion remains unexplained?")["report"]
    gap = next(s for s in r["sections"] if s["id"] == "gap")
    assert "concentrated in Commercial" in gap["text"] and "not why" in gap["text"]
    assert any("Commercial coverage" in c["question"] for c in r["what_to_check"])
    assert "segments" in r["charts"] and "segments" in r["charts_shown"]
    assert not any("Split the South Central gap" in c["question"] for c in r["what_to_check"])


def test_every_pinned_finding_must_appear_in_a_model_version():
    from forecast_agent.report import check, finding_from_run
    f1 = _f1()
    f2 = finding_from_run("F2", "b", answer("Top 5 largest gaps in the last 3 months")["report"])
    text = "# T\nMetacora {F1:d1}, medium; Southeast {F1:d2}, medium; residual {F1:residual}."
    assert any("F2" in p and "missing" in p for p in check(text, {"F1": f1, "F2": f2}, require_all=True))


def test_a_driver_named_in_words_must_carry_its_own_confidence():
    from forecast_agent.report import check
    f1 = {"F1": _f1()}
    assert check("We are confident in the Metacora launch and medium on the Southeast lapse.", f1)
    assert check("The Metacora launch explains most of it, with medium confidence.", f1) == []


def test_a_refused_model_paragraph_falls_back_to_codes_own(monkeypatch):
    import forecast_agent.report as report

    class Writer:
        def __init__(self, *a, **k):
            self.tools = k["tools"]

        async def run(self, *a, **k):
            self.tools[0](summary="The Metacora launch explains most of the miss, with medium confidence.",
                          key_points="Most of the miss matches the launch\nPart is unexplained",
                          chapters="F1: Metacora explains 2,000 TRx of it.", conclusion="Forecasting reviews the assumption.")

    monkeypatch.setattr("agent_framework.Agent", Writer)
    monkeypatch.setattr("pharmagentics.llm.chat_client", lambda spec: None)
    prose, refused = report.model_prose([_f1()], "ollama:none", None, None)
    assert "Metacora" in prose["summary"] and prose["key_points"].count("\n") == 1
    assert prose["F1"] == report.LEAD_IN["attribution"] and any(r.startswith("F1") for r in refused)

def test_a_model_written_summary_is_used_and_tidied(monkeypatch):
    import forecast_agent.prose as prose

    monkeypatch.setattr(prose, "write_summary", lambda w, parts, spec: ("Cardiovela missed by {c2} percent... ", "ok"))
    import forecast_agent.charts as charts
    monkeypatch.setattr(charts, "choose", lambda q, i, menu, spec: (["waterfall"], "model"))
    out = answer("Why did we miss?", model="ollama:none", territory="NATIONAL", weeks=["2026-08-24"], intent="attribution")
    assert out["report"]["summary_by"] == "model" and out["report"]["charts_by"] == "model"


def test_local_model_options_keep_qwen_loaded_and_grow_the_context_only_when_needed():
    from forecast_agent.models import options
    short = options("ollama:qwen3:4b-instruct-2507-q4_K_M")
    assert short["num_ctx"] == 8192 and short["keep_alive"] == "30m"
    assert options("ollama:qwen3:4b-instruct-2507-q4_K_M", prompt_chars=30000)["num_ctx"] == 16384


@pytest.mark.parametrize("question,clear", [
    ("Week of 2026-08-24: How much of the miss does each driver explain?", True),
    ("Weeks of 2025-08-04 to 2025-10-27, Mid-Atlantic: How much can credibly be attributed to each driver?", True),
    ("Why were we so far below plan in the Southeast last August?", False),
    ("Which region hurt us most this summer?", False),
    ("What were the most likely commercial drivers between March and September 2026?", False),
])
def test_only_clear_questions_skip_the_model(question, clear):
    from forecast_agent.scope import confident
    assert confident(question, parse_scope(question, FIRST, LATEST)) is clear


def test_a_report_reads_as_a_report_not_a_chat():
    from forecast_agent.followup import weekly
    from forecast_agent.report import code_draft, finding_from_explain, finding_from_run, finding_from_weekly
    r = answer("Week of 2026-08-24: How much of the miss does each driver explain?")["report"]
    fs = [finding_from_run("F1", "a", r),
          finding_from_weekly("F2", "a", {"id": "q1", "question": "Show it week by week", "table": weekly(r)["table"]}, r),
          finding_from_explain("F3", "a", {"id": "q2", "question": "Why was this driver accepted?", "answer": "It moved away from clean controls."}, r)]
    t = code_draft(fs, "Cardiovela forecast performance")
    assert "Asked" not in t and "?" not in "".join(l for l in t.splitlines() if l.startswith("#"))
    assert "## The miss week by week: National" in t and "## The reasoning behind the findings: National" in t


# ---- inputs that reach SQL text (review 2026-11-22) ---------------------------------------------------------------

def test_an_unknown_cut_or_a_malformed_week_is_refused_before_any_query():
    """A model-chosen follow-up scope reaches the engine: a name instead of an id used to answer from zero rows
    ("0.0% above forecast in Pacific"), and a week is put into SQL text."""
    reg = Registry(DEFAULT_DB)
    try:
        with pytest.raises(Refused, match="Unknown territory"):
            Case(reg, parse_scope("Why did we miss?", FIRST, LATEST, territory="Pacific", weeks=["2026-03-02"]))
        with pytest.raises(Refused, match="Not a week date"):
            Case(reg, parse_scope("Why did we miss?", FIRST, LATEST, weeks=["2026-03-02' or '1'='1"]))
    finally:
        reg.close()


def test_a_repeated_week_is_one_week():
    assert parse_scope("Why did we miss?", FIRST, LATEST, weeks=["2026-03-02", "2026-03-02"]).weeks == ["2026-03-02"]


def test_a_plan_split_takes_only_a_payer_channel_the_data_holds():
    c = case("Week of 2026-08-24: Which regions or segments drive the miss?")
    with pytest.raises(Refused, match="Unknown payer channel"):
        c.split("PACIFIC", "plan", "COMMERCIAL' or '1'='1")
    assert c.split("PACIFIC", "plan", "commercial")["within_channel"] == "COMMERCIAL"
