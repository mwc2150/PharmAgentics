# Feature Specification: Competitive Intelligence (Stage 3a)

**Spec ID**: `brief-001-competitive-intelligence` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `004-competitive-intelligence` (Oct 16)
**Input**: System Architecture §4 (3a); Briefing Architecture §5.3; Evaluation Pack EV-3.1 to EV-3.4; Personas P1-Q3, P1-Q5, P3-Q1, P3-Q2; User stories P1-Q1, P1-Q3, P1-Q5, P2-Q1, P3-Q1, P3-Q2

"Competitive intelligence" is the mentor's name for this stage. "Statistical surveillance" and "surveillance" are not used. The Forecast lane's parallel stage is the variance screen (3b), owned by Alvin and Sienna.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Governed KPIs for the week (Priority: P1)

For the validated week, the stage computes the governed KPIs (TRx, NRx, NBRx, TRx in 30-day equivalents, market share, NBRx share) for every reportable cut, and compares each with last week, the four-week average and the same week last year. National and regional totals carry their territory coverage.

**Why this priority**: The KPI table is in every brief, routine weeks included (EV-1.1). Detection builds on it.

**Independent Test**: Compute KPIs for a dev week and check them against an independent calculation on the pinned snapshot.

**Acceptance Scenarios**:

1. **Given** a validated week, **When** the stage runs, **Then** each KPI comes from the governed view on the pinned snapshot, for every reportable cut, with each comparison present.
2. **Given** week 2026-07-06 with Great Lakes withheld, **When** the stage runs, **Then** national BXA TRx is 3,665 and carries "7 of 8 territories". It is never compared with full-coverage weeks as if complete. (User story P1-Q1.)
3. **Given** week 2026-04-06 as of today, with Mid-Atlantic withheld, **When** national is compared with the week before, **Then** the stage computes the like-for-like change on the 7 territories reporting both weeks (4,005 to 3,860, −3.6%), not the raw −18.4% (4,729 to 3,860). (User story P2-Q1.)
4. **Given** a move from 30-day to 90-day fills, **When** TRx is normalized to 30-day equivalents, **Then** the conversion alone does not read as a TRx drop.

---

### User Story 2 - Flag material changes and leave noise out (Priority: P1)

The stage removes seasonality, scores changes robustly, and flags a change only if it clears the semantic layer's absolute, relative and statistical thresholds. Normal territory swings do not reach the brief.

**Why this priority**: A brief is judged on what it misses and on what it falsely alarms (P1-Q3, P1-Q5).

**Independent Test**: Run on the anchor weeks and dev null weeks. Count recall and false flags.

**Acceptance Scenarios**:

1. **Given** week 2025-04-21, with national BXA 0.2% below its 4-week average and territories swinging from −10.8% to +24.8%, **When** the stage runs, **Then** no candidate is raised: these swings are inside the normal range (outside holidays, 1 week in 10 moves more than 15% to 22% in every territory). (User story P1-Q3.)
2. **Given** week 2026-06-08 (national BXA −11.7% against its 4-week average), **When** the stage runs, **Then** it raises candidates for the Pacific drop and for Metacora's share gain, and records what else it tested and dropped. (User story P1-Q5.)
3. **Given** a change that clears the statistical threshold but not the absolute floor, **When** the stage runs, **Then** it is not flagged.
4. **Given** a sustained gap in one territory against the others (for example South Central, September 2026), **When** the peer-relative comparison runs, **Then** the gap is a candidate even if no single week-over-week move clears the thresholds. (User story P2-Q3; proposed.)

---

### User Story 3 - Recognize calendar effects (Priority: P1)

Holiday weeks and plan-year resets are recognized. Expected seasonal moves are tagged as calendar effects, not reported as business events.

**Why this priority**: Seasonal dips reported as crises cause alarm fatigue (P3-Q2).

**Independent Test**: Run on the December 2025 weeks and on Thanksgiving weeks.

**Acceptance Scenarios**:

1. **Given** weeks 2025-12-22 and 2025-12-29 (national BXA 4,309 and 4,188; 16.1% and 19.0% below the 4-week average; 4 business days; the second is the plan-year reset), **When** the stage runs, **Then** both carry a calendar tag citing the same weeks a year earlier (−18.9%, −18.2%), and neither is ranked as a business event. (User story P3-Q2.)
2. **Given** a holiday week with a drop far larger than the seasonal pattern, **When** the stage runs, **Then** the excess is still flagged.

---

### User Story 4 - Rank by impact and hand off (Priority: P1)

Flagged changes are ranked by business impact and capped at about 15. The stage writes candidate changes and builds one `briefing.investigation_request` with every candidate. With no candidates, the run enters ROUTINE.

**Why this priority**: The brand director needs the few changes that matter, ranked (P3-Q1).

