# Feature Specification: Data Generator and Injection Library

**Feature Branch**: `001-data-generator`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §8 and §14; Evaluation Pack §4, §5, §7; `data/agent_visible/README.md`; Data Research Brief

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rebuild the same brand world from a seed (Priority: P1)

A data owner gives the generator a seed and a world size. It produces the same linked commercial tables every time. The tables follow the shared data dictionary. The current Day 1 release (seed 7, 8 territories, 4 specialties, 104 weeks) is one setting of this world. The team will expand it.

**Why this priority**: Every other spec tests against this world. Without a reproducible world, no result can be compared across builds.

**Independent Test**: Run the generator twice with the same seed and settings. Compare the outputs byte for byte. Run it with a larger world size. Check that every table still matches its dictionary entry.

**Acceptance Scenarios**:

1. **Given** seed S and world settings W, **When** the generator runs twice, **Then** both runs produce identical tables.
2. **Given** a larger world setting, **When** the generator runs, **Then** all tables keep their documented columns and grain, and no spec-level count is wrong.
3. **Given** any generated world, **When** the integrity checks run, **Then** NBRx is never above NRx, NRx is never above TRx, no volume is negative, and market shares sum to one within tolerance.

---

### User Story 2 - Inject labeled events and artifacts (Priority: P1)

An evaluator asks for specific events in specific weeks. The generator injects them into the commercial data and logs each one to an answer key that is stored apart from the agent-visible data.

**Why this priority**: The evaluation measures whether the agent finds and explains what was planted. Without labels there is no ground truth.

**Independent Test**: Generate a world with one access restriction in one region. Check that the affected cut moves by the logged magnitude, and that the answer key holds one matching record.

**Acceptance Scenarios**:

1. **Given** an event request (type, cut, start week, magnitude, decay), **When** the generator runs, **Then** the affected cut moves as logged and the answer key holds one record with every schema field.
2. **Given** a data artifact request (restatement, panel coverage drop, duplicate load, missing or late week), **When** the generator runs, **Then** the feed shows the defect, the feed metadata records it, and the answer key labels it a data artifact.
3. **Given** a request with no events, **When** the generator runs, **Then** the world is a null world and the answer key has no event records.
4. **Given** two events in one region, or an event masked by an artifact, **When** the generator runs, **Then** the answer key marks the compound case.

---

### User Story 3 - Split dev and held-out worlds (Priority: P2)

An evaluator generates dev worlds that the builders see and held-out worlds whose parameters the builders do not see. About 40 dev cases and 15 held-out cases cover every case category.

**Why this priority**: The headline back-test needs a held-out seed. It cannot count if the builders can read its parameters.

**Independent Test**: Generate a held-out world with a sealed parameter file. Check that no agent-visible file or log contains its event parameters.

**Acceptance Scenarios**:

1. **Given** a held-out request, **When** the generator runs, **Then** its event parameters appear only in the answer-key store.
2. **Given** the case taxonomy, **When** the scenario requests for the case set are written, **Then** the requests cover every category in both the dev and the held-out split. The evaluation harness (spec 010) builds the cases from the answer key.

---

### User Story 4 - Calibrate the world to public sources (Priority: P3)

A data owner picks a drug class and fits the world's scale, regional mix, specialty mix, and PA and step-edit rates to public sources. The fit is documented, with its limits.

**Why this priority**: The Proposal lists data realism as a risk. The Day 1 data is schema-aligned only.

**Independent Test**: Compare the calibrated world's mix against the public extract. Report the gaps.

**Acceptance Scenarios**:

1. **Given** a chosen drug class and saved public extracts, **When** the world is calibrated, **Then** a calibration report lists each parameter, its source, the retrieval date and the fit gap.
2. **Given** a quantity that no public source can support (weekly NBRx, commercial payer behavior), **When** the report is written, **Then** it states that the value is assumed.

### Edge Cases

