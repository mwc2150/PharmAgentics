# Feature Specification: Load, Pin and Validation Gate (Stages 1 and 2)

**Spec ID**: `core-003-load-pin-gate` (shared; owners: both teams)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. The v0 gate (`reporting.v_feed_health`, `v_reportable_rx`, `v_weekly_rx_kpis`) is built. Snapshots, pinning and the health report are not started.
**Replaces**: `003-validation-gate` (Oct 16)
**Input**: System Architecture §3.1 (feed-health gate), §4 stages 1–2, S4; Briefing Architecture §5.1, §5.2, §6; Evaluation Pack EV-1.2, EV-2.1, EV-2.3, EV-2.4; Forecast FE-01 to FE-03, TC-06, TC-12; User stories P1-Q1, P1-Q2, P2-Q1, P2-Q5, P3-Q6, CA-Q1, CA-Q6

## Context

Stages 1 and 2 are shared outright (System §4). Every run of either lane pins what it reads, and no metric is interpreted before the gate has judged every week × territory cut. The v0 gate is built: a cut is reportable only with one COMPLETE metadata record, reconciled row counts, no missing or duplicate keys, coverage 0.98 to 1.0, lag within one day of target, and no restatement. A failed cut is withheld from the KPI views, never read as zero demand.

The release ships one pull, with restatements already applied: `rx_weekly` holds the revised value and `restatement_log` the prior one (Mid-Atlantic BXA TRx for 2026-04-06 is 742 in `rx_weekly`, 692 in the log). So "the numbers as they stood at sign-off" must be rebuilt as of a date.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pin one data version per run (Priority: P1)

A run records its `run_id`, its lane, its as-of date and the versions it reads: release and import fingerprint, semantic layer, model, prompt and code. Forecast runs also pin `forecast_issue_week` and the actual release. Every later number reconciles to that pin, even after newer data arrives.

**Why this priority**: Numeric fidelity and the audit trail both depend on it (P1-Q1, P2-Q5, CA-Q6).

**Independent Test**: Run a week as of 2026-04-13, then again as of today. Check each run reads its own values and the first is unchanged by the second.

**Acceptance Scenarios**:

1. **Given** a closed week, **When** stage 1 runs, **Then** the run record holds every version pin and the snapshot ID, and the run moves to LOADED.
2. **Given** the Monday run of 2026-04-13, after that week's 07:00 UTC load, for week 2026-04-06, **When** Mid-Atlantic BXA TRx is read, **Then** it is 692, because the restatement was recorded on 2026-07-13. (User story P2-Q5.)
3. **Given** the same week re-run as of today, **When** the value is read, **Then** it is 742 and carries the restatement record. The earlier run still reads 692.
4. **Given** a Forecast request for week 2026-08-24, **When** it is pinned, **Then** the run records forecast issue week 2026-07-27, horizon 4, and the actual release. A re-run of the same request returns identical figures. (User story CA-Q6.)

---

### User Story 2 - Catch data artifacts before interpretation (Priority: P1)

Before any metric is read, the gate checks every week × territory cut and writes a health report: result per cut, every check, the evidence and the threshold behind it.

**Why this priority**: A data artifact read as a business change is the most damaging error (P2-Q1, CA-Q1).

**Independent Test**: Run the gate on `day1-v1` and on dev worlds with each seeded artifact type. Check each is flagged in the right cut and clean cuts pass.

**Acceptance Scenarios**:

1. **Given** week 2026-07-06, **When** the gate runs, **Then** Great Lakes fails with `DUPLICATE_RX_KEYS`, `ROW_COUNT_MISMATCH` and `SOURCE_NOT_COMPLETE`: 143 rows against 128 expected, 15 duplicate keys. The evidence shows raw BXA TRx 670 against 624 with duplicates removed. (User stories P1-Q1, CA-Q1.)
2. **Given** week 2026-05-04, **When** the gate runs, **Then** New England fails with `MISSING_RX_KEYS`, `ROW_COUNT_MISMATCH`, `LOW_OR_INVALID_COVERAGE`, `LATE_OR_UNKNOWN_DELIVERY` and `SOURCE_NOT_COMPLETE`: 84 of 128 rows, coverage 0.656 against a 0.98 floor, 10.29 days after week end against a 7-day target. (User story P1-Q2.)
3. **Given** week 2026-04-06 as of today, **When** the gate runs, **Then** Mid-Atlantic fails with `RESTATEMENT_REVIEW`, and the health report lists all 32 restated BXA cells. (User story P2-Q1.)
4. **Given** a clean week, **When** the gate runs, **Then** every cut passes.

