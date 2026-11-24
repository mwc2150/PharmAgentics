---
branch: fix/static-revalidate
lane: shared
next: Optionally nudge the class to fill in the questionnaire, then re-run the feedback export and commit the workbook again
---

# Class demo feedback export

After the class demo, `uv run python deploy/gcp.py feedback --project pharmagentics --account mwc2150@columbia.edu` wrote `feedback/class-demo-feedback.xlsx`, committed as 3fd942d on `fix/static-revalidate` (not pushed). This branch was merged to `main` as PR #34 (09cb1ed) before the commit, so the workbook commit needs its own PR or a cherry-pick onto a fresh branch off `origin/main`.

## What came in

The state bucket holds four feedback documents in all, every one from the shared tester login:

- Comment, 2026-11-23 23:00 UTC: "the app is alright, i guess" (Michael's test).
- Questionnaire, 2026-11-23 23:01 UTC: 3/3/3, recommend 5, "bleh" (Michael's test). This single response is the whole UMUX-Lite 50 and NPS -100.
- Comment, 2026-11-24 01:24 UTC: "Focus on business. You guys know your Tech Stack already! Great job!" The only entry from the demo.
- Session rating "good", 2026-11-20 (before the demo, likely a test).
- No answer votes.

Free text was checked: pseudonymous user IDs only, no names, emails or rep identifiers.

## Why so few

Not a bug. Cloud Run request logs for `/api/feedback` since 2026-11-23 23:00 UTC show only three POSTs, all 200, all in the bucket. During the demo the questionnaire was opened twice (00:26, 00:30 UTC) and closed without submitting, and vote buttons loaded on a few briefs and forecasts with no votes cast. The live build (09cb1ed) already keeps questionnaires per login and browser (70b8ba5), so classmates on the shared login did not overwrite each other. Traffic was light overall.

Note: the local `main` ref was behind `origin/main`; fetch before comparing branches.
