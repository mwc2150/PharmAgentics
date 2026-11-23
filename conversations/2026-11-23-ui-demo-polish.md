# 2026-11-23 — UI demo polish (Briefing form, runs in progress, teal, names)

Michael asked for a clean demo: six UI items, planned first and approved as recommended. Claude Opus planned, did the teal theme and the names itself, and gave two packets to Sonnet agents in worktrees (form: `feature/ui-demo-form`; runs in progress: `feature/ui-demo-progress`). Both are merged into `feature/ui-demo-polish` off `main` 604ae24.

## Decisions (Michael)
1. "Make primary" is gone. Territories counted, Measure and Relative to: a **Main** radio choice plus **"Also show beside it"** checkboxes; the request is still `[main, ...extras]`. Grain: plain checkboxes with a one-line description (the server re-sorts grain, `tools/definition.py`, so its order meant nothing).
2. Compare with: the row layout only; row 1's first option is "Default: the 4 weeks before the period" (sends no comparison, as before). Extra rows are "Also compare with"; adding one turns a Default row 1 into "previous min(4, earlier) weeks".
3. One question box: the bottom bar reads the question and fills the form; it never starts a brief. The form shows the question, who read it, the reader's notes and Clear.
4. Teal #2a8c7c for fills, plus a lighter `primaryink` #45b8a3 for accent text (AA on panels).
5. No page-reload recovery for runs this round.
6. Names, with no "UAT": Ace (Briefing and Forecast analyst), Diana (Brand Director, P3), Miranda (Brand Manager; Michael asked for a name that alliterates with the role and has its syllable count, as Diana does with Director), Tester. Greeting: "Good afternoon, Ace."

## Where things are
- `BriefDefinition.tsx` (Main/Also, grain descriptions, Assumptions words "X; also Y"), `ComparisonPicker.tsx`, `BriefingScope.tsx` (`useQuestionReader` replaces `QuestionReader`), `MessageBar.tsx` (`onRead`), `App.tsx` (`runView`, status line, `opened` approved brief, `SideNav` dots, Forecast workspace kept mounted, `SignedInName` context for the greeting).
- Realm: `deploy/keycloak/realm-pharmagentics.json` (firstName only); dev stand-ins: `src/pharmagentics/api/auth.py` `DEV_USERS`.
- Tokens: `frontend/figma-make/src/index.css`; DESIGN.md.

## Checks
- `tsc`, Vite build; 159 focused tests (`test_feedback`, `test_feedback_votes`, `test_rbac`, `test_brand_access`, `test_deploy`, `test_frontend_scope`, `test_classification`). `test_frontend_scope` was updated for the new form wording.
- Playwright walk on the running app (API :8010 dev auth with Haiku, Vite :5180): no page errors; see PROJECT_STATE for what it covered.

## Open
- `/code-review` and Bombadil not run.
- The hosted Keycloak still serves the old realm until `uv run python deploy/gcp.py keycloak --project <ID>` (by hand). Local compose re-imports on start.
- Forecast persona names (Ace, Miranda) are for the logins only; Alvin and Sienna may want to confirm them.
- `feature/materialize-views` is a separate PR; both add a PROJECT_STATE entry at the top, so the second to merge resolves a one-hunk conflict.
