# Golden set changes

From 2026-11-24, each change to the golden set is a new file here: `YYYY-MM-DD-topic.md`. A new file per branch cannot conflict in a merge; rows added to the one table in `../CHANGELOG.md` did. That table is the record up to 2026-11-23.

A case still changes only after its source changes (Evaluation Pack, user stories or the Forecast eval design: pack first, then cases).

## Format

```
# P4-Q3, WIN-2: promotion added to the Southeast finding

- Date: 2026-11-24
- Cases: P4-Q3, WIN-2 (C-021, C-032)
- Source: specs/brief-010-target-analyses/spec.md FR-012

What changed and why, in a few lines. Say whether facts were recomputed (`uv run python -m eval check`).
```

The case loader reads only `*.yaml` in the lane folders, so files here never load as cases.
