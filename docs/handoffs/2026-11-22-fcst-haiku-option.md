# 2026-11-22 Forecast: Claude Haiku as an internal trial model

Sienna, with Claude Opus. Docs only, committed straight to `main` (from `3f36238`, merged with `b804ca1`).

## Decision

The Forecast model is chosen internally, like Briefing's `PHARMAGENTICS_AGENT_MODEL`, never by users. The existing `FORECAST_AGENT_MODEL` setting already does this, so no code changed. A per-question model picker was built first and then removed at Sienna's request.

How to switch (restart the app after changing):

- Haiku: `FORECAST_AGENT_MODEL=anthropic:claude-haiku-5-5` plus `ANTHROPIC_API_KEY` in the git-ignored `.env`, or exported before `docker compose up`.
- Local Qwen 3 4B (default): leave `FORECAST_AGENT_MODEL` unset with Ollama running.
- No model: `FORECAST_AGENT_MODEL=rules`.

## Results (data version unchanged)

| Reader on the forty paraphrases | Fully right | Seconds a question | Run |
|---|---|---|---|
| Keyword rules | 37.5% | 0 | earlier run, same code |
| Qwen 3 4B, local | 92.5% | 10.5 | `300ab924` |
| Claude Haiku 5.5 | 97.5% | 1.9 | `301b4800` |

Both models leave the same 12 clear questions to code. Golden set with Haiku: `accf8a276cbb43d6bbb741a8edcc6164`, seven gated checks 1.000, golden number recall 0.593 (rules 0.592), about 11 s a question; `eval gate accf8a27… 227ed325…` exit 0. The asyncio "Event loop is closed" message after the Anthropic runs is client cleanup at exit, not a failure. Driver recovery was not rerun: the rules investigate by default.

## Changed

- `specs/fcst-002-question-driven-agent/spec.md`: SC-004 rerun recorded; its open item for a Haiku rerun is resolved.
- `agents/forecast-explanation/README.md`: how to try Haiku internally, with the measured numbers.
- `PROJECT_STATE.md`: entry at the top.

## Open

- Alvin: whether Haiku replaces Qwen once the designs are set (the team default stays Qwen until then).
- Hosted app: setting `FORECAST_AGENT_MODEL` there bills the app's Anthropic secret (the team key from `gcp.py anthropic-key`, Michael's). Agree with Michael first.
