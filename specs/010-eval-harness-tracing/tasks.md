# Tasks: Evaluation Harness and Tracing

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/evalharness/`, `src/pharmagentics/tracing/`, matching test folders
- [ ] T002 [P] Define case, experiment, scorecard, failure-catalog and span-attribute models
- [ ] T003 [P] Agree with the Forecast team: answer-key convention, failure tags, held-out rules (Evaluation Pack open items 8 to 12)

## Phase 2: Foundational

- [ ] T004 Isolation scan and runtime probe (`isolation.py`): flag any read outside the harness; allow only the generator's write path (FR-006)
- [ ] T005 Case loader with dev and held-out split and an access log (`cases.py`) (FR-007)
- [ ] T036 Case builder: Given/When/Then cases from the answer key and scenario requests, including "must say" and "must not say" (FR-021). Moved here from spec 001 (X1 fix).
- [ ] T006 Span helpers and the attribute vocabulary (`spans.py`) (FR-010)

## Phase 3: User Story 1 - One command scores a build (P1) MVP

- [ ] T007 [US1] Runner with reruns and artifact capture (`runner.py`) (FR-001, FR-003)
- [ ] T008 [P] [US1] Auto items EV-1.1, 1.2 (numeric reconciliation, restatement disclosure)
- [ ] T009 [P] [US1] Auto items EV-2.1 to 2.4
- [ ] T010 [P] [US1] Auto items EV-3.1, 3.2, 3.3 (auto part), 3.4
- [ ] T011 [US1] Scorecard layout, versions by dimensions (`scorecard.py`) (FR-005)
- [ ] T012 [US1] CLI: one command runs the suite and logs one experiment (SC-001)
- [ ] T013 [US1] Run the scripted baseline on dev; this is the first scorecard row

## Phase 4: User Story 2 - Answer-key isolation (P1)

- [ ] T014 [P] [US2] Test: scan passes on the current tree
- [ ] T015 [P] [US2] Test: a planted reader outside the harness fails the scan (SC-002)
- [ ] T016 [US2] EV-9.3 as a continuous check in CI

## Phase 5: User Story 3 - Tracing and provenance (P1)

- [ ] T017 [US3] Instrument stages, tools, agent turns and model calls with spans; confirm all attributes (FR-010)
- [ ] T018 [US3] Claim provenance link builder (`provenance.py`) (FR-011)
- [ ] T019 [P] [US3] Test: every link in a dev brief resolves to a span (SC-003)
- [ ] T020 [US3] Phoenix experiment logging (`phoenix.py`) (FR-012)

## Phase 6: User Story 4 - Splits, held-out discipline, back-test (P1)

- [ ] T021 [US4] Held-out guard: sealed parameters, access log, score-before-change rule (FR-008)
- [ ] T022 [US4] Target-loosening guard and regression gate (`regression.py`) (FR-017)
- [ ] T023 [P] [US4] Test: planted regression is caught and blocks merge (SC-006)
- [ ] T024 [US4] Ten-week back-test and the four course-floor outputs (`backtest.py`) (FR-009, SC-004)
- [ ] T025 [US4] Gold briefs: blind, timed, a subset double-written; record time as the manual baseline (Evaluation Pack §7)

## Phase 7: User Story 5 - Failure catalog and judge agreement (P2)

- [ ] T026 [US5] Failure tags and catalog (`failures.py`) (FR-013)
- [ ] T027 [US5] Human rubric sheets and anchors (`rubric.py`) (FR-014). Settle anchors with the mentor.
- [ ] T028 [US5] Judge-human agreement report (`agreement.py`) (FR-015)
- [ ] T029 [US5] Remaining items: EV-4.x, 5.x, 6.x, 7.x, 8.x, 9.x by their methods, including critical error rate (EV-8.3, SC-009)
- [ ] T029a [US5] Data-inventory review record for each release (EV-9.4, SC-010)

## Phase 8: User Story 6 - Ablation and stability (P2)

- [ ] T030 [US6] Manager-off ablation and trajectory-diversity report (`ablation.py`) (FR-016)
- [ ] T031 [US6] Run-to-run stability report (EV-8.4) (FR-018)
- [ ] T032 [US6] Cost and time comparison against timed gold briefs (FR-020; EV-8.2)

## Phase 9: Schedule and polish

- [ ] T033 Check-in packs per Evaluation Pack §9: Oct 30 low-code, Nov 23 baseline, Nov 27 triage, Dec 4 executed pack, Dec 7 full model, Dec 14 final
- [ ] T034 Failure walk-through for the final presentation
- [ ] T035 [P] Quickstart: run the suite on a dev seed and read the scorecard

## Dependencies

Starts after 001 provides cases. Tracing (US3) needs the stages to emit spans, so it grows with 003 to 009. T013 needs only the scripted baseline. Held-out opening is a human decision, never automatic.

## White-box tests owed

Isolation scan, planted regression, planted reader, agreement statistic, scorecard layout stability.
