# Tasks: Triage, Manager and Specialists

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/triage/`, `prompts/triage/`, test folders
- [ ] T002 [P] Decide the framework (A3) and wire tool registration; record the decision
- [ ] T003 [P] Fixtures: the `day1-v1` anchors (Mid-Atlantic access and restoration, Great Lakes lapse, Pacific supply, Southeast lapse, South Central gap, 2026-04-06 artifact, 2026-06-08 compound week) and a conflict stress case

## Phase 2: Foundational

- [ ] T004 Ledgers and no-repeat guard (`ledgers.py`) (FR-006, FR-016)
- [ ] T005 Caps and defined exit (`caps.py`) (FR-017)
- [ ] T006 Code test library per catalog entry (`tests_catalog.py`) (FR-020)
- [ ] T007 Episodic memory and continuity (`memory.py`) (FR-018)

## Phase 3: User Story 1 - Triage (P1) MVP

- [ ] T008 [P] [US1] Test: withheld-cut candidates dropped with reason (FR-003)
- [ ] T009 [P] [US1] Test: 2026-06-08 gives two stories, Pacific first (P1-Q5)
- [ ] T010 [P] [US1] Test: Metacora links to the open story and is marked continuing (P3-Q4)
- [ ] T011 [US1] Code triage rules (`rules.py`) and manager grouping and ordering (`manager.py`)
- [ ] T012 [US1] TRIAGE_REVIEW path and plan-review switch (FR-005, FR-019)
- [ ] T013 [US1] Log the layer for each call; clarify A1 and update the spec

## Phase 4: User Story 2 - Forensics then drivers (P1)

- [ ] T014 [US2] Data Forensics (`forensics.py`) (FR-007)
- [ ] T015 [US2] Driver Investigator (`drivers.py`) (FR-008, FR-009, FR-011)
- [ ] T016 [P] [US2] Test: 2026-04-06 closes as a data artifact with the like-for-like change (P2-Q1)
- [ ] T017 [P] [US2] Test: Mid-Atlantic Aug–Oct 2025 supports access and rules out the other four with evidence (P2-Q2)
- [ ] T018 [P] [US2] Test: Pacific June 2026 supports inventory; competitor and promotion ruled out (P3-Q3)
- [ ] T019 [US2] Decomposition to plan and specialty; sums to total (FR-012, P2-Q4)

## Phase 5: User Story 3 - Promotion verdicts (P1)

- [ ] T020 [US3] Promotion rules (`promotion.py`) (FR-010)
- [ ] T021 [P] [US3] Test: Great Lakes lapse supported as an association, method and controls named (P4-Q1)
- [ ] T022 [P] [US3] Test: Mid-Atlantic Nov–Dec 2025 promotion ruled out; access leads; seasonal share noted (P4-Q4)
- [ ] T023 [P] [US3] Test: no promotion credit in any window where activity did not change (SC-005)

## Phase 6: User Story 4 - Honest closure (P1)

- [ ] T024 [US4] Closure rules (`closure.py`) (FR-013, FR-014)
- [ ] T025 [P] [US4] Test: South Central closes Low, unresolved, with checks run and next checks (P2-Q3)
- [ ] T026 [P] [US4] Test: two-lapse promotion finding is Medium, names both, states the next read (P4-Q5)
- [ ] T027 [P] [US4] Test: a contaminated control is dropped and recorded
- [ ] T028 [US4] Calibration table by level on dev seeds (SC-006)

## Phase 7: User Story 5 - The loop ends (P1)

- [ ] T029 [P] [US5] Test: depth two; specialists cannot call agents (FR-015)
- [ ] T030 [P] [US5] Test: repeated test refused (FR-016)
- [ ] T031 [P] [US5] Test: each cap's exit closes the story unresolved and the run continues (SC-008)
- [ ] T032 [US5] Stress case: exit by finite-search or stall rule

## Phase 8: User Story 6 - Replay (P2)

- [ ] T033 [US6] Span per ledger update with snapshot; replay from a trace

## Phase 9: Baseline and eval

- [ ] T034 Scripted manager-off baseline (`scripted.py`) (FR-021)
- [ ] T035 Parameter accuracy ≥ 95%; tool-sequence diversity vs scripted (SC-011)
- [ ] T036 Run EV-2.2, EV-4.x, EV-5.x on dev cases; log failure tags

## Dependencies

Needs core-002 (catalog, caps), core-003, core-004 (tools) and brief-001 (request). brief-003 consumes the result. core-006 scores it. Held-out stays closed until check-ins.
