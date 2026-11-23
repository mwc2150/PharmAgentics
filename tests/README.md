# Tests

Most files here are data-foundation, tools, API, RBAC, classification and briefing smoke tests. `test_codemap.py` and `test_status.py` cover the two developer commands.

- `test_*.py`: unit and integration tests for the data layer, tools, API, RBAC, classification, briefing smoke, and the forecast and feedback features.
- `ui/`: Bombadil UI checks (`run_bombadil.py`, `bombadil.spec.ts`, `setup_wsl.sh`). See `ui/` for setup on WSL.
- `fixtures/scripted_answers.json`: a recorded fixture of about 93k tokens. Search it with `grep` or `rg`; never load it whole.

## Running

- `uv run pytest` runs the suite. CI runs `uv run python -m unittest discover -s tests -v`, so prefer `unittest.TestCase` for new tests. Plain pytest functions run under pytest but unittest discovery skips them.
- Most tests need the DuckDB built first: `uv run python src/pharmagentics/data/load_duckdb.py`.
- Eval tests live in `eval/tests/`, not here.
