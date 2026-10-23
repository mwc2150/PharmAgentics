# Implementation Plan: Run Orchestrator

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the orchestrator half of the 2026-10-16 plan for `009-run-orchestrator-review`)

## Summary

A deterministic driver runs any registered lane graph. Lane graphs are data: states, transitions, terminal states, and the stage function bound to each state. The Briefing graph ships with this spec; the Forecast team registers theirs. One registry, one transition log, one alert path and one cost meter serve both lanes.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic v2, DuckDB, OpenTelemetry (stage spans and cost attributes), core-002 to core-004
**Storage**: `runtime.run_registry`, `runtime.state_transition_log` in DuckDB
**Testing**: pytest; graph property tests; end-to-end dev-week run with stubs
**Target Platform**: Local; OS scheduler or a simple loop for the Monday trigger
**Project Type**: library with a command-line entry point (`python -m pharmagentics.orchestrator run --lane briefing --week 2026-08-24 --as-of …`)
**Performance Goals**: A dev-week Briefing run finishes within its wall-clock cap
**Constraints**: No agent inside the orchestrator. Lanes never call each other
**Scale/Scope**: One brand; two lanes; one run per lane per week, plus replays

## Constitution Check

| Article | Status |
| :- | :- |
| Shared II People decide | Review states are human gates; the orchestrator never skips them. |
| Shared IV Typed contracts | Only typed objects pass between stages. |
| Shared VII Loops end | Run-level caps and terminal-state checks on every graph. |
| Shared platform: one orchestrator | This spec is the rule (S2 pending). |
| Briefing B-III Pinned version | Writes and enforces pins from core-003. |

## Project Structure

```text
src/pharmagentics/orchestrator/
  graph.py         LaneGraph model; validation (terminal reachability, RUN_ERROR present)
  lanes/briefing.py  the 16-state Briefing graph and stage bindings
  run.py           driver: pins, stage calls, handoff validation, caps, RUN_ERROR
  registry.py      run_registry and transition log
  triggers.py      Monday schedule, manual, replay (as-of)
  alerts.py        RUN_ERROR alert
  meter.py         wall time, tokens, cost per stage from spans
  __main__.py      CLI
tests/unit/orchestrator/  tests/integration/orchestrator/
```

**Structure Decision**: Lane graphs are data, so the Forecast lane plugs in by adding `lanes/forecast.py` (or registering from `agents/forecast-explanation`, per S16) with no change to `run.py`.

## Briefing Graph (Briefing Architecture §6)

LOADED, VALIDATED, VALIDATION_WARNING, VALIDATION_FAILED, ROUTINE, INVESTIGATION_REQUESTED, TRIAGE_REVIEW, INVESTIGATING, EVIDENCE_RECEIVED, DRAFTED, VERIFIED, VERIFICATION_FLAGGED, IN_REVIEW, RETURNED, PUBLISHED, RUN_ERROR. Terminal: PUBLISHED, RUN_ERROR. Transitions are encoded once in `lanes/briefing.py` and tested as a graph.

## Key Design Points

- **Stage binding**: each non-human state names the stage function that leaves it; human states (TRIAGE_REVIEW, IN_REVIEW) wait for an event from brief-005.
- **Stubs first**: every Briefing stage has a stub so the end-to-end run works before stages land (milestone "end-to-end run, stubs OK", Oct 9–30).
- **Caps**: stage 4 enforces story caps itself (brief-002); the orchestrator enforces run-level wall clock and token budget and turns a breach into RUN_ERROR with reason.
- **Replay**: the harness starts runs with an as-of timestamp; the orchestrator passes it to core-003.
- **Cost**: model calls emit token counts on spans; `meter.py` sums them per stage into the registry row.

## Complexity Tracking

None.
