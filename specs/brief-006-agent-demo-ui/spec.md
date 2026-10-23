# Feature Specification: Agent Demo and Question-Answer UI (custom-agent prototype)

**Spec ID**: `brief-006-agent-demo-ui` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-23
**Status**: Draft v1. **Unfinished build**: the foundation modules exist; the pipeline, agents, verifier, server, UI and tests do not. See [tasks.md, Build status](tasks.md#build-status-review-of-2026-10-23).
**Input**: User request, 2026-10-23: "Make an architecture diagram for the multi-agent system using draw.io, then build really basic custom agents that follow it. We need a UI for the multi-agent system and a demo where you ask questions and get answers." Sources: System Architecture §3, §4, §4a, §4c, §5; Briefing Architecture §4, §5, §6, §9, §10, §13, §14; user stories P1-Q2, P1-Q3, P1-Q5, P2-Q1, P2-Q2, P2-Q3, P3-Q1, P3-Q2, P3-Q3, P4-Q2.

This spec covers a **cheap, runnable prototype** of the Briefing lane's seven-stage spine. Per Briefing Architecture §14, the prototype exists to learn what the component specs (core-003, core-004, core-005, brief-001 to brief-005) should say. It is then rebuilt from those specs, and it stays runnable as a baseline. It does not replace any of those specs, and it does not touch the Forecast lane.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a question, get a verified answer (Priority: P1)

A Briefing persona types a question in plain words, for example "What changed in the week of 2026-06-08?" or "Why did Pacific fall in June 2026?". The system runs the spine scoped to the question: load and pin, the feed-health gate, competitive intelligence, triage and investigation, narrative, and verification. It returns a short answer. Every figure in the answer comes from a tool and can be clicked.

**Why this priority**: The question-and-answer loop is the demo. Without it there is nothing to show.

**Independent Test**: Ask each of the dev anchor questions below. Compare each answer's labels, leading drivers and withheld cuts with the user stories.

**Acceptance Scenarios**:

1. **Given** week 2026-06-08, **When** the user asks what changed, **Then** the answer has a Pacific story with supply (inventory) as the leading driver and a continuing Metacora competitor story. National figures are labelled with the count of territories reporting. (User story P1-Q5.)
2. **Given** week 2025-04-21, **When** the user asks what changed, **Then** the answer is routine: a KPI line, no stories, and nothing like "Pacific surged". (User story P1-Q3.)
3. **Given** week 2026-04-06, **When** the user asks what changed, **Then** Mid-Atlantic is named as withheld (restatement review), the national dip is labelled a data artifact, and the like-for-like change is stated. The answer never says "BXA fell 18% nationally". (User story P2-Q1.)
4. **Given** week 2026-05-04, **When** the user asks whether the data is complete, **Then** New England is named as not reportable, with its reasons, and the other seven territories are reported. (User story P1-Q2.)
5. **Given** the question "Why did Pacific fall in June 2026?", **When** the agents investigate, **Then** inventory is supported, and promotion and competitor are ruled out, each with evidence. (User story P3-Q3.)
6. **Given** the question "Why did Mid-Atlantic weaken in October 2025?", **When** the agents investigate, **Then** access is supported, naming the plan that added restrictions, and promotion, supply and competitor are ruled out. (User story P2-Q2.)
7. **Given** the question "Why is South Central behind in September 2026?", **When** the agents investigate, **Then** no driver is supported. The story closes at Low confidence as "unresolved, investigate next", and lists the checks run. (User story P2-Q3.)
8. **Given** the question "What happened in the Southeast in August 2026?", **When** the agents investigate, **Then** promotion is supported, stated as an association with its method named, and the other drivers are ruled out. (User story P4-Q2.)

---

### User Story 2 - Watch the agents work (Priority: P1)

While a question runs, the user sees each stage, each manager round, each specialist call and each tool call appear as it happens, with timings. The manager's task ledger and progress ledger are visible.

**Why this priority**: The audience must see that this is a multi-agent system, not a script. Trajectory diversity is the evidence (Briefing Architecture §9).

**Independent Test**: Ask the Pacific question and the South Central question. Check that the trace shows different tool sequences and different exits.

**Acceptance Scenarios**:

1. **Given** a running question, **When** a stage starts or ends, **Then** the trace shows it within one second.
2. **Given** a manager round, **When** it ends, **Then** the trace shows which specialist acted next, which checks it ran, and why the manager stopped or continued.
3. **Given** a story that hits a cap, **When** the loop exits, **Then** the trace shows the cap that tripped and the story closes as "unresolved, investigate next".

---

### User Story 3 - See the architecture (Priority: P1)

The team has one editable architecture diagram of the multi-agent system in draw.io format. It shows the shared platform, the seven-stage spine, the Briefing lane in detail, the Forecast lane as a reserved lane, the human gates and the guardrails. A second page shows the prototype's agents and UI. The UI can display the diagram.

**Why this priority**: The user asked for it first, and the demo's agents must follow it.

**Independent Test**: Open the file in draw.io. Check that each Briefing stage names its spec and its mode (code, agent or human).

**Acceptance Scenarios**:

1. **Given** the diagram file, **When** it is opened in draw.io, **Then** it opens without errors and every box can be edited.
2. **Given** the diagram, **When** a reader looks for the answer-key store, **Then** it sits outside the repository boundary and only the evaluation harness connects to it.

---

### User Story 4 - Two-person review (Priority: P2)

Each answer arrives as a draft. The analyst (P1) approves or returns it. The insights manager (P2) signs it off. The answer shows as approved only after both gates.

**Why this priority**: Agents propose and people decide (shared Principle II). It matters, but the demo works without it.

**Independent Test**: Approve one answer as P1, then sign it off as P2. Return another answer. Check the recorded states.

**Acceptance Scenarios**:

1. **Given** a verified draft, **When** P1 approves and P2 signs off, **Then** the run ends PUBLISHED and both decisions are recorded with their time.
2. **Given** a draft, **When** P2 tries to sign off before P1 approves, **Then** the action is refused.
3. **Given** a draft, **When** either reviewer returns it, **Then** the run is RETURNED and the reason is recorded.

---

### User Story 5 - Run with no model (Priority: P2)

A switch replaces the language-model agents with fixed rules: a fixed order of checks, fixed stop rules and a template narrative. The tools, verdict rules and verifier stay the same. If the model is unreachable, the system falls back to this mode and says so.

**Why this priority**: The demo must never fail on stage. The rule-based mode is also the manager-off ablation (Briefing Architecture §9).

**Independent Test**: Run every anchor question in both modes and compare the labels.

**Acceptance Scenarios**:

1. **Given** the switch set to scripted, **When** any anchor question runs, **Then** no model is called and the answer passes verification.
2. **Given** the model returns an error, **When** a question runs, **Then** the answer still arrives, marked as produced by the scripted fallback.

---

### Edge Cases

- A question with no date uses the latest closed week in the release and says so.
- A date outside the release returns the release's date range and runs nothing.
- An unknown territory returns the list of valid territories.
- A month name resolves to the last Monday-start week of that month.
- A narrative with a digit outside a claim token fails verification. It gets one revision. If it still fails, the template narrative is used and the flags stay visible.
- A story that hits a cap closes as "unresolved, investigate next" and keeps its evidence. The run continues.
- A withheld cut is never read as zero demand.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a free-text question and turn it into a typed intent: question type (what changed, why, data health, metric lookup, competitor), week, territory, product and metric. Every field is checked against the release's allowed values. The parsed intent is shown to the user.
- **FR-002**: Every question MUST start a run with a run ID that pins the data version (import ID and source fingerprint), the model, the prompt version and the code version.
- **FR-003**: The feed-health gate MUST run before any figure is interpreted. Withheld cuts are named with their reasons. National figures state how many territories report.
- **FR-004**: Competitive intelligence MUST be deterministic and read its thresholds from one configuration (a stand-in for core-002).
- **FR-005**: The investigation MUST follow the Magentic pattern: a manager agent groups candidates into stories, orders them, and chooses checks from a fixed catalog. Data Forensics runs before the Driver Investigator. Call depth is two. A no-repeat ledger refuses a check rerun with the same parameters. Caps limit rounds per story, checks per story and run wall time. Hitting a cap closes the story as "unresolved, investigate next".
- **FR-006**: Each check's verdict (supported, ruled out, insufficient evidence) MUST be computed by code. Confidence follows the Briefing rules: High when one driver is supported and every other tested driver is ruled out; Medium when one is supported and others stay open, or more than one is supported; Low otherwise, which means the agent abstains.
- **FR-007**: Promotion MUST get a verdict either way. It is ruled out when activity did not change, and a supported verdict is stated as an association with its method named.
- **FR-008**: The narrative MUST be written only from the closed evidence. Every figure, date and identifier with a digit MUST be a claim token that code fills.
- **FR-009**: Verification MUST reject: a digit outside a claim token; a token that does not resolve; banned terms ("surveillance", "new patients" used for anything but NBRx); causal wording when no story is High confidence; and a story with no evidence. A failing narrative gets one revision. If it still fails, the template narrative is used and the flags stay visible.
- **FR-010**: Every figure in an answer MUST open its evidence item: tool, parameters, query text, result, pinned data version and span.
- **FR-011**: The UI MUST stream the trace of stages, agent turns and tool calls as they happen.
- **FR-012**: The UI MUST provide the two review gates (P1 approve or return, then P2 sign-off or return) and record each decision.
- **FR-013**: The UI MUST offer a scripted mode, and the system MUST fall back to it when the model fails.
- **FR-014**: Tools MUST read Rx metrics only through the governed reporting views, and read context only from an allowlist of agent-visible tables. Access is read-only. The answer-key store and its environment variable are never read.
- **FR-015**: No answer line identifies an individual rep. The detection stage is called "competitive intelligence".
- **FR-016**: Prompts sent to an external model MUST contain only synthetic aggregates, metric definitions, catalog entries and closed tool outputs. Each run records the provider and model (S14).
- **FR-017**: The repository MUST hold an editable draw.io architecture diagram covering the full system (shared platform, spine, Briefing lane, Forecast lane as reserved) and the prototype. The UI can display it.

### Key Entities

- **Question intent**: The typed reading of the user's question: type, week, window, territory, product, metric.
- **Run**: One question's execution: run ID, pins, state history, mode (agent or scripted), timings.
- **Candidate change**: A flagged move from competitive intelligence: cut, metric, actual, baseline, change, peer gap, rule.
- **Story**: A group of candidates investigated together: label, confidence, leading driver, checks run, what to investigate next, function to involve, closure reason.
- **Hypothesis check**: One catalog entry tested for one story: parameters, verdict, evidence references.
- **Evidence item**: One tool call's record: tool, parameters, query, result, data version, span.
- **Claim**: One token in the narrative and the formatted value code puts in its place, linked to an evidence item.
- **Review decision**: A reviewer's role, decision, comment and time.
- **Span**: One traced step: name, agent, parent, start, end, attributes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the eight anchor questions in User Story 1, the answer's labels, withheld cuts and leading drivers match the user stories in 8 of 8 cases in scripted mode, and in at least 7 of 8 in agent mode.
- **SC-002**: Across all anchor answers, zero digits appear outside claim tokens.
- **SC-003**: Answers arrive in under 5 seconds in scripted mode and under 90 seconds in agent mode.
- **SC-004**: A reviewer reaches the evidence behind any figure in one click.
- **SC-005**: Every run ends in a defined state (DRAFTED, VERIFIED, VERIFICATION_FLAGGED, PUBLISHED, RETURNED or RUN_ERROR). No investigation loop runs past its caps.

## Assumptions

- Detection thresholds, the hypothesis catalog and the caps live in one prototype configuration until core-002 ships the semantic layer. Values are starting points, not decisions on Evaluation Pack item 17.
- The handoff objects are prototype forms of the core-004 contracts. Run state is kept in memory, not in `runtime` tables.
- The language model is Gemini (Briefing Architecture §13), called only when a key is set locally. All data is synthetic (shared Principle VI). The agent framework question (A3) stays open: this prototype uses plain Python.
- The LLM judge is not used, because judge agreement has not been measured (Evaluation Pack item 2). Verification here is code only.
- One local user. No authentication.
- The anchors' expected answers come from `docs/planning/user-stories.md`, never from the answer key.
