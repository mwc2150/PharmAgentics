# Feature Specification: Triage, Manager and Specialists (Stage 4)

**Feature Branch**: `006-triage-investigation`
**Created**: 2026-10-16
**Status**: Draft
**Input**: Architecture §5.4, §9, §10.1; Evaluation Pack EV-2.2, EV-4.1 to 4.4, EV-5.1, EV-5.2, EV-5.4; Personas P2-Q1 to P2-Q4

This is the only stage with an agentic loop. The loop is a Magentic pattern: a manager keeps a task ledger and a progress ledger and delegates to two specialists. The decision to run the briefing at all is code-driven and needs no agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triage: decide what to investigate (Priority: P1)

Given all candidate changes of a run, the stage groups them into stories, picks which stories to investigate and in what order, and sets first hypotheses. Code makes the calls a rule can make. The manager makes judgment calls. The analyst reviews only flagged or uncertain calls.

**Why this priority**: Without triage, no story is investigated. The analyst's time depends on review by exception (P1-Q6).

**Independent Test**: Give the stage a week with two events in one region and a few noise candidates. Check that it groups, orders and records which layer made each call.

**Acceptance Scenarios**:

1. **Given** candidates on cuts that failed validation, **When** triage runs, **Then** code drops them and records why.
2. **Given** candidates sharing a cut and timing, **When** triage runs, **Then** code suggests a grouping and the manager confirms or changes it.
3. **Given** a story already resolved in a prior brief, **When** triage runs, **Then** it is linked to that story, so it is not "discovered" again.
4. **Given** code and manager disagree, or the manager marks low confidence, **When** triage finishes, **Then** the run waits in TRIAGE_REVIEW for the analyst.
5. **Given** two events in one region, **When** triage runs, **Then** both stories exist, or the interaction is flagged.

---

### User Story 2 - Check the data first, then find the driver (Priority: P1)

For each story, Data Forensics first asks whether the data is wrong for this change. The Driver Investigator then tests competing explanations: access, promotion, competitor, inventory, segment or geography mix, and days-supply shift. Each hypothesis gets a verdict: supported, ruled out, or insufficient evidence, with tool outputs attached.

**Why this priority**: This is the product's point: first-pass forensics with alternatives on record (P2-Q1, P2-Q2).

**Independent Test**: Run on a seeded access restriction. Check that Data Forensics rules out a data artifact, access is supported, and promotion and competitor are ruled out with evidence.

**Acceptance Scenarios**:

1. **Given** a story, **When** Data Forensics runs, **Then** it checks feed metadata, restatements, panel coverage, the holiday calendar and days-supply mix, and records each result.
2. **Given** a story that is a data artifact, **When** Data Forensics finishes, **Then** the story closes as a data artifact and no driver is claimed.
3. **Given** a real change, **When** the Driver Investigator runs, **Then** each tested hypothesis has a verdict and evidence IDs.
4. **Given** a national change, **When** a contribution decomposition runs, **Then** the story states where the change is concentrated.

---

### User Story 3 - Close every story with an honest label (Priority: P1)

Each story closes with a label (real change, data artifact or calendar effect), a confidence level, a leading driver or none, the alternatives ruled out, what to investigate next, and which function to involve. Low confidence means the agent abstains.

**Why this priority**: Overclaiming costs more than "still investigating" (P2-Q3).

**Independent Test**: Run an ambiguous case. Check that the story closes Low with an "investigate next" entry and no named driver.

**Acceptance Scenarios**:

1. **Given** one supported explanation and others ruled out, **When** the story closes, **Then** confidence is High.
2. **Given** one supported explanation and open alternatives, **When** the story closes, **Then** confidence is Medium.
3. **Given** weak evidence, **When** the story closes, **Then** confidence is Low, no driver is named, and the story is listed under "investigate next" with the function to involve.

---

### User Story 4 - The loop always ends (Priority: P1)

The loop cannot recurse and cannot run forever. The manager calls specialists. Specialists cannot call the manager, each other or new agents. Hypotheses come from a fixed catalog. A test is never repeated with the same parameters. Caps are the backstop. A story that hits a cap closes as "unresolved, investigate next" and the run continues.

**Why this priority**: The mentor raised runaway recursion. The brief must never be blocked.

**Independent Test**: Run a stress case built to conflict across sources. Check the loop exits by the finite-search rule or by the stall cap, not by wall-clock timeout.

**Acceptance Scenarios**:

1. **Given** a story that reaches a cap, **When** the cap trips, **Then** the story closes "unresolved, investigate next", keeps its evidence, and the run reaches stage 5.
2. **Given** a repeated test with the same parameters, **When** the manager requests it, **Then** the ledger refuses.
3. **Given** the call graph, **When** it is inspected, **Then** its depth is two and no specialist can call an agent.
4. **Given** the stress case, **When** the loop runs, **Then** the trace shows exit by the finite-search or stall rule.

---

### User Story 5 - Replay the reasoning (Priority: P2)

A reviewer can replay the manager's task ledger and progress ledger from the trace and see why each tool was chosen.

**Why this priority**: Audit and failure analysis (P2-Q5).

**Independent Test**: Open the trace of a closed story. Check each hypothesis verdict links to tool outputs and the ledger snapshot.

