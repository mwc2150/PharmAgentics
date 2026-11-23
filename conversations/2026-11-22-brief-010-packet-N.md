# brief-010 packet N: the national competitor card (2026-11-22)

Branch `feature/brief-010-national`. Spec: brief-010 FR-006, User Story 4; core-011 FR-004, FR-017.

## What changed
- `tools/checks.py`: `check_competitor_national(reg, W)` (new). Supported once Metacora has launched and holds at least `COMPETITOR_FLOOR` (5 points) of the basket on the brief's weeks; ruled out before launch or below the floor. Its text carries no number, so it adds no claim.
- `tools/stages.py`: `competitor_status` now also fills `facts` through `_national_reading`: the check, `directions` (`bxa_share`, `competitor_share`, `trx`; share points and TRx change both use `stages.word`, flat inside 0.5) and the comparison-week shares as claims (`bxa_base`, `bxe_base`). No comparison weeks: no directions and no base claims. TRx is like-for-like (`p.ok`).
- `tools/memo.py`: `competitor_card` builds the national card. Shape: `territory: "NATIONAL"`, `cut: None`, `direction` = BXA basket-share direction, `directions` {bxa_share, competitor_share, trx}, `drivers_checked: ["competitor"]`, `drivers_supported` / `drivers_ruled_out` from the check, confidence Medium. Headline: "Metacora holds {bxe} of the four-brand basket, up from {bxe_base} on the comparison weeks, and BXA holds {bxa}, down from {bxa_base}." (plain old headline when no comparison shares). Both engines already call `competitor_status` then `competitor_card`, so the agent engine gets the same card; there is one competitor block, so at most one national card a brief.
- `eval/harness/scorers.py`: `_finding_points` reads `card["directions"][measure]` when the finding has a `measure`, else `card["direction"]`.
- `CARD_FIELDS` (leader allow-list) is unchanged, so `directions` stays analyst-only; leaders see the card with territory NATIONAL.

## Tests
`eval/tests/test_national_measure.py` (scorer), `tests/test_memo.py` (card on P3-Q1, P3-Q4, P1-Q5; leader view; ruled-out and fallback headline). `test_memo.py` and `test_targets_cuts.py` assertions that the competitor card had territory None / no drivers_checked were updated.

## Open
- P3-Q1 `bxa_share` down is not met on the default comparison weeks: BXA share was 33.6% on the four weeks before (03-30 to 04-20) and 33.2% that week, a 0.4-point change, flat. The golden answer measures against the pre-launch weeks (35.4%, down 2.2). Option: take `bxa_share` direction from the pre-launch weeks (`facts["pre"]`) when the brief's comparison weeks start after launch. Michael's call; not done.
- P3-Q1 also expects access, promotion and supply ruled out on the national card; the national card has no such checks, so at best 2 of 5 points there.
- P3-Q4 and P1-Q5 meet their findings. The scripted run and gate were not run (integration packet).
- Other NATIONAL findings (P2-Q1, P3-Q2, WIN-1): a national competitor card that supports competitor counts as a false driver unless their findings list it. Check at integration.
