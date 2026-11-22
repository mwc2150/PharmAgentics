# Docs index

This folder holds the project's written documentation, grouped by type.

## What lives where

- `planning/`: Markdown copies of the source documents from Google Drive. See [planning/README.md](planning/README.md) for their precedence.
- `adr/`: architecture decision records. Numbered, one decision each.
- `architecture/`: draw.io diagrams and `CODEMAP.md`, the generated code map (`uv run python -m pharmagentics.devtools.codemap`).
- `guides/`: how-to guides. `build-and-run.md` and `workflow.md` are here now. `DUCKDB_FIRST_RUN.md`, `MULTI_BRAND_UAT.md` and `BRIEFING_UI_INTEGRATION.md` move here in a later move-only PR. `TEAM.md` moves to `team/`.

## Where the rest lives

- Constitutions: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) (shared) and [`.specify/memory/constitution-briefing.md`](../.specify/memory/constitution-briefing.md) (Briefing lane).
- Specs: [`specs/README.md`](../specs/README.md).
- Project status: [`PROJECT_STATE.md`](../PROJECT_STATE.md).
- Handoffs between sessions: [`conversations/`](../conversations/).

## Dot folders

These stay where they are because the tools look for them there.

| Folder | What it holds |
| --- | --- |
| [`.github/`](../.github/) | CI and deploy workflows |
| [`.claude/skills/`](../.claude/skills/) | Spec Kit skills for Claude Code |
| [`.agents/skills/`](../.agents/skills/) | The same Spec Kit skills for Codex |
| [`.specify/`](../.specify/) | Spec Kit templates, scripts and the constitutions |
| [`.impeccable/`](../.impeccable/) | Hook config for the impeccable UI skill |
