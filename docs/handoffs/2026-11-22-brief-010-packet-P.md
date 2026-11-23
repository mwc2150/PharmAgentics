# brief-010 packet P: plan cut cards (2026-11-22)

Branch `feature/brief-010-plancuts` (worktree `pa-010-P`), on the merged brief-010 branch (definition, golden definitions, national
card, restatement detail, brief-009 events). Tasks P1 to P3 in `specs/brief-010-target-analyses/tasks.md` are ticked; P4 (the scripted
run and gate, the Haiku run) is the integrator's. Spec: brief-010 FR-001, FR-002, FR-007, FR-008, FR-009, User Story 1.

## What was built

- `tools/splits.py`
  - `screen_cuts(reg, p, territories)` (no claims): per story territory, per plan, the primary measure on the period against the
    comparison weeks. A plan is flagged when its direction runs against its territory's (neither inside the flat band, plan change at
    least `CUT_FLOOR` = 10%), or when the access check supports an access change on that plan (`lag_checks.check_access(plan=...)` on a
    scratch registry: the months of the period and the two weeks before it, lined up with the plan's TRx). Cell size is the plan's TRx a
    week (the smaller of the two sides) whatever the measure, because weekly NBRx is always under `SMALL_CELL` (50); below it the plan gets
    no card and nothing is quoted. At most `MOST_CUT_CARDS` = 2, largest absolute change in the primary measure first. BXA only, and only
    when the definition's grain has `plan` and the brief has comparison weeks and is not a calendar week.
  - `cut_figures(reg, p, territory, plan)`: the claims (before, after, percent per measure the definition holds, the territory's own
    change). Labels: grain "plan", cut `plan:<id>`; an extra measure is under `reg.under(measure=...)`. Levels use the new `dec1` format
    for NBRx (`registry.FORMATS`), `int` for TRx. `plan_territory(reg, plan)`.
- `tools/lag_checks.py`: `check_access(..., plan=None)`; with a plan it considers only that plan's events (text "on this plan").
- `tools/memo.py`
  - `cut_checks`, `cut_card`, `cut_block`. Card shape: `{headline, confidence, drivers_checked, territory, cut: "plan:<id>", direction,
    directions: {measure: dir}, drivers_supported, drivers_ruled_out}`. Headline: "Medicare Part D plan one in Mid-Atlantic fell from
    {158} to {145} TRx a week (down {8.0%}), while Mid-Atlantic rose {9.9%}." ("and" when the plan moves with its territory; the primary
    measure only). Block id `cut:<plan>`, title "Medicare Part D plan one in Mid-Atlantic" (the triage card has the same title, so a left-out line reads "Mid-Atlantic, Medicare Part D plan one in Mid-Atlantic"). Visible `lines`: one sentence per measure the
    definition holds (after, before, change; "... averaged X a week on the comparison weeks against Y before (down Z)"), then the
    "Confidence: ... Leading driver: ..." line. Folded `detail`: "Checked for this plan, in this order:" plus the five checks (access is the
    plan's own) and a line saying the other four carry the territory's verdicts. Lines and detail both reach the scored `answer` (FR-009).
  - Drivers: the plan-scoped access verdict; data, promotion, supply and competitor are the territory story's verdicts (they have no plan
    scope), taken from the story's own checks when it ran them, else run again with the same call. `directions` lets a new-patients finding
    score on NBRx (P1-Q4: `{"nbrx": "down", "trx": "down"}`).
  - Budget (FR-008): `compose` is now `_compose` plus the shrink. `WORD_BUDGET` = 836 (mirrors `eval.harness.scorers.WORD_BUDGET["analyst"]`,
    a test keeps them equal), `visible_words(sections)` is the scorer's `count_words` over compose's sections. Over the budget, territory
    cards (block ids `territory:` and `plan:`) move their `lines` into the folded detail, longest first, until it fits or none is left.
    Cut, national, restatement and promotion blocks never shrink; nothing is dropped. Applies to both engines (both compose through it).
    The flattened `answer` is the unshrunk brief's, word for word (the shrink changes only the sections: where a reader finds the lines).
