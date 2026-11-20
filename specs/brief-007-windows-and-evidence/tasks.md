# Tasks: brief-007 slice A (windows named, per-territory table, feed figures, Assumptions block)

Slice A follows memo PR #13. Both engines build the affected sections in `tools/memo.py` and `tools/stages.py`.

- [X] T001 [FR-001] Default to four weeks for reported changes. Screen multi-week requests over the preceding weeks, matching the requested length up to 13 weeks and using weeks that pass the feed gate for every territory being compared.
- [X] T002 [FR-004] Name the comparison weeks beside the first comparison in §1.
- [X] T003 [FR-007] Show per-territory changes in §2 against the previous week and the comparison weeks. Label withheld territories.
- [X] T004 [FR-009] Show coverage and lateness against their thresholds for withheld cuts, the focus territory's feed figures, and the comparison-week range for projected or estimated territories.
- [X] T005 [FR-012] Add the Assumptions block to §6 and a one-line scope summary at the top of §2 for leaders.
- [X] T006 Run the focused tests and the full suite. On 2026-11-20, the two focused files passed (32 tests), the feed-week regression and P2-Q4 anchor passed on the final code, and the full suite passed (646 tests, 10 subtests).
- [ ] T007 Gate both engines (scripted; agent on Haiku, 4 workers) against the rebased memo runs; record recall on the 24 single-turn cases
