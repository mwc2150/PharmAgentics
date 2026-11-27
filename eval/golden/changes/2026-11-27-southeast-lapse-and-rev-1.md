# P4-Q3, WIN-2: promotion is the Southeast lapse's cause; REV-1 added

- Date: 2026-11-27
- Cases: P4-Q3 (C-021), WIN-2 (C-032); new REV-1 (C-057)
- Source: Michael's decision 2026-11-27 ("each case needs the right assumptions"), closing the brief-010 integration open item; the mentor's review of 2026-11-20, item 2.1, recorded as H-1 in `docs/reviews/2026-11-27-uat-review-v1.md`

**P4-Q3 and WIN-2.** Both cases are about the Southeast rep-coverage lapse (calls 15 to 26 a week from 2026-08-03 to 2026-08-31, against about 50 to 60 before). Under each case's own assumptions the lapse is inside the weeks compared: WIN-2 compares the week of 2026-08-24 with the chosen July weeks, and P4-Q3 is a release-wide Promotion review, whose comparison is each lapse against the weeks before it. P1-Q6, P3-Q5 and P4-Q5 already list promotion for the same lapse, so P4-Q3 and WIN-2 now do too. P4-Q3 also states its intent (`promotion_review`), which the engine already read from its words; its period stays the whole release, as a review's does. No fact changed.

**REV-1 (new, draft).** The week the mentor reviewed: Southeast, week of 2026-10-05, against the stated four weeks before (2026-09-07 to 2026-09-28). The change (up 19.6%) is inside those weeks' range, so it is within Southeast's normal range; calls (61 against 52) are under the promotion bar on the stated weeks. The finding supports no driver; the lapse and recovery are context the answer must name (`must_say`). Facts are from SQL, all `reviewed: false`.

`uv run python -m eval check` recomputes every fact.
