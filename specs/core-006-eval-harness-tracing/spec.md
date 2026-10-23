# Feature Specification: Evaluation Harness and Tracing

**Spec ID**: `core-006-eval-harness-tracing` (shared; owners: both teams. Briefing owns EV scoring; Forecast owns FE scoring)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `010-eval-harness-tracing` (Oct 16)
**Input**: System Architecture §3.5, §3.6, §9, S10; Briefing Architecture §11, §12, §14; Evaluation Pack (all sections, 37 items); Forecast Personas & Eval Design §3 (FE-01 to FE-31, TC-01 to TC-12; cited by ID); User stories (all 42, as dev anchor cases)

## Context

One harness is the only component that reads the answer key, which lives outside the repository (System §3.6; shared Principle III). It scores each lane against that lane's own pack: Briefing on EV-1.1 to EV-9.4, Forecast on FE-01 to FE-31. Shared conventions: held-out seeded cases, scripted and low-code baselines, repeated runs, answer-key isolation. Five item pairs measure the same property in both lanes and share one scoring function while each lane reports its own number (System §9).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One command scores a version on the same cases (Priority: P1)

An evaluator runs one command for a lane, a version and a case set. The harness runs each case through the orchestrator, scores every item that can be scored automatically, and logs one experiment. Every version of a lane runs the same cases and is scored by the same items.

**Why this priority**: Like-for-like comparison across builds is the project's evidence.

**Independent Test**: Run the Briefing scripted baseline on the dev split. Check the scorecard has a row per eval item and a logged experiment.

**Acceptance Scenarios**:

1. **Given** a lane, a version and a case set, **When** the suite runs, **Then** each case runs the configured number of times, and mean and spread are reported.
2. **Given** two versions of a lane, **When** both run on the same cases, **Then** the scorecard shows versions by dimensions in one layout (Briefing: Evaluation Pack §1 dimensions; Forecast: by scenario family, with N/A where an item does not apply).
3. **Given** a change that lowers a gated score, **When** the suite runs, **Then** it is reported as a regression and blocks the merge (Briefing B-VII).

---

### User Story 2 - Score against the answer key without exposing it (Priority: P1)

Only the harness reads the ground-truth store, through `PHARMAGENTICS_EVAL_STORE`. No agent, tool, prompt, UI or log can. No ground-truth file is in the repository. Tests prove both.

**Why this priority**: A leaked key makes every score meaningless (EV-9.3, FE-30).

**Independent Test**: Run the isolation scan and probe. Plant a reader outside the harness and a committed answer-key file; check each fails the test.

**Acceptance Scenarios**:

1. **Given** the codebase, **When** the scan runs, **Then** only `evalharness` reads `PHARMAGENTICS_EVAL_STORE`, and no committed file matches the ground-truth patterns.
2. **Given** any tool or agent path, **When** the probe tries the store, **Then** access is refused (core-004).
3. **Given** a planted reader or a committed answer-key file, **When** the scan runs, **Then** the test fails.

---

### User Story 3 - Trace every step and link every number (Priority: P1)

Every Briefing stage, tool call, agent turn and model call emits a span with run ID, seed, week, metric ID, story ID, agent name, ledger snapshot, tokens, cost, latency, handoff state and failures. A number in a brief links to the span that computed it. The Forecast lane meets the shared floor: every number traces to a tool record on the pinned data version.

**Why this priority**: Traceability is a core need of both lanes (P1-Q4, P2-Q5, CA-Q6, FM-Q6).

**Independent Test**: Run a dev week. Pick five numbers and open their spans and tool records.

**Acceptance Scenarios**:

1. **Given** a Briefing run, **When** it finishes, **Then** every stage, tool call and model call has a span with the listed attributes.
2. **Given** a claim token, **When** its link is followed, **Then** it opens the tool record and span that produced the value, on the pinned snapshot (EV-6.2).
3. **Given** a Forecast report, **When** a figure's citation is followed, **Then** it resolves to a tool record on the pinned versions (FE-20).

---

### User Story 4 - Dev anchor cases from the user stories (Priority: P1)

