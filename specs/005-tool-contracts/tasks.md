# Tasks: Tool Interface and Handoff Contracts

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: Not started. No code yet.

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/contracts/`, `src/pharmagentics/tools/`, `tests/contract/`
- [ ] T002 [P] Define schemas: candidate, request, result, story, hypothesis, evidence, health (FR-007)
- [ ] T003 [P] Define typed errors (`UnknownMetric`, `UnknownDimension`, `SuppressedCut`, `Timeout`, `AccessDenied`, `SchemaError`)
- [ ] T004 Export JSON Schemas to `specs/005-tool-contracts/contracts/`

## Phase 2: Foundational

- [ ] T005 Data-access layer with allowlist; refuses any path outside agent-visible data (`access.py`) (FR-011)
- [ ] T006 Tool wrapper: ID check, span, evidence record, error mapping (`registry.py`) (FR-002, FR-003)
- [ ] T007 Rep-level aggregation helper (`aggregation.py`) (FR-010)

## Phase 3: User Story 1 - Typed tools (P1) MVP

**Independent Test**: Each tool returns typed results with evidence, and typed errors for bad input.

- [ ] T008 [P] [US1] Contract test per tool: valid, invalid and unknown-ID inputs (SC-001)
- [ ] T009 [P] [US1] `get_metric`
- [ ] T010 [P] [US1] `validate_feed`
- [ ] T011 [P] [US1] `lookup_access_events`
- [ ] T012 [P] [US1] `lookup_promo`
- [ ] T012a [P] [US1] `lookup_inventory`, returning `inventory_fill_rate` and `distribution_backorder_rate` as governed context metrics
- [ ] T012b [US1] Contract test: every field any tool returns has a metric or context-metric entry; every catalog `tests` tool name is in the registry (feeds spec 002 T018a)
- [ ] T013 [P] [US1] `compare_competitors`
- [ ] T014 [P] [US1] `lookup_calendar`
- [ ] T015 [P] [US1] `reconcile_numbers`
- [ ] T016 [US1] Test: identical results on repeat calls (FR-005); no tool imports a model client (FR-004)
- [ ] T017 [US1] Test: every success records an evidence item with a span ID (SC-002)

## Phase 4: User Story 2 - Schema handoffs (P1)

- [ ] T018 [US2] Builder: one `investigation_request` per run from candidates, health report and history (FR-008)
- [ ] T019 [US2] Builder and validator for `investigation_result`
- [ ] T020 [P] [US2] Mutation tests: break each required field; each break is rejected (SC-006)
- [ ] T021 [US2] On schema failure, stop the stage and log the field (FR-009)

## Phase 5: User Story 3 - Individuals and answer key (P1)

- [ ] T022 [P] [US3] Probe test: every tool and the access layer try `eval_private/` paths; all return `AccessDenied` and log (SC-003)
- [ ] T023 [P] [US3] Test: seeded rep-vacancy cases return nothing that identifies one person (SC-004)
- [ ] T024 [US3] Resolve the aggregation floor with the mentor (FR-010) and record it in the semantic layer

## Phase 6: User Story 4 - Contribution decomposition (P2)

- [ ] T025 [US4] `decompose_change` with contributions that sum to the total
- [ ] T026 [P] [US4] Test: sums to total; largest contribution matches the seeded event's location (SC-005)

## Phase 7: Polish

- [ ] T027 Decide framework (A3) and write the registration adapter; tools stay unchanged (FR-014)
- [ ] T028 Confirm the `lookup_inventory` addition with the team and add it to Architecture §5.4 and the decision log
- [ ] T029 [P] Quickstart: call each tool from a script and read the evidence record

## Dependencies

Needs 002 and 003. 006 uses all tools. 008 and 010 use the evidence schema and the probe test.

## White-box tests owed (Architecture §12)

Tool unit tests and schema checks at 100% pass (T008, T020). Handoff completeness (T018 to T020). Answer-key isolation probe (T022).
