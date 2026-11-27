---
name: uat-review
description: Review the PharmAgentics web app the way the project mentor did on 2026-11-20 - walk every role, then judge the screens, briefs and Forecast answers for content errors, copy, accessibility and security, and write a dated UAT report. Use before a release or demo, after a change that touches the UI, a brief, a driver check or the API, or when asked to "UAT", "review the app" or "review the hosted version".
---

# UAT review

The mentor's review found problems the test suite missed because it read the app as a user and cross-checked what each screen says against the other screens and against the brief's own Assumptions. This skill repeats that method on any version. A script captures the evidence; you judge it.

The report is the product. Do not stop at the script's flags: they are leads, and the best findings (a story the Overview calls normal, a comparison window that differs from the stated one) come from reading the briefs against themselves.

## Rules

- Review the local app, started from the current checkout. Never sign in to, click in, or change the hosted app. One read-only `curl -sI <hosted URL>/` for its response headers is allowed; add them to section 5 and say they come from the hosted app.
- Never read the path in `PHARMAGENTICS_EVAL_STORE`, never open `eval/` golden cases to compare answers, never run `eval run` or the full pytest suite. A review judges what a user can see.
- Clicking Approve, Reject and Submit is fine locally (state goes to a git-ignored folder). Do not run an Agent-team brief unless an Anthropic key is configured; if not, say so under Coverage.
- No emojis. Plain words. Name a screen by what it says, not by a code.

## 1. Start the app (about a minute)

```bash
uv sync                                                   # once; the worktree needs its own .venv
uv run python -c "import pharmagentics;print(pharmagentics.__file__)"   # must point into THIS checkout; else set PYTHONPATH=<checkout>/src
uv run python src/pharmagentics/data/load_duckdb.py       # builds local/pharmagentics.duckdb if missing
uv run playwright install chromium                        # once
cd frontend/figma-make && pnpm install --frozen-lockfile  # once (no pnpm: npx --yes pnpm@10 ...)
VITE_PHARMAGENTICS_API_BASE_URL=. pnpm exec vite build --config vite.config.standalone.ts && cd ../..
```

Then start the server with dev sign-in, the checkout's own `src`, a fresh state folder and the built frontend (run it in the background; stop it when done):

```bash
# state folder: start from the PREVIOUS review's saved state when there is one, so briefs written by the older
# version are in the approved list and get compared with today's format; otherwise start empty.
rm -rf local/state-review; [ -d local/state-<previous-label> ] && cp -r local/state-<previous-label> local/state-review
PHARMAGENTICS_AUTH=dev PHARMAGENTICS_STATIC_DIR="$PWD/frontend/figma-make/dist" PHARMAGENTICS_STATE_DIR="$PWD/local/state-review" \
  uv run uvicorn --app-dir src pharmagentics.api.app:app --port 8765
```

After the capture, keep the state: `cp -r local/state-review local/state-<label>` (git-ignored). No Docker is needed. If a `node_modules` junction to another checkout is used, say so in the report. On Windows set `PYTHONUTF8=1`.

## 2. Capture (mechanical)

```bash
uv run python -u tests/ui/review_walkthrough.py --label <label>      # --no-mobile skips the 390 px pass; takes about 4 minutes
```

It writes `local/reviews/<date>-<label>/`: `screens/NN-<d|m>-<role>-<screen>.png` in walkthrough order (d = 1280x800, m = 390 px), `aria/*.txt`, `console.json`, `network.json` (4xx, 5xx, failed), `headers.json`, `briefs/*.json`, and `observations.json`. Open `observations.json` first: `flags` (mechanical leads), `run_errors` (steps that did not work: each is itself a finding or a script drift), `api` (role matrix, leader payload leaks, brief cross-checks, cross-lane, follow-up chat answers), `notes`.

The walk covers every role and the tester's view switch and second brand: Overview, KPI query panel, territory drawer, New briefing form, triage plan, full brief (analyst and leadership), evidence drawer, follow-up chat, Reject dialog, Approve, approved list, Evaluation, Share feedback and questionnaire, Forecast question, scope check, investigation, follow-up, report, leadership preview, Submit, Brand Manager review and approval.

## 3. Judge (this is the review)

Look at the screenshots (Read the PNGs, at least every full-brief and every first screen of a role), the aria files and the briefs JSON. Do each of these and write down what you find, including "checked, no issue" in Coverage.

Content cross-checks, in this order, because they found the worst problems:

