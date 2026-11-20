# Feature Specification: Windows, Assumptions and Evidence in the Brief

**Spec ID**: `brief-007-windows-and-evidence` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: next branch after `feature/brief-memo-follow-ups` merges (not started)
**Created**: 2026-11-20 | **Updated**: 2026-11-20
**Status**: Draft v1. Not planned or built.
**Input**: Recall analysis of the rebased scripted run `e2599995` (2026-11-20); decisions taken with Michael on 2026-11-20; course slides Weeks 1–7 (Applied Data Science and AI in Pharma Commercial, Fall 2026); brief-003 v3 (memo outline and section numbers); brief-002 (baseline weeks); brief-006 (`split_change`); Briefing constitution B-I, B-III, B-VI and the Promotion constraint.

## Why

On the 24 single-turn Briefing golden cases, the memo brief states 0.406 of the golden numbers on both engines (0.388 before the memo). The model is not the cause: every number is code-built, and the agent and the scripted engine score the same. The missing recall splits into three gaps:

| Gap | Cases | Share of lost recall |
| :- | -: | -: |
| Campaign questions get a weekly brief with no promotion content; the four undated ones get the latest week | P4-Q1 to P4-Q6 | 40% (with P2-Q6, out of scope here) |
| Content the brief does not carry: splits of a change, per-territory changes, data-quality counts | P1-Q3, P1-Q4, P1-Q5, P2-Q1, P2-Q2, P2-Q4, P2-Q5, P3-Q2 | 33% |
| A number stated at a different value because the comparison window differs (verified on P3-Q5: golden 639 from the four July weeks, brief 636 from five weeks) | P1-Q1, P2-Q2, P3-Q2, P3-Q4, P3-Q5, P4-Q5 and others | 27% |

The slides set the standard this spec follows: compare mature weeks with mature weeks and flag restatements (Week 2, slides 24 and 37); promotion works with a carry-over, and a model of its return is the wrong tool without spend data or spend that varies (Week 3, slides 9 and 31–35); small denominators make noisy rates (Week 4, slides 14 and 34); a naive "after versus before" comparison mixes the effect with what caused the action (Week 5, slides 21–22); and every assumption is written down with its source (Week 6, slides 12–14).

## Clarifications

### Session 2026-11-20

Decided by Michael; do not reopen.

- Q: Which comparison window does the brief use by default? → A: **The 4 weeks immediately before the requested window**, for one-week and multi-week windows alike. This replaces the brief-002 rule (a baseline as long as the window, up to 13 weeks). The length is a semantic-layer setting (B-I).
- Q: Can the analyst choose the window? → A: **Yes.** A comparison picker next to the week and territory pickers: previous N weeks, the same weeks last year, or custom dates. Code applies the choice; the model never chooses it. The brief states the window it used as an assumption.
- Q: How are campaign and return-on-investment questions answered, given no spend data? → A: **A release-wide Promotion review**, not a model of return. It says whether a sustained push happened, compares each promotion lapse and return with the other territories as an association, says why return cannot be priced, and names the experiment that would settle it (a territory holdout).

- Q: How much of brief-007 goes into the memo pull request? → A: **Slice A only**: the 4-week default baseline, the window named in the brief, the per-territory change table, the feed-quality figures and the Assumptions block (User Stories 1 code side, 3 table, 4, 6). Slice B (Promotion review, lag test) and slice C (window picker, story splits) follow in a later pull request.

Planned with the decisions above, not objected to: the per-territory change table, the splits of a story's change, the feed-quality table, the lag test on driver checks and the Assumptions block.

Settled while writing the spec (recommended defaults; Michael may change them in `/speckit-clarify`):

- P2-Q6 ("Is this freeing my team's time…") asks for the version scorecard (EV-8.2 to EV-8.5), not a campaign read. It is out of scope for brief-007.
- A question is a promotion question when code finds a campaign, promotion, reach, response, lift or spend term in it; the question parser decides, not the model (B-II).
- The driver lag test covers 0, 1 and 2 weeks. The data shows at most a weak one-week lag (Great Lakes: association 0.46 at one week against 0.42 at zero; Southeast strongest at zero), so the lag is tested and stated, never assumed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The brief says what it compared with (Priority: P1)