---

### User Story 3 - Withhold or qualify unreliable cuts (Priority: P1)

A failed cut is withheld from the governed view; a warned cut passes with a visible qualification. The health report also says how many territories each national total covers, so later stages can label it.

**Why this priority**: The analyst must know which cuts cannot be reported (P1-Q2), and national totals must not look complete when they are not (P1-Q1, P3-Q6).

**Independent Test**: Fail one cut. Check detection never sees it and the report states the coverage of national totals.

**Acceptance Scenarios**:

1. **Given** a failed cut, **When** later stages read the governed view, **Then** the cut is absent and the report marks it withheld. It is never read as zero.
2. **Given** week 2026-07-06, **When** the report is read, **Then** national BXA TRx from reportable cuts (3,665) is marked "7 of 8 territories". (User story P1-Q1.)
3. **Given** two weeks being compared where a territory is withheld in one of them, **When** the report is read, **Then** it names the territories reportable in both weeks, so a like-for-like change can be computed (user story P2-Q1: 7 territories, 4,005 → 3,860).
4. **Given** every cut failed, **When** the gate finishes, **Then** the run ends as a data-health notice only (proposed answer to A7).

---

### User Story 4 - Disclose restatements (Priority: P2)

When a number reported in an earlier run has changed, the gate records the old value, the new value, the revision date and the reason, so the narrative can say so.

**Why this priority**: A brand director cannot repeat a number that changes silently (P3-Q4, P3-Q6).

**Independent Test**: Run the brief for 2026-07-13. Check the report lists the 2026-04-06 Mid-Atlantic restatement with 692, 742, 2026-07-13 and the reason.

**Acceptance Scenarios**:

1. **Given** a restatement recorded since the previous run, **When** the gate runs, **Then** the report lists cut, week, metric, old value, new value, revision date and reason. (User story P3-Q6.)
2. **Given** a restatement older than the restatement window, **When** the gate runs, **Then** it is flagged as out of window and disclosed, never silently applied to comparisons. [NEEDS CLARIFICATION: the window length and out-of-window treatment (System S4)]

---

### User Story 5 - Forecast inputs fit to attribute (Priority: P1)

For the Forecast lane, the gate answers whether an actual is fit for attribution: provisional actuals pause or qualify the case, restated actuals are flagged, and forecast and actual versions must match (Forecast lane; Alvin and Sienna confirm).

**Why this priority**: Explaining a miss the data invented is the Forecast lane's first failure mode (CA-Q1; FE-01 to FE-03).

**Independent Test**: Request a Forecast case for New England 2026-05-04 and for Mid-Atlantic 2026-04-06.

**Acceptance Scenarios**:

1. **Given** a Forecast case for New England 2026-05-04, **When** the gate runs, **Then** the actual is provisional (V = −173 on a provisional actual of 267) and the case is paused or qualified with the feed reasons. (User story CA-Q1.)
2. **Given** a Forecast case for Mid-Atlantic 2026-04-06, **When** the gate runs, **Then** the actual is flagged as restated, even though `forecast_vs_actual_weekly` marks it not provisional. (User stories, "What the data cannot answer yet".)
3. **Given** a forecast version that does not match the requested issue week, **When** the gate runs, **Then** the case stops with a version-mismatch reason (TC-12).

### Edge Cases

