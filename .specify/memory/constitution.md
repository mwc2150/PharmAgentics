<!--
Sync Impact Report
- Version change: 1.0.0 → 2.0.0 (MAJOR: the constitution is now system-wide and
  holds only shared articles; Briefing-only articles moved to a lane constitution)
- Basis: System Architecture §8 (docs/planning/system-architecture.md), open item S11
- Principles kept as shared (renumbered): old I → I, old VIII → II, old XI → III,
  old VI → IV, old X → VI
- Principle added: V Abstain When Evidence Is Weak (Briefing EV-5.2 and Low
  confidence; Forecast Article III)
- Principle added as a shared floor: VII Every Loop Ends by Construction
  (System Architecture §4c; strength set per lane)
- Moved to .specify/memory/constitution-briefing.md: old II, III, IV, V, VII (full
  strength), IX, XII, and the Briefing "Additional Constraints"
- Templates: spec, plan and tasks templates read this file at run time; no edits
  needed. plan.md Constitution Check sections must now cite both this file and the
  lane constitution (see "Lane constitutions" below).
- Follow-up: Forecast team (Alvin, Sienna) to accept, amend or reject (S11). Their
  constitution v1.0.0 on branch alvin-forecast-explanation stays in force until then.
-->

# PharmAgentics Constitution

Project: PharmAgentics capstone (IEOR4573E, Fall 2026). One shared platform, a seven-stage spine, and two use cases: the Weekly Brand-Performance Briefing Agent (Michael, Meghna) and the Forecast-Explanation Agent (Alvin, Sienna).

This file holds only the articles both use cases share (System Architecture §8). Each lane keeps its own articles in a lane constitution. Where a lane article and a shared article conflict, the shared article wins.

**Status.** Adopted for `specs/core-*` and `specs/brief-*` on 2026-10-23. Proposed to the Forecast team under open item S11. Until Alvin and Sienna accept it, the Forecast lane follows its own constitution v1.0.0, which already contains Principles I to V in its own words.

## Core Principles

### I. Every Number Comes From a Tool (NON-NEGOTIABLE)

Every figure in any output comes from deterministic code and is backed by a tool record that the output cites. The language model never computes and never types a digit. The Briefing lane enforces this with claim tokens that code fills; the Forecast lane enforces it by forcing reconciliation through a tool after the model's final answer.

Rationale: auditability is the product. A hallucinated number in a pharma commercial setting is worse than no number.

### II. Agents Explain and Propose; People Decide (NON-NEGOTIABLE)

Agents explain what changed, why, how sure they are and what to check next. They do not act on the business, revise a forecast, or send anything outside the team. No output leaves without analyst review. The Briefing lane adds a second gate (manager sign-off); the Forecast lane has one.

Rationale: the Proposal scopes both agents as first-pass analysts. Decisions stay with the brand team.

### III. Answer-Key Isolation (NON-NEGOTIABLE)

The answer key, the generator internals, the pre-artifact "true" data and any held-out parameters live in a store **outside this repository**. Only the evaluation harness reads them. No agent, tool, prompt, retrieval index, UI or log can reach them, and no file of theirs is committed. Hidden ground truth never crosses a handoff.

Rationale: a leaked key makes every score meaningless (EV-9.3, FE-30).

### IV. Typed Contracts at Every Handoff

Stages and agents exchange schema-validated objects, never free-form conversation. An object that fails its schema stops the stage and names the field. Renaming or repurposing a field is a contract version bump; new optional fields are allowed. Any payload that crosses a lane boundary carries its `run_id`, its pinned data version and its evidence references, so the receiver can trace it.

Rationale: the contract is the only coupling between stages and between teams.

### V. Abstain When Evidence Is Weak

When controls are missing or contaminated, sources conflict, data is unreliable, or no driver clears its test, the agent says so. It abstains, marks the driver inconclusive, or closes the story as "unresolved, investigate next". It never forces a single cause, and never spreads an unexplained remainder across drivers.

