---
branch: feature/v2-assumptions-first
lane: briefing
next: Michael tops up the Anthropic credit, then runs the release steps below; the settings and light-mode branch gets its own pull request
---

# PharmAgentics v2: the brief follows its Assumptions (2026-11-27)

Merged into `main` from `feature/v2-assumptions-first` (62 commits on `origin/main` 09cb1ed). The packet handoffs keep their own detail: `2026-11-27-lipidara-cases.md`, `2026-11-27-uat-review.md`, `2026-11-27-promo-verdict.md`, `2026-11-27-marketer-view.md`.

## What v2 is

- **brief-011, the brief follows its Assumptions.** No comparison window the brief does not state; inside the normal range nothing is credited, for every question and brand; a lapse the period falls in is named.
- **brief-012, sign-off and personas.** Two-step sign-off (the Commercial Analyst sends, the Insights Manager signs off or returns with a comment and flags), Insights Manager (P2) and Marketer (P4) roles, the Evaluation page limited by role (the Brand Manager keeps it), seven UAT logins. P2 asks follow-ups on the briefs sent to them and votes on the answers.
- **brief-013, promotion verdict and Marketer view.** Controls first (`not_separable`), `not_testable` where no channel moved, new patients first, four channels, comparison with territories whose promotion held. The Marketer sees a promotion read under each territory story and the budget note (Q15).
- **brief-014, Lipidara (BXC).** Lag-tested driver checks, the lapse rule and Promotion review, the question reader, plan and continuing cards by brand, and the agent engine taking the brand from the run. 24 golden cases, C-033 to C-056 (drafts).
- **brief-015, Briefing workspace.** The Overview, New briefing and Approved tabs split: brand is a field of the New briefing form; the Overview keeps its own brand and week for exploring; the workspace band is frosted; every fold shows a chevron; a follow-up thread asks for a vote on its newest answer only; the sidebar names the release ("PharmAgentics v2").
- Follow-ups: free text goes to the agent and counts toward the 20; chips stay scripted and free; with no model the free-text box is disabled with its reason.
- UAT review v1 (`docs/reviews/2026-11-27-uat-review-v1.md`, 39 findings) and the `uat-review` skill; fixes for its U and server items (security headers, decided-brief approval rate, readable plan names, written dates in the question reader).

## Golden set

Change records in `eval/golden/changes/`: `2026-11-27-lipidara-cases.md`, `2026-11-27-southeast-lapse-and-rev-1.md` (P4-Q3 and WIN-2 credit promotion for the Southeast lapse; REV-1, C-057, reviewed), `2026-11-27-promotion-not-testable.md`. Counts: 51 Cardiovela and 24 Lipidara Briefing cases.

## Evaluation

- Gates (scripted, run in the merge worktree's MLflow store), both exit 0:
  - Cardiovela: `eval gate 42165fe9e0ee4a09959c75147d44bbd1 8691720f4ee7401a95334b9d736c0931` (`briefing_scripted`, 33 against 32 cases)
  - Lipidara: `eval gate 20c2323ff8fb480ebbeea6816513e06f 65245c85041b4553a14fc7996db4edc4` (`briefing_scripted@BXC`, 24 cases)
- Haiku (`briefing_agent`, `anthropic:claude-haiku-5-5`, three passes, main checkout's store):
  - Cardiovela `55bafa9245bf42648ac9c88c5aa9bfe3` (33 cases): every gated check 1.000, `run_errors` 0, `key_fact_recall_pooled` 1.000, `finding_recall_pooled` 0.971, `scope_match` 0.794. `eval gate 55bafa9245bf42648ac9c88c5aa9bfe3 377b37f27acc4dc4934f6c4ad0a1d6aa` (the earlier Haiku baseline: 1.000, 0.971, 0.802) exits 0.
  - Lipidara `ca92e2ec228d42beb1df3ecfc0538c7e` (24 cases): **pass 3 is void.** The Anthropic credit ran out ("credit balance is too low"), so 15 of its 24 cases crashed. Passes 1 and 2 (`e4a56ff44adf4b78b77417ca731b0b6b`, `eeceae3667ac4ac79129f185ca97a2b8`) are clean and identical on the gated checks: `run_errors` 0, `claims_reconcile`, `links_resolve`, `must_not_say`, `numbers_traced`, `no_individual_rep`, `governed_terms` all 1.000, `false_drivers` 0; `key_fact_recall_pooled` 0.780, `finding_recall_pooled` 0.714, `scope_match` 0.683. This is the agent's first Lipidara run, so there is no Haiku baseline; recall is under the targets (0.85, 0.90), as the scripted engine's was before tuning. Rerun the three passes once the credit is topped up and use that run as the Lipidara Haiku baseline.
- `uv run pytest` (1436 passed) and the frontend type check pass on the branch tip; the UI checks (`tests/ui/check_layout_fixes.py` 53 of 53 on a fresh state, `check_workspace_split.py` 9 of 9) pass on the local preview, which runs the settings branch built on this tip.

## Release steps (Michael)

1. **Top up the Anthropic credit first.** The hosted app's agent runs on Haiku with the same key; until the credit is back, free-text follow-ups and agent briefs fail.
2. `uv run python deploy/gcp.py telemetry --project pharmagentics --account <you>` (fresh scores on the Evaluation page).
3. `uv run python deploy/make_env.py`, then `deploy/gcp.py env-push` (the P2 and P4 login passwords), then `deploy/gcp.py keycloak` (the realm with the seven logins).
4. The app itself deploys on the merge once CI passes.

## Notes for Alvin and Sienna (Forecast lane; nothing of theirs was edited)

- The mentor's review items in their lane (2.4 first half, 3.8 to 3.10, 3.13) and H-3 of the v1 UAT review (Briefing and Forecast describe the Southeast fall differently) are theirs to answer.
- The Briefing question reader now takes written dates (Aug 24, 2026; 24 Aug 2026; 8/24/2026); the Forecast reader may want the same.
- App-wide visuals reach the Forecast screens: the frosted workspace band, the fold chevrons, and the account name on phones. Forecast roles' actions and logins are exactly as before v2; the Forecast lane keeps Evaluation.

## Open

- The Lipidara Haiku rerun (above) and tuning toward the recall targets.
- The settings and light-mode branch (`feature/settings-light-mode`, worktree `pa-v2-settings`) rebases on this merge and gets its own pull request; its handoff is `2026-11-27-settings-light-mode.md` on that branch.
- Lipidara golden cases are drafts (`reviewed: false`) apart from what the change records say.
