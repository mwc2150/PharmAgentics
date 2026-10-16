# Implementation Plan: Load, Pin and Validation Gate

**Branch**: `003-validation-gate` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Deterministic code stores each weekly pull as an immutable snapshot, then runs per-feed and per-cut checks and writes a health report. No LLM is involved. Downstream stages read data only through a view that applies the report's suppression and qualification flags.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: DuckDB, PyArrow/Parquet, pandas or Polars, Pydantic, spec 002 API
**Storage**: Parquet snapshots under `snapshots/<snapshot_id>/`; DuckDB views over them; `run_registry` and `health_report` as tables
**Testing**: pytest; seeded-artifact fixtures from spec 001
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: A Day 1 week validates in seconds; a 10x world in under a minute
**Constraints**: Snapshots are write-once. No network. Reads only `data/agent_visible/` style inputs.
**Scale/Scope**: Day 1 is 14 tables, about 106k Rx rows; per-cut checks over all geography, channel and specialty cuts

## Constitution Check

| Principle | Status |
|---|---|
| IV Pinned data version | This spec is the principle. |
| III Declared mode | Deterministic. Listed in the autonomy ledger. |
| VI Typed handoffs | Health report is a typed object with a schema. |
| XI Answer-key isolation | Reads only agent-visible tables. |
| II One semantic layer | All thresholds and the restatement window come from spec 002. |

## Project Structure

```text
src/pharmagentics/validation/
  snapshot.py      write-once snapshot store, content hash, ID
  loader.py        latest closed week plus history window
  checks/          schema.py missing.py rowcount.py duplicates.py coverage.py freshness.py restatement.py
  report.py        HealthReport model, per-cut results, evidence
  view.py          governed data view that applies suppression and qualification
  gate.py          orchestrates the checks, returns report and next state
tests/unit/validation/  tests/integration/validation/
```

**Structure Decision**: One module per check. Each returns `(result, evidence)`. The gate composes them. Adding a check needs no change elsewhere.

## Key Design Points

- Snapshot ID is a content hash plus a pull timestamp. A second pull never overwrites the first.
- The restatement diff compares the pinned snapshot with the previous snapshot inside the window and records old and new values.
- A cut is the product of geography, payer channel and HCP specialty at each hierarchy level the semantic layer lists. Checks run at the leaf and roll up.
- The data view returns each row with a `qualification` flag. Stage 3 and the tools never read raw tables.
- All-cuts-fail returns state `VALIDATION_FAILED`. Spec 009 maps it to the data-health notice.
- Thresholds (coverage floor, row-count tolerance, lag limit) come from the semantic layer data contracts.

## Complexity Tracking

None.
