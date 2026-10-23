# Implementation Plan: Tool Interface and Handoff Contracts

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `005-tool-contracts`)

## Summary

Pydantic models define every handoff object and the shared `tool_record`. Tools are plain Python functions over the governed view. One registry wraps every tool call: it checks IDs against the semantic layer, enforces the allowlist and aggregation floor, opens a span, writes the tool record and maps errors to types. JSON Schema export gives both lanes and the harness a language-neutral contract.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic v2, DuckDB, core-002 API, core-003 governed view, OpenTelemetry API (spans)
**Storage**: `runtime.evidence_items` table keyed by `run_id`, `record_id`; JSON Schemas in `specs/core-004-tool-handoff-contracts/contracts/` (generated)
**Testing**: pytest; contract tests with valid samples and one mutation per required field; probe tests
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: A tool call returns in under one second on `day1-v1`
**Constraints**: No model in any tool. Read-only. Allowlist enforced in the data-access layer, not in prompts
**Scale/Scope**: Ten Briefing tools; about twelve schemas

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | Tools are the source; every call writes a record. |
| Shared III Answer-key isolation | Allowlist and probe tests (FR-010). |
| Shared IV Typed contracts | This spec is the principle; contract versioning (FR-014). |
| Shared VII Loops end | Tools hold no model and cannot call agents. |
| Briefing B-IV Traceable | Every record carries a span ID. |
| Briefing B-VI No individual identified | Floor applied inside tools (FR-009). |

## Project Structure

```text
src/pharmagentics/contracts/
  tool_record.py  candidate.py  health.py  request.py  story.py  hypothesis.py
  result.py  claim.py  review.py  run.py
  export_schemas.py        → specs/core-004-tool-handoff-contracts/contracts/*.json
src/pharmagentics/tools/
  registry.py     ID check, allowlist, span, tool record, error mapping
  access.py       the only data-access path; refuses the ground-truth store and unknown paths
  aggregation.py  rep-level floor; BelowFloor
  smallcell.py    small-cell flag
  get_metric.py  decompose_change.py  compare_to_peers.py  validate_feed.py
  lookup_access_events.py  lookup_promo.py  lookup_inventory.py
  compare_competitors.py  lookup_calendar.py  reconcile_numbers.py
tests/contract/  tests/unit/tools/
```

**Structure Decision**: One module per tool and one wrapper in `registry.py`. The allowlist is a data-access concern, so it lives in `access.py` and is also tested from outside.

## Briefing Tool Summary

| Tool | Answers | Reads |
| :- | :- | :- |
| `get_metric` | A governed metric for a cut and weeks | governed Rx view, market share |
| `decompose_change` | Contribution of each territory, channel, plan, specialty | governed Rx view |
| `compare_to_peers` | Exposed cut vs other territories, same weeks, control set named | governed Rx view, catalog of active events |
| `validate_feed` | Gate result and reasons for a cut and week | health report |
| `lookup_access_events` | Formulary changes for a plan, product and months | `access_status_monthly`, `dim_plan` |
| `lookup_promo` | Aggregated promotion activity for a territory, product, weeks | `promo_activity` (floor applies) |
| `lookup_inventory` | Fill and backorder rates (S5, Proposed) | `inventory_weekly` |
| `compare_competitors` | Competitor share and launches | `market_share_weekly`, `market_basket` |
| `lookup_calendar` | Holidays, business days, plan-year reset | `calendar` |
| `reconcile_numbers` | A value checked against the pinned snapshot | governed Rx view |

## Key Design Points

- **Shared tool record (S9 proposal)**: one model with a `lane` field. Briefing reads it as `evidence_item`; Forecast's evidence log is a list of the same records. Field-name mapping is in [data-model.md](data-model.md).
- **Ground-truth store**: `access.py` refuses any path under `PHARMAGENTICS_EVAL_STORE` and refuses to read that variable at all. The probe test sets the variable to a temp folder and checks every tool is refused.
- **Floor**: promotion results return at territory level or above. A vacancy count below the floor returns `BelowFloor` with the reason.
- **Control set**: `compare_to_peers` takes the story's exposed cut and window, drops territories with their own active event (from candidate changes, access, inventory and promotion lookups), and returns the control set it used.
- **Framework (A3)**: tools are plain callables with Pydantic signatures, so ADK, Microsoft Agent Framework or custom Python can register them through a thin adapter.

## Complexity Tracking

None.
