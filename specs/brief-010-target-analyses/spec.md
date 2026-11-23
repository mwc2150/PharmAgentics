# Feature Specification: The Analyses the Targets Need

**Spec ID**: `brief-010-target-analyses` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `feature/brief-010-targets`
**Created**: 2026-11-22 | **Updated**: 2026-11-23
**Status**: Built and integrated (2026-11-23). Packets D-B, D-U, G, N, R, P, S, X, NC, C and I; integration and review fixes. Work packets in `tasks.md`, file contract in `plan.md`.
**Input**: Grill with Michael, 2026-11-22 (night). core-011 SC-002 (key-fact recall ≥ 0.85, finding recall ≥ 0.90, inside the word budget) and FR-016 to FR-021. Scripted run `ef64671bd20941cc804e19a665c971dc` (brief-008 polish) scored on exact values. Briefing constitution B-II, B-III, B-VI, B-VII.

## Why

On the scripted engine the brief states 45 of 63 must-state facts (0.714) and scores 0.750 on findings. The misses are not wording. They are four things the brief does not say in the text a reader sees:

| Capability (`needs`) | Cases | Lost |
| :- | :- | :- |
| `plan_cut`: a plan that moved against its territory, with its level before and after and its change | P1-Q4, P2-Q2, P2-Q4, P4-Q4 | 9 facts, 2 findings |
| `segment_pct`: a channel or specialty's change in percent | P4-Q2 (and P2-Q4 once reviewed) | 2 to 5 facts |
| `restatement`: the duplicate overstatement, the signed-off and restated figures, a card for the restated territory | P1-Q1, P2-Q5, P3-Q6 | 3 to 7 facts, 1 to 2 findings |
| `national_card`: the competitor story as a national card | P1-Q5, P3-Q4 | 2 findings |

Some of it is already computed. The plan, specialty and channel splits are in each story's folded detail as "TRx a week" changes (brief-008 FR-004), and the feed gate already counts duplicate keys. But folded detail is not in the scored answer, and none of it prints a level or a percent. The competitor card exists but has no territory, so a national finding can never match it.

## Clarifications

### Session 2026-11-22 (grill with Michael; do not reopen)

