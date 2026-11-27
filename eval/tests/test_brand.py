"""The brand a case is about (Cardiovela BXA, Lipidara BXC): the case field, the loader and fingerprint, the importer, the
skip rule for a system without that brand, and the per-brand pooled metrics. A run on BXA alone must stay what it was."""
import hashlib
import re

import mlflow
import pytest
import yaml

from eval.harness import importer
from eval.harness.cases import Case, golden_fingerprint, load_cases
from eval.harness.envelope import AnswerEnvelope
from eval.harness.integrity import BRIEFING_STORIES, LIPIDARA_STORIES, check_facts, id_problems
from eval.harness.paths import DATABASE, GOLDEN_DIR
from eval.harness.run import run_suite
from eval.harness.systems import SYSTEMS, BriefingScripted, brand_option

PERSONA_QUESTIONS = {f"P{p}-Q{q}" for p in range(1, 5) for q in range(1, 7)}


def _draft(brand: str | None = None, **extra) -> Case:
    data = yaml.safe_load((GOLDEN_DIR / "briefing" / "P1-Q1.yaml").read_text(encoding="utf8"))
    if brand:
        data["brand"] = brand
    return Case.model_validate({**data, **extra})


# ---- the case field and the loader -----------------------------------------------------------------------------------

def test_a_case_with_no_brand_is_bxa_and_its_inputs_are_unchanged():
    case = _draft()
    assert case.brand == "BXA"
    assert "brand" not in case.inputs()  # a Cardiovela row is exactly the row it always was


def test_a_bxc_case_sends_its_brand_to_the_system():
    assert _draft("BXC").inputs()["brand"] == "BXC"


def test_an_unknown_brand_is_refused():
    with pytest.raises(ValueError):
        _draft("BXZ")


def test_the_loader_defaults_to_bxa_so_every_older_caller_reads_what_it_always_read():
    assert {c.brand for c in load_cases()} == {"BXA"}
    assert len(load_cases()) == 50
    assert {c.brand for c in load_cases(brand="BXC")} == {"BXC"}
    assert len(load_cases(brand="all")) == 50 + 24


def test_there_is_one_lipidara_case_per_persona_question_with_its_own_id():
    cases = load_cases("briefing", brand="BXC")
    assert {c.story for c in cases} == LIPIDARA_STORIES
    assert {c.story.removeprefix("BXC-") for c in cases} == PERSONA_QUESTIONS
    assert len({c.id for c in load_cases(brand="all")}) == 74  # no id is used twice across brands
    assert sorted(c.id for c in cases) == [f"C-{n:03d}" for n in range(33, 57)]
    assert not LIPIDARA_STORIES & BRIEFING_STORIES  # a Lipidara story never answers to a Cardiovela story id
    assert id_problems(load_cases(brand="all")) == []


def test_lipidara_cases_are_drafts_for_michael_to_review():
    for c in load_cases("briefing", brand="BXC"):
        assert (c.split, c.status) == ("dev", "draft"), c.story
        assert c.source == f"docs/planning/user-stories-lipidara.md#{c.story}"
        assert all(not f.reviewed for f in c.facts) and all(not f.reviewed for f in c.findings), c.story
        assert c.must_say is None or not c.must_say.reviewed, c.story
        scope = c.expected_scope()  # the definition states the weeks the question's own prefix names, as for Cardiovela
        assert (c.definition.first_week, c.definition.last_week) == (scope.week_start, scope.week_end), c.story


def test_asking_for_a_story_of_the_other_brand_selects_nothing():
    assert load_cases("briefing", ["BXC-P1-Q1"]) == []  # the default brand is BXA
    assert [c.id for c in load_cases("briefing", ["BXC-P1-Q1"], brand="BXC")] == ["C-033"]


def test_the_cardiovela_fingerprint_ignores_lipidara_files():
    names = sorted(p for p in (GOLDEN_DIR / "briefing").glob("*.yaml") if not p.name.startswith("BXC-"))
    digest = hashlib.sha256()
    for path in names:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    assert golden_fingerprint("briefing") == digest.hexdigest()[:12]
    assert golden_fingerprint("briefing") != golden_fingerprint("briefing", brand="BXC")
    assert golden_fingerprint("briefing", brand="all") not in (golden_fingerprint("briefing"), golden_fingerprint("briefing", brand="BXC"))


