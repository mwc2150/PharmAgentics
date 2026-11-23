# Project state

Where things stand is no longer written in this file. Run:

```
uv run python -m pharmagentics.devtools.status
```

It lists the handoffs on branches that have not merged yet, then the latest handoffs on `main`, each with its next step. Handoffs live in `conversations/`; their format is in `conversations/README.md`.

**Do not add dated entries here.** Every branch used to add one at the top, so every parallel merge conflicted on this file. A branch now records its state in its own new handoff file, which no other branch touches. If a merge shows a conflict in this file, keep `main`'s version and put your entry in your handoff. This file changes only when the list below changes, in a planning session.

The entries up to 2026-11-23 are kept word for word in `conversations/2026-11-23-project-state-history.md`.

## Open items

Carried over from the entries of 2026-11-22 and 2026-11-23. Read the handoff named before acting: some may have moved since.

- Keycloak deploy script: `put_secret` destroyed the secret version the running revision mounted; fixed by hand, and the script fix is on the local branch `fix/keycloak-secret-pin`, not pushed.
- Golden set: the P4-Q3 and WIN-2 findings omit promotion for the Southeast gap (Michael). `conversations/2026-11-23-brief-010-integration.md`
- Golden set: Michael reviews the golden edits before `key_fact_recall` and `finding_recall` join the gated checks (core-011 FR-006). `conversations/2026-11-22-core-011-integration.md`
- Forecast: Alvin to agree whether Haiku replaces Qwen once the designs are set; the hosted app would bill the team key. `conversations/2026-11-22-fcst-haiku-option.md`
- From the whole-repo review: the eval gate passes a metric that is missing on one run, and `claims_reconcile` runs evidence SQL unguarded. `conversations/2026-11-22-forecast-review-fixes.md`
- UI: no Spec Kit spec covers the theme (DESIGN.md does); drop the token aliases once the other UI branches merge. `conversations/2026-11-22-ui-refresh.md`
- Repo layout (ADR 0004): a later pass over the `frontend/` docs once the UI branches settle. `conversations/2026-11-23-repo-layout.md`
