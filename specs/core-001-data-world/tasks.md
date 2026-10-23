# Tasks: Data World — Foundation, Generator and Injection Library

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: User Story 1 done (PR #1, merged 2026-10-21). Everything else not started.
**Format**: `[ID] [P?] [Story] Description`. `[P]` can run in parallel.

## Phase 1: Built (PR #1)

- [x] T001 [US1] Typed loader for the 14 release files with explicit file list (`src/pharmagentics/data/load_duckdb.py`) (FR-001)
- [x] T002 [US1] Import runs and SHA-256 manifest in `metadata` (FR-002)
- [x] T003 [US1] All-or-nothing import; failures leave the previous load intact (FR-003)
- [x] T004 [US1] Checker with counts, keys, quality, `--json`, `--fail-on-flags` (`check_duckdb.py`) (FR-004)
- [x] T005 [US1] v0 reporting views: expected, missing and duplicate keys; feed health; reportable Rx; weekly KPIs (`sql/001_reporting_views.sql`)
- [x] T006 [US1] 21 integration tests (`tests/test_data_load.py`) and CI on Python 3.11 and 3.12 (SC-001)

## Phase 2: Setup for the rest

- [ ] T007 Create the private store outside the repo; document `PHARMAGENTICS_EVAL_STORE` in `docs/DUCKDB_FIRST_RUN.md` without its location
- [ ] T008 [P] Add pytest to `requirements.txt` and confirm it runs the `unittest` suite unchanged (proposed answer to S15)
- [ ] T009 [P] Release verifier `src/pharmagentics/data/release.py`: a folder must match its validation report before load
- [ ] T010 [P] Test: no committed file in the repo matches the ground-truth patterns in `.gitignore` (SC-005; also run by core-006)

## Phase 3: User Story 2 - Rebuild from a seed (P1)

- [ ] T011 [US2] Port the `day1-v1` generator into the private store with settings-driven sizes (FR-005, FR-006)
- [ ] T012 [US2] Test: two runs with seed 7 give byte-identical agent-visible output; diff against `data/agent_visible/` (SC-002)
- [ ] T013 [P] [US2] Test: invariants, including territory forecasts and actuals summing to NATIONAL (FR-007)
- [ ] T014 [P] [US2] Test: a 10× territory world builds and loads with no schema change (SC-006)

## Phase 4: User Story 3 - Inject labeled events and artifacts (P1)

- [ ] T015 [US3] Event registry with type, label, ranges and affected cut
- [ ] T016 [P] [US3] Business events, including access restoration and promotion lapse (FR-009)
- [ ] T017 [P] [US3] Artifacts, including restatement delay and forecast/actual version mismatch (FR-010)
- [ ] T018 [US3] Calendar effects, null, compound, multi-week, anticipated-by-forecast and stress cases (FR-011)
- [ ] T019 [US3] Agree the answer-key format with Alvin and Sienna (FR-014, S10, Eval 8); write both tables to the private store
- [ ] T020 [P] [US3] Test: each event shows in its cut at the logged magnitude; every record complete (SC-003)
- [ ] T021 [US3] Edge-case tests: out-of-span event, same-cut collision, holiday overlap, zero-row cut

## Phase 5: User Story 4 - Dev and held-out (P2)

- [ ] T022 [US4] Scenario request format (FR-016)
- [ ] T023 [US4] Sealed held-out parameters; decide who generates held-out seeds (FR-015, Eval 11)
- [ ] T024 [P] [US4] Scenario requests cover every Briefing category and Forecast class in both splits (SC-004)
- [ ] T025 [US4] With Alvin: express LUMINA Week 18 as a scenario request in this world (FR-019, S3)

## Phase 6: User Story 5 - Calibration (P3)

- [ ] T026 [US5] Confirm the class with Dr. Admasu (FR-018, A12)
- [ ] T027 [US5] Save public extracts with retrieval dates; fit scale, regional and specialty mix, PA and step-edit rates
- [ ] T028 [US5] Calibration report: fitted vs assumed per parameter

## Dependencies

Phase 1 is done, so every other spec can start on `day1-v1` now. US2 then US3; US4 needs US3; US5 can follow US2. core-006 needs US3 and US4 for scored cases.
