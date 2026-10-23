# Data Model: Runtime, Handoff, Evidence and Review Objects

**Spec**: [spec.md](spec.md) | **Date**: 2026-10-23

Every object below is a Pydantic model and is exported as JSON Schema to `specs/core-004-tool-handoff-contracts/contracts/` (generated, not hand-written). Grain and key fields follow Briefing Architecture §7.3. Field names for data follow `data/agent_visible/data_dictionary.json`. Objects prefixed `briefing.` or `forecast.` collide by name across lanes (System Architecture §6).

## Shared

### tool_record (shared core; Proposed answer to S9)

| Field | Type | Notes |
| :- | :- | :- |
| record_id | str | Unique per run. Briefing calls it `evidence_id`; Forecast calls it `tool_id` |
| run_id | str | |
| lane | enum `briefing`, `forecast` | |
| tool | str | Registry name |
| parameters | object | Briefing "parameters"; Forecast "arguments" |
| result | object | Briefing "result"; Forecast "payload" |
| snapshot_id | str | Release fingerprint + as-of timestamp (core-003) |
| source_reference | str | Tables and filters read |
| span_id | str or null | Briefing always sets it; Forecast may leave it null until it traces with spans |
| qualification | list[str] | Gate reasons or small-cell flag, if any |
| created_at | datetime | |

Lane views: `evidence_item` (Briefing) = `tool_record` with `lane = briefing`; the Forecast evidence log is a list of `tool_record` with `lane = forecast`.

### run_registry (owned by core-005, pins by core-003)

`run_id`, `lane`, `trigger` (monday, manual, flagged_miss, request), `week_start`, `as_of`, `current_state`, `started_at`, `ended_at`, `release_id`, `import_fingerprint`, `snapshot_id`, `layer_version`, `model_id`, `prompt_version`, `code_version`, `forecast_issue_week` (Forecast only), `horizon_weeks` (Forecast only), `cost_usd`, `tokens`, `wall_seconds`.

### state_transition (core-005)

`run_id`, `from_state`, `to_state`, `at`, `reason`.

### health_report (core-003)

| Field | Type | Notes |
| :- | :- | :- |
| run_id, snapshot_id | str | |
| cuts | list[cut_result] | One per week × territory |
| coverage | list[coverage_entry] | Per week: reportable territories, count, total |
| comparable_sets | list | Per compared week pair: territories reportable in both |
| restatements | list[restatement_record] | Since the previous run of the lane |
| forecast_fitness | list[forecast_fitness] | Forecast lane only |
| state | enum VALIDATED, VALIDATION_WARNING, VALIDATION_FAILED | |

`cut_result`: `week_start`, `territory_id`, `result` (pass, warn, fail), `reasons` (v0 codes, e.g. `MISSING_RX_KEYS`, `DUPLICATE_RX_KEYS`, `ROW_COUNT_MISMATCH`, `LOW_OR_INVALID_COVERAGE`, `LATE_OR_UNKNOWN_DELIVERY`, `SOURCE_NOT_COMPLETE`, `UNKNOWN_SCHEMA`, `RESTATEMENT_REVIEW`, `INVALID_RX_METRICS`, `MISSING_FEED_METADATA`, `DUPLICATE_FEED_METADATA`, `UNEXPECTED_CUT`), `evidence` (counts, coverage, lag), `thresholds`.

`restatement_record`: `week_start`, `territory_id`, `plan_id`, `hcp_specialty`, `product_id`, `metric`, `prior`, `revised`, `revised_at`, `reason`, `in_window`.

`forecast_fitness`: `week_start`, `territory_id`, `status` (fit, provisional, restated), `version_match` (bool).

## Briefing lane

### candidate_change (brief-001)

`run_id`, `candidate_id`, `metric_id`, `cut` (territory, payer_channel, plan_id, hcp_specialty, product_id; any may be "all"), `week_start`, `actual`, `baselines` (prior_week, avg_4wk, same_week_last_year, trailing_13wk, peers), `abs_change`, `rel_change`, `anomaly_score`, `business_impact`, `calendar_tag` (none, holiday, plan_year_reset), `thresholds_cleared` (with margins), `coverage_label` (e.g. "7 of 8 territories"), `like_for_like` (bool), `evidence_ids`.

### briefing.investigation_request (brief-001 → brief-002)

`run_id`, `request_id`, `candidates` (all of the run), `history_weeks`, `health_report_ref`, `evidence_ids`, `prior_story_refs` (from episodic memory).

### story (brief-002)

`run_id`, `story_id`, `candidate_ids`, `label` (real_change, data_artifact, calendar_effect, unresolved), `confidence` (High, Medium, Low), `leading_driver` (catalog ID or none), `concentration` (territory, channel, plan, specialty), `continuity` (new, continuing; improving, worsening, flat; weeks_running), `investigate_next`, `function_to_involve` (from core-002 list), `closure_reason` (closed, cap_rounds, cap_stalls, cap_tools, cap_time, cap_tokens), `comparison` (method, control_set, dropped_controls), `promotion_context_ref`.

### hypothesis (brief-002)

`run_id`, `story_id`, `hypothesis_id`, `driver` (catalog ID), `parameters`, `verdict` (supported, ruled_out, insufficient_evidence), `evidence_ids`, `tested_by` (specialist), `round`.

### briefing.investigation_result (brief-002 → brief-003)

`run_id`, `request_id`, `stories`, `hypotheses`, `contributions` (per story: segment → value, sum, total), `uncertainty_notes`, `evidence_ids`, `ledger_snapshot_refs`.

### brief_claim (brief-003, status by brief-004)

`run_id`, `claim_id`, `token` (e.g. `{{c17}}`), `claim_text`, `evidence_ids`, `metric_id`, `rounding`, `confidence`, `section`, `verification_status` (pending, pass, fail, flagged), `failure_tag`.

### analyst_review (brief-005)

`run_id`, `reviewer_role` (P1, P2), `decision` (approve, edit, return, sign_off), `edits` (claim_id, before, after), `comments`, `failure_tag` (one per edit; Briefing tag list until S10), `minutes`, `at`.

## Forecast lane (reference only; owned by Alvin and Sienna)

`forecast.InvestigationRequest` and `forecast.InvestigationReport` are defined in the `feagent` package on branch `alvin-forecast-explanation` (`feagent/schema.py`). The report's analyst-reviewable content follows Forecast Personas & Eval Design §3.7: case ID and pinned versions; signed absolute and percent variance with affected cuts; data-quality checks and limits; ranked driver hypotheses with supporting and contradicting evidence; contributions and signed residual where identifiable; assumptions, confidence and uncertainty; follow-up checks with owners; tool references and review status. A Briefing-originated request sets `source: "briefing_agent"` (System §5).

## Relationships

```text
run_registry 1─* state_transition
run_registry 1─1 health_report
run_registry 1─* candidate_change ─* briefing.investigation_request (one per run)
briefing.investigation_request 1─1 briefing.investigation_result
briefing.investigation_result 1─* story 1─* hypothesis *─* evidence_item (tool_record)
story 1─* brief_claim *─* evidence_item
run_registry 1─* analyst_review
evidence_item ─ span (core-006 tracing)
```
