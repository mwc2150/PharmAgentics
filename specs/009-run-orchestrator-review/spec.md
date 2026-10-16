# Feature Specification: Run Orchestrator and Review Flow

**Feature Branch**: `009-run-orchestrator-review`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §3, §4, §5.7, §6, §14; Evaluation Pack EV-6.2, EV-6.3, EV-8.1, EV-8.5; Personas P1, P2, P3

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One Monday run from start to finish (Priority: P1)

A Monday run takes one brand and one closed week and moves through the stages in order. Each transition is logged against the run ID. Every run ends in PUBLISHED or RUN_ERROR.

**Why this priority**: Nothing else runs without it. It owns the run states.

**Independent Test**: Run a dev week end to end. Check the state log is complete and the run ends in a terminal state.

**Acceptance Scenarios**:

1. **Given** a closed week, **When** the run starts, **Then** it moves through LOADED, VALIDATED (or a warning or failure state), ROUTINE or INVESTIGATION_REQUESTED, and on to DRAFTED, VERIFIED or VERIFICATION_FLAGGED, IN_REVIEW and PUBLISHED, with each transition logged.
2. **Given** a run with no material change, **When** it runs, **Then** it skips stage 4 and still passes the narrative, verification and two-person review.
3. **Given** a tool, data or model failure, **When** it stops the run, **Then** the state is RUN_ERROR, an alert is raised and a rerun is possible.
4. **Given** the same week and the same pinned versions, **When** the run is repeated, **Then** it reads the same snapshot.

---

### User Story 2 - Analyst review with one-click tracing (Priority: P1)

The analyst reads the verified draft with evidence one click from every number. They edit it, and every edit is captured. They see the verification flags and the data-health notes first.

**Why this priority**: The analyst reviews output instead of rebuilding it (P1-Q1, P1-Q4, P1-Q6).

**Independent Test**: Open a draft, click a number, edit a sentence. Check the span opens and the edit is stored with a failure tag.

**Acceptance Scenarios**:

1. **Given** a draft, **When** the analyst clicks a number, **Then** the tool output and span for it open.
2. **Given** an edit, **When** the analyst saves, **Then** the edit, the reviewer role, the comment and a failure tag are stored.
3. **Given** a flagged triage plan, **When** the analyst opens the run, **Then** they can approve or edit the plan before the investigation proceeds.

---

### User Story 3 - Manager sign-off before anything leaves the team (Priority: P1)

The manager signs off the analyst-approved brief before it is published. No brief leaves without both approvals. If the manager returns it, it goes back to the narrative stage with comments.

**Why this priority**: The agent proposes and people decide (constitution VIII).

**Independent Test**: Try to publish with only analyst approval. Check it is blocked. Return a brief and check it redrafts with comments.

**Acceptance Scenarios**:

1. **Given** an analyst-approved brief, **When** the manager signs off, **Then** the run becomes PUBLISHED and the approved text is frozen.
2. **Given** a brief without both approvals, **When** publish is attempted, **Then** it is blocked.
3. **Given** a returned brief, **When** the manager adds comments, **Then** the run goes to RETURNED and back to DRAFTED with the comments.

---

### User Story 4 - Feedback becomes eval data (Priority: P2)

Every edit and every runtime failure gets one failure tag. Repeated corrections become new eval cases.

**Why this priority**: The same fix must not be needed next week (P1 core need).

**Independent Test**: Make three similar edits across runs. Check the catalog shows the repeat and proposes a case.

**Acceptance Scenarios**:

1. **Given** an edit or failure, **When** it is saved, **Then** exactly one tag from the shared list is attached.
2. **Given** a repeated tag on the same pattern, **When** the catalog is read, **Then** it proposes a new eval case.

---

### User Story 5 - Limits and visible state (Priority: P2)

Every run stays within the caps for rounds, run time and brief length. Operators can see each run's state, timing, cost and failures.

