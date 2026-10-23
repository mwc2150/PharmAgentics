# Feature Specification: Run Orchestrator

**Spec ID**: `core-005-run-orchestrator` (shared; owners: both teams)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: the orchestrator half of `009-run-orchestrator-review` (Oct 16). The review half is now `brief-005-review-signoff`.
**Input**: System Architecture §3.4, §4, §5, S1, S2; Briefing Architecture §3, §4, §6, §10.1; Evaluation Pack EV-8.2, EV-8.5; Forecast FE-21, FE-26; User stories P1-Q6, P2-Q6, CA-Q6

## Context

The Proposal's shared orchestration layer becomes one run orchestrator (System §3.4). It owns run IDs, state, timeouts, failures and logging for both lanes. Each lane keeps its own trigger, its own state graph and its own Magentic loop, so neither agent waits on the other. The orchestrator is code, not an agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One Briefing run from start to finish (Priority: P1)

A Monday run takes one brand and the latest closed week and moves through the Briefing graph's sixteen states (Briefing Architecture §6). Each transition is logged against the `run_id`. Every run ends in PUBLISHED or RUN_ERROR.

**Why this priority**: Nothing else runs without it.

**Independent Test**: Run a dev week end to end with stubs for stages 4 to 6. Check the transition log is complete and the run ends in a terminal state.

**Acceptance Scenarios**:

1. **Given** a closed week, **When** the run starts, **Then** it moves through LOADED, VALIDATED (or VALIDATION_WARNING or VALIDATION_FAILED), ROUTINE or INVESTIGATION_REQUESTED, then DRAFTED, VERIFIED or VERIFICATION_FLAGGED, IN_REVIEW and PUBLISHED, logging each transition.
2. **Given** a quiet week (2025-04-21), **When** the run runs, **Then** it goes ROUTINE, skips stage 4, and still passes narrative, verification and two-person review. (User story P1-Q3.)
3. **Given** a tool, data or model failure, **When** it stops the run, **Then** the state is RUN_ERROR, an alert is raised, and a rerun is possible with a new `run_id`.
4. **Given** the same week and the same pins, **When** the run is repeated, **Then** it reads the same snapshot.

---

### User Story 2 - Lanes run independently on one orchestrator (Priority: P1)

The Forecast lane registers its own trigger (a flagged forecast miss or a manual `forecast.InvestigationRequest`) and its own state graph. Both lanes share run IDs, the registry, timeouts, alerts and logging. Neither lane's run waits on, reads or changes the other's.

**Why this priority**: The System Architecture amends the Proposal's single manager to one orchestrator with a loop per lane (S2).

**Independent Test**: Start a Briefing run and a Forecast run for the same week at once. Check both complete with separate run IDs and logs.

**Acceptance Scenarios**:

1. **Given** a registered lane graph, **When** it is loaded, **Then** the orchestrator checks it has RUN_ERROR and at least one other terminal state, and that every state can reach a terminal state.
2. **Given** a Briefing run and a Forecast run on the same week, **When** both run, **Then** neither blocks the other and each registry row names its lane.
3. **Given** a Forecast re-run of the request for 2026-08-24, **When** it runs, **Then** it pins the same versions and returns identical figures. (User story CA-Q6; FE-21.)
4. **Given** no runtime handoff is wired (S1), **When** either lane runs, **Then** it never calls the other lane.

---

### User Story 3 - Limits, cost and visible state (Priority: P2)

Every run stays within its lane's caps. Operators see each run's state, timing, tokens, cost and failures per stage.

**Why this priority**: Cost and time must be predictable (P1-Q6, P2-Q6), and the scorecard compares cost and time across versions (EV-8.2, FE-26).

**Independent Test**: Force a cap breach in stage 4. Check the story closes as unresolved and the run continues to stage 5.

**Acceptance Scenarios**:

1. **Given** a cap breach in a Briefing story, **When** it occurs, **Then** the story closes "unresolved, investigate next" and the run continues (EV-5.4, EV-8.5).
2. **Given** a run-level wall-clock breach, **When** it occurs, **Then** the run ends in RUN_ERROR with the reason, never hangs.
3. **Given** any run, **When** its record is read, **Then** it holds wall time, tokens and cost per stage.

### Edge Cases

- The week has not closed, or its feed has not loaded yet: the run refuses to start and says why.
- A second run starts for the same week and lane: it gets its own `run_id` and snapshot; the first is untouched.
- A run waits in TRIAGE_REVIEW or IN_REVIEW for days: it stays there; the next week's run is independent.
- An illegal transition is requested: it raises and is logged; the run goes to RUN_ERROR.
- A stage returns an object that fails its schema: the stage stops and the run goes to RUN_ERROR with the field named.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The orchestrator MUST assign every run a `run_id` and a lane, and MUST write the run registry row with the pins from core-003.
- **FR-002**: The orchestrator MUST run each lane against that lane's registered state graph and log every transition with `run_id`, from, to, time and reason.
- **FR-003**: The Briefing graph MUST be the sixteen states and transitions in Briefing Architecture §6. Every Briefing run MUST end in PUBLISHED or RUN_ERROR.
- **FR-004**: A Briefing run with no candidates MUST skip stage 4 and still pass stages 5 to 7.
- **FR-005**: VALIDATION_FAILED MUST route to a data-health notice brief (proposed answer to A7). RETURNED MUST route to DRAFTED with the reviewer's comments (proposed answer to A8).
- **FR-006**: The Forecast lane MUST be able to register its own trigger and graph without changes to the orchestrator (Forecast lane; Alvin and Sienna supply the graph).
- **FR-007**: The orchestrator MUST pass only typed objects between stages (core-004).
- **FR-008**: The orchestrator MUST enforce each lane's run-level caps from the semantic layer and record wall time, tokens and cost per stage.
- **FR-009**: The orchestrator MUST raise an alert on RUN_ERROR and allow a rerun with a new `run_id`.
- **FR-010**: The orchestrator MUST support a scheduled Monday trigger and a manual trigger for demos and evaluation, and MUST accept an as-of timestamp so the harness can replay past weeks (core-006 back-test).
- **FR-011**: Lanes MUST NOT call each other at run time. [NEEDS CLARIFICATION: whether to wire a runtime handoff, and in which direction (System S1)]
- **FR-012**: The orchestration model MUST be confirmed with the mentor as an amendment to the Proposal. [NEEDS CLARIFICATION: one orchestrator with a Magentic loop per lane, not one manager over both (System S2; supersedes Briefing A2)]

### Key Entities

- **Run registry row**: see core-004 data-model.md.
- **State graph**: per lane: states, allowed transitions, terminal states.
- **State transition log**: from, to, time, reason.
- **Trigger**: Monday schedule, manual, flagged miss, request.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of runs end in a terminal state with every transition logged (Briefing Architecture §14 criterion).
- **SC-002**: 100% of Briefing runs stay within round, time and length limits (EV-8.5).
- **SC-003**: Per-run wall time, tokens and cost are reported for every version (EV-8.2, FE-26).
- **SC-004**: Concurrent runs of both lanes complete with no shared state other than the registry.
- **SC-005**: Re-runs on the same pins reproduce every figure (FE-21).

## Assumptions

- The only agentic loop in each lane is stage 4. The orchestrator is deterministic code.
- The Monday trigger is a scheduled job; a simple loop is enough for demos.
- The review surface is brief-005 for Briefing; the Forecast lane has its own.
