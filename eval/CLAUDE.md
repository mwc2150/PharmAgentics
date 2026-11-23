@README.md

# eval rules

- The golden cases are an answer key. Nothing in `src/` or `agents/` imports `eval/` or opens its files; `eval/tests/test_isolation.py` enforces this.
- Ground truth lives outside the repo. Only `eval/harness/store.py` reads `PHARMAGENTICS_EVAL_STORE`, and only for evaluation work the user asks for.
- LLM judges are report-only until their agreement with human labels clears the bar (Evaluation Pack open item 2). Never gate a merge on a judge score.
- Controls: `--system reference` must score 1.0 on every code check; `--system naive_llm` must fail the numeric checks.
- No change merges if a gated check regresses (Briefing B-VII): `uv run python -m eval gate <candidate-run-id> <baseline-run-id>`.
- A new system plugs in through `eval/harness/systems.py` and returns the contract in `eval/harness/envelope.py`: answer text, claims, evidence items.
- MLflow telemetry stays off in `eval/__init__.py`: it sends usage data to an external service and deadlocks parallel scorer threads in MLflow 3.17.
- The Forecast golden cases and FE scorers are drafts until Alvin and Sienna confirm them.
- A change to a golden case is recorded as a new file in `eval/golden/changes/`, not as a row in `eval/golden/CHANGELOG.md`.
