# 2026-11-23 — Governed views stored as tables (core-001 FR-003a)

Why: a scripted brief spent about 11 of 11.5 s in about 145 DuckDB queries, each recomputing the feed gate through the views (50 to 100 ms a read; about 1 ms from a table). Measured 2026-11-23 night; Michael asked for it in this session with a scripted gate run.

What: `src/pharmagentics/data/load_duckdb.py` drops any reporting relation, runs the views SQL, then for each view in file order does CREATE TABLE AS SELECT, DROP VIEW, RENAME, all inside the load transaction (a failure still rolls back). `reporting_names()` reads the view names from the SQL file. `materialize=False` keeps views.

Gate: candidate `26f760c10cde448483c2494bc5945121` vs baseline `1adaa0e72c5d415f9fd53a9625e8b940` (main 604ae24), both in the main checkout's MLflow store: exit 0; every metric equal except latency (brief p50 20.3 s -> 1.9 s).

Caveat: the data is static between loads. Anyone who edits `raw` by hand must reload, or the stored tables show the old answer (DUCKDB_FIRST_RUN.md says so).

Next: merge; rebuild each checkout's database; the Haiku agent run when convenient (the agent reads the same tables, so no change is expected beyond speed).
