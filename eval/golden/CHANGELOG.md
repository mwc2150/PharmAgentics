# Golden set changelog

A case changes only after its source changes (Evaluation Pack, user stories or the Forecast eval design: pack first, then cases). One line per change.

| Date | Cases | Change | Source |
| :- | :- | :- | :- |
| 2026-10-29 | All 42 | Drafted by `python -m eval import-stories`: one case per persona question, C-001 to C-024 (Briefing P1-Q1 to P4-Q6) and F-001 to F-018 (Forecast CA-Q1 to FM-Q6). All `status: draft` until reviewed by hand. | `docs/planning/user-stories.md` (copy of 2026-10-23, checked against Drive 2026-10-29) |
| 2026-10-29 | 14 | Added 69 facts (number plus the SQL that recomputes it) to P1-Q1, P1-Q2, P1-Q3, P1-Q5, P2-Q1, P2-Q2, P2-Q5, P3-Q1, P3-Q2, P3-Q4, P3-Q5, CA-Q1, CA-Q2, FM-Q1. All recompute from `day1-v1`. | `local/pharmagentics.duckdb` |

## Open before freezing

- **Questions without a period** (the story names no weeks): P2-Q6, P4-Q2, P4-Q3, P4-Q5, P4-Q6, FM-Q4. Each carries a `review_note`.
- **Briefing categories** are draft assignments to the Evaluation Pack §4 taxonomy; check them.
- **Forecast scenarios** (`scenario: null`): Alvin and Sienna map each Forecast case to TC-01 to TC-12 and confirm the cases (core-006).
- **Facts** for the other 28 cases.