**Independent Test**: Run week 2026-04-27. Check the competitor share story leads.

**Acceptance Scenarios**:

1. **Given** week 2026-04-27, eight weeks after Metacora's launch (Metacora 9.3% of the basket; BXA 33.2%, down 2.6 points from 35.8% on 2026-02-23), **When** candidates are ranked, **Then** the share change is first, ahead of territory moves. (User story P3-Q1.)
2. **Given** no flagged change, **When** the stage finishes, **Then** the run is ROUTINE and the candidate list is empty.
3. **Given** more flags than the cap, **When** the list is cut, **Then** the detection summary states how many were dropped.

### Edge Cases

- A competitor launches mid-window: the market basket's effective dates change the share denominator from that week.
- A cut lacks 52 weeks of history: same-week-last-year is marked unavailable, not zero.
- Two events in one territory: both are candidates; grouping is brief-002's job.
- Thousands of leaf cuts are tested a week (territory × channel × plan × specialty × product): chance flags must be controlled. [NEEDS CLARIFICATION: multiple-testing control, such as hierarchical drill-down or false-discovery-rate control (Briefing A5)]
- A plan-level change hides inside a rising national trend (Mid-Atlantic Part D plan, Aug–Oct 2025, while national rose 9.0%): the hierarchy must reach plan level under its parent cut, or the change is missed (user story P2-Q4).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The stage MUST compute TRx, NRx, NBRx, TRx in 30-day equivalents, market share and NBRx share for each reportable cut, reading only the governed view on the pinned snapshot.
- **FR-002**: The stage MUST normalize TRx to 30-day equivalents before detection.
- **FR-003**: The stage MUST compare each metric and cut with the prior week, the four-week average and the same week last year.
- **FR-004**: The stage MUST also compare each territory with the other territories over the same weeks (peer-relative change) and with its own trailing 13-week baseline, so sustained local gaps are found. (Proposed; derived from the user stories' comparison method.)
- **FR-005**: The stage MUST remove seasonality by time-series decomposition and score robust z-scores on the residuals.
- **FR-006**: The stage MUST flag a change only if it clears the absolute, relative and statistical thresholds in the semantic layer.
- **FR-007**: The stage MUST tag holiday and plan-year-reset weeks, cite the same weeks a year earlier, and not rank expected seasonal moves as business events.
- **FR-008**: The stage MUST carry each total's territory coverage, and MUST compare weeks like-for-like on the territories reportable in both (core-003 FR-008).
- **FR-009**: The stage MUST rank flagged changes by business impact and cap the list at about 15. [NEEDS CLARIFICATION: business impact is proposed as the absolute change in TRx 30-day equivalents; it must match the answer key's definition (Briefing A4; confirm with Alvin and Sienna)]
- **FR-010**: The stage MUST write candidate changes with the fields in core-004 data-model.md, including thresholds cleared and their margins, calendar tag, coverage label and like-for-like flag.
- **FR-011**: The stage MUST build exactly one `briefing.investigation_request` per run, holding every candidate (A15). With no candidates it MUST set ROUTINE.
- **FR-012**: The stage MUST control false flags across the cuts tested, down to plan level. [NEEDS CLARIFICATION: method, tuned on dev null weeks (Briefing A5)]
- **FR-013**: The stage MUST be deterministic and MUST NOT call a language model.
- **FR-014**: The stage MUST write a detection summary: cuts tested, flagged, dropped by the cap, and the list of tested-and-dropped changes the brief shows (user story P1-Q5).
- **FR-015**: The stage MUST work on any world size.

### Key Entities

- **KPI table**: governed metrics by cut and comparison, with coverage labels.
- **Candidate change**: one flagged change (core-004 data-model.md).
- **Calendar tag**: holiday, plan-year reset, or none, with the prior-year comparison.
- **Detection summary**: counts and the tested-and-dropped list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of seeded material events appear among candidates on dev worlds (EV-3.1), including every visible `day1-v1` event on its anchor weeks.
- **SC-002**: No more than one false flag per null week (EV-3.2); zero candidates on 2025-04-21.
- **SC-003**: The December 2025 holiday weeks are tagged and not ranked (EV-3.4).
- **SC-004**: Candidate order agrees with answer-key business impact order (EV-3.3; target to set); on 2026-04-27 the share change ranks first.
- **SC-005**: KPI values match an independent calculation on the pinned snapshot in 100% of checked cells.
- **SC-006**: Two runs on the same snapshot give identical candidates.
- **SC-007**: 100% of totals built on fewer than all territories carry their coverage label; 100% of cross-week comparisons with a withheld territory are like-for-like.

## Assumptions

- The governed view (core-003) is the only source; withheld cuts never arrive.
- Thresholds start from the semantic layer's illustrative values and are tuned on dev null weeks only.
- Detection finds changes. It does not explain them; brief-002 does.
