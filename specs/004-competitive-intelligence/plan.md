# Implementation Plan: Competitive Intelligence

**Branch**: `004-competitive-intelligence` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Deterministic statistics turn the validated view into governed KPIs and a ranked, capped list of candidate changes. Seasonality is removed first, residuals are scored robustly, and thresholds come from the semantic layer. Multiple-testing control is tuned on dev null weeks.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pandas or Polars, NumPy, SciPy, statsmodels (STL decomposition); optional change-point library; DuckDB for cut aggregation
**Storage**: `candidate_changes` table keyed by run ID and candidate ID; KPI table per run
**Testing**: pytest; recall and false-alarm harness from spec 010
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Day 1 world in seconds; a 10x world in under a minute
**Constraints**: No LLM. Deterministic. Reads only the governed view.
**Scale/Scope**: Day 1 has several hundred cuts per week across the hierarchy, in the thousands at leaf level with more territories

## Constitution Check

| Principle | Status |
|---|---|
| I Every number from a tool | Pass. Stage output feeds evidence items. |
| II One semantic layer | Thresholds, baselines and impact definition come from spec 002. |
| III Declared mode | Deterministic. |
| IV Pinned data version | Reads only the pinned snapshot. |
| XII Evaluation gate | Cites EV-3.1 to 3.4. |

## Project Structure

```text
src/pharmagentics/ci/
  kpis.py           governed KPI computation, 30-day normalization
  baselines.py      prior week, 4-week average, same week last year
  decompose.py      seasonality removal and residuals
  score.py          robust z-scores
  filters.py        absolute, relative and statistical threshold filters
  calendar.py       holiday and plan-year-reset tags
  multitest.py      multiple-testing control (open: A5)
  rank.py           business impact and cap
  stage.py          orchestrates; writes candidate_changes; sets ROUTINE
tests/unit/ci/  tests/integration/ci/
```

## Key Design Points

- Business impact starts as the absolute change in TRx 30-day equivalents (proposed A4). It lives in the semantic layer so the answer key and the stage use one definition.
- Multiple-testing options for the A5 decision: hierarchical drill-down (test national, then regions, then territories only under flagged parents) or false-discovery-rate control. Tune on dev null weeks to meet SC-002. Record the choice in the decision log.
- Calendar effects: compare to the same holiday in prior years when available, else to the seasonal component. Mark `calendar_tag`.
- Same-week-last-year needs 52 weeks of history. With a shorter history the comparison is marked unavailable.
- Basket effective dates select the share denominator for each week.
- The stage returns candidates plus a detection summary (tested, flagged, dropped by cap) for the data-health footnote and the eval harness.

## Complexity Tracking

None.