Each of the 42 user stories becomes a dev case on its anchor week: its Given / When / Then is the case, its "must not say" is the fail phrase, its eval items are the items scored. Briefing cases get `C-###` IDs; Forecast cases get `TC-##` IDs and are confirmed by Alvin and Sienna.

**Why this priority**: The stories are already written on real weeks of the release. They are the fastest route to a scored dev set, and the user stories doc says to do exactly this.

**Independent Test**: Build the case file from the user stories. Run the scripted baseline. Check each case scores its listed items.

**Acceptance Scenarios**:

1. **Given** user story P1-Q2 (New England, 2026-05-04), **When** its case runs, **Then** the brief must name New England as not reportable with its three reasons and label national totals "7 of 8", and fails if it says "New England BXA fell 34%".
2. **Given** user story P2-Q3 (South Central, September 2026), **When** its case runs, **Then** the story must close Low as "unresolved, investigate next" and fails if it names Metacora as the cause.
3. **Given** any case whose expected outcome needs the answer key (for example whether the South Central gap is the sixth event), **When** it is scored, **Then** the harness reads the key; the case file holds no key fields.

---

### User Story 5 - Splits, held-out discipline and the back-test (Priority: P1)

Dev cases are open while building. Held-out cases open only at check-ins, and scores are logged before any change. The Briefing headline test is a ten-week back-test of consecutive weeks on a held-out seed, replayed through the orchestrator with as-of timestamps.

**Why this priority**: The course's four success criteria depend on it.

**Independent Test**: Ask for held-out cases before a check-in; check refusal. Run the ten-week back-test on a dev seed; check the four outputs.

**Acceptance Scenarios**:

1. **Given** held-out cases outside a check-in, **When** they are requested, **Then** access is refused unless the evaluator opens them, and the opening is logged.
2. **Given** a held-out run, **When** it finishes, **Then** scores are logged before any code or prompt change.
3. **Given** the back-test, **When** it finishes, **Then** it produces factual accuracy for ten briefs, numeric reconciliation, a failure catalog, and a cost and time comparison with timed gold briefs.

---

### User Story 6 - Failure catalog, judge agreement, ablation and stability (Priority: P2)

Every failed item and every analyst edit gets one failure tag from its lane's list. Human rubric scoring and judge agreement are supported. The scripted baseline runs as the manager-off ablation; tool-sequence diversity and run-to-run stability are reported.

**Why this priority**: The final presentation walks through one failure; "is the agent really a script?" is a Proposal risk.

**Independent Test**: Run agent and scripted versions on the same cases with seeded failures.

**Acceptance Scenarios**:

1. **Given** a failed item, **When** the scorecard is built, **Then** the failure carries exactly one tag from its lane's list.
2. **Given** human and judge labels, **When** agreement is computed, **Then** the report shows the statistic and the bar.
3. **Given** agent and scripted runs, **When** compared, **Then** the report shows tool-sequence variety by case and where scores differ (EV-4.x, EV-5.x; FE-29).

### Edge Cases

