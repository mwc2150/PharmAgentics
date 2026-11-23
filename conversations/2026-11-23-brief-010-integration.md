# brief-010 integration (2026-11-23)

Claude Opus, with Michael. Branch `feature/brief-010-targets` (PR #25). Spec `specs/brief-010-target-analyses/`.

## What landed

Packets, all merged into the branch:

- **D-B, D-U, G:** the brief definition (six selectors, lists, the primary first) on both engines, the form and the golden cases.
- **N:** the national card.
- **R:** restatement detail.
- **P:** plan cut cards.
- **S:** channel and specialty percent movers.
- **X:** data notes. The restatement card has its own `restated_figure` measure. A national data-artifact card is added when a territory drops out. P2-Q1 compares with one week.
- **NC:** every brief has a national card with a TRx direction. Holiday is the cause only when the period is holiday weeks and the comparison is not. A driver is ruled out nationally unless it is supported in a territory that has its own story.
- **C:** continuing cards for a promotion lapse or plan access restriction still running in the period.
- **I:** golden cases carry the app's `intent`. P4-Q5 is a Promotion review.

Decisions, from the grills of 2026-11-23:

- **The word budget is no longer a target.** It is report-only. `false_drivers` is the guard against padding.
- The four rules above (NC, C, I, and the P2-Q1 data notes) are Michael's.

Integration fixes:

- New Briefing figures use the Briefing percent format (brief-008 FR-016). The packets were written before the polish merge.
- When the data-artifact card exists, it owns national TRx, so a data artifact is never pinned on the competitor.
- Packet C's requirement is FR-012; packet X already used FR-010.

Full-suite fixes. CI found 12 failures across the merged packets:

- Cut and continuing cards now record a "Split the change" step, so every claim has its event.
- The agent's citation index now covers claims shown only in card headlines.
- Tests were updated to the merged behaviour.
- Word anchors were re-measured.

Fixes from `/code-review medium`:

1. The agent's out-of-release fallback handled an empty comparison list wrongly.
2. The agent's national card now reads only the investigated story territories.
3. Kept continuing cards are no longer re-ranked out.
4. A Promotion review clears chosen weeks.

## Results

- **Scripted:** run `60927c3280374d748a44c55ca309b8d1`, gated against `1b8eaaafd97f438f90e8b0e8528a4884`. Exit 0, and all seven gated checks are at 1.000.
  - Finding recall: pooled **1.000** (27 of 27 cases), up from 0.618.
  - Key facts: pooled **1.000** (25 of 25), up from 0.857.
  - `false_drivers`: 0.074, down from 0.12.
  - 8 briefs are over the old budget (report-only).
- **Haiku:** run `6f62d72ae3ba4327bd52d8145aac31be` (code `d3d01d5`) gated against `727bc0064e75480cbd73dca00748f56e`: exit 0, all seven 1.000, no run errors. Finding recall pooled 0.971 (target 0.90), key facts pooled 1.000, false drivers 0.074. One miss: P2-Q4's plan cut card, which the Manager left out. An earlier run `364c704c` on `1591779..cce5df9` crashed on 5 cases (a citation-index KeyError, fixed in `d3d01d5`). The four review fixes in `da4b00d` came after this run and are covered by tests.
- **App check:** through the API, analyst and director. Cut, national and continuing cards appear. The leader view has no evidence, claims or SQL.

## Open

- **P4-Q3 and WIN-2:** the brief names promotion as the cause of the Southeast coverage gap, but their golden findings list no cause. P1-Q6 and P4-Q5 list promotion. Michael to decide whether to add promotion to the two cases. It is the only remaining `false_drivers` source.
- **Five review nits not fixed:**
  - the restatement row filter leaves out `reason`;
  - TRx-only claims carry the `nbrx` label when NBRx is the primary measure;
  - the follow-up scope ignores the definition;
  - a duplicated proposed grain drops the model's reading;
  - the form does not check that a pre-launch comparison can apply.
- **PR #26 (UI refresh):** brief-010 is merged into it locally (`65889f6` on `feature/ui-refresh`; App, ComparisonPicker and Memo resolved, build passes). Push after #25 merges.
- **Repo reorg:** next, per the repo-layout plan (stage 1: append-only `state/` files, so `PROJECT_STATE.md` stops conflicting).
