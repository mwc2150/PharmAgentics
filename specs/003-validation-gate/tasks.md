# Tasks: Load, Pin and Validation Gate

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/validation/` and `tests/unit/validation/`
- [ ] T002 [P] Define `HealthReport`, `CutResult`, `RestatementRecord`, `RunRegistryRow` models
- [ ] T003 [P] Build seeded-artifact fixtures from spec 001 (one per artifact type, plus a clean week)

## Phase 2: Foundational

- [ ] T004 Snapshot store: write-once, content hash, ID (`snapshot.py`)
- [ ] T005 Loader for the latest closed week plus history window (`loader.py`)
- [ ] T006 Data view that applies suppression and qualification flags (`view.py`)

## Phase 3: User Story 1 - Pin one data version (P1) MVP

**Independent Test**: A later restated pull does not change an earlier run's snapshot.

- [ ] T007 [P] [US1] Test: snapshots are immutable; second pull gets a new ID (SC-006)
- [ ] T008 [P] [US1] Test: run record holds all version pins (FR-001)
- [ ] T009 [US1] Implement run registry write for LOADED
- [ ] T010 [US1] Test: moving the window forward flags restated weeks and never overwrites (FR-003)

## Phase 4: User Story 2 - Catch artifacts (P1)

**Independent Test**: Each seeded artifact type is flagged in the right cut.

- [ ] T011 [P] [US2] Check: schema and types (`checks/schema.py`)
- [ ] T012 [P] [US2] Check: missing sources (`checks/missing.py`)
- [ ] T013 [P] [US2] Check: row count against trailing average (`checks/rowcount.py`)
- [ ] T014 [P] [US2] Check: duplicate keys, including conflicting values (`checks/duplicates.py`)
- [ ] T015 [P] [US2] Check: panel coverage (`checks/coverage.py`)
- [ ] T016 [P] [US2] Check: freshness and lag (`checks/freshness.py`)
- [ ] T017 [US2] Health report with per-cut, per-check evidence and the threshold behind each result (FR-005, FR-009)
- [ ] T018 [US2] Test: catch rate ≥ 90% on dev seeds (SC-001); zero false flags on clean weeks (SC-005)

## Phase 5: User Story 3 - Suppress or qualify (P1)

- [ ] T019 [US3] Test: failed cut is suppressed or qualified in the view; none unqualified (SC-002)
- [ ] T020 [US3] All-cuts-fail path returns `VALIDATION_FAILED` (FR-012); confirm A7 with the team

## Phase 6: User Story 4 - Restatement disclosure (P2)

- [ ] T021 [US4] Check: restatement diff against previous snapshot (`checks/restatement.py`)
- [ ] T022 [US4] Test: every seeded restatement lists old and new values (SC-004); in-window flagged 100% (SC-003)
- [ ] T023 [US4] Decide handling of restatements older than the window; update this spec

## Phase 7: Polish

- [ ] T024 [P] Test on a 10x world (FR-011)
- [ ] T025 [P] Quickstart: validate a dev week and read the report

## Dependencies

Needs 002 (thresholds, window) and 001 fixtures. 004 and 009 consume the report and view.

## White-box tests owed (Architecture §12)

Catches each seeded artifact type on dev seeds (T018). Unit tests for each check (T011 to T016).
