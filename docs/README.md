# Docs index

This folder holds the project's written documentation, grouped by type.

## What lives where

- `planning/`: Markdown copies of the source documents from Google Drive. See [planning/README.md](planning/README.md) for their precedence.
- `adr/`: architecture decision records. Numbered, one decision each.
- `architecture/`: draw.io diagrams. The code map is printed on demand: `uv run python -m pharmagentics.devtools.codemap`.
- `guides/`: how-to guides: `build-and-run.md`, `workflow.md`, `duckdb-first-run.md`, `multi-brand-uat.md` and `briefing-ui-integration.md`.
- `team/`: `TEAM.md`, how to use, host, run and deploy the web app.

## Where the rest lives

- Constitutions: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) (shared) and [`.specify/memory/constitution-briefing.md`](../.specify/memory/constitution-briefing.md) (Briefing lane).
- Specs: [`specs/README.md`](../specs/README.md).
- Project status: run `uv run python -m pharmagentics.devtools.status`. Known open work: [`open-items.md`](open-items.md).
- Handoffs between sessions: [`handoffs/`](handoffs/README.md), one new file per branch.

## Dot folders

These stay where they are because the tools look for them there.

| Folder | What it holds |
| --- | --- |
| [`.github/`](../.github/) | CI and deploy workflows |
| [`.claude/skills/`](../.claude/skills/) | Spec Kit skills for Claude Code |
| [`.agents/skills/`](../.agents/skills/) | The same Spec Kit skills for Codex |
| [`.specify/`](../.specify/) | Spec Kit templates, scripts and the constitutions |
| [`.impeccable/`](../.impeccable/) | Hook config for the impeccable UI skill |
