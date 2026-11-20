# Tasks: brief-007 slice A (windows named, per-territory table, feed figures, Assumptions block)

Slice A follows memo PR #13. Both engines build the affected sections in `tools/memo.py` and `tools/stages.py`.

- [X] T001 [FR-001] Default to four weeks for reported changes. Screen multi-week requests over the preceding weeks, matching the requested length up to 13 weeks and using weeks that pass the feed gate for every territory being compared.
- [X] T002 [FR-004] Name the comparison weeks beside the first comparison in §1.
- [X] T003 [FR-007] Show per-territory changes in §2 against the previous week and the comparison weeks. Label withheld territories.
- [X] T004 [FR-009] Show coverage and lateness against their thresholds for withheld cuts, the focus territory's feed figures, and the comparison-week range for projected or estimated territories.
- [X] T005 [FR-012] Add the Assumptions block to §6 and a one-line scope summary at the top of §2 for leaders.
- [X] T006 Run the focused tests and the full suite. On 2026-11-20, the two focused files passed (32 tests), the feed-week regression and P2-Q4 anchor passed on the final code, and the full suite passed (646 tests, 10 subtests).
- [X] T007 Gate the scripted engine against the rebased memo run. On 2026-11-20, `0c466ccaf8864b35b336f6baa0e4b8cc` (`023a200`, 30 cases) passed against `a4df1c30339f4cafabd292bcae83a052` with all seven gated checks at 1.000 and zero run errors. Report-only golden-number recall across the 24 single-turn cases rose from 0.406 to 0.498.
  - [ ] Haiku gate deferred. The rebased memo baseline is `ae4c68b6ff154458b652fdce04367224`.
