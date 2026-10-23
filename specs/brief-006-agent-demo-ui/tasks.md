# Tasks: Agent Demo and Question-Answer UI

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Status**: **Unfinished.** The Antigravity build stopped partway through Phase 2. Reviewed 2026-10-23.

## Build status (review of 2026-10-23)

Antigravity built the foundation modules and the first diagram, then stopped. **The prototype does not run end to end.** No question can be asked and no answer comes back: there is no pipeline, no agent, no server and no UI. No `agentdemo` tests exist.

| Part | State | Evidence |
| :- | :- | :- |
| `config.py`, `db.py`, `contracts.py`, `tracing.py`, `claims.py`, `detection.py`, `tools.py` | Built | Imports cleanly. The allowlist refuses `raw.rx_weekly`, `getenv` and relation-free queries. 12 of the 13 tools return results in a smoke run; `get_plan_metric` was not called. Detection flags Pacific on 2026-06-08 |
| `data_pin` tool (stage 1 pin) | **Broken** | Fails with `ModuleNotFoundError: pytz`: DuckDB needs it to return `import_runs.completed_at`, and `requirements-demo.txt` omits it (T022) |
| Competitor rule in `detection.py` | **Wrong** | BXC and BXD have `effective_start` 2024-10-14 (the release start), so every week up to 52 weeks later gets two "recent launch" candidates. Week 2025-04-21 is not routine, which breaks US1 scenario 2 (T023) |
| `checks.py`, `closure.py`, `verifier.py` | **Not built** | T008, T009 |
| `llm.py`, `agents/` (Intake, Manager, Data Forensics, Driver Investigator, Narrator) | **Not built** | T010 |
| `prompts/agentdemo/v1/` | **Not built** | T001, T011 |
| `pipeline.py`, `__main__.py` CLI | **Not built** | T012, T013 |
| `tests/agentdemo/` | **Not built** | T001, T014, T015 |
| `server.py`, `static/` UI, `review.py` | **Not built** | T016 to T019 |
| `quickstart.md`, spec index row | **Not built** (index row added at review) | T020, T021 |
| Architecture diagram | Built: Antigravity draft `pharmagentics-architecture.drawio`, rebuilt layout `pharmagentics-architecture-v2.drawio` | T002. Page 2 of v2 marks each module that is not built yet |

## Phase 1: Setup

- [ ] T001 Create `src/pharmagentics/agentdemo/`, `prompts/agentdemo/v1/`, `tests/agentdemo/`; add `requirements-demo.txt` — **partial**: package and `requirements-demo.txt` exist; `prompts/agentdemo/v1/` and `tests/agentdemo/` do not
- [x] T002 Draw the architecture in `docs/architecture/pharmagentics-architecture.drawio`: page 1 system, page 2 prototype (FR-017, US3). Rebuilt layout in `pharmagentics-architecture-v2.drawio`; the team picks one

## Phase 2: Foundational

- [x] T003 [P] Stand-in semantic config (`config.py`) (FR-004)
- [x] T004 [P] Governed read-only access with allowlist (`db.py`) (FR-014)
- [x] T005 [P] Contracts (`contracts.py`) and tracing (`tracing.py`) (FR-010, FR-011)
- [x] T006 Tools and registry that write evidence items (`tools.py`) (FR-010, FR-014). Defect: `data_pin` fails (T022)
- [x] T007 Competitive intelligence (`detection.py`) (FR-003, FR-004). Defect: the competitor rule misfires before 2025-10 (T023)
- [ ] T008 Catalog checks, peer comparison and verdict rules (`checks.py`); closure rules (`closure.py`) (FR-006, FR-007) — **not built**
- [ ] T009 Claims and renderer (`claims.py`); verifier (`verifier.py`) (FR-008, FR-009) — **partial**: `claims.py` built; `verifier.py` not built

## Phase 3: User Story 1 - Ask and answer (P1) MVP

- [ ] T010 [US1] LLM client (`llm.py`) and agents with rule twins (`agents/`) (FR-001, FR-005, FR-013, FR-016)
- [ ] T011 [US1] Prompts in `prompts/agentdemo/v1/`
- [ ] T012 [US1] Pipeline with run states, pins and caps (`pipeline.py`) (FR-002, FR-005)
- [ ] T013 [US1] CLI `python -m pharmagentics.agentdemo ask "…"`
- [ ] T014 [P] [US1] Anchor tests for the eight scenarios in scripted mode (SC-001, SC-002)
- [ ] T015 [P] [US1] Verifier tests: digit outside a token, unknown token, banned terms, causal wording (FR-009)

## Phase 4: User Story 2 - Watch the agents (P1)

- [ ] T016 [US2] FastAPI server with SSE trace stream (`server.py`) (FR-011)
- [ ] T017 [US2] UI: chat, live trace, evidence drawer, diagram tab (`static/`) (FR-010, FR-011, FR-017)

## Phase 5: User Stories 4 and 5 - Review and scripted mode (P2)

- [ ] T018 [US4] Review gates and registry (`review.py`); UI review bar (FR-012)
- [ ] T019 [US5] Mode switch in the UI; automatic fallback on model error (FR-013)

## Phase 6: Polish

- [ ] T020 Browser walkthrough of the anchors in both modes; fix what breaks
- [ ] T021 `quickstart.md`; add brief-006 to `specs/README.md` — **partial**: index row added at review; `quickstart.md` not written

## Phase 7: Defects found at review (2026-10-23)

- [ ] T022 Make `data_pin` run: add `pytz` to `requirements-demo.txt`, or cast `completed_at` to text in the query (FR-002)
- [ ] T023 Competitor rule: count a product as a recent launch only if it launched after the release's first week (BXE Metacora, 2026-03-02). Add an anchor test that 2025-04-21 has no candidates (US1 scenario 2, SC-001)

## Dependencies

Reads the core-001 DuckDB build. Lifts no code from, and blocks no work on, core-002 to core-006 or brief-001 to brief-005. Those specs may lift code from here.
