"""Regression guard: the live Briefing frontend contains no fictitious prototypes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "figma-make" / "src"


def test_frontend_contains_only_supported_feature_modules():
    assert SRC.is_dir()
    assert sorted(p.relative_to(SRC).as_posix() for p in SRC.rglob("*") if p.is_file()) == [
        "App.tsx",
        "BriefingScope.tsx",
        "ComparisonPicker.tsx",
        "Feedback.tsx",
        "FeedbackReview.tsx",
        "ForecastCharts.tsx",
        "ForecastDrivers.tsx",
        "Memo.tsx",
        "MessageBar.tsx",
        "Overview.tsx",
        "Telemetry.tsx",
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
    assert "useState<Comparison | null>(null)" in app
    assert "setComparison(null)" in app
    assert 'if (value === null) return null' in picker  # the default is always allowed
    assert "There are no earlier weeks in the release to compare with" in picker
    assert "!count || count === Math.min(DEFAULT_COMPARISON_WEEKS, earlier) ? null" in scope
