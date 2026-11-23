@README.md

# specs rules

- Never delete a spec. Mark a superseded one "History" in `specs/README.md`, with what replaced it.
- Code may run ahead of its spec while iterating. The spec and the branch's handoff in `conversations/` catch up in the same pull request.
- Flow: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Spec Kit finds the active spec from `.specify/feature.json`, not from the branch.
- Do not edit `fcst-###` specs (Forecast lane). Cite them by ID.
- Mark unknowns `[NEEDS CLARIFICATION: … (open-item ID)]`. Do not guess.
