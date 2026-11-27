---
branch: packet/promo-verdict
lane: briefing
next: Michael decides the golden side (promotion "ruled out" where activity held level, list below); then the Haiku agent gate on the merged branch
---

# v2 promotion verdict a marketer can act on (2026-11-27)

Based on `feature/v2-assumptions-first` f317992. Scripted engine only; no model was run. brief-011 invariants I1 to I5 hold
(`tests/test_follows_assumptions.py` passes; comparisons stay on the stated weeks; the lapse-recovery wording stays).

## What changed

- `tools/lag_checks.py` `check_promotion(reg, terr, W, B, brand, *, use_selected_baseline=False)`
  - **Controls first.** When rep calls line up with TRx (the old `supported` test, unchanged) the controls are read inside the check
    on a scratch registry (so they add no claim and the verdict does not depend on the order an agent calls its tools):
    access (the territory's access check), competitor (the story's own reference weeks) and the calendar (half or more of the
    comparison weeks are holiday or plan-year-reset weeks, the period's own calendar-mode rule). Any supported control makes the
    verdict `not_separable`: "Promotion: cannot be separated from access in these weeks." A data artifact is not read: a flagged
    feed already leaves promotion `insufficient`.
  - **Not testable.** If no channel moved at any tested lag the verdict is `not_testable` ("Promotion: not testable; activity held
    level, so its effect cannot be measured this period."). `ruled_out` is now only: a channel moved and TRx did not follow (the text
    names the channels that moved).
  - A channel "moved" when it changed by `PROMOTION_CHANGE_PCT` (30%) or more against the comparison weeks; the sparse speaker-programs
    count must also change by at least `SPARSE_FLOOR` (2 a week), otherwise noise (a mean of about one a week) would make nothing
    ever "flat".
  - **Effect against comparable territories** (supported only). Territories whose four channels all held level at the verdict's lag
    and whose TRx is reportable in every week compared. For each, implied extra TRx a week = this territory's period TRx a week less
    its comparison-weeks TRx scaled by that territory's own change. The range is the lowest to the highest across them (two claims, `min`
    and `max`, plus the territory count and the 30% threshold). Said as "Compared with territories without a promotion change"; never
    ROI or attribution. With no such territory the line says so.
  - **Lag and re-check.** The line names the lag; `recheck` = the period's last week plus as many weeks as the comparison (Southeast
    2026-10-05: "Re-check after 2026-11-02").
  - **New patients first.** The line leads (after the verdict clause) with NBRx change, then TRx. The direction test stays on rep calls
    against TRx. NBRx claims are labelled `measure: nbrx`, TRx and the effect `measure: trx`.
- `tools/checks.py`: `Check.verdict` vocabulary gains `not_separable` and `not_testable`. `confidence()`: a not_separable promotion keeps
  the supported driver a candidate (Medium, never High) and the lead says "access; promotion cannot be separated from access"; a
  `not_testable` promotion counts as closed for High (it did not move, so it is no rival explanation) but is never called ruled out.
- `tools/memo.py`: `story_card` adds `card["promotion"]` (see below); `story_detail(reg, p, t, checks)` adds the folded "Promotion detail"
  lines (NBRx, TRx, the four channels, the comparison and how the range is built, lags tested and the re-check date);
  `render_sections` fills the claim tokens inside `card["promotion"]`; the Assumptions "Drivers" line gains "Promotion: controls first,
  then comparable territories." (7 words; a longer sentence put P4-Q1 over its word budget).
- Both engines: `pipeline._story` passes the checks to `story_detail`; the MCP `_driver` passes `use_selected_baseline`, and
  `story_section` passes the checks to `story_detail`. `events._LABEL` reads the two new lines as "inconclusive"; `pipeline._VERDICT` too.
- `tools/registry.py` `_pct`: a percentage of a thousand or more ("1,500.0%") broke the one-decimal check (speaker programs from a
  fraction of a week). Commas are stripped before parsing; output unchanged for every other value.
- Scoring: `not_separable` and `not_testable` are in neither `drivers_supported` nor `drivers_ruled_out` (`driver_calls` only reads
  `supported` and `ruled_out`). The national card's `drivers_ruled_out` no longer lists promotion when every story territory's
  promotion was not testable (`national_ruled_out` reads verdicts).

## `card["promotion"]` (analysts' view; leaders' `CARD_FIELDS` do not include it)

Keys in order: `verdict`, `lag` (0, 1 or 2), `lag_label`, `tested` (all three labels), `new_patients` and `trx`
(`{measure, before, after, change, direction}`), `channels` (rep calls, digital impressions, samples, speaker programs, each
`{channel, before, after, change, direction, moved}`), `effect` (`{low, high, territories, threshold, held_level, method}` or null),
`separable_from` (not_separable only: access, competitor or holiday) and `recheck`. Every figure is a claim token filled in the
sections. Aggregated columns only; no rep-level column (`rep_vacancy_count_aggregated` is not read).

## Evaluation (scripted, data version of `local/pharmagentics.duckdb` loaded in this worktree)

