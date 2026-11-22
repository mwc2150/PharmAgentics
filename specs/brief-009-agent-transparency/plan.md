# Plan: brief-009 Agent Transparency

A file contract for the two work packets in `tasks.md`.

## Run event (the contract between the backend and the UI)

```python
{"seq": 12,                                  # order within the run
 "t": "2026-11-22T14:03:11Z",
 "actor": "Manager" | "Data Forensics" | "Driver Investigator" | "Writer" | "Code" | "Person",
 "kind": "agent" | "llm" | "code" | "person",
 "step": "Plan the stories" | "Coordinate story" | "Is the story done?" | "Check the data" | "Test a driver"
         | "Draft the paragraphs" | "Rewrite a sentence" | "Screen territories" | "Review the plan" | …,
 "story": "territory:SOUTHEAST" | None,
 "tool": "check_promotion" | None,
 "args": {"territory": "SOUTHEAST"} | None,  # analysts only, never leaders
 "verdict": "supported" | "ruled out" | "inconclusive" | "abstained" | "done" | None,
 "summary": "Promotion lines up with the drop, read with a one-week lag.",  # written by code from the tool result; no model digits
 "claims": [14, 15],                         # claim indexes this step produced, if any
 "prompt": "driver_investigator@3f2a9c1"}   # prompt file and short hash, model steps only
```

- The agent engine emits events from one hook: the `RunLog` middleware (`agents/brand-briefing/briefing_lowcode/team.py`), which every agent, tool and chat call passes through, plus `_triage`, `_write` and the revise round in `briefing_agent/__init__.py`. Tool verdicts and claims come from the MCP tool results (`RunSession.calls`), not from model text.
- The scripted engine emits the same shape with actor Code from `briefing_baseline/pipeline.py` and the triage, so both engines show one timeline.
- Progress: a Briefing job gains `progress: [event]`, copying the Forecast pattern (`api/forecast.py` `on_step` and `forecast_store.update`). The external worker posts events (`POST /api/worker/jobs/{id}/progress`, batched with the heartbeat); the built-in worker (`api/agent_host.py`) appends them directly. The finished brief stores `events` beside `flow`.
- Leaders get `process_summary` only: one line built by code ("Built by the agent team: 2 stories, 9 checks; reviewed by the analyst on 2026-11-22").
- Claim to event: each claim index maps to the event that produced it, so the UI can link both ways.

## Packets and the files they own

| Packet | Owns |
| :- | :- |
| **E: events** | `briefing_lowcode/team.py` (RunLog events), `briefing_agent/__init__.py`, `briefing_agent/investigate.py`, `briefing_agent/worker.py`, `briefing_baseline/pipeline.py` (events only), `briefing_baseline/triage.py` (events only), `src/pharmagentics/api/jobs.py`, `api/agent_host.py`, `api/app.py` (progress route), `api/service.py` (store events), `api/views.py` (`process_summary`, leaders never get events), tests for each |
| **T: timeline and tab** | new `frontend/figma-make/src/Timeline.tsx`, new `frontend/figma-make/src/HowItWorks.tsx`, `App.tsx` (replace the FlowPanel call; add the tab; a few lines), `agent/briefingApi.ts` (event and actor types), new `src/pharmagentics/api/agents_info.py` and its route in `api/app.py` (`GET /api/briefing/agents`: actors, jobs, tools, prompts verbatim for analysts and the tester only, the latest scripted-versus-agent comparison from the telemetry the Evaluation page already reads), `tests/test_frontend_scope.py`, new `tests/test_agents_info.py` |

T builds against the event schema above with sample events; E does not touch the frontend.

## Checks

Focused tests per packet; `tsc` and `vite build` for T; no eval runs. The integrator runs the full suite, the scripted gate (events must not change the answer, claims or evidence: FR-008), one Haiku agent run, and a real-app check of the live timeline.
