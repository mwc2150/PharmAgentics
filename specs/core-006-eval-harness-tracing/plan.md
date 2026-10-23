# Implementation Plan: Evaluation Harness and Tracing

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `010-eval-harness-tracing`)

## Summary

A harness package is the only code allowed to read ground truth, which it finds outside the repository through `PHARMAGENTICS_EVAL_STORE`. It replays cases through the orchestrator, scores each lane against its own items, and logs experiments. Dev cases come first from the user stories. OpenTelemetry spans viewed in Arize Phoenix trace the Briefing lane; the Forecast lane meets the shared floor through tool records.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest; OpenTelemetry SDK; Arize Phoenix (local); DuckDB; pandas or Polars; Pydantic; SciPy or scikit-learn (confusion matrices, agreement)
**Storage**: `cases/` (dev case files, no key fields) in the repo; experiments, scorecards and failure catalog in a local DuckDB file; ground truth and held-out cases outside the repo
**Testing**: pytest for the harness; planted-reader, planted-key-file and planted-regression tests
**Target Platform**: Local; Phoenix runs locally
**Project Type**: library with a CLI (`python -m pharmagentics.evalharness run --lane briefing --version scripted --split dev`)
**Performance Goals**: Budgeted by cost, not code
**Constraints**: Black-box scoring. Only `evalharness` reads the store. Nothing from the store is written into the repo
**Scale/Scope**: About 55 Briefing cases × 5 reruns × 4 versions; Forecast TC-01 to TC-12 variants

## Constitution Check

| Article | Status |
| :- | :- |
| Shared III Answer-key isolation | This spec enforces it: env-var store, scan, probe, committed-file check. |
| Shared VI Synthetic data only | Data-inventory review per release and provider (SC-009). |
| Briefing B-IV Traceable | Spans and provenance. |
| Briefing B-VII Evaluation gate | Regressions block merge; targets never loosen after held-out. |
| Briefing B-III Pinned version | Every score references the run's snapshot. |

## Project Structure

```text
cases/
  briefing/dev/C-001.yaml …     built from user stories P1-Q1 … P4-Q6 (no key fields)
  forecast/dev/                 built by the Forecast team from CA-Q1 … FM-Q6
src/pharmagentics/evalharness/
  store.py        the only reader of PHARMAGENTICS_EVAL_STORE
  cases.py        case model; user-story importer; scenario-request importer; splits; access log
  runner.py       replays cases through core-005 with as-of; reruns; artifact capture
  items/briefing/ numeric reliability detection explanation calibration traceability communication efficiency governance
  items/forecast/ (owned by Alvin and Sienna)
  items/shared.py the five parallel-pair functions
  scorecard.py  failures.py  rubric.py  agreement.py  ablation.py  regression.py
  isolation.py    import and env-var scan; committed-file pattern scan; runtime probe
  backtest.py     ten consecutive weeks; four course-floor outputs
  __main__.py
src/pharmagentics/tracing/
  spans.py  provenance.py  phoenix.py
tests/unit/evalharness/  tests/integration/evalharness/  tests/eval/
```

**Structure Decision**: The harness is its own package so one import rule keeps ground truth sealed. Lane item modules are separate so each team owns its own.

## Briefing Item Methods (Evaluation Pack §3)

| Group | Items | Methods |
| :- | :- | :- |
| Numeric fidelity | EV-1.1 to 1.3 | Auto, Auto, Human |
| Data reliability | EV-2.1 to 2.4 | Auto |
| Detection | EV-3.1 to 3.4 | Auto (3.3 also Human) |
| Explanation | EV-4.1 to 4.5 | Auto (4.2, 4.4 also Human) |
| Calibration | EV-5.1 to 5.4 | Auto, Auto, Judge, Auto |
| Traceability | EV-6.1 to 6.3 | Auto, Auto, Human |
| Communication | EV-7.1 to 7.5 | Human or Judge; Auto and Human; Human; Auto; Auto and Human |
| Efficiency | EV-8.1 to 8.5 | Human; Auto and Human; Auto; Auto; Auto |
| Governance | EV-9.1 to 9.4 | Auto and Judge; Auto and Judge; Auto; Review |

## Key Design Points

- **User-story importer**: parses `docs/planning/user-stories.md` sections (story ID, anchor weeks, Given/When/Then, must-not-say, eval items) into case files. Each case is reviewed by hand once, then frozen; the case file, not the doc, is what runs.
- **Store**: `store.py` reads `PHARMAGENTICS_EVAL_STORE`; no other module may import it or read the variable. `isolation.py` enforces both and scans the git index for ground-truth file patterns.
- **Held-out**: sealed parameters stay in the store; opening needs an explicit flag; `regression.py` rejects target changes after the first held-out score.
- **Back-test**: `backtest.py` asks core-005 for ten consecutive weekly replays with as-of timestamps on the held-out seed.
- **N/A scoring**: each item declares which scenario families it applies to; others score N/A.

## Complexity Tracking

None.
