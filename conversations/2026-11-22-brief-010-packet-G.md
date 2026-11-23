# 2026-11-22 brief-010 packet G: golden definitions and Michael's golden review

Worktree `pa-010-G`, branch `feature/brief-010-golden` (base: `feature/brief-010-targets`). Owner: packet G (`eval/` only). No change to `src/`, `agents/` or `frontend/`. Not pushed.

## What changed

**G1, `eval/harness/cases.py`, `systems.py`, `run.py`**
- `Definition` (eval-side twin of `tools/definition.py`, same JSON names, `extra=forbid`): `first_week`, `last_week`, `comparison`, `territories`, `measure`, `grain`, `relative_to`. Not imported from `src/`.
- `Case.definition`; the top-level `comparison:` is gone from the YAML. A `before` validator reads an old top-level `comparison:` into `definition.comparison` (an explicit `definition.comparison` wins). `Case.comparison` stays as a read-only property so existing callers and tests work; it returns None for the house default (previous 4 weeks), so "the case chose a comparison" means what it did before (WIN-1, WIN-2, P1-Q5, P2-Q3, P2-Q4, P4-Q4).
- `inputs()` carries `definition` (every field; the house default comparison goes as `None`, which means the same and avoids an explicit comparison refusing a release-wide Promotion review). `expectations()["definition"]` keeps the full explicit form. The expected scope's `comparison` stays None for the default, so `scope_match` is unchanged.
- Harness: `predict_fn` takes `definition`; `systems.definition_option(fn, definition)` passes it only to a `predict` / `predict_follow_up` / `_answer` that names a `definition` parameter (signature check). `BriefingScripted` and `BriefingAgent` accept it and forward it to their `_answer` only when that takes it. `comparison=` is still passed as before. Nothing breaks before the backend packet (D-B) lands; once its `answer(..., definition=...)` exists the harness starts passing it, with no further eval change.
- `Finding.measure` (`trx` | `nbrx` | `bxa_share` | `competitor_share`, None = BXA TRx). `finding_recall` untouched; it reads findings as dicts and ignores the new field (tested).

**G2, golden YAML (all 32 Briefing cases) and `eval/golden/CHANGELOG.md`**
- Explicit `definition:` block on every case. Weeks come from `derive_scope(question)`: null for questions with no prefix (P2-Q6, P4-Q2, P4-Q3, P4-Q5, P4-Q6). Comparison as encoded, else `previous` 4. `territories: like_for_like`, `measure: trx` (P1-Q4: `both`), `grain` all five, `relative_to: other_territories`.
- Every `must` fact and every finding is `reviewed: true` (context facts keep their value).
- Plan cut `plan:SYN_MID_ATLANTIC_MEDICARE_PART_D_1` + `needs: plan_cut` on findings P1-Q4 `mid_atlantic_plan_nbrx_drop`, P2-Q2 and P2-Q4 `mid_atlantic_plan_access`, P4-Q4 `mid_atlantic_access_restored`.
- `needs`: `plan_cut` on every `plan_*` fact of those four cases (including the context tier / prior-auth / step-therapy facts, since the rule was "plan_* ids"); `segment_pct` on P4-Q2 `gl_cash_change_pct`, `se_commercial_change_pct`; `restatement` on P1-Q1 `gl_bxa_trx_naive_sum`, `gl_bxa_trx_deduplicated`, P2-Q5 `trx_signed_off`, `trx_restated`, `restatement_change_pct` and finding `mid_atlantic_restated_figure`, P3-Q6 `ma_restated_old`, `ma_restated_new` and its finding; `national_card` on the NATIONAL competitor findings P1-Q5 `national_metacora_competitor` and P3-Q4 `national_metacora_continuing`.
- Measures: P3-Q1 `national_metacora_share_gain` `bxa_share` (down); P3-Q4 `national_metacora_continuing` `competitor_share` (flat); P1-Q5 `national_metacora_competitor` `competitor_share` (direction left null = any).

## Like-for-like restatements (old -> new, all from SQL; none from system output)

The brief's rule (`stages.resolve`): a territory is reportable when its row in `reporting.v_feed_health` is PASS in every week of the period and the baseline together; the period mean sums those territories and divides by the weeks counted; a calendar (holiday) week that is a minority of the period leaves the period (`p.weeks`). I mirrored that in plain read-only SQL (`with ok as (... v_feed_health ... group by 1 having count(*) = N and count(*) filter (where health_status = 'PASS') = N)` joined to `reporting.v_weekly_rx_kpis`). My SQL was written and run independently of the brief's output; it reproduced Michael's expected brief figures.

