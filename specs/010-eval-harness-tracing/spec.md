# Feature Specification: Evaluation Harness and Tracing

**Feature Branch**: `010-eval-harness-tracing`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §11, §12, §14; Evaluation Pack (all sections); Personas

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One command scores a build on the same cases (Priority: P1)

An evaluator runs one command. It runs a chosen version (manual, scripted, low-code or custom agent) on the chosen cases, scores every eval item, and logs the result as one experiment. Every version runs the same cases and is scored by the same items.

**Why this priority**: The comparison across builds is the project's evidence. The Evaluation Pack requires like-for-like scoring.

**Independent Test**: Run the scripted baseline on the dev split. Check the scorecard has a row per eval item and a logged experiment.

**Acceptance Scenarios**:

1. **Given** a version and a case set, **When** the evaluator runs the suite, **Then** each case runs five times and the mean and spread are reported (proposed; Evaluation Pack open item 15).
2. **Given** two versions, **When** both run on the same cases, **Then** the scorecard shows versions by dimensions in one layout.
3. **Given** a change that lowers any gated score, **When** the suite runs, **Then** it is reported as a regression and blocks the merge.

---

### User Story 2 - Score against the answer key without exposing it (Priority: P1)

Only the harness reads the answer key. Auto-scored items compare the brief and its evidence to the key. No agent, tool, index or prompt can see it. Tests prove it.

**Why this priority**: A leaked key makes every score meaningless (EV-9.3).

**Independent Test**: Run the isolation probe against every agent path. Run a build with a planted key reader and check the test fails.

**Acceptance Scenarios**:

1. **Given** the codebase, **When** the import and path scan runs, **Then** only the harness module touches `eval_private/` and the answer-key store.
2. **Given** any tool or agent path, **When** the probe tries the answer key, **Then** access is refused.
3. **Given** a planted reader outside the harness, **When** the scan runs, **Then** the test fails.

---

### User Story 3 - Trace every step and link every number (Priority: P1)

Every tool call, agent turn and LLM call emits a span with run ID, seed, week, metric ID, story ID, agent name, ledger snapshot, tokens, cost, latency, handoff state and failures. A number in a brief links to the span that computed it.

**Why this priority**: Traceability is a Personas core need (P1-Q4, P2-Q5).

**Independent Test**: Run a dev week. Pick five numbers and open their spans.

**Acceptance Scenarios**:

1. **Given** a run, **When** it finishes, **Then** every stage, tool call and model call has a span with the listed attributes.
2. **Given** a claim token, **When** its link is followed, **Then** the span of the tool that produced the value opens.
3. **Given** the run record, **When** read, **Then** it holds tokens, cost and latency per stage.

---

### User Story 4 - Splits, held-out discipline and the back-test (Priority: P1)

Dev cases are open while building. Held-out cases open only at check-ins, and scores are logged before any change is made. The headline test is a ten-week back-test of consecutive weeks on a held-out seed.

**Why this priority**: The course's four success criteria depend on it: ten weeks of briefings scored for accuracy, numbers reconciled to tables, a failure-mode catalog, and a cost and time comparison with manual work.

**Independent Test**: Request held-out cases before a check-in. Check access is refused. Run the ten-week back-test on a dev seed and check the four outputs are produced.

**Acceptance Scenarios**:

1. **Given** held-out cases outside a check-in, **When** the harness is asked for them, **Then** access is refused unless the evaluator opens them, and the opening is logged.
2. **Given** a held-out run, **When** it finishes, **Then** scores are logged before any code or prompt change.
3. **Given** the ten-week back-test, **When** it finishes, **Then** it produces factual accuracy, numeric reconciliation, a failure catalog, and a cost and time comparison with the timed gold briefs.

---

### User Story 5 - Failure catalog and judge agreement (Priority: P2)

Every failed eval item and every analyst edit gets one failure tag. The catalog counts them by tag and version. Human rubric scoring and judge agreement are supported.

**Why this priority**: The final presentation walks through one meaningful failure. The judge must be measured before it is trusted.

**Independent Test**: Run a build with seeded failures. Check each is tagged once and counted.

**Acceptance Scenarios**:

1. **Given** a failed item, **When** the scorecard is built, **Then** the failure is tagged from the shared list.
2. **Given** human labels and judge labels, **When** agreement is computed, **Then** the report shows the agreement statistic and the bar.

---

### User Story 6 - Ablation and stability (Priority: P2)

The harness runs the scripted baseline as the manager-off ablation, reports trajectory diversity, and reports run-to-run stability.

**Why this priority**: It answers "is the agent really a script?" (Proposal risk).

**Independent Test**: Run agent and scripted versions on the same cases. Check the tool-sequence report and the stability spread.

**Acceptance Scenarios**:

1. **Given** the agent and scripted runs, **When** compared, **Then** the report shows tool-sequence variety by case and where the agent scores differently.
2. **Given** five reruns, **When** compared, **Then** spread in stories reported and drivers named is shown.