- Q: Optimize for what? → A: **The core-011 targets, not plain recall**: key-fact recall ≥ 0.85, finding recall ≥ 0.90, every case inside the measured word budget (core-011 FR-020). Numbers are scored on exact values (core-011 FR-016).
- Q: When? → A: **After the golden review** of the 63 must-state facts and the 18 scored findings, and **after brief-009 merges** (it changes the same pipeline). This spec is written during the review; it cites facts by ID and follows the review's changes.
- Q: Scope? → A: **Exactly the four capabilities above, in this order**: plan cuts, segment and channel percent, restatement detail, national card. Holiday year-over-year, a peer-trend counterfactual and share trajectory wait for a later spec unless a golden case needs them.
- Q: A plan that fell inside a territory that rose? → A: **A cut card beside the territory card** (core-011 FR-017). When the brief is near its word budget the territory card shrinks to its headline; the cut card is never dropped.
- Q: National card? → A: **Built by code, at most one a brief**, when a check is supported at national level (competitor share first).
- Q: Who finds the cuts? → A: **Code** (deterministic first). Code screens plans, channels and specialties, builds the cut and national cards and fills every number. The agent's Manager sees cut cards as candidate stories and chooses what to tell; the Writer words them around claim tokens.
- Q: Why do golden and brief disagree? → A: **Unstated assumptions** (raw or deduplicated, which territories count, TRx or NBRx, plan or territory, against what). Every brief is built from an explicit **brief definition** the analyst selects at the start, and the golden set and the scorer read the same definition.
- Q: Which choices? → A: **Six selectors, always shown at the start of the form, whatever the question**: period (first and last week), comparison (previous N weeks, last year, named weeks, or the pre-launch weeks: the four weeks before the competitor launched), territories counted (like-for-like, all reportable, projected national), measure (TRx, NBRx, or both), grain (any of national, territory, plan, channel, specialty) and relative to (the other territories, national, or nothing). Each has a pre-selected value; nothing is enforced or hidden; there is no team setting. The scope reader proposes values from the question and the analyst confirms them. Data basis is not a choice: metrics come only from the governed views; raw figures appear only as labelled tie-outs.
- Q: Holiday weeks? → A: **Always left out of the period, in every brief and every golden case.** A stated assumption printed in the Assumptions block, not a selector.
- Q: P3-Q1 ("what changed this week")? → A: A case-definition question: its golden finding was written against the pre-launch weeks, so its definition's comparison is `pre_launch` (Michael, 2026-11-22).
- Q: Several values at once? → A: **Any combination.** Every selector takes one or more values; the **first is the primary**. The primary drives story choice, cards and the direction a finding is scored against; each extra value adds labelled figures beside the primary (KPI strip, territory table, story headlines), never a second set of stories. A single value (and measure "both") is read as a list. The word budget still applies.
- Q: Golden cases? → A: Each case carries the **same explicit definition** (it replaces `comparison`); its facts are computed under it; a finding names its measure (BXA TRx unless it says BXA share or a competitor's share).
- Q: Merge bar? → A: Each packet, on the scripted engine: pooled key-fact recall and finding recall do not fall, no case goes over the word budget, and the packet raises its own target cases. The Haiku agent runs after the plan-cut packet and at the end; "numbers lost by the agent" (core-011 FR-013) must be 0.

### Session 2026-11-23 (grill with Michael, data notes; do not reopen)

- Q: A restatement is a fact about what? → A: **The data record, not the business.** The restatement card (FR-005) has its own measure, `restated_figure`, and carries `directions: {"restated_figure": up|down|flat}` beside `direction`. A card covers the measures in its `directions`, so it never counts as the territory's TRx story: a finding `withheld: true` for that territory is still met. The golden findings `mid_atlantic_restated_figure` (P2-Q5, P3-Q6) name `measure: restated_figure`. The restatement stays prominent: the Bottom line data note and the never-shrunk restatement card are unchanged.
- Q: A national total that falls because a territory dropped out? → A: **A national data-artifact card, built by code** (FR-011), at most one a brief, beside the national competitor card (which covers share measures only).
- Q: P2-Q1's comparison? → A: **The previous 1 week** (`comparison: {kind: previous, weeks: 1}`); its facts already use the week before.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The plan behind a territory's number (Priority: P1)

A commercial analyst asks where Mid-Atlantic's change came from in the weeks of 2025-08-04 to 2025-10-27. Mid-Atlantic rose, but Medicare Part D plan one fell after its formulary change. The brief shows a cut card for that plan beside the Mid-Atlantic card: its TRx a week before and after, its change in percent, and access supported.

**Acceptance Scenarios**:
1. **Given** P2-Q2, **When** the scripted engine answers, **Then** a card with territory MID_ATLANTIC, cut `plan:SYN_MID_ATLANTIC_MEDICARE_PART_D_1`, direction down and access supported is in the brief, and `plan_trx_before_per_week`, `plan_trx_after_per_week` and `plan_change_pct` are stated in its text.
2. **Given** P1-Q4 (a new-patients question), **Then** the cut card states the plan's NBRx before and after and its change.

### User Story 2 - Which channels responded (Priority: P2)

A brand manager asks which segments and channels responded to the promotion lapse. Each lapsed territory's story names its largest channel and specialty movers in percent.

**Acceptance Scenarios**:
1. **Given** P4-Q2, **Then** `gl_cash_change_pct` and `se_commercial_change_pct` are stated, and small cells are named as noisy instead of quoted.

### User Story 3 - Can I quote this number (Priority: P2)

An analyst asks whether a figure ties out. The brief says how much a naive sum of the duplicated feed overstates the territory, and, where a week was restated, the signed-off and restated figures and the change, with a card for the restated territory.

**Acceptance Scenarios**:
1. **Given** P1-Q1, **Then** `gl_bxa_trx_naive_sum` and `gl_bxa_trx_deduplicated` are stated.
2. **Given** P2-Q5 or P3-Q6, **Then** the signed-off and restated figures are stated and a MID_ATLANTIC card with data supported and direction up is in the brief.

### User Story 4 - The competitor story at national level (Priority: P3)

A leader asks whether the issue is new or continuing. The competitor story is a national card whose direction is Metacora's share change on the comparison weeks.

**Acceptance Scenarios**:
1. **Given** P3-Q4, **Then** a NATIONAL card with competitor supported and direction flat is in the brief.

### Edge Cases

- A cut smaller than the small-cell floor (`splits.SMALL_CELL`) is never quoted as a level or a percent; it is named as noisy.
- A plan that moved with its territory and is not where a supported driver sits gets no card.
- No cut card ever names an individual prescriber or rep (B-VI); cuts are plan, channel or specialty only, and leaders see them as cards, never as split tables.
- When the feed gate withholds a territory, its restatement or duplicate figures are stated as data-quality facts, never folded into a national total.

## Requirements *(mandatory)*

- **FR-000a**: A brief MUST be built from a **brief definition** (`tools/definition.py`): `first_week`, `last_week`, `comparison`, `territories` (`like_for_like` | `all_reportable` | `projected`), `measure` (`trx` | `nbrx` | `both`), `grain` (subset of `national`, `territory`, `plan`, `channel`, `specialty`) and `relative_to` (`other_territories` | `national` | `none`). `comparison.kind` adds `pre_launch` (the four weeks before the competitor launched; refused for a period before the launch). Holiday weeks are always out of the period, and the Assumptions block says so. The pre-selected values (like-for-like, TRx, all five grains, other territories, the house comparison) reproduce today's brief exactly.
- **FR-000e**: Every definition field except the period MUST accept a list (one or more values; the first is the primary; a single value is read as a one-item list). Extra values add labelled figures beside the primary in the KPI strip, the territory table and story headlines; stories, cards and finding directions follow the primary. Claims record which value of each field they were made under. *(Form, 2026-11-23: Territories counted, Measure and Relative to show a Main choice and "Also show beside it" extras, sent as [main, ...extras]; Grain has no primary (the server keeps a fixed order), so it is plain checkboxes with a one-line description each. The Assumptions block says "X; also Y".)*
- **FR-000b**: The brief form MUST show the six selectors before the question is answered, pre-selected and editable; the scope reader only proposes values. The request carries the definition; the stored brief keeps it; the Assumptions block (both views) prints it in words.
- **FR-000c**: Both engines MUST honour every field: `territories` sets which territories a national figure counts; `measure` sets the KPI strip, territory table and story figures (both: NBRx beside TRx, labelled "new patients (NBRx)"); `grain` sets which levels get lines, stories, cut cards and splits; `relative_to` sets what a story's change is set against. Every claim records the definition fields it was made under plus its own grain and cut.
- **FR-000d**: The golden set MUST carry an explicit definition per Briefing case; the harness passes it to the system; facts are computed under it.
- **FR-001**: Code MUST screen each story territory's plans on the brief's comparison weeks and build a **cut card** for a plan whose change runs against its territory's, or that holds the access driver the checks support, at most two a brief, largest first. The card carries `territory`, `cut` (`plan:<id>`), `direction`, `drivers_supported`, `drivers_ruled_out` and a headline with the plan's readable name (brief-008 FR-004). The screen (packet P): a plan is flagged when its direction on the primary measure runs against its territory's and its own change reaches 10% (`splits.CUT_FLOOR`), or when the access check supports an access change on that plan in the period's months or up to two weeks before; a plan whose TRx a week is below `SMALL_CELL` on either side gets no card (the cell size is TRx whatever the measure). The card also carries `directions` (one direction per measure the definition holds, so a new-patients finding scores on its own measure). Its access verdict is scoped to the plan; data, promotion, supply and competitor have no plan scope, so the card reuses its territory's verdicts.
- **FR-002**: A cut card's unfolded text MUST state the cut's TRx a week before and after and its change in percent (Briefing percent format, brief-008 FR-016); for a new-patients question, NBRx instead. Every number is a claim token filled from a stored SQL query.
- **FR-003**: Each story's unfolded text MUST name its largest channel and specialty movers in percent, at most two, above the small-cell floor. The Promotion review MUST do the same for each lapsed territory.
- **FR-004**: When the feed gate withholds a territory for duplicate keys, the brief MUST state the naive sum, the deduplicated figure and the overstatement.
- **FR-005**: When `raw.restatement_log` has a restatement of a week in the brief's period for a territory, the brief MUST state the signed-off and restated figures and the change, and build a card for that territory with `data` supported and the restatement's direction. A brief reports a restatement when the restated week is inside its period or the restatement was published (its restated date) inside its period (assumption of packet R, printed in the Assumptions block; Michael to confirm). The figures come from `reporting.v_restatements`; the duplicate tie-out from `reporting.v_rx_duplicate_tieout`, labelled "raw, before deduplication". At most one restatement card a brief, the largest change.
- **FR-006**: The competitor story's card MUST be a national card: territory `NATIONAL`, direction from the change in Metacora's basket share on the comparison weeks (flat inside the house flat band), `competitor` supported when the competitor check supports it. At most one national card a brief.
- **FR-006a** (packet NC): Every brief that has the national grain MUST carry one national card, the competitor story's when Metacora has a reading and otherwise a card of its own titled "National BXA TRx" (no competitor line, never competitor supported). The card's `directions` MUST include `trx`: national BXA TRx on the primary comparison weeks, over the territories the brief counts, inside the house flat band (up above 0.5%, down below -0.5%). The card's `direction` is the share direction when Metacora has a reading, else the TRx direction. Any figure printed is a claim token (the KPI strip's own percent is reused).
- **FR-006b** (packet NC): `holiday` is supported on the national card only when the brief's period is calendar weeks (half or more of its weeks are holiday or plan-year-reset weeks) and the primary comparison weeks are not. The previous four weeks give national down with holiday supported (P3-Q2); the same weeks last year give national up with no holiday driver (WIN-1). `holiday` is in `drivers_checked` whenever it was supported.
- **FR-006c** (packet NC): Access, promotion and supply are ruled out nationally unless a territory that has its own story card in this brief supports the driver or cannot rule it out (inconclusive, insufficient, untested). A territory without a story does not keep a driver off the list, so P3-Q1 rules promotion out nationally. A calendar week opens no story, so its national card lists no ruled-out driver.
- **FR-007**: The agent engine MUST receive cut and national cards as candidate stories from code (triage) and carry them to the brief unchanged in their numbers; the Writer words them around claim tokens.
- **FR-008**: A brief near its word budget MUST shrink a territory card to its headline before it drops anything; a cut or national card is never dropped for length.
- **FR-009**: The scored `answer` MUST carry the new text (cards' unfolded text), so the eval scores what a reader sees.
- **FR-010**: The restatement card (FR-005) MUST be a data-record note with its own measure: `directions: {"restated_figure": <direction of the restatement>}` (and `direction`). A scorer matches a finding to a card only on a measure the card covers (FR-006), so a restatement card is never the territory's TRx story; the golden finding that expects it names `measure: restated_figure`, and a `withheld` finding for the same territory is met.
- **FR-011**: When the national change over the reportable territories differs materially from the like-for-like change because a territory dropped out of one period (withheld by the feed gate), the brief MUST add one national data-artifact card, built by code: territory `NATIONAL`, `cut` None, `direction` and `directions: {<primary measure>: ...}` the direction of the reportable-total change, `drivers_supported: ["data"]`, a headline of claim tokens naming the territory that dropped out ("National BXA TRx over the reportable territories fell 18.4%, but on the 7 territories that report both weeks it fell 3.6%: Mid-Atlantic is withheld."). **Materiality: the gap between the two changes reaches `stages.MATERIAL_GAP` (the house 8 points, `tools/stages.py`)**; the card is built from the KPI block's own claims (reportable-total change, like-for-like change, territory count), so it adds none. At most one a brief, in both engines (`memo.data_artifact_block`; the agent session returns `data_artifact_stories` with the restatement stories).
- **FR-012**: A territory whose promotion lapse or plan access restriction is still running in the brief's period MUST get a **continuing card**, so a lapse that hides inside the comparison weeks (Southeast, week of 2026-08-24, P1-Q6) still tells its story (`tools/continuing.py`). Code finds the events with the code that already finds them: lapses from `promotion.lapses` (`LAPSE_RATIO`, `LAPSE_WEEKS`), restrictions from `checks.access_events` (a restriction runs from the Monday on or after its month until the Monday before the relief month). An event is *running* when it began before the period's first week and had not ended before it (it may end inside it); a lapse must also have run `LAPSE_WEEKS` weeks by the period's last week, so a brief never reports a lapse that was not yet a lapse. The card's figures and direction are measured against the four weeks before the event began (`continuing.BASELINE_WEEKS`), not the comparison weeks, and the card says so ("continuing since 2026-08-03"). It supports the event's own driver (promotion for a lapse, access for a restriction, each with its figures as claim tokens); data, supply, competitor and the other driver come from the usual checks run on the period against the same pre-event weeks. The territory (a lapse) or plan (access) must have fallen by at least the material change (`stages.MATERIAL_CHANGE`) against that level, and a plan must clear `SMALL_CELL`. Only a territory with no regular story card or cut card in this brief gets one, and an access restriction whose plan already has a cut card gets none; one card a territory, at most two a brief (`MOST_CONTINUING`), largest change first. The card carries `continuing: true` and `since: <ISO week>`, plus the card fields of FR-001 (`cut` is `plan:<id>` for access, None for a lapse). In §3 it follows the regular territory and cut cards and precedes the national card; it joins §1 and §5 like a territory story (a next check). Triage proposes it as a candidate story (`kind: "continuing"`, id `continuing:<territory>`), the Manager keeps or drops it and orders no drivers, and the agent engine builds it at `memo_close` (`running=[territory]`). The scorer needs no change. Assumption (Michael to confirm): a restriction counts as running until the week before its relief month; the months-long Mid-Atlantic restriction (2025-08 to 2025-11) therefore adds a card only to briefs inside it that give Mid-Atlantic no other card.

## Success Criteria *(mandatory)*

- **SC-001**: On the scripted engine after all four packets: pooled key-fact recall ≥ 0.85, finding recall ≥ 0.90, `over_word_budget` 0. *(2026-11-23: met on recall, 1.000 and 1.000, run `60927c3280374d748a44c55ca309b8d1`. Michael dropped the word budget as a target the same day; it stays report-only, 8 briefs over.)*
- **SC-002**: The Haiku agent run at the end: the same finding recall as scripted or better, "numbers lost by the agent" 0, all seven gated checks 1.000.
- **SC-003**: The full suite and the scripted gate pass after every packet; Forecast scores are unchanged.
