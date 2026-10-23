# Implementation Plan: Load, Pin and Validation Gate

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `003-validation-gate`)

## Summary

Keep the v0 SQL gate as the core of stage 2 and wrap it: thresholds come from the semantic layer, an as-of layer of DuckDB views rebuilds any earlier snapshot from the one release, and a typed health report carries reasons, evidence and territory coverage to later stages. Stage 1 writes the run registry row with every pin.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: DuckDB 1.5.6, Pydantic v2, core-002 API
**Storage**: `local/pharmagentics.duckdb`. New schema `snapshot` holds as-of views parameterized by `as_of`; `run_registry` and `health_report` tables in a `runtime` schema
**Testing**: pytest; `day1-v1` artifacts as fixtures; dev-world artifacts from core-001
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: A `day1-v1` week validates in seconds
**Constraints**: Deterministic. No LLM. Later stages never read `raw` for metrics
**Scale/Scope**: 832 week × territory cuts in `day1-v1`

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | The governed view is the only metric source; the health report is evidence. |
| Shared IV Typed contracts | Health report and run registry row are schemas (core-004). |
| Shared platform: one feed-health gate | This spec is the rule. |
| Briefing B-III Pinned data version | This spec implements it, including as-of rebuilds. |
| Briefing B-II Declared mode | Deterministic. |

## Project Structure

```text
sql/
  001_reporting_views.sql     built: v0 gate (thresholds rendered from core-002)
  002_snapshot_views.sql      new: as-of views over raw + restatement_log + feed_metadata
src/pharmagentics/validation/
  pin.py           run registry row, version pins, snapshot ID
  snapshot.py      as-of view selection; immutability check
  report.py        HealthReport, CutResult, RestatementRecord, ForecastFitness
  coverage.py      territory coverage of totals; like-for-like territory sets
  forecast.py      provisional, restated and version-match checks (Forecast lane)
  gate.py          runs the view checks, builds the report, returns next state
tests/unit/validation/  tests/integration/validation/
```

**Structure Decision**: The checks stay in SQL, where they already run and are tested; Python reads their output into a typed report. No check is reimplemented.

## Key Design Points

- **Snapshot ID** = release manifest fingerprint + as-of timestamp (UTC). Two runs with the same pair read identical numbers by construction.
- **As-of rebuild**: for each Rx key, if `restatement_log.revised_at > as_of`, use the `*_prior` values; a cut whose `feed_metadata.loaded_at_utc > as_of` is not yet delivered; `RESTATEMENT_REVIEW` applies only to restatements recorded on or before `as_of`. Today's snapshot (as of the latest load) equals the v0 views.
- **Pass, warn, fail**: v0 `FLAG` maps to fail for every reason. A reason moves to warn only when core-002 defines a warn band for it.
- **Coverage**: the report lists reportable territories per week; national totals carry "N of M territories"; comparisons carry the intersection set.
- **Restatement window (S4)**: a semantic-layer setting. Restatements inside it are flagged; outside it are flagged as out of window and disclosed. Neither is applied to comparisons silently.
- **Forecast fitness**: `actual_is_provisional = 1` → provisional; any `restatement_log` row for the week × territory → restated; issue week ≠ requested → version mismatch.
- **All cuts fail**: return `VALIDATION_FAILED`; core-005 routes it (A7 proposal).

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
| :- | :- | :- |
| As-of views | The release ships one pull with restatements applied; P2-Q5 and the back-test need earlier values | Storing a copy per week duplicates the release and cannot be rebuilt for held-out worlds |
