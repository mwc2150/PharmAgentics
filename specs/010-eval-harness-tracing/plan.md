# Implementation Plan: Evaluation Harness and Tracing

**Branch**: `010-eval-harness-tracing` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

A harness module is the only code allowed to read ground truth. It runs any version on a case set, scores the 35 eval items by their methods, logs one experiment, and builds the scorecard and failure catalog. OpenTelemetry spans viewed in Arize Phoenix provide tracing and claim provenance.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest; OpenTelemetry SDK; Arize Phoenix (experiments and trace viewer); DuckDB; pandas or Polars; Pydantic; scikit-learn or SciPy for confusion matrices and agreement statistics
**Storage**: Experiment and scorecard tables; failure catalog table; sealed held-out parameter store (outside the agent-visible tree); gold briefs as files
**Testing**: pytest for the harness itself; planted-reader and planted-regression tests
**Target Platform**: Local; Phoenix runs locally
**Project Type**: library with a command-line entry point
**Performance Goals**: Dev split (about 40 cases × reruns) completes within a budget set by cost, not by code
**Constraints**: Black-box scoring only (brief plus evidence). No dependency on model, framework or orchestration. Only `evalharness` imports ground truth.
**Scale/Scope**: About 55 cases, five reruns, four versions

## Constitution Check

| Principle | Status |
|---|---|
| V Traceable | This spec provides spans and links. |
| X Synthetic data only | Harness data is synthetic. A data-inventory review item (EV-9.4) is a manual check. |
| XI Answer-key isolation | This spec enforces it with a scan and a probe. |
| XII Evaluation gate | This spec is the principle: regressions block merge; targets never loosen after held-out. |
| IV Pinned data version | Every score references the run's pinned snapshot. |

## Project Structure

```text
src/pharmagentics/evalharness/
  cases.py        build Given/When/Then cases from the answer key and scenario requests; dev and held-out; sealed access log
  runner.py       run a version on cases with reruns; collect briefs and evidence
  items/          one module per eval group (numeric, reliability, detection, explanation,
                  calibration, traceability, communication, efficiency, governance)
  scorecard.py    versions by dimensions
  failures.py     failure tags and catalog
  rubric.py       human scoring sheets and anchors
  agreement.py    judge-human agreement
  ablation.py     manager-off comparison and trajectory diversity
  regression.py   gated-item regression and target-loosening guard
  isolation.py    import and path scan, runtime probe
  backtest.py     ten-week back-test and course-floor outputs
  cli.py          one command to run the suite
src/pharmagentics/tracing/
  spans.py        span helpers, attribute names
  provenance.py   claim token to evidence to span URL
  phoenix.py      experiment logging
tests/unit/evalharness/  tests/integration/evalharness/  tests/eval/
```

**Structure Decision**: The harness lives in its own package so one import rule keeps the answer key sealed. Items are separate modules so adding or tightening one needs no change elsewhere.

## Eval Item Methods (from Evaluation Pack §3)

| Group | Items | Methods |
|---|---|---|
| Numeric fidelity | EV-1.1 to 1.3 | Auto, Auto, Human |
| Data reliability | EV-2.1 to 2.4 | Auto |
| Detection | EV-3.1 to 3.4 | Auto (3.3 also Human) |
| Explanation | EV-4.1 to 4.4 | Auto (4.2, 4.4 also Human) |
| Calibration | EV-5.1 to 5.4 | Auto, Auto, Judge, Auto |
| Traceability | EV-6.1 to 6.3 | Auto, Auto, Human |
| Communication | EV-7.1 to 7.4 | Human or Judge; Auto and Human; Human; Auto |
| Efficiency | EV-8.1 to 8.5 | Human; Auto and Human; Auto; Auto; Auto |
| Governance | EV-9.1 to 9.4 | Auto and Judge; Auto and Judge; Auto; Review |

## Key Design Points

- **Isolation test**: a static import and path scan fails if any module outside `evalharness` reads `eval_private`, the answer-key store or counterfactual files. The generator's writer module is the only allowed non-harness reference, and only for writing. A runtime probe repeats the check against the live tool layer (works with spec 005 T022).
- **Held-out discipline**: sealed parameters and an access log. Opening requires an explicit evaluator flag. Scores are written before any change. `regression.py` rejects any target change made after the first held-out score.
- **Reruns**: five per case, configurable. Mean and spread reported. Variance is a finding.
- **Back-test**: ten consecutive weeks on a held-out seed; outputs the four course-floor items.
- **Tracing**: spans use one attribute vocabulary. `provenance.py` builds the link the review UI opens (spec 009).
- **Phoenix experiments** compare manual, scripted, low-code and custom-agent versions on the same cases.

## Complexity Tracking

None.
