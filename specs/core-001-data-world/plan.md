# Implementation Plan: Data World — Foundation, Generator and Injection Library

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `001-data-generator`)

## Summary

The foundation is built: `src/pharmagentics/data/load_duckdb.py` loads the 14 release files into DuckDB, `check_duckdb.py` verifies them, `sql/001_reporting_views.sql` builds the v0 gate, and `tests/test_data_load.py` runs in CI. What remains is the generator and injection library, which live in a private store outside this repository and export agent-visible releases into `data/agent_visible/`, plus the answer-key format both lanes agree on.

## Technical Context

**Language/Version**: Python 3.11+ (CI runs 3.11 and 3.12)
**Primary Dependencies**: DuckDB 1.5.6 (loader, built). Generator: NumPy seeded `Generator`, pandas or Polars, Pydantic for settings and answer-key schema
**Storage**: `local/pharmagentics.duckdb` (git-ignored) with `raw`, `metadata`, `reporting` schemas. Release CSVs in `data/agent_visible/`. Ground truth in a private store outside the repo, located by `PHARMAGENTICS_EVAL_STORE`
**Testing**: `unittest` suite today; pytest runs it unchanged (proposed answer to S15)
**Target Platform**: Local Windows, macOS, Linux; GitHub Actions on Ubuntu
**Project Type**: library with command-line entry points
**Performance Goals**: `day1-v1` loads in seconds; a 10× world generates in under ten minutes
**Constraints**: Deterministic by seed. No network at generation time. No real data. Nothing from the ground-truth store is ever committed
**Scale/Scope**: `day1-v1`: 104 weeks, 8 territories in 4 regions, 64 plans, 4 specialties, 4 products, 106,467 observed Rx rows, 6 business events, 3 feed artifacts

Rx sampling follows the Data Research Brief: Gamma-Poisson for TRx, binomial for NRx and NBRx.

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | Pass. The release and its views are the only source of numbers. |
| Shared III Answer-key isolation | Pass by design. The generator and ground truth live outside the repo (FR-013). `.gitignore` already blocks `eval_private/`, `answer_key*`, `*counterfactual*`, `*true_before_feed_artifacts*` and `heldout_*`. |
| Shared VI Synthetic data only | Pass. FR-017. |
| Shared platform: one data world | This spec is the rule. |
| Briefing B-III Pinned data version | Supported. Each release and import run is versioned and fingerprinted; core-003 builds snapshots on it. |

## Project Structure

```text
data/agent_visible/                 the release (14 CSVs, README, dictionary, validation report)
sql/001_reporting_views.sql         v0 gate and gated KPI views (built; governed by core-003)
src/pharmagentics/data/
  load_duckdb.py                    built: typed load, manifest, transactional replace
  check_duckdb.py                   built: counts, keys, quality, --json, --fail-on-flags
  release.py                        new: verify a release folder against its validation report
tests/test_data_load.py             built: 21 tests
.github/workflows/data-foundation.yml   built

Outside the repository (private store; path in PHARMAGENTICS_EVAL_STORE)
  generator/   settings.py world.py sampling.py events/ artifacts/ answer_key.py scenarios.py calibration.py cli.py
  releases/<release_id>/answer_key.*  true_rx.*  counterfactual_components.*
  heldout/<seed_id>/sealed_params.*
```

**Structure Decision**: The repository holds only what agents may see and the code that loads it. The generator lives with the answer key so its internals and parameters never reach an agent's workspace. A release is exported into the repo as a folder of CSVs, and the loader reads it by an explicit file list.

## Key Design Points

- **Already built (PR #1).** Typed schemas per table; `TABLE_KEYS` define natural keys (a restatement's key includes `revised_at`; a forecast's includes issue week and horizon); expected Rx cells come from the dimension cross product; zero-volume pre-launch cells are not missing; imports replace all tables and views in one transaction.
- **Release export.** The generator writes a release folder and its validation report. `release.py` checks a folder against its report before the loader accepts it. A new release gets a new ID; `day1-v1` is never edited.
- **Seeded streams.** One `numpy.random.Generator` per (seed, purpose), so adding an event does not shift unrelated draws.
- **Answer key for both lanes.** Proposed shape: an event table (Briefing's 7 fields) and a case table (Forecast's fields: `case_id`, `scenario_type`, `forecast_version`, `true_variance`, `injected_driver_labels`, `driver_incremental_trx`, `interaction_effect`, `identifiable_contributions`, `identifiability_reason`, `true_residual`, `data_artifact_labels`, `affected_cuts`, `expected_checks`, `prohibited_claims`), linked by `event_id`. Settled under S10.
- **Restatement delay.** The artifact library takes a delay in weeks, so dev worlds can test both an in-window and an out-of-window restatement (S4).
- **LUMINA port (S3).** Alvin re-expresses the Week 18 reference case as a scenario request in this world. The Forecast stub's exact-recovery test then runs against it.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
| :- | :- | :- |
| Generator kept outside the repo | Shared Principle III and the user's rule that the answer key stays outside the repo | Keeping it in-repo behind `.gitignore` leaves its code and parameters in every agent's workspace |
