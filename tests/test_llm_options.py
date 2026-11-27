"""Shared model options: the opt-in switches that turn Claude's thinking off (PHARMAGENTICS_ANTHROPIC_THINKING) and prompt caching on."""
from pharmagentics.llm import ANTHROPIC_MAX_TOKENS, chat_options

HAIKU = "anthropic:claude-haiku-5-5"


def test_claude_requests_are_unchanged_by_default(monkeypatch):
    monkeypatch.delenv("PHARMAGENTICS_ANTHROPIC_THINKING", raising=False)
    assert chat_options(HAIKU) == {"max_tokens": ANTHROPIC_MAX_TOKENS}


def test_the_switch_turns_thinking_off_for_claude_only(monkeypatch):
    for value in ("off", "OFF", "disabled", "0"):
        monkeypatch.setenv("PHARMAGENTICS_ANTHROPIC_THINKING", value)
        assert chat_options(HAIKU)["thinking"] == {"type": "disabled"}
    monkeypatch.setenv("PHARMAGENTICS_ANTHROPIC_THINKING", "off")
    assert "thinking" not in chat_options("ollama:qwen3:4b-instruct-2507-q4_K_M")
    monkeypatch.setenv("PHARMAGENTICS_ANTHROPIC_THINKING", "on")
    assert "thinking" not in chat_options(HAIKU)


def test_prompt_caching_is_opt_in_and_claude_only(monkeypatch):
    """A caller whose model loops over tool calls asks for caching; nobody else gets it (the Forecast lane included)."""
    monkeypatch.delenv("PHARMAGENTICS_ANTHROPIC_CACHE", raising=False)
    monkeypatch.delenv("PHARMAGENTICS_ANTHROPIC_THINKING", raising=False)
    assert "cache_control" not in chat_options(HAIKU)
    assert chat_options(HAIKU, cache=True) == {"max_tokens": ANTHROPIC_MAX_TOKENS, "cache_control": {"type": "ephemeral"}}
    assert "cache_control" not in chat_options("ollama:qwen3:4b-instruct-2507-q4_K_M", cache=True)


def test_the_cache_switch_turns_caching_off_everywhere(monkeypatch):
    for value in ("off", "OFF", "disabled", "0"):
        monkeypatch.setenv("PHARMAGENTICS_ANTHROPIC_CACHE", value)
        assert "cache_control" not in chat_options(HAIKU, cache=True)
