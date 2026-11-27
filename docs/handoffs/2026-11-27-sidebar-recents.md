---
branch: feature/sidebar-recents
lane: shared
next: Michael reviews and merges the PR (auto-deploys); a note to Alvin and Sienna that Forecast roles get Recents too
---

# Sidebar Recents (2026-11-27)

Michael asked for a Recents and View all block in the sidebar, as in Claude's web app, to reach Your briefings and Your reports quickly. Decisions (all four recommendations accepted, then adjusted on the preview):

- **Who:** every role, each seeing what it already works on:
  - the analyst: their own briefs;
  - the Insights Manager: the sign-off queue;
  - the Director and the Marketer: signed-off briefs;
  - the Forecast analyst: their questions and reports;
  - the Brand Manager: their reviews.
- **What counts as recent:** the newest change, from the server (the same on every device); six items.
- **Each item:**
  - a single line, the question when one was asked, else brand, territory and week;
  - a dot when it waits on this person;
  - the status as hover text.
- **Placement:**
  - at the foot of the sidebar, above Share feedback and Settings;
  - a fold this browser remembers;
  - hidden in the collapsed rail; shown in the phone drawer.
- **All briefings and All reports:** under the fold, always shown, as muted sidebar rows (not link colour).

## What changed

- `App.tsx`:
  - `loadRecents` and `Recents`; Shell loads and opens them.
  - The three Briefing apps say which brief is open and how to open one.
  - `ForecastWorkspace` opens a run or report on request (`openItem`) and reports what is showing.
- `motion.ts`: a view transition replaced by a newer one is skipped and its promises reject. They are now handled; a Recents item starts two transitions, and the second one raised a page error.
- Spec `brief-015` I12.

## Checks

On the 8765 preview, a scratch Recents check passed 30 of 30:
- each role;
- opening an item, marked current while open;
- the fold and its memory after a reload;
- All briefings outside the fold;
- the collapsed rail;
- the phone drawer;
- no page errors.

Also on the preview:
- `check_workspace_split.py`: 11 of 11.
- `check_settings.py`: 51 of 51, 0 contrast failures.
- site-wide motion: 24 of 24.

## Same day, deployed

- Keycloak sign-in and sign-out pages (#39, #40) are live on revision 10: v2 on the wordmark baseline, and "Sign out of PharmAgentics?" with Sign out and Stay signed in.
- `make_env.py` added the Insights Manager and Marketer passwords from `deploy/demo-credentials.env`; `env-push` and `gcp.py keycloak` then ran.
- Checked by signing in as `uat-tester` and signing out on the live site.

## Notes for Alvin and Sienna (Forecast lane)

Forecast roles get Recents too (their questions and reports, or what waits for review), opening in the Forecast workspace. No Forecast access, login or engine behaviour changed.

## Open

- The app's own "You are signed out" page shows only the tile, without the wordmark and "v2" that the Keycloak pages now have.
