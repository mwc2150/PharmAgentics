---
branch: feature/repo-layout-a
lane: shared
next: Michael reviews and pushes; later, a pass over the frontend/ docs once the UI branches settle
---

# Repo layout and context map (2026-11-22 to 2026-11-23)

Michael and Claude planned the cleanup over two sessions; the decisions are in `docs/adr/0004-repo-layout-and-context-map.md`. One branch, five commits: additions, moves (`git mv` only), links, then a second pair of moves and links for `docs/handoffs/` and `docs/open-items.md`.

## What changed

- **Status is generated.** `uv run python -m pharmagentics.devtools.status` reads `docs/handoffs/` and git. `PROJECT_STATE.md` is gone: known open work is in `docs/open-items.md`, and its entries up to 2026-11-23 are word for word in `docs/handoffs/2026-11-23-project-state-history.md`. Handoffs carry a three-line header from 2026-11-24 (`docs/handoffs/README.md`).
- **Code map is generated.** `uv run python -m pharmagentics.devtools.codemap` prints folders, context files and every module (about 5k tokens). It is not committed: one day of `main` made 33 of 189 lines stale, and a committed copy would conflict between parallel branches.
- **`AGENTS.md`** went from 12.2k to about 5k characters. The hard rules are unchanged. The Workflow and Build and run sections live in `docs/guides/workflow.md` and `docs/guides/build-and-run.md`; the Layout block is the code map's Folders table.
- **Folder rules** load from nested `CLAUDE.md` files in `eval/`, `src/pharmagentics/`, `agents/brand-briefing/`, `agents/forecast-explanation/`, `deploy/` and `specs/`.
- **Golden changes** go in `eval/golden/changes/<date>-<topic>.md`; `eval/golden/CHANGELOG.md` is the record up to 2026-11-23.
- **Moves:** `conversations/` to `docs/handoffs/`; `PROJECT_STATE.md` to `docs/open-items.md`; `TEAM.md` to `docs/team/`; `docs/DUCKDB_FIRST_RUN.md`, `docs/MULTI_BRAND_UAT.md` and `docs/BRIEFING_UI_INTEGRATION.md` to `docs/guides/` in lower case. `sql/` stays (moving it would change the agent's evidence text). `SoT/` stays (its path is wired into the isolation scan and the deploy image check, and the drops are local, git-ignored folders).
- **Repomix:** `npx repomix` writes a compressed pack to `local/repomix-pack.xml` for readers outside the repo.

## Why no test guards the formats

CI runs the whole suite and a red run blocks the deploy from `main`. A stale code map or a handoff without a header should not stop a deploy, so both are generated or reported by the status command instead of asserted in a test.

## Checks

See the commit messages for the test counts. No agent or scorer changed, so there is no eval run.
