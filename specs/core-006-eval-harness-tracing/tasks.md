# Tasks: Evaluation Harness and Tracing

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: In progress (2026-10-29). Paths are now under `eval/` (see plan.md). Done: T001, T005, T008, T019. Built beyond the original list: scripted baselines for both lanes and the evidence checks (EV-1.1, EV-6.1, EV-6.2 re-run each claim's SQL). Partly done: T002 (case and answer models only), T004 (no runtime probe yet), T006 (no held-out access log), T010 (Forecast cases drafted as F-001 to F-018), T011 (reruns work; no core-005 replay yet), T014 (CLI; no versions-by-dimensions scorecard yet).

## Phase 1: Setup

- [x] T001 Create `eval/` (golden, harness, labels, tests, mlflow)
- [ ] T002 [P] Models: case, experiment, scorecard, failure entry, span attributes
- [ ] T003 [P] Agree with Alvin and Sienna: answer-key format, tags, confidence, driver labels, held-out rules (FR-012; S10; Eval 8 to 12)

## Phase 2: Foundational

- [ ] T004 `store.py` and `isolation.py`: env-var store, import scan, committed-file scan, runtime probe (FR-006)
- [x] T005 [P] Test: scan passes on the tree; a planted reader and a planted `answer_key.csv` each fail it (SC-002)
- [ ] T006 Case model, splits and access log (`cases.py`) (FR-008)
- [ ] T007 Span helpers and attribute vocabulary (`tracing/spans.py`) (FR-010)

## Phase 3: User Story 4 - Dev anchor cases (P1) MVP

- [x] T008 [US4] User-story importer: 24 Briefing stories to `eval/golden/briefing/` (C-001 … C-024) (FR-007)
- [ ] T009 [US4] Review each imported case by hand against `docs/planning/user-stories.md`; freeze
- [ ] T010 [P] [US4] Hand the 18 Forecast stories to Alvin and Sienna as `TC` drafts

## Phase 4: User Story 1 - One command (P1)

- [ ] T011 [US1] Runner with reruns, replay through core-005, artifact capture (`runner.py`) (FR-001, FR-003)
- [ ] T012 [P] [US1] Auto items EV-1.1, EV-1.2; EV-2.1 to 2.4; EV-3.1, 3.2, 3.3 (auto), 3.4
- [ ] T013 [P] [US1] Shared parallel-pair functions (`items/shared.py`) (FR-005)
- [ ] T014 [US1] Scorecard layout (`scorecard.py`); CLI (SC-001)
- [ ] T015 [US1] First scorecard row: Briefing scripted baseline on the dev cases

## Phase 5: User Story 3 - Tracing and provenance (P1)

- [ ] T016 [US3] Instrument stages, tools, agent turns and model calls (FR-010)
- [ ] T017 [US3] Provenance links token → tool record → span (`provenance.py`)
- [ ] T018 [P] [US3] Test: every link in a dev brief resolves (SC-003)
- [x] T019 [US3] MLflow run, rerun and trace logging (`eval/harness/run.py`) (FR-011)

## Phase 6: User Story 5 - Held-out and back-test (P1)

- [ ] T020 [US5] Held-out guard, score-before-change, target-loosening guard (`regression.py`) (FR-008, FR-016)
- [ ] T021 [P] [US5] Test: planted regression blocks merge (SC-006)
- [ ] T022 [US5] Ten-week back-test and four outputs (`backtest.py`) (FR-009, SC-005)
- [ ] T023 [US5] Gold briefs: blind, timed, a subset double-written (Eval 6)

## Phase 7: User Story 6 - Failures, judge, ablation (P2)

- [ ] T024 [US6] Failure catalog per lane (`failures.py`) (FR-012)
- [ ] T025 [US6] Rubric sheets and anchors (`rubric.py`) (FR-013, Eval 13)
- [ ] T026 [US6] Judge-human agreement (`agreement.py`) (FR-014)
- [ ] T027 [US6] Remaining Briefing items EV-4.x (incl. 4.5), 5.x, 6.x, 7.x (incl. 7.5), 8.x, 9.x (SC-008, SC-009)
- [ ] T028 [US6] Ablation and trajectory diversity (`ablation.py`) (FR-015); stability and cost (FR-017)

## Phase 8: Schedule and polish

- [ ] T029 Check-in packs per Evaluation Pack §9 (SC-010)
- [ ] T030 Failure walk-through for the final presentation
- [ ] T031 [P] `quickstart.md`: run the dev suite and read the scorecard

## Dependencies

T004 and T008 can start now on `day1-v1`. Scored runs need core-005 and the stages. Held-out needs core-001 US4. Opening held-out is a human decision, never automatic.
