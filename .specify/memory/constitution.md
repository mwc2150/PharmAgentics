# PharmAgentics Constitution

Source of truth: the Proposal, the Briefing Agent Personas and the Evaluation Pack, then the Architecture doc (`docs/planning/`). This constitution binds the Briefing Agent. The Forecast-Explanation Agent adopts it unless its own amendment says otherwise.

## Core Principles

### I. Every Number Comes From a Tool (NON-NEGOTIABLE)
The LLM never computes and never types a digit. Numbers in any output are claim tokens that code fills from evidence. A digit that does not come from a token fails the brief.

### II. One Semantic Layer
Metric definitions, dimensions, materiality thresholds, the hypothesis catalog and governed terms live only in the versioned semantic layer. Tools reject any metric ID the layer does not hold. Prompts, verifiers and glossaries read from it. Nothing is redefined elsewhere.

### III. Deterministic, Agentic, or Human — Declared
Use code where the answer is knowable, an agent where the path is not known, and a person where judgment stays uncertain. Every component states which mode it is in the autonomy ledger. A component not listed as agentic is not allowed to claim autonomy.

### IV. Pinned Data Version
Every run pins one data snapshot plus model, prompt and code versions. Every claim reconciles to that snapshot and links to it. Weeks restated inside the restatement window are flagged, never silently overwritten or double-counted.

### V. Traceable by Construction
Every step emits a span. Every claim links to an evidence item and to the span that produced it. A reviewer reaches the source of any number in one step.

### VI. Typed Handoffs
Stages exchange typed, schema-validated objects, not free-form agent conversation. Requests and results that fail their schema stop the run.

### VII. Bounded Loops
Agentic loops end by construction: two call levels only, tools are plain functions with no LLM inside, hypotheses come from a finite catalog, and a test is never rerun with the same parameters. Caps are the backstop. A story that hits a cap closes as "unresolved, investigate next" and the run continues.

### VIII. The Agent Proposes, People Decide (NON-NEGOTIABLE)
No brief leaves the team without analyst review and manager sign-off. Triage goes to the analyst by exception. The agent never acts outside the brief.

### IX. No Individual Is Identified
No output line identifies an individual rep. Rep-level activity is aggregated or suppressed inside the tools, before any agent sees it.

### X. Synthetic Data Only
No patient or proprietary data goes to an external model. All data is synthetic and seeded. Code is reproducible from its seed; LLM output is not, and is never presented as if it were.

### XI. Answer-Key Isolation (NON-NEGOTIABLE)
No agent, tool, retrieval index or prompt can read the answer key, the generator internals or the pre-artifact "true" data. Only the evaluation harness can. These live in a separate store with a tool allowlist that excludes them.

### XII. Evaluation Gate
Eval items live in the Evaluation Pack. Component specs cite them by ID (EV-x.y). The Evaluation Pack changes first, then the specs. Targets may be set or tightened until held-out results are seen, and never loosened after. No change merges if the evaluation suite regresses.

## Additional Constraints

- **Terminology.** Use "competitive intelligence" for the change-detection stage. Never use "statistical surveillance" in any project doc, prompt or brief. Use "new patients" only for NBRx, never for NRx.
- **Reader-facing text.** Follow ASD-STE100 principles: short sentences, one word with one meaning, paired with business framing for tone.
- **Confidence.** High, Medium or Low. Causal wording ("driven by") appears only at High. Low means the agent abstains and lists the story under "investigate next".
- **Baselines.** Scripted, low-code and custom-agent versions stay runnable. All run on the same cases and are scored by the same eval items. The scripted version is the manager-off ablation.
- **Technology.** Stack choices belong in `plan.md`, not in specs or this constitution.

## Development Workflow

- Spec Kit loop per component: specify, clarify, plan, tasks, implement, converge. When reality disagrees with a spec, update the spec first, then the code.
- Each component gets one spec. White-box tests (tool unit tests, router parameter accuracy, loop guardrails, validation-gate catch rates) live in that spec's `tasks.md`.
- Open items are marked `[NEEDS CLARIFICATION: …]` and resolved in the spec's clarify step. Do not guess.
- Prototypes stay runnable because they become baselines.
- If time runs short, cut features, not evaluation quality.

## Governance

This constitution supersedes other practices. An amendment needs a decision-log row in the Architecture doc, a version bump, and a check of every spec that cites the changed principle. Plans must pass a constitution check before implementation. Complexity must be justified against the autonomy ledger.

**Version**: 1.0.0 | **Ratified**: 2026-10-16 | **Last Amended**: 2026-10-16
