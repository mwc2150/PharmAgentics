# BXC Briefing and per-user access

BXC (Lipidara) supports scripted Weekly Briefing. BXA (Cardiovela) retains scripted/agent Briefing and the existing Forecast workflow. Forecast and the agent worker do not support BXC yet.

## Local walkthrough

Build DuckDB, start the app with the existing local launch command, and sign in through development sign-in (`PHARMAGENTICS_AUTH=dev`) or your local Keycloak stack.

| Dev identity | Keycloak template identity | Persona | Brands |
| :- | :- | :- | :- |
| dev-analyst | uat-briefing-analyst | Commercial Analyst (P1) | BXA, BXC |
| dev-insights | uat-briefing-insights | Insights Manager (P2) | BXA, BXC |
| dev-director | uat-briefing-director | Brand Director (P3) | BXA, BXC |
| dev-marketer | uat-briefing-marketer | Marketer (P4) | BXA, BXC |
| dev-forecast-analyst | uat-forecast-analyst | Commercial Analytics Analyst (CA) | BXA |
| dev-forecast-manager | uat-forecast-manager | Brand Manager (BM) | BXA |
| dev-tester | uat-tester | Tester, switches personas | BXA, BXC |
| dev-analyst-no-brands | Not seeded | Briefing analyst | None |

Since 2026-11-27 every Briefing login holds both brands, so the two `-multibrand` logins are gone (the realm has seven UAT logins). Same persona with different grants (core-010 US2) is proved at the API level with fabricated principals in `tests/test_brand_access.py` (`dev-bxa-analyst`, `dev-bxa-insights`, `dev-bxa-director`, `dev-bxa-marketer`), not with a login. Passwords are in `deploy/demo-credentials.env`.

1. As the analyst, select Lipidara (BXC), Pacific, June 8, 2026. Scripted is the supported engine. Review the triage, generate, and open the evidence. Pacific BXC TRx/NRx/NBRx are **626/140/83**; BXA for the same cut is **464/96/49**. The figures come from `reporting.v_weekly_rx_kpis`.
2. Before sign-off, the Director and the Marketer cannot open the draft. Send it for sign-off as the analyst, then sign it off as the Insights Manager. The Director and the Marketer can now open the BXC executive summary, with no analyst evidence, query text or trace controls.
3. For a BXA-only analyst (a fabricated principal in the tests; in the hosted realm, a login whose `brand-bxc` grant an admin removes), BXC never appears in the selector. Direct BXC Overview, triage and generation requests return 403. Saved BXC brief IDs, reviews, sign-offs, threads, shared links and votes return 404. A BXA-only Director cannot list or open the signed-off BXC brief.
4. Switch BXA → BXC → BXA. The reporting week stays selected, while old plans, reports and evidence drawers close. BXA agent choices remain available; BXC uses Scripted. Delayed previous-brand responses cannot replace the current workspace.
5. Run BXC New England, May 4, and Great Lakes, July 6, 2026. The shared missing/duplicate feed flags remain visible. No driver is assigned to those withheld cuts. Any projection or estimate is explicitly an assumption.
6. A role without brand grants sees **No brand access**. A tester's persona switch retains that account's grants. Changing Keycloak grants requires sign-out/sign-in; this version does not revoke an already active session immediately.

## Competitor policy

A grant protects a dedicated brand workspace and its detailed records. Within an authorized workspace, aggregate market-basket competitor volumes/shares and their aggregate evidence remain available, so a BXA Overview may name BXC as a competitor. This policy also applies to already saved BXA briefs.

## Hosted rollout with Michael

The PR changes the realm **template**. A GitHub merge/app deployment does not update the running Keycloak realm or overwrite existing users. Before deploying the enforcing app, create realm roles `brand-bxa` and `brand-bxc` and assign explicit BXA grants to the existing UAT accounts that retain BXA access. The template now gives BXA and BXC to the four Briefing logins and the tester, and BXA only to the two Forecast logins. Keep persona roles separate from grants.

After both the app and realm are updated, sign out/in and repeat the walkthrough above. Record the app revision, account/grant combination, one allowed BXC brief ID and one denied BXC request/status. No hosted rollout is performed by this code change.

## Checks

```bash
uv sync --locked --no-default-groups --group dev --group api --group agent
uv run --no-sync python src/pharmagentics/data/load_duckdb.py
uv run --no-sync python src/pharmagentics/data/check_duckdb.py
uv run --no-sync pytest tests/test_brand_access.py tests/test_rbac.py tests/test_signoff.py tests/test_briefing_api.py tests/test_briefing_smoke.py tests/test_overview.py tests/test_triage.py tests/test_threads.py tests/test_jobs.py tests/test_feedback_votes.py -q
```

The requested scripted evaluation additionally needs the locked `eval` dependency group. Run `python -m eval run --system briefing_scripted --lane briefing` before and after the change, then `python -m eval gate <candidate> <baseline>`.
