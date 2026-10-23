# Feature Specification: Triage, Manager and Specialists (Stage 4a)

**Spec ID**: `brief-002-triage-investigation` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `006-triage-investigation` (Oct 16)
**Input**: System Architecture §4a, §4c, S5; Briefing Architecture §5.4, §9, §10.1, decisions 4, 5, 9, 18, 20; Evaluation Pack EV-2.2, EV-4.1 to EV-4.5, EV-5.1, EV-5.2, EV-5.4, EV-7.2; Personas P2, P4; User stories P1-Q5, P2-Q1, P2-Q2, P2-Q3, P2-Q4, P3-Q3, P3-Q4, P4-Q1, P4-Q2, P4-Q4, P4-Q5

This is the only Briefing stage with an agentic loop: a Magentic manager keeps a task ledger and a progress ledger and delegates to two specialists, Data Forensics and the Driver Investigator. The decision to run the brief at all is code-driven. The Forecast lane's loop (4b) is separate and owned by Alvin and Sienna.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triage: decide what to investigate (Priority: P1)

Given every candidate of the run in one `briefing.investigation_request`, the stage groups candidates into stories, picks which to investigate and in what order, and sets first hypotheses. Code makes the calls a rule can make. The manager makes judgment calls. P1 reviews only flagged or uncertain calls.

**Why this priority**: Without triage, no story is investigated. The analyst's time depends on review by exception (P1-Q6).

**Independent Test**: Run week 2026-06-08 (Pacific supply plus Metacora). Check two stories, their order and which layer made each call.

**Acceptance Scenarios**:

1. **Given** candidates on withheld cuts, **When** triage runs, **Then** code drops them and records why.
2. **Given** candidates sharing a cut and timing, **When** triage runs, **Then** code suggests a grouping and the manager confirms or changes it.
3. **Given** a story already open in a prior brief (Metacora, from 2026-03-02), **When** triage runs, **Then** the candidate links to it and the story is marked continuing, not rediscovered. (User story P3-Q4.)
4. **Given** code and manager disagree, or the manager marks low confidence, **When** triage finishes, **Then** the run waits in TRIAGE_REVIEW for P1.
5. **Given** week 2026-06-08, **When** triage runs, **Then** there are two stories, ranked by impact: the Pacific drop (about half of the national gap) and Metacora's share gain. (User story P1-Q5.)

---

### User Story 2 - Check the data first, then test every driver (Priority: P1)

For each story, Data Forensics first asks whether the data is wrong. The Driver Investigator then tests the catalog drivers, each with a verdict and its evidence: access, promotion, competitor, inventory, rep vacancy, segment or geography mix, days-supply shift.

**Why this priority**: First-pass forensics with alternatives on record is the product (P2-Q1, P2-Q2).

**Independent Test**: Run the Mid-Atlantic access weeks and the Pacific supply weeks.

**Acceptance Scenarios**:

