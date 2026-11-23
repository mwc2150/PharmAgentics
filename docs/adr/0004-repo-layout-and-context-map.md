# Context loads in tiers, status is generated, and no branch edits a shared log

Status: Accepted (2026-11-22, revised 2026-11-23)

The repo holds about a million tokens of tracked text and close to 200 Markdown files, and agents spent many tokens crawling it. `PROJECT_STATE.md` had grown to 30k characters read at the start of every session, and it conflicted on nearly every parallel merge because each branch added an entry at the top. A full Repomix dump would cost more, not less, because Claude Code reads files only when it needs them.

## Decision

1. **No feature branch edits a file that every branch writes to.** A branch records its state in one new file, `docs/handoffs/YYYY-MM-DD-topic.md`, with a `branch`, `lane` and `next` header (`docs/handoffs/README.md`). A golden-set change is a new file in `eval/golden/changes/`. New files cannot conflict in a merge.
2. **Status is generated, not stored.** `uv run python -m pharmagentics.devtools.status` reads the handoffs and asks git which branches have merged: open handoffs first, then the latest on `main`. `PROJECT_STATE.md` is gone: the known open work is a short list in `docs/open-items.md` that changes in planning sessions, and the old entries up to 2026-11-23 are kept word for word in `docs/handoffs/2026-11-23-project-state-history.md`.
3. **Context loads in tiers, small to large.** `AGENTS.md` (global hard rules, a short workflow, the most-used commands) and the status command; then the code map and the `CLAUDE.md` in the folder being worked on (each starts with `@README.md` and adds that folder's rules; Claude Code loads it only there); then `docs/guides/`, specs, ADRs and full handoffs; then the code. Nothing left `AGENTS.md` without a fuller home.
4. **The code map is printed, not committed.** `uv run python -m pharmagentics.devtools.codemap` lists folders, context files and every module with the first line of its docstring. It never reads `eval/`.
5. **Repomix serves readers outside the repo.** `repomix.config.json` packs `src/`, `agents/`, `eval/harness/` and the root docs, compressed to signatures, into `local/` (git-ignored). Run it with `npx repomix`. We considered gitingest, code2prompt and files-to-prompt (the same idea, smaller user bases) and Aider's repo map (a ranked symbol graph; the code map is a lighter version).
6. **Tool-mandated paths stay.** `.github`, `.claude`, `.agents`, `.specify` and `.impeccable` stay where their tools look for them; `.agents/` stays for teammates on Codex. The root keeps `README.md`, `AGENTS.md`, `CLAUDE.md`, `GLOSSARY.md` (the domain-modeling skill) and `PRODUCT.md` and `DESIGN.md` (the impeccable skill reads them at the root).
7. **`docs/` is organised by type:** `handoffs/`, `guides/`, `planning/`, `architecture/`, `adr/` and `team/`, with `docs/README.md` as the index and `open-items.md` beside it. All prose lives under `docs/`: the root `conversations/` folder moved to `docs/handoffs/`. It stays flat; merged handoffs are not archived, because the status command already separates open from merged and an agent may need the history. Agent prompts and specs are out of scope.

## Considered and rejected

- **A committed `CODEMAP.md` with a staleness test** (the first version of this ADR). One day of `main` made 33 of its 189 lines stale. It would be one more file that parallel branches regenerate and conflict on, and the test would turn CI red, which blocks the deploy from `main`.
- **A test that fails when a handoff has no header.** Handoffs are sometimes committed straight to `main`; a missing header should not block a deploy. The status command lists such files as a warning instead.
- **`merge=union` in `.gitattributes`** for `PROJECT_STATE.md`. Local git honours it; GitHub's merge button ignores custom merge drivers, so pull requests would still show conflicts.
- **A separate `state/` folder.** It would repeat what the handoffs already say.
- **Moving `sql/001_reporting_views.sql` under `src/`.** The path is printed in the agent's evidence text and recorded in a test fixture; moving it changes agent output to remove one root folder.
- **Moving `SoT/` under `docs/`.** Its path is wired into the answer-key isolation scan, the image content check in both workflows and `deploy/gcp.py`, and `.gitignore`. The drops are git-ignored local folders that git would not move, so the scan would pass on an empty folder until every teammate moved theirs by hand.

## Consequences

- An agent starts a session with one command, about a thousand tokens, where it used to read about 7,500.
- A handoff with no header still lists, by its title; only the `next` line is lost.
- A branch that was opened before this change and still adds an entry to `PROJECT_STATE.md` conflicts once on merge: drop the file and move the entry into the handoff. A handoff such a branch adds under the old `conversations/` folder still lists, under a warning to move it.
- Folder rules live at two levels: a global rule stays in `AGENTS.md`, a folder-specific one goes in that folder's `CLAUDE.md`.