Rationale: a confident wrong attribution is the main failure mode for root-cause agents (P2-Q3, FM-Q3).

### VI. Synthetic Data Only

All data is synthetic and seeded. No patient, prescriber or proprietary data goes to any external model or service. Code is reproducible from its seed; model output is not, and is never presented as if it were. Each lane records which model provider it sends prompts to, and what those prompts contain (S14).

Rationale: the Proposal's data-use rule; Gemini is an external API.

### VII. Every Loop Ends by Construction

Every agentic loop has, as a minimum: call depth two (a manager calls specialists; specialists never call an agent; tools contain no model), a finite hypothesis catalog, a refusal to rerun a test with the same parameters, caps as a backstop, and a defined exit that never blocks the output. Each lane may make these rules stricter, never looser.

Rationale: the mentor's concern about runaway recursion (System Architecture §4c).

## Shared Platform Rules

These come from System Architecture §3 and §5. They bind every `core-*` spec and every lane that uses the platform.

- **One data world.** The repo's DuckDB data foundation (seed 7, release `day1-v1`) is the single data world for both agents (D7). Specs never hard-code its size.
- **One feed-health gate.** `reporting.v_feed_health` is stage 2 for both lanes. A failed cut is withheld or visibly qualified, never read as zero demand.
- **One semantic layer.** Versioned YAML validated by Pydantic holds every metric, dimension and threshold. Tools reject unknown metric IDs. Forecast adopts it when it ports to the shared world (S3).
- **Tool records.** Every tool call returns a record that outputs cite. Whether Briefing evidence items and Forecast tool records share one shape is S9; the rule in Principle I is not open.
- **Lane names.** Where both lanes use one word for different things, shared docs and code prefix it: `briefing.investigation_request`, `forecast.InvestigationRequest` (System Architecture §6).
- **No individual identified.** Rep calls and vacancies arrive aggregated at the source. No output line points to one person.
- **Shared stack base.** Python 3.11 or newer and DuckDB. Every other stack choice lives in a lane's `plan.md`, never here.

## Lane Constitutions

| Lane | File | Owners | Binds |
| :- | :- | :- | :- |
| Briefing | [.specify/memory/constitution-briefing.md](constitution-briefing.md) | Michael, Meghna | `specs/brief-*`, and the Briefing-only parts of `specs/core-*` |
| Forecast | `agents/forecast-explanation/.specify/memory/constitution.md` on branch `alvin-forecast-explanation` | Alvin, Sienna | `specs/fcst-*` once merged |

A plan's Constitution Check cites this file for every spec, and the lane constitution for every requirement that serves one lane only.

## Development Workflow

- Spec Kit loop per component: specify, clarify, plan, tasks, analyze, implement, converge. When reality disagrees with a spec, update the spec first, then the code.
- Specs are namespaced by owner: `core-###` (both teams), `brief-###` (Briefing), `fcst-###` (Forecast) (S12, Proposed).
- Specs say what and why; `plan.md` says how. Unknowns are marked `[NEEDS CLARIFICATION: …]` with the open-item ID they belong to. Do not guess.
- Each lane's personas and evaluation pack are referenced by ID and never edited from another lane (D3).
- If time runs short, cut features, not evaluation quality.

## Governance

This constitution supersedes other practices where they conflict. Source precedence is: the Proposal, then each lane's personas and evaluation pack, then the System Architecture, then each lane's architecture doc (System Architecture §1).

Amendments: propose the change in a spec or PR description, add a row to the System Architecture decision log, bump the version, update the Sync Impact Report above, and check every spec that cites the changed article. Principles I to III need approval from both teams.

Versioning: MAJOR for removing or redefining a principle; MINOR for adding a principle or materially expanding guidance (including contract rules); PATCH for wording.

Compliance: every plan passes a Constitution Check before implementation. Deviations are justified in the plan's Complexity Tracking; unjustified deviations block merge.

**Version**: 2.0.0 | **Ratified**: 2026-10-16 | **Last Amended**: 2026-10-23