Ace (P1) asks about Southeast for the weeks of 2026-08-03 to 2026-08-31. The brief compares them with the 4 weeks before (2026-07-06 to 2026-07-27) and says so beside the first comparison and in the Assumptions block. If Ace picks "same weeks last year" instead, the brief is rebuilt against those weeks and says that.

**Why this priority**: A comparison without its window cannot be checked or repeated, and the window is the largest single cause of numbers that differ from the golden answers.

**Independent Test**: Generate the P3-Q5 brief with the default window and again with "same weeks last year"; read the baseline values, the stated window, and the Assumptions block.

**Acceptance Scenarios**:

1. **Given** the P3-Q5 question, **When** the brief is built with the default window, **Then** the Southeast baseline is 639 TRx a week from 2026-07-06 to 2026-07-27, and the brief names those weeks.
2. **Given** a one-week question (P1-Q2), **When** the brief is built, **Then** the baseline is the 4 weeks before, as today.
3. **Given** the analyst picks "same weeks last year", **When** the brief is built, **Then** every comparison uses those weeks, the brief names them, and the Assumptions block records that the analyst chose them.
4. **Given** the window picker, **When** the analyst enters a custom window that overlaps the requested weeks or falls outside the release, **Then** the picker refuses it with the reason, before any brief is built.
5. **Given** any brief, **When** the agent writes prose, **Then** it cannot change the window; only the analyst's choice or the default applies.

---

### User Story 2 - Promotion review for campaign questions (Priority: P1)

Magdalena (P4) asks "Did the campaign reach the people it was meant to reach?" with no week. Instead of the latest-week brief, she gets a Promotion review over the whole release: whether a sustained push happened, where promotion lapsed and returned and what TRx did against the other territories, and why the release cannot say which channel worked or what a dollar returns.

**Why this priority**: Campaign questions are 40% of the lost recall, and today they get an answer to a different question.

**Independent Test**: Ask P4-Q1, P4-Q3 and P4-Q6 on both engines; compare the review with the golden reference answers.

**Acceptance Scenarios**:

1. **Given** an undated promotion question, **When** the brief is built, **Then** its scope is the whole release, and the review says whether any territory's rep calls or digital impressions stayed above their territory median long enough to count as a push (the golden answer: none exceeds 1.5 times the median; sample spikes last one week).
2. **Given** the Great Lakes lapse (P4-Q1), **When** the review describes it, **Then** it states calls before and during the lapse (about 48 a week, then about 20), digital impressions against their median (915 against 1,652), Great Lakes TRx against the other territories over the same weeks (−16.5% against +1.1%), and the recovery when calls returned (503 to 730 TRx in one week), and labels the link an association.
3. **Given** "Where should the next dollar go?" (P4-Q6), **When** the review answers, **Then** it says the release cannot rank channels or price a dollar because there is no spend data and calls and digital impressions fell together, gives the size of the lapses (about 120 to 200 TRx a week), and recommends discussing coverage backfill with sales operations at territory level.
4. **Given** any promotion review, **When** it is written, **Then** no line names or implies an individual rep (B-VI), and no line states a return on investment.
5. **Given** a dated promotion question for one territory (P4-Q4), **When** the brief is built, **Then** it is the normal brief for that scope, with promotion as one tested driver, plus the review's lapse comparison for that territory.

---

### User Story 3 - Per-territory changes and splits of a change (Priority: P2)

Ace asks "Which changes are big enough to make the brief?" (P1-Q3) and Marcus (P2) asks where a change is concentrated (P2-Q4). The Numbers section shows every territory's change against last week and against the baseline, and each story shows its change split by plan, specialty and channel, with small cells marked.

**Why this priority**: These numbers are what an analyst checks first, and the brief already computes most of them without showing them.

