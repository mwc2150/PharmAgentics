# Feature Specification: Agent Transparency

**Spec ID**: `brief-009-agent-transparency` (Briefing lane; owners: Michael, Meghna)
**Feature Branch**: `feature/brief-009-agent-transparency`
**Created**: 2026-11-22 | **Updated**: 2026-11-22
**Status**: Specified; builds after brief-008's first wave (work packets in `tasks.md`)
**Input**: Grill with Michael, 2026-11-22. Briefing Architecture §4a (Triage and investigation: Manager, Data Forensics, Driver Investigator; the blue boxes), §6 states, §9 modes. brief-002 (triage, manager and specialists; US7 stage flow).

## Why

The architecture has three agents: the Manager, Data Forensics and the Driver Investigator. The code has seven prompts:
- `manager_triage`, `manager` and `story_done` are three steps of the Manager. `story_done` is Magentic's own "is this story finished?" check.
- `data_forensics` and `driver_investigator` are one prompt each.
- `writer` and `revise` are a Writer step that the diagram does not show. `revise` runs only when the writer's sentences break a rule.

A user cannot see any of this. The brief shows only a collapsed "How this brief was made" list of the seven stages, with Code / Agent / LLM chips. It shows no tool call, no finding, and nothing about which part of the brief came from which agent. Nor can the user see whether the prompts matter. With Haiku now driving the agents and reading the question (brief-008), the flow must be readable by someone who is not an engineer.

## Clarifications

### Session 2026-11-22 (grill with Michael; do not reopen)

- Q: Which agents does the user see? → A: **Four actors**: Manager, Data Forensics, Driver Investigator (the architecture's blue boxes) and Writer, marked as **an LLM step, not an agent**. Prompts appear as steps under their actor: triage plan, per-story coordination and story-done check under Manager; first draft and rewrite under Writer. The code keeps its seven prompts.
- Q: What is "the new Briefing tab"? → A: **Both**: (a) a live **timeline** in each brief, replacing the collapsed panel, and (b) a **"How it works"** tab.
- Q: What does the timeline record? → A: An event log on each run: actor, step, tool, verdict (supported, ruled out, inconclusive, abstained) and the claim it produced. It fills in live while the brief builds and is saved with the brief. The scripted engine shows the same timeline with **Code** as the actor, so both engines read the same way. Leaders get a one-line process summary, not the timeline.
- Q: Who sees what in the tab? → A: Everyone sees each actor's job, its tools and its place in the flow. **Analysts and the tester** also see each prompt verbatim. Impact evidence now is the existing scripted-versus-agent comparison from the Evaluation runs; per-actor ablations (for example, a brief without the Driver Investigator) come in a later spec.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Watch the brief being built (Priority: P1)

Ace (P1) builds a brief on the agent engine. A timeline under the brief fills in as it runs:
- The Manager picks two stories.
- Data Forensics checks Southeast's feed and finds it complete.
- The Driver Investigator runs the promotion check, which supports a one-week lag, and the access check, which is ruled out.
- The Writer drafts the paragraphs, and one sentence is rewritten.

Each line shows its result in plain words, and each finding links to the line of the brief it produced.

**Independent Test**: An agent run of the P3-Q5 question with the timeline open; the same question on the scripted engine.

**Acceptance Scenarios**:

1. **Given** an agent run, **When** it is in progress, **Then** the timeline shows each actor's steps as they finish, in order, with the tool used and its verdict.
2. **Given** a finished brief, **When** the analyst clicks a timeline finding, **Then** the brief scrolls to the sentence or claim it produced; **and** clicking a claim in the brief shows which actor produced it.
3. **Given** the scripted engine, **When** the brief is built, **Then** the timeline shows the same steps with "Code" as the actor.
4. **Given** the leader view, **When** it opens, **Then** it shows one line ("Built by the agent team: 2 stories, 9 checks, reviewed by the analyst on …") and no timeline.

---

### User Story 2 - Understand the agents (Priority: P2)

A new teammate opens "How it works". A diagram shows the flow from question to brief, with the four actors as in the architecture. Each actor has a card with its job in one sentence, its tools, and where its output lands in the memo. An analyst can expand a card to read the prompt verbatim. A panel shows what the agents add: scripted against agent on the latest Evaluation runs (recall, gated checks, cost a brief, time a brief).

**Independent Test**: Open the tab as an analyst, a leader and the tester.

**Acceptance Scenarios**:

1. **Given** any role, **When** the tab opens, **Then** it shows the flow and the four actor cards.
2. **Given** an analyst or the tester, **When** a card is expanded, **Then** it shows the prompts of that actor verbatim from the repository; a leader sees no prompt.
3. **Given** the Evaluation store has a scripted and an agent run, **When** the tab opens, **Then** it shows their comparison with run dates; with none, it says so.

### Edge Cases

- An agent run that fails or hits a cap: the timeline shows where it stopped and the story closes "unresolved, investigate next".
- A brief made before this spec: no event log; the tab still works and the brief shows the old stage list.
- A prompt changed after a brief was built: the timeline links to the prompt version used (its hash).
- Many tool calls: the timeline groups them under their story and shows the first five per actor, with the rest folded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each run MUST record an ordered event log: time, actor (Manager, Data Forensics, Driver Investigator, Writer, Code, Person), step, tool and arguments, verdict, claim indexes produced, and prompt hash for model steps.
- **FR-002**: The log MUST be available while the job runs (polling the job) and saved with the brief.
- **FR-003**: Both engines MUST produce the log; the scripted engine's actor is Code.
- **FR-004**: The analyst view MUST show the timeline, replacing the collapsed stage list, with links between findings and the brief's claims in both directions.
- **FR-005**: The leader view MUST show a one-line process summary and no timeline, tool arguments or prompts.
- **FR-006**: A "How it works" tab MUST show the flow, the four actors with job, tools and memo destination, prompts verbatim for analysts and the tester only, and the latest scripted-versus-agent comparison.
- **FR-007**: The log MUST NOT carry ground truth, golden cases or an individual rep's identity; it holds only what the brief's own evidence holds.
- **FR-008**: Recording the log MUST NOT change the brief's answer, claims or evidence (gated checks unchanged).

### Key Entities

- **Run event**: time, actor, step, tool, arguments, verdict, claims, prompt hash, story.
- **Actor**: name, kind (agent, LLM step, code, person), job, tools, prompts.

## Success Criteria *(mandatory)*

- **SC-001**: Every gated check stays at 1.000 on both engines.
- **SC-002**: 100% of claims in an agent brief link to the event that produced them.
- **SC-003**: In a hallway test, a teammate who has not seen the code can name what each of the four actors did in a given brief after reading its timeline.
