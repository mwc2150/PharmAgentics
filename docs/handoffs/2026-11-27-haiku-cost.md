---
branch: feature/haiku-cost
lane: briefing
next: Michael runs deploy/gcp.py telemetry so the Evaluation page shows the v2 scores and the Cost a brief row
---

# Haiku cost: prompt caching and per-run cost, and the v2 evaluation record (2026-11-27)

Based on `main` 76a4145 (v2 merged). The Anthropic credit ran out during the v2 Haiku runs; Michael added $5. This branch makes each brief cheaper and makes every run report what it cost.

## What changed

- **Prompt caching.** `chat_options(spec, cache=True)` (`src/pharmagentics/llm.py`) turns on Anthropic's automatic prompt caching (top-level `cache_control`, passed through Agent Framework). The investigation team (`briefing_agent/investigate.py`) and the follow-up agent ask for it, because they loop over tool calls. One-shot calls (the writer, the question reader) and the Forecast lane do not. `PHARMAGENTICS_ANTHROPIC_CACHE=off` turns it off everywhere. The model sees the same prompt either way.
- **Token counts.** The run log (`briefing_lowcode/team.py` RunLog) also counts cache reads and writes, and the question reader's call now records its tokens.
- **Cost per run.** `eval/harness/cost.py` prices each answer at list prices (Haiku 5.5 $0.10 / $0.50 per million; cache reads a tenth of input, five-minute writes 1.25 times). Each run logs `tokens_input`, `tokens_output`, `cache_read_share`, `cost_usd_brief`, `cost_usd_rerun` and `cost_usd_run`, and prints the total. Report only, never gated.
- **Evaluation page.** The How it works comparison's "Cost a brief" row reads `cost_usd_brief`; the scripted engine shows $0 (it calls no model).
- Tests: `tests/test_llm_options.py` (caching is opt-in, Claude only, switch off), `eval/tests/test_cost.py`, `tests/test_agents_info.py`.

## Measurements

- Caching on two Cardiovela cases, side experiment `pharmagentics-smoke`: $0.0300 without (`2ff1da0d05cc419ab35f27a24c4c24bf`), $0.0245 with (`ef539847419041329587469f6519b9d8`); 32% of input read from the cache; every gated check 1.000 in both. About half of a brief's cost is output (Haiku's thinking), which caching cannot touch.

## The v2 evaluation record (main checkout's MLflow store)

| Run | ID | Result |
| :- | :- | :- |
| `eval check` | | 57 Briefing and 18 Forecast cases; 410 of 410 facts recompute |
| reference, Cardiovela | `ce0123b8a4b5404bacc6a4699a014794` | key facts 1.000, no errors |
| reference, Lipidara | `3a3f1d93f8de4c5f86f473f66244cef2` | key facts 1.000 (finding recall is low by design: reference answers have no story cards) |
| scripted, Cardiovela | `d84fc6d8f49f4497893d449989be5c91` | every gated check 1.000; key facts 1.000, findings 1.000 |
| scripted, Lipidara | `cc9132b1` (export id) | key facts 0.780, findings 0.714 |
| Haiku, Lipidara, 3 passes | `1bfce778cac84ac9923f8ca26495c1a0` | every gated check 1.000, no errors; key facts 0.780, findings 0.714, scope 0.683; $0.50 the run ($0.007 a brief) |
| Haiku, Cardiovela, 3 passes, with caching | `e37a68f7e39741cca8f67433b3214444` | every gated check 1.000, no errors; key facts 1.000, findings 0.971, scope 0.796; $1.11 the run ($0.013 a brief), 34% of input from the cache |

`eval gate e37a68f7e39741cca8f67433b3214444 55bafa9245bf42648ac9c88c5aa9bfe3` (v2's Haiku run without caching) exits 0. The Lipidara run replaces this morning's, whose third pass was void (the credit ran out); it is the Lipidara Haiku baseline. Haiku runs used `MLFLOW_GENAI_EVAL_MAX_WORKERS=4` (about 10 minutes for Lipidara's three passes, 30 for Cardiovela's); the "Event loop is closed" tracebacks in their logs are cleanup noise from earlier runs too, not errors.

`eval export-telemetry` refreshed `src/pharmagentics/api/telemetry.json` from these runs.

## Release (Michael)

`uv run python deploy/gcp.py telemetry --project pharmagentics --account <you>`, so the hosted Evaluation page reads the new snapshot without a redeploy. The app itself deploys on merge.

## Open

- Lipidara recall (0.780 key facts, 0.714 findings) is under the targets (0.85, 0.90) on both engines: the gaps listed in `2026-11-27-lipidara-cases.md` (plan-level card for the Mid-Atlantic Medicare Part D plan, P4-Q3 figures, June share figures, the `data` ruled-out driver).
- Next cost lever, if wanted: lower thinking effort on some calls. It changes what Haiku reasons through, so it needs a full gated run.
- The settings branch (PR #36) also edits `HowItWorks.tsx`; expect a small merge in the comparison table's `show()` when it rebases on this.
