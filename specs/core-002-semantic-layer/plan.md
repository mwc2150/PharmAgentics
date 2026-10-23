# Implementation Plan: Semantic Layer

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `002-semantic-layer`)

## Summary

Versioned YAML files hold metrics, dimensions, rules, contracts, two lane catalogs, two lane cap sets and term lists. Pydantic models validate them on load. A small read-only API serves both lanes. The v0 gate SQL is rendered from the layer's data-contract values instead of hard-coded literals.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PyYAML, Pydantic v2; DuckDB (to read `dim_*` members)
**Storage**: YAML under `semantic_layer/`, tracked in git. Version = content hash of the file set plus a `layer_version` string
**Testing**: pytest
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Load and validate in under one second
**Constraints**: Read-only at run time. Unknown IDs always raise. Dimension members come from the database, not YAML
**Scale/Scope**: About 7 KPIs, 7 forecast metrics, 15 context metrics, 6 dimensions, two catalogs of about a dozen entries each

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | Pass. The layer holds rules and thresholds, never run-time values. |
| Shared VII Loops end by construction | Catalogs and caps live here, per lane (FR-008, FR-009). |
| Shared platform: one semantic layer | This spec is the rule. |
| Briefing B-I One semantic layer | This spec is the article. |
| Briefing B-VI No individual identified | Aggregation floor stored here (FR-012). |
| Shared III, VI | Pass. Holds no data and no ground truth. |

## Project Structure

```text
semantic_layer/
  metrics.yaml          KPIs (owner Briefing), context metrics
  metrics_forecast.yaml forecast metrics (owner Forecast)
  dimensions.yaml       week, geography, payer_channel, plan, hcp_specialty, product
  rules.yaml            materiality, basket, calendar, plan-year reset, small-cell floor
  contracts.yaml        per-table lag, gate thresholds, restatement window, owner
  catalog_briefing.yaml catalog_forecast.yaml
  caps_briefing.yaml    caps_forecast.yaml
  terms.yaml            governed, banned, reader_jargon, association, confidence_wording, functions
src/pharmagentics/semantic/
  models.py  loader.py  api.py  errors.py
  sql_params.py         renders gate thresholds into sql/001_reporting_views.sql
tests/unit/semantic/  tests/contract/semantic/
```

**Structure Decision**: One file per concern, with lane-owned files split out so each team edits only its own. Config at the repo root; code in the package.

## Entry Shapes

Metric (from Briefing Architecture §7.1, extended): `metric, label, kind, definition, not_to_be_confused_with, grain, source, lineage, refresh, rounding, materiality{abs_min, rel_min, z_min}, allowed_phrases, banned_phrases, owner`.

Context metrics, read by tool:

| Context metric ID | Source | Read by tool |
| :- | :- | :- |
| `days_supply_90day_share` | `rx_weekly.share_90day_fills_proxy` | `get_metric` |
| `inventory_fill_rate`, `distribution_backorder_rate` | `inventory_weekly` | `lookup_inventory` |
| `rep_calls_aggregated`, `digital_impressions`, `samples_units`, `speaker_programs`, `rep_vacancy_count_aggregated` | `promo_activity` | `lookup_promo` (floor applies) |
| `covered`, `formulary_tier`, `prior_authorization`, `step_therapy`, `quantity_limit`, `covered_lives_weight` | `access_status_monthly` | `lookup_access_events` |

Briefing catalog examples: `inventory` → `lookup_inventory` with `inventory_fill_rate`, `distribution_backorder_rate`; `days_supply_shift` → `get_metric` with `days_supply_90day_share`, `trx_30day_equivalent`; `promotion` → `lookup_promo` with all promotion context metrics.

## Proposed Starting Values (tune on dev seeds)

| Setting | Starting value | Source |
| :- | :- | :- |
| Panel coverage band | 0.98 to 1.0 | v0 gate (built) |
| Lag tolerance | target + 1 day | v0 gate (built) |
| Expected schema | `rx_v1` | v0 gate (built) |
| Restatement window | 3 weeks, flag-and-disclose beyond it | Briefing §5.1; S4 open |
| Small-cell floor | 50 TRx per week per cut | Proposed from P4-Q2 (cash cells are 36 to 49) |
| Briefing rounds per run | 20 | Oct 16 plan |
| Briefing stalls | 3 per story | Oct 16 plan |
| Briefing tool calls per story | 25 | Oct 16 plan |
| Briefing Data Forensics calls per story | 6 | Oct 16 plan |
| Briefing wall clock | 15 minutes per run | Oct 16 plan |
| Briefing brief length | 600 words, excluding tables and glossary | Oct 16 plan |
| Forecast rounds | 8 | `MAX_INVESTIGATOR_STEPS` in feagent |

## Key Design Points

- `api.get_metric(id)` raises `UnknownMetricError`. Managers treat it as a tool error.
- Glossary text is taken straight from `definition` and `not_to_be_confused_with`.
- `terms.yaml` scopes each phrase: "new patients" allowed only for `nbrx`; reader jargon banned only in reader-facing sections, allowed in evidence and appendix text.
- Gate parameters: `sql_params.py` renders the coverage band, lag tolerance and schema version into the view SQL at load time, so core-003 needs no literals. The loader keeps working with default values if the layer is absent (backward compatible with PR #1).

## Complexity Tracking

None.