- A requested event falls on a holiday week. The answer key records both the event and the calendar effect.
- A requested event starts before the first week or ends after the last. The generator rejects it with a clear error.
- Two events request the same cut and week. The generator composes them and logs both, or rejects the request if they conflict.
- An artifact request would leave no usable rows for a cut. The generator warns.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The generator MUST produce identical output for identical seed and settings.
- **FR-002**: World size (weeks, territories, regions, plans, specialties, products, payer channels) MUST be settings. No component may assume a fixed size.
- **FR-003**: The generator MUST produce every table in the data dictionary at its documented grain.
- **FR-004**: The generator MUST enforce the metric invariants in User Story 1, and MUST write a validation report.
- **FR-005**: The injection library MUST support these business events: access restriction, competitor launch, inventory disruption, promotion change, rep vacancy, 30-to-90-day conversion, competitive pressure.
- **FR-006**: The injection library MUST support these data artifacts: restatement, panel coverage drop, duplicate load, missing week, late week.
- **FR-007**: The injection library MUST support calendar effects (Thanksgiving, Christmas, January plan-year reset), null weeks, compound weeks, multi-week events with decay, and stress cases (missing data, inconsistent sources, unsupported questions).
- **FR-008**: Each event MUST draw magnitude, onset lag and decay from ranges set by the seed, unless the request fixes them.
- **FR-009**: The generator MUST write one answer-key record per event with: event ID, event type, affected cut (metric, geography, payer channel, HCP specialty), start week, magnitude, duration or decay, and label (real event, data artifact, or calendar effect).
- **FR-010**: The answer key, the pre-artifact true data, and the counterfactual components MUST be written to a store separate from the agent-visible data. The generator MUST only write to that store. It MUST NOT read it back. Only the evaluation harness reads it (constitution XI).
- **FR-011**: The generator MUST support dev and held-out splits, and held-out parameters MUST stay sealed.
- **FR-012**: The generator MUST accept scenario requests (seed, events, weeks, split) as input. The Given/When/Then case list (Evaluation Pack §4) is built from the answer key by the evaluation harness (spec 010 FR-021), not by the generator.
- **FR-013**: The generator MUST NOT use real patient, prescriber or proprietary data. All names, IDs and plans are fictional.
- **FR-014**: The calibration report MUST state, for each parameter, whether it is fitted or assumed.
- **FR-015**: The generator MUST stay compatible with the Forecast-Explanation Agent's use of the same world, including forecast-versus-actual data with injected drivers. [NEEDS CLARIFICATION: answer-key format and driver labels, agreed with Alvin and Sienna (Evaluation Pack open items 8 and 9)]
- **FR-016**: The calibration step MUST name the therapeutic class it mimics. [NEEDS CLARIFICATION: therapeutic class and competitor basket (Architecture A12)]
- **FR-017**: Held-out seeds MUST be generated by someone other than the builders of the agent under test. [NEEDS CLARIFICATION: who generates them, and whether the two teams swap seeds (Evaluation Pack open item 11)]

### Key Entities

- **World settings**: seed, size, calendar span, event requests.
- **Commercial tables**: the 14 tables in the data dictionary.
- **Event**: one injected real event, artifact or calendar effect.
- **Answer-key record**: the ground truth for one event (FR-009).
- **Scenario request**: a seed, a set of events, weeks and a split. The harness turns it into a case with expected outcomes.
- **Calibration report**: parameters, sources, fit gaps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of regenerated worlds match their first generation exactly.
- **SC-002**: 100% of injected events appear in the answer key with every field filled, and 100% of events show up in the affected cut at the logged magnitude, within a stated tolerance.
- **SC-003**: Every case category in Evaluation Pack §4 has at least one dev and one held-out scenario request. The set holds about 40 dev and 15 held-out requests.
- **SC-004**: A scan of all agent-visible files and logs finds zero answer-key fields or held-out parameters.
- **SC-005**: A world with 10 times the Day 1 territories builds with no spec or schema change.

## Assumptions

- The Day 1 release (v0) stays as an engineering baseline. v1 adds expansion and calibration.
- The world models one fictional brand and three fictional competitors in one therapy class.
- The data is a sample for now. The team expects to expand it, so specs never depend on its size.
- Weekly NBRx and commercial payer behavior cannot be fitted to public data. They remain assumptions.
- The generator code is written by an AI assistant, and code, not LLM output, carries reproducibility.