**Why this priority**: Cost and time must be predictable (P1-Q6, P2-Q6).

**Independent Test**: Force a cap breach. Check the story closes as unresolved and the run still publishes after review.

**Acceptance Scenarios**:

1. **Given** a cap breach, **When** it occurs, **Then** the affected story closes as unresolved and the run continues.
2. **Given** any run, **When** its record is read, **Then** it holds timing, tokens and cost per stage.

### Edge Cases

- The week has not closed. The run refuses to start.
- A second run starts for the same week. It gets its own run ID and snapshot, and the first is untouched.
- Review is pending for days. The run stays IN_REVIEW, and the next week's run is independent.
- The manager and analyst disagree on a number. The disagreement and the evidence are on record.
- The reviewer edits a number. The tool path is the only way to change a figure, not typing a digit. [NEEDS CLARIFICATION: whether reviewers may overwrite a number by hand; proposal: no, they request a re-run of the token]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The orchestrator MUST implement the sixteen run states in Architecture §6 and log every transition with run ID and time.
- **FR-002**: Every run MUST end in PUBLISHED or RUN_ERROR.
- **FR-003**: A run with no candidates MUST skip stage 4 and still pass stages 5 to 7.
- **FR-004**: The orchestrator MUST pass only typed objects between stages (spec 005).
- **FR-005**: The orchestrator MUST pin the semantic layer, model, prompt, code and data versions in the run record.
- **FR-006**: The review flow MUST show verification flags and data-health notes before the draft.
- **FR-007**: The review flow MUST let the analyst open the evidence and span for any number.
- **FR-008**: The review flow MUST capture every edit with reviewer role, comment and one failure tag.
- **FR-009**: Publishing MUST require analyst approval and then manager sign-off. [NEEDS CLARIFICATION: whether sign-off sits with the Insights Manager or one level higher (A9)]
- **FR-010**: A returned brief MUST go back to the narrative stage with the manager's comments (proposed answer to A8).
- **FR-011**: The approved brief MUST be frozen and remain reconcilable to its pinned snapshot.
- **FR-012**: The orchestrator MUST enforce run-level limits and record cost, time and tokens per stage.
- **FR-013**: The orchestrator MUST surface RUN_ERROR through an alert and allow a rerun.
- **FR-014**: The review flow MUST provide a triage-review step, switchable between always-on (demo) and by-exception (Monday).
- **FR-015**: No reviewer or system action MAY expose the answer key.
- **FR-016**: Repeated failure tags MUST propose new eval cases.

### Key Entities

- **Run registry row**: run ID, week, state, timestamps, version pins, snapshot.
- **State transition log**: from, to, time, reason.
- **Analyst review**: run ID, reviewer role (P1 or P2), decision, edits, comments, time, failure tag.
- **Published brief**: frozen text and claims.
- **Failure catalog**: tags, counts, proposed cases.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of runs end in PUBLISHED or RUN_ERROR, with every transition logged (Architecture §14 criterion).
- **SC-002**: 100% of evidence links open the output that produced the value on the pinned snapshot (EV-6.2).
- **SC-003**: Reviewer minutes to trace a sampled claim are reported against the manual baseline (EV-6.3).
- **SC-004**: Share of claims edited or removed and reviewer minutes are reported (EV-8.1).
- **SC-005**: 100% of runs stay within round, time and length limits (EV-8.5).
- **SC-006**: Zero briefs reach PUBLISHED without both approvals.
- **SC-007**: 100% of edits and failures carry exactly one failure tag.
- **SC-008**: Per-brief run time and dollars are reported against timed gold-brief writing (EV-8.2).

## Assumptions

- The orchestrator is code and a review surface, not an agent. The only agentic loop is stage 4.
- The review surface is a simple web page. Its tooling and layout are plan matters.
- The Monday trigger is a scheduled job. A manual trigger exists for demos and evaluation.
- Only synthetic data is shown in review.
