# Feature Specification: Narrative and Renderer (Stage 5)

**Spec ID**: `brief-003-narrative-renderer` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `007-narrative-renderer` (Oct 16)
**Input**: System Architecture §4 (stage 5, Briefing); Briefing Architecture §5.5, decision 6, decision 20; Evaluation Pack EV-1.1 to EV-1.3, EV-7.1 to EV-7.5, EV-8.5; Personas P1, P3, P4; User stories P1-Q1, P1-Q2, P1-Q3, P1-Q6, P3-Q2, P3-Q3, P3-Q4, P3-Q5, P3-Q6, P4-Q2, P4-Q3, P4-Q6

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A brief where code writes every number (Priority: P1)

The writer produces prose around claim tokens. Code fills each token from the closed evidence pack. No digit in the brief comes from the language model.

**Why this priority**: Numeric reconciliation is a hard gate (EV-1.1). Preventing errors beats catching them (Briefing decision 6).

**Independent Test**: Draft the 2026-08-24 brief. Scan for digits outside tokens. Render and compare every number with the pinned snapshot.

**Acceptance Scenarios**:

1. **Given** a closed evidence pack, **When** the writer drafts, **Then** each figure in the prose is a claim token such as `{{c17}}`.
2. **Given** a draft, **When** the renderer fills the tokens, **Then** each value comes from a tool record and is rounded by the metric's rule.
3. **Given** a draft with a digit outside a token, **When** checks run, **Then** the draft is rejected (brief-004).

---

### User Story 2 - The Monday format, every week (Priority: P1)

The brief follows one template: data health first when any cut is unreliable; a KPI table filled by code; what changed, ordered by impact; is it real; likely drivers with confidence; promotion context for stories where promotion was tested; investigate next and who to involve; restatement disclosure; data-health footnote; glossary from the semantic layer. Routine weeks use the same template.

**Why this priority**: The director wants the same short format each week (P3-Q1); P1 wants the team's Monday format (P1-Q6).

**Independent Test**: Draft a routine week (2025-04-21), a week with a withheld cut (2026-05-04) and an eventful week (2026-08-24).

**Acceptance Scenarios**:

1. **Given** the routine week 2025-04-21, **When** the brief is drafted, **Then** it holds the KPI table, at most one line saying territory swings stayed in their normal range, the footnote and the glossary, and no story. It never says "Pacific surged 25%". (User story P1-Q3.)
2. **Given** week 2026-05-04, **When** the brief is drafted, **Then** the data-health section leads, names New England as not reportable with its three reasons, and national figures say "7 of 8 territories". It never says "New England BXA fell 34%". (User story P1-Q2.)
3. **Given** week 2026-08-24, **When** the brief is drafted, **Then** it carries a Southeast story and a continuing Metacora line, and nothing about a national "collapse". (User story P1-Q6.)
4. **Given** any brief, **When** its length is counted, **Then** it is within the semantic-layer limit.

---

### User Story 3 - Plain words and honest confidence (Priority: P1)

Reader-facing text follows ASD-STE100: short sentences, one idea and one number per sentence, one word with one meaning, with business framing. Method terms stay in the evidence, not the prose. Causal wording appears only for High stories; promotion findings are always worded as associations.

**Why this priority**: The director must repeat the explanation upward (P3-Q3). Overclaiming is the costliest error (P2-Q3).

**Independent Test**: Draft the Pacific supply story and a Medium promotion story. Run the plain-language rubric.

**Acceptance Scenarios**:

