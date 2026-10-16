# Implementation Plan: Data Generator and Injection Library

**Branch**: `001-data-generator` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

A seeded Python generator builds one fictional brand world as linked tables, injects labeled events and feed artifacts, and writes ground truth to a separate store. The existing Day 1 v0 generator output is the reference for schema and behavior. The plan formalizes it with settings, an event registry and a scenario request format. Case building lives in the evaluation harness (spec 010).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: NumPy (seeded `Generator`), pandas or Polars, PyArrow, Pydantic (settings and answer-key schema), PyYAML
**Storage**: Parquet for tables; CSV export for the agent-visible release; a separate directory for ground truth
**Testing**: pytest; property tests for invariants
**Target Platform**: Local Windows and Linux; no services
**Project Type**: library with a command-line entry point
**Performance Goals**: Day 1 size builds in under one minute; 10x size builds in under ten minutes
**Constraints**: Deterministic by seed. No network access at generation time. No real data.
**Scale/Scope**: Day 1 is 104 weeks, 8 territories, 64 plans, 4 specialties, 4 products, about 106k observed Rx rows

Stack follows Architecture §13. The Rx sampling model is Gamma-Poisson for TRx and binomial for NRx and NBRx (Data Research Brief).

## Constitution Check

| Principle | Status |
|---|---|
| X Synthetic data only | Pass. FR-013. |
| XI Answer-key isolation | Pass. Ground truth is written to a separate store and never read back by the generator (FR-010). Case building moved to the harness. |
| IV Pinned data version | Pass. Each release carries a version and seed in its validation report. |
| II One semantic layer | Pass. Metric semantics come from spec 002. The generator only needs its field list. |
| XII Evaluation gate | Pass. Scenario requests feed the harness, which emits the Evaluation Pack case format. |

## Project Structure

```text
specs/001-data-generator/  spec.md  plan.md  tasks.md  checklists/requirements.md
src/pharmagentics/generator/
  settings.py        world settings and validation
  world.py           dimensions, baselines (trend, seasonality, holidays)
  sampling.py        TRx, NRx, NBRx sampling
  events/            one module per event type + registry
  artifacts/         restatement, coverage drop, duplicate, missing, late
  answer_key.py      answer-key schema and writer (separate store)
  scenarios.py       scenario request format (seed, events, weeks, split); no case building
  calibration.py     public-source fit and report
  cli.py
tests/unit/generator/  tests/integration/generator/
```

**Structure Decision**: One package. Each event type is a plug-in behind one registry, so adding an event type needs no change elsewhere.

## Key Design Points

- One `numpy.random.Generator` per (seed, purpose) so adding an event does not shift unrelated draws.
- The generator writes `agent_visible/` and `eval_private/` in one pass. It is write-only toward `eval_private/` and has no read path to it. Its own tests use the in-memory answer key returned by a run, not the files on disk.
- The Given/When/Then case builder lives in spec 010 (`evalharness/cases.py`) because it reads the answer key.
- The event registry exposes: type, label, ranges for magnitude, onset lag, decay, and the cut it affects. The answer key stores the realized values.
- Held-out parameters live in a sealed parameter file outside the repository's agent-visible tree.
- The calibration step is optional and records fitted versus assumed for every parameter.

## Complexity Tracking

None.