**Independent Test**: Generate the P1-Q3 and P2-Q4 briefs and read the territory table and the story splits.

**Acceptance Scenarios**:

1. **Given** any brief, **When** the Numbers section is built, **Then** it holds one row per territory with TRx this period, change against last week and change against the baseline, and withheld or projected territories are labelled as such.
2. **Given** a story, **When** its splits are shown, **Then** the plan, specialty and channel contributions add up to the territory's change, and cells below the semantic layer's floor are suppressed or marked as noise.
3. **Given** a split, **When** it is labelled, **Then** it is called a cut of the change, never a segment of prescribers.

---

### User Story 4 - Data quality in numbers (Priority: P2)

Before quoting a number, Marcus checks whether the week is complete. "What the data can't tell us" (§4) shows, for each territory in scope, rows received against rows expected, panel coverage, how late the feed was, and any restatement with its old and new values. Weeks still inside the restatement window are flagged, and a comparison that uses one says so.

**Why this priority**: The golden answers for data-quality questions quote these counts; without them the brief can only say a feed "failed".

**Independent Test**: Generate the P1-Q2 (New England incomplete feed) and P2-Q5 (restatement) briefs and read §4.

**Acceptance Scenarios**:

1. **Given** the 2026-05-04 brief, **When** §4 is built, **Then** it states New England's received and expected rows and its panel coverage.
2. **Given** a restated week, **When** it appears in a comparison, **Then** the brief states the value before and after the restatement and its reason, and does not count the week twice (B-III).
3. **Given** the latest week in the release is inside the restatement window, **When** it is compared with a mature week, **Then** the brief flags the comparison as immature.

---

### User Story 5 - Driver checks state their lag (Priority: P3)

When the brief tests promotion, access or supply as a driver, it tests the driver against TRx in the same week and one and two weeks later, and states which lag it used.

**Why this priority**: Promotion works with a delay (Week 3); a check that silently assumes no delay can rule out a real driver or credit the wrong week.

**Independent Test**: Generate the P4-Q1 brief; read the promotion check's stated lag.

**Acceptance Scenarios**:

1. **Given** a promotion check, **When** it runs, **Then** it reports the lag (0, 1 or 2 weeks) at which the driver's change lines up with the TRx change, or says none does.
2. **Given** a driver that did not change in the window or the tested lags, **When** the check runs, **Then** it is not credited (Briefing constitution, Promotion).

---

### User Story 6 - An Assumptions block (Priority: P3)

