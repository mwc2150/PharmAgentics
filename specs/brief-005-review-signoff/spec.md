# Feature Specification: Review, Sign-off and Feedback (Stage 7)

**Spec ID**: `brief-005-review-signoff` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-23 (split from `009-run-orchestrator-review`, 2026-10-16)
**Status**: Draft v1. Not started.
**Replaces**: the review half of `009-run-orchestrator-review`. The orchestrator half is `core-005-run-orchestrator`.
**Input**: System Architecture §3.7, §4 (stage 7, Briefing); Briefing Architecture §5.7, §6, decision 11; Evaluation Pack EV-6.2, EV-6.3, EV-8.1, EV-8.2; Personas P1, P2, P3, P4; User stories P1-Q1, P1-Q4, P1-Q6, P2-Q1, P2-Q5, P2-Q6

## Context

Two people approve every brief, and every correction becomes data (Briefing §5.7). P1 reviews and edits; P2 signs off; only then can P3 and P4 read it. The agent proposes; people decide (shared Principle II).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - P1 reviews with one-click tracing (Priority: P1)

P1 opens the verified draft. Verification flags and data-health notes come first. Every number opens its tool record and span in one click. P1 edits wording, and every edit is captured with one failure tag.

**Why this priority**: P1 reviews output instead of rebuilding it (P1-Q1, P1-Q4, P1-Q6).

**Independent Test**: Open the 2026-07-06 draft, click two numbers, edit a sentence.

**Acceptance Scenarios**:

1. **Given** the 2026-07-06 draft, **When** P1 opens it, **Then** the data-health section shows Great Lakes withheld first; P1 opens two claim links at random, confirms the withheld cut, and asks P2 to request a clean reload. No table is rebuilt. (User story P1-Q1.)
2. **Given** any number, **When** P1 clicks it, **Then** the tool record (tool, parameters, snapshot) and span open, and reviewer minutes to trace are logged. (User story P1-Q4; EV-6.3.)
3. **Given** an edit, **When** P1 saves, **Then** the edit, reviewer role, comment and one failure tag are stored. (User story P1-Q6.)
4. **Given** a flagged triage plan (TRIAGE_REVIEW), **When** P1 opens the run, **Then** P1 can approve or edit the plan before investigation continues.

---

### User Story 2 - P2 signs off before anything leaves the team (Priority: P1)

P2 signs off the P1-approved brief. No brief is published without both approvals. If P2 returns it, it goes back to stage 5 with comments.

**Why this priority**: The agent proposes and people decide.

**Independent Test**: Try to publish with only P1 approval; return a brief.

**Acceptance Scenarios**:

1. **Given** a P1-approved brief, **When** P2 signs off, **Then** the run is PUBLISHED and the approved text, claims and snapshot ID are frozen.
2. **Given** a brief without both approvals, **When** publish is attempted, **Then** it is blocked.
3. **Given** a returned brief, **When** P2 adds comments, **Then** the run goes RETURNED, then DRAFTED with the comments (proposed answer to A8).
4. **Given** a data-artifact story (2026-04-06), **When** P2 reviews, **Then** P2 can approve the artifact label and record a request to the data vendor. (User story P2-Q1.)

---

### User Story 3 - Answer a challenge against the numbers as they stood (Priority: P1)

Months later, someone challenges a published number. P2 opens the frozen brief; each link opens the value on the snapshot pinned at sign-off, with any later restatement shown beside it.

**Why this priority**: Defending a number must not mean rebuilding the analyst's work (P2-Q5).

**Independent Test**: Open the April 2026 brief after 2026-07-13.

**Acceptance Scenarios**:

1. **Given** the brief signed off in April with Mid-Atlantic BXA TRx 692 for 2026-04-06, **When** it is challenged after 2026-07-13, **Then** the link opens 692 on the pinned snapshot and shows the restatement record (742, 2026-07-13, late claims adjustment) beside it. It never presents 742 as the April figure. (User story P2-Q5.)

