# brief-010 packet C: continuing cards (2026-11-23)

Branch `feature/brief-010-continuing` (worktree `pa-010-C`), on packet P's tip `3653240`. Spec: brief-010 FR-010; tasks C1 to C4 ticked.
The gap: golden P1-Q6 (week of 2026-08-24) expects a Southeast card (down, promotion supported). Southeast's rep coverage lapsed
2026-08-03 to 2026-08-31, so against the previous four weeks (three of them inside the lapse) it looks flat and triage told no story.

## What was built

- `src/pharmagentics/tools/continuing.py` (new)
  - `screen(reg, p, covered, cut_plans)`: events still running in the period, no claims. Lapses come from `promotion.lapses`
    (`LAPSE_RATIO`, `LAPSE_WEEKS`); access restrictions from `checks.access_events` over the whole release, paired with their relief
    (a restriction runs from the Monday on or after its month to the Monday before the relief month). Running = began before the first
    period week, not ended before it; a lapse must also be `LAPSE_WEEKS` old by the period's last week. The territory (lapse) or plan
    (access) must be down at least `MATERIAL_CHANGE` against the four weeks before the event; a plan must clear `SMALL_CELL`. Skips
    territories in `covered` (a regular story card) and plans in `cut_plans`. One card a territory, at most `MOST_CONTINUING` = 2.
  - `figures`, `card`, `block`, `place`: figures per measure against the four weeks before the event, as claim tokens labelled
    `comparison` = those weeks and `comparison_kind` = `before_event`. The event's own driver (promotion for a lapse, access for a
    restriction) is supported by construction with its own claim-token text; data, supply, competitor and the other driver come from
    `run_checks` on the period against the pre-event weeks. Card: `continuing: true`, `since: <ISO week>`, `cut` = `plan:<id>` for
    access, None for a lapse, `direction`, `directions`, drivers supported and ruled out. Text says "continuing since <week>".
- Pipeline (`briefing_baseline/pipeline.py`): `Front.continuing`; `default_order` adds `continuing:<territory>` after the cut cards;
  the block is built after the regular cards, placed after the last territory, plan, cut or continuing block and before the national
  card, and joins `told` so §1 and §5 (a next check) include it.
- Triage (`triage.py`): a candidate card of kind `continuing`, never over the cap, before the national card.
- Agent engine: `plan.apply` treats it as coded (no drivers), `investigate` skips it, `memo_close(competitor, cuts, running)` builds it
  (`continuing_stories`, cards, details, §1 and §5 entry), `write.place_continuing`, the writer and manager prompts, and the raw-ID guard.
  The agent's `__init__` passes `running` from the kept `continuing:` ids.
- Not touched: national and competitor card code, the scorer, the Forecast lane, constitutions.

## Results

- P1-Q6 before: Southeast card absent (finding 0 of 2 points). After: card Southeast, down, promotion supported, since 2026-08-03
  (2 of 2). Headline: "Southeast, continuing since 2026-08-03: TRx fell from 639 to 469 a week (down 26.6%) against the four weeks
  before the rep coverage lapse began." `false_drivers` 0.
- Direct per-case scoring (same scorers, one pipeline call each, no MLflow): P1-Q2 1/1, P1-Q4 2/2, P2-Q2 6/6, P2-Q4 2/2, P4-Q4 3/3,
  P4-Q1 2/2, P2-Q5 2/2, all unchanged, none gains a continuing card, `false_drivers` 0 throughout. P1-Q3 has no findings. P4-Q3 is the
  Promotion review (no cards path, unchanged).
- The Mid-Atlantic restriction (2025-08 to 2025-11) adds a card only to briefs inside it that give Mid-Atlantic no other card
  (for example the week of 2025-09-22: a Medicare Part D plan one card, down, access supported, since 2025-08-04).

## Decisions and unsettled

- A restriction counts as running until the week before its relief month (assumption in FR-010; Michael to confirm).
- The leader view shows the continuing card like a territory card (text and headline); only plan cut cards are headline-only there.
- Continuing cards add words to a brief only when they appear; the word-budget gate for P1-Q6 is the integrator's (full eval run).
- The Haiku agent run and gate for this packet are the integrator's.

## Tests (focused only; no full suite, no eval run, no model)

- New `tests/test_continuing_card.py` (20 tests, all pass): P1-Q6 Southeast card (down, promotion supported, since 2026-08-03, claims
  labelled `before_event` and set against 2026-07-06 to 2026-07-27, scores the golden finding in full), order and §5 next check, none a
  week after the lapse ended or before it counts, no duplicate for a territory with a regular story or a plan with a cut card, the
  access plan card (week of 2025-09-22), none on the four golden Mid-Atlantic briefs, triage, decision drop, Manager, agent session.
- Run once with `test_triage`, `test_brief_definition`, `test_plan_cuts`, `test_agent_build3`, `test_memo`: 158 passed, 7 failed.
  Four were this packet's deliberate changes and are fixed: `test_answer_unchanged` and `reproduces_todays_brief[CMP-3]` (fixtures,
  below), `test_claim_labels_name_the_value_of_each_field...` (the label set gains `before_event`), `test_blocks_follow_the_schema_for_a_one_week_brief`
  (the week of 2026-08-24 now opens with the Southeast card; the national card is looked up by territory). Those four re-ran green.
  The other three are not packet C's (the `cards()` helper in `test_brief_definition.py` counts the NATIONAL card as a territory story;
  already noted in the packet P handoff): `test_grain_without_territory...`, `test_relative_to_sets_what_a_story_is_set_against`,
  `test_two_comparisons_show_both_figures_...`.
- Fixtures regenerated by the engine (never by hand): `tests/fixtures/scripted_answers.json`, the 2026-04-06 entry only (Great Lakes lapse
  still running that week: a continuing card); `tests/fixtures/brief010_db_baseline.json`, entry CMP-3 only (week of 2026-08-24, six-week
  comparison: the Southeast card). Merge by regenerating: both files conflict all or nothing.
