# Implementation Plan: Competitive Intelligence

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `004-competitive-intelligence`)

## Summary

Deterministic statistics turn the governed view into KPIs and a ranked, capped list of candidate changes. Seasonality is removed first, residuals are scored robustly, and three thresholds from the semantic layer gate every flag. Peer-relative and trailing comparisons catch sustained local gaps. Coverage labels and like-for-like comparisons keep partial weeks honest. Multiple-testing control is tuned on dev null weeks.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: DuckDB (cut aggregation over the governed view), pandas or Polars, NumPy, SciPy, statsmodels (STL); optional change-point library; core-002, core-003, core-004
**Storage**: `runtime.candidate_changes` and a per-run KPI table
**Testing**: pytest; anchor-week fixtures from `day1-v1`; recall and false-alarm harness from core-006
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: `day1-v1` week in seconds; a 10× world in under a minute
**Constraints**: No LLM. Deterministic. Reads only the governed view
**Scale/Scope**: `day1-v1`: 8 territories × 4 channels × 64 plans × 4 specialties × 4 products at leaf level

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | Candidate values become tool records cited downstream. |
| Shared IV Typed contracts | Candidates and the request are schemas (core-004). |
| Briefing B-I One semantic layer | Thresholds, impact and calendar come from core-002. |
| Briefing B-II Declared mode | Deterministic. |
| Briefing B-III Pinned version | Reads only the pinned snapshot. |
| Briefing B-VII Evaluation gate | Cites EV-3.1 to 3.4. |

## Project Structure

```text
src/pharmagentics/ci/
  kpis.py        governed KPIs, 30-day normalization, coverage labels
  baselines.py   prior week, 4-week average, same week last year, trailing 13 weeks
  peers.py       territory vs other territories, same weeks
  likeforlike.py comparisons on territories reportable in both weeks
  decompose.py   seasonality removal and residuals
  score.py       robust z-scores
  filters.py     absolute, relative and statistical thresholds; margins
  calendar.py    holiday and plan-year tags with prior-year comparison
  multitest.py   multiple-testing control (A5)
  rank.py        business impact and cap
  stage.py       writes candidates, detection summary and the one request; sets ROUTINE
tests/unit/ci/  tests/integration/ci/
```

## Key Design Points

- **Hierarchy**: national → region → territory → channel → plan, and specialty at each level. For A5, the default is hierarchical drill-down: test a child only under a parent that is flagged or whose peer-relative gap clears its threshold. False-discovery-rate control is the alternative. Tune on dev null weeks to meet SC-002; log the choice.
- **Peer-relative change**: territory change minus the change in the other territories over the same weeks. This is the same comparison the user stories use; brief-002's `compare_to_peers` then names controls and drops contaminated ones.
- **Like-for-like**: when a week pair has different reportable territories, compute on the intersection from the health report and mark `like_for_like = true`.
- **Business impact (A4)**: absolute change in TRx 30-day equivalents, defined once in core-002 so the answer key uses the same definition.
- **Calendar**: compare to the same holiday weeks in prior years when available, else to the seasonal component.
- **Share**: basket effective dates set the denominator each week, so Metacora counts from 2026-03-02.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
| :- | :- | :- |
| Peer-relative and trailing comparisons | User stories P2-Q3, P2-Q4, P4-Q1 describe sustained local gaps that no week-over-week move reveals | WoW, 4-week and same-week-last-year alone miss them |