| Case | Fact | Old | New | Exact | Note |
| :- | :- | -: | -: | -: | :- |
| P2-Q3 | `sc_change_pct` | -4.2 | -2.9 | -2.8728 | 6 of 7 reportable plus South Central (7 of 8; Great Lakes withheld); 4 weeks 2026-08-31, 09-14, 09-21, 09-28 (Labor Day week 09-07 out) against 2026-07-06 to 07-27 |
| P2-Q3 | `other_territories_change_pct` | 11.1 | 9.1 | 9.1125 | the other six |
| P2-Q3 | `sc_gap_points` (context) | 15.3 | 12.0 | 11.9853 | not on the list; restated with the two above so the sentence "a gap of ... points" stays true |
| P2-Q4 | `national_change_pct` | 9.0 | 10.1 | 10.0959 | all 8 reportable; 12 weeks (Labor Day week 2025-09-01 out) against 2025-06-02 to 07-28 (9 weeks) |
| P2-Q4 | `ma_change_pct` | 3.2 | 4.3 | 4.3308 | |
| P1-Q5 | `national_vs_4wk_avg_pct` (must) | -10.8 | -13.8 | -13.7677 | 7 of 8 (New England's May feed is withheld) |
| P1-Q5 | `national_gap_vs_4wk_avg` (context) | 467 | 556 | 556.25 | restated so the prose stays consistent |
| P1-Q5 | `national_like_for_like_bxa_trx` (new, context, reviewed false) | | 3,484 | 3484 | the prose states it |

Reference prose updated: P2-Q3 ("Like for like (the seven territories that report in every week compared, Labor Day week left out), South Central BXA TRx slipped 2.9% from July while the other territories rose 9.1%, a gap of 12.0 points."), P2-Q4 ("like for like, BXA TRx rose 10.1% against June and July. Mid-Atlantic rose only 4.3%."), P1-Q5 ("National BXA TRx was 3,860. Like for like, on the 7 of 8 territories ... it was 3,484, which is 556 below its average for the four May weeks (-13.8%)", and "about half" became "a little under half": Pacific's gap is 245 of 556, 44%).

## Not reproduced / left as is (for Michael or the next packet)

- Nothing failed to reproduce: the four expected brief figures match (South Central -2.9, others +9.1, national +10.1, Mid-Atlantic +4.3, P1-Q5 -13.8 on 7 of 8).
- P2-Q4 `plan_change_pct` -22.5 and `ma_other_channels_change_pct` 15.1 (and the P2-Q4 plan NBRx facts) still count the Labor Day week; not on Michael's list, so unchanged. If the brief's cut card computes them with the holiday week out, those two will differ slightly.
- P1-Q4: its numbers (15.0 NBRx over 13 weeks against 23.8 over the 9 weeks before) do not follow the previous-4-weeks comparison its definition states. Left as approved; the finding `mid_atlantic_plan_nbrx_drop` has no `measure` (the list set only three), although it is about NBRx. Setting `measure: nbrx` there is a one-line change if Michael wants it.
- `sc_gap_points`, `national_gap_vs_4wk_avg` and the new 3,484 fact are context facts and `reviewed: false` (the new one) / unchanged (the two restated): they are mine, not Michael's.
- `national_bxa_trx` 3,860 (P1-Q5, all 8 territories) kept as a true all-territory fact.
- `must_say` blocks keep `reviewed: false` (the decision covers must-state facts and findings only).
- Findings with a `cut` are met only by a cut card (core-011 FR-017); the scripted run builds none until packet P, so `finding_recall` for P1-Q4, P2-Q2, P2-Q4 and P4-Q4 drops now. Report-only, and exactly what `needs: plan_cut` is for.
- The like-for-like facts hard-code the week lists and gate counts (`count(*) = 9` etc.); if a case's period moves, its SQL moves with it.

## Tests

- `uv run python -m eval check`: 181 of 181 facts recompute (was 179 of 181 before the P2-Q4 week count was fixed to 22; final run clean).
- New `eval/tests/test_definition.py`: every case states every field and has no top-level `comparison`; period equals `derive_scope`; measure; explicit comparison; old `comparison:` mapping (and explicit wins); old file without a comparison loads with no definition; default comparison goes as None while expectations keep it; definition validation; signature guard; finding `measure` and `finding_recall` does not crash; the review decisions (reviewed flags, cuts, needs, restated values and prose).
- `uv run pytest -q eval/tests --deselect eval/tests/test_run_smoke.py`: see PROJECT_STATE line below / final report. No eval run, no full suite.

## Next step

Packet D-B: have the engines take `definition=` (the harness already passes it when the parameter exists). Then packets P, S, R, N raise the `needs`-tagged facts and findings. `PROJECT_STATE.md` is left for the integrator.
