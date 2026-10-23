<!--
Sync Impact Report
- New file, 2026-10-23. Carries the Briefing-only articles of the project
  constitution v1.0.0 (2026-10-16) after the shared articles moved to
  .specify/memory/constitution.md v2.0.0.
- Mapping from v1.0.0: II → B-I, III → B-II, IV → B-III, V → B-IV, VII → B-V,
  IX → B-VI, XII → B-VII. The v1.0.0 "Additional Constraints" are kept below.
- Updated for the Oct 21 personas: P4 Marketer added; promotion verdict rule
  (Architecture decision 20).
-->

# PharmAgentics Briefing Lane Constitution

Lane: Weekly Brand-Performance Briefing Agent. Owners: Michael, Meghna.
Source of truth, in order: the Proposal; the Briefing Personas and Evaluation Pack; the System Architecture; the Briefing Architecture (all in `docs/planning/`).

These articles add to the shared constitution (`.specify/memory/constitution.md`). They never loosen it. They bind every `specs/brief-*` spec and every Briefing-only requirement in a `specs/core-*` spec.

## Lane Articles

### B-I. One Semantic Layer

Metric definitions, dimensions, materiality thresholds, the hypothesis catalog, loop caps and governed terms live only in the versioned semantic layer. Prompts, tools, verifiers and glossaries read from it. Nothing is redefined elsewhere.

### B-II. Deterministic, Agentic, or Human — Declared

Use code where the answer is knowable, an agent where the path is not, and a person where judgment stays uncertain. Every component states its mode in the autonomy ledger (Briefing Architecture §9). A component not listed as agentic must not claim autonomy.

### B-III. Pinned Data Version

Every run pins one data snapshot plus semantic-layer, model, prompt and code versions. Every claim reconciles to that snapshot and links to it. A restated week is flagged, never silently overwritten or double-counted. The restatement window is a semantic-layer setting (S4).

### B-IV. Traceable by Construction

Every stage, tool call, agent turn and model call emits a span. Every claim links to an evidence item and to the span that produced it. A reviewer reaches the source of any number in one step.

### B-V. Bounded Loops, Full Strength

The stage 4 loop applies shared Principle VII in full: call depth two, hypotheses only from the catalog, a no-repeat ledger, caps on rounds, stalls, tool calls, Data Forensics calls, wall time, tokens and brief length. A story that hits a cap closes as "unresolved, investigate next", keeps its evidence, and the run continues to stage 5.

### B-VI. No Individual Is Identified

No brief line identifies an individual rep, including promotion results read by P4. Rep-level activity is aggregated or suppressed inside the tools, before any agent sees it, to the floor the semantic layer sets (Evaluation Pack open item 5).

### B-VII. Evaluation Gate

Eval items live in the Evaluation Pack. Specs cite them by ID (EV-x.y) and user stories by persona question ID (P1-Q1 to P4-Q6). The Evaluation Pack changes first, then the specs. Targets may be set or tightened until held-out results are seen, and never loosened after. No change merges if the evaluation suite regresses.

## Lane Constraints

- **Terminology.** Stage 3 is "competitive intelligence". "Statistical surveillance" and "surveillance" are not used in any doc, prompt or brief (S8). "New patients" is used only for NBRx, never for NRx.
- **Reader-facing text.** ASD-STE100 principles: short sentences, one word with one meaning, paired with business framing for tone.
- **Confidence.** High, Medium or Low. High: one explanation supported, the others ruled out. Medium: one supported, alternatives open. Low: the agent abstains and lists the story under "investigate next". Causal wording appears only at High.
- **Promotion.** Promotion is one tested driver with a verdict either way. The brief never credits promotion in a week where promotion activity did not change. No attribution or ROI model in v1 (decision 20, A16).
- **Baselines.** Manual, scripted, low-code and custom-agent versions stay runnable. All run on the same cases and are scored by the same eval items. The scripted version is the manager-off ablation.
- **Technology.** Stack choices belong in `plan.md`. The lane's working stack is in Briefing Architecture §13.

## Governance

Amendments follow the shared constitution's process, with a row in the Briefing Architecture decision log (§16). Michael and Meghna approve lane amendments. A lane article that becomes shared moves to the shared constitution by a MINOR bump there.

**Version**: 1.0.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-23