@pytest.mark.skipif(not DATABASE.exists(), reason="build it with: uv run python src/pharmagentics/data/load_duckdb.py")
def test_every_lipidara_fact_recomputes_from_the_data():
    cases = load_cases(brand="BXC")
    bad = [r for r in check_facts(cases) if not r.ok]
    assert not bad, "\n".join(f"{r.case} {r.fact}: golden {r.expected!r}, data {r.actual!r}" for r in bad)
    assert sum(len(c.facts) for c in cases) > 200


# ---- which system answers for which brand ----------------------------------------------------------------------------

def test_only_the_scripted_briefing_baseline_and_the_reference_control_support_lipidara():
    assert {name for name, cls in SYSTEMS.items() if "BXC" in cls.brands} == {"reference", "briefing_scripted"}
    for name in ("briefing_agent", "briefing_lowcode", "naive_llm", "forecast_scripted", "forecast_rules", "forecast_agent",
                 "forecast_investigator"):
        assert SYSTEMS[name].brands == ("BXA",), name


def test_a_brand_goes_to_a_system_as_brand_id_only_for_a_brand_other_than_bxa():
    def takes(question, brand_id="BXA"): ...
    def old(question): ...
    assert brand_option(takes, "BXC") == {"brand_id": "BXC"}
    assert brand_option(takes, "BXA") == {} and brand_option(takes, None) == {}  # Cardiovela's call is untouched
    assert brand_option(old, "BXC") == {}


def test_the_scripted_baseline_passes_the_brand_to_the_engine():
    seen = {}

    def answer(question, db=None, brand_id="BXA", **options):
        seen.update(brand_id=brand_id, **options)
        return {"system": "briefing_scripted", "answer": "x"}

    system = object.__new__(BriefingScripted)
    system._answer = answer
    system.predict("q", brand_id="BXC")
    assert seen["brand_id"] == "BXC"
    system.predict("q")
    assert seen["brand_id"] == "BXA"


# ---- the run: skip, select, label, per-brand metrics -----------------------------------------------------------------

class _Stub:
    """A system that answers every question with nothing, and says which brands it supports."""

    name = "stub"
    uses_llm = False
    returns_evidence = False
    brands = ("BXA",)
    calls: list = []

    def __init__(self, cases):
        _Stub.calls = []

    def predict(self, question: str) -> dict:
        _Stub.calls.append((question, None))
        return AnswerEnvelope(system="stub", answer="nothing").model_dump()


class _StubBoth(_Stub):
    name = "stub_both"
    brands = ("BXA", "BXC")

    def predict(self, question: str, brand_id: str | None = None) -> dict:  # None: the harness passed no brand
        _Stub.calls.append((question, brand_id))
        return AnswerEnvelope(system="stub_both", answer="nothing").model_dump()


@pytest.fixture
def stubs(monkeypatch, tmp_path):
    monkeypatch.setitem(SYSTEMS, "stub", _Stub)
    monkeypatch.setitem(SYSTEMS, "stub_both", _StubBoth)
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    return uri, tmp_path / "artifacts", mlflow.MlflowClient(uri)


def _run(client, run_id):
    return client.get_run(run_id)


def test_a_case_for_a_brand_the_system_lacks_is_skipped_not_run_and_not_an_error(stubs):
    uri, artifacts, client = stubs
    run_id = run_suite("stub", "briefing", stories=["P1-Q1", "BXC-P1-Q1"], brand="all", uri=uri, experiment="skip", artifacts=artifacts)
    run = _run(client, run_id)
    assert [q for q, _ in _Stub.calls] == [load_cases("briefing", ["P1-Q1"])[0].question]  # only the Cardiovela case ran
    assert run.data.params["skipped_cases"] == "C-033" and run.data.params["cases"] == "1"
    assert run.data.metrics["cases_skipped"] == 1.0 and run.data.metrics["run_errors/mean"] == 0.0
    assert run.data.tags["system"] == "stub@BXA+BXC"  # a mixed run is its own system row, never Cardiovela's
    assert [a.path for a in client.list_artifacts(run_id)] == ["skipped_cases.txt"]


