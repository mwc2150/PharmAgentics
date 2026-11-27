# brief-013: A promotion verdict a marketer can act on, and the Marketer view

**Spec ID**: brief-013-promotion-verdict-and-marketer (Briefing lane)
**Created**: 2026-11-27 (v2; written after the code, invariants and acceptance tests only, per the v2 spec format)
**Branch**: feature/v2-assumptions-first
**Source**: Michael's v2 decisions of 2026-11-27 (Q6, from the course study guide's marketing weeks; Q15, the Marketer view); `docs/handoffs/2026-11-27-promo-verdict.md` and `docs/handoffs/2026-11-27-marketer-view.md`.

## Why

v1 tested promotion on its own and on TRx only, so it could be "supported" next to a supported access change, and flat promotion read as "ruled out". A marketer asks whether a campaign moved the brand and by how much. The honest answer controls for the other drivers first, reads new patients first, and gives a range against territories whose promotion did not change, never a return on spend.

## Invariants

- **I1. Controls first.** Promotion is judged after access, the competitor launch and the calendar for the same territory and weeks. If any of them is supported, the verdict is `not_separable` ("Promotion: cannot be separated from <control> in these weeks"); it is in neither driver list, the story's confidence is Medium at most, and the lead names the control.
- **I2. Not testable is not ruled out.** When no channel (rep calls, digital impressions, samples, speaker programs) moved at any tested lag (30% or more against the comparison weeks; speaker programs also by 2 a week), the verdict is `not_testable`. `ruled_out` means a channel moved and TRx did not follow, and the line names the channels that moved.
- **I3. New patients first.** The line and the card lead with NBRx, then TRx. The direction test stays rep calls against TRx.
- **I4. Four channels, aggregated.** All four channels appear at the verdict's lag; nothing at rep level.
- **I5. A range, never a return.** A supported verdict is compared with the territories whose four channels held level at the same lag and whose TRx is reportable in every week: each gives an implied effect, and the line states the lowest to the highest ("34 to 221 extra TRx a week", "152 to 199 fewer TRx a week", or "a change of -20 to 35 TRx a week" when they disagree on the sign). No ROI, return, attribution or spend wording.
- **I6. Timing.** The line and the card state the lag tested and a re-check date: the period's last week plus as many weeks as the comparison.
- **I7. Lapses are named.** Recovery after a lapse in the comparison weeks, and a period that falls inside a lapse, are named with their dates (brief-011 I3). Inside a normal range nothing is credited (brief-011 I6).
- **I8. The Marketer view.** P4 reads the leadership cut plus, on each territory story, the promotion read from an allow-list (verdict, lag, new patients, TRx, the four channels, the effect range and its phrase, what it cannot be separated from, the re-check date) and, once, the budget note on what data would answer "where should the next dollar go". No evidence, query text, claim token or trace. The Brand Director's (P3) response is unchanged.

## Acceptance tests

- `tests/test_promotion_verdict.py` (I1 to I7, including the agent's MCP check equal to the scripted one in any call order).
- `tests/test_marketer_view.py` (I8: the allow-list, no tokens or SQL, P3 unchanged, the test login's Marketer view equal to P4).
- `tests/ui/check_marketer_view.py` (I8 in the browser at 1280 and 390 px; the Director sees no panel).
- Golden: `eval/golden/changes/2026-11-27-promotion-not-testable.md` (I2 applied to P2-Q2, P2-Q3, P4-Q4 and BXC-P4-Q4).
