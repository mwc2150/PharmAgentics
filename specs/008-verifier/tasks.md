# Tasks: Verifier

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/verifier/` and `tests/unit/verifier/`
- [ ] T002 [P] Define verification result, flag and failure-tag models
- [ ] T003 [P] Planted-error fixtures: wrong number, missing token, stray digit, missing evidence, rep name, banned term, "new patients" on NRx, causal wording on Medium, number from newer data

## Phase 2: Foundational

- [ ] T004 Shared failure-tag list; agree with the Forecast team (Evaluation Pack open item 12)
- [ ] T005 Verification driver: run checks in order, collect flags (`verify.py`)

## Phase 3: User Story 1 - Reject wrong numbers (P1) MVP

- [ ] T006 [P] [US1] Test: each planted numeric error is rejected and named (SC-001)
- [ ] T007 [US1] Token and stray-digit checks (`tokens_check.py`)
- [ ] T008 [US1] Reconcile to the pinned snapshot with stated rounding (`reconcile.py`)
- [ ] T009 [US1] Test: a value from newer data fails; only the pinned snapshot counts

## Phase 4: User Story 2 - Evidence coverage (P1)

- [ ] T010 [US2] Story and numeric-claim evidence coverage (`evidence_check.py`)
- [ ] T011 [P] [US2] Test: link resolution opens the span and output on the pinned snapshot (EV-6.2 input)

## Phase 5: User Story 3 - Governance (P1)

- [ ] T012 [US3] Individual-identification scan, banned terms, NRx vs NBRx rule (`governance.py`)
- [ ] T013 [P] [US3] Test: each planted governance error is caught (SC-003)
- [ ] T014 [US3] Wording check per metric from the semantic layer (`wording_check.py`)

## Phase 6: User Story 4 - Judge (P2)

- [ ] T015 [US4] Judge for faithfulness and overclaiming (`judge.py`)
- [ ] T016 [US4] Human-labeled brief set; agreement statistics (`agreement.py`) (SC-005)
- [ ] T017 [US4] Shadow-mode gate: judge does not score until agreement meets the bar. Set the bar with the mentor (FR-010)
- [ ] T018 [P] [US4] Test: causal claim on Medium is flagged (SC-004)

## Phase 7: User Story 5 - Revision loop (P1)

- [ ] T019 [US5] One revision call to the narrative stage; then `VERIFICATION_FLAGGED` with flags (FR-011)
- [ ] T020 [P] [US5] Test: fixable error passes after one revision; unfixable reaches review flagged (SC-006)

## Phase 8: Polish

- [ ] T021 Wire failure tags into the failure catalog (spec 010)
- [ ] T022 [P] Quickstart: verify a brief and read the flags

## Dependencies

Needs 007 output, 005 evidence schema, 002 terms. 009 sequences it. 010 scores the planted-error suite.

## White-box tests owed (Architecture §12)

Judge agreement with human labels (T016). Planted wrong number rejected (T006). Governance planted cases (T013).
