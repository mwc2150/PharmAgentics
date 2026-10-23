# Implementation Plan: Agent Demo and Question-Answer UI

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23

## Summary

A self-contained prototype package, `pharmagentics.agentdemo`, runs the Briefing spine for one question at a time. Code handles load and pin, the feed-health gate, competitive intelligence, every hypothesis test, the claim renderer and the verifier. Five small custom agents in plain Python handle the judgment calls: Intake, Manager, Data Forensics, Driver Investigator and Narrator. Each agent calls Gemini through one LLM client, returns a typed JSON decision that code validates, and has a rule-based twin for scripted mode. A FastAPI server streams the trace to a vanilla HTML, CSS and JavaScript UI over server-sent events. The architecture lives in one draw.io file with two pages.

## Technical Context

**Language/Version**: Python 3.11+ (tested on 3.14 in `.venv`)
**Primary Dependencies**: DuckDB 1.5.6 (shared base); demo only, in `requirements-demo.txt`: Pydantic v2, FastAPI, Uvicorn, google-genai
**Storage**: Read-only `local/pharmagentics.duckdb`, built by the core-001 loader. Runs, evidence and reviews are kept in memory.
**Testing**: `unittest` (also runs under pytest). Each test builds a temporary DuckDB from the release, as `tests/test_data_load.py` does.
**Target Platform**: Local; browser UI at `http://127.0.0.1:8000`
**Project Type**: Library + web service + static UI
**Performance Goals**: Scripted under 5 s per question; agent mode under 90 s (SC-003)
**Constraints**: Depth two. No model in any tool. No digits from the model. Allowlisted, read-only data access. No answer-key access.
**Scale/Scope**: One brand, one user, one question at a time; about 10 tools, 7 catalog checks, 5 agents

## Constitution Check

Shared constitution v2.0.0 and Briefing lane constitution v1.0.0.

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | The narrator writes claim tokens only. The verifier fails any digit or spelled-out number outside a token. The scripted narrator is a template with tokens. |
| Shared II People decide | Answers arrive as drafts. P1 approves, then P2 signs off (FR-012). Nothing acts outside the answer. |
| Shared III Answer-key isolation | `db.py` opens only the local DuckDB file, read-only, and only allowlisted relations. It never reads `PHARMAGENTICS_EVAL_STORE`. A test checks the allowlist. |
| Shared IV Typed contracts | Pydantic models for intent, candidate, story, check, evidence, claim, answer and review. Each agent decision is validated before use. A failed validation falls back to the rule twin, and the trace says so. |
| Shared V Abstain | No supported driver means Low confidence and "unresolved, investigate next". |
| Shared VI Synthetic data only | Prompts carry only synthetic aggregates, definitions, catalog entries and closed tool outputs. The provider and model are recorded per run (S14). The key lives in git-ignored `.env`. |
| Shared VII Loops end | Depth two by construction (specialists cannot call agents). Fixed catalog, no-repeat ledger, caps per story and per run, defined exit. |
| Briefing B-I One semantic layer | **Deviation**: thresholds, catalog and caps live in `agentdemo/config.py` until core-002 lands. See Complexity Tracking. |
| Briefing B-II Declared mode | The UI and the diagram label each component as code, agent or human. |
| Briefing B-III Pinned version | Each run pins the import ID, the `rx_weekly` fingerprint, the model, the prompt version and the code version. |
| Briefing B-IV Traceable | Each stage, agent turn, model call and tool call emits a span. Each claim links to an evidence item and its span. |
| Briefing B-V Bounded loops | Caps: 3 rounds per story, 8 checks per story, 2 stalls, 6 stories per run, run wall time of 120 s. |
| Briefing B-VI No individual identified | Promotion data is read already aggregated, at territory level only. |
| Briefing B-VII Evaluation gate | Anchor tests encode the user stories. The prototype is not scored by core-006 yet. |

## Project Structure

```text
docs/architecture/pharmagentics-architecture.drawio   page 1 system, page 2 prototype
prompts/agentdemo/v1/                                 intake, manager, forensics, driver, narrator
src/pharmagentics/agentdemo/
  config.py        stand-in semantic config: thresholds, catalog, caps, display names
  db.py            governed read-only access; relation allowlist
  contracts.py     Pydantic models
  tracing.py       spans and the event stream
  tools.py         tool functions and the registry that writes evidence items
  detection.py     stage 3 competitive intelligence
  checks.py        catalog checks and verdict rules; peer comparison with control set
  closure.py       story label and confidence rules
  claims.py        claim tokens from evidence; renderer
  llm.py           Gemini client and availability
  agents/          base.py intake.py manager.py forensics.py driver.py narrator.py
  verifier.py      stage 6 code checks
  pipeline.py      the run: states, stages, caps
  review.py        run registry and review gates
  server.py        FastAPI: /api/meta, /api/ask (SSE), /api/review, /api/diagram
  __main__.py      CLI: serve | ask
  static/          index.html styles.css app.js
tests/agentdemo/   test_verifier.py test_tools.py test_anchors.py
```

**Structure Decision**: The prototype stays in its own package so it does not pre-empt `contracts/`, `tools/`, `orchestrator/`, `triage/`, `narrative/`, `verifier/` and `review/`. Those belong to core-004, core-005 and brief-002 to brief-005. Those specs can lift code from here when they are built.

## Agents

| Agent | Mode | Decides | Rule twin (scripted) |
| :- | :- | :- | :- |
| Intake | LLM, JSON | Question type, week or month, territory, metric | Regex parser |
| Manager | LLM, JSON | Story grouping and order; next checks each round; stop | One story per candidate cut; fixed check order; stop when every catalog check has run |
| Data Forensics | LLM, JSON | Parameters for feed, restatement and calendar checks | Story defaults |
| Driver Investigator | LLM, JSON | Parameters for access, promotion, inventory, competitor and concentration checks | Story defaults |
| Narrator | LLM, text with tokens | Wording around claim tokens | Template |

Guardrails in code: Data Forensics must run before any driver check (inserted if the manager skips it, and logged). Repeats are refused. Caps trip `closure.py`. Verdicts and confidence are never taken from a model.

## Detection Rules (starting values)

- **National**: like-for-like BXA TRx against the 4-week average. Flag at 8% or more.
- **Territory, single week**: peer-adjusted change against the 4-week average. Flag at 22 points or more and 50 TRx or more.
- **Territory, sustained**: last 4 weeks against the 8 weeks before, minus the same change for the other territories. Flag at 15 points or more and 40 TRx a week or more.
- **Competitor**: a product launched in the last 52 weeks with 5% share or more is a continuing story.
- **Holiday weeks**: tagged by code. A national drop in a holiday week goes to Data Forensics for the calendar check.

Values were checked against the anchor weeks. 2025-04-21 stays routine (largest peer-adjusted single-week move: 19 points).

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
| :- | :- | :- |
| Stand-in semantic config in `config.py` (B-I deviation) | core-002 has not shipped. The prototype needs thresholds now | Hard-coding values across modules would break B-I worse. One file is easy to replace |
| In-memory run registry | A demo for one user. core-005 owns `runtime` tables | Writing `runtime` tables would pre-empt core-005's schema |
| LLM and rule twin per agent | The demo must never fail on stage, and the scripted twin is the manager-off ablation | Model-only would fail without a key or network |
