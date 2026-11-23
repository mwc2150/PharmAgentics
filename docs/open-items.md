# Open items

Work that is known and not done, across branches. This list changes in planning sessions, not on feature branches. Where the project stands day to day is not written here: run `uv run python -m pharmagentics.devtools.status`, which reads the handoffs in `docs/handoffs/` and git.

There is no `PROJECT_STATE.md` any more. Every branch used to add an entry at its top, so every parallel merge conflicted on it. A branch now records its state in its own new handoff file (`docs/handoffs/README.md`). If a merge of an older branch shows a conflict on `PROJECT_STATE.md`, drop that file and move the branch's entry into its handoff. The entries up to 2026-11-23 are kept word for word in `docs/handoffs/2026-11-23-project-state-history.md`.

Carried over from the entries of 2026-11-22 and 2026-11-23. Read the handoff named before acting: some may have moved since.

- Keycloak deploy script: `put_secret` destroyed the secret version the running revision mounted (fixed by hand on 2026-11-23). The script fix (pin Keycloak to the new version, prune only after it serves; `setup` no longer prunes the realm secret) is committed on `fix/keycloak-secret-pin`, not pushed or merged.
- Golden set: the P4-Q3 and WIN-2 findings omit promotion for the Southeast gap (Michael). `docs/handoffs/2026-11-23-brief-010-integration.md`
- Golden set: Michael reviews the golden edits before `key_fact_recall` and `finding_recall` join the gated checks (core-011 FR-006). `docs/handoffs/2026-11-22-core-011-integration.md`
- Forecast: Alvin to agree whether Haiku replaces Qwen once the designs are set; the hosted app would bill the team key. `docs/handoffs/2026-11-22-fcst-haiku-option.md`
- From the whole-repo review: the eval gate passes a metric that is missing on one run, and `claims_reconcile` runs evidence SQL unguarded. `docs/handoffs/2026-11-22-forecast-review-fixes.md`
- UI: no Spec Kit spec covers the theme (DESIGN.md does); drop the token aliases once the other UI branches merge. `docs/handoffs/2026-11-22-ui-refresh.md`
- Repo layout (ADR 0004): a later pass over the `frontend/` docs once the UI branches settle. `docs/handoffs/2026-11-23-repo-layout.md`
