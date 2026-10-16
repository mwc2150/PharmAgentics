# PharmAgentics

Multi-agent first-pass forensic analyst for pharma brand performance. Course capstone (IEOR4573E). Built with Spec Kit (spec-driven development).

## Read first
- `.specify/memory/constitution.md` — binding principles
- `docs/planning/` — Architecture.docx (source of truth for the Briefing Agent), Evaluation Pack.docx, Personas.docx, proposal PDF, data research brief
- `data/agent_visible/README.md` and `data_dictionary.json` — the synthetic data world

## Hard rules
- **Never read, open, grep, index or copy anything in `eval_private/`** while building or running agents. It holds the answer key and the true pre-artifact data. Only the eval harness may use it, and only when the user asks for evaluation work.
- Agent tools may read only `data/agent_visible/`.
- No digit in any generated brief may come from the LLM; use claim tokens.
- Say "competitive intelligence", never "statistical surveillance".
- Mark unknowns `[NEEDS CLARIFICATION: …]`; do not guess.

## Decisions (2026-10-16, user)
- Each use case has its own Magentic loop. The decision to pursue a use case is deterministic and code-driven, with no agent. This settles Architecture open item A2; no mentor approval is needed.
- `data/agent_visible/` is a sample (8 territories, 4 specialties, 104 weeks) to show the feel of the data definitions. It will be expanded. Specs must not hard-code these sizes.
- Spec-writing only for now. No code, and no git init or push until the user asks. A push to an existing GitHub repo comes later.

## Workflow
`/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`. One spec per component (Architecture §14).
