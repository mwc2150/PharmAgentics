# Feature Specification: Tool Interface and Handoff Contracts

**Spec ID**: `core-004-tool-handoff-contracts` (shared; owners: both teams. Briefing owns its tool set and `briefing.*` objects; Forecast owns its tool set and `forecast.*` objects)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `005-tool-contracts` (Oct 16)
**Input**: System Architecture §3.3, §3.7, §4a, §4b, §5, §6, S1, S5, S9; Briefing Architecture §5.4, §7.3, §10.2; Evaluation Pack EV-4.3, EV-6.1, EV-9.1, EV-9.3; Forecast FE-19, FE-20, FE-30; User stories P1-Q4, P2-Q2, P2-Q4, P3-Q5, P4-Q1, P4-Q2, P4-Q6
**Design detail**: [data-model.md](data-model.md)

## Context

Every tool is plain deterministic code with no model inside, and every call returns a record that outputs cite (System §3.3). Stages hand off through typed objects. This spec owns the shared rules (tool record, registry, allowlist, typed errors, aggregation floor, contract versioning), the Briefing tool set and the `briefing.*` handoff objects. The Forecast tool set and the `forecast.InvestigationRequest` / `forecast.InvestigationReport` contracts belong to Alvin and Sienna; this spec only records the seam rules they share.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Typed tools bound to governed metrics (Priority: P1)

The investigation agents touch data only through typed tools bound to semantic-layer IDs. Each call returns a typed result and a tool record. An unknown ID returns a typed error the manager must handle.

**Why this priority**: Every number in an output comes from a tool. Tools are the only way an agent touches data.

**Independent Test**: Call each tool with valid, invalid and unknown inputs. Check typed results, typed errors, and a tool record on every success.

**Acceptance Scenarios**:

1. **Given** a valid `get_metric` call on a pinned snapshot, **When** it runs, **Then** the result is typed, read through the governed view, and carries a tool record with tool, parameters, result, snapshot and span ID.
2. **Given** a claim "BXA NBRx on plan SYN_MID_ATLANTIC_MEDICARE_PART_D_1 fell 37%", **When** its evidence is opened, **Then** it shows the `get_metric` record (15.0 a week over 2025-08-04 to 2025-10-27 against 23.8 over the 9 weeks before) and the `lookup_access_events` record (tier 2 to tier 3, prior authorization and step therapy, effective 2025-08-01). (User story P1-Q4.)
3. **Given** an unknown metric ID, **When** any tool is called, **Then** it returns `UnknownMetric`.
4. **Given** the same call twice on one snapshot, **When** both run, **Then** the results and records are identical except for record and span IDs.

---

### User Story 2 - Briefing stages hand off through schemas (Priority: P1)

Competitive intelligence passes one `briefing.investigation_request` into stage 4. Stage 4 returns one `briefing.investigation_result`. Objects that fail their schema stop the stage and name the field.

**Why this priority**: Free-form conversation hides errors and breaks traceability (shared Principle IV).

**Independent Test**: Validate a good request and result, then break each required field in turn.

**Acceptance Scenarios**:

1. **Given** the candidates of a run, **When** the request is built, **Then** it holds every candidate with metric, cut, magnitude, baseline and history, plus evidence IDs and the health report. There is one request per run (A15).
2. **Given** a result with a missing field, **When** it is validated, **Then** it is rejected and the run records the field.
3. **Given** a closed story, **When** the result is built, **Then** it holds the label, confidence, leading driver or none, every hypothesis with its verdict and evidence IDs, contributions, next step and function to involve.

---

### User Story 3 - Keep individuals and the answer key out of reach (Priority: P1)

Rep-level data is aggregated or suppressed inside the tools, to the floor the semantic layer sets, before any agent sees it. No tool, data path or prompt can reach the ground-truth store.

**Why this priority**: HR protection and eval integrity are hard rules (shared Principle III; Briefing B-VI).

**Independent Test**: Probe every tool and the data-access layer for the ground-truth store. Query rep activity below the floor.

**Acceptance Scenarios**:

1. **Given** the allowlist, **When** any tool or path is probed for the ground-truth store or its environment variable, **Then** access is refused and logged.
2. **Given** the Southeast coverage gap (2026-08-03 to 2026-08-31), **When** `lookup_promo` runs, **Then** it returns territory-level aggregated calls (about 19 a week against about 50) and impressions, and returns the vacancy count only if it meets the floor; otherwise it returns `BelowFloor`. (User stories P3-Q5, P4-Q6.)
3. **Given** any promotion result, **When** it is returned, **Then** no field names or implies an individual rep.

---

### User Story 4 - Locate and compare a change (Priority: P1)

Two tools say where a change sits and how it compares with peers. `decompose_change` splits a change into territory, channel, plan and specialty contributions that sum to the total. `compare_to_peers` compares an exposed territory with the other territories over the same weeks, dropping territories with their own active event.

**Why this priority**: Concentration (P2-Q4) and every driver verdict in the user stories rest on these two tools.

**Independent Test**: Decompose the Mid-Atlantic access weeks; compare Great Lakes with peers in February 2026.

**Acceptance Scenarios**:

1. **Given** weeks 2025-08-04 to 2025-10-27, **When** `decompose_change` runs on Mid-Atlantic BXA TRx, **Then** contributions sum to the territory change, and the Part D plan with 26% of covered lives shows −22.5% (about 41 TRx a week) while the territory's other channels rose 15.1%. (User story P2-Q4.)
2. **Given** Great Lakes 2026-02-02 to 2026-02-23 against January, **When** `compare_to_peers` runs, **Then** it reports Great Lakes −16.5% against +1.1% for the other territories, names the control set and states the method. (User story P4-Q1.)
3. **Given** a cut below the small-cell floor (cash, 36 to 49 TRx a week), **When** either tool returns it, **Then** the result carries a small-cell flag. (User story P4-Q2.)
4. **Given** a control territory with its own active event in the window, **When** `compare_to_peers` runs, **Then** it drops that territory from the control set and says why.

