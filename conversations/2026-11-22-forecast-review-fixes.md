# 2026-11-22: review fixes, Forecast lane and shared guards (Sienna, Claude Opus)

Branch `fix/forecast-review-2026-11-22` from `main` 758b4d0. Not committed or pushed.

## What changed

Forecast lane (fcst-002 FR-016, FR-017):
- `src/pharmagentics/api/forecast.py`: `_rerun_scope` checks a rerun follow-up's territory (an id, a name or NATIONAL), weeks (ISO dates, snapped to Mondays, inside the release) and dropped controls before the engine runs; a bad scope answers in words (`op: help`) and runs nothing. Background threads register as live (`forecast_store.hold` / `held`); follow-ups record `started_at`.
- `agents/forecast-explanation/forecast_agent/engine.py`: `Case` refuses an unknown cut or a non-ISO week; `split` accepts only a payer channel the data holds (it was interpolated into SQL from the model's `within_channel`). `scope.py`: repeated weeks collapse.
- `src/pharmagentics/api/forecast_store.py`: one `LOCK` around every read-modify-write (`mutate`); `updated_at` on every save; `get` and `all_runs` mark an investigation or follow-up that no thread here holds and that has been silent for 120 s (or any silent for an hour) as failed. `forecast_reports.py` does the same for a draft stuck in `drafting`.

Shared (for Michael and Meghna to review):
- `src/pharmagentics/tools/registry.py`: `check_sql` walks DuckDB's `json_serialize_sql` tree; it refuses table functions, unqualified names (except the query's own CTEs), and anything outside `ALLOWED`. `enable_external_access=False` on the Registry connection was tried and dropped: DuckDB refuses a second connection to one file with a different config, and the eval scorers open the file plainly in the same process.
- `digits_outside_tokens`: a digit-first word is a typed number; letter-first identifiers and hex hashes of 8+ characters still pass.
- `.github/workflows/data-foundation.yml`: the integration job syncs every group and runs `pytest -q` (all testpaths) with `FORECAST_AGENT_MODEL=rules`; the eval job runs `python -m eval check`. The `api` job is unchanged and now redundant; it was kept in case branch protection names it.

## Results

- `uv run pytest`: 848 passed, 10 subtests, with `OLLAMA_HOST` pointed at a dead port (as in CI). About 17 minutes locally; the slowest test is the scripted Briefing baseline (222 s).
- Gates (exit 0, seven gated checks at 1.000): forecast_rules `227ed325…` vs `e307d1aa…`; briefing_scripted `4bf4fd7f…` vs `360ca41f…`. Full IDs in PROJECT_STATE.md.

## Open

- Run the Haiku Briefing agent on the stricter digit check (it may now send back prose that wrote "2nd" or "3x" for revision).
- Eval: `gate()` passes a gated metric missing on one run; `claims_reconcile` runs evidence SQL with no guard.
- A second app instance would need Cloud Storage generation preconditions; the lock is per process (max-instances=1 today).
