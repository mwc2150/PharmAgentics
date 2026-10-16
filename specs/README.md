# PharmAgentics Briefing Agent: Spec Index

One Spec Kit feature per component in Architecture §14. Specs say WHAT and WHY. Each `plan.md` holds HOW. Each `tasks.md` is the work list. No code exists yet.

Source of truth, in order: Proposal, Personas, Evaluation Pack, Architecture (all in `docs/planning/`). The constitution is `.specify/memory/constitution.md`.

## Specs

| # | Feature | Stages | Owner (A13) | Eval items cited | Depends on |
|---|---|---|---|---|---|
| 001 | [data-generator](001-data-generator/spec.md) | §8 | Data | supports all | none |
| 002 | [semantic-layer](002-semantic-layer/spec.md) | cross-cutting | Data | EV-9.2 | 001 (field list) |
| 003 | [validation-gate](003-validation-gate/spec.md) | 1, 2 | Data | EV-2.1, 2.3, 2.4, 1.2 | 002 |
| 004 | [competitive-intelligence](004-competitive-intelligence/spec.md) | 3 | Data | EV-3.1 to 3.4 | 002, 003 |
| 005 | [tool-contracts](005-tool-contracts/spec.md) | 4 | Agent | EV-9.1, 9.3 | 002 |
| 006 | [triage-investigation](006-triage-investigation/spec.md) | 4 | Agent | EV-2.2, 4.1 to 4.4, 5.1, 5.2, 5.4 | 003, 004, 005 |
| 007 | [narrative-renderer](007-narrative-renderer/spec.md) | 5 | Agent | EV-1.1 to 1.3, 7.1 to 7.4 | 006 |
| 008 | [verifier](008-verifier/spec.md) | 6 | Agent | EV-1.1, 5.3, 6.1, 9.1, 9.2 | 007 |
| 009 | [run-orchestrator-review](009-run-orchestrator-review/spec.md) | 1 to 7 | Both | EV-6.2, 6.3, 8.1, 8.5 | 003 to 008 |
| 010 | [eval-harness-tracing](010-eval-harness-tracing/spec.md) | cross-cutting | Both | all | 001, then all |

Build order follows the Architecture's three builds (ADLC): scripted baseline (001 to 004, a fixed-order version of 006, then 007 to 009), low-code, then the Magentic agent. 010 starts early so every build is scored on the same cases.

## Shared decisions every spec uses

These are the Architecture's proposed answers. A spec that changes one must log it here and in the Architecture decision log.

| Decision | Value | Source |
|---|---|---|
| Restatement window | 3 weeks | Arch §5.1, Eval open item 18 |
| Confidence scale | High, Medium, Low. Low means abstain | Arch §5.4, Eval open item 3 |
| Business impact | Absolute change in TRx 30-day equivalents (proposed) | Arch A4 |
| Investigation requests | One per run | Arch A15 |
| All cuts fail validation | Publish a data-health notice only (proposed) | Arch A7 |
| P2 returns a brief | Back to the narrative stage with comments (proposed) | Arch A8 |
| Orchestration | One Magentic loop per use case. Choosing to pursue a use case is code-driven. | User, 2026-10-16 (settles A2) |
| Data size | Sample data only. Never hard-code territory, specialty or week counts. | User, 2026-10-16 |
| Loop caps | Values live in the semantic layer; proposed starting values are in spec 002 | Eval open item 17 |
| Inventory tool (departure from Arch §5.4) | `lookup_inventory` is added so seeded inventory events can be tested. Recorded in Architecture §5.4, §7.2 and decision 19, and in Evaluation Pack §4 (example events), 2026-10-16. | User, 2026-10-16 (X3) |
| Context metrics | Days-supply mix, inventory, promotion and access fields are governed context metrics. Every tool returns only governed fields. Every catalog entry names a tool that exists. | Spec 002 FR-002, FR-006, SC-007 |

## Open items by spec

Markers `[NEEDS CLARIFICATION]` stay in the spec that owns them. Each spec has at most three.

| Spec | Open |
|---|---|
| 001 | Calibration drug class (A12); answer-key format and driver labels, shared with the Forecast team; held-out seed ownership |
| 002 | Values for loop caps and materiality thresholds |
| 003 | Treatment of restatements older than the window; A7 (proposed) |
| 004 | Multiple-testing control (A5); business impact definition (A4, proposed) |
| 005 | Agent framework (A3); minimum rep-activity aggregation level |
| 006 | Triage decision junction (A1); plan review default (A10) |
| 007 | Monday template and length (Eval open item 4) |
| 008 | Judge agreement bar (Eval open item 2) |
| 009 | Sign-off level (A9); whether reviewers may overwrite a number by hand |
| 010 | Rerun count (Eval open item 15); human rubric anchors (open item 13) |

Evaluation Pack open items 1, 6, 7 and 14 are for the mentor or the team and are not tied to one spec. Item 6 (gold-brief writer) and item 11 (held-out seeds) are tracked in 010 and 001.

## Source layout shared by all plans

```text
semantic_layer/           versioned YAML (spec 002)
src/pharmagentics/
  generator/  semantic/  validation/  ci/  tools/  contracts/
  triage/  narrative/  verifier/  orchestrator/  review/
  evalharness/  tracing/
tests/  unit/  contract/  integration/  eval/
data/agent_visible/       agent tools may read this only
eval_private/             only evalharness may read this
```

Only `evalharness` may read anything under `eval_private/`. The generator may write to it and never read it back. Spec 010 owns the test that enforces both rules.
