# Implementation Plan: Tool Interface and Handoff Contracts

**Branch**: `005-tool-contracts` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Pydantic schemas define every handoff object and every tool signature. Tools are plain Python functions over the governed data view. Each returns an evidence record. A tool registry enforces the allowlist and the answer-key block, and applies rep-level aggregation before returning data.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic v2, DuckDB, pandas or Polars, spec 002 API, OpenTelemetry API (spans)
**Storage**: `evidence_items` table keyed by run ID and evidence ID; contracts as Pydantic models and exported JSON Schema under `contracts/`
**Testing**: pytest; contract tests that validate sample objects and mutations
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: A tool call returns in under one second on the Day 1 world
**Constraints**: No LLM in any tool. Read-only access. Allowlist enforced at the data-access layer, not in prompts.
**Scale/Scope**: Nine tools; about eight schemas

## Constitution Check

| Principle | Status |
|---|---|
| I Every number from a tool | Tools are the source. |
| V Traceable | Every success records an evidence item and a span ID. |
| VI Typed handoffs | This spec is the principle. |
| IX No individual identified | Aggregation inside tools (FR-010). |
| XI Answer-key isolation | Allowlist and probe test (FR-011). |
| VII Bounded loops | Tools have no LLM and cannot call other agents. |

## Project Structure

```text
src/pharmagentics/contracts/
  candidate.py  request.py  result.py  story.py  hypothesis.py  evidence.py  health.py
  export_schemas.py        writes JSON Schema into specs/005-tool-contracts/contracts/
src/pharmagentics/tools/
  registry.py     allowlist, call wrapper (span, evidence, error mapping)
  access.py       the only data-access path; refuses eval_private and unknown paths
  aggregation.py  rep-level floor
  get_metric.py  decompose_change.py  validate_feed.py  lookup_access_events.py
  lookup_promo.py  compare_competitors.py  lookup_calendar.py  reconcile_numbers.py
tests/contract/  tests/unit/tools/
specs/005-tool-contracts/contracts/   exported JSON Schemas (generated)
```

**Structure Decision**: One module per tool, one wrapper in `registry.py` that adds spans, evidence and error typing. The allowlist is a data-access concern, so it is enforced in `access.py` and also tested from the outside.

## Tool Summary

| Tool | Answers | Tables read |
|---|---|---|
| `get_metric` | Value of a governed metric for a cut and week | rx, share |
| `decompose_change` | Contribution of each cut to a change | rx |
| `validate_feed` | Feed health for a cut and week | feed metadata, restatements |
| `lookup_access_events` | Formulary changes affecting a cut | access status, plan |
| `lookup_promo` | Aggregated promotion activity | promo (aggregated) |
| `lookup_inventory` | Fill rate and backorder rate for a cut and week | inventory |
| `compare_competitors` | Competitor movement and share | share, basket |
| `lookup_calendar` | Holiday, business days, plan-year reset | calendar |
| `reconcile_numbers` | Check a value against the pinned snapshot | rx, share |

`lookup_inventory` is not in the Architecture §5.4 list. It is added because the generator injects inventory disruptions into the shared world, and the catalog lists inventory as a driver. Without the tool, a seeded inventory event could not be tested and would force an abstention by design. The days-supply mix is read through `get_metric` on the `days_supply_90day_share` context metric, so it needs no extra tool. Every tool returns only governed metric and context-metric fields (spec 002 SC-007).

## Key Design Points

- Every tool takes a snapshot ID, a metric ID and a cut. The wrapper checks IDs against the semantic layer before the tool body runs.
- Errors are typed: `UnknownMetric`, `UnknownDimension`, `SuppressedCut`, `Timeout`, `AccessDenied`, `SchemaError`.
- Aggregation floor: promotion data returns at a geography level at or above the floor. Below it, the tool returns `SuppressedCut` with the reason.
- The probe test tries every tool and the raw data-access layer against paths named in `eval_private/`, expecting `AccessDenied` each time.
- JSON Schema export gives the Forecast team and the eval harness a language-neutral contract.

## Complexity Tracking

None.
