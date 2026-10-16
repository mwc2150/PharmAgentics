# Feature Specification: Narrative and Renderer (Stage 5)

**Feature Branch**: `007-narrative-renderer`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §5.5; Evaluation Pack EV-1.1 to 1.3, EV-7.1 to 7.4, EV-8.5; Personas P1-Q6, P3-Q3, P3-Q5, P3-Q6

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A brief where code writes every number (Priority: P1)

The writer produces prose around placeholders. Code fills each placeholder from the closed evidence pack. No digit in the brief comes from the language model.

**Why this priority**: Numeric reconciliation is a hard gate (EV-1.1). Preventing errors beats catching them.

**Independent Test**: Draft a brief for a dev week. Scan the draft for digits outside claim tokens. Render and compare every number with the pinned snapshot.

**Acceptance Scenarios**:

1. **Given** a closed evidence pack, **When** the writer drafts, **Then** each figure in the prose is a claim token such as `{{c17}}`.
2. **Given** a draft, **When** the renderer fills the tokens, **Then** each value comes from an evidence item and is rounded by the stated rule.
3. **Given** a draft with a digit outside a token, **When** the checks run, **Then** the draft is rejected (spec 008).

---

### User Story 2 - The Monday format, every week (Priority: P1)

The brief follows a fixed template: a KPI table filled by code; what changed, ordered by impact; is it real; likely drivers with confidence; investigate next and who to involve; a data-health footnote; restatement disclosure; and a glossary generated from the semantic layer. Routine weeks follow the same template.

**Why this priority**: The director wants the same short format each week (P3-Q1).

**Independent Test**: Draft a routine week and an eventful week. Check both match the template and stay within the length limit.

**Acceptance Scenarios**:

1. **Given** a routine run, **When** the brief is drafted, **Then** it has the KPI table, the data-health footnote and the glossary, and says no material change was found.
2. **Given** several stories, **When** the brief is drafted, **Then** they are ordered by business impact.
3. **Given** any brief, **When** its length is counted, **Then** it is within the semantic-layer limit.

---

### User Story 3 - Plain words and honest confidence (Priority: P1)

Reader-facing text follows ASD-STE100: short sentences and one word with one meaning, paired with business framing. Causal wording appears only for High-confidence stories. Medium and Low stories use hedged wording and appear under "investigate next" when Low.

**Why this priority**: A director must repeat the explanation upward (P3-Q3). Overclaiming is the costliest error (P2-Q3).

**Independent Test**: Draft High, Medium and Low stories. Check wording per level and run the plain-language rubric.

**Acceptance Scenarios**:

1. **Given** a High story, **When** drafted, **Then** causal wording is allowed.
2. **Given** a Medium or Low story, **When** drafted, **Then** the draft uses hedged wording and no causal verb.
3. **Given** a Low story, **When** drafted, **Then** it appears under "investigate next" with the function to involve.

---

### User Story 4 - Continuity, restatements and next steps (Priority: P2)

For multi-week events, the brief says whether the change is new or continuing and whether it is improving or worsening. When a number reported last week changed, the brief says so with old and new values. Each open story names what to investigate next and which function (market access, sales, finance) to involve.

**Why this priority**: Repeated alarms erode attention; hidden restatements erode trust (P3-Q4, P3-Q5, P3-Q6).

**Independent Test**: Draft a week that continues an event from the prior week and has a restatement. Check the continuity statement and the disclosure.

**Acceptance Scenarios**:

1. **Given** a story linked to a prior-week story, **When** drafted, **Then** the brief states new or continuing and the direction of change.
2. **Given** a restated number, **When** drafted, **Then** the brief names the old and new values.
3. **Given** an open story, **When** drafted, **Then** it names a next step and a function to involve where relevant.

---

### User Story 5 - No individual identified, governed terms (Priority: P1)

No line identifies a rep. "New patients" is used only for NBRx. "Competitive intelligence" is used, never "statistical surveillance". Wording per metric follows the semantic layer.

