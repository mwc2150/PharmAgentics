# brief-015: The Briefing workspace in v2

**Spec ID**: brief-015-briefing-workspace (Briefing lane)
**Created**: 2026-11-27 (v2; written after the code, invariants and acceptance tests only, per the v2 spec format)
**Branch**: feature/v2-assumptions-first
**Source**: Michael, 2026-11-27 (the Overview and New briefing; selector descriptions; the frosted band; the Insights Manager's follow-ups); the v1 UAT review `docs/reviews/2026-11-27-uat-review-v1.md` (C-6, U-5, U-6, U-12).

## Invariants

- **I1. Exploring never changes the work.** The Overview has its own brand and week; changing them never changes the New briefing form, and the form never changes them. The one link is the Overview's "Generate brief for <territory>", which carries its brand, territory and week to the form.
- **I2. The brand is a choice of the brief.** The New briefing form has a Brand field. The Overview has its own brand selector beside its week selector; the tab row has no brand toggle; the Approved tab lists every brand, each row labelled.
- **I3. The form reads the dates the app prints.** The Briefing question reader takes "Aug 24, 2026", "24 Aug 2026" and "8/24/2026" as the week typed; a date that is not a real day is named, never silently replaced by the latest week. The Forecast lane's reading is unchanged.
- **I4. Selector descriptions on demand.** Each brief-definition option's description shows on hover or focus and is always the input's accessible description.
- **I5. Nothing covers what you are doing.** A reason or comment box (Reject, Return) is never under the floating bars; one vote prompt shows at a time (in a follow-up thread, on the newest answer only); at 390 px no table cell is clipped, the account button shows a name, and controls have a 24 px target.
- **I6. The Insights Manager asks follow-ups** from the brief they are signing off (brief-012 I3).
- **I7. The workspace band is frosted**: the page scrolls under it, blurred; print is unchanged.
- **I8. Every fold shows that it folds.** Each collapsible section (a `<details>` summary, or a button with `aria-expanded` that folds content) has a chevron before or beside its label, pointing right when shut and down when open; it is not printed. App-wide, so the Forecast and Evaluation folds carry it too (a visual only; no Forecast behaviour changes).

## Acceptance tests

- `tests/ui/check_workspace_split.py` (I1, I2, I8). `tests/ui/check_layout_fixes.py` (I5).
- `tests/test_comparison_windows.py::test_the_briefing_reader_takes_the_dates_the_app_prints`, `::test_a_date_that_is_not_a_real_day_is_named_not_ignored`, `::test_the_forecast_reading_of_written_dates_is_unchanged` (I3).
- `tests/test_threads.py` (I6).