def test_when_nothing_is_supported_the_run_records_the_skip_and_runs_nothing(stubs):
    uri, artifacts, client = stubs
    run_id = run_suite("stub", "briefing", stories=["BXC-P1-Q1", "BXC-P2-Q1"], brand="BXC", uri=uri, experiment="none", artifacts=artifacts)
    run = _run(client, run_id)
    assert _Stub.calls == []
    assert run.data.metrics["cases_skipped"] == 2.0 and "run_errors/mean" not in run.data.metrics
    assert run.data.params["cases"] == "0" and run.data.params["skipped_cases"] == "C-033,C-039"
    assert run.data.tags["system"] == "stub@BXC"
    exp = client.get_experiment_by_name("none").experiment_id
    assert client.search_runs([exp], filter_string=f"tags.mlflow.parentRunId = '{run_id}'") == []  # no rerun, nothing scored


def test_a_bxa_only_run_logs_what_it_always_logged(stubs):
    uri, artifacts, client = stubs
    run_id = run_suite("stub", "briefing", stories=["P1-Q1"], uri=uri, experiment="bxa", artifacts=artifacts)
    run = _run(client, run_id)
    assert run.data.tags["system"] == "stub" and run.data.params["system"] == "stub"
    assert not {"brand", "skipped_cases"} & set(run.data.params)
    assert "cases_skipped" not in run.data.metrics
    assert not [k for k in run.data.metrics if k.endswith(("_bxa", "_bxc"))]
    assert run.data.params["golden_version"] == golden_fingerprint("briefing")


def test_the_default_brand_is_bxa_so_a_lipidara_story_needs_the_brand(stubs):
    uri, artifacts, _ = stubs
    with pytest.raises(SystemExit):
        run_suite("stub", "briefing", stories=["BXC-P1-Q1"], uri=uri, experiment="default", artifacts=artifacts)


def test_the_brand_filter_selects_cases_and_a_mixed_run_logs_per_brand_pooled_metrics(stubs):
    uri, artifacts, client = stubs
    run_id = run_suite("stub_both", "briefing", stories=["P1-Q1", "BXC-P1-Q1", "BXC-P1-Q2"], brand="all", uri=uri, experiment="mixed", artifacts=artifacts)
    run = _run(client, run_id)
    assert sorted(b or "" for _, b in _Stub.calls) == ["", "BXC", "BXC"]  # brand_id reaches the engine for Lipidara only
    assert run.data.tags["system"] == "stub_both@BXA+BXC" and run.data.params["brand"] == "BXA+BXC"
    metrics = run.data.metrics
    for key in ("key_fact_recall_pooled", "key_fact_recall_pooled_bxa", "key_fact_recall_pooled_bxc"):
        assert key in metrics, key
    assert "cases_skipped" not in metrics
    only = run_suite("stub_both", "briefing", stories=["BXC-P1-Q1"], brand="BXC", uri=uri, experiment="bxc", artifacts=artifacts)
    assert _run(client, only).data.tags["system"] == "stub_both@BXC"
    assert not [k for k in _run(client, only).data.metrics if k.endswith(("_bxa", "_bxc"))]  # one brand: the plain metrics are its own


# ---- the importer ----------------------------------------------------------------------------------------------------

STORY = """# **Part A. Briefing Agent personas, Lipidara (BXC)**
## **P1 · Commercial Analyst (Ace)**
### **BXC-P1-Q1 · Do the numbers tie out?**
*As Ace, I want it to tie out.*
  - **Answer from the data (week of 2026-07-06).** Great Lakes BXC TRx is 615.
  - **Given** a duplicate. **When** the brief runs. **Then** it is withheld.
  - **Must not say** "Great Lakes BXC TRx was 670."
  - **Action.** Ace checks.
  - **Eval items** EV-1.1.
# **Coverage and gaps**
| Question | Anchor | Eval items | Stage |
| :- | :- | :- | :- |
| BXC-P1-Q1 | Great Lakes duplicates | EV-1.1 | 2 |
"""


