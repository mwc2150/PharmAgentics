# Tasks: brief-009 Agent Transparency

Two packets in parallel after brief-008 merges (`plan.md` has the event schema and file ownership).

### Packet E: events (FR-001, FR-002, FR-003, FR-005, FR-007, FR-008)
- [x] E1 Event recording in `RunLog` and the agent run (triage, story teams, story-done, writer, revise), with actor names mapped to the four actors and prompt file plus hash on model steps.
- [x] E2 The scripted engine emits the same events with actor Code.
- [x] E3 Job `progress` (external worker route, built-in worker) and `events` stored with the brief; claim-to-event map.
- [x] E4 `process_summary` for leaders; leaders never get events, arguments or prompts.
- [x] E5 Tests: event order and actors on a stubbed agent run; scripted events; progress round trip; the answer, claims and evidence are unchanged with events on; leader cut.

### Packet T: timeline and "How it works" (FR-004, FR-006)
- [x] T1 `Timeline.tsx`: live while the job runs (polls the job's `progress`), saved afterwards; grouped by story; first five steps per actor with the rest folded; findings link to claims in the memo and back.
- [x] T2 Replace the collapsed stage list for analysts; leaders see `process_summary`.
- [x] T3 `HowItWorks.tsx` tab: the flow from question to brief with the four actors, a card per actor (job, tools, where its output lands), prompts verbatim for analysts and the tester, and the scripted-versus-agent comparison.
- [x] T4 `GET /api/briefing/agents` and its tests (prompts hidden from leaders).
- [x] T5 `tsc`, `vite build`, `tests/test_frontend_scope.py`.

## Integration review fixes
Found in review of the merged branch; each has a test in `tests/test_run_events.py`.
- [x] R1 The built-in worker keeps progress in memory (`jobs.add_progress(persist=False)`) and a beat writes the store at most every 3 s (`jobs.persist_progress`, snapshot taken under the lock, written outside it), always again at the job's end; the beat is stopped before the job completes.
- [x] R2 "Check the competitor" is recorded only when the competitor section is not empty (the scripted engine's `if comp`), so an empty one is no story in the timeline or the leader's count.
- [x] R3 The Promotion review and out-of-scope early returns in `_run` attach `events` and `claim_events`, so the saved brief keeps its timeline.
- [x] R4 `ProgressPost` posts in chunks of at most 200 (the app's limit); a refused batch (4xx other than 408 and 429) is dropped and logged, only network errors and 5xx are retried.
- [x] R5 Flushes are serialized and `ProgressPost.close()` waits for one in flight before the http client closes; `jobs.add_progress` inserts a late earlier `seq` in order (idempotent, no duplicates).
- [x] R6 Inside a story's timed team run, tool events record no `export_run` round trip (`EventLog.defer`); their summaries are filled once after the run (`EventLog.resolve`). Live, a summary shows the values known when it was recorded, else "a figure".
- [x] R7 `Timeline.tsx` counts checks as `views.process_summary` does (`countChecks`).
- [x] R8 "Check the writer's sentences" counts problems found, not the parts that had any.
- [x] R9 "Screen territories" is recorded after the out-of-scope check, so an out-of-scope plan never claims to have screened territories.
- [x] R10 `process_summary` ends "; reviewed by the analyst." with no date; the leader view adds "on <date>" in the viewer's time zone from `reviewed_at` (already in the leader allow-list).

## Integration (Opus)
- [ ] I1 Merge E and T; full suite; scripted gate (unchanged answers); one Haiku agent run and gate; real-app check of a live run; `/code-review`; pull request.
