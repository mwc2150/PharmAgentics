# PharmAgentics

Multi-agent first-pass forensic analyst for pharma brand performance. Course capstone (IEOR4573E, Columbia, Fall 2026; mentor Dr. Fikreab S. Admasu). One shared platform (data layer and orchestration), a seven-stage spine, and two use cases: the Weekly Brand-Performance Briefing Agent (Michael, Meghna) and the Forecast-Explanation Agent (Alvin, Sienna). The Proposal dropped payer-access impact and HCP segmentation / next-best action; do not bring them back.

Development is eval-driven (since 2026-10-29): every version of each agent answers the same 42 golden questions in `eval/` and is scored in MLflow. Specs are written with Spec Kit.

This file is the shared instruction set for coding agents; `CLAUDE.md` only imports it. Context is layered, and each layer links to the more detailed one: this file → the code map and the `CLAUDE.md`/README in each folder → `docs/guides/`, specs, ADRs → the code. Where a more specific source disagrees with this file, it wins. Layout decision: `docs/adr/0004-repo-layout-and-context-map.md`.

## Read first

- `uv run python -m pharmagentics.devtools.status`: where the project stands, from the handoffs and git (open work first, then the latest on `main`). `PROJECT_STATE.md` holds only the open-items list
- `uv run python -m pharmagentics.devtools.codemap`: folders, context files and every module in one page. Run it before crawling the tree
- `conversations/`: one dated handoff per branch or session; read the ones for your task. Old handoffs are history, not current instructions
- `docs/README.md`: what lives where in `docs/`, the constitutions (`.specify/memory/`), and the dot folders
- `specs/README.md`, `eval/README.md`, `data/agent_visible/README.md`, `SoT/README.md`, `docs/planning/README.md` (source-doc precedence)

## Hard rules

- **Ground truth stays outside this repository.** The generator, answer key, pre-artifact true data, counterfactual components and held-out parameters live in a private store found through `PHARMAGENTICS_EVAL_STORE`. Never commit, read, open, grep, index or copy them. Only `eval/harness/store.py` may read that variable, and only for evaluation work the user asks for.
- **Agent code never reads `eval/`.** Nothing in `src/` or `agents/` imports the eval package or opens the golden cases; they are an answer key for development. `eval/tests/test_isolation.py` enforces this.
- **A SoT drop never holds ground truth.** Run `uv run python SoT/check.py` on every new drop; it refuses files that look like an answer key or held-out parameters.
- Agent tools read data only through the governed views over `data/agent_visible/` (DuckDB). Never read `raw` tables for metrics.
- No digit in any generated brief or report comes from a language model. Briefing uses claim tokens filled by code.
- Say "competitive intelligence", never "statistical surveillance" or "surveillance". "New patients" only for NBRx.
- No output line identifies an individual rep.
- Mark unknowns `[NEEDS CLARIFICATION: … (open-item ID)]`. Do not guess.
- Do not edit the Forecast lane's personas, evaluation (Sienna's Personas & Eval Design: FE-01 to FE-31, TC-01 to TC-12), constitution or specs; cite them by ID. The Forecast golden cases and any FE scorers are drafts until Alvin and Sienna confirm them.
- LLM judges are report-only until their agreement with human labels clears the bar (Evaluation Pack open item 2). Never gate a merge on a judge score before that.
- Do not push to GitHub or open pull requests unless the user asks.

## Workflow (full version: `docs/guides/workflow.md`)

- **Eval loop:** change a system, `uv run python -m eval run --system <name>`, then `uv run python -m eval gate <candidate-run-id> <baseline-run-id>`. No change merges if a gated check regresses (Briefing B-VII).
- **Specs and state together:** specs hold what and why, constitutions the rules, `conversations/` the handoffs. Code may lead its spec; the spec and the handoff catch up in the same pull request. Never delete a spec.
- **Handoff:** before ending a session, write `conversations/YYYY-MM-DD-topic.md` with the `branch`, `lane` and `next` header (`conversations/README.md`). It is a new file, so it never conflicts. Never add status to `PROJECT_STATE.md` or to any other file every branch edits; a golden-set change goes in `eval/golden/changes/`.
- **Source documents:** a new Drive export goes into `SoT/<YYYY-MM-DD>/`; run `SoT/check.py`, then follow `SoT/README.md`.

## Most-used commands (full reference: `docs/guides/build-and-run.md`)

Dependencies are managed with uv (`uv sync`; change them only with `uv add` / `uv remove` and commit `uv.lock`).

- Data: `uv run python src/pharmagentics/data/load_duckdb.py`, then `uv run python src/pharmagentics/data/check_duckdb.py`
- Tests: `uv run pytest`
- Golden set: `uv run python -m eval check`
- Baselines: `uv run python -m eval run --system briefing_scripted --lane briefing` (and `--system forecast_scripted --lane forecast`)
- Agent: `uv run python -m eval run --system briefing_agent --lane briefing` (add `--model anthropic:claude-haiku-5-5` for the Haiku team; key in the git-ignored `.env`)
- Dashboard: `uv run python -m eval ui`, then http://127.0.0.1:5000
- Status and code map: `uv run python -m pharmagentics.devtools.status` and `uv run python -m pharmagentics.devtools.codemap` (printed, never committed)
- Web app: `uv run python deploy/make_env.py` once, then `docker compose up --build` (`deploy/README.md`)