1. **Given** week 2026-04-06 as of today, with Mid-Atlantic withheld for restatement, **When** Data Forensics runs, **Then** the national dip closes as a data artifact, the like-for-like change is stated, and no business story opens unless that change clears the thresholds. (User story P2-Q1.)
2. **Given** Mid-Atlantic, 2025-08-04 to 2025-10-27, **When** the Driver Investigator runs, **Then** access is supported (plan SYN_MID_ATLANTIC_MEDICARE_PART_D_1 moved BXA to tier 3 with PA and step therapy; BXA TRx on that plan fell 22.5%, competitors each gained about 20%), and promotion (calls 50 against 53), supply (fill 0.98), competitor launch (Metacora not until 2026-03-02) and data artifact (all cuts pass) are each ruled out with evidence. (User story P2-Q2.)
3. **Given** Pacific, 2026-06-01 to 2026-06-29, **When** the Driver Investigator runs, **Then** inventory is supported (fill 0.69 to 0.72, about 23% backordered; recovery when fill returned to 1.0), competitor is ruled out (Metacora's Pacific share in line with other territories) and promotion is ruled out (calls about 54 a week, no vacancy). (User stories P1-Q5, P3-Q3.)
4. **Given** a national change, **When** the contribution decomposition runs, **Then** the story states its concentration down to plan and specialty, and contributions sum to the total. (User story P2-Q4.)

---

### User Story 3 - Promotion gets a verdict either way (Priority: P1)

Promotion is tested in every story where promotion activity is available. It is supported only when activity changed and the comparison with peers supports it; it is ruled out when another driver explains the change or activity did not change. A supported promotion finding is an association, with its method named, never an attributed lift.

**Why this priority**: P4 needs to know whether a campaign moved the brand without crediting the latest campaign for a formulary win (P4-Q1, P4-Q4; EV-4.5).

**Independent Test**: Run the Great Lakes lapse and the Mid-Atlantic restoration.

**Acceptance Scenarios**:

1. **Given** Great Lakes, 2026-02-02 to 2026-04-06 (aggregated calls fell from about 48 to about 20 a week, impressions averaged 915 against a median of 1,652; TRx fell 16.5% while other territories rose 1.1% in the four weeks before Metacora's launch; TRx jumped 503 to 730 when calls returned on 2026-04-13), **When** promotion is tested, **Then** it is supported for the drop, stated as an association, with method and control set named. (User story P4-Q1.)
2. **Given** Mid-Atlantic, 2025-11-03 to 2025-12-15 (Part D plan BXA +19%, NBRx +42% after PA and step therapy were removed on 2025-11-01; calls steady near 50; national +14.4% the same weeks), **When** promotion is tested, **Then** it is ruled out, access is the leading driver, and the seasonal share is noted. (User story P4-Q4.)
3. **Given** any week where promotion activity did not change, **When** the story closes, **Then** promotion is not credited.
4. **Given** a promotion story, **When** the result is built, **Then** it carries promotion activity for the same cut and weeks for the narrative (EV-7.5).

---

### User Story 4 - Close every story with an honest label (Priority: P1)

Each story closes with a label (real change, data artifact, calendar effect, or unresolved), a confidence level, a leading driver or none, the alternatives ruled out, what to investigate next, which function to involve, and its comparison (method, control set, dropped controls).

**Why this priority**: Overclaiming costs more than "still investigating" (P2-Q3; shared Principle V).

**Independent Test**: Run the South Central gap and the Great Lakes and Southeast lapses together.

**Acceptance Scenarios**:

1. **Given** South Central, 2026-08-31 to 2026-09-28 (BXA −4.2% against July while others rose 11.1%; calls normal, no vacancy, no PA or step-therapy change, fill ≥ 0.968, feeds clean; Metacora share 16.0% against 13.8% to 15.8% elsewhere), **When** the story closes, **Then** it is Low, "unresolved, investigate next", lists the checks run, names no driver, and suggests plan and specialty splits and local context from sales leadership. (User story P2-Q3.)
2. **Given** the Great Lakes and Southeast lapses six months apart, both about 31 points below other territories, **When** the promotion finding closes, **Then** confidence is Medium, both cases are named, and the next read is due four weeks after the next change. It is never High from one territory. (User story P4-Q5.)
3. **Given** one supported explanation with the others ruled out, **When** the story closes, **Then** confidence is High; with alternatives still open it is Medium.
4. **Given** a control territory with its own event in the window (for example Pacific in June 2026), **When** a comparison runs, **Then** that territory is dropped from the control set, and the story records why. (User story method note; Forecast story FM-Q4.)

---

### User Story 5 - The loop always ends (Priority: P1)

The loop cannot recurse or run forever: depth two, a fixed catalog, a no-repeat ledger, and caps as backstop. A story that hits a cap closes as "unresolved, investigate next", keeps its evidence, and the run continues.

**Why this priority**: The mentor raised runaway recursion. The brief must never be blocked.

**Independent Test**: Run a stress case built to conflict across sources.

**Acceptance Scenarios**:

1. **Given** a story that reaches a cap, **When** the cap trips, **Then** the story closes unresolved with its evidence and the run reaches stage 5.
2. **Given** a repeated test with the same parameters, **When** the manager requests it, **Then** the ledger refuses.
3. **Given** the call graph, **When** inspected, **Then** its depth is two and no specialist can call an agent.
4. **Given** the stress case, **When** the loop runs, **Then** the trace shows exit by the finite-search or stall rule, not by wall-clock timeout.

---

### User Story 6 - Replay the reasoning (Priority: P2)

A reviewer replays the manager's ledgers from the trace and sees why each tool was chosen.

**Why this priority**: Audit and failure analysis (P2-Q5).

**Independent Test**: Open the trace of a closed story; each verdict links to tool records and a ledger snapshot.

**Acceptance Scenarios**:

1. **Given** a closed story, **When** its trace is opened, **Then** each ledger update is a span with a snapshot.

### Edge Cases

- Zero candidates: stage 4 is skipped; the run goes to the narrative as ROUTINE.
- Too many stories for the round cap: lower-impact stories close as "unresolved, investigate next".
- A tool returns `SuppressedCut`, `BelowFloor` or an error mid-story: the manager treats it as insufficient evidence for that test.
- Episodic memory holds a prior story with a different driver: the manager notes the conflict and reports continuity honestly.
- An artifact masks a real event in the same week: the stage separates them and does not attribute everything to one cause.
- Two drivers overlap in time and place (the Great Lakes lapse overlaps Metacora's launch): the controls stay valid only if the overlapping driver hits every territory alike (Metacora at 8.8% to 10.0% everywhere); otherwise confidence drops or the story abstains.
- A cell is below the small-cell floor (cash, 36 to 49 TRx a week): its split is reported as noisy and never generalized (user story P4-Q2).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The stage MUST accept one `briefing.investigation_request` per run and return one `briefing.investigation_result` (core-004).
- **FR-002**: Triage MUST be layered: code, then manager, then P1 by exception. The record MUST show which layer made each call.
- **FR-003**: Code MUST drop candidates on withheld cuts, tag calendar weeks, link candidates to stories in episodic memory, and suggest groupings by shared cut and timing.
- **FR-004**: The manager MUST group candidates into stories, choose which to investigate and in what order, and set first hypotheses. Whatever groups candidates MUST see every candidate of the run together.
- **FR-005**: The run MUST pause in TRIAGE_REVIEW when code and manager disagree or the manager marks low confidence. [NEEDS CLARIFICATION: the decision junction: which calls are code, which are LLM, and what flags human review (Briefing A1)]
- **FR-006**: The manager MUST keep a task ledger (known facts, facts to look up, hypotheses) and a progress ledger (done, looping, who acts next), both logged as spans.
- **FR-007**: Data Forensics MUST run before the Driver Investigator for each story, and MUST check feed health, restatements, coverage, the holiday calendar and days-supply mix.
- **FR-008**: The Driver Investigator MUST draw hypotheses only from the Briefing catalog (core-002), including inventory (S5, Proposed) and rep vacancy.
- **FR-009**: Each hypothesis MUST end with a verdict (supported, ruled out, insufficient evidence) and evidence IDs.
- **FR-010**: Promotion MUST receive a verdict in every story where promotion activity exists. It MUST NOT be supported in a window where activity did not change. A supported promotion finding MUST be stated as an association with its method and control set.
- **FR-011**: Every driver test that compares an exposed cut with others MUST use `compare_to_peers`, name its control set, and drop territories with their own active event in the window.
- **FR-012**: The stage MUST produce a contribution decomposition for national and territory changes down to plan and specialty, with contributions that sum to the total.
- **FR-013**: Each story MUST close with every field of `story` in core-004 data-model.md: label, confidence, leading driver or none, concentration, continuity, investigate next, function to involve, closure reason and comparison.
- **FR-014**: Confidence MUST follow the Briefing scale: High (one supported, others ruled out), Medium (one supported, alternatives open), Low (abstain). A finding resting on one territory MUST NOT be High.
- **FR-015**: Call depth MUST be two. Specialists MUST NOT call the manager, each other or new agents. Tools contain no model.
- **FR-016**: The ledger MUST refuse a test with parameters already run for the same story.
- **FR-017**: The stage MUST enforce the Briefing caps from the semantic layer. A story that hits a cap MUST close as "unresolved, investigate next" with its evidence kept.
- **FR-018**: Episodic memory MUST be a query over prior runs' stories and brief claims, not a separate store, and MUST supply continuity: weeks running and direction (user story P3-Q4: Metacora in its 31st week, worse than at launch, flat for 8 weeks).
- **FR-019**: Plan review by P1 MUST be switchable: always on for demos, by exception in the Monday run. [NEEDS CLARIFICATION: confirm the default with Dr. Admasu (Briefing A10)]
- **FR-020**: Hypothesis tests MUST be code. The agent chooses which test and its parameters, never the math.
- **FR-021**: A scripted baseline MUST exist: the same tools, narrative and verifier, with the manager replaced by a fixed order of checks. It is the manager-off ablation.

### Key Entities

Story, hypothesis, task and progress ledgers, triage record, `briefing.investigation_result` (fields in core-004 data-model.md).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Leading driver matches the injected driver in at least 70% of single-event weeks (EV-4.1), and on every `day1-v1` anchor with a visible driver.
- **SC-002**: Every story records competing explanations with verdicts and evidence (EV-4.2); the P2-Q2 case lists all five.
- **SC-003**: Stated concentration matches the event location, and contributions sum to the total (EV-4.3).
- **SC-004**: In compound or masked weeks, both causes are found or the interaction is flagged (EV-4.4).
- **SC-005**: Promotion verdicts are right on seeded cases with and without a promotion change; promotion is never credited where it was not injected (EV-4.5).
- **SC-006**: Higher stated confidence is right more often than lower (EV-5.1).
- **SC-007**: The agent abstains on ambiguous cases (South Central) and not when evidence is strong (EV-5.2).
- **SC-008**: 100% of capped stories close unresolved or flagged; none with an unsupported driver (EV-5.4).
- **SC-009**: Artifact, real and calendar labels are scored with a confusion matrix (EV-2.2).
- **SC-010**: Continuing stories are marked with direction (EV-7.2 input).
- **SC-011**: At least 95% of tool calls have correct parameters; tool-sequence variety is reported against the scripted baseline (white-box; Briefing Architecture §12).

## Assumptions

- core-003, core-004 and brief-001 exist.
- Caps start from core-002's proposed values and are tuned on dev seeds.
- The more triage moves to code or people, the more the agentic claim rests on this loop; it must show its value against the scripted baseline.
- No runtime handoff to the Forecast lane in v1 (S1). A Forecast report, if one exists, could later enter as one evidence item.
