# Tasks: Triage, Manager and Specialists

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/triage/`, `prompts/`, `tests/unit/triage/`
- [ ] T002 [P] Decide the framework (A3) and wire tool registration; record in the decision log
- [ ] T003 [P] Dev fixtures: single-event weeks, compound weeks, masked-by-artifact weeks, ambiguous cases, a conflict stress case (from spec 001)

## Phase 2: Foundational

- [ ] T004 Ledgers and no-repeat guard (`ledgers.py`) (FR-007, FR-016)
- [ ] T005 Cap enforcement and defined exit (`caps.py`) (FR-017)
- [ ] T006 Hypothesis test library: code tests per catalog entry (`tests_catalog.py`) (FR-020)
- [ ] T007 Episodic memory query over prior stories and claims (`memory.py`) (FR-018)

## Phase 3: User Story 1 - Triage (P1) MVP

- [ ] T008 [P] [US1] Test: failed-cut candidates dropped with a reason (FR-003)
- [ ] T009 [P] [US1] Test: grouping sees all candidates; compound weeks give two stories or a flagged interaction (FR-005)
- [ ] T010 [US1] Code triage rules (`rules.py`)
- [ ] T011 [US1] Manager grouping, ordering and first hypotheses (`manager.py`)
- [ ] T012 [US1] TRIAGE_REVIEW path and plan-review switch (FR-006, FR-019)
- [ ] T013 [US1] Log which layer made each call; report share per layer
- [ ] T014 [US1] Clarify A1 with the team and update the spec

## Phase 4: User Story 2 - Forensics then drivers (P1)

- [ ] T015 [US2] Data Forensics specialist (`forensics.py`) (FR-008, FR-009)
- [ ] T016 [US2] Driver Investigator specialist (`drivers.py`) (FR-010, FR-011)
- [ ] T017 [P] [US2] Test: seeded access restriction → artifact ruled out, access supported, promotion and competitor ruled out
- [ ] T018 [P] [US2] Test: seeded artifact closes as data artifact with no driver
- [ ] T019 [US2] Contribution decomposition integration (FR-012); test sums to total (SC-003)

## Phase 5: User Story 3 - Honest closure (P1)

- [ ] T020 [US3] Closure rules: label, confidence, abstention (`closure.py`) (FR-013, FR-014)
- [ ] T021 [P] [US3] Test: High, Medium, Low cases
- [ ] T022 [P] [US3] Test: ambiguous case abstains; strong case does not (SC-006)
- [ ] T023 [US3] Confidence calibration table by level on dev seeds (SC-005)

## Phase 6: User Story 4 - The loop ends (P1)

- [ ] T024 [P] [US4] Test: call depth is two; specialists cannot call agents (FR-015)
- [ ] T025 [P] [US4] Test: repeated test refused (FR-016)
- [ ] T026 [P] [US4] Test: each cap's exit path closes the story as unresolved (SC-007)
- [ ] T027 [US4] Stress case: trace shows exit by finite-search or stall rule (SC-009)

## Phase 7: User Story 5 - Replay (P2)

- [ ] T028 [US5] Emit a span per ledger update with a snapshot; verify replay from a trace

## Phase 8: Baseline and eval

- [ ] T029 Scripted manager-off baseline (`scripted.py`) (FR-022)
- [ ] T030 Parameter-extraction accuracy ≥ 95% (SC-011)
- [ ] T031 Trajectory-diversity report: tool sequences by case, agent vs scripted (SC-010)
- [ ] T032 Run EV-2.2, EV-4.x, EV-5.x on dev seeds; log failure tags

## Dependencies

Needs 003, 004, 005 and spec 002 caps. 007 consumes the result. 010 scores it. Held-out cases stay closed until check-ins.

## White-box tests owed (Architecture §12)

Router tool choice and parameter extraction ≥ 95% (T030). Convergence: steps to an answer and spread across reruns (T031). Escalation precision. Loop guardrails: call depth, no-repeat, each cap's exit (T024 to T027).