- `api/views.py`: the leader view of a cut section has `text` and `prose` empty (the card headline only; `CARD_FIELDS` is unchanged, so no
  `cut` or `directions` reaches a leader).
- Scripted engine (`briefing_baseline/pipeline.py`): `Front.cuts` (screened in stage 3 over the first `MAX_STORIES` story territories,
  no claims), `default_order(found, cuts)`, cut cards built after the territory stories and inserted after their territory's story (and
  earlier cut cards), reusing that story's checks. `_story` info carries `checks`. A brief without a flagged plan makes the same claims
  in the same order as before.
- Triage (`briefing_baseline/triage.py`): `_cut_card` (kind "cut", id `cut:<plan>`, proposed "investigate", never over the cap), between the
  territory stories and the competitor. The plan id changes only for briefs that have a cut card.
- Agent engine: `plan.apply` gives cut cards no hypotheses; `investigate` skips them; `memo_close(competitor, cuts)` (MCP admin tool and
  `RunSession`) returns `cut_stories` and puts each card in `story_cards` and `story_details` keyed by `cut:<plan>`; `write.place_cuts`,
  `assemble` (key, title), `chart_targets` (no chart for a cut), `RAW_ID` (`cut:`); the Writer gets the cut story and words it in one or two
  sentences (`writer.md`); the Manager prompt (`manager_triage.md`) explains cut cards. Contract note added to
  `specs/brief-003-narrative-renderer/contracts/mcp-admin-tools.md`.

## Golden targets (scripted engine, before to after)

| Case | Cut card | Direction | Drivers | Plan facts stated | Findings |
| :- | :- | :- | :- | :- | :- |
| P1-Q4 | MID_ATLANTIC `plan:SYN_MID_ATLANTIC_MEDICARE_PART_D_1` | down (nbrx down, trx down) | access supported; data, promotion, supply, competitor ruled out | plan_nbrx_change_pct, plan_nbrx_before_per_week 23.8, plan_nbrx_after_per_week 15.9 (key facts 0 of 3 to 3 of 3) | 0 of 2 to 2 of 2 points |
| P2-Q2 | same | down (trx) | same | plan_trx_before 158, plan_trx_after 145, plan_change_pct -8.0 | 0 of 6 to 6 of 6 |
| P2-Q4 | same | down | same | plan_change_pct -20.7 | 0 of 2 to 2 of 2 |
| P4-Q4 | same | up | access supported; promotion ruled out (and the rest) | plan_trx_summer 183, plan_trx_gap 222 (plan_change_pct) | 0 of 3 to 3 of 3 |

Analyst words (`count_words`): P1-Q4 898 to 817, P2-Q2 572 to 620, P2-Q4 765 to 813, P4-Q4 780 to 828; all inside 836. P1-Q4 stays inside only
because the Mid-Atlantic territory card shrinks to its headline.

Other cases the screen flags (not targets): P2-Q3 (South Central, a Medicare Part D plan against its territory) and FU-6 (Southeast Commercial
plan two, against its territory). They now get a cut card; the word budget for them is the integrator's gate.

## Decisions to confirm (Michael)

- The `against` floor is 10% and "just before" is the access check's two-week lag. Both are constants in `splits.py` (`CUT_FLOOR`) and
  `lag_checks.DRIVER_LAGS`.
- Cut cards reuse the territory's data, promotion, supply and competitor verdicts (the checks have no plan scope). A territory-level
  "promotion supported" therefore also shows on the plan's card.
