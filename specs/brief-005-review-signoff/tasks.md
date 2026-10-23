# Tasks: Review, Sign-off and Feedback

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/review/` and test folders
- [ ] T002 [P] Local roles (`roles.py`); `published_brief` model

## Phase 2: Foundational

- [ ] T003 Gate rules and freeze (`signoff.py`) (FR-005 to FR-007)
- [ ] T004 Trace links, including restatement beside frozen values (`trace_links.py`) (FR-002, FR-008)

## Phase 3: User Story 1 - P1 review (P1) MVP

- [ ] T005 [US1] App: flags and data health first, then the draft (`app.py`) (FR-001)
- [ ] T006 [US1] Edit capture with tag and minutes (`edits.py`) (FR-003)
- [ ] T007 [US1] TRIAGE_REVIEW step with demo and Monday modes (`triage.py`) (FR-004)
- [ ] T008 [P] [US1] Test: 2026-07-06 draft shows Great Lakes withheld first; two links open (P1-Q1, SC-001)
- [ ] T009 [P] [US1] Test: trace minutes logged (SC-002)

## Phase 4: User Story 2 - Sign-off (P1)

- [ ] T010 [P] [US2] Test: publish blocked without both approvals (SC-004)
- [ ] T011 [US2] Return path: RETURNED → DRAFTED with comments (FR-006)
- [ ] T012 [US2] Resolve A9 and the number-edit rule; update this spec

## Phase 5: User Story 3 - Challenge (P1)

- [ ] T013 [P] [US3] Test: the April 2026 brief resolves to 692 with the 742 restatement beside it (P2-Q5, SC-006)

## Phase 6: User Story 4 - Readers (P2)

- [ ] T014 [US4] Reader view; nothing before PUBLISHED (FR-009)

## Phase 7: User Story 5 - Feedback (P2)

- [ ] T015 [US5] Repeated-tag proposals to core-006 (`catalog.py`) (FR-010)
- [ ] T016 [P] [US5] Test: every edit and failure has exactly one tag (SC-005)

## Phase 8: Polish

- [ ] T017 [P] `quickstart.md`: review and sign off a dev week

## Dependencies

Needs brief-004 output, core-004 models, core-005 events and states, core-006 tracing. EV-6.3 and EV-8.1 are scored in core-006 from this spec's logs.
