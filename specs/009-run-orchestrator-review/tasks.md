# Tasks: Run Orchestrator and Review Flow

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/orchestrator/`, `src/pharmagentics/review/`, matching test folders
- [ ] T002 [P] Encode the 16 states and allowed transitions (`states.py`)
- [ ] T003 [P] Run registry and transition log (`registry.py`)

## Phase 2: Foundational

- [ ] T004 Stage driver with typed-handoff validation (`run.py`) (FR-004)
- [ ] T005 Run-level limits and defined exit (FR-012)
- [ ] T006 RUN_ERROR handling and alert (`alerts.py`) (FR-013)

## Phase 3: User Story 1 - One Monday run (P1) MVP

- [ ] T007 [P] [US1] Property test: every path through the graph ends in PUBLISHED or RUN_ERROR (SC-001)
- [ ] T008 [P] [US1] Test: routine run skips stage 4 and still reviews (FR-003)
- [ ] T009 [US1] End-to-end run on a dev week with stubs for stages 4 to 6 (milestone: end-to-end run, stubs OK)
- [ ] T010 [US1] Test: rerun on the same week reads the same snapshot
- [ ] T011 [US1] Monday and manual triggers (`schedule.py`)

## Phase 4: User Story 2 - Analyst review (P1)

- [ ] T012 [US2] Review app: flags and data-health first, then the draft (`app.py`) (FR-006)
- [ ] T013 [US2] Trace links from number to evidence to span (`trace_links.py`) (FR-007)
- [ ] T014 [US2] Edit capture with reviewer role, comment and one failure tag (`edits.py`)
- [ ] T015 [US2] Triage-review step; demo-on and Monday-by-exception switch (FR-014)
- [ ] T016 [P] [US2] Test: every evidence link opens the right output on the pinned snapshot (SC-002)

## Phase 5: User Story 3 - Sign-off (P1)

- [ ] T017 [US3] Two-gate approval and freeze (`signoff.py`) (FR-009, FR-011)
- [ ] T018 [P] [US3] Test: publish blocked without both approvals (SC-006)
- [ ] T019 [US3] Return path: RETURNED to DRAFTED with comments (FR-010)
- [ ] T020 [US3] Resolve the sign-off level (A9) and the number-edit rule; update this spec

## Phase 6: User Story 4 - Feedback to eval data (P2)

- [ ] T021 [US4] Failure catalog and repeated-tag case proposals (`catalog.py`) (FR-016)
- [ ] T022 [P] [US4] Test: every edit and failure has exactly one tag (SC-007)

## Phase 7: User Story 5 - Limits and visibility (P2)

- [ ] T023 [US5] Per-stage time, tokens and cost in the run record (SC-008)
- [ ] T024 [P] [US5] Test: forced cap breach closes the story and the run still publishes after review (SC-005)

## Phase 8: Polish

- [ ] T025 Replace stubs with real stages as 003 to 008 land; rerun T009
- [ ] T026 [P] Quickstart: run a dev week and walk through review

## Dependencies

Needs 002 (versions, caps), 003 (state inputs), 005 (contracts). Real stages arrive from 004, 006, 007, 008. 010 scores the runs.

## White-box tests owed

State-graph test (T007), handoff schema checks (T004), transition logging, alerts.