| | BXA before `a91dfe00` | BXA after `b439890a` | BXC before `6f15e6da` | BXC after `3830aa06` |
| :- | :- | :- | :- | :- |
| finding_recall_pooled | 1.000 | 0.956 | 0.700 | 0.700 |
| key_fact_recall_pooled | 1.000 | 1.000 | 0.763 | 0.780 |
| false_drivers/mean | 0.074 | 0.074 | 0.000 | 0.000 |
| brief_words/mean | 699.3 | 705.8 | 571.0 | 572.5 |
| latency_brief_p50 | 1.7 s | 2.2 s | 1.2 s | 1.3 s |

Gates: BXA `eval gate b439890a a91dfe00` exit 0; BXC `eval gate 3830aa06 6f15e6da` exit 0.

## Golden impact (Michael decides the golden side; nothing was edited)

A "not_testable" promotion is no longer "ruled out". Findings that list `promotion` in `drivers_ruled_out` for a card whose promotion
held level lose that one point:

| Case (id) | Finding | Territory and cut | Old verdict | New verdict | Why |
| :- | :- | :- | :- | :- | :- |
| P2-Q2 (C-008) | `mid_atlantic_plan_access` | MID_ATLANTIC `plan:SYN_MID_ATLANTIC_MEDICARE_PART_D_1` | ruled_out | not_testable | all four channels flat at every lag; 6 of 6 to 5 of 6 |
| P2-Q3 (C-009) | `south_central_unresolved` | SOUTH_CENTRAL | ruled_out | not_testable | same; 5 of 5 to 4 of 5 |
| P4-Q4 (C-022) | `mid_atlantic_access_restored` | MID_ATLANTIC `plan:...PART_D_1` | ruled_out | not_testable | same; 3 of 3 to 2 of 3 |

BXA pooled findings 68 of 68 to 65 of 68. Cards that lost "promotion" from `drivers_ruled_out` without costing a point (the golden
finding does not list it): P1-Q4, P2-Q4, P3-Q3 (and the national cards in all of these, which now omit promotion).
BXC: no point lost, but `BXC-P4-Q4` finding `mid_atlantic_plan_lift_unexplained` lists promotion ruled out and would lose it once BXC has a
plan cut card (it scores 0 of 4 today). Key facts: BXC `BXC-P4-Q3` gains `ma_digital_impressions_aug_oct_avg` by coincidence (the
folded promotion detail states digital impressions).

No `not_separable` verdict occurs in any golden case (the Mid-Atlantic 2025-09-01 week is the real example, in the tests).
Across all single-week periods from 2025-03-03 to 2026-10-05, BXA: 236 not_testable, 325 ruled_out, 91 supported, 5 not_separable
(4 holiday, 1 access), 15 insufficient; BXC: 133, 357, 166, 1, 15.

## Decisions to confirm (Michael)

- `not_testable` counts as closed for a High confidence (it did not move); `not_separable` does not.
- The calendar control reads half or more of the comparison weeks as holiday or plan-year-reset weeks (the period's own rule), not any one.
- The 30% and speaker-program 2-a-week floors; the "held level" comparison group uses the same rule.
- NBRx now appears in every promotion line, including a brief whose definition holds TRx only (`tests/test_brief_definition.py` now allows
  "new patients" only as "New patients (NBRx)"). Say if a TRx-only brief should leave it out of the line (the card data would still lead with it).
- The effect range is wide when the comparison territories differ (Southeast 2026-10-05: 34 to 221 extra TRx a week) because it is the
  honest min to max, not an estimate.
- Continuing cards and plan cut cards reuse the territory's verdict text; they carry no `card["promotion"]`.

## Tests

New `tests/test_promotion_verdict.py` (11 tests, no model): supported line and structure, claim measure labels, not_testable, ruled_out
with a moved channel, not_separable end to end (verdict, card lists, confidence, lead), confidence unit, events regex, scripted card and
folded detail, agent-equals-scripted whatever order the tools are called (BXA and BXC), the agent's story card and detail.
Updated for intended changes: `test_memo` (Pacific supply card), `test_plan_cuts` (cut card lists; the cut finding may lose only the
promotion point), `test_brief_definition` (new patients only beside NBRx). 661 focused tests pass (eval/tests, tests/ for the briefing
stack).

Fixtures regenerated deliberately: `tests/fixtures/scripted_answers.json` and `tests/fixtures/brief010_db_baseline.json`. Every changed line
is one of: the Drivers line gaining "Promotion: controls first, then comparable territories."; a ruled-out or not-testable promotion
line gaining the NBRx and TRx sentence, the "moved" note and "Re-check after <date>."; the folded "Promotion detail" block (seven
lines) under a story; or a supported promotion line gaining the NBRx, comparison and re-check sentences. Entries touched: scripted Pacific
2026-06-08 (12 lines), Mid-Atlantic 2026-07-13 (24), New England 2026-05-04, 2026-04-06, 2025-04-21 and 2025-12-29 (2 each, the Drivers
line); baseline CMP-3, P3-Q1, WIN-1 (2 each), P1-Q1 (12), P1-Q4, P2-Q2, P4-Q4 (14 each), P2-Q3, P3-Q4 (23 each). Claims grow where a story
carries a promotion check (12 channel claims and the outcome claims are made for the card and folded detail).

`MEASURED_ANCHORS` re-measured (dated comment): P1-Q2 633/595, P1-Q3 409/376, P1-Q6 618/584, P3-Q5 776/613, P4-Q1 868/834.

Not done: no Haiku or other model run (the writer and manager prompts are untouched); no frontend change (the new `promotion` card key
is data only).
