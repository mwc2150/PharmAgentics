# Implementation Plan: Review, Sign-off and Feedback

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (review half of the 2026-10-16 plan for `009-run-orchestrator-review`)

## Summary

A Streamlit app serves P1, P2 and read-only readers. It reads the run from the registry, shows flags and data health first, opens tool records and Phoenix spans from any number, captures edits with failure tags, drives the two approval gates and the return path, and freezes the published brief. It sends human events (approve, edit, return, sign off, triage decision) to the orchestrator.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Streamlit; DuckDB; Pydantic; core-004 (records, claims, reviews); core-005 (events, states); core-006 tracing links (Arize Phoenix)
**Storage**: `runtime.analyst_review`; published briefs as frozen files plus a `published_brief` row (text hash, claims, snapshot ID); failure catalog via core-006
**Testing**: pytest; Streamlit app tests for gate rules; end-to-end review on a dev week
**Target Platform**: Local browser
**Project Type**: small web UI
**Performance Goals**: A trace link opens in one click, under two seconds locally
**Constraints**: Readers see only PUBLISHED. No path to the ground-truth store. Numbers change only through the tool path
**Scale/Scope**: One brand, two reviewer roles, a few readers

## Constitution Check

| Article | Status |
| :- | :- |
| Shared II People decide | This spec is the human gate. |
| Shared III Answer-key isolation | The app imports nothing from `evalharness`. |
| Briefing B-III Pinned version | Frozen briefs read their pinned snapshot. |
| Briefing B-IV Traceable | One-click links to records and spans. |
| Briefing B-VI No individual identified | Shows only upstream-aggregated data. |

## Project Structure

```text
src/pharmagentics/review/
  app.py           Streamlit entry: run list, draft view, reader view
  trace_links.py   claim → tool record → span URL; restatement beside frozen values
  edits.py         edit capture with failure tag and minutes
  triage.py        TRIAGE_REVIEW approve or edit plan
  signoff.py       two-gate approval, return path, freeze
  roles.py         P1, P2, reader roles (local)
  catalog.py       repeated-tag proposals to core-006
tests/unit/review/  tests/integration/review/
```

## Key Design Points

- Gate rules live in `signoff.py` and are tested without the UI.
- Freeze writes text, claims and snapshot ID once; the brief file is content-hashed.
- A reviewer "change this number" request becomes a token re-run request, not a typed digit, until the team decides otherwise.
- The reader view is a separate page with no access to drafts or flags.

## Complexity Tracking

None.