1. **Given** the Pacific supply story (June 2026), **When** drafted, **Then** it reads like: "For five weeks in June, Pacific pharmacies could fill only about 7 in 10 BXA orders. Pacific BXA prescriptions fell 34% while other territories fell 1%. Supply returned to normal on July 6, and prescriptions recovered." It calls it a supply problem, not a demand problem. (User story P3-Q3.)
2. **Given** any reader-facing sentence, **When** scanned, **Then** it holds no reader-jargon term ("difference-in-differences", "fill-rate elasticity").
3. **Given** a Medium or Low story, **When** drafted, **Then** it uses hedged wording and no causal verb; a Low story appears under "investigate next" with the function to involve.
4. **Given** a supported promotion finding, **When** drafted, **Then** it is worded as an association, names the method and the comparison, and never states a promotion-caused lift. (User story P4-Q1.)

---

### User Story 4 - Continuity, restatements, coverage and next steps (Priority: P2)

For multi-week events, the brief says new or continuing and improving, worsening or flat. When a number reported earlier changed, it states old value, new value and reason. National figures built on fewer territories say so. Each open story names what to investigate next and which function to involve.

**Why this priority**: Repeated alarms erode attention; hidden restatements erode trust (P3-Q4, P3-Q5, P3-Q6).

**Independent Test**: Draft the 2026-09-28 brief (Metacora continuing) and the 2026-07-13 brief (restatement).

**Acceptance Scenarios**:

1. **Given** week 2026-09-28, **When** drafted, **Then** the Metacora story is marked continuing, in its 31st week, worse than at launch and flat for the last 8 weeks, with BXA 32.1% and Metacora 15.2% that week. It never says "New: competitor gaining share". (User story P3-Q4.)
2. **Given** the 2026-07-13 brief, **When** drafted, **Then** it says Mid-Atlantic BXA TRx for 2026-04-06 was restated from 692 to 742 on 2026-07-13 for a late claims adjustment, and every national figure built on 7 territories says so. (User story P3-Q6.)
3. **Given** the Southeast coverage gap (August 2026), **When** next steps are drafted, **Then** they say to involve sales leadership on Southeast coverage, at territory level, and say rep and digital effects cannot be separated. (User stories P3-Q5, P4-Q6.)
4. **Given** the December 2025 holiday weeks, **When** drafted, **Then** the brief labels the drop a calendar effect, cites last year's same weeks, opens no story, and says a rebound is expected. (User story P3-Q2.)

---

### User Story 5 - Promotion context next to performance (Priority: P2)

For each story where promotion was tested, the brief shows promotion activity (aggregated calls, impressions) for the same cut and weeks next to TRx, splits by channel and specialty with small cells flagged, and states what the data cannot show yet.

**Why this priority**: P4 needs activity beside results, and an honest statement of what is missing (P4-Q2, P4-Q3; EV-7.5).

**Independent Test**: Draft the Southeast story.

**Acceptance Scenarios**:

1. **Given** the Southeast story, **When** drafted, **Then** it shows calls and impressions beside TRx for 2026-08-03 to 2026-08-31 (impressions about 870 against a median of about 1,774) and says reach by target segment cannot be shown yet. It never says "the campaign reached its target HCPs". (User story P4-Q3.)
2. **Given** a channel split with cash cells of 36 to 49 TRx a week, **When** drafted, **Then** those cells are marked noisy and no claim generalizes from them. (User story P4-Q2.)

---

### User Story 6 - No individual identified, governed terms (Priority: P1)

No line identifies a rep. "New patients" is used only for NBRx. "Competitive intelligence" is used; "surveillance" never is.

**Why this priority**: The brief is forwarded to sales leadership and marketing. Terminology is a mentor directive.

**Independent Test**: Draft the Southeast brief and scan.

**Acceptance Scenarios**:

1. **Given** a rep-vacancy case, **When** drafted, **Then** the brief mentions only territory-level aggregated activity.
2. **Given** any draft, **When** scanned, **Then** banned terms are absent.

### Edge Cases