- A week arrives with a changed schema version: the cut fails with `UNKNOWN_SCHEMA`.
- A duplicate key carries two different values: the gate flags the conflict and does not pick one.
- Metadata is missing or duplicated for a cut: the cut fails closed (`MISSING_FEED_METADATA`, `DUPLICATE_FEED_METADATA`).
- A cut is wholly absent: it appears in the report as failed, not as zero volume.
- A feed's `loaded_at_utc` is after a run's as-of date: the as-of snapshot treats that week and territory as not yet delivered.
- A holiday week has low volume: that is a calendar matter for stage 3, not a gate failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Stage 1 MUST assign a `run_id` and record lane, week, as-of date, state, timestamps, and release, import fingerprint, semantic-layer, model, prompt and code versions. Forecast runs MUST also record `forecast_issue_week`, horizon and the actual release.
- **FR-002**: A snapshot MUST be identified by the release fingerprint plus an as-of timestamp (UTC), and MUST be immutable. A run MUST pin exactly one. A Monday run's as-of is its start time. Delivery lag counts from the week's Monday start (the `day1-v1` target is 7 days, so a week's feed lands the following Monday).
- **FR-003**: An as-of snapshot MUST present each value as it stood on the as-of date: restatements with `revised_at` after it show their prior value; feeds with `loaded_at_utc` after it are not yet delivered; restatement flags recorded after it do not apply.
- **FR-004**: The gate MUST evaluate every week × territory cut with the v0 checks (expected, missing and duplicate keys; invalid metrics; metadata count; row-count reconciliation; coverage band; delivery lag; source status; schema version; restatement review), with thresholds from the semantic layer (core-002).
- **FR-005**: The gate MUST write a health report: result per cut (pass, warn or fail), every reason code, its evidence, and the threshold behind it. In v0, every reason fails the cut; warn levels are added only when the semantic layer defines them.
- **FR-006**: Later stages MUST read data only through the governed view, which withholds failed cuts and qualifies warned cuts. No stage MAY read `raw` tables for metrics.
- **FR-007**: The gate MUST NOT fill, backfill, deduplicate or drop data silently. Raw rows and evidence views stay queryable.
- **FR-008**: The health report MUST state, for each national or regional total, how many territories it covers, and for any comparison of two weeks, the territories reportable in both.
- **FR-009**: The gate MUST record old value, new value, revision date and reason for every restatement recorded since the previous run of the same lane, inside or outside the window. [NEEDS CLARIFICATION: window length and out-of-window treatment (System S4); proposal: flag and disclose, exclude from comparisons]
- **FR-010**: For the Forecast lane, the gate MUST mark an actual as provisional, restated or fit, and MUST stop a case whose forecast and actual versions do not match.
- **FR-011**: The gate MUST work on any world size.
- **FR-012**: If every cut fails, the run MUST end as a data-health notice only. [NEEDS CLARIFICATION: confirm the A7 proposal with Michael and Meghna; Forecast lane states its own behavior]
- **FR-013**: The gate MUST be deterministic and MUST NOT call a language model.

### Key Entities

- **Run registry row**: `run_id`, lane, week, as-of date, state, timestamps, version pins, snapshot ID (shared with core-005).
- **Snapshot**: release fingerprint plus as-of date; immutable.
- **Health report**: per cut, per check, result, evidence, threshold; territory coverage of totals; restatement records.
- **Restatement record**: cut, week, metric, old value, new value, revision date, reason.
- **Forecast fitness record**: case, actual status (fit, provisional, restated), version match.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The three `day1-v1` artifacts are failed in the right cut with the reasons in User Story 2 (EV-2.1 and FE-01 inputs).
- **SC-002**: At least 90% of seeded artifacts are flagged on dev worlds (EV-2.1, FE-01).
- **SC-003**: 100% of failed cuts are withheld or visibly qualified downstream (EV-2.3).
- **SC-004**: 100% of restatements are recorded with old and new values. None is silently overwritten or double-counted when the window moves (EV-1.2 input, EV-2.4).
- **SC-005**: A re-opened run reads exactly the numbers it read at sign-off (user story P2-Q5; EV-6.2 input).
- **SC-006**: 100% of national totals built on fewer than all territories carry their coverage count.
- **SC-007**: 100% of Forecast cases with provisional or restated actuals are paused or qualified; 100% of version mismatches stop the case (FE-02, FE-03).

## Assumptions

- The gate judges data fitness only. It does not judge business meaning.
- Calendar effects belong to stage 3 (brief-001 and the Forecast variance screen).
- core-005 owns the state machine; this spec supplies LOADED, VALIDATED, VALIDATION_WARNING and VALIDATION_FAILED inputs.
- One release can serve many as-of snapshots, which is what the 10-week back-test needs.
