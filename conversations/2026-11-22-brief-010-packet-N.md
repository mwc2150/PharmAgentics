# brief-010 packet N: the national competitor card (2026-11-22)

Branch `feature/brief-010-national`. Spec: brief-010 FR-006, User Story 4; core-011 FR-004, FR-017.

## What changed
- `tools/checks.py`: `check_competitor_national(reg, W)` (new). Supported once Metacora has launched and holds at least `COMPETITOR_FLOOR` (5 points) of the basket on the brief's weeks; ruled out before launch or below the floor. Its text carries no number, so it adds no claim.
- `tools/stages.py`: `competitor_status` now also fills `facts` through `_national_reading`: the check, `directions` (`bxa_share`, `competitor_share`, `trx`; share points and TRx change both use `stages.word`, flat inside 0.5). No comparison weeks: no directions. TRx is like-for-like (`p.ok`).
- `tools/memo.py`: `competitor_card` builds the national card. Shape: `territory: "NATIONAL"`, `cut: None`, `direction` = BXA basket-share direction, `directions` {bxa_share, competitor_share, trx}, `drivers_checked: ["competitor"]`, `drivers_supported` / `drivers_ruled_out` from the check, confidence Medium. Headline unchanged ("Metacora holds {bxe} of the four-brand basket, and BXA holds {bxa}."). Both engines already call `competitor_status` then `competitor_card`, so the agent engine gets the same card; there is one competitor block, so at most one national card a brief.
- `eval/harness/scorers.py`: `_finding_points` reads `card["directions"][measure]` when the finding has a `measure`, else `card["direction"]`.
- `CARD_FIELDS` (leader allow-list) is unchanged, so `directions` stays analyst-only; leaders see the card with territory NATIONAL.

## Tests
`eval/tests/test_national_measure.py` (scorer), `tests/test_memo.py` (card on P3-Q1, P3-Q4, P1-Q5; leader view; ruled-out and fallback headline). `test_memo.py` assertions that the competitor card had territory None / no drivers_checked were updated.

## Open
- P3-Q1 `bxa_share` down is not met on the default comparison weeks: BXA share was 33.6% on the four weeks before (03-30 to 04-20) and 33.2% that week, a 0.4-point change, flat. The golden answer measures against the pre-launch weeks (35.4%, down 2.2). Option: take `bxa_share` direction from the pre-launch weeks (`facts["pre"]`) when the brief's comparison weeks start after launch. Michael's call; not done.
- P3-Q1 also expects access, promotion and supply ruled out on the national card; the national card has no such checks, so at best 2 of 5 points there.
- P3-Q4 and P1-Q5 meet their findings. The scripted run and gate were not run (integration packet).
- False drivers on the other NATIONAL findings (checked with `false_drivers` and `finding_recall` against a national card that supports competitor, direction down): P2-Q1 (expects data), P3-Q2 (expects holiday) and WIN-1 (expects no driver) each count 1 false driver, because those findings do not list competitor. `finding_recall` gives a partial point where the card's direction matches (P2-Q1 and P3-Q2 0.5, WIN-1 0.0 as it expects up). So yes: wherever a brief for those weeks carries the competitor story, the national card scores a false driver. The score is report-only. Options for Michael: list competitor on those findings where the golden answer allows it, or have the scorer skip the national competitor card when no finding names a competitor driver. Not changed here (golden YAML and cases are another packet's).
- The headline stays at its old wording and length. A fuller headline ("up from X on the comparison weeks") added 10 words and moved `MEASURED_ANCHORS` (the word budget; `test_measured_anchor_counts_still_hold`), which needs a print-fit re-measure, so it was left out. The card's `direction` / `directions` carry the comparison.