The Appendix ends with an Assumptions block in the form of the Week 6 assumption book: comparison window, baseline, lag tested, projection method, exclusions (withheld territories, suppressed cells), each with its source (default, analyst's choice, semantic layer, data). Leaders see one line under The Numbers: the period, the comparison window and whether any figure is projected.

**Why this priority**: It makes every other change in this spec visible in one place; it adds no new numbers.

**Independent Test**: Generate any brief; read the Appendix and the leadership view.

**Acceptance Scenarios**:

1. **Given** any brief, **When** the Appendix is built, **Then** the Assumptions block lists every item above with its source.
2. **Given** the leadership view, **When** it opens, **Then** it shows the one-line summary and no evidence tables (core-007).

### Edge Cases

- "Same weeks last year" is chosen and the release has no data for those weeks: the picker says so and offers the default; no brief is built on missing weeks.
- The 4 weeks before the window start before the release does: the baseline uses the weeks that exist, and the Assumptions block says how many.
- A promotion question names a territory but no week: the review covers that territory over the whole release.
- Every split cell for a story is below the floor: the story says the change cannot be split at this size.
- A follow-up (brief-006) asks to change the window: the answer offers a new brief with that window; the current brief is not rewritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The default comparison window MUST be the 4 weeks immediately before the requested window, set in the semantic layer, for every window length.
- **FR-002**: Analysts MUST be able to choose the comparison window (previous N weeks, same weeks last year, custom dates) before a brief is built; invalid choices MUST be refused with the reason. Leaders MUST NOT get the picker.
- **FR-003**: The window MUST be applied by code; no model output may set or change it.
- **FR-004**: Every brief MUST name its comparison weeks beside the first comparison and in the Assumptions block, with the source (default or analyst's choice).
- **FR-005**: A promotion question with no week MUST produce a Promotion review over the whole release (or over the named territory), not a latest-week brief.
- **FR-006**: The Promotion review MUST state whether a sustained push happened, compare each lapse and return with the other territories as an association, state why return on investment cannot be priced, and name the experiment that would settle it. It MUST NOT state a return, rank channels, or identify an individual rep.
- **FR-007**: The Numbers section MUST carry a per-territory table of TRx, change against last week and change against the baseline, with withheld and projected territories labelled.
- **FR-008**: Each story MUST show its change split by plan, specialty and channel; contributions MUST add up to the story's change; cells below the floor MUST be suppressed or marked as noise.
- **FR-009**: §4 MUST carry feed-quality figures: for every withheld cut, rows received against expected, panel coverage against the gate's floor, and feed lateness against its target; for the focus territory, its row even when it passes; for a projected or estimated week, the range of the territory's observed TRx in the comparison weeks. Restatements keep their prior and revised values and reason in §2.
- **FR-010**: [NEEDS CLARIFICATION: In this release every restatement (32 rows, one event) landed 98 days after its week, so a "latest weeks may be restated" window would cover about fourteen weeks. Options: (a) flag only weeks the gate already marks for restatement review; (b) set a restatement window in the semantic layer anyway and flag weeks inside it; (c) drop the maturity flag.] Slice A builds none of these.
- **FR-011**: Each driver check MUST test lags of 0, 1 and 2 weeks and state the lag it used, or that none lines up.
- **FR-012**: The Appendix MUST end with an Assumptions block (window, baseline, lag, projection method, exclusions, each with its source); the leadership view MUST show a one-line summary.
- **FR-013**: Every new number MUST be a claim token filled by code with an evidence item; the no-digit rule and governed terms apply.
- **FR-014**: The golden set SHOULD gain two draft cases for the picker (same weeks last year; custom window), drafted with SQL facts and labelled by Michael before they count beyond the gated code checks.

### Key Entities

- **Comparison window**: the weeks a period is compared with; has a source (default or analyst's choice) and a length.
- **Assumption**: one line of the Assumptions block; has a value and a source.
- **Promotion review**: the release-wide answer to a promotion question; holds pushes, lapses and returns, and limits.
- **Lapse**: a run of weeks in which a territory's aggregated promotion fell well below its median, with its return week.
- **Split cell**: one plan, specialty or channel's contribution to a story's change, with its size and whether it is suppressed or noisy.
- **Feed-quality row**: one territory-week's received and expected rows, coverage, lateness and restatement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every gated code check stays at 1.000 on both engines (B-VII); zero digits outside claim tokens.
- **SC-002**: 100% of briefs name their comparison window; 100% of window choices recorded in the run trace.
- **SC-003**: Golden-number recall on the 24 single-turn Briefing cases rises from 0.406 to at least 0.60 on both engines (target set before any held-out result; report-only, not gated).
- **SC-004**: Zero promotion reviews state a return on investment or rank channels; zero lines identify an individual rep.
- **SC-005**: The P3-Q5 brief states 639 as the Southeast baseline on the default window.
- **SC-006**: Every story split adds up to its change to the claim's stated precision.

## Assumptions

- Builds on brief-003 v3 (section numbers, evidence tables) and brief-006 (`split_change`, follow-ups).
- The release has no spend data and no randomized promotion; the review can only report associations (Week 5).
- The small-cell floor and the restatement window already exist in the semantic layer (B-III, B-VI); this spec reuses them.
- The golden reference answers are Michael's labels; brief-007 changes the brief, not the golden set, except the two draft cases in FR-014.
- No new persona, role or Forecast-lane change.
