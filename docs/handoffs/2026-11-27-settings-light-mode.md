---
branch: feature/settings-light-mode
lane: shared
next: Michael reviews the pull request (dark is the default) and merges; then `deploy/gcp.py keycloak` for the login theme; Forecast teammates glance at their screens
---

# Settings workspace and light theme

Decisions of 2026-11-27: a gear at the bottom of the sidebar opens Settings (Appearance, New briefing defaults for the analyst, Reading, About). Choices are saved per browser in localStorage under `pa-settings`, never on the server. Dark is the product default; `VITE_PHARMAGENTICS_DEFAULT_THEME` (light | dark | system, unset = dark) changes the build default, and a saved choice always wins.

## What changed
- `src/userSettings.ts` (store, date helpers, theme/density/motion/footnote attributes on `<html>`) and `src/Settings.tsx` (the workspace). Both are in the `tests/test_frontend_scope.py` allow-list.
- `public/theme-init.js`, a classic script in `<head>`, sets `data-theme` before first paint. It is a file, not an inline script, because the CSP allows `script-src 'self'` only. The build default travels in `<meta name="pa-default-theme">`, filled by `vite.config.standalone.ts`, which also injects the git short sha as `__PA_APP_VERSION__` (fallback "dev"; `PHARMAGENTICS_APP_VERSION` overrides).
- `index.css`: `:root[data-theme="light"]` redefines every token (dark stays on `:root`); `--pa-glass`, `--pa-highlight` and `--pa-mark-*` carry the values that were hard-coded; density, reduce-motion and footnote rules; the print block now also matches `:root[data-theme]`.
- Logo: inline SVG in `BrandMark` following the theme; `public/pa-mark.svg` (dark colourway) and `public/favicon.svg` (prefers-color-scheme) redrawn as the 3D tile (edge 6 px below, 3 px right).
- Dates: `labelWeek`, `longDates`, `when`, Overview `day`, Memo axis labels, `processLine`, `labelTime` follow the date style. The superscripts carry `.pa-fn`. Scroll helpers use `motionReduced()`.
- API: `ReleaseContext` gains an optional `data_version` (additive), shown under Settings > About.
- No Forecast file needed a colour change; shared files with a date or class change: `App.tsx`, `Memo.tsx`, `Timeline.tsx`, `MessageBar.tsx`, `HowItWorks.tsx`.

## Later the same day (Michael's review on the 8765 preview)
- **Dark palette in neutral greys:** page `#0e0e10`, panels `#161619`, sidebar `--color-rail` true black (white in light), quiet hairlines, slab edge `#28282d`; no blue tint. Theme colour `#0e0e10` in `index.html`, `theme-init.js` and `userSettings.ts`.
- **Section headings are tiles like the logo** (`.pa-mark`, `--pa-mark-face/edge/ink`; inverted in light).
- **Frost and motion** (`src/motion.ts`, in the scope allow-list): a frosted foot under a brief's bars (`.pa-frostbar`) and a blurred scrim behind drawers and dialogs (`.pa-scrim`); folds ease open (`::details-content`); tab changes and opening a brief are view transitions (the title moves into the heading); a brief's sections arrive in sequence; charts draw on first view; clickable tiles lift; a status change pops; the theme crossfades. Everything script-driven checks `motionReduced()`; the CSS has matching reduced-motion lists.
- **Headline numbers spin in like a combination lock** (`RollIn` in `agent/primitives.tsx`; `.pa-roll`, `.pa-reel`, `.pa-reel-strip`): each digit is a wheel that lands on the real figure; at rest it shows the figure, so print, reduced motion and no-animation all read correctly; screen readers and copying get the number whole; cited figures keep their dotted underline.
- **Overview:** the brand selector sits beside the week (no tab-row toggle; brief-015 I2 updated); the line under the tabs says only what the selectors do not (territories, how far the data runs). The greeting has no full stop. The question bar reaches 16 px past the form on each side.
- **Account avatar:** the first initial in a circle before the name, coloured by seniority (`--pa-rank-1..6`: Brand Director red, Brand Manager orange, Insights Manager yellow, Marketer green, Commercial Analyst blue, the test login violet; grey with no role). The dev sign-in page lists each persona with it (`auth.py` `_rank_color`).
- **Server pages and the Keycloak login theme** on the neutral palette with the tile logo (`deploy/keycloak/themes/pharmagentics/login/`); the hosted login picks it up on the next `deploy/gcp.py keycloak`.
- **Site-wide motion (later still):** every sidebar move between workspaces, Forecast tab, opened question (its question moves from the list into the page, `RUN_TITLE`), back to the list, and opened Forecast report is a page transition. Tile headings on the Forecast report's top-level sections and the Evaluation page's sections; the headline stays plain. Padlock numbers on the Forecast / Actual / Miss tiles, driver figures, Evaluation's headline figures, golden-set scores and driver-recovery table, How it works' comparison, and the brief's territory table; a table's wheels wait until it scrolls into view (`InView`, `useDrawOnView(threshold)`). Forecast bars grow out of the zero line and the actual line draws in. A Forecast report's sections arrive in sequence. Print and reduced motion show every figure at rest. Checked on 8765 by a 24-assertion script (scratch).
- Forecast screens get the shared visuals only (palette, avatar, greeting, frost, motion); no Forecast file or behaviour changed. Worth a note to Alvin and Sienna.

## Checks
- After the later work: `tests/test_briefing_api.py` and the auth tests (479 passed), `tests/test_frontend_scope.py` (5 passed), `check_settings.py` 51 of 51 with 0 contrast failures, `check_workspace_split.py` 9 of 9, a motion check of 14 assertions (scratch script), all on the 8765 preview in dark.

Earlier:
`tests/ui/check_settings.py` (Playwright, local app, port of your choice): 51 assertions, plus light and dark screenshots at 1280x800 and 390x844 into `local/settings-check/` and an in-page text-contrast scan (axe is not in the repo). The pytest suite was not run (an evaluation was using the machine); only `tests/test_frontend_scope.py`.

## Open
- Light tokens: text accent is `#007a72` (not `#00857c`, which is 4.15:1 on the grey page); `#00857c` is the fill, ring and logo face.
- `AGENTS.md` and `DESIGN.md` still describe the dark look only.