- A small cell gets no card at all (rather than a card naming it noisy); the territory's folded splits still mark small cells.
- The leader sees the cut card headline only, and the analyst view's visible text for a shrunk territory card is empty (its headline
  stays; the lines are in the detail). The frontend (D-U's) renders a section with an empty `text`: look at it in the real-app check (I3).

## Tests (focused only; no full suite, no eval run, no model)

- New `tests/test_plan_cuts.py` (32 tests): the four golden cases (card territory, cut, direction, `directions`, drivers; the cut text
  for each measure; the golden plan facts and findings through the scorer's own `key_fact_counts` and `finding_counts`), the order (cut
  after its territory), the headline, claim labels, the leader view (headline only), a brief with a story and no flagged plan (P4-Q1), the
  screen (access, against, two at most and ordered, small cell, no plan grain), the budget (no shrink under it, longest first, a cut card
  never, nothing dropped, `visible_words` equals the scorer's `count_words`, P1-Q4 inside the budget), triage cards, run with a decision that
  drops the cut, the Manager (`cards_text`, no hypotheses, may drop), and the agent session's `memo_close(cuts=...)` against the scripted
  card and the `assemble` order.
- Fixtures regenerated deliberately: `tests/fixtures/scripted_answers.json`, the 2026-07-13 Mid-Atlantic entry only (a new cut card for Medicare Part D plan two, which rose 44.3% while Mid-Atlantic fell; the other five entries are unchanged); `tests/fixtures/brief010_db_baseline.json`, entries P1-Q4, P2-Q2 and P4-Q4 (the cut card) and P1-Q1 (stale on the merged base: packet R's window no longer reports the 2026-04-06 restatement in the week of 2026-07-06; regenerated from the current engine). The other five entries are unchanged. Merge note: that file is one line of compact JSON, so a conflict with the integrator's copy is all or nothing; regenerate the four entries with the engine if it conflicts.

## Results



Last run (focused, one process, 70 minutes): `tests/test_plan_cuts.py` 33, `test_triage.py`, `test_agent_build3.py`, `test_restatement.py`,
`test_memo.py`, `eval/tests/test_national_measure.py` all pass; 183 passed, 8 failed, and the 8 are not packet P's:

- `test_brief_definition.py::test_the_pre_selected_definition_reproduces_todays_brief[P1-Q1, P1-Q4, P2-Q2, P4-Q4]`: ran against the old
  fixture (collected before the regeneration above); P1-Q1 and P1-Q4 re-run green on the regenerated fixture.
- `test_brief_definition.py::test_grain_without_territory..., test_relative_to_sets_what_a_story_is_set_against,
  test_two_comparisons_show_both_figures_...`: their `cards()` helper counts the NATIONAL competitor card as a territory story. The
  integrator already fixed this on `feature/brief-010-targets`.
- `eval/tests/test_targets_cuts.py::test_measured_anchor_counts_still_hold`: stale on the merged base (P1-Q2 627/589 against 622/584,
  all five anchors +5 for the holiday sentence). The integrator re-measured it to P1-Q2 627/589, P1-Q3 399/366, P1-Q6 503/469,
  P3-Q5 693/564, P4-Q1 908/777. With packet P, P4-Q1 is **784 analyst / 750 leader**, not 908/777, because FR-008 shrinks the Great Lakes
  card to its headline (tested in `test_the_shrink_brings_p4_q1_back_inside_the_analyst_budget`). Decide which P4-Q1 count the anchor
  test holds. Packet P alone cannot bring the leader view under 705: the shrink is for the analyst view.
- Left in `test_memo.py` (stale since packet N): `drivers_checked == ["competitor"]` and `drivers_ruled_out == []` on the national card now
  read `[0] == "competitor"` and a subset of access, promotion, supply (the integrator made the same change).

Open issues: P2-Q3 and FU-6 get a cut card (a plan against its territory); the 2026-07-13 Mid-Atlantic brief reaches 858 words with
both territory cards already shrunk (the cut card and the restatement card are never shrunk), so `over_word_budget` can still trip there.
The Haiku run (agent writer words cut cards in one or two sentences; extra prose adds words) and the real-app look at a shrunk card
(empty `text`, headline kept) are the integrator's.
