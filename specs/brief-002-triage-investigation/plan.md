# Implementation Plan: Triage, Manager and Specialists

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `006-triage-investigation`)

## Summary

A bounded Magentic loop inside stage 4a. Code triage rules run first. A manager agent groups stories and keeps two ledgers. Data Forensics and the Driver Investigator call typed tools and return verdicts. Comparisons go through `compare_to_peers` with named control sets. A promotion rule set guarantees a verdict either way. A deterministic scripted baseline replaces only the manager. Every ledger update is a span.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Gemini API with function calling (Briefing Architecture §13); agent framework open (A3): Google ADK, custom Python, or Microsoft Agent Framework; Pydantic; OpenTelemetry; core-002, core-003, core-004
**Storage**: `story`, `hypothesis` and ledger snapshots in `runtime` tables; episodic memory is a query over prior runs
**Testing**: pytest with recorded tool fixtures on the `day1-v1` anchors; harness from core-006
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Within the Briefing wall-clock cap (starting at 15 minutes per run); cost per story reported (EV-8.2)
**Constraints**: Depth two. Tools contain no model. Hypotheses come from the catalog. Prompts see only closed tool outputs and the metric definitions in play, all synthetic (shared VI; S14 for Gemini)
**Scale/Scope**: About 15 candidates per run grouped into a handful of stories

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | The manager cites evidence IDs; it never types a digit. |
| Shared II People decide | Triage review by exception; the stage only proposes. |
| Shared IV Typed contracts | Request in, result out (core-004). |
| Shared V Abstain | Low confidence and "unresolved" closures (FR-014, FR-017). |
| Shared VII / Briefing B-V Loops end | Depth two, catalog, no-repeat ledger, caps, defined exit. |
| Briefing B-II Declared mode | Autonomy ledger: manager groups, orders, picks parameters, stops; tests are code. |
| Briefing B-VI No individual identified | Tools enforce the floor; promotion findings stay at territory level. |

## Project Structure

```text
src/pharmagentics/triage/
  rules.py          code triage: drop, tag, link, suggest groups
  manager.py        grouping, ordering, first hypotheses, stop or abstain
  ledgers.py        task ledger, progress ledger, no-repeat guard
  forensics.py      Data Forensics specialist
  drivers.py        Driver Investigator specialist
  promotion.py      promotion verdict rules (FR-010)
  tests_catalog.py  code tests per catalog entry; parameters chosen by the agent
  closure.py        label, confidence rules, abstention
  memory.py         episodic memory and continuity
  caps.py           cap enforcement and defined exit
  scripted.py       manager-off baseline: fixed order of checks
  stage.py          request in, result out, state transitions
prompts/triage/     versioned prompt files (pinned per run)
tests/unit/triage/  tests/integration/triage/
```

## Key Design Points

- **Triage layers (proposed answer to A1)**: code drops withheld cuts, tags calendar weeks, links to open stories, suggests groups; the manager groups, orders and sets first hypotheses; P1 approves or edits when code and manager disagree or the manager marks low confidence. Share of calls per layer is logged.
- **Confidence**: High when one hypothesis is supported and every other tested one is ruled out, with at least two independent territories or a clean exposed-vs-control comparison; Medium when one is supported and others stay open, or support rests on one territory; Low otherwise.
- **Promotion rules**: `promotion.py` checks whether activity changed in the window (from `lookup_promo`); if not, the verdict is ruled out with that evidence. If it changed, the verdict comes from `compare_to_peers` plus a check that no other supported driver explains the same gap. Seasonality is netted against the national change for the same weeks.
- **Controls**: `compare_to_peers` drops territories with their own active event; if the overlapping driver is national and even across territories (Metacora at 8.8% to 10.0%), the control stays valid and the story says so.
- **No-repeat guard**: key is (story, catalog entry, canonical parameters); a repeat returns a refusal the manager must handle.
- **Defined exit**: any cap trips `closure.py`; the stage moves to the next story, then returns the result.
- **Plan review switch (A10)**: a run setting that forces TRIAGE_REVIEW on every plan for demos.
- **Scripted baseline**: forensics checks, then each catalog entry in a fixed order, with fixed stop rules; same tools, narrative and verifier.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
| :- | :- | :- |
| Agent loop with two ledgers | The Proposal commits to a Magentic pattern for open-ended tasks | A fixed script cannot vary the test path by case; the ablation measures this |
| Separate promotion rule set | EV-4.5 and P4 need a verdict either way, never a default credit | Leaving promotion to the manager's judgment risks crediting the latest campaign |
