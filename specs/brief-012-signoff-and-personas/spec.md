# brief-012: Two-step sign-off and the four Briefing personas

**Spec ID**: brief-012-signoff-and-personas (Briefing lane)
**Created**: 2026-11-27 (v2; written after the code, invariants and acceptance tests only, per the v2 spec format)
**Branch**: feature/v2-assumptions-first
**Source**: Michael's v2 decisions of 2026-11-27 (Q5, Q13, Q17, Q18, #6); `User stories.docx` and `copy of personas - 10/21.docx` (SoT) for P2 and P4. brief-005 (review and sign-off) and core-007 (roles) are unchanged; this spec states what v2 adds.

## Why

v1 had one reviewer (the analyst) between a brief and its leaders. The persona documents give the Insights Manager (P2) the sign-off and add the Marketer (P4) as a reader. v2 puts all four Briefing personas on the app without touching the Forecast lane's roles.

## Invariants

- **I1. The state machine.** P1 sends a draft for sign-off (`sent`) or rejects it (`rejected`). P2 signs a sent brief off (`signed_off`) or returns it (`returned`); a return needs a comment and may flag single claims. A signed-off brief is frozen. Every transition is a UAT event and an entry in the brief's audit trail. Briefs stored before v2 are read through a legacy map (pending, approved, rejected read as draft, signed_off, rejected); stored records are never rewritten.
- **I2. Who reads what.** P1 reads every state. P2 reads `sent`, `returned` and `signed_off`, in the analyst view, read-only. P3 and P4 read `signed_off` only, in the leadership view. Anything else is 404, so a brief's existence is not disclosed. The roles and their states live in `src/pharmagentics/api/roles.json`.
- **I3. Follow-ups.** Any role that reads the analyst view (P1, P2) can ask follow-ups on a brief it may open, in its own thread, and vote on the answers. Leaders (P3, P4) get 404 on every thread route.
- **I4. The Evaluation page.** Closed to P3 and P4 (403 from the server, not only a hidden nav item). Open to P1, P2, the test login and the Forecast lane's roles exactly as before v2: CA and BM keep their pre-v2 action lists, and their access lives in `rbac.can_evaluate`.
- **I5. Logins.** Seven UAT logins: four Briefing personas, two Forecast personas and the test login. Every Briefing login and the test login hold both Briefing brands (BXA, BXC); the Forecast logins hold BXA only. The test login switches between the analyst (P1, CA), Insights Manager (P2), leadership (P3, BM) and Marketer (P4) views and then has exactly that role's rights; its credentials are unchanged from v1.
- **I6. The Forecast lane is unchanged.** No Forecast role, action, login, screen or API answer changes in v2.

## Acceptance tests

- `tests/test_signoff.py`: every (state, role, action) pair against the real API, for the real logins and for the test login in each view (I1, I2, I5).
- `tests/test_threads.py::test_the_insights_manager_asks_follow_ups_on_a_brief_sent_for_sign_off`, `::test_the_marketer_never_reaches_a_thread`, `::test_the_test_login_asks_follow_ups_as_the_insights_manager_but_not_as_the_marketer`, `::test_leaders_never_reach_a_thread` (I3).
- `tests/test_telemetry.py::test_the_evaluation_page_is_closed_to_the_briefing_leaders_only` (I4).
- `tests/test_forecast_api.py` passes unchanged (I4, I6). `tests/test_deploy.py` checks the realm's logins and grants (I5).
