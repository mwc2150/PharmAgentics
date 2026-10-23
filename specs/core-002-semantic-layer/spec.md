# Feature Specification: Semantic Layer

**Spec ID**: `core-002-semantic-layer` (shared; owners: both teams. Briefing owns Rx metrics, Forecast owns forecast metrics)
**Feature Branch**: `speckit-briefing`
**Created**: 2026-10-16 | **Updated**: 2026-10-23
**Status**: Draft v2. Not started.
**Replaces**: `002-semantic-layer` (Oct 16)
**Input**: System Architecture §3.2, §4c, §6, S4, S5, S8, S10; Briefing Architecture §2 (principle 2), §7.1, §10; Evaluation Pack EV-9.2, open items 5, 17, 18; `data/agent_visible/data_dictionary.json`; `sql/001_reporting_views.sql`; User stories P1-Q6, P3-Q3, P4-Q1, P4-Q2

## Context

One set of versioned YAML files, validated on load, defines every metric, dimension, threshold, catalog entry, cap and governed term for both agents (System §3.2). The release's `data_dictionary.json` seeds it. The v0 gate's thresholds are hard-coded in `sql/001_reporting_views.sql` today ("provisional Day 1 rules, not yet the governed metrics"); this spec moves them into the layer.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One definition for every metric (Priority: P1)

A component asks the layer what a metric means and how to cut it. It gets one answer: label, definition, what it is not to be confused with, source field, grain, refresh rule, rounding, materiality thresholds, allowed and banned phrases, and owner. A metric or dimension the layer does not hold is rejected with an error.

**Why this priority**: Every tool, prompt and check depends on it. A second definition anywhere is a risk to numeric fidelity.

**Independent Test**: Ask for every Rx and forecast field in the data dictionary, then a made-up ID. The first return full entries; the last raises.

**Acceptance Scenarios**:

1. **Given** every field of `rx_weekly` and `forecast_vs_actual_weekly`, **When** the layer is checked, **Then** each has a metric entry or is listed as a non-metric (keys, labels, `source`).
2. **Given** an unknown metric ID or dimension, **When** any tool asks for it, **Then** the layer raises an error the caller must handle.
3. **Given** NRx and NBRx, **When** their entries are read, **Then** each says what it is not to be confused with, and only NBRx allows "new patients" (user story P1-Q6).
4. **Given** the Forecast metrics, **When** they are read, **Then** `variance_trx` is defined as A − F and `variance_pct` as (A − F) / F, with the locked forecast as denominator (user story FM-Q1).

---

### User Story 2 - Rules in one place (Priority: P1)

A data owner changes a materiality threshold, a gate threshold, a loop cap, the restatement window or the small-cell floor in one file. Every consumer sees the change on the next run, and the run records the layer version it used.

**Why this priority**: Thresholds and caps drive detection precision, gate behavior and run cost. They must be tunable without code changes.

**Independent Test**: Change the panel-coverage floor. Rebuild the gate. Check the set of withheld cuts changes and the run records the new layer version.

**Acceptance Scenarios**:

1. **Given** a changed threshold, **When** the next run starts, **Then** it records the new layer version.
2. **Given** the gate's coverage, lag and schema rules, **When** the gate builds, **Then** it reads them from the layer, and the `day1-v1` artifacts are still withheld with the default values.
3. **Given** an invalid layer file (missing field, wrong type, bad value), **When** it loads, **Then** loading fails and names the file and field.

---

### User Story 3 - Governed wording and glossary (Priority: P2)

The narrative writer receives only the definitions of the metrics in play. The verifier checks wording against allowed, banned and reader-jargon terms. Each brief gets a glossary built from the layer.

**Why this priority**: Terminology is an eval item (EV-9.2) and a mentor directive. Plain language is what P3 repeats upward (P3-Q3).

**Independent Test**: Build a glossary for TRx and NBRx. Scan the term lists.

**Acceptance Scenarios**:

1. **Given** a set of metric IDs, **When** a glossary is requested, **Then** it holds exactly those definitions, taken from the layer.
2. **Given** the banned-term list, **When** it is read, **Then** it holds "statistical surveillance" and "surveillance" (S8), and "new patients" is allowed only for NBRx.
3. **Given** the reader-jargon list, **When** it is read, **Then** it holds method terms that must stay out of reader-facing prose, such as "difference-in-differences" and "fill-rate elasticity" (user story P3-Q3).
4. **Given** the association wording list, **When** promotion findings are worded, **Then** only association phrasing is allowed (user story P4-Q1: "not 'promotion caused a 120 TRx lift'").

---

### User Story 4 - Hypothesis catalogs, caps and shared use (Priority: P2)

Each lane's investigation specialists draw hypotheses only from that lane's catalog, and run under that lane's caps. Both catalogs and both cap sets live in the layer. The Forecast team adds and owns its entries.

**Why this priority**: A finite catalog is one of the guarantees that loops end (shared Principle VII).

**Independent Test**: List each lane's catalog. Check every driver label in that lane's eval pack is in it, and every entry names a tool that exists.

**Acceptance Scenarios**:

1. **Given** the Briefing catalog, **When** a specialist asks for hypotheses, **Then** it gets only catalog entries: access, promotion, competitor, inventory (S5, proposed), rep vacancy, segment or geography mix, days-supply shift; plus artifact types and calendar effects.
2. **Given** a new Forecast metric or catalog entry, **When** it is added, **Then** no Briefing entry, threshold or cap changes.
3. **Given** the caps, **When** they are read, **Then** each lane has its own set: Briefing per Evaluation Pack open item 17; Forecast's round cap is 8 today.

