---
branch: feature/settings-light-mode
lane: shared
next: Michael reviews the light theme and Settings in a preview build (dark is the default), then merge; Forecast teammates glance at their screens in light
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

## Checks
`tests/ui/check_settings.py` (Playwright, local app, port of your choice): 51 assertions, plus light and dark screenshots at 1280x800 and 390x844 into `local/settings-check/` and an in-page text-contrast scan (axe is not in the repo). The pytest suite was not run (an evaluation was using the machine); only `tests/test_frontend_scope.py`.

## Open
- Light tokens: text accent is `#007a72` (not `#00857c`, which is 4.15:1 on the grey page); `#00857c` is the fill, ring and logo face.
- `AGENTS.md` and `DESIGN.md` still describe the dark look only.
