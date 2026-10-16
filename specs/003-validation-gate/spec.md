# Feature Specification: Load, Pin and Validation Gate

**Feature Branch**: `003-validation-gate`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §5.1, §5.2; Evaluation Pack EV-1.2, EV-2.1, EV-2.3, EV-2.4; Personas P1-Q2, P2-Q1

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pin one data version per run (Priority: P1)

The Monday run loads the latest closed week and its history, and stores the pull as an immutable snapshot. The run pins that snapshot. Every later number reconciles to it, even if a newer pull arrives.

**Why this priority**: Numeric fidelity and the audit trail both depend on it (P1-Q1, P2-Q5).

**Independent Test**: Run a week, then load a restated pull for the same week. Check that the first run's snapshot is unchanged and the second run has its own.

**Acceptance Scenarios**:

1. **Given** a closed week, **When** the load step runs, **Then** it stores an immutable snapshot, records its ID and the layer, model, prompt and code versions, and moves the run to LOADED.
2. **Given** a later pull that changes past values, **When** an older run is re-opened, **Then** it still reads its own pinned snapshot.
3. **Given** the history window moves forward one week, **When** the next run loads, **Then** weeks inside the restatement window are flagged as restated, not overwritten.

---

### User Story 2 - Catch data artifacts before interpretation (Priority: P1)

Before any metric is read, the gate checks every feed and every cut: structure, missing sources, row counts, duplicate keys, panel coverage, freshness and lag, and the diff against the previous pull. It writes a health report with pass, warn or fail per cut.

**Why this priority**: A data artifact read as a business change is the most damaging error (P2-Q1).

**Independent Test**: Run on dev seeds with each seeded artifact type. Check that each one is flagged in the right cut.

**Acceptance Scenarios**:

1. **Given** a week with a duplicate load, **When** the gate runs, **Then** the affected cut shows warn or fail and names the duplicate-key check.
2. **Given** a week with a panel coverage drop, **When** the gate runs, **Then** the cut is flagged and the coverage figure is in the report.
3. **Given** a week with a missing or late source, **When** the gate runs, **Then** the report shows the freshness or lag breach.
4. **Given** a clean week, **When** the gate runs, **Then** every cut passes and no false flag appears.

---

### User Story 3 - Suppress or qualify unreliable cuts (Priority: P1)

When a cut warns or fails, downstream stages either suppress its numbers or carry a visible qualification. The brief leads with the unreliable cuts and reports the rest.

**Why this priority**: The analyst needs to know which cuts they cannot report (P1-Q2).

**Independent Test**: Fail one cut. Check that detection ignores it and the report marks it suppressed.

**Acceptance Scenarios**:

1. **Given** a failed cut, **When** later stages read the data, **Then** the cut's numbers are suppressed or carry a qualification flag. None appear unqualified.
2. **Given** every cut failed, **When** the gate finishes, **Then** the run ends as a data-health notice only (proposed answer to A7).

---

### User Story 4 - Disclose restatements (Priority: P2)

When a number reported last week has changed, the gate records the old and new value so the narrative can say so.

**Why this priority**: A brand director cannot repeat a number that later changes silently (P3-Q4, P3-Q6).

**Independent Test**: Seed a restatement. Check that the report lists the cut, week, old value and new value.

**Acceptance Scenarios**:

1. **Given** a restated week inside the window, **When** the gate runs, **Then** the report lists old and new values for each affected metric and cut.
2. **Given** a restated week outside the window, **When** the gate runs, **Then** it is flagged as out of window and not silently applied. [NEEDS CLARIFICATION: confirm treatment of restatements older than the window; proposal: flag and exclude from comparisons]

### Edge Cases

- The week arrives with a changed schema version. The gate fails the feed.
- A duplicate key has two different values. The gate flags the conflict and does not pick one.
- Row count is low because a territory legitimately has fewer rows. The check compares against the trailing average, not a fixed number.
- The previous pull is missing. The restatement diff is skipped and the report says so.
- A holiday week has low volume. This is a calendar matter for spec 004, not a feed failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The run MUST assign a run ID and record week, state, timestamps, and data, layer, model, prompt and code versions.
- **FR-002**: Each weekly pull MUST be stored as an immutable snapshot. A run MUST pin exactly one.
- **FR-003**: The load step MUST bring in the history window the semantic layer defines and flag weeks restated inside the restatement window.
- **FR-004**: The gate MUST run these checks per feed and per cut: schema and types, missing sources, row counts against the trailing average, duplicate keys, panel coverage, freshness and reporting lag, restatement diff.
- **FR-005**: The gate MUST write a health report with pass, warn or fail for each cut and the evidence for each result.
- **FR-006**: On warn or fail, later stages MUST suppress or visibly qualify the cut's numbers.
- **FR-007**: The gate MUST NOT silently fill, backfill or drop bad data.
- **FR-008**: The gate MUST record old and new values for every restated metric and cut inside the window.
- **FR-009**: The gate MUST name the check and the threshold behind every warn or fail.
- **FR-010**: Thresholds for the checks MUST come from the semantic layer.
- **FR-011**: The gate MUST work on any world size.
- **FR-012**: If every cut fails, the gate MUST end the run as a data-health notice only. [NEEDS CLARIFICATION: confirm A7 proposal with Michael and Meghna]

### Key Entities

- **Run registry row**: run ID, week, state, timestamps, version pins, snapshot ID.
- **Snapshot**: an immutable weekly pull plus history.
- **Health report**: per cut, per check, result and evidence.
- **Restatement record**: cut, week, metric, old value, new value, recorded time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of seeded artifacts are flagged in the health report on dev seeds (EV-2.1).
- **SC-002**: 100% of failed cuts are suppressed or visibly qualified (EV-2.3).
- **SC-003**: 100% of restated weeks inside the window are flagged. None are overwritten or double-counted (EV-2.4).
- **SC-004**: 100% of seeded restatements show old and new values in the report (EV-1.2 input).
- **SC-005**: Zero false flags on clean dev weeks, within a rate set by the semantic layer.
- **SC-006**: A re-opened run reads exactly the numbers it read at sign-off.

## Assumptions

- The gate runs before any metric is interpreted. It does not judge business meaning.
- Feed metadata is available for each source and week.
- Calendar effects belong to competitive intelligence (spec 004), not this gate.
- The run's state machine belongs to spec 009. This spec supplies the LOADED, VALIDATED and VALIDATION_* transitions' inputs.
