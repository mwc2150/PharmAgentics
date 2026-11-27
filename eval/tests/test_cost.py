"""The estimated model cost of a run (harness/cost.py): list prices, cache reads and writes, local models free."""
import pytest

from eval.harness.cost import answer_cost, usage_metrics

HAIKU = "anthropic:claude-haiku-5-5"


def test_an_answer_without_the_cache_costs_input_plus_output():
    # one million input tokens at $0.10 and one million output tokens at $0.50
    t = {"model": HAIKU, "tokens": {"input": 1_000_000, "output": 1_000_000, "cache_read": 0, "cache_write": 0}}
    assert answer_cost(t) == pytest.approx(0.60)


def test_cache_reads_cost_a_tenth_and_writes_a_quarter_more():
    # of 1,000,000 input tokens, 600,000 read from the cache and 200,000 written to it; 200,000 fresh
    t = {"model": HAIKU, "tokens": {"input": 1_000_000, "output": 0, "cache_read": 600_000, "cache_write": 200_000}}
    assert answer_cost(t) == pytest.approx(0.2 * 0.10 + 0.2 * 0.10 * 1.25 + 0.6 * 0.01)


def test_an_answer_from_before_cache_counts_still_prices():
    assert answer_cost({"model": HAIKU, "tokens": {"input": 2_000_000, "output": 0}}) == pytest.approx(0.20)


def test_a_local_model_is_free_and_an_unknown_one_has_no_estimate():
    tokens = {"input": 5000, "output": 500}
    assert answer_cost({"model": "ollama:qwen3:4b-instruct-2507-q4_K_M", "tokens": tokens}) == 0.0
    assert answer_cost({"model": "gemini:gemini-3-flash", "tokens": tokens}) is None
    assert answer_cost({"model": HAIKU, "tokens": {}}) is None


def test_run_metrics_average_over_answers_with_tokens_and_total_the_rerun():
    answers = [
        {"trajectory": {"model": HAIKU, "tokens": {"input": 100_000, "output": 10_000, "cache_read": 50_000, "cache_write": 0}}},
        {"trajectory": {"model": HAIKU, "tokens": {"input": 300_000, "output": 30_000, "cache_read": 150_000, "cache_write": 0}}},
        {"answer": "a scripted answer has no trajectory"},
    ]
    m = usage_metrics(answers)
    assert m["tokens_input/mean"] == 200_000 and m["tokens_output/mean"] == 20_000
    assert m["cache_read_share"] == pytest.approx(0.5)
    first = (50_000 * 0.10 + 50_000 * 0.01 + 10_000 * 0.50) / 1e6
    assert m["cost_usd_rerun"] == pytest.approx(4 * first) and m["cost_usd_brief/mean"] == pytest.approx(2 * first)


def test_a_run_with_no_model_logs_no_usage():
    assert usage_metrics([{"answer": "x"}, {"trajectory": {"tokens": {"input": 0, "output": 0}}}]) == {}
