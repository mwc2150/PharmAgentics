---
branch: feature/overview-workspace
lane: shared
next: Michael reviews on the preview; the later commits are local, not pushed (Michael, 2026-11-27: leave the PR for now); merge after PR #36 (stacked on it); then a note to Alvin and Sienna on the Forecast changes below
---

# The Overview workspace, Your briefings and Your reports (2026-11-27)

Stacked on `feature/settings-light-mode` (PR #36), which now carries `main` (v2 and the Haiku cost work). Decisions, Michael 2026-11-27:

- The Overview leaves the Weekly briefing and becomes its own workspace, first in the sidebar. It keeps its brand, week, tiles, territory list and drawers, and it is where the app greets.
- From a territory it offers what the role can start: **Brief this week** (fills the New briefing form with brand, territory and week; nothing runs) and **Explain the forecast miss** (reads "Week of D, Territory: How much of the miss does each driver explain?" into the Forecast scope card to check; nothing runs). The forecast option shows only for Cardiovela and only to a role with Forecast access, which today is the test login.
- Who has it: the Commercial Analyst and the Insights Manager open it (new role action `overview` in `roles.json`; the Insights Manager can inspect but has no button to start anything) and start on it. The Director and the Marketer have the item and read: "The Overview is open to the Commercial Analyst and the Insights Manager. Ask one of them for viewing access." The Forecast roles' sidebar is unchanged; who sees what is to be sorted out later.
- Weekly briefing tabs: **New briefing** and **Your briefings**. Forecast tabs: **New explanation** and **Your reports** (the Brand Manager: one **Reports** tab).
- Your briefings and Your reports have the same sections, by whose move it is: **Approved** (everything leadership sees on the current release), **Needs you** (returned items and drafts; a brief still generating too), **With the reviewer** (the Brand Manager's view: **With the analyst**), and a closed **Rejected (n)** fold. Your reports lists both things the Brand Manager reviews, reports and question runs, each row saying which (as before the remodel, where the runs were "Your forecast questions" and "Waiting for your review").
- The greeting is on the Overview only. Forecast's "Forecast versus actual, through Oct 5, 2026." moved into its intro: "Ask about forecast versus actual TRx for BXA Cardiovela, with data through Oct 5, 2026: …".
- Every workspace starts 24 px below the header (20 px on phones), as the Weekly briefing's tab row does.
- The Evaluation page names each Briefing run's brand ("Briefing agent · Lipidara", "· Cardiovela").

## Later the same day (local commits, not pushed)

- New briefing: **Your briefing questions** under the form (spec I11), the counterpart of Forecast's "Your forecast questions", which stays as it is. Six example questions above the form read into it like a typed question. `/api/briefing/mine` rows carry `question` (as asked, scope prefix off) and `promotion_review`; a Promotion review's row says "release-wide Promotion review" instead of its latest week, in both lists. A brief opened from the questions returns to New briefing ("Back to New briefing").
- On the preview, six questions were asked through the bar and the examples, read by Haiku and generated with the scripted engine, so the list has entries.
- Hover text follows the pointer: `HoverTips.tsx`, one layer mounted in `main.tsx`, shows an element's `title` (held off the element while hovered, so the browser's own tooltip does not open under the cursor, and put back after) or `data-tip`. Chart marks (`Memo.tsx`, `ForecastCharts.tsx`) moved their SVG `<title>` to `data-tip` (each chart is `role="img"` with its own label). Definition option notes follow the pointer for a mouse and stay anchored for the keyboard and touch.
- The data classification is a quiet chip (shield, the level in sentence case, a four-step meter from Public to Sensitive; hover gives the meaning) instead of a bare upper-case word.
- How it works opens and closes by growing and shrinking (`.pa-expand`), its section headings are tiles, its sections arrive in sequence, and the steps and actor cards arrive one by one when seen (`.pa-reveal`). Reduced motion: no transition.
- Overview: the count line became a call to action naming what the role can start ("Pick a territory to brief its week, or any figure to see its query."; the Insights Manager: "…to see how its week went…").
- Checks on the preview: a scratch check (27 items: the list, the examples, the tips, the chip, How it works, reduced motion, phone width) passed; `check_workspace_split.py` 11 of 11, `check_settings.py` 51 of 51 (0 contrast failures), the site-wide motion check 24 of 24; `tests/test_signoff.py` 27 passed.

## What changed

- API: `GET /api/briefing/mine` (this login's briefs in every state on the current release, newest first; no evidence; a pseudonym, never a person); `/api/briefing/overview` allows the `overview` action instead of `run`. `deploy/README.md` role table updated.
- Frontend: `OverviewWorkspace` and `YourBriefings` (App.tsx), `ForecastReports` rewritten into the sections with question runs, `Overview` takes `onBrief` / `onForecast`, `listMine` in `briefingApi.ts`, a `grid` icon.
- Spec: `specs/brief-015-briefing-workspace/spec.md` I1, I2 updated, I9 (who has the Overview) and I10 (Your briefings) added.

## Checks

- `tests/test_signoff.py::test_your_briefings_lists_this_logins_briefs_in_every_state_and_nobody_elses`, `tests/test_overview.py` (P1 and P2 open it, P3 and P4 do not); API and auth tests 159 passed.
- UI on the 8765 preview: `check_workspace_split.py` 11 of 11, `check_settings.py` 51 of 51 (0 contrast failures), a role walkthrough (27 checks: who starts where, which buttons each role sees, the forecast option reading its question, the sections), the motion checks (14 and 24). `check_layout_fixes.py` and `review_walkthrough.py` follow the new tabs (not rerun end to end here).

## Notes for Alvin and Sienna (Forecast lane)

Forecast's tabs became New explanation and Your reports (the Brand Manager: Reports), with the sections above; question runs are listed there too, so the Brand Manager reaches runs waiting for review from Reports (back returns there). The greeting left the Forecast workspace and its date moved into the intro. The Overview can open the Forecast form with a question filled in, for roles that already have Forecast access. Later the same day: hover text across the app, the Forecast charts' bars included, sits beside the pointer instead of under it (`HoverTips.tsx`). No Forecast access, login or engine behaviour changed.

## Open

- New explanation keeps its "Your forecast questions" list (Michael: keep it; Briefing now has the same).
- Proposed, not built: a Recents / View all block in the sidebar (as in Claude's web app) for quick access to Your briefings and Your reports.
- Held-out results: none yet. The Evaluation page shows the golden (development) runs; the held-out run reads the private store and is a separate step Michael asks for (due Dec 4).