**Why this priority**: The brief is forwarded to sales leadership. Terminology is a mentor directive.

**Independent Test**: Draft a brief on a seeded rep-vacancy case. Scan for individual references and banned terms.

**Acceptance Scenarios**:

1. **Given** a rep-vacancy case, **When** drafted, **Then** the brief mentions at most aggregated promotion activity.
2. **Given** any draft, **When** scanned, **Then** banned terms are absent.

### Edge Cases

- A failed cut: the brief leads with the unreliable cuts and states which numbers are suppressed.
- All cuts failed: the brief is a data-health notice only (A7 proposal; see spec 003).
- A run with a capped story: the story is listed as unresolved, with the evidence kept.
- Too many stories for the length limit: lower-impact stories move to "investigate next" with a count.
- A draft revision loop: one revision is allowed after a failed check (spec 008).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The writer MUST read only the closed evidence pack and the definitions of the metrics in play.
- **FR-002**: The writer MUST emit claim tokens for every figure and MUST NOT emit a digit outside a token.
- **FR-003**: The renderer MUST replace each token with the value from its evidence item, applying the stated rounding, and MUST fail on an unresolved token.
- **FR-004**: The brief MUST follow the fixed template (User Story 2) and the length limit from the semantic layer. [NEEDS CLARIFICATION: the template and length a real brand team uses (Evaluation Pack open item 4)]
- **FR-005**: Code MUST fill the KPI table and the glossary. The writer does not write them.
- **FR-006**: Stories MUST be ordered by business impact.
- **FR-007**: Routine runs, runs with warnings and runs with flagged stories MUST all use the same template.
- **FR-008**: Causal wording MUST appear only on High-confidence stories.
- **FR-009**: Reader-facing text MUST follow ASD-STE100 principles with business framing.
- **FR-010**: The brief MUST state new or continuing, and improving or worsening, for multi-week stories.
- **FR-011**: The brief MUST disclose restatements with old and new values.
- **FR-012**: Each open story MUST name a next step and a function to involve where relevant.
- **FR-013**: The brief MUST NOT identify an individual rep. "New patients" MUST be used only for NBRx.
- **FR-014**: The brief MUST carry a data-health footnote, and lead with unreliable cuts when there are any.
- **FR-015**: The draft MUST store, for each claim, the token, the claim text, the evidence IDs and the confidence (`brief_claims`).
- **FR-016**: The prompt version MUST be pinned in the run record.
- **FR-017**: The stage MUST accept analyst or manager comments on a returned brief and redraft from them.

### Key Entities

- **Draft**: prose with claim tokens.
- **Claim**: token, text, evidence IDs, confidence, status.
- **Rendered brief**: the draft with values filled in.
- **Template**: the fixed section list and length limit.
- **Glossary**: generated from the semantic layer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero digits outside claim tokens in any draft (supports EV-1.1).
- **SC-002**: 100% of rendered numbers match the pinned data after stated rounding (EV-1.1, hard gate).
- **SC-003**: 100% of seeded restatement cases are disclosed with old and new values (EV-1.2).
- **SC-004**: Non-numeric claims (direction, metric, cut, timing) are checked against the answer key and pinned data (EV-1.3; target to set).
- **SC-005**: Briefs pass format conformance (EV-7.4; target to set) and the length limit (EV-8.5).
- **SC-006**: Plain-language score on the rubric (EV-7.1; target to set).
- **SC-007**: Multi-week events carry a continuity statement (EV-7.2) and open stories carry next steps (EV-7.3).
- **SC-008**: Zero individual identifications and zero banned terms (EV-9.1, EV-9.2).
- **SC-009**: Edit burden and run-to-run stability are reported (EV-8.1, EV-8.4).

## Assumptions

- The investigation result is closed before this stage starts.
- Unreliable cuts arrive flagged. The writer does not decide reliability.
- The template starts from the Architecture §5.5 sections. A real brand team's format replaces it if the mentor provides one.
- ASD-STE100 is a style target. The rubric scores it by human reviewers.
