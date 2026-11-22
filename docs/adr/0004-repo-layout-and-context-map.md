# Context loads in tiers, and the repo keeps its layout stable for tools

Status: Accepted (2026-11-22)

The repo holds about 975k tokens of tracked text and 160 Markdown files, and agents spent many tokens crawling it to find the right file. A full Repomix dump would cost more, not less, because Claude Code reads lazily. We organise context in tiers, each linking to the next, and keep the dot folders and root files where the tools expect them.

## Decision

1. Context loads in tiers, each linking to the next. `AGENTS.md` holds the global hard rules, a short workflow and the most-used commands. `docs/architecture/CODEMAP.md` is the generated code map (`uv run python -m pharmagentics.devtools.codemap`), checked for staleness by a pytest test and kept under 30k characters; it never reads `eval/`. Nested `CLAUDE.md` files hold folder rules: each starts with `@README.md` and loads only when an agent works in that folder. Below them sit `docs/guides/`, the specs, the ADRs and the code. Nothing leaves `AGENTS.md` without a higher-fidelity home.
2. Repomix serves readers outside the repo. `repomix.config.json` is committed. It packs `src/`, `agents/`, `eval/harness/` and the root docs into a compressed pack (signatures only) under `local/`, which is git-ignored. Run it with `npx repomix`. We considered gitingest, code2prompt and files-to-prompt (the same idea, smaller user bases), and Aider's repo map (a symbol graph; the code map is a lighter version of it).
3. Dot folders stay where they are: `.github`, `.claude`, `.agents`, `.specify` and `.impeccable` are mandated by their tools. `.agents/` stays for teammates who work in Codex.
4. The root keeps `README.md`, `AGENTS.md`, `CLAUDE.md`, `PROJECT_STATE.md`, `GLOSSARY.md` (used by the domain-modeling skill), `PRODUCT.md` and `DESIGN.md` (the impeccable skill reads them at the root). `TEAM.md` moves to `docs/team/`.
5. `docs/` is organised by type: `guides/`, `planning/`, `architecture/`, `adr/` and `team/`, with `docs/README.md` as the index. `conversations/` stays at the root with an `archive/` folder. Agent prompts and specs are out of scope for this move.
6. `sql/001_reporting_views.sql` moves to `src/pharmagentics/data/sql/`.

## Rollout

- PR-A is additive: this ADR, the code map, the Repomix config, the nested `CLAUDE.md` files, the guides and a shorter `AGENTS.md`. It lands first.
- PR-B is move-only (`git mv`). It follows core-011 merging and its worktrees being pruned, so the renames do not conflict.
- PR-C fixes links and moves the SQL file. The new path appears in `.dockerignore`, the `Dockerfile` and a scope string in `src/pharmagentics/tools/stages.py` that is recorded in `tests/fixtures/scripted_answers.json`. The change therefore regenerates the fixture and runs the eval gate.

## Consequences

- One more generated file, the code map, must stay current. The staleness test catches drift.
- Folder rules now live at two levels. A global rule stays in `AGENTS.md`; only folder-specific rules go in nested files.
- Moving the SQL file touches the Docker allow-list and a recorded fixture, so PR-C needs the eval gate, not just a link check.
