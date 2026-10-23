# Tasks: Tool Interface and Handoff Contracts

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md)
**Status**: Not started.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/contracts/`, `src/pharmagentics/tools/`, `tests/contract/`
- [ ] T002 [P] Models for every object in data-model.md (FR-006)
- [ ] T003 [P] Typed errors (FR-005)
- [ ] T004 JSON Schema export to `contracts/`

## Phase 2: Foundational

- [ ] T005 `access.py` with allowlist; refuses the ground-truth store and its variable (FR-010)
- [ ] T006 `registry.py`: ID check, span, tool record, error mapping (FR-001, FR-002)
- [ ] T007 [P] `aggregation.py` floor and `smallcell.py` flag (FR-009, FR-013)

## Phase 3: User Story 1 - Typed tools (P1) MVP

- [ ] T008 [P] [US1] Contract test per tool: valid, invalid, unknown-ID inputs (SC-001)
- [ ] T009 [P] [US1] `get_metric`, `validate_feed`, `lookup_calendar`, `reconcile_numbers`
- [ ] T010 [P] [US1] `lookup_access_events`, `lookup_promo`, `lookup_inventory`, `compare_competitors`
- [ ] T011 [US1] Test: P1-Q4 figures (15.0 vs 23.8 NBRx a week; tier 2 → 3 with PA and ST from 2025-08-01) with records (SC-007)
- [ ] T012 [US1] Test: repeat calls identical; no tool imports a model client (FR-001)
- [ ] T013 [US1] Test: every success records a tool record with a span ID (SC-002)
- [ ] T014 [US1] Contract test with core-002: every tool field has an entry; every catalog tool exists

## Phase 4: User Story 2 - Schema handoffs (P1)

- [ ] T015 [US2] Builder: one `briefing.investigation_request` per run (FR-007)
- [ ] T016 [US2] Builder and validator for `briefing.investigation_result`
- [ ] T017 [P] [US2] Mutation tests: each broken required field is rejected and named (SC-006)

## Phase 5: User Story 3 - Individuals and ground truth (P1)

- [ ] T018 [P] [US3] Probe test: every tool and `access.py` refused for the ground-truth store (SC-003)
- [ ] T019 [P] [US3] Test: Southeast 2026-08 returns territory-level calls and impressions; vacancy count below floor returns `BelowFloor` (SC-004)
- [ ] T020 [US3] Agree the floor with the mentor (Eval 5); record in core-002

## Phase 6: User Story 4 - Locate and compare (P1)

- [ ] T021 [US4] `decompose_change` at territory, channel, plan, specialty (FR-011)
- [ ] T022 [US4] `compare_to_peers` with control-set rules (FR-012)
- [ ] T023 [P] [US4] Test: P2-Q4 decomposition sums; Part D plan −22.5% vs other channels +15.1%
- [ ] T024 [P] [US4] Test: P4-Q1 Great Lakes −16.5% vs +1.1%, control set named
- [ ] T025 [P] [US4] Test: cash cells flagged small; a contaminated control is dropped

## Phase 7: User Story 5 - Lane seam (P3)

- [ ] T026 [US5] Cross-lane payload rules and contract-version test (FR-014)
- [ ] T027 [US5] With Alvin: validate a sample `forecast.InvestigationRequest` with `source: "briefing_agent"` against `feagent/schema.py` (no runtime wiring; S1)

## Phase 8: Polish

- [ ] T028 Decide the framework (A3) and write the registration adapter; tools unchanged (FR-015)
- [ ] T029 Decide S9 with the Forecast team; update data-model.md
- [ ] T030 [P] `quickstart.md`: call each tool and read its record

## Dependencies

Needs core-002 and core-003. brief-002 uses every tool. brief-004 and core-006 use the record schema and probe test.
