# Handoffs

One file per branch or session: `YYYY-MM-DD-topic.md`. A handoff is how the next person or agent picks up the work, and it is the only place a branch records its state. Because every branch adds its own new file, handoffs never conflict in a merge.

`uv run python -m pharmagentics.devtools.status` reads this folder and git: it lists the handoffs on unmerged branches first, then the latest on `main`.

## Format

Start the file with this header (required from 2026-11-24; older handoffs are left as written):

```
---
branch: feature/brief-010-continuing
lane: briefing
next: Haiku run and gate on the merged branch
---

# brief-010 packet C: continuing cards
```

- `branch`: the branch the work is on (`main` if committed there).
- `lane`: `briefing`, `forecast` or `shared`.
- `next`: one line, the next step for whoever picks this up. Write `none` when nothing is left.

Then the body: what changed, tests and gate results with run IDs, the data version, open issues. A second session working on the same branch adds its own section to the same file.

## Rules

- Never edit another branch's handoff, and do not add status to `docs/open-items.md` or any other shared file.
- Handoffs stay in this folder after their branch merges. Old handoffs are history, not current instructions.
- The status command lists a handoff with a missing header under a warning; fix it when you see it.
