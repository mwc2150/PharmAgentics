# Feature Specification: The Analyses the Targets Need

**Spec ID**: `brief-010-target-analyses` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `feature/brief-010-targets`
**Created**: 2026-11-22 | **Updated**: 2026-11-22
**Status**: Building. Packet D (the brief definition) first; the golden review was done in the grill of 2026-11-22. Work packets in `tasks.md`, file contract in `plan.md`.
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
- Q: P3-Q1 ("what changed this week")? → A: A case-definition question: its golden finding was written against the pre-launch weeks, so its definition chooses that comparison explicitly (pending Michael's confirmation, 2026-11-22).
- Q: Golden cases? → A: Each case carries the **same explicit definition** (it replaces `comparison`); its facts are computed under it; a finding names its measure (BXA TRx unless it says BXA share or a competitor's share).
- Q: Merge bar? → A: Each packet, on the scripted engine: pooled key-fact recall and finding recall do not fall, no case goes over the word budget, and the packet raises its own target cases. The Haiku agent runs after the plan-cut packet and at the end; "numbers lost by the agent" (core-011 FR-013) must be 0.

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
- **FR-000b**: The brief form MUST show the six selectors before the question is answered, pre-selected and editable; the scope reader only proposes values. The request carries the definition; the stored brief keeps it; the Assumptions block (both views) prints it in words.
- **FR-000c**: Both engines MUST honour every field: `territories` sets which territories a national figure counts; `measure` sets the KPI strip, territory table and story figures (both: NBRx beside TRx, labelled "new patients (NBRx)"); `grain` sets which levels get lines, stories, cut cards and splits; `relative_to` sets what a story's change is set against. Every claim records the definition fields it was made under plus its own grain and cut.
- **FR-000d**: The golden set MUST carry an explicit definition per Briefing case; the harness passes it to the system; facts are computed under it.
- **FR-001**: Code MUST screen each story territory's plans on the brief's comparison weeks and build a **cut card** for a plan whose change runs against its territory's, or that holds the access driver the checks support, at most two a brief, largest first. The card carries `territory`, `cut` (`plan:<id>`), `direction`, `drivers_supported`, `drivers_ruled_out` and a headline with the plan's readable name (brief-008 FR-004).
- **FR-002**: A cut card's unfolded text MUST state the cut's TRx a week before and after and its change in percent (Briefing percent format, brief-008 FR-016); for a new-patients question, NBRx instead. Every number is a claim token filled from a stored SQL query.
- **FR-003**: Each story's unfolded text MUST name its largest channel and specialty movers in percent, at most two, above the small-cell floor. The Promotion review MUST do the same for each lapsed territory.
- **FR-004**: When the feed gate withholds a territory for duplicate keys, the brief MUST state the naive sum, the deduplicated figure and the overstatement.
- **FR-005**: When `raw.restatement_log` has a restatement of a week in the brief's period for a territory, the brief MUST state the signed-off and restated figures and the change, and build a card for that territory with `data` supported and the restatement's direction. [NEEDS CLARIFICATION: how far back a restatement counts (brief-007 FR-010 window, open for Michael)]
- **FR-006**: The competitor story's card MUST be a national card: territory `NATIONAL`, direction from the change in Metacora's basket share on the comparison weeks (flat inside the house flat band), `competitor` supported when the competitor check supports it. At most one national card a brief.
- **FR-007**: The agent engine MUST receive cut and national cards as candidate stories from code (triage) and carry them to the brief unchanged in their numbers; the Writer words them around claim tokens.
- **FR-008**: A brief near its word budget MUST shrink a territory card to its headline before it drops anything; a cut or national card is never dropped for length.
- **FR-009**: The scored `answer` MUST carry the new text (cards' unfolded text), so the eval scores what a reader sees.

## Success Criteria *(mandatory)*

- **SC-001**: On the scripted engine after all four packets: pooled key-fact recall ≥ 0.85, finding recall ≥ 0.90, `over_word_budget` 0.
- **SC-002**: The Haiku agent run at the end: the same finding recall as scripted or better, "numbers lost by the agent" 0, all seven gated checks 1.000.
- **SC-003**: The full suite and the scripted gate pass after every packet; Forecast scores are unchanged.