---

### User Story 4 - Readers see only the published brief (Priority: P2)

P3 and P4 read the published brief with clickable evidence. They never see drafts, flags in progress or the agent.

**Why this priority**: P3 and P4 act on signed-off output only (Personas).

**Independent Test**: Log in as a reader before and after sign-off.

**Acceptance Scenarios**:

1. **Given** a run not yet PUBLISHED, **When** a reader opens it, **Then** nothing is shown.
2. **Given** a published brief, **When** a reader clicks a number, **Then** its evidence opens read-only.

---

### User Story 5 - Feedback becomes eval data (Priority: P2)

Every edit and runtime failure gets one failure tag. A fix repeated in two weeks proposes a new eval case.

**Why this priority**: The same fix must not be needed next week (P1 core need).

**Independent Test**: Make the same edit in two weekly runs.

**Acceptance Scenarios**:

1. **Given** an edit or failure, **When** it is saved, **Then** exactly one tag from the Briefing list is attached.
2. **Given** the same tag on the same pattern in two weeks, **When** the catalog is read, **Then** it proposes a new eval case to core-006. (User story P1-Q6.)

### Edge Cases

- Review is pending for days: the run stays IN_REVIEW; next week's run is independent.
- P1 and P2 disagree on a number: the disagreement and the evidence are on record.
- A reviewer wants to change a figure: the tool path is the only way. [NEEDS CLARIFICATION: whether reviewers may overwrite a number by hand; proposal: no, they request a re-run of the token]
- The reviewer is not P2 but someone more senior: see FR-005.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The review surface MUST show verification flags and data-health notes before the draft.
- **FR-002**: Every number MUST open its tool record and span in one click, on the pinned snapshot; reviewer minutes to trace MUST be logged.
- **FR-003**: The review surface MUST capture every edit as an `analyst_review` row with reviewer role, before and after, comment, one failure tag and minutes.
- **FR-004**: The review surface MUST provide the TRIAGE_REVIEW step, switchable between always-on (demo) and by-exception (Monday).
- **FR-005**: Publishing MUST require P1 approval and then sign-off. [NEEDS CLARIFICATION: whether sign-off sits with P2 or one level higher (Briefing A9)]
- **FR-006**: A returned brief MUST go to RETURNED, then DRAFTED with the comments (A8 proposal).
- **FR-007**: On sign-off, the brief text, claims and snapshot ID MUST be frozen. Later changes create a new run.
- **FR-008**: A frozen brief's links MUST open values on its pinned snapshot and show later restatements beside them.
- **FR-009**: Readers (P3, P4) MUST see only PUBLISHED briefs, read-only, with clickable evidence.
- **FR-010**: Repeated failure tags on the same pattern in two weeks MUST propose a new eval case.
- **FR-011**: No reviewer or reader action MAY expose the answer key or the ground-truth store.
- **FR-012**: No line shown to any reader MAY identify an individual rep (enforced upstream; the surface shows nothing below the floor).

### Key Entities

`analyst_review` (core-004), published brief (frozen text, claims, snapshot ID), failure catalog entry, reader view.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of links open the output that produced the value on the pinned snapshot (EV-6.2).
- **SC-002**: Reviewer minutes to trace a sampled claim are reported against the manual baseline (EV-6.3).
- **SC-003**: Share of claims edited or removed and reviewer minutes are reported (EV-8.1).
- **SC-004**: Zero briefs reach PUBLISHED without both approvals.
- **SC-005**: 100% of edits and failures carry exactly one failure tag.
- **SC-006**: A challenge to the April 2026 brief resolves to 692 with the restatement beside it.

## Assumptions

- The review surface is a small web app; its tooling is a plan matter (Streamlit).
- Only synthetic data is shown.
- Reviewer accounts are local roles for the demo; no real identity system.
