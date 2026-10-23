# Feature Specification: Data World — Foundation, Generator and Injection Library

**Spec ID**: `core-001-data-world` (shared; owners: both teams, data owner Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. The foundation (User Story 1) is built and merged (PR #1). The rest is not started.
**Replaces**: `001-data-generator` (Oct 16)
**Input**: System Architecture §3.1, §3.6, §3.7, S3, S10; Briefing Architecture §8 (superseded for the world by System §3.1); Evaluation Pack §4, §5, §7; Forecast Personas & Eval Design §3.4; `data/agent_visible/README.md`; `docs/DUCKDB_FIRST_RUN.md`; User stories P1-Q1, P1-Q2, P2-Q1, CA-Q1, CA-Q6

## Context

Both agents share one data world (System Architecture D7). Meghna's data foundation is that world: the `day1-v1` release (seed 7) of 14 agent-visible tables, loaded into one DuckDB file with `raw`, `metadata` and `reporting` schemas. The generator that made the release and its hidden answer key are kept **outside this repository**. This spec covers the release as it is loaded today, and the generator and injection library that will produce further dev and held-out worlds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load the shared world the same way every time (Priority: P1) — built

A team member loads the 14 release tables into DuckDB. The load keeps duplicates and NULLs, records each file's fingerprint, and never half-replaces a good database. The checker confirms the known artifacts are present as intended test cases.

**Why this priority**: Every other spec reads this database. Both lanes must see the same numbers.

**Independent Test**: Run the loader and checker on a fresh checkout. Compare the counts with the release's validation report.

**Acceptance Scenarios**:

1. **Given** the `day1-v1` release, **When** the loader runs, **Then** 14 typed tables land in `raw`, an import run and 14 fingerprints land in `metadata`, and the reporting views build.
2. **Given** the loaded release, **When** the checker runs, **Then** it reports 106,467 observed Rx rows against 106,496 expected cells, 44 missing keys, and 15 duplicate keys with 15 excess rows. `106,496 − 44 + 15 = 106,467`.
3. **Given** the loaded release, **When** the checker runs, **Then** it flags `2026-05-04 / NEW_ENGLAND` (missing keys, incomplete and late feed, low coverage), `2026-07-06 / GREAT_LAKES` (duplicate keys) and `2026-04-06 / MID_ATLANTIC` (restatement review). (User stories P1-Q1, P1-Q2, P2-Q1, CA-Q1.)
4. **Given** a missing file, a changed header, a type error or a failing view, **When** the loader runs, **Then** the import fails and the previous database is left intact.
5. **Given** the same files, **When** the loader runs twice, **Then** the raw tables are identical and the audit history gains one run.

---

### User Story 2 - Rebuild the same world from a seed (Priority: P1)

The data owner runs the generator, which lives outside the repository, with a seed and world settings. It produces the same agent-visible release every time and a validation report that names the release and seed. The current `day1-v1` release (seed 7) is one setting of this world.

**Why this priority**: Results compare across builds only if the world is reproducible. New dev and held-out worlds depend on it.

**Independent Test**: Run the generator twice with seed 7 and the `day1-v1` settings. Diff the agent-visible output against the files in `data/agent_visible/`.

**Acceptance Scenarios**:

1. **Given** seed S and settings W, **When** the generator runs twice, **Then** both agent-visible releases are byte-identical.
2. **Given** a larger world setting, **When** the generator runs, **Then** every table keeps its documented columns and grain, and the loader, checker and every spec still work with no change.
3. **Given** any generated world, **When** its integrity checks run, **Then** NBRx ≤ NRx ≤ TRx, no volume is negative, shares sum to one within tolerance, and territory forecasts and actuals sum exactly to NATIONAL. (User story CA-Q6.)

---

### User Story 3 - Inject labeled events and artifacts (Priority: P1)

An evaluator asks for specific events in specific weeks. The generator injects them and writes one answer-key record each, to a store outside the repository. The record format serves both lanes: Briefing scores events; Forecast scores cases with identifiability.

**Why this priority**: Both evaluations measure whether the agent finds and explains what was planted. Without labels there is no ground truth.

**Independent Test**: Generate a world with one access restriction on one plan. Check the affected cut moves by the logged magnitude and the answer key holds one matching record, outside the repo.

**Acceptance Scenarios**:

1. **Given** an event request (type, cut, start week, magnitude, decay), **When** the generator runs, **Then** the affected cut moves as logged, and the answer key holds one record with every field.
2. **Given** a data-artifact request (restatement, coverage drop, duplicate load, missing or late week), **When** the generator runs, **Then** the feed shows the defect, `feed_metadata` or `restatement_log` records it, and the answer key labels it a data artifact.
3. **Given** a request with no events, **When** the generator runs, **Then** the world is a null world and the answer key holds no event records.
4. **Given** two events in one territory, or an event masked by an artifact, **When** the generator runs, **Then** the answer key marks the compound case and, for the Forecast lane, whether separate, combined or no contributions are identifiable.
5. **Given** an event the locked forecast already anticipated, **When** the generator runs, **Then** the answer key records the incremental forecast-miss effect separately from the event's total effect (Forecast TC-10; Forecast lane, Alvin and Sienna confirm).

---

### User Story 4 - Split dev and held-out worlds (Priority: P2)

An evaluator generates dev worlds the builders can see and held-out worlds whose parameters they cannot. About 40 dev and 15 held-out Briefing cases cover every case category.

**Why this priority**: The headline 10-week back-test needs a held-out seed. It does not count if the builders can read its parameters.

**Independent Test**: Generate a held-out world. Scan the repository, the agent-visible output and the logs for its parameters.

**Acceptance Scenarios**:

1. **Given** a held-out request, **When** the generator runs, **Then** its event parameters exist only in the sealed store outside the repository.
2. **Given** the Briefing case taxonomy and the Forecast scenario catalog, **When** the scenario requests are written, **Then** every category has at least one dev and one held-out request. core-006 builds the cases.

---

### User Story 5 - Calibrate the world to public sources (Priority: P3)

The data owner fits scale, regional mix, specialty mix, and PA and step-edit rates to public sources and documents the fit and its limits.

**Why this priority**: The Proposal lists data realism as a risk. The release is schema-aligned only.

**Independent Test**: Compare the calibrated world's mix against saved public extracts and report the gaps.

**Acceptance Scenarios**:

1. **Given** a chosen class and saved public extracts, **When** the world is calibrated, **Then** a report lists each parameter, its source, the retrieval date and the fit gap.
2. **Given** a quantity no public source supports (weekly NBRx, commercial payer behavior), **When** the report is written, **Then** it says the value is assumed.

### Edge Cases

- A requested event falls on a holiday week: the answer key records both the event and the calendar effect.
- A requested event starts before the first week or ends after the last: the generator rejects it with a clear error.
- Two events request the same cut and week: the generator composes and logs both, or rejects the request if they conflict.
- An artifact would leave a cut with no usable rows: the generator warns. The gate (core-003) must still withhold the cut, not read it as zero.
- A product has no volume before its launch: the release still holds a zero-volume cell, which is not missing (Metacora before 2026-03-02).
- A restatement lands long after the week (the release restates 2026-04-06 on 2026-07-13): the release keeps the revised value in `rx_weekly` and the prior value in `restatement_log`. core-003 rebuilds earlier snapshots from it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The loader MUST load exactly the 14 listed release files into typed `raw` tables, keeping duplicates and NULLs, and MUST NOT ingest any other file. *(built)*
- **FR-002**: Each import MUST record an import run and the SHA-256 fingerprint, row count and size of every file in `metadata`. *(built)*
- **FR-003**: An import MUST be all-or-nothing. Any failure MUST leave the previous successful load intact. *(built)*
- **FR-004**: The checker MUST verify row counts against the manifest, required fields, empty tables and duplicate natural keys for every table, and MUST compute missing Rx cells from the expected key universe (`calendar × dim_plan × dim_specialty × dim_product`), not from the feed's advertised count. *(built)*
- **FR-005**: The generator MUST produce identical agent-visible output for identical seed and settings, and MUST write a validation report naming the release and seed.
- **FR-006**: World size (weeks, territories, regions, plans, specialties, products, payer channels) MUST be settings. No spec, query or test may assume the `day1-v1` sizes.
- **FR-007**: The generator MUST enforce the metric invariants in User Story 2, including that territory forecasts and actuals sum exactly to NATIONAL.
- **FR-008**: The locked forecast MUST stay blind to unplanned launch, payer, promotion and inventory shocks, and MUST mark `actual_is_provisional` on weeks whose feed fails the gate.
- **FR-009**: The injection library MUST support these business events: access restriction and restoration, competitor launch, inventory or supply disruption, promotion change and lapse, rep vacancy, 30-to-90-day conversion, competitive pressure.
- **FR-010**: The injection library MUST support these data artifacts: restatement (with a configurable delay), panel coverage drop, duplicate load, missing week or cut, late delivery, and forecast or actual version mismatch.
- **FR-011**: The injection library MUST support calendar effects (Thanksgiving, Christmas, January plan-year reset), null weeks, compound weeks, multi-week events with decay, events already anticipated by the forecast, and stress cases (missing data, inconsistent sources).
- **FR-012**: Each event MUST draw magnitude, onset lag and decay from seeded ranges unless the request fixes them.
- **FR-013**: The generator, the answer key, the pre-artifact true data, the counterfactual components and held-out parameters MUST live outside this repository. No such file MAY be committed. The generator MUST only write that store and never read it back. Only the eval harness reads it (shared Principle III).
- **FR-014**: The answer key MUST serve both lanes: one record per injected event (Briefing Evaluation Pack §5) and one record per case with identifiability fields (Forecast §3.4). [NEEDS CLARIFICATION: one shared format or two linked formats (System S10, Evaluation Pack open item 8)]
- **FR-015**: The generator MUST support dev and held-out splits. Held-out parameters MUST stay sealed. [NEEDS CLARIFICATION: who generates held-out seeds, and whether the teams swap them (Evaluation Pack open item 11)]
- **FR-016**: The generator MUST accept scenario requests (seed, events, weeks, split). The eval harness (core-006), not the generator, builds cases from them.
- **FR-017**: The world MUST use no real patient, prescriber, plan or proprietary data. Names, IDs and plans are fictional.
- **FR-018**: The calibration report MUST state, for each parameter, whether it is fitted or assumed, and MUST name the class it mimics. [NEEDS CLARIFICATION: `day1-v1` is a fictional cardiometabolic basket; confirm calibration follows it (Briefing A12)]
- **FR-019**: The Forecast lane's reference case (LUMINA Week 18) MUST be reproduced inside this world, so both lanes test on one world (System S3; Forecast lane, Alvin and Sienna confirm).

### Key Entities

- **Release**: a versioned set of the 14 agent-visible tables plus README, dictionary and validation report (`day1-v1` today).
- **Import run and manifest**: one load and its file fingerprints.
- **World settings and scenario request**: seed, size, calendar span, events, split.
- **Event**: one injected business event, artifact or calendar effect.
- **Answer-key record**: the ground truth for one event or case. Lives outside the repository.
- **Calibration report**: parameters, sources, fit gaps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh checkout loads and passes the checker with the counts in User Story 1 on Python 3.11 and 3.12. *(met in CI)*
- **SC-002**: 100% of regenerated worlds match their first generation byte for byte.
- **SC-003**: 100% of injected events appear in the answer key with every field filled and show in the affected cut at the logged magnitude, within a stated tolerance.
- **SC-004**: Every Briefing case category and every Forecast scenario class has at least one dev and one held-out request.
- **SC-005**: A scan of the repository, its history from this spec onward, the agent-visible release and all logs finds zero answer-key fields or held-out parameters.
- **SC-006**: A world with ten times the `day1-v1` territories builds and loads with no spec or schema change.

## Assumptions

- `day1-v1` stays as the engineering baseline. New releases add worlds; they never edit `day1-v1` in place.
- The world models one fictional index brand (BXA Cardiovela) and three fictional competitors, one of which (BXE Metacora) launches mid-history.
- Weekly NBRx and commercial payer behavior cannot be fitted to public data. They remain assumptions.
- Code carries reproducibility. Model output does not.
- The release documents still say "surveillance" in one place; replacing it is S8, not this spec.
