# Feature Specification: Tool Interface and Handoff Contracts

**Feature Branch**: `005-tool-contracts`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §5.4, §7.3, §10.2, §14; Evaluation Pack EV-9.1, EV-9.3; Personas (HR guardrail)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Typed tools bound to governed metrics (Priority: P1)

The investigation agents call a fixed set of tools. Each tool has a typed signature and is bound to semantic-layer metric IDs. Each call returns a typed result with an evidence record. A tool contains no language model.

**Why this priority**: Every number in the brief comes from a tool. Tools are the only way the agent touches data.

**Independent Test**: Call each tool with valid, invalid and unknown inputs. Check typed results, typed errors, and an evidence record on every success.

**Acceptance Scenarios**:

1. **Given** a valid call to `get_metric`, **When** the tool runs, **Then** the result is typed, comes from the pinned snapshot, and carries an evidence ID.
2. **Given** an unknown metric ID, **When** any tool is called, **Then** the tool returns a typed error that the caller must handle.
3. **Given** the same call twice on one snapshot, **When** both run, **Then** the results are identical.

---

### User Story 2 - Stages hand off through schemas (Priority: P1)

The competitive-intelligence stage passes one typed investigation request into stage 4. Stage 4 returns one typed investigation result. Requests and results that fail their schema stop the run with a clear error.

**Why this priority**: Free-form agent conversation hides errors and breaks traceability (constitution VI).

**Independent Test**: Validate a good request and result. Break each required field in turn. Check each break is rejected.

**Acceptance Scenarios**:

1. **Given** the candidates of a run, **When** the request is built, **Then** it holds every candidate ID, metric, cut, magnitude, baseline, history, evidence IDs and the health report. There is one request per run.
2. **Given** a result with a missing field, **When** it is validated, **Then** it is rejected and the run records the failure.
3. **Given** a closed story, **When** the result is built, **Then** it holds driver findings, contributions, confidence, uncertainty and evidence references.

---

### User Story 3 - Keep individuals and the answer key out of reach (Priority: P1)

Rep-level data is aggregated inside the tools before any agent sees it, to the minimum level the semantic layer sets. No tool can read the answer key, the generator internals or the pre-artifact data.

**Why this priority**: HR protection and eval integrity are hard rules (constitution IX, XI).

**Independent Test**: Try to read the answer key through every tool and through the data access layer. Try to query rep activity below the floor.

**Acceptance Scenarios**:

1. **Given** the tool allowlist, **When** any tool or storage path is probed for the answer key, **Then** access is refused and the attempt is logged.
2. **Given** a rep-activity query below the aggregation floor, **When** the tool runs, **Then** the result is suppressed or aggregated up. It never points to one person.
3. **Given** a seeded rep-vacancy case, **When** tools return promotion data, **Then** no field identifies an individual.

---

### User Story 4 - Contribution decomposition (Priority: P2)

A tool splits a national change into the contribution of each region, payer channel or specialty. Contributions sum to the total.

**Why this priority**: The manager needs to know where a change is concentrated (P2-Q4).

**Independent Test**: Decompose seeded events. Check contributions sum to the total and match the event's location.

**Acceptance Scenarios**:

1. **Given** a national change, **When** `decompose_change` runs, **Then** the contributions sum to the total within rounding.
2. **Given** a change concentrated in one region, **When** the tool runs, **Then** that region has the largest contribution.

### Edge Cases

- A tool call times out. The tool returns a typed error. The loop's caps handle it.
- A tool is called with parameters it has already used for the same story. The ledger refuses the repeat (spec 006). The tool does not change.
- A suppressed cut is requested. The tool returns the cut with its qualification, never raw numbers.
- A query would return a single territory with a single vacancy. The tool suppresses it.
- The Forecast agent calls the same tools. Only the shared semantic layer and tracing conventions are common.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide these tools: `get_metric`, `decompose_change`, `validate_feed`, `lookup_access_events`, `lookup_promo`, `lookup_inventory`, `compare_competitors`, `lookup_calendar`, `reconcile_numbers`. `lookup_inventory` is an addition to the Architecture §5.4 list (see specs/README.md decisions).
- **FR-002**: Every tool MUST have a typed input and a typed output, and MUST bind to semantic-layer metric IDs and dimensions.
- **FR-003**: Every tool MUST return an evidence record with: evidence ID, source tool, parameters, result, source reference, and span ID.
- **FR-004**: Every tool MUST be a plain function with no language model inside.
- **FR-005**: Tools MUST be deterministic on a pinned snapshot.
- **FR-006**: An unknown metric ID or dimension MUST return a typed error.
- **FR-007**: The system MUST define typed schemas for: `investigation_request`, `investigation_result`, `story`, `hypothesis`, `evidence_item`, `candidate_changes` (from spec 004) and `health_report` (from spec 003).
- **FR-008**: The request MUST contain every candidate of the run together, so grouping sees them all.
- **FR-009**: Objects that fail their schema MUST stop the stage and be logged with the field named.
- **FR-010**: Tools MUST aggregate or suppress rep-level activity to the semantic layer's floor before returning data. [NEEDS CLARIFICATION: minimum aggregation level (Evaluation Pack open item 5)]
- **FR-011**: No tool, storage path, retrieval index or prompt MAY reach the answer key, generator internals or pre-artifact data. A tool allowlist MUST enforce this, and attempts MUST be logged.
- **FR-012**: `decompose_change` MUST return contributions that sum to the total.
- **FR-013**: Tool results on suppressed or qualified cuts MUST carry the qualification.
- **FR-014**: The orchestration framework MUST be able to call the tools without changing them. [NEEDS CLARIFICATION: agent framework (A3): Google ADK, custom Python or Microsoft Agent Framework]

### Key Entities

- **Tool**: name, typed input, typed output, metric binding.
- **Evidence item**: one tool call's recorded result (FR-003).
- **Investigation request / result**: the typed handoff into and out of stage 4.
- **Story and hypothesis**: records defined here, filled by spec 006.
- **Tool allowlist**: the set of data paths and tools that agents may use.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tool unit tests and schema checks pass (Architecture §12).
- **SC-002**: 100% of tool calls on success produce an evidence record that links to a span (EV-6.1, EV-9.1).
- **SC-003**: Zero answer-key reads succeed across all probes (EV-9.3).
- **SC-004**: Zero outputs on seeded rep-vacancy cases identify one person (EV-9.1).
- **SC-005**: Contributions sum to the total in 100% of decomposition checks (EV-4.3).
- **SC-006**: 100% of malformed requests and results are rejected.

## Assumptions

- The data view from spec 003 is the only data the tools read.
- Tools return the minimum data the agents need, not raw tables.
- The framework choice affects only how tools are registered, not their behavior.
