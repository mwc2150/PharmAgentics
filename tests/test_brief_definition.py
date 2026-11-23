"""brief-010 packet D-B: the brief definition (FR-000a, FR-000c, FR-000e). The pre-selected definition reproduces today's
brief exactly; each field changes what it should; every field takes a list whose first value is the primary and whose
extra values add labelled figures; the API stores, returns and words the definition. Real scripted engine, no model.

The golden question texts are copied here on purpose: agent code and tests under src/ never import eval/.
The fixture tests/fixtures/brief010_db_baseline.json is today's output (before the definition existed), except that the
Assumptions block now also says "Holiday weeks are left out." (the one deliberate text change).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents" / "brand-briefing"))

from pharmagentics.tools import DEFAULT_DB  # noqa: E402
from pharmagentics.tools import definition as defs  # noqa: E402
from pharmagentics.tools.definition import Definition  # noqa: E402
from pharmagentics.tools.registry import digits_outside_tokens  # noqa: E402
from pharmagentics.tools.window import Comparison, comparison_weeks  # noqa: E402

needs_db = pytest.mark.skipif(not DEFAULT_DB.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")
BASELINE = json.loads((ROOT / "tests" / "fixtures" / "brief010_db_baseline.json").read_text(encoding="utf-8"))
ROUTINE, WITHHELD, EVENTFUL = "2025-04-21", "2026-05-04", "2026-08-24"
STORY = "Weeks of 2026-08-03 to 2026-08-31, Southeast: What should I do, and who should I loop in?"  # opens a Southeast story
GRAINS = ["national", "territory", "plan", "channel", "specialty"]
PREVIOUS4, PRE_LAUNCH = Comparison(kind="previous", weeks=4), Comparison(kind="pre_launch")


def brief(question: str, **kw) -> dict:
    from briefing_baseline import answer

    return answer(question, **kw)


def q(week: str, tail: str = "What changed this week?") -> str:
    return f"Week of {week}: {tail}"


def section(env: dict, number: str) -> dict:
    return next(s for s in env["sections"] if s["number"] == number)


def cards(env: dict) -> list[dict]:
    return [s["card"] for s in env["sections"] if s["number"].startswith("3.") and s.get("card") and s["card"]["territory"]]


# -- DB1: the model -----------------------------------------------------------------------------------

def test_pre_selected_values_and_validation():
    d = Definition()
    assert (d.territories, d.measure, d.relative_to, d.grain) == (["like_for_like"], ["trx"], ["other_territories"], GRAINS)
    assert d.is_pre_selected and d.comparison == [] and d.first_week is None and d.primary_comparison is None
    with pytest.raises(ValueError, match="Monday"):
        Definition(first_week="2026-08-25")
    with pytest.raises(ValueError, match="before the first"):
        Definition(first_week="2026-08-24", last_week="2026-08-17")
    with pytest.raises(ValueError, match="at least one"):
        Definition(grain=[])
    with pytest.raises(ValueError, match="at least one"):
        Definition(measure=[])
    with pytest.raises(ValueError, match="first_week"):
        Definition(last_week="2026-08-24")
    with pytest.raises(ValueError):
        Definition(measure="visits")
    with pytest.raises(ValueError):
        Definition.model_validate({"territories": "like_for_like", "surprise": 1})
    for repeated in ({"grain": ["territory", "territory"]}, {"measure": ["trx", "trx"]}, {"territories": ["projected", "projected"]},
                     {"relative_to": ["none", "none"]}, {"comparison": [PREVIOUS4, PREVIOUS4]}):
        with pytest.raises(ValueError, match="twice"):
            Definition(**repeated)
    assert Definition(grain=["territory", "national"]).grain == ["national", "territory"]
    with pytest.raises(ValueError, match="outside the release"):
        Definition(first_week="2020-01-06").validate_release("2024-10-14", "2026-10-05")


def test_every_field_but_the_period_takes_a_list_and_a_single_value_is_a_one_item_list():
    d = Definition(comparison={"kind": "previous", "weeks": 4}, territories="projected", measure="nbrx", relative_to="none")
    assert d.comparison == [PREVIOUS4] and d.territories == ["projected"] and d.measure == ["nbrx"] and d.relative_to == ["none"]
    assert Definition(comparison=None).comparison == [] and Definition.model_validate({"comparison": None}).primary_comparison is None
    many = Definition(comparison=[PREVIOUS4, PRE_LAUNCH], territories=["like_for_like", "all_reportable"], measure=["nbrx", "trx"],
                      relative_to=["national", "other_territories"])
    assert many.primary_comparison == PREVIOUS4 and many.extra_comparisons == [PRE_LAUNCH]
    assert (many.territory_rule, many.primary_measure, many.relative) == ("like_for_like", "nbrx", "national")
    assert Definition.model_validate(many.to_json()) == many
    assert Definition(measure="both") == Definition(measure=["trx", "nbrx"])  # "both" is the two measures, TRx first


def test_from_comparison_and_coerce():
    c = Comparison(kind="previous", weeks=6)
    assert Definition.from_comparison(c).comparison == [c] and Definition.from_comparison(c).is_pre_selected
    assert Definition.coerce(None, c).comparison == [c]
    assert Definition.coerce({"measure": "nbrx"}, c).comparison == [c]
    own = Comparison(kind="last_year")
    assert Definition.coerce(Definition(comparison=own), c).comparison == [own]  # the definition wins over the keyword
    assert Definition.coerce({"comparison": None}, c).comparison == [c]  # null is the default comparison
    assert Definition.coerce(None, None) == Definition.pre_selected()


def test_the_pre_launch_comparison_weeks_and_refusals():
    available = {f"2026-{m:02d}-{d:02d}" for m in range(1, 10) for d in range(1, 29)}
    weeks = comparison_weeks(PRE_LAUNCH, ["2026-08-24"], available | {"2026-02-02", "2026-02-09", "2026-02-16", "2026-02-23"}, launch="2026-03-02")
    assert weeks == ["2026-02-02", "2026-02-09", "2026-02-16", "2026-02-23"]
    with pytest.raises(ValueError, match="starts on or after the competitor launch"):
        comparison_weeks(PRE_LAUNCH, ["2026-02-23"], available, launch="2026-03-02")
    with pytest.raises(ValueError, match="No competitor launch"):
        comparison_weeks(PRE_LAUNCH, ["2026-08-24"], available, launch=None)
    with pytest.raises(ValueError):
        Comparison(kind="pre_launch", weeks=4)


def test_words_are_plain_sentences():
    d = Definition(first_week="2026-08-24", measure=["trx", "nbrx"], grain=["national", "territory"], territories="all_reportable",
                   relative_to=["national", "other_territories"], comparison=[Comparison(kind="previous", weeks=6), PRE_LAUNCH])
    text = " ".join(defs.words(d, launch="2026-03-02"))
    assert "the previous six weeks" in text and "Levels shown: national and territory." in text
    assert "Also shown against the four weeks before Metacora launched (2026-02-02 to 2026-02-23)." in text
    assert "total prescriptions (TRx) beside new patients (NBRx)" in text and "the national change and the other territories" in text
    assert "Holiday weeks are left out." in text
    assert not re.search(r"[a-z]+_[a-z]+", text)  # no raw ids
    assert "Territories counted: like for like, only territories reportable in both periods." in defs.words(Definition())
    assert defs.changed_words(Definition()) == [] and defs.assumption_sentence(Definition()) is None
    assert "new patients (NBRx)" in defs.assumption_sentence(Definition(measure="nbrx"))
    assert not digits_outside_tokens(defs.assumption_sentence(Definition(measure="both", grain=["territory"], relative_to="none",
                                                                          comparison=[PREVIOUS4, PRE_LAUNCH])))


# -- DB4 (1): the pre-selected definition is today's brief ----------------------------------------------

def _same_as_today(env: dict, saved: dict) -> None:
    assert env["answer"] == saved["answer"]
    assert [(c["value"], c["evidence_id"]) for c in env["claims"]] == [(c["value"], c["evidence_id"]) for c in saved["claims"]]
    assert json.loads(json.dumps(env["evidence"])) == saved["evidence"]
    assert env["abstained"] == saved["abstained"]


@needs_db
@pytest.mark.parametrize("case", sorted(BASELINE))
def test_the_pre_selected_definition_reproduces_todays_brief(case):
    saved = BASELINE[case]
    comparison = Comparison.model_validate(saved["comparison"]) if saved["comparison"] else None
    # golden P1-Q1, P1-Q4, P2-Q2, P2-Q3, P3-Q1, P3-Q4, P4-Q4 and WIN-1, plus a six-week comparison
    implicit = brief(saved["question"], **({"comparison": comparison} if comparison else {}))
    explicit = brief(saved["question"], definition=Definition(comparison=comparison))
    from_json = brief(saved["question"], definition=Definition(comparison=comparison).to_json())
    for env in (implicit, explicit, from_json):
        _same_as_today(env, saved)
    assert "Holiday weeks are left out." in implicit["answer"] or "Calendar weeks in this period are left out" in implicit["answer"] \
        or "Calendar weeks are left out of the stories." in implicit["answer"]


@needs_db
def test_chosen_weeks_in_the_definition_are_the_questions_weeks():
    saved = BASELINE["P3-Q1"]
    env = brief(saved["question"], definition=Definition(first_week="2026-04-27", last_week="2026-04-27"))
    _same_as_today(env, saved)
    other = brief(saved["question"], definition=Definition(first_week="2026-04-20"))  # the analyst's weeks win
    assert "week of 2026-04-20" in other["answer"].split("\n")[0]


# -- DB4 (4): claims carry the labels --------------------------------------------------------------------

@needs_db
def test_every_claim_records_the_definition_it_was_made_under():
    env = brief(STORY, definition=Definition(measure="both", relative_to="national", territories="all_reportable"))
    assert env["claims"]
    for c in env["claims"]:
        lab = c["labels"]
        assert (lab["territories"], lab["relative_to"], lab["comparison_kind"]) == ("all_reportable", "national", "default")
        assert lab["measure"] in ("trx", "nbrx")
        assert lab["period"] == "2026-08-03 to 2026-08-31" and re.fullmatch(r"\d{4}-\d\d-\d\d to \d{4}-\d\d-\d\d", lab["comparison"])
        assert lab["grain"] in GRAINS
    assert {c["labels"]["measure"] for c in env["claims"]} == {"trx", "nbrx"}  # the extra measure's claims say so
    assert {"national", "territory"} <= {c["labels"]["grain"] for c in env["claims"]}
    cuts = [c["labels"]["cut"] for c in env["claims"] if c["labels"].get("cut")]
    assert cuts and all(re.match(r"(plan|channel|specialty):", x) for x in cuts)
    assert all(c["labels"]["grain"] in ("plan", "channel", "specialty") for c in env["claims"] if c["labels"].get("cut"))


@needs_db
def test_claim_labels_name_the_value_of_each_field_the_claim_used():
    env = brief(q(EVENTFUL), definition=Definition(comparison=[PREVIOUS4, PRE_LAUNCH], relative_to=["other_territories", "national"]))
    kinds = {c["labels"]["comparison_kind"] for c in env["claims"]}
    assert kinds == {"previous", "pre_launch", "before_event"}  # before_event: the Southeast continuing card (brief-010 FR-010)
    pre = [c for c in env["claims"] if c["labels"]["comparison_kind"] == "pre_launch"]
    assert pre and all(c["labels"]["comparison"] == "2026-02-02 to 2026-02-23" for c in pre)
    assert all(c["labels"]["comparison"] != "2026-02-02 to 2026-02-23" for c in env["claims"] if c["labels"]["comparison_kind"] == "previous")


# -- DB4 (2): each field changes what it should ----------------------------------------------------------

@needs_db
def test_nbrx_is_labelled_and_comes_from_nbrx_sql():
    import duckdb

    env = brief(q(ROUTINE), definition=Definition(measure="nbrx"))
    text = env["answer"]
    assert "Like for like, BXA new patients (NBRx) averaged" in text and "Like for like, BXA TRx averaged" not in text
    assert any("sum(nbrx)" in e["query"] for e in env["evidence"])
    tile = next(k for k in section(env, "1")["kpis"] if k["label"] == "National BXA new patients (NBRx)")
    con = duckdb.connect(str(DEFAULT_DB), read_only=True)
    try:  # no territory is withheld in the routine week, so the national is the sum of the reportable view
        total = con.execute(f"select sum(nbrx) from reporting.v_reportable_rx where product_id = 'BXA' and week_start = DATE '{ROUTINE}'").fetchone()[0]
    finally:
        con.close()
    assert tile["value"] == f"{round(total):,}"
    assert any(k["label"] == "Change in new patients (NBRx)" for k in section(env, "1")["kpis"])
    table = section(env, "2")["territory_table"]
    assert "new patients (NBRx)" in table["columns"][1] and "TRx" not in table["columns"][1]
    assert all(row["cells"][1] not in ("", None) for row in table["rows"])


@needs_db
def test_the_word_new_patients_appears_only_with_nbrx():
    assert "new patients" not in brief(q(EVENTFUL))["answer"].lower()
    assert "new patients" not in brief(q(EVENTFUL), definition=Definition(relative_to="national"))["answer"].lower()


@needs_db
def test_measure_trx_and_nbrx_is_both_and_puts_nbrx_beside_trx():
    env = brief(STORY, definition=Definition(measure=["trx", "nbrx"]))
    text = env["answer"]
    assert "BXA TRx averaged" in text and "new patients (NBRx) averaged" in text
    table = section(env, "2")["territory_table"]
    assert sum("new patients (nbrx)" in c.lower() for c in table["columns"]) == 2 and any("TRx" in c for c in table["columns"])
    assert len({len(r["cells"]) for r in table["rows"]}) == 1 and len(table["columns"]) == len(table["rows"][0]["cells"])
    labels = [k["label"] for k in section(env, "1")["kpis"]]
    assert any("TRx" in x for x in labels) and any("new patients (NBRx)" in x for x in labels)
    story = next(s for s in env["sections"] if s["number"].startswith("3.") and s.get("card") and s["card"]["territory"])
    assert "New patients (NBRx) averaged" in story["text"] and "New patients (NBRx)" in story["card"]["headline"]
    # the same definition said as the string "both" is the same brief
    assert brief(STORY, definition={"measure": "both"})["answer"] == text


@needs_db
def test_the_first_measure_is_the_primary():
    env = brief(q(ROUTINE), definition=Definition(measure=["nbrx", "trx"]))
    assert "Like for like, BXA new patients (NBRx) averaged" in env["answer"] and "BXA TRx averaged" in env["answer"]
    assert section(env, "2")["territory_table"]["columns"][1].startswith("BXA new patients (NBRx)")
    assert section(env, "1")["kpis"][0]["label"] == "National BXA new patients (NBRx)"


@needs_db
def test_grain_without_territory_has_no_territory_stories_or_table():
    env = brief(STORY, definition=Definition(grain=["national"]))
    assert not cards(env)
    assert section(env, "2").get("territory_table") is None
    assert "Change by territory" not in env["answer"] and "Metacora" in env["answer"]
    assert "Projected national" in env["answer"]


@needs_db
def test_grain_without_national_has_no_national_lines_or_competitor_card():
    default = brief(STORY)
    assert "Metacora" in default["answer"]
    env = brief(STORY, definition=Definition(grain=["territory", "plan", "channel", "specialty"]))
    assert "This is a continuing story" not in env["answer"] and "Projected national" not in env["answer"]
    assert "four-brand" not in env["answer"] and "National figures are not part of this brief" in env["answer"]
    assert section(env, "2")["territory_table"]
    assert all(k["label"] not in ("National BXA TRx", "BXA basket share") for k in section(env, "1").get("kpis", []))


@needs_db
def test_grain_limits_the_splits():
    full = brief(STORY)
    cut = brief(STORY, definition=Definition(grain=["national", "territory", "plan"]))
    details = lambda env: "\n".join((s.get("detail") or "") for s in env["sections"] if s["number"].startswith("3."))  # noqa: E731
    assert "Cuts of the change by channel" in details(full) and "Cuts of the change by specialty" in details(full)
    assert "Cuts of the change by plan" in details(cut)
    assert "by channel" not in details(cut) and "by specialty" not in details(cut)


@needs_db
def test_relative_to_sets_what_a_story_is_set_against():
    base = brief(STORY)
    assert cards(base) and all("while the other territories were" in c["headline"] for c in cards(base))
    nat = brief(STORY, definition=Definition(relative_to="national"))
    assert cards(nat) and all("while national was" in c["headline"] for c in cards(nat))
    tile = next(k for k in section(nat, "1")["kpis"] if k["label"] == "Change on the comparison weeks")
    assert all(f"national was {'up' if tile['direction'] == 'up' else 'down' if tile['direction'] == 'down' else 'flat'}" in c["headline"] for c in cards(nat))
    assert all(tile["value"] in c["headline"] for c in cards(nat))  # the national change the territory is set against
    none = brief(STORY, definition=Definition(relative_to="none"))
    assert cards(none) and all("while" not in c["headline"] and not c["headline"].endswith("..") for c in cards(none))
    heads = "\n".join(s["text"] for s in none["sections"] if s["number"].startswith("3.") and s.get("card"))
    assert "other territories were" not in heads
    both = brief(STORY, definition=Definition(relative_to=["other_territories", "national"]))  # national beside the primary
    assert cards(both) and all("the other territories were" in c["headline"] and "and national was" in c["headline"] for c in cards(both))
    assert [c["territory"] for c in cards(both)] == [c["territory"] for c in cards(base)]  # the same stories


@needs_db
def test_all_reportable_counts_each_period_separately():
    import duckdb

    env = brief(q(WITHHELD), definition=Definition(territories="all_reportable"))
    default = brief(q(WITHHELD))
    assert "all reportable" in env["answer"] and "when" in env["answer"]
    assert "all reportable" not in default["answer"]
    con = duckdb.connect(str(DEFAULT_DB), read_only=True)
    try:
        cur = con.execute(f"select sum(trx) from reporting.v_reportable_rx where product_id = 'BXA' and week_start = DATE '{WITHHELD}'").fetchone()[0]
    finally:
        con.close()
    assert f"{round(cur):,}" in {c["value"] for c in env["claims"]}  # the national figure over the territories reportable in the period
    scopes = {e["params"].get("scope") for e in env["evidence"]}
    assert "national over the territories reportable in the period" in scopes
    assert "territories reportable in the comparison weeks" in scopes


@needs_db
def test_projected_uses_the_projected_national_as_the_headline_figure():
    env = brief(q(EVENTFUL), definition=Definition(territories="projected"))
    s1 = section(env, "1")["text"]
    assert "The projected national BXA TRx is" in s1 and "against the projected national of" in s1
    queries = [e["query"] for e in env["evidence"] if e["params"].get("scope") == "projected national"]
    assert queries and all("v_rx_projection" in x for x in queries)
    tile = next(k for k in section(env, "1")["kpis"] if k["label"] == "Change on the comparison weeks")
    assert tile["detail"].startswith("projected national")
    assert "Like for like on" not in s1


@needs_db
def test_an_extra_territories_rule_adds_a_labelled_figure_beside_the_primary():
    env = brief(q(WITHHELD), definition=Definition(territories=["like_for_like", "all_reportable"]))
    s1 = section(env, "1")["text"]
    assert "Like for like on" in s1 and "reportable in these weeks" in s1
    assert any(k["label"] == "Change, all reportable territories" for k in section(env, "1")["kpis"])
    assert {c["labels"]["territories"] for c in env["claims"]} == {"like_for_like", "all_reportable"}


@needs_db
def test_two_comparisons_show_both_figures_labelled_and_keep_todays_stories():
    one = brief(STORY, definition=Definition(comparison=[PREVIOUS4]))
    two = brief(STORY, definition=Definition(comparison=[PREVIOUS4, PRE_LAUNCH]))
    ids = lambda env: [(s["number"], s["title"]) for s in env["sections"] if s["number"].startswith("3.")]  # noqa: E731
    assert ids(two) == ids(one)  # the primary drives the stories: no second set
    assert [c["direction"] for c in cards(two)] == [c["direction"] for c in cards(one)] and cards(two)
    s1 = section(two, "1")
    assert "against the four weeks before Metacora launched (2026-02-02 to 2026-02-23)" in s1["text"]
    tiles = {k["label"]: k for k in s1["kpis"]}
    assert "Change against the pre-launch weeks" in tiles and "Change on the comparison weeks" in tiles
    assert tiles["Change against the pre-launch weeks"]["detail"].endswith("(2026-02-02 to 2026-02-23)")
    columns = section(two, "2")["territory_table"]["columns"]
    assert "On the comparison weeks" in columns and "On the pre-launch weeks" in columns
    heads = [c["headline"] for c in cards(two)]
    assert all("since before Metacora launched" in h for h in heads), heads
    assert all("since before Metacora launched" not in c["headline"] for c in cards(one))
    labelled = [c["labels"] for c in two["claims"] if c["labels"]["comparison_kind"] == "pre_launch"]
    assert labelled and {x["comparison"] for x in labelled} == {"2026-02-02 to 2026-02-23"}
    assert "four weeks before Metacora launched" in section(two, "6")["text"]


@needs_db
def test_the_pre_launch_comparison_is_refused_for_a_period_before_the_launch():
    with pytest.raises(ValueError, match="starts on or after the competitor launch"):
        brief(q(ROUTINE), definition=Definition(comparison=[PRE_LAUNCH]))
    with pytest.raises(ValueError, match="starts on or after the competitor launch"):
        brief(q(ROUTINE), definition=Definition(comparison=[PREVIOUS4, PRE_LAUNCH]))  # an extra comparison is checked too


@needs_db
def test_the_assumptions_block_adds_one_short_line_for_a_changed_definition():
    env = brief(q(EVENTFUL), definition=Definition(measure="nbrx", relative_to="none"))
    text = section(env, "6")["text"]
    assert "Brief definition, changed from the pre-selected values:" in env["answer"]
    assert len([x for x in text.splitlines() if x.startswith("- ")]) <= 5
    default = brief(q(EVENTFUL))
    assert "Brief definition" not in default["answer"] and "Holiday weeks are left out." in section(default, "6")["text"]


@needs_db
def test_outside_the_release_still_says_so():
    env = brief("Week of 2019-01-07: What changed?", definition=Definition(first_week="2019-01-07"))
    assert "outside the release" in env["answer"]


# -- the MCP session holds the definition beside the period -----------------------------------------------

@needs_db
def test_the_mcp_session_computes_under_the_definition():
    from pharmagentics.mcp_server.server import RunSession

    s = RunSession(DEFAULT_DB)
    try:
        s.open_run(q(EVENTFUL), None, Definition(measure="nbrx", grain=["territory"]))
        assert s.p.definition.measure == ["nbrx"] and s.reg.labels["measure"] == "nbrx"
        assert "new patients (NBRx)" in s.national_kpis() or "Change in new patients" in s.national_kpis()
        assert "leave out national" in s.competitor_status()
        s.open_run(q(EVENTFUL))
        assert s.p.definition.is_pre_selected
        assert "new patients" not in s.national_kpis()
    finally:
        s.close()


@needs_db
def test_the_triage_plan_names_the_definition_and_changes_with_it():
    from briefing_baseline.pipeline import triage

    a, b = triage(q(EVENTFUL)), triage(q(EVENTFUL), definition=Definition(measure="nbrx"))
    assert a["definition"]["measure"] == ["trx"] and b["definition"]["measure"] == ["nbrx"]
    assert a["plan_id"] != b["plan_id"]
    assert triage(q(EVENTFUL), definition=Definition())["plan_id"] == a["plan_id"]
    assert triage(q(EVENTFUL), definition=Definition(measure="both"))["plan_id"] == triage(q(EVENTFUL), definition=Definition(measure=["trx", "nbrx"]))["plan_id"]
    assert triage(q(EVENTFUL), definition=Definition(comparison=[PREVIOUS4, PRE_LAUNCH]))["plan_id"] != \
        triage(q(EVENTFUL), definition=Definition(comparison=[PREVIOUS4]))["plan_id"]
    no_national = triage(q(EVENTFUL), definition=Definition(grain=["territory"]))
    assert all(c["kind"] != "competitor" for c in no_national["stories"])
    no_territory = triage(q(EVENTFUL), definition=Definition(grain=["national"]))
    assert all(c["kind"] == "competitor" for c in no_territory["stories"])


# -- DB4 (3): the API stores, returns and words the definition ---------------------------------------------

def _client(tmp_path, monkeypatch, who="dev-analyst"):
    from fastapi.testclient import TestClient

    from pharmagentics.api.app import app

    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    c = TestClient(app)
    assert c.post("/auth/dev-login", data={"username": who}, follow_redirects=False).status_code == 303
    return c


QUERY = {"intent": "weekly_brief", "brand_id": "BXA", "territory_id": "PACIFIC", "week_start": EVENTFUL, "question": "What changed?"}


def test_the_query_validates_its_definition():
    from pydantic import ValidationError

    from pharmagentics.api.schemas import BriefingQuery

    ok = BriefingQuery.model_validate({**QUERY, "definition": {"measure": "nbrx", "first_week": EVENTFUL, "comparison": None}})
    assert ok.definition.measure == ["nbrx"] and ok.definition.comparison == []  # null is the default comparison
    for bad in ({"measure": "visits"}, {"grain": []}, {"first_week": "2026-08-25"}, {"first_week": "2026-08-17"},
                {"last_week": "2026-09-07", "first_week": EVENTFUL}, {"surprise": 1}, {"measure": ["trx", "trx"]}):
        with pytest.raises(ValidationError):
            BriefingQuery.model_validate({**QUERY, "definition": bad})
    # the top-level comparison carries the primary alone; when both are present the definition wins (no error)
    both = BriefingQuery.model_validate({**QUERY, "comparison": {"kind": "previous", "weeks": 4},
                                         "definition": {"comparison": [{"kind": "previous", "weeks": 6}]}})
    assert both.definition.primary_comparison.weeks == 6


@needs_db
def test_a_brief_is_stored_and_returned_with_its_definition_and_leaders_see_it_in_words(tmp_path, monkeypatch):
    analyst = _client(tmp_path, monkeypatch)
    body = {**QUERY, "definition": {"measure": "nbrx", "relative_to": "national", "grain": ["national", "territory"], "comparison": None}}
    r = analyst.post("/api/briefing/query", json=body)
    assert r.status_code == 200, r.text
    brief_ = r.json()
    d = brief_["definition"]
    assert d["measure"] == ["nbrx"] and d["relative_to"] == ["national"] and d["grain"] == ["national", "territory"]
    assert d["territories"] == ["like_for_like"]
    assert (d["first_week"], d["last_week"]) == (EVENTFUL, EVENTFUL) and d["comparison"] == []  # weeks filled from the query
    assert "Measure: new patients (NBRx)." in brief_["definition_words"] and "Holiday weeks are left out." in brief_["definition_words"]
    assert brief_["claims"][0]["labels"]["measure"] == "nbrx" and "new patients (NBRx)" in brief_["answer"]
    # the same request again is the same brief; the default definition is a different one
    assert analyst.post("/api/briefing/query", json=body).json()["brief_id"] == brief_["brief_id"]
    plain = analyst.post("/api/briefing/query", json=QUERY).json()
    assert plain["brief_id"] != brief_["brief_id"] and plain["definition"]["measure"] == ["trx"]
    assert plain["definition"]["grain"] == GRAINS and "new patients" not in plain["answer"].lower()
    stored = analyst.get(f"/api/briefing/{brief_['brief_id']}").json()
    assert stored["definition"] == d
    # the leader sees it in words in the Assumptions block, and never the claims, args or SQL
    assert analyst.post(f"/api/briefing/{brief_['brief_id']}/review", json={"decision": "approved"}).status_code == 200
    leader = _client(tmp_path, monkeypatch, "dev-director")
    seen = leader.get(f"/api/briefing/{brief_['brief_id']}").json()
    assert seen["view"] == "leadership" and seen["definition"] == d
    assert "Territory changes are set against: the national change." in seen["definition_words"]
    assumptions = next(s for s in seen["sections"] if s["number"] == "6")["text"]
    assert "Brief definition, changed from the pre-selected values" in assumptions and "new patients (NBRx)" in assumptions
    assert "claims" not in seen and "evidence" not in seen
    assert "select " not in json.dumps(seen).lower() and "labels" not in json.dumps(seen)


@needs_db
def test_a_two_comparison_brief_round_trips(tmp_path, monkeypatch):
    analyst = _client(tmp_path, monkeypatch)
    body = {**QUERY, "territory_id": "SOUTHEAST", "definition": {"comparison": [{"kind": "previous", "weeks": 4}, {"kind": "pre_launch"}]}}
    r = analyst.post("/api/briefing/query", json=body)
    assert r.status_code == 200, r.text
    got = r.json()
    assert [c["kind"] for c in got["definition"]["comparison"]] == ["previous", "pre_launch"]
    assert got["comparison"]["kind"] == "previous"  # the top-level comparison is the primary alone
    assert any("four weeks before Metacora launched (2026-02-02 to 2026-02-23)" in w for w in got["definition_words"])
    # a period that starts before the launch is refused for the pre-launch comparison
    early = {**QUERY, "week_start": "2026-02-16", "definition": {"comparison": [{"kind": "pre_launch"}]}}
    bad = analyst.post("/api/briefing/query", json=early)
    assert bad.status_code == 400 and "competitor launch" in bad.text


@needs_db
def test_the_old_comparison_field_still_works_and_the_definition_wins_when_both_are_given(tmp_path, monkeypatch):
    analyst = _client(tmp_path, monkeypatch)
    r = analyst.post("/api/briefing/query", json={**QUERY, "comparison": {"kind": "previous", "weeks": 6}})
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["comparison"] == {"kind": "previous", "weeks": 6, "start": None, "end": None}
    assert got["definition"]["comparison"] == [got["comparison"]]
    assert "Comparison: the previous six weeks." in got["definition_words"]
    # null in the definition is the default comparison, so the query's comparison fills it
    nulled = analyst.post("/api/briefing/query", json={**QUERY, "comparison": {"kind": "previous", "weeks": 6}, "definition": {"comparison": None}}).json()
    assert nulled["definition"]["comparison"] == [got["comparison"]]
    # a definition comparison beside a top-level one: the definition wins
    wins = analyst.post("/api/briefing/query", json={**QUERY, "comparison": {"kind": "previous", "weeks": 6},
                                                     "definition": {"comparison": [{"kind": "previous", "weeks": 3}]}}).json()
    assert wins["comparison"]["weeks"] == 3 and wins["definition"]["comparison"][0]["weeks"] == 3


@needs_db
def test_the_triage_route_builds_the_plan_under_the_definition(tmp_path, monkeypatch):
    analyst = _client(tmp_path, monkeypatch)
    r = analyst.post("/api/briefing/triage", json={**QUERY, "definition": {"grain": ["territory"]}})
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["definition"]["grain"] == ["territory"] and all(c["kind"] != "competitor" for c in plan["stories"])
    brief_ = analyst.post("/api/briefing/query", json={**QUERY, "definition": {"grain": ["territory"]},
                                                       "triage": {"plan_id": plan["plan_id"], "stories": [c["id"] for c in plan["stories"] if c["proposed"] == "investigate"][:1]}})
    assert brief_.status_code == 200, brief_.text
    assert "This is a continuing story" not in brief_.json()["answer"]


@needs_db
def test_the_scope_route_proposes_a_definition(tmp_path, monkeypatch):
    analyst = _client(tmp_path, monkeypatch)
    r = analyst.post("/api/briefing/scope", json={"question": "How many new patients did Pacific add in the week of 2026-08-24?"})
    assert r.status_code == 200, r.text
    body = r.json()
    d = body["definition"]
    assert (d["first_week"], d["last_week"]) == (body["week_start"], body["week_end"]) == (EVENTFUL, EVENTFUL)
    assert d["comparison"] == [{"kind": "previous", "weeks": 4, "start": None, "end": None}] and d["measure"] == ["nbrx"]
    assert d["territories"] == ["like_for_like"] and d["grain"] == GRAINS and d["relative_to"] == ["other_territories"]
    plain = analyst.post("/api/briefing/scope", json={"question": "What changed in the week of 2026-08-24?"}).json()["definition"]
    assert plain["measure"] == ["trx"]
    both = analyst.post("/api/briefing/scope", json={"question": "Show TRx and new patients for the week of 2026-08-24"}).json()["definition"]
    assert both["measure"] == ["trx", "nbrx"]
    pre = analyst.post("/api/briefing/scope", json={"question": "Compare the week of 2026-08-24 with the weeks before Metacora launched"}).json()["definition"]
    assert pre["comparison"] == [{"kind": "pre_launch", "weeks": None, "start": None, "end": None}]
    early = analyst.post("/api/briefing/scope", json={"question": "Compare the week of 2025-06-02 with the weeks before Metacora launched"}).json()
    assert early["definition"]["comparison"][0]["kind"] == "previous" and any("pre-launch" in n for n in early["notes"])


def test_a_models_proposed_selectors_are_checked_and_never_an_error():
    from pharmagentics.api import service

    notes: list[str] = []
    d = service.proposed_definition("2026-08-24", "2026-08-24", 6, False,
                                    {"measure": "nbrx", "territories": "everything", "grain": ["territory", "plan"], "relative_to": ["none", "national"]}, notes)
    assert (d["measure"], d["territories"], d["grain"], d["relative_to"]) == (["nbrx"], ["like_for_like"], ["territory", "plan"], ["none", "national"])
    assert d["comparison"] == [{"kind": "previous", "weeks": 6, "start": None, "end": None}] and notes and "territories" in notes[0]
    assert service.proposed_definition("2026-08-24", "2026-08-24", 4, False, {"measure": "both"}, [])["measure"] == ["trx", "nbrx"]
    n2: list[str] = []
    assert service.proposed_definition("2026-08-24", "2026-08-24", 4, False, {"grain": ["moon"]}, n2)["grain"] == GRAINS and n2
    assert service.proposed_definition("2026-08-24", "2026-08-24", 4, True, {}, []) is None  # the release-wide Promotion review
