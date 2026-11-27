# brief-015: The Briefing workspace in v2

**Spec ID**: brief-015-briefing-workspace (Briefing lane)
**Created**: 2026-11-27 (v2; written after the code, invariants and acceptance tests only, per the v2 spec format)
**Branch**: feature/v2-assumptions-first
**Source**: Michael, 2026-11-27 (the Overview and New briefing; later the same day, the Overview as its own workspace and Your briefings; selector descriptions; the frosted band; the Insights Manager's follow-ups); the v1 UAT review `docs/reviews/2026-11-27-uat-review-v1.md` (C-6, U-5, U-6, U-12).

## Invariants

- **I1. Exploring never changes the work.** The Overview is its own workspace, first in the sidebar, with its own brand and week; changing them never changes the New briefing form, and the form never changes them. From a territory it offers what the role can start: "Brief this week", which carries its brand, territory and week to the form (nothing runs yet), and, for Cardiovela and a role with Forecast access, "Explain the forecast miss", which reads a question for that territory and week into the Forecast scope card to check (nothing runs yet).
- **I2. The brand is a choice of the brief.** The New briefing form has a Brand field. The Overview has its own brand selector beside its week selector; the tab row has no brand toggle; Your briefings lists every brand, each row labelled.
- **I9. Who has the Overview.** The Commercial Analyst and the Insights Manager open it (role action `overview`) and start on it; it is where the app greets. The Director and the Marketer have the sidebar item and read who can grant viewing access. The Forecast roles' sidebar is unchanged.
- **I10. Your briefings, by whose move it is.** The Weekly briefing has two tabs, New briefing and Your briefings. Your briefings lists, in order: Approved (every signed-off briefing on the current data release, what leadership sees), Needs you (returned with a comment, drafts, and a run still going), With the reviewer (sent for sign-off), and a closed Rejected fold. A brief made and left is still there to open (`GET /api/briefing/mine`: this login's briefs in every state, no evidence, no person named). Forecast's Your reports has the same sections for its reports and question runs.
- **I11. Your briefing questions, under the form.** As Forecast lists its questions under New explanation, New briefing lists, under its form, every brief this login started from a question (typed in the bar, or one of the form's example questions), newest first, each titled by the question as asked; a brief made from the form alone is listed only under Your briefings. A brief opened from it returns to New briefing. Example questions above the form read into it like a typed question; nothing runs until Generate. `GET /api/briefing/mine` carries each brief's question without its scope prefix, and whether it is a release-wide Promotion review (its row names that instead of a week).
- **I3. The form reads the dates the app prints.** The Briefing question reader takes "Aug 24, 2026", "24 Aug 2026" and "8/24/2026" as the week typed; a date that is not a real day is named, never silently replaced by the latest week. The Forecast lane's reading is unchanged.
- **I4. Selector descriptions on demand.** Each brief-definition option's description shows on hover or focus and is always the input's accessible description.
- **I5. Nothing covers what you are doing.** A reason or comment box (Reject, Return) is never under the floating bars; one vote prompt shows at a time (in a follow-up thread, on the newest answer only); at 390 px no table cell is clipped, the account button shows a name, and controls have a 24 px target.
- **I6. The Insights Manager asks follow-ups** from the brief they are signing off (brief-012 I3).
- **I7. The workspace band is frosted**: the page scrolls under it, blurred; print is unchanged.
- **I8. Every fold shows that it folds.** Each collapsible section (a `<details>` summary, or a button with `aria-expanded` that folds content) has a chevron before or beside its label, pointing right when shut and down when open; it is not printed. App-wide, so the Forecast and Evaluation folds carry it too (a visual only; no Forecast behaviour changes).

## Acceptance tests

- `tests/ui/check_workspace_split.py` (I1, I2, I8, I10). `tests/ui/check_layout_fixes.py` (I5).
- `tests/test_overview.py::test_the_analyst_and_the_insights_manager_open_it_and_the_leaders_do_not` (I9); `tests/test_signoff.py::test_your_briefings_lists_this_logins_briefs_in_every_state_and_nobody_elses` (I10), `::test_a_briefs_question_is_listed_as_the_analyst_asked_it` (I11).
- `tests/test_comparison_windows.py::test_the_briefing_reader_takes_the_dates_the_app_prints`, `::test_a_date_that_is_not_a_real_day_is_named_not_ignored`, `::test_the_forecast_reading_of_written_dates_is_unchanged` (I3).
- `tests/test_threads.py` (I6).
