# Tasks: brief-009 Agent Transparency

Two packets in parallel after brief-008 merges (`plan.md` has the event schema and file ownership).

### Packet E: events (FR-001, FR-002, FR-003, FR-005, FR-007, FR-008)
- [x] E1 Event recording in `RunLog` and the agent run (triage, story teams, story-done, writer, revise), with actor names mapped to the four actors and prompt file plus hash on model steps.
- [x] E2 The scripted engine emits the same events with actor Code.
- [x] E3 Job `progress` (external worker route, built-in worker) and `events` stored with the brief; claim-to-event map.
- [x] E4 `process_summary` for leaders; leaders never get events, arguments or prompts.
- [x] E5 Tests: event order and actors on a stubbed agent run; scripted events; progress round trip; the answer, claims and evidence are unchanged with events on; leader cut.

### Packet T: timeline and "How it works" (FR-004, FR-006)
- [ ] T1 `Timeline.tsx`: live while the job runs (polls the job's `progress`), saved afterwards; grouped by story; first five steps per actor with the rest folded; findings link to claims in the memo and back.
- [ ] T2 Replace the collapsed stage list for analysts; leaders see `process_summary`.
- [ ] T3 `HowItWorks.tsx` tab: the flow from question to brief with the four actors, a card per actor (job, tools, where its output lands), prompts verbatim for analysts and the tester, and the scripted-versus-agent comparison.
- [ ] T4 `GET /api/briefing/agents` and its tests (prompts hidden from leaders).
- [ ] T5 `tsc`, `vite build`, `tests/test_frontend_scope.py`.

## Integration (Opus)
- [ ] I1 Merge E and T; full suite; scripted gate (unchanged answers); one Haiku agent run and gate; real-app check of a live run; `/code-review`; pull request.