### Edge Cases

- A metric exists but its source field is missing from the loaded week: the layer reports the gap, not a default.
- Two files define the same metric ID: loading fails. IDs are unique across both lanes.
- A threshold is zero or negative, or a coverage band has min above max: loading fails.
- A phrase is both allowed and banned: loading fails.
- `market_share` in the release is share of a fictional four-brand basket, not a national market share: its definition says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The layer MUST hold, per metric: ID, label, definition, not-to-be-confused-with, kind (KPI, context or forecast), grain, source table and field, lineage, refresh rule, rounding rule, materiality thresholds (absolute, relative, statistical) for KPIs, allowed phrases, banned phrases and owner.
- **FR-002**: Briefing KPIs MUST cover TRx, NRx, NBRx, TRx in 30-day equivalents, market share and NBRx share, and business impact once defined (brief-001, A4).
- **FR-003**: Forecast metrics MUST cover `forecast_trx`, `actual_trx`, `variance_trx`, `variance_pct`, `horizon_weeks`, `actual_is_provisional` and the locked-version key `forecast_issue_week` (System §3.2; Forecast lane, Alvin and Sienna confirm).
- **FR-004**: Context metrics MUST cover every field an investigation tool returns: days-supply mix (`share_90day_fills_proxy`), inventory (`inventory_fill_rate`, `distribution_backorder_rate`), promotion (`rep_calls_aggregated`, `digital_impressions`, `samples_units`, `speaker_programs`, `rep_vacancy_count_aggregated`) and access (`covered`, `formulary_tier`, `prior_authorization`, `step_therapy`, `quantity_limit`, `covered_lives_weight`). Context metrics carry no materiality thresholds.
- **FR-005**: Dimensions MUST cover week, geography (region to territory), payer channel (commercial, Medicare Part D, Medicaid, cash), plan (within territory and channel), HCP specialty and product. Members come from the `dim_*` tables, never from the layer files.
- **FR-006**: Business rules MUST cover materiality thresholds per KPI, the market basket with effective dates, the holiday calendar, plan-year resets, and the small-cell floor below which a cut is flagged as noisy and not generalized from (user story P4-Q2).
- **FR-007**: Data contracts MUST cover, per source table: expected lag, the feed-health thresholds (panel coverage band 0.98 to 1.0, lag tolerance of one day beyond target, expected schema version `rx_v1`), the restatement window and the owner. [NEEDS CLARIFICATION: restatement window value; the release restates 14 weeks after the fact, Briefing proposes 3 (System S4, Evaluation Pack item 18)]
- **FR-008**: Each lane's hypothesis catalog MUST list driver categories, artifact types and calendar effects. Each entry MUST name the tools and context metrics that test it. A contract test MUST fail for an entry with no tool, or a tool the registry does not hold.
- **FR-009**: Each lane's cap set MUST hold: rounds per run, stalls, tool calls per story, Data Forensics calls per story, wall-clock time, token budget and output length. [NEEDS CLARIFICATION: Briefing cap values (Evaluation Pack open item 17); plan proposes starting values to tune on dev seeds]
- **FR-010**: Governed terms MUST include the banned terms ("statistical surveillance", "surveillance"), the NBRx-only "new patients" rule, a reader-jargon list, association-only wording for promotion, and the confidence-to-wording map (causal wording only at High).
- **FR-011**: The layer MUST hold the list of functions a story can name as "who to involve": market access, sales leadership, sales operations, marketing, finance, forecasting, supply chain and trade, and the data vendor.
- **FR-012**: The layer MUST hold the aggregation floor for rep-level activity. [NEEDS CLARIFICATION: minimum aggregation level (Evaluation Pack open item 5)]
- **FR-013**: The layer MUST reject unknown metric IDs and dimensions with an error, and MUST validate on load, naming the file and field on failure.
- **FR-014**: The layer MUST be versioned (content hash plus a human version). Every run of either lane MUST record the layer version it used.
- **FR-015**: The layer MUST provide a glossary for any set of metric IDs.
- **FR-016**: The layer MUST NOT assume a fixed number of territories, regions, plans, specialties, products or weeks.

### Key Entities

- **Metric entry**: one governed KPI, context or forecast metric (FR-001).
- **Dimension entry**: one cut and its hierarchy.
- **Business rule**: thresholds, basket, calendar, plan-year rule, small-cell floor.
- **Data contract**: source, lag, gate thresholds, restatement window, owner.
- **Catalog entry**: a driver, artifact type or calendar effect, per lane, with the tools that test it.
- **Cap set**: one lane's loop limits.
- **Term lists**: governed, banned, reader-jargon, association, functions to involve.
- **Layer version**: content hash plus human version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of metric fields in `rx_weekly` and `forecast_vs_actual_weekly` have an entry.
- **SC-002**: 100% of unknown-ID requests raise. None return a default.
- **SC-003**: A changed threshold takes effect on the next run with no other file edited, including the gate's thresholds.
- **SC-004**: 100% of runs in both lanes record the layer version.
- **SC-005**: Zero banned terms in any glossary, prompt or project document, outside text that lists them as banned.
- **SC-006**: Every driver label in each lane's eval pack is in that lane's catalog.
- **SC-007**: 100% of catalog entries name an existing tool, and 100% of fields any tool returns have an entry.

## Assumptions

- The layer is configuration, not code. Changes are reviewed like specs.
- The Forecast team adds its own files or entries with its own `owner`; Briefing does not edit them.
- Materiality values in Briefing Architecture §7.1 are illustrative until tuned on dev null weeks.
- Heavier tooling (dbt, MetricFlow) stays out unless a need appears.