1. **Each brief against its own Assumptions.** Read the stated comparison window (for example "the four weeks before (2026-09-07 to 2026-09-28)"). Then open `briefs/<case>.json` and list every evidence record's dates (`api.brief_checks[].evidence_dates`). Every comparison figure (the "against N in the reference weeks", baselines, controls, driver verdicts) must be dated, and inside the stated window. A verdict computed on a longer or shifted window than the one stated is a `data misread` or `unsupported claim`, even if the number is arithmetically right. Also check the period is the one the user picked.
2. **Chart captions against section 1 and the prose.** If a chart says the week sits inside its baseline band, or the Overview marks the territory "Within normal range", the bottom line and the story must not present the change as a finding without saying so. Same for "Least sure" lines that name a change the triage dropped. Tag `false alarm` or `over-attribution`.
3. **Driver verdicts against the numbers shown.** "Supported" needs the numbers beside it to support it. Does a promotion or coverage verdict compare against a baseline that itself contains the event (a lapse or a launch inside the reference weeks)?
4. **Briefing against Forecast on the same territory and weeks** (`api.cross_lane`, plus the Forecast screens). They must not tell different stories: a coverage lapse the Forecast names must not be absent from, or contradicted by, the Briefing. Run one more pair by hand if a flag suggests it.
5. **Leader views.** `api.leader_payload_leaks` must be empty; the Director's and Brand Manager's screens and the Leadership preview must show no SQL, evidence ids, query text, trace controls, record counts or "Source records". Check what the Director can call (`api.director_forbidden_routes`, `api.role_matrix`).
6. **Same fact, different words.** KPI tiles against the Overview table; "material change" count against the territory statuses; counts of stories against "Built by ... N stories"; period and brand labels in headers against the data; draft or approved status against the footer under it.
7. **Follow-up chat.** Do different questions get different, relevant answers (`api.followup_chat`)? Does a canned answer count against the quota? Do the Forecast follow-up chips depend on the run (a no-driver or abstained run offering "Why was this driver accepted?")?
8. **Old briefs and typed input.** With a seeded state folder, open the oldest approved brief as the Director and the newest side by side (`api.director_brief_formats`, flag `briefs-in-different-formats`): same sections, same wording, same status labels? Retype one request in each date format the app shows ("Aug 24, 2026") and the one it accepts ("2026-08-24"); a reader that silently falls back to the latest week is a finding. Open a brief after a reload and from the Approved list, not only straight after generating it.
9. **Empty, zero and tiny-sample states.** A tile that always reads 0, a rate such as "100% (3 of 3)" with no sample guard, "PASS" over an answer with no drivers, an empty state that names the wrong role.

Copy (leadership-facing first): raw codes or plan ids in prose, ISO dates in prose next to long-form dates, duplicated sentences, jargon (hash, "lag", "gate", "claim"), "projected" on a number that nothing projected, vendor or model names for roles that should not see them, wording that implies certainty the data does not give, tense or role mistakes ("once the Brand Manager approves one" shown to the Brand Manager), a draft under a footer that says the content is approved. House rules: "competitive intelligence" never "surveillance"; "new patients" only for NBRx; no line identifies an individual rep; no unmarked unknowns.

UI, UX, accessibility: selected tab marked `disabled`, ambiguous role labels and no username shown, 100-plus-option selects, two classification labels on one screen, footnote superscripts that merge into the value in copy-paste and for a screen reader (`footnote-merges-into-value`), headings that read as one word ("§1Bottom line"), empty headings, unnamed controls, focus order and focus return after closing a drawer (press Tab and Escape yourself in a short extra Playwright check if the aria files look wrong), time without a time zone, mobile: horizontal overflow, an account button that collapses to an icon, tap targets under 24 px, text clipped at 390 px.

Security and setup: response headers (`headers.json`: CSP, HSTS, frame-ancestors or X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy), console 401/403/404 on a normal visit (`console.json`, `network.json`), design-tool comments in the served HTML, what the Evaluation page shows to roles that should not see it (`api.role_matrix` `/api/telemetry`), dev-only strings that would ship ("Development sign-in"), no list of stubbed features, ground truth anywhere visible. Check each Evaluation number against the page's own sample size.

Do not stop at the first instance of a pattern: say where else it occurs.

## 4. Write the report

Write `docs/reviews/<YYYY-MM-DD>-uat-review-<label>.md` with this structure (headings exactly):

```
# PharmAgentics UAT: review of UI, setup and output quality
App / Reviewed (date, viewport, plus a 390 px spot check) / Accounts tested / Evidence (screenshots, numbered in walkthrough order)
## 1. Summary
   what works well (bullets with screenshot refs); the main risks (numbered)
## 2. High-priority findings
   one subsection each: what the screen says in each place (a small Where | What it says table),
   why it matters, recommendations
## 3. Content and copy issues (leadership-facing)      table: # | Issue | Evidence
## 4. UI, UX and accessibility                          table: # | Finding | Severity (Low / Low-Med / Med / High)
## 5. Setup, configuration and security                 table: # | Finding | Recommendation
## 6. Evaluation page observations
## 7. Coverage and limits of this review                what was tested; what was not done on purpose and why
## 8. Suggested next steps (priority order)
## Tests to add
```

Rules for findings:

- Every finding has an ID (`H-1` for section 2, `C-1`, `U-1`, `S-1`, `E-1`), a severity (High, Med, Low-Med, Low), and a failure tag from: data misread, wrong metric, wrong grain, missed event, false alarm, over-attribution, missed interaction, stale context, unsupported claim, numeric mismatch, governance breach, run error; or `ui`, `copy`, `security` for non-content findings. Put the ID, severity and tag at the start of the row or heading.
- Evidence is a screenshot path relative to the repo, under `local/reviews/...` (screenshots stay git-ignored), or a brief case and evidence id (`southeast-latest e36`), or a header name. Quote the exact words the screen says.
- Separate what you saw from what you infer. If something may be intentional or you could not confirm it, write `[NEEDS CLARIFICATION: ... ]` instead of guessing.
- Section 2 is for findings that could make a leader act on a wrong or contradicted statement, or breach a governance rule. Lead with the worst.
- Section 7 lists every flow covered, what was skipped on purpose (Agent-team brief without a key; hosted app; load; a screen reader) and every `run_errors` entry.
- Last, `## Tests to add`: for each finding ID one line, the test that would prove the fix: pytest for API and headers, a Playwright check for UI, a golden case or scorer for content. Do not write the tests.

Commit the report only (screenshots are git-ignored). Stop the server when done.

## When the script drifts

If a step fails (`run_errors`), the UI changed. Fix the step in `tests/ui/review_walkthrough.py` (locate by accessible role and name), rerun, and record the failure as a finding only if the UI itself is broken. Add a mechanical check to the script when you find a new class of problem that a regex or an API call could have caught; keep judgment calls in this file.
