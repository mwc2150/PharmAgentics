# eval

Eval-driven development for PharmAgentics (spec [core-006](../specs/core-006-eval-harness-tracing/spec.md)). Every system answers the same golden questions, is scored by the same checks, and lands in one MLflow dashboard with its traces and spans.

**Status (2026-10-29):** the golden set, code checks, LLM judge, two controls, **two scripted baselines (one per lane)** and MLflow logging work end to end. The low-code and agent versions plug in next.

## Commands

All from the repository root, after `uv sync` and building the database (`uv run python src/pharmagentics/data/load_duckdb.py`).

| Command | Does |
| :- | :- |
| `uv run python -m eval check` | Validates the 42 cases and recomputes every fact from the data |
| `uv run python -m eval run --system reference` | Scores the golden answers (positive control) |
| `uv run python -m eval run --system naive_llm` | Scores a local model with no data (negative control); needs Ollama |
| `uv run python -m eval run --system briefing_scripted --lane briefing` | The Briefing scripted baseline (`agents/brand-briefing/briefing_baseline/`) |
| `uv run python -m eval run --system forecast_scripted --lane forecast` | The Forecast scripted baseline BL-0 (`agents/forecast-explanation/forecast_baseline/`), a draft for Alvin and Sienna |
| `... --lane briefing` / `--stories P1-Q2,CA-Q1` / `--reruns 3` | Narrows the cases or repeats them; reruns report mean and spread |
| `... --judge` | Adds the LLM judge on `ollama:/gemma3:4b`; `--judge gemini:/<model>` switches provider |
| `uv run python -m eval gate <candidate> <baseline>` | Exits 1 if a gated check scores lower than on the baseline run |
| `uv run python -m eval ui` | MLflow dashboard at http://127.0.0.1:5000 |
| `uv run python -m eval import-stories` | Drafts case files for new user stories; never overwrites an existing case |
| `uv run pytest tests/test_tools.py eval/tests` | The shared-tools and harness tests |

Each `run` is one MLflow parent run with a child run per rerun. Every case becomes a trace with its spans (for the baselines: one per pipeline stage and one per tool call, with the SQL as input), its check results and its expectations, all kept in `eval/mlflow/` (git-ignored).

## Layout

| Path | Holds |
| :- | :- |
| `golden/briefing/` | 24 cases, one per Briefing persona question (C-001 to C-024, P1-Q1 to P4-Q6) |
| `golden/forecast/` | 18 cases, one per Forecast persona question (F-001 to F-018, CA-Q1 to FM-Q6). Drafts until Alvin and Sienna confirm them and map each to TC-01 to TC-12 |
| `golden/CHANGELOG.md` | Every change to a case, and what is still open before freezing |
| `labels/` | Human labels that check the LLM judge (Evaluation Pack open item 2) |
| `harness/` | Case model and importer, fact checks, number matching, scorers, systems, answer contract, runner, isolation scans, the store reader |
| `tests/` | Golden-set integrity, code checks on planted answers, the positive control on all 42 cases, isolation scans, an end-to-end MLflow run |
| `mlflow/` | Runs, traces, spans and scores. Git-ignored |

A case holds the question, the golden answer (the story's "Answer from the data"), the Given / When / Then, the must-not-say rule, its eval items and, where verified, **facts**: numbers with the SQL that recomputes them. Today 69 facts on 14 cases recompute exactly.

## Checks

| Check | Passes when | Eval items | Gated |
| :- | :- | :- | :- |
| `numbers_match_golden` | Every number in the answer matches a golden number at the precision stated. Dates, IDs, years and counts up to 10 are skipped | EV-1.1 proxy for systems without evidence | No: a system with evidence may state correct numbers the golden answer omits |
| `golden_number_recall` | The answer states the golden answer's numbers | Completeness | No |
| `must_not_say` | No literal must-not-say phrase appears, allowing rounding and small rewordings | Case rule | Yes |
| `governed_terms` | No "surveillance"; "new patients" only next to NBRx | EV-9.2 | Yes |
| `no_individual_rep` | No line names or numbers a rep (heuristic) | EV-9.1 | Yes |
| `claims_reconcile` | Each claim's stored SQL, re-run on the data, gives the claimed value at its stated rounding (half up). Systems with evidence only | EV-1.1, FE-04, FE-16 | Yes |
| `numbers_traced` | Every number in the answer text is a claim with evidence. Systems with evidence only | EV-6.1, FE-19 | Yes |
| `links_resolve` | Every claim links to an evidence item pinned to the data version of the run. Systems with evidence only | EV-6.2, FE-20 | Yes |
| `run_errors` | Count of cases where the system crashed; a crash is never scored as zero | Run error tag | Yes (gate) |
| `judge_factual_correctness` | RAGAS FactualCorrectness against the golden answer, with `--judge` | EV-1.3 | No: report-only until judge-human agreement clears the bar |

A must-not-say phrase followed by a qualifier ("… without the plan", "… as if the rest were on plan") is context-dependent, so code does not check it; it is kept for the judge.

## Results so far

| System | Cases | Numbers match | Recall | Must not say | Governed terms | No rep | Judge |
| :- | :- | :- | :- | :- | :- | :- | :- |
| `reference` (golden answers) | 42 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 on 3 |
| `naive_llm` (`gemma3:4b`, no data) | 42 | 0.556 | 0.064 | 1.000 | 1.000 | 1.000 | 0.297 on 3 |

| `briefing_scripted` | 24 | 0.184 | 0.364 | 1.000 | 1.000 | 1.000 | n/a |
| `forecast_scripted` | 18 | 0.189 | 0.293 | 1.000 | 1.000 | 1.000 | n/a |

The baselines also score 1.000 on `claims_reconcile`, `numbers_traced` and `links_resolve`, with 0 run errors. Their low golden-number recall is the finding: they state correct, traced numbers, but only about a third of the numbers each story's answer expects. That gap is what the low-code and agent versions are built to close.

The controls behave as they should: the golden answers pass everything, and a model with no data states almost none of the golden numbers and invents others. The judge separates them too: 1.0 on each golden answer, 0.20 to 0.37 on the no-data answers (P1-Q2, P2-Q1, CA-Q1). That is one sign the judge works, not the calibration open item 2 asks for.

## Known limits

- `numbers_match_golden` is a proxy for EV-1.1 that only suits systems without evidence. Systems with evidence are scored on `claims_reconcile` instead. An answer with no numbers passes it trivially; `golden_number_recall` catches that.
- The baselines are tuned on the dev cases (core-006 allows this; held-out cases will not be). Two analytic bugs the cases exposed: a baseline window that already contained the gap it was meant to detect, and a competitor share that rose mechanically when BXA volume fell.
- The stories' attribution figures (difference-in-differences gaps) are illustrations, so a system with its own valid method may cite different numbers there.
- Item-level checks (driver named, label, abstention, concentration, promotion verdict) need the structured answer that real systems will return (`harness/envelope.py`).
- The judge is slow on a laptop: about 40 seconds per case with `gemma3:4b`, so a full 42-case judged run takes about half an hour. Run it on demand.
- 28 cases have no facts yet; six questions still need a period. See `golden/CHANGELOG.md`.
- Held-out cases and the answer key are not here by design; `harness/store.py` will read them from outside the repository.
