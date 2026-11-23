# Workflow

Full working process, moved from `AGENTS.md` (which keeps a short summary). The handoff rule changed on 2026-11-23 (ADR 0004): status lives in handoffs; `PROJECT_STATE.md` is gone. The rules are in the constitutions: [.specify/memory/](../../.specify/memory/).

**Eval loop.** Change a system, then `uv run python -m eval run --system <name>`, read the result in the MLflow dashboard (`uv run python -m eval ui`), and run `uv run python -m eval gate <candidate-run-id> <baseline-run-id>` before merging. No change merges if a gated check regresses (Briefing B-VII). A new system (the low-code version, then the agents) plugs in through `eval/harness/systems.py` and returns the answer contract in `eval/harness/envelope.py`: answer text, claims, evidence items. Reuse `src/pharmagentics/tools/` so every number stays traceable.

**Specs and project state work together.** Each source has one job:
- Specs (Spec Kit) hold what each feature does and why: requirements, decisions, acceptance.
- The constitutions hold the rules.
- `docs/handoffs/` holds the handoffs, and `uv run python -m pharmagentics.devtools.status` prints where things stand from them. `docs/open-items.md` holds the known open work.

Code may run ahead of its spec while you iterate. Bring the spec and your handoff up to date in the same pull request, so nothing merges with the spec behind the code. When a spec and the code disagree, the pull request fixes whichever is wrong; an older spec does not win just because it is written down. Never delete a spec; mark a superseded one "History" in `specs/README.md`, with what replaced it.

The Spec Kit flow is `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` (with `/speckit-analyze` and `/speckit-converge` when they help), one spec per component. A `plan.md` can be a short file contract, and a `tasks.md` can hold the work packets for a team of agents. Spec Kit finds the active spec from `.specify/feature.json`, not the branch name:

```powershell
'{"feature_directory":"specs/core-007-rbac-uat-deployment"}' | Out-File -Encoding ascii .specify/feature.json
```

**Handoff.** Before ending a session or handing work to another agent, write a handoff file `docs/handoffs/YYYY-MM-DD-topic.md`: the `branch`, `lane` and `next` header (`docs/handoffs/README.md`), then what changed, tests and gate results with run IDs, the data version and open issues. One handoff per branch; a second session on the same branch adds its own section to it. Do not add entries to `docs/open-items.md`, `eval/golden/CHANGELOG.md` or any other file that every branch would edit in the same place: parallel merges conflict there. A golden-set change is a new file in `eval/golden/changes/`.

**Source documents.** The masters are in Google Drive. A new export goes into `SoT/<YYYY-MM-DD>/`; run `SoT/check.py`, refresh the changed copies in `docs/planning/`, update the specs and golden cases that cite them, and log the drop in `SoT/README.md`.
