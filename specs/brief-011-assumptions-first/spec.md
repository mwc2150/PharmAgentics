# brief-011: The brief follows its Assumptions

**Spec ID**: brief-011-assumptions-first (Briefing lane)
**Created**: 2026-11-27 (v2; written after the code, invariants and acceptance tests only, per the v2 spec format)
**Branch**: feature/v2-assumptions-first
**Source**: Michael, 2026-11-27: "always, we need to start from assumptions first". Mentor review 2026-11-20, item 2.1.

## Why

A brief is built from a definition the analyst chooses up front (brief-010: period, comparison, territories counted, measure, grain, relative to) and printed as its Assumptions. A reader checks every figure against those choices. The mentor's review found a brief whose promotion verdict used weeks it never stated: calls were compared with the thirteen weeks before the period (holding the August lapse) while TRx used the stated four, so a recovery read as "+51%, supported".

## Invariants

- **I1. No unstated window.** Every week a claim's SQL reads is a week the brief states: the period, the comparison weeks (and each extra comparison), the tested lags of one and two weeks before either, a window printed with dates, or a window named in words against a printed date ("the four weeks before launch", "the same weeks a year earlier").
- **I2. Driver checks read the comparison weeks.** Promotion, supply and access compare the period with the stated comparison weeks. A check that needs other weeks states them in the Assumptions with dates: the competitor check's weeks ("Metacora's local share: <start> to <end>.") and the multi-week materiality screen of brief-007 FR-001 ("Material-change screen: <start> to <end>.").
- **I3. A lapse is named.** When the comparison weeks hold a promotion lapse (the Promotion review's rule) and calls are back inside the period, the promotion line says "recovery after the promotion lapse of <start> to <end>", not a push. When calls fell and the period itself falls inside a lapse, the line names it ("during the promotion lapse of <start> to <end>") and says when the comparison weeks hold lapse weeks too (UAT review H-3).
- **I4. Asked about is not material.** A territory the question names whose change is inside its normal range says so in its story and in §1's Least sure line; it is never presented as a material change.
- **I5. Same on both engines.** The agent's MCP tools call the same checks and Assumptions builder, so I1 to I4 and I6 hold for agent briefs.
- **I6. Inside the normal range, nothing is credited.** For every question and brand (Michael, 2026-11-27): a territory whose change is inside its normal range on the stated comparison weeks gets no territory-level driver (promotion, competitor, supply, data) credited, on its story or on its plan cards. The check reads "<Driver>: not credited", keeps its evidence and names any lapse, and the story closes "No driver is named: <territory> moved within its normal range, so there is no change to explain", with no next check in §5. Access keeps its verdict: its evidence is always a plan's own TRx. A change nothing explains (no driver supported, as in P2-Q3) still closes "Unresolved, investigate next" with its next check. One function (`stages.credit_rule`) applies the rule for both engines.

## Acceptance tests

- `tests/test_follows_assumptions.py::test_claims_read_only_stated_weeks`: I1 on every Briefing golden case (scripted). Fails on the pre-change code for P2-Q2, P3-Q3, P3-Q5 and P4-Q1.
- `tests/test_follows_assumptions.py::test_the_mentor_southeast_week`: the week of 2026-10-05 in Southeast. Calls read only the period and Sep 7 to 28 (lags included); the lapse of Aug 3 to 31 is named; §1 says the change is within Southeast's normal range; the competitor weeks are stated.
- `tests/test_follows_assumptions.py::test_claims_read_only_stated_weeks` also asserts I6 on every Briefing golden case of both brands (`credited_in_range`).
- Golden REV-1 (C-057, reviewed 2026-11-27): Southeast, week of 2026-10-05, within its normal range, no driver.
- Scripted gate: no gated check regresses (B-VII). Agent gate on Haiku before merge.

## Out of scope

The promotion verdict for marketers (controls first, comparison with other territories, all four channels, NBRx first, `not_testable` for flat promotion) is the promo-verdict packet (`docs/handoffs/2026-11-27-promo-verdict.md`). The Southeast lapse disagreement is settled: P4-Q3 and WIN-2 list promotion under their own assumptions (`eval/golden/changes/2026-11-27-southeast-lapse-and-rev-1.md`). The Forecast lane's "usual" call level (H-3) is Alvin and Sienna's; the Briefing states its own comparison weeks.
