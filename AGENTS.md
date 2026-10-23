# PharmAgentics

Multi-agent first-pass forensic analyst for pharma brand performance. Course capstone (IEOR4573E, Columbia, Fall 2026). One shared platform, a seven-stage spine, two use cases: the Weekly Brand-Performance Briefing Agent (Michael, Meghna) and the Forecast-Explanation Agent (Alvin, Sienna). Built with Spec Kit (spec-driven development).

## Read first

- `.specify/memory/constitution.md`: shared principles (v2.0.0)
- `.specify/memory/constitution-briefing.md`: Briefing lane articles (v1.0.0)
- `specs/README.md`: spec index, shared decisions, open items, dev anchor cases
- `docs/planning/README.md`: source docs and their precedence
- `data/agent_visible/README.md`, `data_dictionary.json`, `docs/DUCKDB_FIRST_RUN.md`: the data world

## Hard rules

- **Ground truth stays outside this repository.** The generator, answer key, pre-artifact true data, counterfactual components and held-out parameters live in a private store found through `PHARMAGENTICS_EVAL_STORE`. Never commit, read, open, grep, index or copy them. Only `src/pharmagentics/evalharness/store.py` may read that variable, and only for evaluation work the user asks for.
- Agent tools read data only through the governed view over `data/agent_visible/` (DuckDB). Never read `raw` tables for metrics.
- No digit in any generated brief or report comes from a language model. Briefing uses claim tokens filled by code.
- Say "competitive intelligence", never "statistical surveillance" or "surveillance". "New patients" only for NBRx.
- No output line identifies an individual rep.
- Mark unknowns `[NEEDS CLARIFICATION: … (open-item ID)]`. Do not guess.
- Do not edit the Forecast lane's personas, evaluation, constitution or specs. They belong to Alvin and Sienna.
- Do not push to GitHub or open pull requests unless the user asks.

## Spec namespaces

`specs/core-###` shared (both teams); `specs/brief-###` Briefing lane; `specs/fcst-###` Forecast lane (reserved). Colliding names carry `briefing.` or `forecast.` prefixes.

## Workflow

`/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`. One spec per component.

Spec Kit finds the active spec from `.specify/feature.json`, not the branch name. Before working on an existing spec:

```powershell
'{"feature_directory":"specs/brief-002-triage-investigation"}' | Out-File -Encoding ascii .specify/feature.json
```

When reality disagrees with a spec, update the spec first, then the code. Update a source doc in Google Drive first, then its copy in `docs/planning/`, then the specs that cite it.

## Build

Python 3.11+. `python -m pip install -r requirements.txt`, then `python src/pharmagentics/data/load_duckdb.py`, `python src/pharmagentics/data/check_duckdb.py`, `python -m unittest discover -s tests -v`.
