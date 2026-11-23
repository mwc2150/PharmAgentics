# pharmagentics rules

- Tools read data only through the governed views over `data/agent_visible/` (DuckDB). Never read `raw` tables for metrics.
- No digit in a generated brief or report comes from a language model. Numbers are claim tokens filled by code from a stored SQL query, so every number stays traceable.
- Never import the eval package or open files under `eval/`.
- `api/roles.json` holds the roles; the server strips evidence from leadership responses.
- `.dockerignore` is an allow-list: a new top-level path the app needs at runtime must be added there and to the Dockerfile.
- The first line of a module docstring is its entry in the code map (`uv run python -m pharmagentics.devtools.codemap`, printed on demand). Give every new module one.
