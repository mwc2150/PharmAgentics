# Handoff: core-011 follow-ups and brief-010 (2026-11-22, late night; Claude Opus, session pharmagentics-e4)

## Done (branch `feature/core-011-exact-values`, worktree `pa-011-exact`)
- `7a893e7` FR-016 exact-value scoring (`eval/harness/truth.py`, `numbers.states`): key_fact_recall, golden_number_recall and numbers_match_golden compare with the fact's SQL value at the answer's printed precision. Rescoring the brief-008 polish run (`ef64671b`): key facts 0.710 -> 0.743, golden numbers 0.652 -> 0.674; the "dip" from the Briefing percent format was double rounding in the golden figures.
- Packet H (`c221c40`, `e7562fe`, Sonnet): `cut`, `needs`, `TARGETS`, pooled metrics and target flags, `over_word_budget`, below-target insights, Evaluation page lines; a fix so a coarse written figure never backs a finer golden number (Forecast CA-Q1).
- `3a63f92` word budget = the measured maxima (836 / 705), not rounded down: rounding down failed P4-Q1, an anchor known to fit two pages.
- Gate: scripted `ebb2952a8faf491cbffc5513c279d322` vs `a5a4968270cb47af890796f2c2979c45`, exit 0, all seven 1.000. Full suite 948 passed.

## In progress (branch `feature/brief-010-targets`, worktree `pa-010`)
- Base: main + this branch + `feature/brief-009-timeline` (brief-009 integration belongs to session pharmagentics-a0; merge again when it lands).
- Packets building in their own worktrees: D-B `pa-010-DB` (`feature/brief-010-definition`), D-U `pa-010-DU` (`feature/brief-010-form`), G `pa-010-G` (`feature/brief-010-golden`). Contract: `specs/brief-010-target-analyses/plan.md`, "The brief definition".
- Then N and R side by side, then P, then S (tasks.md). Merge bar per packet: pooled key-fact and finding recall do not fall, no case over budget, the packet's targets rise.

## Decisions (do not reopen)
- Targets 0.85 / 0.90 / two A4 pages; report-only for two runs after the golden review, then gated (FR-006, FR-021).
- The golden review was done in the grill with Michael; packet G applies it.
- Brief definition: six visible selectors at the start of the form, pre-selected, nothing enforced or hidden, no team setting; measure TRx / NBRx / both; data basis is not a selector (governed views only).
- Findings name their measure (BXA TRx unless BXA share or competitor share).

## Open
- `/code-review` on `feature/core-011-exact-values` was not run before its PR.
- Two briefs over the word budget (C-001, C-016): brief-010 must trim them.
- brief-007 FR-010 restatement window (open for Michael) affects brief-010 FR-005.
