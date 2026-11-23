# brief-010 packet R: restatement detail (2026-11-22)

Branch `feature/brief-010-restatement` (worktree `pa-010-R`). Scope: brief-010 FR-004, FR-005, User Story 3; golden cases P1-Q1, P2-Q5, P3-Q6. The scripted run, the gate and the final recall numbers are the integrator's (tasks I1); this packet ran focused tests only.

## What changed

- `sql/001_reporting_views.sql` (two new governed views, built by `load_duckdb.py`; `local/pharmagentics.duckdb` rebuilt, data version unchanged):
  - `reporting.v_restatements`: one row per restatement event. Columns: `week_start, territory_id, product_id, restated_at, reason, restated_cells, trx_signed_off, trx_restated, nbrx_signed_off, nbrx_restated`. Grain: week, territory, product, restated date, reason (sums over the event's cells). The release has one event: Mid-Atlantic, week 2026-04-06, TRx 692 to 742, NBRx 97 to 98, restated 2026-07-13.
  - `reporting.v_rx_duplicate_tieout`: for each territory-week with duplicate Rx keys, `naive_trx` and `deduplicated_trx` (and the NBRx pair) per product. Naive is every delivered row; deduplicated counts each duplicated key once (`any_value`, the golden definition; the duplicates in this release are identical). The release has one row: Great Lakes, 2026-07-06, BXA 670 and 624. A tie-out, never a metric.
  - Both added to `registry.ALLOWED`. `check_duckdb.py` lists no views by name, so it is unchanged.
- `tools/stages.py`: `duplicate_tie_out` (called from `data_health`) and `restatements(reg, p, facts=None)` now read the views. `facts` receives each restatement's claim tokens for the card.
- `tools/memo.py`: new `restatement_block(facts)` (one card, largest absolute change) and an optional `restated` flag on `appendix`/`assumptions`. Call sites only elsewhere: `pipeline.py` (`Front.restated_facts`, one extend before the promotion blocks), `mcp_server/server.py` (`brief_sections` returns `restatement_stories`) and `briefing_agent/write.py` (`assemble` extends the blocks with them), so both engines build the card the same way.

## Text

- §4 folded gate line, for a territory withheld for duplicate keys: `... 143 rows against 128 expected, 15 duplicate keys. Raw, before deduplication, Great Lakes BXA TRx sums to 670; with each duplicated key counted once it is 624, so the raw sum overstates it by 46 TRx (7.4%). Do not quote the raw sum.` Four claims, tool `validate_feed`, scopes labelled "(data-quality tie-out)".
- §2 line: `Restated: Mid-Atlantic BXA TRx for the week of 2026-04-06 was 692 when first reported and is now 742, up 50 TRx (7.2%). It was restated 2026-07-13; reason: synthetic late claims adjustment. Quote the new value with this note.` (the old line had no change; its first sentence prefix is kept). At most three, largest change first.
- §3 restatement block `3.N` (after the territory stories and the competitor, before promotion blocks): title "<Territory> restatement", one line `Data story: ... from 692 to 742 TRx (up 7.2%). Confidence: High. Leading driver: data.`, and the card.

## Card shape

```python
{"headline": "Mid-Atlantic TRx for the week of 2026-04-06 was restated from {c} to {c} (up {c}).",
 "confidence": "High", "drivers_checked": ["data quality"],
 "territory": "MID_ATLANTIC", "cut": None, "direction": "up",   # up if restated > signed off, down if lower, flat if equal
 "drivers_supported": ["data"], "drivers_ruled_out": []}
```

Block id `restatement:<TERRITORY>:<week>`. All numbers reuse the §2 line's claim tokens (no new claims).

## Assumption (printed in the Assumptions block, in the Like-for-like item, only when the brief reports a restatement, so a brief with none is unchanged)

"A restatement is reported when the restated week is inside the period or the restatement was published inside it." Source line becomes "the feed gate and the vendor's restatement record". Michael to confirm (spec FR-005 updated; the old NEEDS CLARIFICATION is resolved by it).

Behaviour change to know: the old code counted a restatement dated up to one week after the period's last Monday. It now ends at the period's Sunday, so the week of 2026-07-06 (P1-Q1) no longer carries the 2026-07-13 Mid-Atlantic restatement. No frozen fixture used that week.

## Tests

`tests/test_restatement.py`: views, P1-Q1 figures and labels, claim evidence from the governed views, P2-Q5 and P3-Q6 §2 line and one card, both triggers, the boundary, a brief with no restatement, the leader view (card, no SQL), the agent session's `restatement_stories`. Results: `tests/test_restatement.py` 13 passed; with `tests/test_memo.py`, `tests/test_triage.py`, `tests/test_charts.py`, `tests/test_data_load.py`, `tests/test_mcp_server.py`, `tests/test_projection.py`, `tests/test_agent_build3.py`: 104 passed, 1 failed (`test_triage.py::test_answer_unchanged`, the frozen scripted answers). Cause: the two fixture entries for the restated weeks (2026-04-06 and 2026-07-13 Mid-Atlantic) now carry the change in the Restated line, the restatement block and the Assumptions item, and their claims renumber. Those two entries were regenerated (the other four are byte-identical in content); the test then passes.

## Open

- `tests/fixtures/scripted_answers.json`: two entries regenerated (above). Other packets that change briefs must regenerate the same file; merge it by regenerating, not by hand.
- Scripted run, gate and the three cases' scores: integrator (I1).
- Packets P, S, N, D also touch `memo.py`, `pipeline.py` and `server.py`; my edits there are new functions plus call-site lines.
