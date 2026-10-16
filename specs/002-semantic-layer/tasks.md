# Tasks: Semantic Layer

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `semantic_layer/` and `src/pharmagentics/semantic/` skeletons
- [ ] T002 [P] Define Pydantic models for metrics, dimensions, rules, contracts, catalog, caps, terms in `models.py`
- [ ] T003 [P] Define error types in `errors.py`

## Phase 2: Foundational

- [ ] T004 Loader: read YAML, validate, compute content hash and `layer_version` in `loader.py`
- [ ] T005 Cross-file checks: unique IDs, no zero or negative thresholds, no phrase both allowed and banned (FR-011)

## Phase 3: User Story 1 - One definition per metric (P1) MVP

**Independent Test**: Every Rx field has an entry; an unknown ID raises.

- [ ] T006 [P] [US1] Test: every field in `data_dictionary.json` `rx_weekly` has a metric entry or a non-metric entry (SC-001)
- [ ] T007 [P] [US1] Test: unknown metric ID and unknown dimension raise (SC-002)
- [ ] T008 [US1] Write `metrics.yaml` for TRx, NRx, NBRx, TRx 30-day equivalent, market share, NBRx share
- [ ] T008a [US1] Add context metrics (days-supply 90-day share, inventory, promotion, access) with `kind: context` and no thresholds (FR-002). Include `share_90day_fills_proxy` from the Rx table.
- [ ] T009 [US1] Write `dimensions.yaml` (week, geography, payer channel, specialty) with no fixed sizes (FR-013)
- [ ] T010 [US1] Implement `api.get_metric` and `api.get_dimension`

## Phase 4: User Story 2 - Rules in one place (P1)

- [ ] T011 [P] [US2] Test: a changed threshold changes the layer version (SC-003, SC-004)
- [ ] T012 [P] [US2] Test: invalid files fail with file and field named
- [ ] T013 [US2] Write `rules.yaml` (thresholds, basket, holiday calendar, plan-year resets), `contracts.yaml` (3-week restatement window), `caps.yaml` (starting values from plan)
- [ ] T014 [US2] Record the layer version in the run record (interface only; wired in spec 009)

## Phase 5: User Story 3 - Wording and glossary (P2)

- [ ] T015 [P] [US3] Test: glossary text equals layer text for the requested IDs
- [ ] T016 [P] [US3] Test: "statistical surveillance" is banned; "new patients" is allowed only for NBRx
- [ ] T017 [US3] Write `terms.yaml`; implement `api.glossary`

## Phase 6: User Story 4 - Catalog and shared use (P2)

- [ ] T018 [US4] Write `catalog.yaml`: driver categories (access, promotion, competitor, inventory, rep vacancy, mix shift, days-supply shift), artifact types, calendar effects. Each entry lists `tests` (tool names) and `context_metrics` (FR-006).
- [ ] T018a [US4] Contract test: every catalog `tests` name exists in the tool registry, and every field a tool returns has a metric or context-metric entry (SC-007). Runs once spec 005 tools exist.
- [ ] T019 [US4] Test: every driver label in the Evaluation Pack and Forecast agent is in the catalog (SC-006). Needs the Forecast team's labels.
- [ ] T020 [US4] Test: adding a Forecast metric leaves briefing entries unchanged
- [ ] T021 Resolve open items: aggregation floor (FR-014), cap values (FR-015)

## Phase 7: Polish

- [ ] T022 [P] Scan all project docs for banned terms (SC-005). Exempt text that lists a term as banned.
- [ ] T023 Document how to add a metric in `quickstart.md`

## Dependencies

001 supplies the field list. US1 and US2 first. US3 and US4 can run in parallel after US1.

## White-box tests owed

Every Rx field has an entry; unknown ID raises (Architecture §14 acceptance criterion); both are in US1.
