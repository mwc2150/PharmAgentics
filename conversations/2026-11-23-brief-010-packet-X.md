# brief-010 packet X: data notes (2026-11-23)

Branch `feature/brief-010-datanotes` (worktree `pa-010-X`), based on packet P (3653240). Spec: brief-010 FR-010, FR-011 and the Session 2026-11-23 Clarifications. Michael's decisions (grill, 2026-11-23); nothing reopened.

## What changed

- **Restatement card is a data-record note** (`tools/memo.py` `restatement_block`): the card now also carries `directions: {"restated_figure": "up"|"down"|"flat"}` (and keeps `direction`). Cards cover the measures in `directions` (packet N's rule), so it no longer covers `trx`: a finding `withheld: true` for that territory is met. Bottom line data note and the never-shrunk card are unchanged.
- **National data-artifact card** (`memo.data_artifact_block`, built from `facts["data_artifact"]`, which `stages._national_block` sets next to the existing "headline total of reportable cuts" line):
  - Condition: a territory is not in the like-for-like set (`len(tc) < len(p.terrs)`, as the existing artifact line), the existing line is already written (its 5-point screen), and **the two changes differ by at least `MATERIAL_GAP` (the house 8 points, `tools/stages.py`)**. `MATERIAL_CHANGE` is not used: the card is about the gap between the two figures, and the reportable-total change is shown whatever its size. (Easy to add: `abs(naive) >= MATERIAL_CHANGE * 100`.)
  - Card: `territory: "NATIONAL"`, `cut: None`, `direction` and `directions: {<primary measure>: ...}` = direction of the reportable-total change (house flat band), `confidence: "High"`, `drivers_checked: ["data quality"]`, `drivers_supported: ["data"]`, `drivers_ruled_out: []`. Headline: "National BXA TRx over the reportable territories fell {18.4%}, but on the {7} territories that report both weeks it fell {3.6%}: Mid-Atlantic is withheld." ("both periods" when the period or the comparison has more than one week; "are withheld" for several territories). Block id `data_artifact:NATIONAL`, title "National data artifact", one text line "Data story: ... Confidence: High. Leading driver: data."
  - No new claims: the tokens are the KPI block's own (reportable-total change = the existing `p2` claim, like-for-like change, territory count).
  - At most one a brief. Both engines: scripted `pipeline._brief` (before the restatement block); agent session `brief_sections()["data_artifact_stories"]`, appended by `briefing_agent/write.assemble` beside the restatement stories. It is a story block, not a triage candidate.
- **Eval**: `Measure` gains `restated_figure` (`eval/harness/cases.py`); `mid_atlantic_restated_figure` in P2-Q5 and P3-Q6 carries `measure: restated_figure`; P2-Q1's definition compares with the previous 1 week. `eval/golden/CHANGELOG.md` has one row. `eval/harness/scorers.py` needed no change (packet N's `_covers`).

## Tests

`tests/test_data_notes.py` (12 tests; each of the three briefs takes about 30 s): P2-Q1 has the card, no Mid-Atlantic TRx card (its only Mid-Atlantic card is the `restated_figure` one), finding recall through the scorer's own `finding_counts` is full on P2-Q1, P2-Q5 and P3-Q6; a routine brief has no artifact card; the leader view has the headline and no SQL, claims or `directions`; the agent session builds the same card. Results are in the PROJECT report below.

## Open

- `MATERIAL_CHANGE` not applied (above); Michael's call.
- A brief whose reportable-total and like-for-like changes are far apart in a multi-week period gets the card too (the headline says "both periods"). No golden case exercises it.
- Scripted run, gate and the target scores on the full set are the integrator's.