- All cuts failed: the brief is a data-health notice only (A7 proposal).
- A capped story: listed as unresolved, with its evidence kept.
- Too many stories for the length limit: lower-impact stories move to "investigate next" with a count.
- A revision after a failed check: one revision only (brief-004).
- A story's promotion was not tested (no activity data for the cut): the promotion context section says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The writer MUST read only the closed evidence pack, the continuity object and the definitions of the metrics in play.
- **FR-002**: The writer MUST emit claim tokens for every figure and MUST NOT emit a digit outside a token.
- **FR-003**: The renderer MUST replace each token with its tool record's value using the metric's rounding rule, and MUST fail on an unresolved token.
- **FR-004**: The brief MUST follow the fixed template in User Story 2 and the semantic-layer length limit. [NEEDS CLARIFICATION: the template and length a real brand team uses (Evaluation Pack open item 4)]
- **FR-005**: Code MUST fill the KPI table, the data-health section, the coverage labels, the restatement disclosure, the promotion context table and the glossary. The writer does not write them.
- **FR-006**: Stories MUST be ordered by business impact.
- **FR-007**: Routine, warning, failed-validation and eventful runs MUST all use the same template.
- **FR-008**: Causal wording MUST appear only on High stories. Promotion findings MUST use association wording at every level.
- **FR-009**: Reader-facing text MUST follow ASD-STE100 with business framing, and MUST contain no reader-jargon term from the semantic layer.
- **FR-010**: The brief MUST state new or continuing, weeks running, and improving, worsening or flat for multi-week stories.
- **FR-011**: The brief MUST disclose every restatement since the previous brief with old value, new value, date and reason.
- **FR-012**: Every national or regional figure built on fewer than all territories MUST carry its coverage label.
- **FR-013**: Each open story MUST name a next step and a function from the semantic-layer list.
- **FR-014**: For each story where promotion was tested, the brief MUST show promotion activity for the same cut and weeks beside performance, and MUST state what the data cannot show yet. [NEEDS CLARIFICATION: whether reach, channel spend and consumer campaign data enter v1 (Briefing A16, Evaluation Pack open item 19)]
- **FR-015**: Splits below the small-cell floor MUST be marked noisy, and no sentence MAY generalize from them.
- **FR-016**: The brief MUST NOT identify an individual rep. "New patients" MUST be used only for NBRx.
- **FR-017**: The draft MUST store each claim as a `brief_claim` (core-004) with token, text, evidence IDs, metric, rounding, confidence and section.
- **FR-018**: The prompt version MUST be pinned in the run record.
- **FR-019**: The stage MUST accept verifier flags or reviewer comments and redraft only the flagged sections.

### Key Entities

Draft, `brief_claim`, rendered brief, template, glossary, continuity object, promotion context table.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero digits outside claim tokens in any draft (supports EV-1.1).
- **SC-002**: 100% of rendered numbers match the pinned snapshot after stated rounding (EV-1.1, hard gate).
- **SC-003**: 100% of seeded restatement cases are disclosed with old and new values (EV-1.2); the 2026-07-13 brief discloses 692 → 742.
- **SC-004**: Non-numeric claims are checked against the answer key and pinned data (EV-1.3; target to set).
- **SC-005**: Briefs pass format conformance (EV-7.4) and the length limit (EV-8.5).
- **SC-006**: Plain-language score on the rubric (EV-7.1; target to set).
- **SC-007**: Multi-week events carry continuity (EV-7.2); open stories carry next steps (EV-7.3).
- **SC-008**: Every promotion-tested story carries the promotion context table and its limits statement (EV-7.5).
- **SC-009**: Zero individual identifications and zero banned or jargon terms in reader text (EV-9.1, EV-9.2).
- **SC-010**: Every "must not say" phrase in the Briefing user stories is absent from the matching dev brief.

## Assumptions

- The investigation result is closed before this stage starts.
- Unreliable cuts arrive flagged; the writer does not judge reliability.
- The template starts from Briefing Architecture §5.5 and is replaced if the mentor provides a real one.
- ASD-STE100 is a style target scored by human reviewers.
- The language model is Gemini (external); prompts carry only synthetic values and metric definitions (S14).
