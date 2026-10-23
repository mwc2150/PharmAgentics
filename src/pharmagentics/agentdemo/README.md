# agentdemo (brief-006): unfinished

The custom-agent prototype for [brief-006](../../../specs/brief-006-agent-demo-ui/spec.md). Antigravity built the foundation modules from [tasks.md](../../../specs/brief-006-agent-demo-ui/tasks.md) and then stopped. **Nothing runs end to end yet:** you cannot ask a question or get an answer.

Full status, with the evidence for each item: [tasks.md, Build status](../../../specs/brief-006-agent-demo-ui/tasks.md#build-status-review-of-2026-10-23).

## Built

| Module | Task | Note |
| :- | :- | :- |
| `config.py` | T003 | Stand-in semantic config until core-002 |
| `db.py` | T004 | Read-only DuckDB with a relation allowlist |
| `contracts.py`, `tracing.py` | T005 | Pydantic models; spans and event stream |
| `tools.py` | T006 | 13 tools and the evidence registry. **`data_pin` fails** without `pytz` (T022) |
| `detection.py` | T007 | Stage 3. **The competitor rule misfires** on weeks before 2025-10 (T023) |
| `claims.py` | T009 (part) | Claim tokens and renderer |

## Not built

| Module | Task |
| :- | :- |
| `checks.py`, `closure.py` | T008 |
| `verifier.py` | T009 |
| `llm.py`, `agents/` (Intake, Manager, Data Forensics, Driver Investigator, Narrator) | T010 |
| `prompts/agentdemo/v1/` | T011 |
| `pipeline.py`, `__main__.py` | T012, T013 |
| `tests/agentdemo/` | T014, T015 |
| `server.py`, `static/`, `review.py` | T016 to T019 |
| `quickstart.md` | T021 |

Page 2 of [`docs/architecture/pharmagentics-architecture-v2.drawio`](../../../docs/architecture/pharmagentics-architecture-v2.drawio) marks each module that is not built yet.
