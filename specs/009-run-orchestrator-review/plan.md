# Implementation Plan: Run Orchestrator and Review Flow

**Branch**: `009-run-orchestrator-review` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

A deterministic orchestrator drives the seven stages through the sixteen run states, logging each transition. A Streamlit review app serves the analyst and the manager. The orchestrator owns run limits, alerts and the freeze of the approved brief.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Streamlit (review UI); DuckDB; Pydantic; OpenTelemetry; Arize Phoenix (trace links); specs 002 to 008
**Storage**: `run_registry`, `state_transition_log`, `analyst_review`, published briefs as files, failure catalog table
**Testing**: pytest; state-machine property tests; Streamlit smoke tests; end-to-end run on dev weeks
**Target Platform**: Local; scheduled trigger via the OS scheduler or a simple loop for demos
**Project Type**: library plus a small web UI
**Performance Goals**: A dev-week run finishes within the wall-clock cap; UI opens a trace link in one click
**Constraints**: Orchestrator contains no agent. Only typed handoffs. Run states from Architecture §6 are the contract.
**Scale/Scope**: One brand, one week per run; two reviewers

## Constitution Check

| Principle | Status |
|---|---|
| IV Pinned data version | Records and enforces pins. |
| V Traceable | Trace links in the UI. |
| VI Typed handoffs | Only typed objects between stages. |
| VII Bounded loops | Enforces run-level limits and defined exit. |
| VIII People decide | Two-gate review. This spec is the principle. |
| XI | Review UI cannot reach `eval_private/`. |

## Project Structure

```text
src/pharmagentics/orchestrator/
  states.py        16 states and allowed transitions
  run.py           stage driver; handoff validation; caps; RUN_ERROR handling
  registry.py      run_registry and transition log
  schedule.py      Monday trigger and manual trigger
  alerts.py        RUN_ERROR alert
src/pharmagentics/review/
  app.py           Streamlit review app
  trace_links.py   claim to evidence to span URLs
  edits.py         edit capture with failure tag
  signoff.py       two-gate approval, freeze
  catalog.py       failure catalog; repeated-tag case proposals
tests/unit/orchestrator/  tests/integration/orchestrator/  tests/unit/review/
```

## State Table (from Architecture §6)

LOADED, VALIDATED, VALIDATION_WARNING, VALIDATION_FAILED, ROUTINE, INVESTIGATION_REQUESTED, TRIAGE_REVIEW, INVESTIGATING, EVIDENCE_RECEIVED, DRAFTED, VERIFIED, VERIFICATION_FLAGGED, IN_REVIEW, PUBLISHED, RETURNED, RUN_ERROR. Allowed transitions are encoded once in `states.py` and tested as a graph.

## Key Design Points

- Transitions are checked against the graph. An illegal transition raises and logs.
- `VALIDATION_FAILED` leads to a data-health notice brief (proposal A7), then verification and review as usual.
- `RETURNED` leads to `DRAFTED` with the manager's comments (proposal A8).
- Freeze: on sign-off, the brief text, claims and snapshot ID are written once. Later edits create a new run.
- Reviewer number edits (open question) are modeled as a re-run of the token, not a typed digit, until the team decides otherwise.
- Cost and time per stage come from spans and are summarized in the run record for EV-8.2.
- Failure-tag catalog counts tags by pattern and proposes a new eval case when a threshold of repeats is met.

## Complexity Tracking

None.
