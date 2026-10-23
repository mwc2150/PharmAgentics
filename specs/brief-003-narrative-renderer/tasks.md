# Tasks: Narrative and Renderer

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/narrative/`, `prompts/narrative/`, test folders
- [ ] T002 [P] Draft, template and continuity models; use `brief_claim` from core-004
- [ ] T003 [P] Template from Briefing Architecture §5.5 plus data-health-first and promotion context; limits in core-002 (FR-004)

## Phase 2: Foundational

- [ ] T004 Token parse, resolve, rounding (`tokens.py`); renderer fails on unresolved (`renderer.py`)
- [ ] T005 Wording map and association wording from core-002 (`wording.py`)
- [ ] T006 Code-built tables and disclosures (`tables.py`, `disclosures.py`) (FR-005, FR-011, FR-012)

## Phase 3: User Story 1 - Code writes the numbers (P1) MVP

- [ ] T007 [P] [US1] Test: every figure in a draft is a token (SC-001)
- [ ] T008 [P] [US1] Test: rendered numbers equal pinned values after rounding (SC-002)
- [ ] T009 [US1] Writer with structured output, input limited to the closed pack (`writer.py`) (FR-001, FR-002)
- [ ] T010 [US1] Store claims; pin prompt version (FR-017, FR-018)

## Phase 4: User Story 2 - Monday format (P1)

- [ ] T011 [US2] Template assembly and length cap (`template.py`)
- [ ] T012 [P] [US2] Golden tests: 2025-04-21 routine, 2026-05-04 data-health-first, 2026-08-24 eventful (P1-Q3, P1-Q2, P1-Q6)
- [ ] T013 [P] [US2] Test: stories ordered by impact; length within limit (SC-005)

## Phase 5: User Story 3 - Plain words (P1)

- [ ] T014 [US3] Prompts with the STE guide and wording rules
- [ ] T015 [P] [US3] Test: no jargon terms in reader text; no causal verb at Medium or Low; promotion always associative
- [ ] T016 [US3] Rubric run on the Pacific story (P3-Q3, EV-7.1)

## Phase 6: User Story 4 - Continuity, restatements, coverage (P2)

- [ ] T017 [US4] Continuity object (`continuity.py`) (FR-010)
- [ ] T018 [P] [US4] Test: 2026-09-28 Metacora continuing, week 31, flat for 8 weeks (P3-Q4)
- [ ] T019 [P] [US4] Test: 2026-07-13 discloses 692 → 742 with date and reason; 7-of-8 labels (P3-Q6)
- [ ] T020 [P] [US4] Test: Southeast next step names sales leadership at territory level (P3-Q5, P4-Q6)
- [ ] T021 [P] [US4] Test: December 2025 holiday weeks labeled calendar effect with rebound expected (P3-Q2)

## Phase 7: User Story 5 - Promotion context (P2)

- [ ] T022 [US5] Promotion context table and limits statement (FR-014, FR-015)
- [ ] T023 [P] [US5] Test: Southeast table shows calls and impressions beside TRx; says reach cannot be shown (P4-Q3)
- [ ] T024 [P] [US5] Test: cash cells marked noisy; no generalization (P4-Q2)

## Phase 8: User Story 6 - Governance (P1)

- [ ] T025 [P] [US6] Test: rep-vacancy case gives territory-level text only (SC-009)
- [ ] T026 [P] [US6] Test: banned terms absent; "new patients" only for NBRx

## Phase 9: Revision and polish

- [ ] T027 Revision pass from flags or comments (FR-019)
- [ ] T028 Test: every Briefing "must not say" is absent from its dev brief (SC-010)
- [ ] T029 Resolve the template (Eval 4) and A16 with the mentor
- [ ] T030 [P] `quickstart.md`: draft and render one dev week

## Dependencies

Needs brief-002 output, core-004 records and claims, core-002 terms. brief-004 checks the output; core-005 sequences it.
