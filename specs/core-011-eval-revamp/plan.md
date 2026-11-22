# Plan: core-011 Eval Revamp

The file contract for the packets in `tasks.md`. Packets build against these shapes; none changes another's files.

## Golden case additions (`eval/harness/cases.py`)

```yaml
facts:
- id: southeast_bxa_trx_august_avg
  value: 481
  sql: select avg(s) from (...)
  role: must            # must | context (default context)
  tolerance: null       # relative, e.g. 0.05 when the source states the value roughly; null = stated precision
  reviewed: true        # agent drafts write false
findings:
- id: southeast_coverage_gap
  territory: SOUTHEAST  # territory ID or NATIONAL
  direction: down       # up | down | flat
  drivers_supported: [promotion]
  drivers_ruled_out: [access, supply]
  withheld: false       # true: the cut must be withheld, with no story for it
  reviewed: false
```

Drivers use the Forecast `eval drivers` vocabulary plus the Briefing ones: `access`, `promotion`, `supply`, `competitor`, `data`, `holiday`, `none`.

`Case.expectations()` gains `key_facts: [{id, value, tolerance}]` (must-state facts with numeric values) and `findings: [...]`. `golden_numbers` is unchanged.

## Envelope: story cards (`eval/harness/envelope.py` reads `sections`, unchanged type)

Scorers read the story cards from `sections[*].card` on sections numbered `3.N`. brief-008 cards hold `headline`, `confidence`, `drivers_checked`. Packet E adds, built by code from the same tool verdicts on both engines:

```python
"card": {"headline": "...", "confidence": "Medium", "drivers_checked": ["promotion", "access"],
         "territory": "SOUTHEAST", "direction": "down",
         "drivers_supported": ["promotion"], "drivers_ruled_out": ["access"]}
```

Until E lands, `finding_recall` returns not scored.

## Scorers (`eval/harness/scorers.py`)

- `key_fact_recall`: per case, stated must facts / must facts; matching is `numbers.same()` at the fact's stated precision, or `abs(n - v) <= tolerance * abs(v)` when a tolerance is set. Not scored (no value) when the case has no numeric must facts. Rationale names missing fact ids. Pooled share logged as a run metric `key_fact_recall_pooled`.
- `finding_recall`: per expected finding, one point for the story card of that territory with that direction, plus one per expected supported and ruled-out driver found in the card; withheld findings score one point when no story card has that territory. Score = points / possible. `false_drivers`: count of supported drivers on cards that no finding expects.
- `brief_words`: words over each section's text, card headline and table cells, excluding `detail`.
- "Not scored" must not count as 1.0 or 0.0 in the run mean: packet A checks how MLflow aggregates a missing value and, if needed, logs the run mean itself over scored cases only.

## Insights (`eval/harness/insights.py`, `python -m eval insights`)

Arguments: `--store PATH` (repeatable; default this tree's `eval/mlflow/mlflow.db`), `--system`, `--last N` (default 5), `--out DIR`. Opens SQLite with `mode=ro`. Parent runs come from `runs` without an `mlflow.parentRunId` tag; their child run holds the traces (`trace_request_metadata` key `mlflow.sourceRun`); scores are in `assessments` (`trace_id`, `name`, `value`, `rationale`). Case id from the trace request's question matched to the golden cases. Output: `insights.md` (stuck cases, fallen cases, engine comparison, rerun spread, golden-version breaks) and `insights.json` (the per-case matrix).

## Evaluation page (packet C)

`eval/harness/telemetry_export.py` adds a `cases` block from `insights.json` (latest run per system; case id, story, scores; no golden text). `src/pharmagentics/api/telemetry.py` passes it to analysts and the tester only. `frontend/figma-make/src` Evaluation page gains a per-case table with stuck and fallen marks.

## Packets and the files they own

| Packet | Model | Owns | Starts |
| :- | :- | :- | :- |
| **A: schema and scorers** | Sonnet | `eval/harness/cases.py`, `eval/harness/scorers.py`, `eval/harness/run.py` (run-level metrics only), `eval/tests/test_scorers.py`, new `eval/tests/test_key_facts.py` | now |
| **B: insights** | Haiku | new `eval/harness/insights.py`, `eval/__main__.py` (one subcommand), new `eval/tests/test_insights.py` | now, after A's schema commit for the `key_facts` names |
| **C: Evaluation page** | Sonnet | `eval/harness/telemetry_export.py`, `src/pharmagentics/api/telemetry.py`, the Evaluation page component(s) in `frontend/figma-make/src`, their tests | after brief-008 merges (App.tsx) |
| **D: golden facts and findings** | Haiku | `eval/golden/briefing/*.yaml` (facts, findings, exact values in place of "about"), `eval/golden/CHANGELOG.md` | after A's schema commit |
| **E: story card fields** | Sonnet | the memo story builder (`src/pharmagentics/tools/memo.py`, `promotion.py`), `briefing_agent` story cards, their tests | after brief-008 merges |

## Checks

Packets run focused tests only (`eval/tests/`, plus `tests/test_memo.py` for E) and no eval runs. D runs `uv run python -m eval check` and `eval/tests/test_golden_integrity.py`. The integrator runs the full suite, one scripted run and the gate (new scorers report-only), and `eval insights` over the brief-008 runs (SC-003).
