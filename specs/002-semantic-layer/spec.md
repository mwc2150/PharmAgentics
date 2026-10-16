# Feature Specification: Semantic Layer

**Feature Branch**: `002-semantic-layer`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §2 (principle 2), §7.1, §10.2, §14; Evaluation Pack EV-9.2; Personas (terminology note)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One definition for every metric (Priority: P1)

A component asks the layer what a metric means and how to cut it. It gets one answer: the label, definition, source field, grain, refresh rule, materiality thresholds, and allowed and banned phrases. A metric or dimension the layer does not hold is rejected with an error.

**Why this priority**: Every tool, prompt and check depends on it. A second definition anywhere is a risk to numeric fidelity.

**Independent Test**: Ask for each Rx field in the data dictionary. Ask for a made-up metric ID. The first returns a full entry; the second returns an error.

**Acceptance Scenarios**:

1. **Given** every field in the Rx table, **When** the layer is checked, **Then** each field has an entry or is explicitly listed as a non-metric.
2. **Given** an unknown metric ID or dimension, **When** any tool asks for it, **Then** the layer raises an error that the caller must handle.
3. **Given** NRx and NBRx, **When** their entries are read, **Then** each says what it is not to be confused with.

---

### User Story 2 - Rules in one place (Priority: P1)

A data owner changes a materiality threshold, a loop cap, the restatement window or the holiday calendar rule in one file. Every consumer sees the change on the next run, and the run records which layer version it used.

**Why this priority**: Thresholds and caps drive detection precision and run cost. They must be tunable without touching code.

**Independent Test**: Change one threshold. Run detection. Check that the flagged set changes and the run record shows the new layer version.

**Acceptance Scenarios**:

1. **Given** a changed threshold, **When** the next run starts, **Then** the run records the new layer version.
2. **Given** an invalid layer file (missing field, wrong type, bad value), **When** it loads, **Then** loading fails with an error that names the file and field.

---

### User Story 3 - Governed wording and glossary (Priority: P2)

The narrative writer receives only the definitions of the metrics in play. The verifier checks wording against the allowed and banned phrases. Each brief gets a glossary built from the layer.

**Why this priority**: Terminology is a Governance eval item (EV-9.2) and a mentor directive.

**Independent Test**: Render a glossary for a brief that uses TRx and NBRx. Check each entry matches the layer text.

**Acceptance Scenarios**:

1. **Given** a set of metric IDs, **When** a glossary is requested, **Then** it holds exactly those definitions, taken from the layer.
2. **Given** the banned-term list, **When** it is read, **Then** it holds "statistical surveillance", and "new patients" is allowed only for NBRx.

---

### User Story 4 - Hypothesis catalog and shared use (Priority: P2)

The investigation specialists draw hypotheses only from a fixed catalog of driver categories, artifact types and calendar effects. The Forecast team adds its own metrics to the same layer.

**Why this priority**: A finite catalog is one of the guarantees that agentic loops end (constitution VII).

**Independent Test**: List the catalog. Check that every driver label used by the Evaluation Pack is in it.

**Acceptance Scenarios**:

1. **Given** the catalog, **When** a specialist asks for hypotheses for a story type, **Then** it gets only catalog entries.
2. **Given** a new Forecast metric, **When** it is added, **Then** existing briefing metrics and thresholds do not change.

### Edge Cases

- A metric exists but its source field is missing from the loaded week. The layer reports the gap, not a default.
- Two layer files define the same metric. Loading fails.
- A threshold is set to zero or below. Loading fails.
- A phrase is both allowed and banned. Loading fails.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The layer MUST hold, for each metric: ID, label, definition, not-to-be-confused-with, grain, source field, lineage, refresh rule, materiality thresholds (absolute, relative, statistical), allowed phrases, banned phrases, and owner.
- **FR-002**: The layer MUST cover TRx, NRx, NBRx, TRx in 30-day equivalents, market share and NBRx share. It MUST also hold business impact once defined (see spec 004). It MUST also hold the context metrics that investigation tools return, so no tool returns a field the layer does not govern: days-supply mix (90-day fill share), inventory (fill rate, backorder rate), promotion (aggregated rep calls, digital impressions, samples, speaker programs, aggregated rep vacancy count) and access (covered, formulary tier, prior authorization, step therapy, quantity limit, covered lives). Context metrics are not detection KPIs and carry no materiality thresholds.
- **FR-003**: The layer MUST hold the dimensions: week, geography (region to territory), payer channel, HCP specialty.
- **FR-004**: The layer MUST hold the business rules: materiality thresholds per metric, the market basket with effective dates, the holiday calendar, and plan-year resets.
- **FR-005**: The layer MUST hold data contracts: source table, expected lag, restatement window, and owner.
- **FR-006**: The layer MUST hold the hypothesis catalog: driver categories (access, promotion, competitor, inventory, rep vacancy, mix shift, days-supply shift), artifact types, calendar effects. Each entry MUST name the tool or tools, and the context metrics, that can test it. A contract test MUST fail for any entry that names no tool, or a tool the registry does not hold.
- **FR-007**: The layer MUST hold the loop caps: investigation rounds per run, stalls, tool calls per story, data-forensics calls per story, wall-clock time, token budget, and brief length.
- **FR-008**: The layer MUST hold the governed terms and banned terms, including "competitive intelligence" and the NRx versus NBRx rule.
- **FR-009**: The layer MUST reject unknown metric IDs and dimensions with an error.
- **FR-010**: The layer MUST be versioned. Each run MUST record the layer version it used.
- **FR-011**: The layer MUST validate on load and fail with the file and field named.
- **FR-012**: The layer MUST provide a glossary for any set of metric IDs.
- **FR-013**: The layer MUST NOT assume a fixed number of territories, regions, specialties or weeks.
- **FR-014**: The layer MUST hold the aggregation floor for rep-level activity. [NEEDS CLARIFICATION: minimum aggregation level (Evaluation Pack open item 5)]
- **FR-015**: The layer MUST hold values for every loop cap. [NEEDS CLARIFICATION: cap values (Evaluation Pack open item 17). Plan 002 proposes starting values to tune on dev seeds.]

### Key Entities

- **Metric entry**: one governed metric (FR-001).
- **Dimension entry**: one cut and its hierarchy.
- **Business rule**: threshold set, basket, calendar, plan-year rule.
- **Data contract**: source, lag, restatement window, owner.
- **Hypothesis catalog entry**: a driver, artifact type or calendar effect, with the tool evidence that can test it.
- **Cap set**: all loop limits.
- **Layer version**: a content hash plus a human version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of metric fields in the Rx table have an entry (Architecture §14 criterion).
- **SC-002**: 100% of unknown-ID requests return an error. None return a default.
- **SC-003**: A changed threshold takes effect on the next run with no other file edited.
- **SC-004**: 100% of runs record the layer version.
- **SC-005**: Zero banned terms appear in any glossary or project document.
- **SC-006**: Every driver category used in the Evaluation Pack and Forecast agent is in the catalog.
- **SC-007**: 100% of catalog entries name a tool that exists, and 100% of fields returned by a tool have a metric or context-metric entry.

## Assumptions

- Seeded from the course's Week 02 Claims Data Field Guide. Heavier tooling stays out unless a need appears.
- The layer is configuration, not code. Changes are reviewed like specs.
- The Forecast team adds metrics to the same files and owns its entries.
- Materiality threshold values in the Architecture example are illustrative until tuned on dev null weeks.
