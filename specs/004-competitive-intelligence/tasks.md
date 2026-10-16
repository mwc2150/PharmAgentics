# Tasks: Competitive Intelligence

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/ci/` and `tests/unit/ci/`
- [ ] T002 [P] Define `CandidateChange`, `KpiTable`, `DetectionSummary` models (FR-008)
- [ ] T003 [P] Build dev fixtures: seeded-event weeks, null weeks, holiday weeks, from spec 001

## Phase 2: Foundational

- [ ] T004 KPI computation over the governed view (`kpis.py`), including 30-day normalization (FR-001, FR-002)
- [ ] T005 Baselines: prior week, 4-week average, same week last year (`baselines.py`)

## Phase 3: User Story 1 - Governed KPIs (P1) MVP

- [ ] T006 [P] [US1] Test: KPI cells match an independent calculation (SC-005)
- [ ] T007 [P] [US1] Test: suppressed cuts produce no KPIs and record why
- [ ] T008 [US1] Test: a 30-to-90-day conversion does not read as a TRx drop

## Phase 4: User Story 2 - Flag material changes (P1)

- [ ] T009 [US2] Seasonality decomposition and residuals (`decompose.py`)
- [ ] T010 [US2] Robust z-scores (`score.py`)
- [ ] T011 [US2] Three-threshold filter from the semantic layer (`filters.py`); record margins (FR-013)
- [ ] T012 [US2] Multiple-testing control (`multitest.py`). Decide A5; log the decision (FR-010)
- [ ] T013 [P] [US2] Test: recall ≥ 90% on dev seeded events (SC-001)
- [ ] T014 [P] [US2] Test: ≤ 1 false flag per dev null week (SC-002)
- [ ] T015 [US2] Tune thresholds and multitest settings on dev null weeks only

## Phase 5: User Story 3 - Calendar effects (P1)

- [ ] T016 [US3] Holiday and plan-year-reset tagging (`calendar.py`)
- [ ] T017 [P] [US3] Test: Thanksgiving, Christmas, January weeks tagged and not ranked as business events (SC-003)
- [ ] T018 [US3] Test: an excess beyond the seasonal pattern in a holiday week is still flagged

## Phase 6: User Story 4 - Rank and hand off (P1)

- [ ] T019 [US4] Define business impact in the semantic layer; confirm with the Forecast team (FR-011)
- [ ] T020 [US4] Rank and cap (`rank.py`); report drops
- [ ] T021 [US4] Stage entry point; write candidate changes; set ROUTINE on none (`stage.py`)
- [ ] T022 [P] [US4] Test: order matches impact order on seeded events (SC-004)
- [ ] T023 [P] [US4] Test: identical candidates on rerun (SC-006)

## Phase 7: Polish

- [ ] T024 [P] Test on a 10x world (FR-014)
- [ ] T025 Document tuning method and results in `quickstart.md`

## Dependencies

Needs 002 (thresholds, impact, calendar) and 003 (view). 006 consumes candidates. Tuning uses dev seeds only. Never tune on held-out.

## White-box tests owed (Architecture §12)

Escalation precision (candidates that deserved investigation), detection precision and recall on dev seeds, determinism (T023).
