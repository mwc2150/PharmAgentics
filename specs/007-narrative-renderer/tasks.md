# Tasks: Narrative and Renderer

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/narrative/`, `prompts/narrative/`, `tests/unit/narrative/`
- [ ] T002 [P] Define draft, claim and template models
- [ ] T003 [P] Draft the template from Architecture §5.5; mark length limit and sections in the semantic layer (FR-004)

## Phase 2: Foundational

- [ ] T004 Token parse, resolve and rounding (`tokens.py`)
- [ ] T005 Renderer that fails on unresolved tokens (`renderer.py`)
- [ ] T006 Confidence-to-wording table in data form (`wording.py`)

## Phase 3: User Story 1 - Code writes the numbers (P1) MVP

- [ ] T007 [P] [US1] Test: every figure in a draft is a token (SC-001)
- [ ] T008 [P] [US1] Test: rendered numbers equal pinned-data values after rounding (SC-002)
- [ ] T009 [US1] Writer with structured output, input limited to the closed evidence pack (`writer.py`) (FR-001, FR-002)
- [ ] T010 [US1] Store claims in `brief_claims` with evidence IDs (FR-015)
- [ ] T011 [US1] Pin the prompt version in the run record (FR-016)

## Phase 4: User Story 2 - The Monday format (P1)

- [ ] T012 [US2] KPI table builder and glossary hook (`kpi_table.py`) (FR-005)
- [ ] T013 [US2] Template assembly and length cap (`template.py`)
- [ ] T014 [P] [US2] Test: routine, warning and eventful weeks all match the template (FR-007)
- [ ] T015 [P] [US2] Test: stories ordered by impact; length within limit (SC-005)

## Phase 5: User Story 3 - Plain words, honest confidence (P1)

- [ ] T016 [US3] Prompts with STE style guide and wording rules
- [ ] T017 [P] [US3] Test: no causal verb at Medium or Low (FR-008)
- [ ] T018 [P] [US3] Test: Low stories appear under "investigate next" with the function to involve
- [ ] T019 [US3] Human rubric run for plain-language score (EV-7.1); anchors per Evaluation Pack open item 13

## Phase 6: User Story 4 - Continuity, restatements, next steps (P2)

- [ ] T020 [US4] Continuity object from episodic memory (`continuity.py`)
- [ ] T021 [US4] Footnotes: data health and restatement disclosure (`footnotes.py`)
- [ ] T022 [P] [US4] Test: restatement cases disclose old and new values (SC-003)
- [ ] T023 [P] [US4] Test: multi-week stories state new or continuing, direction (SC-007)

## Phase 7: User Story 5 - Governance (P1)

- [ ] T024 [P] [US5] Test: seeded rep-vacancy case yields no individual reference (SC-008)
- [ ] T025 [P] [US5] Test: banned terms absent; "new patients" only for NBRx

## Phase 8: Revision and polish

- [ ] T026 Revision pass from verifier flags or reviewer comments (FR-017)
- [ ] T027 Resolve the template and length with the mentor (Evaluation Pack open item 4)
- [ ] T028 [P] Quickstart: draft and render a brief for one dev week

## Dependencies

Needs 006 output, 005 evidence schema and 002 glossary. 008 checks this stage's output. 009 sequences it.

## White-box tests owed

Token resolution, digit scan, wording table, template conformance. Reconciliation is black-box (EV-1.1) and scored in 010.
