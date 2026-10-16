# Tasks: Data Generator and Injection Library

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.
**Format**: `[ID] [P?] [Story] Description`. `[P]` means it can run in parallel.

## Phase 1: Setup

- [ ] T001 Create package skeleton `src/pharmagentics/generator/` and `tests/unit/generator/`
- [ ] T002 [P] Define world settings model and validation in `src/pharmagentics/generator/settings.py` (FR-002)
- [ ] T003 [P] Define answer-key schema (FR-009) in `src/pharmagentics/generator/answer_key.py`

## Phase 2: Foundational

- [ ] T004 Port Day 1 v0 baselines (trend, seasonality, holidays) into `world.py` with settings-driven sizes
- [ ] T005 Port Rx sampling into `sampling.py`; assert metric invariants (FR-004)
- [ ] T006 Build the per-purpose seeded random stream helper

## Phase 3: User Story 1 - Rebuild the world from a seed (P1) MVP

**Independent Test**: Two runs, same seed, identical bytes; 10x size passes schema checks.

- [ ] T007 [P] [US1] Test: identical output for identical seed and settings (SC-001) in `tests/unit/generator/test_determinism.py`
- [ ] T008 [P] [US1] Test: schema of every table matches the data dictionary in `tests/unit/generator/test_schema.py`
- [ ] T009 [P] [US1] Test: invariants (NBRx ≤ NRx ≤ TRx, non-negative, shares sum to one)
- [ ] T010 [US1] Build all 14 tables and the validation report (FR-003, FR-004)
- [ ] T011 [US1] Test: 10x territories builds with no schema change (SC-005)
- [ ] T012 [US1] Reproduce the Day 1 release from seed 7 and diff against the shipped files; document differences

## Phase 4: User Story 2 - Inject labeled events and artifacts (P1)

**Independent Test**: One access restriction moves its cut by the logged magnitude and writes one record.

- [ ] T013 [P] [US2] Event registry with type, ranges and affected cut in `events/registry.py`
- [ ] T014 [P] [US2] Business events: access restriction, competitor launch, inventory, promotion, rep vacancy, 30-to-90-day conversion, competitive pressure (FR-005)
- [ ] T015 [P] [US2] Artifacts: restatement, coverage drop, duplicate load, missing week, late week (FR-006)
- [ ] T016 [US2] Calendar effects, null weeks, multi-week decay, compound weeks, stress cases (FR-007)
- [ ] T017 [US2] Write the answer key, true data and counterfactual components to the separate store; write-only, no read path (FR-010)
- [ ] T017a [P] [US2] Test: nothing in `src/pharmagentics/generator/` opens or imports from the answer-key store for reading (static scan; checked again by spec 010 T004)
- [ ] T018 [P] [US2] Test: every event appears in the cut at the logged magnitude within tolerance (SC-002)
- [ ] T019 [P] [US2] Test: every answer-key record has every field filled
- [ ] T020 [US2] Edge-case tests: event outside the span, same-cut collision, holiday overlap

## Phase 5: User Story 3 - Dev and held-out splits (P2)

- [ ] T021 [US3] Scenario request format and loader in `scenarios.py` (FR-012). The case builder is spec 010 T036, not here.
- [ ] T022 [US3] Split logic and sealed held-out parameter file (FR-011)
- [ ] T023 [P] [US3] Test: the scenario requests cover every taxonomy category in both splits (SC-003)
- [ ] T024 [P] [US3] Test: scan agent-visible output for answer-key fields and held-out parameters, using the in-memory key from the run; zero hits (SC-004)
- [ ] T025 [US3] Resolve with the Forecast team: answer-key format, driver labels, held-out seed ownership (FR-015, FR-017)

## Phase 6: User Story 4 - Calibration (P3)

- [ ] T026 [US4] Decide drug class and competitor basket (FR-016); record in the decision log
- [ ] T027 [US4] Save public extracts with retrieval dates; fit scale, regional mix, specialty mix, PA and step-edit rates
- [ ] T028 [US4] Write the calibration report with fitted versus assumed per parameter (FR-014)

## Phase 7: Polish

- [ ] T029 [P] Quickstart: generate a dev world and a null world in one command
- [ ] T030 Update the data dictionary and README for the expanded world

## Dependencies

Setup, then Foundational, then US1. US2 needs US1. US3 needs US2. US4 can start after US1. Specs 002 to 010 need only US1 and US2 to begin.

## White-box tests owed (Architecture §12)

Determinism, invariants, event realization, answer-key completeness, isolation scan. All are listed above.
