# 2026-11-22 repo layout, PR-A

Michael and Claude (Opus) grilled the repo cleanup and context map; the decisions are in `docs/adr/0004-repo-layout-and-context-map.md`. Opus wrote the `AGENTS.md` split; two Haiku packets built the code map (`src/pharmagentics/devtools/codemap.py`, `tests/test_codemap.py`) and the docs (Repomix config, `docs/README.md`, `tests/README.md`, nested `CLAUDE.md` files, ADR 0004). Opus reviewed, regenerated the map after staging and ran the tests.

## Where every line removed from AGENTS.md went

| Removed from AGENTS.md | Now in |
| --- | --- |
| Layout block | `docs/architecture/CODEMAP.md`, Folders table (updated: feagent/ and forecast_agent/ are on main) |
| Workflow section (eval loop, specs and state, Spec Kit flow and feature.json, handoff, source documents) | `docs/guides/workflow.md`, verbatim; five-line summary stays in AGENTS.md |
| Build and run section (uv, every system command, judge, dashboard, deploys, web app, MLflow telemetry note) | `docs/guides/build-and-run.md`, verbatim; most-used commands stay in AGENTS.md |
| Read-first entries for constitutions (with versions), data dictionary, DUCKDB_FIRST_RUN | `docs/README.md`, the constitution files themselves, `data/agent_visible/README.md` |
| Folder-specific rules | Repeated, not moved, in the folder `CLAUDE.md` files; every hard rule stays in AGENTS.md |

## Open

- PR-B and PR-C wait for core-011 to merge and its worktrees (`pa-011*`, `pa-008-*`) to be pruned, so the renames don't conflict.
- Regenerate the code map whenever a module is added or renamed; CI's unittest and pytest runs both catch a stale map.
