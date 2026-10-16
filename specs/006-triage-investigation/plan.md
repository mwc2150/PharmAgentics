# Implementation Plan: Triage, Manager and Specialists

**Branch**: `006-triage-investigation` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

A bounded Magentic loop inside stage 4. Code triage rules run first. A manager agent groups stories and keeps two ledgers. Two specialists, Data Forensics and Driver Investigator, call typed tools and return verdicts. A deterministic scripted baseline replaces only the manager. Every ledger update is a span.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Gemini API with function calling (Architecture §13); agent framework open (A3): Google ADK, custom Python, or Microsoft Agent Framework; Pydantic; OpenTelemetry; specs 002, 003, 005
**Storage**: `story`, `hypothesis` and ledger snapshots in DuckDB tables; episodic memory is a query over prior runs
**Testing**: pytest with recorded tool fixtures; held-out harness from spec 010
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Per run within the wall-clock cap in the semantic layer (starting at 15 minutes); cost per story reported (EV-8.2)
**Constraints**: Depth two. Tools contain no LLM. Hypotheses come from the catalog. Prompts see only closed tool outputs and the metric definitions in play.
**Scale/Scope**: About 15 candidates per run grouped into a handful of stories

## Constitution Check

| Principle | Status |
|---|---|
| I Every number from a tool | The manager sees tool outputs and cites evidence IDs. It never types a digit. |
| III Declared mode | Autonomy ledger: manager picks and orders hypotheses and decides to stop; tests are code. |
| VI Typed handoffs | Request in, result out, both schemas (spec 005). |
| VII Bounded loops | Depth two, finite catalog, no-repeat ledger, caps, defined exit. |
| VIII People decide | Triage review by exception. |
| IX, XI | Tools enforce them. |

## Project Structure

```text
src/pharmagentics/triage/
  rules.py          code triage rules (drop, tag, link, suggest groups)
  manager.py        manager agent: grouping, ordering, first hypotheses, stop/abstain
  ledgers.py        task ledger, progress ledger, no-repeat guard
  forensics.py      Data Forensics specialist
  drivers.py        Driver Investigator specialist
  tests_catalog.py  code tests per hypothesis type (parameters chosen by the agent)
  closure.py        label, confidence rules, abstention
  memory.py         episodic memory as a query over prior stories and claims
  caps.py           cap enforcement and defined exit
  scripted.py       manager-off baseline: fixed order of checks
  stage.py          request in, result out, state transitions
prompts/            versioned prompt files (pinned per run)
tests/unit/triage/  tests/integration/triage/
```

## Key Design Points

- **Layer split for triage (proposed answer to A1)**. Code: drop failed cuts, tag calendar, link to resolved stories, suggest groupings. Manager: group, order, first hypotheses. Analyst: approve or edit when code and manager disagree or manager marks low confidence. Share of calls per layer is logged.
- **One request per run (A15)**. Grouping sees all candidates.
- **Confidence rule**: High when one hypothesis is supported and the rest are ruled out. Medium when one is supported and alternatives stay open. Low otherwise.
- **No-repeat guard**: key is (story, hypothesis type, canonicalized parameters). A second call returns a refusal the manager must handle.
- **Defined exit**: any cap trips `closure.py` to close the story as unresolved. The stage keeps going to the next story, then returns the result.
- **Plan review switch (A10)**: a run setting that forces TRIAGE_REVIEW on every plan for demos.
- **Inventory and days-supply**: the Driver Investigator tests inventory through `lookup_inventory` (spec 005). Data Forensics and the days-supply-shift hypothesis read `days_supply_90day_share` through `get_metric`. Both are catalog entries with named tools (spec 002 FR-006).
- **Prompts**: stored as files with a version string. The version is pinned in the run record.
- **Scripted baseline** uses the same tools, narrative and verifier. It runs a fixed order: forensics checks, then each catalog hypothesis in a fixed order, with fixed stop rules.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| Agent loop with two ledgers | The Proposal commits to a Magentic pattern for open-ended tasks | A fixed script cannot vary the test path by case; the ablation measures this |

## Open Decisions

A1 (triage junction), A3 (framework), A10 (plan review default), and cap values. Each is resolved in a clarify pass before implementation.