### Edge Cases

- A case's answer-key record is incomplete. The harness fails the case and reports the data error, not a model error.
- A version crashes on a case. The case scores as a failure with tag "run error".
- A held-out seed is regenerated. Its old scores stay tied to the old seed ID.
- Targets set after seeing held-out results. The harness rejects any loosening of a target.
- Cost data is missing for a model call. The harness reports the gap rather than assuming zero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: One command MUST run a version on a case set and score all eval items that can be scored automatically.
- **FR-002**: The harness MUST support these versions: manual (timed gold briefs), scripted, low-code, custom agent.
- **FR-003**: Each case MUST run the configured number of times, and the harness MUST report mean and spread. [NEEDS CLARIFICATION: rerun count, weighed against cost (Evaluation Pack open item 15); proposal: five]
- **FR-004**: The harness MUST implement the 35 eval items in the Evaluation Pack with their methods (auto, human, judge, review).
- **FR-005**: The harness MUST produce one scorecard of versions by dimensions in the same layout at every check-in.
- **FR-006**: Only the harness MAY read the answer key, the true data and the counterfactual components. The generator (spec 001) MAY write to that store but MUST NOT read it. A scan test MUST enforce both rules.
- **FR-007**: The harness MUST manage dev and held-out splits. Held-out MUST open only on request and every opening MUST be logged.
- **FR-008**: The harness MUST log scores before any change after a held-out run.
- **FR-009**: The harness MUST run the ten-week back-test and produce the four course-floor outputs.
- **FR-010**: Every run MUST emit spans for each stage, tool call, agent turn and model call, with the attributes in User Story 3.
- **FR-011**: Claim provenance MUST run from claim token to evidence item to span, and each link MUST open on click.
- **FR-012**: Experiments MUST log to the trace viewer so versions compare on the same cases.
- **FR-013**: The harness MUST keep the failure catalog, attach one tag per failure, and count by tag and version.
- **FR-014**: The harness MUST support human rubric scoring (Meets, Partly, Misses) with anchors per item. [NEEDS CLARIFICATION: rubric anchors (Evaluation Pack open item 13)]
- **FR-015**: The harness MUST compute judge-human agreement and report it against the bar.
- **FR-016**: The harness MUST run the manager-off ablation and report tool-sequence diversity by case.
- **FR-017**: The harness MUST reject any change that loosens a target after held-out results are seen.
- **FR-018**: The harness MUST report run-to-run variance and never hide it.
- **FR-019**: The harness MUST tune nothing on held-out cases.
- **FR-020**: The harness MUST report cost and time per brief and compare them with timed gold briefs.
- **FR-021**: The harness MUST build the Given/When/Then cases (Evaluation Pack §4) from the answer key and the generator's scenario requests, with expected stories, drivers, concentration, confidence range and "must not say" phrases, and MUST assign each case to the dev or held-out split.

### Key Entities

- **Case**: seed, week, split, Given/When/Then, eval items.
- **Experiment**: version, case set, reruns, scores, time and cost.
- **Scorecard**: versions by dimensions.
- **Failure catalog entry**: tag, item or edit, version, count.
- **Gold brief**: blind-written, timed, optionally double-written.
- **Span**: one traced step with attributes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full suite runs in one command and logs one experiment (Architecture §14 criterion).
- **SC-002**: The isolation scan and probe pass with 100% on the current build, and fail on a planted reader (EV-9.3).
- **SC-003**: 100% of runs produce complete spans, and 100% of claim links resolve (EV-6.2).
- **SC-004**: The ten-week held-out back-test produces all four course-floor outputs by the final presentation.
- **SC-005**: Every version's scorecard row uses the same case set and items.
- **SC-006**: A regression on any gated item is detected and blocks the merge in 100% of planted-regression tests.
- **SC-007**: Judge-human agreement is reported before any judge-scored item is used.
- **SC-009**: Critical error rate is reported per version: the share of briefs with a wrong number, a wrong driver at High confidence, a missed top event, or a false alarm in the top three (EV-8.3; target to set).
- **SC-010**: A data-inventory review confirms no proprietary or patient data went to an external tool, and the review is recorded for each release (EV-9.4).
- **SC-008**: Check-in evidence meets the schedule in Evaluation Pack §9 (Oct 30 low-code; Nov 23 scripted vs low-code; Dec 4 executed pack; Dec 7 custom agent; Dec 14 final).

## Assumptions

- About 40 dev and 15 held-out cases (Evaluation Pack §7), generated by spec 001.
- Gold briefs are written blind by someone who did not build the generator. Who writes them is Evaluation Pack open item 6, for the mentor.
- The Forecast team has its own eval items. The harness shares the answer-key convention, tag list and held-out rules with it.
- The harness scores the brief and its evidence only. It does not depend on the model, framework or orchestration (black-box rule).
