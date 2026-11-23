# brief-010 packet NC: the national TRx card (2026-11-23)

Branch `feature/brief-010-nationaltrx`, worktree `pa-010-NC`, base packet P's tip `3653240`. Not pushed.

## What changed

- `stages.national_reading` (new): builds the national card's facts for every brief with the national grain: national BXA TRx direction (`national_trx_direction`: the brief's territories rule, primary comparison, the house flat band, no claim), the competitor reading when Metacora has one, the holiday driver (`holiday_effect`) and the ruled-out list. `competitor_status` no longer computes the national reading itself (`_national_reading` is now `_competitor_reading`, the check and the share directions only).
- Holiday driver: supported only when the period's weeks are calendar weeks (`Period.calendar`, half or more of the weeks flagged `holiday_flag` or `plan_year_reset` in `raw.calendar`) and fewer than half of the primary comparison weeks are. Previous four weeks: national down, holiday supported (P3-Q2). Last year's same holiday weeks: national up, no holiday (WIN-1).
- Ruled out nationally (Q2): `lag_checks.national_ruled_out(story_checks)` now takes the checks of the territories that have a story card in the brief (what the brief ran for its cards; no checks re-run). A driver is ruled out unless a story territory supports it or cannot rule it out (inconclusive or untested). No story territory rules all three out. In a calendar week no story is opened, so the card lists none.
- `memo.competitor_card` carries `directions["trx"]`, the holiday driver and, without a competitor reading, a "National BXA TRx ..." headline that reuses the KPI strip's percent token (no new claim). `memo.national_block` is the card of a brief with no competitor story: card headline visible, the sentence in the folded detail (so the answer holds it and the visible words grow by the headline only). Block id `national:trx`.
- Carried by the scripted pipeline (`briefing_baseline/pipeline.py`: the competitor block's card is set after the stories' checks are known; a brief with no competitor story appends the national block), by the MCP `memo_close` (`national_story`, and the competitor card from `national_reading`) and by `briefing_agent/write.assemble`. The agent engine's triage still lists the competitor story only when Metacora has a reading; the national block is code-added at close, not a story the Manager chooses.

## Not built

- Packet X's separate NATIONAL data-artifact card.
- Triage or the Manager's plan listing the national TRx card as a candidate.

## Open

- `holiday` is supported on the stated rule alone (period holiday, comparison not), whatever the direction. If the national move were up or flat in a holiday period against ordinary weeks, the card would still say holiday supported; add "and down" if that is not wanted.
- A card that covers `trx` and also supports `competitor` raises `false_drivers` in a case with a NATIONAL TRx finding that lists no competitor (P2-Q1: national down, data). The cause is the one-card decision; a per-measure driver list or a scorer that holds `competitor` to the share measures would remove it.

## Checks (laptop was slow; the full suite is the integrator's)

- Cards, direct pipeline calls with each golden case's definition (before to after, finding points): P3-Q2 0/2 to 2/2, WIN-1 0/1 to 1/1, P3-Q1 4/5 to 5/5. Others unchanged: P1-Q5 4/4, P3-Q4 2/2, P1-Q2 1/1, P3-Q5 2/2, P4-Q1 2/2, P1-Q6 0/2, P4-Q5 0/4. `false_drivers`: P2-Q1 1 to 2 (the competitor note above), all others unchanged.
- Words (analyst view): pre-launch or calendar briefs gain the card headline only (P1-Q3 399 to 409, P3-Q2 417 to 437, WIN-1 399 to 408, P4-Q1 784 to 793); briefs with a competitor card are unchanged. `MEASURED_ANCHORS` was not touched; P1-Q3 and P4-Q1 move by the new headline, so the integrator's `test_word_budget` recount should be checked.
- Tests run: `tests/test_national_trx.py` (new), and by `-k` the national tests in `tests/test_memo.py`, `tests/test_brief_definition.py` (the four regenerated baseline entries, the grain, relative_to and two-comparison tests), `tests/test_triage.py::test_answer_unchanged`: 21 passed. Not run: the rest of `test_memo.py` and `test_brief_definition.py` (a full earlier run passed everything else, 88 of 95, before the fixes below), `test_agent_build3.py`, `test_mcp_server.py` (the `memo_close` and `write.assemble` change is untested by a test).
- Fixtures regenerated with the engine, not by hand: `tests/fixtures/brief010_db_baseline.json` entries P1-Q4, P2-Q2, P4-Q4, WIN-1 (a national block's sentence in the answer); `tests/fixtures/scripted_answers.json` entries 2025-04-21 and 2025-12-29 (same). Claims and evidence are identical; only the answer text changed.
- Three `test_brief_definition.py` tests (grain without territory, relative_to, two comparisons) already failed on the base because the `cards()` helper counted the competitor card; the helper now leaves out NATIONAL cards.
- `tests/test_memo.py`: the P3-Q1 anchor now expects promotion ruled out; the national card tests expect `trx` in `directions`; the old scan test is replaced by the unit test in `test_national_trx.py`.