def test_the_importer_drafts_a_lipidara_case_after_the_highest_id_and_never_overwrites(tmp_path, monkeypatch):
    golden = tmp_path / "golden"
    (golden / "briefing").mkdir(parents=True)
    (golden / "briefing" / "P1-Q1.yaml").write_text("id: C-032\nlane: briefing\nstory: P1-Q1\n", encoding="utf8")
    stories = tmp_path / "docs" / "planning" / "user-stories-lipidara.md"
    stories.parent.mkdir(parents=True)
    stories.write_text(STORY, encoding="utf8")
    monkeypatch.setattr(importer, "GOLDEN_DIR", golden)
    monkeypatch.setattr(importer, "REPO_ROOT", tmp_path)
    monkeypatch.setitem(importer.STORY_FILES, "BXC", stories)
    assert importer.run(brand="BXC") == ["BXC-P1-Q1"]
    written = yaml.safe_load((golden / "briefing" / "BXC-P1-Q1.yaml").read_text(encoding="utf8"))
    assert (written["id"], written["brand"], written["story"], written["lane"]) == ("C-033", "BXC", "BXC-P1-Q1", "briefing")
    assert written["category"] == "data_artifact"  # the persona question's category, BXC- prefix stripped
    assert written["source"] == "docs/planning/user-stories-lipidara.md#BXC-P1-Q1"
    assert written["question"].startswith("Week of 2026-07-06: ")
    # a hand edit survives a second run
    path = golden / "briefing" / "BXC-P1-Q1.yaml"
    path.write_text(path.read_text(encoding="utf8") + "review_note: edited by hand\n", encoding="utf8")
    assert importer.run(brand="BXC") == []
    assert path.read_text(encoding="utf8").endswith("review_note: edited by hand\n")
    assert (golden / "briefing" / "P1-Q1.yaml").read_text(encoding="utf8").startswith("id: C-032")  # the Cardiovela file is untouched


def test_the_cardiovela_importer_still_numbers_from_one():
    stories, _ = importer.parse((GOLDEN_DIR.parent.parent / "docs" / "planning" / "user-stories.md").read_text(encoding="utf8"))
    assert "P1-Q1" in stories and not [s for s in stories if s.startswith("BXC-")]
    assert re.fullmatch(r"C-\d{3}", importer.build_case(stories["P1-Q1"], 1, "x")["id"])
    assert "brand" not in importer.build_case(stories["P1-Q1"], 1, "x")  # a Cardiovela file has no brand line, as before


# ---- the positive control, on the Lipidara cases ---------------------------------------------------------------------

import inspect  # noqa: E402

from eval.harness.scorers import DETERMINISTIC, key_fact_counts, must_say_recall  # noqa: E402

LIPIDARA = load_cases("briefing", brand="BXC")


def _run_scorer(s, **kwargs):
    wanted = inspect.signature(getattr(s, "_original_func", s)).parameters
    return s(**{k: v for k, v in kwargs.items() if k in wanted})


@pytest.mark.parametrize("case", LIPIDARA, ids=lambda c: c.story)
def test_a_lipidara_golden_answer_passes_every_code_check_and_states_every_must_fact(case):
    outputs = {"system": "test", "answer": case.reference_answer}
    for s in DETERMINISTIC:
        fb = _run_scorer(s, inputs={"question": case.question}, outputs=outputs, expectations=case.expectations())
        assert fb.value in (True, 1.0), f"{s.name}: {fb.rationale}"
    stated, missing, total = key_fact_counts(outputs, case.expectations())
    assert stated == total, f"{case.story}: the reference does not state {missing}"
    if case.must_say:
        assert must_say_recall(outputs=outputs, expectations=case.expectations()).value == 1.0, case.story
    for f in case.expectations()["key_facts"]:  # an integer 0 to 10 is a value no brief can be credited for
        assert not (isinstance(f["value"], int) and abs(f["value"]) <= 10), (case.id, f["id"])
