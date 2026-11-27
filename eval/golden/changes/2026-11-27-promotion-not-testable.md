# Promotion "not testable" where no channel moved; the within-range rule (REV-1) for every question

- Date: 2026-11-27
- Cases: P2-Q2 (C-008), P2-Q3 (C-009), P4-Q4 (C-022); BXC-P4-Q4 (draft)
- Source: Michael's v2 decisions of 2026-11-27: Q6, "flat promotion produces 'not testable this period'" (in place of
  "ruled out"), and "anything relating to assumptions should apply to all questions, not just problematic ones"

**Not testable.** The promotion check now calls promotion `not_testable` when no channel (rep calls, digital
impressions, samples, speaker programs) moved at any tested lag against the brief's comparison weeks, and keeps
`ruled_out` for a channel that moved with TRx not following (packet promo-verdict). In these four findings promotion
held level, so it can be neither credited nor ruled out: it leaves `drivers_ruled_out`, and the reference answers and
`then` clauses say "not testable". No fact changed; the three Cardiovela findings stay `reviewed: true`, as the edit
applies Michael's decision and changes nothing else.

**The within-range rule, checked on every case.** A territory whose change is inside its normal range on the brief's
stated comparison weeks gets no territory-level driver (promotion, competitor, supply, data) credited, on its story
or its plan cards; access, which is always a plan's own evidence, keeps its verdict. A sweep of all 57 Briefing cases
(33 Cardiovela, 24 Lipidara) found REV-1 the only finding the rule changes, and it already expects no driver. BXC-P3-Q5 keeps
`competitor`: its cause is a competitor's coverage change on one plan, plan-level evidence like access.
`tests/test_follows_assumptions.py` now asserts the rule on every case.

`uv run python -m eval check` recomputes every fact.
