# Tasks: Run Orchestrator

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/orchestrator/` and test folders
- [ ] T002 [P] `LaneGraph` model and validation (`graph.py`) (FR-002)
- [ ] T003 [P] Registry and transition log (`registry.py`) (FR-001)

## Phase 2: Foundational

- [ ] T004 Driver with typed-handoff validation and RUN_ERROR handling (`run.py`) (FR-007)
- [ ] T005 Run-level caps and per-stage meter (`meter.py`) (FR-008)
- [ ] T006 Alerts (`alerts.py`) (FR-009)

## Phase 3: User Story 1 - One Briefing run (P1) MVP

- [ ] T007 [US1] Briefing graph and stage stubs (`lanes/briefing.py`) (FR-003, FR-005)
- [ ] T008 [P] [US1] Property test: every path ends in PUBLISHED or RUN_ERROR (SC-001)
- [ ] T009 [P] [US1] Test: week 2025-04-21 goes ROUTINE, skips stage 4, still reviews (FR-004)
- [ ] T010 [US1] End-to-end dev-week run with stubs for stages 4 to 6 (milestone: end-to-end, stubs OK)
- [ ] T011 [US1] Test: rerun on the same pins reads the same snapshot
- [ ] T012 [US1] Monday, manual and replay triggers with as-of (`triggers.py`) (FR-010)

## Phase 4: User Story 2 - Independent lanes (P1)

- [ ] T013 [US2] Lane registration API; doc for the Forecast team (FR-006)
- [ ] T014 [P] [US2] Test: concurrent Briefing and Forecast-stub runs share only the registry (SC-004)
- [ ] T015 [US2] With Alvin and Sienna: register the Forecast graph; re-run of the 2026-08-24 request is identical (SC-005)
- [ ] T016 Raise S1 and S2 with the team and Dr. Admasu; record the outcome in the System Architecture decision log

## Phase 5: User Story 3 - Limits and visibility (P2)

- [ ] T017 [P] [US3] Test: a forced story cap closes the story and the run continues (EV-5.4, EV-8.5)
- [ ] T018 [P] [US3] Test: a wall-clock breach ends in RUN_ERROR with reason
- [ ] T019 [US3] Per-stage time, tokens and cost in the registry row (SC-003)

## Phase 6: Polish

- [ ] T020 Replace stubs as core-003, brief-001 to brief-005 land; rerun T010
- [ ] T021 [P] `quickstart.md`: run a dev week from the CLI

## Dependencies

Needs core-002 (caps), core-003 (pins, states), core-004 (contracts). Real stages arrive from brief-001 to brief-005. core-006 drives replays.
