# Feature Specification: Competitive Intelligence (Change Detection)

**Feature Branch**: `004-competitive-intelligence`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §5.3; Evaluation Pack EV-3.1 to EV-3.4; Personas P1-Q3, P1-Q5, P3-Q1, P3-Q2

"Competitive intelligence" is the mentor's name for this stage. "Statistical surveillance" is not used anywhere.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Governed KPIs for the week (Priority: P1)

For the validated week, the stage computes the governed KPIs (TRx, NRx, NBRx, TRx in 30-day equivalents, market share, NBRx share) for every reliable cut. It compares each against last week, the four-week average, and the same week last year.

**Why this priority**: The KPI table is in every brief, including routine weeks (EV-1.1). Detection builds on it.

**Independent Test**: Compute KPIs for a dev week. Check them against an independent calculation from the pinned snapshot.

**Acceptance Scenarios**:

1. **Given** a validated week, **When** the stage runs, **Then** each KPI is computed from the pinned snapshot for every reliable cut and each comparison is present.
2. **Given** a cut suppressed by the gate, **When** the stage runs, **Then** it computes nothing for that cut and records why.
3. **Given** a move from 30-day to 90-day fills, **When** TRx is normalized to 30-day equivalents, **Then** the conversion alone does not appear as a TRx drop.

---

### User Story 2 - Flag material changes and ignore noise (Priority: P1)

The stage removes seasonality, scores each change robustly, and flags a change only if it clears the semantic layer's absolute, relative and statistical thresholds. Small territories that swing wildly do not flood the list.

**Why this priority**: A brief judged on what it misses and on what it falsely alarms (P1-Q3, P1-Q5).

**Independent Test**: Run on dev weeks with seeded events and on null weeks. Count recall and false flags.

**Acceptance Scenarios**:

1. **Given** a week with a seeded material event, **When** the stage runs, **Then** the event's cut appears in the candidates.
2. **Given** a null week, **When** the stage runs, **Then** at most one candidate is flagged.
3. **Given** a change that clears the statistical threshold but not the absolute floor, **When** the stage runs, **Then** it is not flagged.

---

### User Story 3 - Recognize calendar effects (Priority: P1)

Holiday weeks and plan-year resets are recognized. Expected seasonal moves are tagged as calendar effects, not reported as business events.

**Why this priority**: Seasonal dips reported as crises cause alarm fatigue (P3-Q2).

**Independent Test**: Run on Thanksgiving, Christmas and January weeks. Check each is tagged and not flagged as a business event.

**Acceptance Scenarios**:

1. **Given** a holiday or plan-year-reset week, **When** a drop matches the expected pattern, **Then** the candidate carries a calendar tag and is not ranked as a business event.
2. **Given** a holiday week with a drop far larger than the seasonal pattern, **When** the stage runs, **Then** the excess is flagged.

---

### User Story 4 - Rank by impact and hand off (Priority: P1)

Flagged changes are ranked by business impact and capped at about 15 candidates. The stage writes candidate changes with the metric, cut, actual, baseline, absolute and relative change, anomaly score and impact. With no candidates, the run enters ROUTINE.

**Why this priority**: The brand director needs the few changes that matter, ranked (P3-Q1).

**Independent Test**: Seed events of different sizes. Check the ranking matches impact order.

**Acceptance Scenarios**:

1. **Given** flagged changes, **When** ranked, **Then** order follows business impact and the list holds at most the cap.
2. **Given** no flagged change, **When** the stage finishes, **Then** the run state is ROUTINE and the candidate list is empty.
3. **Given** more flags than the cap, **When** the list is cut, **Then** the report states how many were dropped.

### Edge Cases

- A new competitor launches mid-window. The market basket's effective dates change the share denominator.
- A cut has too little history for same-week-last-year. The comparison is marked unavailable, not zero.
- Compound weeks: two events in one region. Both cuts are candidates; grouping is spec 006's job.
- Thousands of leaf cuts are tested in one week. The chance of false flags must be controlled. [NEEDS CLARIFICATION: multiple-testing control, such as hierarchical drill-down or false-discovery-rate control (Architecture A5)]
- A fully reliable week with zero movement. The routine path still fills the KPI table.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The stage MUST compute TRx, NRx, NBRx, TRx in 30-day equivalents, market share and NBRx share for each reliable cut, using only the pinned snapshot.
- **FR-002**: The stage MUST normalize TRx to 30-day equivalents before detection.
- **FR-003**: The stage MUST compare each metric and cut against the prior week, the four-week average and the same week last year.
- **FR-004**: The stage MUST remove seasonality by time-series decomposition and score robust z-scores on the residuals.
- **FR-005**: The stage MUST flag a change only if it clears the absolute, relative and statistical thresholds in the semantic layer.
- **FR-006**: The stage MUST tag holiday and plan-year-reset weeks and not rank expected seasonal moves as business events.
- **FR-007**: The stage MUST rank flagged changes by business impact and cap the list at about 15.
- **FR-008**: The stage MUST write candidate changes with: run ID, candidate ID, metric ID, cut, actual, baseline, absolute change, relative change, anomaly score, business impact, calendar tag.
- **FR-009**: With no candidates, the stage MUST set the run to ROUTINE.
- **FR-010**: The stage MUST control false flags across the many cuts tested. [NEEDS CLARIFICATION: method and tuning on dev null weeks (A5)]
- **FR-011**: Business impact MUST be defined once in the semantic layer, and the same definition MUST be used by the answer key. [NEEDS CLARIFICATION: proposed definition is the absolute change in TRx 30-day equivalents (A4); confirm with Alvin and Sienna]
- **FR-012**: The stage MUST be deterministic and MUST NOT call a language model.
- **FR-013**: The stage MUST record, for each flag, which thresholds it cleared and by how much.
- **FR-014**: The stage MUST work on any world size.

### Key Entities

- **KPI table**: governed metrics by cut and comparison.
- **Candidate change**: one flagged change (FR-008).
- **Calendar tag**: holiday, plan-year reset, or none.
- **Detection summary**: counts tested, flagged, dropped by the cap.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of seeded material events appear among candidates on dev seeds (EV-3.1).
- **SC-002**: No more than one false flag per null week (EV-3.2).
- **SC-003**: Holiday and plan-year-reset weeks are recognized and not reported as business events (EV-3.4; target to set).
- **SC-004**: Candidate order agrees with answer-key business impact order (EV-3.3; target to set).
- **SC-005**: KPI values match an independent calculation from the pinned snapshot in 100% of checked cells.
- **SC-006**: Two runs on the same snapshot produce identical candidates.

## Assumptions

- The data view from spec 003 is the only source. Unreliable cuts arrive already suppressed or qualified.
- Thresholds start from the semantic layer's illustrative values and are tuned on dev null weeks.
- Detection finds changes. It does not explain them. Explanation is stage 4 (spec 006).
