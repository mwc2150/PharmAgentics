# Tasks: Semantic Layer

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `semantic_layer/` and `src/pharmagentics/semantic/` skeletons
- [ ] T002 [P] Pydantic models for every file in `models.py`
- [ ] T003 [P] Error types in `errors.py`

## Phase 2: Foundational

- [ ] T004 Loader: read, validate, hash, version (`loader.py`) (FR-013, FR-014)
- [ ] T005 Cross-file checks: unique IDs across lanes, no zero or negative thresholds, coverage min ≤ max, no phrase both allowed and banned

## Phase 3: User Story 1 - One definition per metric (P1) MVP

- [ ] T006 [P] [US1] Test: every metric field in `rx_weekly` and `forecast_vs_actual_weekly` has an entry or a non-metric entry, read from `data_dictionary.json` (SC-001)
- [ ] T007 [P] [US1] Test: unknown metric and dimension raise (SC-002)
- [ ] T008 [US1] `metrics.yaml`: TRx, NRx, NBRx, TRx 30-day equivalent, market share (basket share, defined as such), NBRx share; context metrics (FR-002, FR-004)
- [ ] T009 [US1] `metrics_forecast.yaml` with Alvin and Sienna: forecast metrics with A − F and (A − F) / F definitions (FR-003)
- [ ] T010 [US1] `dimensions.yaml` including plan; members read from `dim_*` tables (FR-005, FR-016)
- [ ] T011 [US1] `api.get_metric`, `api.get_dimension`

## Phase 4: User Story 2 - Rules in one place (P1)

- [ ] T012 [US2] `rules.yaml` including the small-cell floor; `contracts.yaml` with gate thresholds and restatement window (FR-006, FR-007)
- [ ] T013 [US2] `sql_params.py`: render gate thresholds into the v0 view SQL; loader falls back to defaults if the layer is absent
- [ ] T014 [P] [US2] Test: default values reproduce today's withheld cuts on `day1-v1` (`tests/test_data_load.py` still passes)
- [ ] T015 [P] [US2] Test: a changed coverage floor changes the withheld set and the layer version (SC-003, SC-004)
- [ ] T016 [P] [US2] Test: invalid files fail with file and field named

## Phase 5: User Story 3 - Wording and glossary (P2)

- [ ] T017 [US3] `terms.yaml`: banned ("statistical surveillance", "surveillance"), NBRx-only "new patients", reader jargon, association wording, confidence wording, functions to involve (FR-010, FR-011)
- [ ] T018 [US3] `api.glossary` (FR-015)
- [ ] T019 [P] [US3] Test: glossary equals layer text; term scopes enforced

## Phase 6: User Story 4 - Catalogs and caps (P2)

- [ ] T020 [US4] `catalog_briefing.yaml` including inventory (S5, proposed) and rep vacancy; `caps_briefing.yaml` with starting values (FR-008, FR-009)
- [ ] T021 [US4] With Alvin and Sienna: `catalog_forecast.yaml`, `caps_forecast.yaml` (round cap 8)
- [ ] T022 [US4] Contract test: every catalog tool exists in the registry; every tool field has an entry (SC-007; runs once core-004 tools exist)
- [ ] T023 [P] [US4] Test: every driver label in each eval pack is in its catalog (SC-006)
- [ ] T024 [P] [US4] Test: adding a Forecast entry leaves Briefing entries unchanged
- [ ] T025 Resolve open items: aggregation floor (Eval 5), Briefing caps (Eval 17), restatement window (S4)

## Phase 7: Polish

- [ ] T026 [P] Scan all project docs and prompts for banned terms, exempting lines that list them (SC-005)
- [ ] T027 `quickstart.md`: how to add a metric, a catalog entry or a cap

## Dependencies

core-001 supplies the field list (done). US1 and US2 first. core-003 needs US2 for gate thresholds. US3 and US4 can run in parallel after US1.
