# Implementation Plan: Semantic Layer

**Branch**: `002-semantic-layer` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Versioned YAML files hold metrics, dimensions, rules, contracts, the hypothesis catalog, caps and governed terms. Pydantic models validate them on load. A small read-only API serves every other component. Nothing else defines a metric.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PyYAML, Pydantic v2
**Storage**: YAML files under `semantic_layer/`, tracked in the repository; version is the file-set content hash plus a `layer_version` string
**Testing**: pytest
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Load and validate in under one second
**Constraints**: Read-only at run time. Unknown IDs always raise.
**Scale/Scope**: Six KPI metrics, about 20 context metrics, four dimensions, a dozen catalog entries at launch

## Constitution Check

| Principle | Status |
|---|---|
| II One semantic layer | This spec is the principle. |
| I Every number from a tool | The layer holds no run-time numbers, only thresholds. |
| VII Bounded loops | Catalog and caps live here (FR-006, FR-007). |
| IX No individual identified | Aggregation floor stored here (FR-014). |
| X, XI | Pass. Holds no data and no answer-key content. |

## Project Structure

```text
semantic_layer/
  metrics.yaml  dimensions.yaml  rules.yaml  contracts.yaml
  catalog.yaml  caps.yaml  terms.yaml
src/pharmagentics/semantic/
  models.py     Pydantic models for every file
  loader.py     load, validate, hash, version
  api.py        get_metric, get_dimension, list_catalog, caps, glossary
  errors.py     UnknownMetricError, UnknownDimensionError, LayerValidationError
tests/unit/semantic/  tests/contract/semantic/
```

**Structure Decision**: Config in YAML at the repo root, code in the package. Domain experts edit YAML only.

## Metric Entry Shape

The Architecture §7.1 `nbrx` entry is the model. Fields: `metric, label, definition, not_to_be_confused_with, grain, source, lineage, refresh, materiality{abs_min, rel_min, z_min}, allowed_phrases, banned_phrases, owner`.

## Context Metrics and Catalog Binding

Context metrics use the same entry shape with `kind: context`, no `materiality`, and a `source` table and field. Starting set:

| Context metric ID | Source field | Table | Read by tool |
|---|---|---|---|
| `days_supply_90day_share` | `share_90day_fills_proxy` | rx_weekly | `get_metric` |
| `inventory_fill_rate`, `distribution_backorder_rate` | same names | inventory_weekly | `lookup_inventory` |
| `rep_calls_aggregated`, `digital_impressions`, `samples_units`, `speaker_programs`, `rep_vacancy_count_aggregated` | same names | promo_activity | `lookup_promo` (aggregated; floor applies) |
| `covered`, `formulary_tier`, `prior_authorization`, `step_therapy`, `quantity_limit`, `covered_lives_weight` | same names | access_status_monthly | `lookup_access_events` |

Each catalog entry carries `tests: [tool names]` and `context_metrics: [IDs]`. Examples: `inventory` → `lookup_inventory`, `inventory_fill_rate`, `distribution_backorder_rate`. `days_supply_shift` → `get_metric`, `days_supply_90day_share`, `trx_30day_equivalent`. A contract test in spec 005 checks every `tests` name against the tool registry.

## Proposed Starting Cap Values (to tune on dev seeds; FR-015)

| Cap | Starting value |
|---|---|
| Investigation rounds per run | 20 |
| Stalls (rounds with no new verdict) | 3 per story |
| Tool calls per story | 25 |
| Data Forensics calls per story | 6 |
| Wall-clock per run | 15 minutes |
| Brief length | 600 words, excluding tables and glossary |

These are guesses. The eval harness tunes them, and Evaluation Pack open item 17 settles them.

## Key Design Points

- `api.get_metric(id)` raises `UnknownMetricError`. Callers must handle it. The manager treats it as a tool error.
- The glossary builder takes metric IDs and returns text taken straight from `definition` and `not_to_be_confused_with`.
- `terms.yaml` holds governed and banned terms with a `scope` (for example, "new patients" allowed only for the `nbrx` metric).
- The Forecast team adds files or entries with their own `owner`. A metric ID is unique across all files.

## Complexity Tracking

None.