---

### User Story 5 - One seam between the lanes (Priority: P3)

In v1 neither agent calls the other (S1). The seam is defined so either team can wire a handoff later without a redesign.

**Why this priority**: Keeps both lanes independent now and joinable later.

**Independent Test**: Validate a sample `forecast.InvestigationRequest` with `source: "briefing_agent"` built from a Briefing candidate, without sending it.

**Acceptance Scenarios**:

1. **Given** any payload that crosses lanes, **When** it is built, **Then** it carries `run_id`, the pinned data version and evidence references, and no ground-truth field.
2. **Given** a renamed field in a cross-lane contract, **When** contract tests run, **Then** they fail unless the contract version is bumped.

### Edge Cases

- A tool call times out: it returns `Timeout`; the loop's caps handle it.
- A tool is called with parameters already used for the same story: the ledger refuses (brief-002); the tool does not change.
- A withheld cut is requested: the tool returns `SuppressedCut` with the gate's reasons, never raw numbers.
- A territory-level vacancy count of one could point to one person: the floor decides; below it the tool returns `BelowFloor`.
- Promotion activity did not change in a window: `lookup_promo` says so explicitly, so the promotion hypothesis can be ruled out (EV-4.5; user story P2-Q2: calls 50 against 53).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every tool in either lane MUST be a plain function with no language model inside, deterministic on a pinned snapshot, with a typed input and a typed output bound to semantic-layer IDs.
- **FR-002**: Every successful call MUST return a tool record holding: record ID, `run_id`, tool name, parameters, result, snapshot ID, source reference and span ID. Briefing stores it as an `evidence_item`; Forecast lists it in the report's evidence log. [NEEDS CLARIFICATION: one shared record shape, or a shared core with two lane views (System S9); plan proposes the shared core]
- **FR-003**: The Briefing tool set MUST be: `get_metric`, `decompose_change`, `compare_to_peers`, `validate_feed`, `lookup_access_events`, `lookup_promo`, `lookup_inventory`, `compare_competitors`, `lookup_calendar`, `reconcile_numbers`. `lookup_inventory` is Proposed under S5; `compare_to_peers` is new, required by the user stories' comparison method.
- **FR-004**: Tools MUST read data only through the governed view (core-003). A withheld cut MUST return `SuppressedCut`; a qualified cut's result MUST carry the qualification.
- **FR-005**: Errors MUST be typed: `UnknownMetric`, `UnknownDimension`, `SuppressedCut`, `BelowFloor`, `Timeout`, `AccessDenied`, `SchemaError`.
- **FR-006**: The system MUST define typed schemas for `candidate_change`, `health_report`, `briefing.investigation_request`, `story`, `hypothesis`, `evidence_item`, `briefing.investigation_result`, `brief_claim`, `analyst_review` and `run_registry`. Field lists are in [data-model.md](data-model.md).
- **FR-007**: The request MUST contain every candidate of the run, so grouping sees them all (Briefing decision 5).
- **FR-008**: An object that fails its schema MUST stop the stage and be logged with the field named.
- **FR-009**: Tools MUST aggregate or suppress rep-level activity to the semantic layer's floor before returning data (core-002 FR-012).
- **FR-010**: No tool, data path, retrieval index, prompt or log MAY reach the ground-truth store. The data-access layer MUST enforce an allowlist, and every refused attempt MUST be logged.
- **FR-011**: `decompose_change` MUST return contributions that sum to the total within rounding, at territory, channel, plan and specialty levels.
- **FR-012**: `compare_to_peers` MUST name its control set, drop territories with their own active event in the window, report the method, and lower confidence inputs when fewer than a semantic-layer minimum of controls remain.
- **FR-013**: Any tool result on a cut below the small-cell floor MUST carry a small-cell flag.
- **FR-014**: Any payload that crosses lanes MUST carry `run_id`, pinned data version and evidence references, and MUST NOT carry ground truth. Renaming or repurposing a cross-lane field MUST bump the contract version (System §5).
- **FR-015**: The agent framework MUST be able to call the tools without changing them. [NEEDS CLARIFICATION: agent framework (Briefing A3): Google ADK, custom Python or Microsoft Agent Framework]

### Key Entities

See [data-model.md](data-model.md) for fields. Summary: tool, tool record (`evidence_item` in Briefing), the Briefing handoff objects, the allowlist, and the cross-lane seam.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tool unit tests and schema checks pass (Briefing Architecture §12).
- **SC-002**: 100% of successful calls produce a tool record that links to a span (EV-6.1; FE-19 input).
- **SC-003**: Zero ground-truth reads succeed across all probes (EV-9.3, FE-30).
- **SC-004**: Zero tool outputs on seeded rep-vacancy cases identify one person (EV-9.1).
- **SC-005**: Contributions sum to the total in 100% of decomposition checks (EV-4.3).
- **SC-006**: 100% of malformed requests and results are rejected with the field named.
- **SC-007**: The four user-story checks in User Stories 1 and 4 return the stated figures on `day1-v1`.

## Assumptions

- Tools return the minimum data the agents need, never raw tables.
- The framework choice changes only how tools are registered, not what they do.
- The Forecast tools (`validate_and_quantify`, `get_region_deltas`, `list_candidate_events`, `compare_exposed_control`, `reconcile_attribution`) register in the same registry once they read the shared world (S3, S16). `compare_to_peers` and `compare_exposed_control` may become one shared function; the owners decide.
