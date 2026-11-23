# 2026-11-22 brief-009 packet E: run events

Branch `feature/brief-009-events` (worktree `pa-009-E`). Continues the interrupted agent's work (`d2d3026`); packet T (timeline UI, `GET /api/briefing/agents`) is on `feature/brief-009-timeline`.

## What was built

- `src/pharmagentics/tools/events.py` (new): `EventLog` (ordered, thread-safe, `on_event` hook, claim-token filling, claim-to-event attribution in `finalize`), plus `clean` and `clean_claim_events`, the server-side allow-list of what a worker may post.
- E1, agent engine:
  - `briefing_lowcode/team.py`: `RunLog(events=None)` gains `record_tool` and `record_chat`, called from the existing tool and chat middleware. Manager turns map to Manager, `data_forensics` to Data Forensics, `driver_investigator` to Driver Investigator, writer and reviser to Writer. Model steps carry `prompt` as `<file>@<7-hex sha256>`.
  - `briefing_agent/trace.py` (new): prompt refs, `note` (a step done by code), `attach` (puts `events` and `claim_events` on the run result).
  - `briefing_agent/__init__.py` and `investigate.py`: events for the code screen, the manager's plan, the analyst's review (actor Person, no identity), pinning, code sections, each story's close, the writer's check, and assembly. `events_for(on_event, seed)` builds a log; `triage` and `run_with_plan` take `events=`.
- E2, scripted engine: `briefing_baseline/pipeline.py` takes `events=` on `answer` and `run_with_plan` and emits actor Code steps (pin, data check, national figures, screen, per-check events in run order, close the story, write, verify). `api/service.py` always records them.
- E3: `jobs.add_progress` (idempotent by `seq`, counts as a heartbeat), `POST /api/worker/jobs/{id}/progress` (bearer token, 200 events per batch), `GET /api/agent/jobs/{id}?after=N`, built-in worker posts through `agent_host._run_job`, external worker posts in batches with the heartbeat (`worker.ProgressPost`). The brief job continues the triage job's log (seeded from the plan's `events`). The finished brief stores `events` and `claim_events` (for each brief claim, the seq of the producing event). `store.save_brief` backfills them on an existing brief.
- E4: `views.process_summary` and `leadership()` returns it. The leader view is allow-listed, so events, arguments and prompts never reach it.
- E5: `tests/test_run_events.py`.

## Event shape emitted

As in `plan.md`: `seq, t, actor, kind, step, story, tool, args, verdict, summary, claims, prompt`. `claims` is empty while a run is live and filled when the brief is finished (indexes into `claims`). `summary` is code text; claim tokens are replaced by the run's own claim values (an unknown one reads "a figure"). Steps emitted: Screen territories, Plan the stories, Review the manager's plan, Review the plan (Person), Pin the data and period, Build the memo's code sections, Coordinate story, Check the data, Test a driver, Is the story done?, Check the competitor, Close the story, Build the bottom line and next checks, Draft the paragraphs, Check the writer's sentences, Rewrite a sentence, Assemble the memo; scripted adds Read the national figures, Write the brief, Verify the numbers. Verdicts are read from the tool result by code.

Leader view: `process_summary`, for example "Built by the scripted engine: 2 stories, 4 checks; reviewed by the analyst on 2026-11-22."

## Tests

- `uv run pytest -q tests/test_run_events.py`: 9 passed (stubbed agent run with the real MCP server and RunLog; answer, claims, evidence, flow and triage identical with events on and off; worker streaming and log continuation; scripted events and unchanged brief; external-worker progress round trip including bad token, junk events, retried batch and `after`; built-in worker; leader cut; summary without events; claim attribution; batching with a failed post).
- Related existing files (test_agent_build3, test_tools, test_rbac, test_briefing_api, test_jobs, test_agent_host): 123 tests, 4 failed on first run (three fakes without the new `events` kwarg, one leader allow-list assertion without `process_summary`); fixed in the tests, then test_briefing_api and test_rbac 56 passed.
- Full suite, the scripted gate, a Haiku run and a real-app timeline check are the integrator's (I1). No eval run was made.

## Fixes made in this session

The earlier agent's `tests/test_run_events.py` did not run: it patched `briefing_agent.investigate._team` through `from briefing_agent import investigate`, which resolves to the function, and kept a half-written first test and an unused fixture. Both were replaced (module imported with `importlib`, dead code removed).

## Deviations and open items

- `briefing_baseline/triage.py` was not changed. The scripted triage (a stateless route) emits no events; the scripted brief run carries the "Screen territories" and "Review the plan" steps. The agent's triage job does record events and they are continued in the brief.
- `claim_events` is not in packet T's `briefingApi.ts` types (only `RunEvent.claims` and `progress`); the UI links both ways through `event.claims`, which is filled. `claim_events` is there for the claim-to-event direction if T wants it.
- Events are bounded at 600 per run and 200 per posted batch.
- Not run here: the app against a live agent worker (no model).
