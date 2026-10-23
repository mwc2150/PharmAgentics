# Tasks: Verifier

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/verifier/` and test folders
- [ ] T002 [P] Verification result, flag and failure-tag models
- [ ] T003 [P] Planted-error fixtures, one per Briefing user-story "must not say" plus the generic set

## Phase 2: Foundational

- [ ] T004 Briefing failure-tag list; agree a shared list with the Forecast team when S10 is settled (FR-014)
- [ ] T005 Driver: checks in order, flags collected (`verify.py`)

## Phase 3: User Story 1 - Wrong numbers (P1) MVP

- [ ] T006 [US1] Token and stray-digit checks (`tokens_check.py`)
- [ ] T007 [US1] Reconcile to the pinned snapshot (`reconcile.py`)
- [ ] T008 [P] [US1] Test: each planted numeric error rejected and named (SC-001)
- [ ] T009 [P] [US1] Test: "Great Lakes BXA TRx was 670" fails on 2026-07-06 (P1-Q1)
- [ ] T010 [P] [US1] Test: an April brief reconciles to 692; 742 fails (P2-Q5)

## Phase 4: User Story 2 - Evidence (P1)

- [ ] T011 [US2] Coverage and link resolution (`evidence_check.py`)
- [ ] T012 [P] [US2] Test: P1-Q4 claim links open both records and spans (SC-002)

## Phase 5: User Story 3 - Disclosure and coverage (P1)

- [ ] T013 [US3] `disclosure_check.py` (FR-005)
- [ ] T014 [P] [US3] Test: missing 692 → 742 disclosure and missing "7 of 8" label each fail (SC-003)

## Phase 6: User Story 4 - Governance and wording (P1)

- [ ] T015 [US4] `wording_check.py` and `governance.py` (FR-006 to FR-009)
- [ ] T016 [P] [US4] Test: rep line, banned terms, NRx "new patients", jargon, causal promotion, small-cell generalization, promotion credit without a supported verdict — each caught (SC-004, SC-005)

## Phase 7: User Story 5 - Judge (P2)

- [ ] T017 [US5] Judge and agreement (`judge.py`, `agreement.py`)
- [ ] T018 [US5] Shadow-mode gate; set the bar with the mentor (FR-010, Eval 2)
- [ ] T019 [P] [US5] Test: causal claim on Medium flagged by code (SC-005)

## Phase 8: User Story 6 - Revision (P1)

- [ ] T020 [US6] One revision; then VERIFICATION_FLAGGED (FR-011)
- [ ] T021 [P] [US6] Test: fixable passes after one revision; unfixable reaches review flagged (SC-007)

## Phase 9: Polish

- [ ] T022 Wire failure tags into the core-006 catalog
- [ ] T023 [P] `quickstart.md`: verify a brief and read the flags

## Dependencies

Needs brief-003 output, core-004 records, core-002 terms, core-003 snapshot reads. core-005 sequences it; core-006 scores the planted-error suite.
