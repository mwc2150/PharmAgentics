"""Estimated model cost of the answers in a run, from the token counts each answer's trajectory carries (report only).

Anthropic first-party list prices, US dollars per million tokens (as of 2026-11-27). A cache read costs a tenth of the
input price on Haiku 5.5 and a twentieth on Opus 5.5 and Sonnet 5.5; a five-minute cache write costs a quarter more than
input. Haiku 5.5 bills a prompt over 100K tokens at a higher rate; a trajectory sums its tokens over all its calls, so
that tier cannot be applied and the estimate is a floor for such prompts. A local model costs nothing; a model without a
price here gets no estimate. Never gated: what an answer costs is a fact to watch, not a score.
"""
from __future__ import annotations

from typing import Iterable

# model id: (input, output, cache read), dollars per million tokens
PRICES: dict[str, tuple[float, float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
}
CACHE_WRITE = 1.25  # times the input price, five-minute cache


def answer_cost(trajectory: dict) -> float | None:
    """Dollars for one answer, or None when its model has no price here or it carries no token counts."""
    tokens = trajectory.get("tokens") or {}
    provider, _, model = str(trajectory.get("model") or "").partition(":")
    if provider == "ollama":
        return 0.0
    if model not in PRICES or not tokens:
        return None
    price_in, price_out, price_read = PRICES[model]
    read, write = tokens.get("cache_read", 0), tokens.get("cache_write", 0)
    fresh = max(0, tokens.get("input", 0) - read - write)  # "input" counts every input token, cached or not
    return (fresh * price_in + write * price_in * CACHE_WRITE + read * price_read + tokens.get("output", 0) * price_out) / 1e6


def usage_metrics(outputs: Iterable) -> dict[str, float]:
    """Run-level metrics over one rerun's answers: mean input and output tokens an answer, the share of input tokens
    read from the cache, the mean estimated dollars an answer and the rerun's total. Empty when no answer carries token
    counts (the scripted engine calls no model)."""
    rows = []
    for out in outputs:
        t = out.get("trajectory") if isinstance(out, dict) else None
        if isinstance(t, dict) and isinstance(t.get("tokens"), dict) and any(t["tokens"].values()):
            rows.append(t)
    if not rows:
        return {}
    n = len(rows)

    def total(key: str) -> int:
        return sum(t["tokens"].get(key, 0) for t in rows)

    tokens_in = total("input")
    metrics = {"tokens_input/mean": tokens_in / n, "tokens_output/mean": total("output") / n,
               "cache_read_share": total("cache_read") / tokens_in if tokens_in else 0.0}
    costs = [c for c in (answer_cost(t) for t in rows) if c is not None]
    if costs:
        metrics["cost_usd_brief/mean"] = sum(costs) / len(costs)
        metrics["cost_usd_rerun"] = sum(costs)
    return metrics