- A case's answer-key record is incomplete: the case fails as a fixture error, not a model error.
- A version crashes on a case: the case scores as a failure tagged "run error" (Briefing) or WORKFLOW / GOVERNANCE (Forecast).
- An item does not apply to a scenario: it is marked N/A, never scored as a failure (Forecast §3.3).
- A held-out seed is regenerated: old scores stay tied to the old seed ID.
- A target is loosened after held-out results are seen: the harness rejects it.
- Cost data is missing for a model call: the harness reports the gap, not zero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: One command MUST run a lane's version on a case set and score every automatically scorable item.
- **FR-002**: Versions MUST be: Briefing manual (timed gold briefs), scripted, low-code, custom agent; Forecast BL-0 (stub), BL-1 (low-code), BL-2 (adaptive Investigator), optional human reference.
- **FR-003**: Each case MUST run the configured number of times, with mean and spread reported. [NEEDS CLARIFICATION: rerun count, weighed against cost (Evaluation Pack open item 15); proposal: five]
- **FR-004**: The harness MUST implement the 37 Briefing items (EV-1.1 to EV-9.4) with their methods. It MUST provide the hooks for the Forecast team to implement FE-01 to FE-31.
- **FR-005**: The five parallel pairs (EV-2.1 / FE-01, EV-6.2 / FE-20, EV-8.4 / FE-28, EV-9.3 / FE-30, EV-9.4 / FE-31) MUST share one scoring function; each lane reports its own number.
- **FR-006**: Only `evalharness` MAY read the ground-truth store, through `PHARMAGENTICS_EVAL_STORE`. A scan MUST fail on any other reader and on any committed ground-truth file.
- **FR-007**: The harness MUST build dev cases from the user stories (anchor week, Given/When/Then, must-not-say, eval items) and from the generator's scenario requests (core-001), and MUST assign each case to dev or held-out.
- **FR-008**: The harness MUST manage dev and held-out splits. Held-out MUST open only on request, every opening MUST be logged, and scores MUST be logged before any change.
- **FR-009**: The harness MUST run the ten-week back-test through the orchestrator's replay trigger and produce the four course-floor outputs.
- **FR-010**: Briefing runs MUST emit spans for every stage, tool call, agent turn and model call with the attributes in User Story 3. Claim provenance MUST run from token to tool record to span.
- **FR-011**: Experiments MUST log to the trace viewer so versions compare on the same cases.
- **FR-012**: The harness MUST keep a failure catalog per lane, one tag per failure, counted by tag and version. [NEEDS CLARIFICATION: shared vocabulary for tags, confidence, driver labels and answer-key format (System S10; Evaluation Pack open items 8, 9, 12)]
- **FR-013**: The harness MUST support human rubric scoring with anchors per item. [NEEDS CLARIFICATION: rubric scale and anchors (Evaluation Pack open item 13)]
- **FR-014**: The harness MUST compute judge-human agreement and report it against the bar before any judge-scored item is used.
- **FR-015**: The harness MUST run the manager-off ablation and report tool-sequence diversity by case.
- **FR-016**: The harness MUST reject any target loosened after held-out results are seen, and MUST tune nothing on held-out cases.
- **FR-017**: The harness MUST report run-to-run variance and never hide it, and MUST report cost and time per output against the manual baseline.
- **FR-018**: Scores MUST be reported by scenario family as well as pooled; an always-abstaining or always-attributing system must not score well (Forecast §3.1).

### Key Entities

- **Case**: ID, lane, category or scenario family, seed, week, split, Given/When/Then, must-not-say, eval items, source (user story ID or scenario request).
- **Experiment**: lane, version, case set, reruns, scores, time and cost.
- **Scorecard**: versions by dimensions (Briefing) or by scenario family (Forecast).
- **Failure catalog entry**: tag, item or edit, version, count.
- **Gold brief**: blind-written, timed, optionally double-written.
- **Span**: one traced step with attributes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full suite for a lane runs in one command and logs one experiment.
- **SC-002**: The isolation scan and probe pass on the current tree and fail on a planted reader or committed key file (EV-9.3, FE-30).
- **SC-003**: 100% of Briefing runs produce complete spans; 100% of claim links and Forecast citations resolve (EV-6.2, FE-20).
- **SC-004**: All 24 Briefing user stories run as dev cases and score their listed items; the 18 Forecast stories are available to the Forecast team as cases.
- **SC-005**: The ten-week held-out back-test produces all four course-floor outputs by the final presentation.
- **SC-006**: A planted regression on any gated item is caught and blocks the merge.
- **SC-007**: Judge-human agreement is reported before any judge-scored item is used.
- **SC-008**: Critical error rate per Briefing version is reported (EV-8.3).
- **SC-009**: A data-inventory review is recorded per release and per model provider (EV-9.4, FE-31, S14).
- **SC-010**: Check-in evidence meets Evaluation Pack §9 (Oct 30, Nov 23, Nov 27, Dec 4, Dec 7, Dec 14).

## Assumptions

- About 40 dev and 15 held-out Briefing cases (Evaluation Pack §7); the 24 Briefing user stories are the first dev cases.
- Gold briefs are written blind by someone who did not build the generator (Evaluation Pack open item 6).
- The harness scores the output and its evidence only; it does not depend on the model, framework or orchestration (black-box rule).
- The Forecast team writes its own FE scoring modules inside the harness package and owns them.
