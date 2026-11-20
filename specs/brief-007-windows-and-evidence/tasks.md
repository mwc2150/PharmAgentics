# Tasks: brief-007 slice A (windows named, per-territory table, feed figures, Assumptions block)

Slice A goes into the memo pull request (Session 2026-11-20). Code-built sections only; both engines compose through `tools/memo.py` and `tools/stages.py`, so no prompt or model change.

- [ ] T001 [FR-001] `BASELINE_WEEKS = 4` beside `MATERIAL_CHANGE` in `src/pharmagentics/tools/stages.py`; `resolve` uses it for every window length
- [ ] T002 [FR-004] Name the comparison weeks beside the first comparison (like-for-like line in §1)
- [ ] T003 [FR-007] Per-territory change lines in §2 from `stages.kpis` (latest week on the week before; period on the comparison weeks; withheld territories named without a change)
- [ ] T004 [FR-009] Feed figures: coverage against the gate floor and lateness against its target for withheld cuts; the focus territory's row; the comparison-week range of a projected or estimated territory
- [ ] T005 [FR-012] Assumptions block at the end of §6; one-line scope summary at the top of §2 for leaders
- [ ] T006 Tests for T001 to T005; full suite
- [ ] T007 Gate both engines (scripted; agent on Haiku, 4 workers) against the rebased memo runs; record recall on the 24 single-turn cases
