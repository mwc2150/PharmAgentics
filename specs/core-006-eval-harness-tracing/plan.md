# Implementation Plan: Evaluation Harness and Tracing

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23; revised 2026-10-29 for eval-driven development (MLflow replaces Phoenix; the harness moves to `eval/`)

## Summary

A harness package is the only code allowed to read ground truth, which it finds outside the repository through `PHARMAGENTICS_EVAL_STORE`. It runs every system on the golden set (one case per persona question, 42 in all), scores each lane against its own items, and logs runs, reruns, traces and spans to MLflow. LLM-judge items use RAGAS metrics inside MLflow, served by a local model until a provider is chosen.

## Technical Context

**Language/Version**: Python 3.12 (uv-managed; shared floor 3.11)
**Primary Dependencies**: MLflow 3.17 (`mlflow.genai.evaluate`, tracing, dashboard); RAGAS 0.4 through `mlflow.genai.scorers.ragas`; Ollama with `gemma3:4b` as the local judge; DuckDB; Pydantic; PyYAML; pytest
**Storage**: `eval/golden/` (case files, no answer-key fields) in the repo; runs, traces and scores in `eval/mlflow/` (SQLite, git-ignored); ground truth and held-out cases outside the repo
**Testing**: pytest (`eval/tests/`): golden-set integrity, code checks on planted answers, positive control on all 42 cases, isolation scans with planted violations, end-to-end MLflow run
**Target Platform**: Local; `python -m eval ui` serves the MLflow dashboard
**Project Type**: package with a CLI (`python -m eval run --system reference --lane briefing`)
**Performance Goals**: Budgeted by cost, not code. One prediction at a time (SQLite store; local model)
**Constraints**: Black-box scoring. Only `eval/harness/store.py` reads the store. MLflow telemetry off. Nothing from the store is written into the repo
**Scale/Scope**: About 55 Briefing cases × 5 reruns × 4 versions; Forecast TC-01 to TC-12 variants

## Constitution Check

| Article | Status |
| :- | :- |
| Shared III Answer-key isolation | This spec enforces it: env-var store, scan, probe, committed-file check. |
| Shared VI Synthetic data only | Data-inventory review per release and provider (SC-009). |
| Briefing B-IV Traceable | Spans and provenance. |
| Briefing B-VII Evaluation gate | Regressions block merge; targets never loosen after held-out. |
| Briefing B-III Pinned version | Every score references the run's snapshot. |

## Project Structure

```text
eval/
  __main__.py     CLI: import-stories, check, run, gate, ui
  golden/
    briefing/P1-Q1.yaml …     C-001 to C-024, from user stories P1-Q1 … P4-Q6 (no answer-key fields)
    forecast/CA-Q1.yaml …     F-001 to F-018, from CA-Q1 … FM-Q6; drafts until Alvin and Sienna confirm
    CHANGELOG.md
  labels/         human labels for judge agreement (Evaluation Pack open items 2 and 13)
  harness/
    cases.py      case model and loader        importer.py   user-story importer (never overwrites)
    integrity.py  ID checks; facts recompute   numbers.py    number extraction and rounding match
    scorers.py    code checks; RAGAS judges    systems.py    reference and naive_llm controls; baselines plug in here
    envelope.py   the answer contract          run.py        MLflow runs, reruns, gate
    isolation.py  store-reader, ground-truth-file, agent-import and SoT-drop scans
    store.py      the only reader of PHARMAGENTICS_EVAL_STORE
  tests/
  mlflow/         git-ignored store: runs, traces, spans, assessments
```

**Structure Decision**: The harness is its own top-level package so one import rule keeps ground truth sealed: agent code in `src/` and `agents/` must never import it. Forecast FE scorers will live beside the Briefing ones once Alvin and Sienna own them.

## Briefing Item Methods (Evaluation Pack §3)

| Group | Items | Methods |
| :- | :- | :- |
| Numeric fidelity | EV-1.1 to 1.3 | Auto, Auto, Human |
| Data reliability | EV-2.1 to 2.4 | Auto |
| Detection | EV-3.1 to 3.4 | Auto (3.3 also Human) |
| Explanation | EV-4.1 to 4.5 | Auto (4.2, 4.4 also Human) |
| Calibration | EV-5.1 to 5.4 | Auto, Auto, Judge, Auto |
| Traceability | EV-6.1 to 6.3 | Auto, Auto, Human |
| Communication | EV-7.1 to 7.5 | Human or Judge; Auto and Human; Human; Auto; Auto and Human |
| Efficiency | EV-8.1 to 8.5 | Human; Auto and Human; Auto; Auto; Auto |
| Governance | EV-9.1 to 9.4 | Auto and Judge; Auto and Judge; Auto; Review |

## Key Design Points

- **User-story importer**: parses `docs/planning/user-stories.md` sections (story ID, anchor weeks, Given/When/Then, must-not-say, eval items) into case files. Each case is reviewed by hand once, then frozen; the case file, not the doc, is what runs.
- **Facts**: each hard number in a golden answer carries the read-only SQL that recomputes it; `check` and the integrity test fail if the data stops matching.
- **Must-not-say**: a quoted phrase is checked by code unless a qualifier follows it ("without the plan", "as if …"); qualified phrases go to the judge, so a correct answer that uses the same words is not failed.
- **Controls**: the `reference` system (golden answers) must pass every code check; the `naive_llm` system (local model, no data) must fail the numeric checks. A control that scores wrongly means a broken check.
- **Judges**: RAGAS FactualCorrectness through MLflow on `ollama:/gemma3:4b`; the judge sees only the question, the answer and the golden answer. Report-only until human agreement clears the bar (open item 2).
- **Store**: `store.py` reads `PHARMAGENTICS_EVAL_STORE`; no other module may import it or read the variable. `isolation.py` enforces both and scans the git index for ground-truth file patterns.
- **Held-out**: sealed parameters stay in the store; opening needs an explicit flag; `regression.py` rejects target changes after the first held-out score.
- **Back-test**: `backtest.py` asks core-005 for ten consecutive weekly replays with as-of timestamps on the held-out seed.
- **N/A scoring**: each item declares which scenario families it applies to; others score N/A.

## Complexity Tracking

None.