**Acceptance Scenarios**:

1. **Given** a closed story, **When** the trace is opened, **Then** each ledger update is a span with a snapshot.

### Edge Cases

- Zero candidates: stage 4 is skipped and the run goes to the narrative as ROUTINE.
- Too many stories for the round cap: lower-impact stories close as "unresolved, investigate next".
- A tool returns `SuppressedCut` or an error mid-story: the manager handles it as evidence of insufficient data.
- Episodic memory has a prior story with a different driver: the manager notes the conflict and reports continuity honestly.
- A compound week where an artifact masks a real event: the stage separates them. It does not attribute everything to one cause.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The stage MUST accept one `investigation_request` per run and return one `investigation_result` (spec 005).
- **FR-002**: Triage MUST be layered: code, then manager, then analyst by exception. The record MUST show which layer made each call.
- **FR-003**: Code MUST drop candidates on failed cuts, tag calendar weeks, link candidates to resolved stories, and suggest groupings by shared cut and timing.
- **FR-004**: The manager MUST group candidates into stories, choose which to investigate and in what order, and set first hypotheses.
- **FR-005**: Whatever groups candidates MUST see every candidate of the run together.
- **FR-006**: The run MUST pause in TRIAGE_REVIEW when code and manager disagree or the manager marks low confidence. [NEEDS CLARIFICATION: the decision junction: which calls are code, which are LLM, and what flags human review (A1)]
- **FR-007**: The manager MUST keep a task ledger (known facts, facts to look up, hypotheses) and a progress ledger (done, looping, who acts next), both logged as spans.
- **FR-008**: Data Forensics MUST run before the Driver Investigator for each story.
- **FR-009**: Data Forensics MUST check feed metadata, restatements, panel coverage, the holiday calendar and days-supply mix. The days-supply check reads the 90-day fill share context metric (spec 002).
- **FR-010**: The Driver Investigator MUST draw hypotheses only from the semantic-layer catalog.
- **FR-011**: Each hypothesis MUST end with a verdict (supported, ruled out, insufficient evidence) and evidence IDs.
- **FR-012**: The stage MUST produce a contribution decomposition for national changes, with contributions that sum to the total.
- **FR-013**: Each story MUST close with: label, confidence, leading driver or none, alternatives ruled out, next step, function to involve, closure reason.
- **FR-014**: Confidence MUST follow the shared scale: High, Medium, Low (Low means abstain).
- **FR-015**: Call depth MUST be two. Specialists MUST NOT call the manager, each other or new agents. Tools contain no language model.
- **FR-016**: The ledger MUST refuse a test with parameters it has already run for the same story.
- **FR-017**: The stage MUST enforce the caps from the semantic layer. A story that hits a cap MUST close as "unresolved, investigate next" with its evidence kept.
- **FR-018**: Episodic memory MUST be a query over prior runs' stories and brief claims, not a separate store.
- **FR-019**: Manager plan review by the analyst MUST be switchable: on for demos, by exception in the Monday run. [NEEDS CLARIFICATION: confirm default with Dr. Admasu (A10)]
- **FR-020**: Hypothesis tests MUST be code. The agent chooses which test and its parameters, not the math.
- **FR-021**: No story output MAY name a driver at Medium or Low confidence as a cause. The wording gate is spec 008.
- **FR-022**: A scripted baseline MUST exist: the same tools, narrative and verifier with the manager replaced by a fixed order of checks. It is the manager-off ablation.

### Key Entities

- **Story**: candidates, label, confidence, leading driver, continuity, next step, function to involve, closure reason.
- **Hypothesis**: driver, parameters, verdict, evidence IDs.
- **Task ledger and progress ledger**: the manager's logged state.
- **Triage record**: each call and which layer made it.
- **Investigation result**: the closed evidence pack that reaches the narrative.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Leading driver matches the injected driver in at least 70% of single-event weeks (EV-4.1).
- **SC-002**: Every story records competing explanations with verdicts and evidence (EV-4.2).
- **SC-003**: Stated concentration matches the event location, and contributions sum to the total (EV-4.3).
- **SC-004**: In compound or masked weeks, both causes are found or the interaction is flagged, with no single-cause over-attribution (EV-4.4).
- **SC-005**: Higher stated confidence is right more often than lower; rates are reported by level (EV-5.1).
- **SC-006**: The agent abstains on cases built to be ambiguous and does not abstain when evidence is strong (EV-5.2).
- **SC-007**: 100% of stories that reach a cap close as unresolved or are flagged. None close with an unsupported driver (EV-5.4).
- **SC-008**: Artifact versus real versus calendar labels are scored against the answer key with a confusion matrix (EV-2.2).
- **SC-009**: On the stress case, the trace shows exit by the finite-search or stall rule.
- **SC-010**: Tool-sequence variety by case is reported against the scripted baseline.
- **SC-011**: At least 95% of tool calls have correct parameters (white-box; proposed).

## Assumptions

- The data view, tools and contracts from specs 003 and 005 exist.
- Magentic runs inside the briefing use case. The Forecast agent has its own loop.
- Caps start from spec 002's proposed values and are tuned on dev seeds.
- The more triage moves to code or people, the more the agentic claim rests on this loop. It must show its own value against the scripted baseline.
