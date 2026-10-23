# Tasks: Competitive Intelligence

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/ci/` and test folders
- [ ] T002 [P] Use `CandidateChange`, KPI table and detection summary models from core-004
- [ ] T003 [P] Anchor-week fixtures from `day1-v1`: 2025-04-21, 2025-12-22, 2025-12-29, 2026-04-06, 2026-04-27, 2026-06-08, 2026-07-06; plus dev null weeks

## Phase 2: Foundational

- [ ] T004 KPIs over the governed view with 30-day normalization and coverage labels (`kpis.py`) (FR-001, FR-002)
- [ ] T005 Baselines, including trailing 13 weeks (`baselines.py`) (FR-003)
- [ ] T006 Like-for-like comparisons from the health report (`likeforlike.py`) (FR-008)

## Phase 3: User Story 1 - Governed KPIs (P1) MVP

- [ ] T007 [P] [US1] Test: KPI cells match an independent calculation (SC-005)
- [ ] T008 [P] [US1] Test: 2026-07-06 national BXA TRx 3,665 labeled "7 of 8 territories" (P1-Q1)
- [ ] T009 [P] [US1] Test: 2026-04-06 vs 2026-03-30 like-for-like 4,005 → 3,860 (−3.6%), not −18.4% (P2-Q1)
- [ ] T010 [US1] Test: a 30-to-90-day conversion does not read as a TRx drop

## Phase 4: User Story 2 - Flag material changes (P1)

- [ ] T011 [US2] Seasonality decomposition (`decompose.py`) and robust z (`score.py`)
- [ ] T012 [US2] Three-threshold filter with margins (`filters.py`) (FR-006)
- [ ] T013 [US2] Peer-relative comparison (`peers.py`) (FR-004)
- [ ] T014 [US2] Multiple-testing control; decide A5 and log it (`multitest.py`) (FR-012)
- [ ] T015 [P] [US2] Test: zero candidates on 2025-04-21 (P1-Q3, SC-002)
- [ ] T016 [P] [US2] Test: 2026-06-08 raises Pacific and Metacora candidates and a tested-and-dropped list (P1-Q5, FR-014)
- [ ] T017 [P] [US2] Test: South Central September 2026 gap is a candidate via the peer comparison (P2-Q3)
- [ ] T018 [P] [US2] Test: the Mid-Atlantic Part D plan change (Aug–Oct 2025) is reached at plan level (P2-Q4)
- [ ] T019 [US2] Tune thresholds and A5 settings on dev null weeks only; recall ≥ 90% (SC-001)

## Phase 5: User Story 3 - Calendar effects (P1)

- [ ] T020 [US3] Holiday and plan-year tags with prior-year comparison (`calendar.py`) (FR-007)
- [ ] T021 [P] [US3] Test: 2025-12-22 and 2025-12-29 tagged, cite −18.9% and −18.2% a year earlier, not ranked (P3-Q2, SC-003)
- [ ] T022 [US3] Test: an excess beyond the seasonal pattern is still flagged

## Phase 6: User Story 4 - Rank and hand off (P1)

- [ ] T023 [US4] Business impact in core-002; confirm with the Forecast team (FR-009, A4)
- [ ] T024 [US4] Rank and cap; report drops (`rank.py`)
- [ ] T025 [US4] Stage entry point: candidates, summary, one request, ROUTINE on none (`stage.py`) (FR-010, FR-011)
- [ ] T026 [P] [US4] Test: 2026-04-27 share change ranks first (P3-Q1, SC-004)
- [ ] T027 [P] [US4] Test: identical candidates on rerun (SC-006)

## Phase 7: Polish

- [ ] T028 [P] Test on a 10× world (FR-015)
- [ ] T029 `quickstart.md`: tuning method and results

## Dependencies

Needs core-002 (thresholds, impact, calendar), core-003 (governed view, health report) and core-004 (schemas). brief-002 consumes the request. Tune on dev only; never on held-out.
