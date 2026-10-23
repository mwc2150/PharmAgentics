# Tasks: Load, Pin and Validation Gate

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: v0 gate built (PR #1). Everything else not started.

## Phase 1: Built (PR #1)

- [x] T001 v0 gate views: `v_rx_expected_keys`, `v_rx_missing_keys`, `v_rx_duplicate_keys`, `v_feed_health`, `v_reportable_rx`, `v_weekly_rx_kpis` (FR-004, FR-006)
- [x] T002 Tests: the three `day1-v1` artifacts are flagged; wholly missing cuts are not read as zero; metadata faults fail closed

## Phase 2: Setup

- [ ] T003 Create `src/pharmagentics/validation/` and test folders
- [ ] T004 [P] Models: `HealthReport`, `CutResult`, `RestatementRecord`, `ForecastFitness`, `RunRegistryRow` (shared with core-004, core-005)
- [ ] T005 [P] Fixtures: the three `day1-v1` artifact weeks, a clean week, and dev-world artifacts from core-001

## Phase 3: User Story 1 - Pin one data version (P1) MVP

- [ ] T006 [US1] Run registry row with every pin, including Forecast issue week and horizon (`pin.py`) (FR-001)
- [ ] T007 [US1] `sql/002_snapshot_views.sql`: as-of views over `rx_weekly`, `restatement_log`, `feed_metadata` (FR-003)
- [ ] T008 [P] [US1] Test: as of 2026-04-13T12:00Z, Mid-Atlantic BXA TRx for 2026-04-06 is 692; as of the latest load it is 742 (user story P2-Q5)
- [ ] T008a [P] [US1] Test: as of 2026-05-11T12:00Z, New England 2026-05-04 is not yet delivered (it loaded 2026-05-14)
- [ ] T009 [P] [US1] Test: same snapshot ID reads identical numbers; a later run does not change an earlier one (SC-005)
- [ ] T010 [P] [US1] Test: a Forecast request for 2026-08-24 pins issue week 2026-07-27, horizon 4; re-run is identical (user story CA-Q6)

## Phase 4: User Story 2 - Catch artifacts (P1)

- [ ] T011 [US2] Render v0 thresholds from core-002 (depends on core-002 T013)
- [ ] T012 [US2] `gate.py` and `report.py`: reasons, evidence and thresholds per cut (FR-005)
- [ ] T013 [P] [US2] Test: Great Lakes 2026-07-06 evidence shows 143 vs 128 rows, 15 duplicate keys, raw 670 vs deduplicated 624 (P1-Q1)
- [ ] T014 [P] [US2] Test: New England 2026-05-04 reasons and evidence: 84 of 128, coverage 0.656, lag 10.29 vs 7 (P1-Q2)
- [ ] T015 [P] [US2] Test: catch rate ≥ 90% on dev worlds; no false flags on clean weeks (SC-002)

## Phase 5: User Story 3 - Withhold or qualify (P1)

- [ ] T016 [US3] Coverage of totals and like-for-like territory sets (`coverage.py`) (FR-008)
- [ ] T017 [P] [US3] Test: 2026-07-06 national BXA TRx 3,665 labeled "7 of 8 territories" (P1-Q1)
- [ ] T018 [P] [US3] Test: 2026-03-30 vs 2026-04-06 like-for-like set is 7 territories; 4,005 → 3,860 (P2-Q1)
- [ ] T019 [US3] All-cuts-fail path returns `VALIDATION_FAILED`; confirm A7 (FR-012)

## Phase 6: User Story 4 - Restatement disclosure (P2)

- [ ] T020 [US4] Restatement records since the previous run of the lane (FR-009)
- [ ] T021 [P] [US4] Test: the run for 2026-07-13 lists 692 → 742, revised 2026-07-13, reason `SYNTHETIC_LATE_CLAIMS_ADJUSTMENT` (P3-Q6)
- [ ] T022 [US4] Decide the window and out-of-window rule (S4) with Meghna; update core-002 and this spec

## Phase 7: User Story 5 - Forecast fitness (P1)

- [ ] T023 [US5] `forecast.py`: provisional, restated, version match (FR-010)
- [ ] T024 [P] [US5] Test: New England 2026-05-04 provisional; Mid-Atlantic 2026-04-06 restated despite `actual_is_provisional = 0` (CA-Q1)
- [ ] T025 [US5] Review with Alvin and Sienna against FE-01 to FE-03 and TC-06, TC-12

## Phase 8: Polish

- [ ] T026 [P] Test on a 10× world (FR-011)
- [ ] T027 [P] `quickstart.md`: validate a week as of a date and read the report

## Dependencies

Needs core-002 (thresholds, window). core-005 consumes states; brief-001 and the Forecast variance screen consume the governed view and report.
