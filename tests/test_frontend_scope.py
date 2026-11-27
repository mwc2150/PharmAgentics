"""Regression guard: the live Briefing frontend contains no fictitious prototypes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "figma-make" / "src"


def test_frontend_contains_only_supported_feature_modules():
    assert SRC.is_dir()
    assert sorted(p.relative_to(SRC).as_posix() for p in SRC.rglob("*") if p.is_file()) == [
        "App.tsx",
        "ApprovedNews.tsx",
        "BriefDefinition.tsx",
        "BriefingScope.tsx",
        "ComparisonPicker.tsx",
        "Feedback.tsx",
        "FeedbackResponses.tsx",
        "FeedbackReview.tsx",
        "ForecastCharts.tsx",
        "ForecastDrivers.tsx",
        "HowItWorks.tsx",
        "Memo.tsx",
        "MessageBar.tsx",
        "Overview.tsx",
        "Promotion.tsx",
        "Telemetry.tsx",
        "Timeline.tsx",
        "agent/briefingApi.ts",
        "agent/feedbackApi.ts",
        "agent/forecastApi.ts",
        "agent/overviewApi.ts",
        "agent/primitives.tsx",
        "agent/reviewApi.ts",
        "agent/telemetryApi.ts",
        "agent/threadApi.ts",
        "components/ui/dropdown-menu.tsx",
        "index.css", "main.tsx", "vite-env.d.ts"
    ]


def test_live_frontend_no_mock_fallback_or_fake_review():
    app = (SRC / "App.tsx").read_text(encoding="utf-8")
    api = (SRC / "agent" / "briefingApi.ts").read_text(encoding="utf-8")
    for s in ["mockAgentService", "mockService", "SEED.runs", "sampleFixture", "sample_fixture", "offline (simulated)"]:
        assert s not in app and s not in api
    assert 'getBriefing({' in app
    assert 'getContext()' in app
    assert 'evidence_id' in app and 'data_version' in app
    assert 'throw new Error("API URL is not configured' in api


def test_the_comparison_defaults_to_none_so_app_briefs_match_the_eval():
    """brief-008 review: the form sends no comparison unless the analyst picks one; the server applies its default."""
    app = (SRC / "App.tsx").read_text(encoding="utf-8")
    picker = (SRC / "ComparisonPicker.tsx").read_text(encoding="utf-8")
    scope = (SRC / "BriefingScope.tsx").read_text(encoding="utf-8")
    assert "DEFAULT_COMPARISON" not in app and "DEFAULT_COMPARISON_WEEKS" not in app
    assert "useState<Comparison[]>([])" in app  # brief-010 FR-000e: a list, empty is the default
    assert "setComparisons([])" in app
    assert 'if (value === null) return null' in picker  # the default is always allowed
    assert "There are no earlier weeks in the release to compare with" in picker
    assert "!count || count === Math.min(DEFAULT_COMPARISON_WEEKS, earlier) ? []" in scope


def test_the_brief_definition_form_sends_the_six_selectors():
    """brief-010 FR-000b: six selectors at the start of the form, pre-selected; the request carries `definition`."""
    app = (SRC / "App.tsx").read_text(encoding="utf-8")
    api = (SRC / "agent" / "briefingApi.ts").read_text(encoding="utf-8")
    picker = (SRC / "BriefDefinition.tsx").read_text(encoding="utf-8")
    memo = (SRC / "Memo.tsx").read_text(encoding="utf-8")
    form = app.split('<form onSubmit={submit}', 1)[1]
    assert form.index("<PeriodPicker") < form.index("<ComparisonPicker") < form.index("<DefinitionPicker")
    # One question box: the message bar reads the question into the form; the form has no box of its own.
    assert "<QuestionReader" not in app and "Read my question" not in (SRC / "BriefingScope.tsx").read_text(encoding="utf-8")
    assert "useQuestionReader" in app and "onRead=" in app and "autoAsk" not in app
    for field in ["first_week", "last_week", "comparison", "territories", "measure", "grain", "relative_to"]:
        assert field in api
    assert "definition:s.definition" in app and "definition?: BriefDefinition | null" in api
    assert 'territories: ["like_for_like"], measure: ["trx"]' in picker and 'relative_to: ["other_territories"]' in picker
    for label in ["Like for like", "All reportable", "Projected national", "NBRx (new patients)", "The other territories", "Nothing"]:
        assert label in picker
    assert "Choose at least one level of detail." in picker
    assert "<DefinitionWords" in memo and "definition={brief.definition}" in app and "definition={result.definition}" in app
    cmp_picker = (SRC / "ComparisonPicker.tsx").read_text(encoding="utf-8")
    assert '["pre_launch", "Pre-launch weeks"]' in cmp_picker and '{ kind: "pre_launch" }' in api
    assert "the four weeks before Metacora launched" in picker
    assert "UAT" not in picker and "persona" not in picker.lower()


def test_every_selector_takes_several_values_and_the_first_is_the_main_one():
    """brief-010 FR-000e: lists on the wire, a Main choice with "Also show beside it" extras (no "primary" in the visible
    UI), grain as plain checkboxes, a single value or a list from the reader."""
    api = (SRC / "agent" / "briefingApi.ts").read_text(encoding="utf-8")
    picker = (SRC / "BriefDefinition.tsx").read_text(encoding="utf-8")
    cmp_picker = (SRC / "ComparisonPicker.tsx").read_text(encoding="utf-8")
    scope = (SRC / "BriefingScope.tsx").read_text(encoding="utf-8")
    for line in ["comparison?: Comparison[] | null", "territories: TerritoriesCounted[]", "measure: MeasureChoice[]",
                 "grain: GrainLevel[]", "relative_to: RelativeTo[]", 'MeasureChoice = "trx" | "nbrx"']:
        assert line in api
    assert "OneOrMany" in api and '"both"' in api  # the reader may send one value, a list or the old "both"
    assert "Also show beside it" in picker and "Main" in picker and "; also " in picker
    assert "Make primary" not in picker + cmp_picker and "(primary)" not in picker and "asList(def.measure" in picker
    assert "Default: the" in cmp_picker and "Main comparison" in cmp_picker and "Also compare with" in cmp_picker
    assert "Choose at least one measure." in picker
    assert "Choose each comparison once." in cmp_picker
    assert "proposedComparisons" in scope
