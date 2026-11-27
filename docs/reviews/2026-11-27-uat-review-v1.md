# PharmAgentics UAT: review of UI, setup and output quality

**App:** PharmAgentics v1, the `origin/main` checkout at commit `09cb1ed` (data version `47bcfd650564`), run locally with dev sign-in and the built frontend. One read-only `curl -sI` of the hosted app's `/` was added for headers (section 5); the hosted app was not signed in to or changed.

**Reviewed:** 2026-11-27. Desktop 1280x800 (Chromium, time zone America/New_York), plus a 390x844 pass of every role's landing screen and the key screens of four roles. Method: `.claude/skills/uat-review/SKILL.md`; capture by `tests/ui/review_walkthrough.py` (0 run errors, 58 screenshots, 58 mechanical flags, 2 console errors, 2 failed requests).

**Accounts tested:** the five stand-ins for the hosted logins: `dev-analyst` (Briefing Commercial Analyst), `dev-director` (Brand Director), `dev-forecast-analyst` (Forecast Commercial Analytics Analyst), `dev-forecast-manager` (Brand Manager), `dev-tester` (view switch Analyst/Leadership, second brand Lipidara BXC). The hosted logins (`uat-*`) were not used, so anything specific to Keycloak is outside this review.

**Evidence:** screenshots under `local/reviews/2026-11-27-v1/screens/` (git-ignored), numbered in walkthrough order and cited as S01 to S58 (index at the end of this file; `d` = 1280 px, `m` = 390 px). Accessibility snapshots are in `.../aria/` under the same names; the briefs, evidence records and the Forecast run that findings quote are in `.../briefs/` (`southeast-latest`, `southeast-aug24`, `pacific-latest`, `forecast-southeast-aug24`); `observations.json` holds every mechanical flag, the role matrix and the follow-up chat answers. A case is cited as `southeast-latest e36` (brief case, evidence id).

## 1. Summary

**What works well**

- Every number in the briefs is a clickable claim with a stored query and a pinned data version (S08, S09); the Director and Brand Manager screens carry none of it. Leader payloads were checked at the API: no evidence, claims, trace or SQL in what the Director or Brand Manager can fetch, and the four analyst routes probed (query, triage, scope, overview) returned 403 to the Director (`observations.json` `api.leader_payload_leaks`, `api.director_forbidden_routes`).
- Role separation holds in the UI and the API: Director sees only approved summaries (S20, S21), Brand Manager only submitted reports (S37), the tester's Leadership switch drops to the leader view (S47), a second brand (BXC) works end to end (S44 to S46).
- The Overview is a good first screen: each territory shows its change against its own normal range, and says so in words (S01). The triage plan lets the analyst keep, drop or reorder stories before anything runs (S07).
- Each brief ends with a brief definition and an Assumptions block (S08, S10), which made the cross-checks in this review possible.
- The Forecast investigation shows its method, the driver confidence reasons and what remains unknown (S28); an out-of-scope or provisional question abstains instead of attributing (S34).
- Skip link, named landmarks, named buttons on every claim ("4,891, evidence 26"), tables with captions and column headers, `lang="en"` and a page title are all present.

**Main risks**

1. A brief presents a Southeast change as a finding, "Least sure" in the bottom line and a story with an action, while the Overview, the triage rule and its own chart all say the change is inside the normal range (H-1).
2. The driver verdict that carries the Southeast story, "promotion supported ... 51% higher", is computed on a 13-week window the brief never states; on the four weeks it does state, the same comparison is about +17% (H-2).
3. Briefing and Forecast describe the same Southeast fall in rep calls differently, with different baselines (50 against 44) and only the Forecast naming it a coverage lapse (H-3).
4. The follow-up chat returns one canned paragraph for every question and counts each against a 20-question limit (H-4).
5. No security headers on the app, local or hosted (S-1); the Evaluation data and model names are open to every role (S-2, C-12).
6. A draft is shown under a footer that says it comes from the approved brief (C-3); dates are shown in two formats on the same screen almost everywhere (C-2), and the question reader understands only one of them (C-6).

## 2. High-priority findings

### H-1 (High, over-attribution; also false alarm): the Southeast change is a finding in the brief and normal variation everywhere else

The same week (Oct 5, 2026), the same territory, five places:

| Where | What it says |
| :- | :- |
| Overview row (S01); drawer (S03) | "Southeast: +19.6% against a normal range of ±32.3%; Within normal range". Drawer: "Up 19.6% on the 4 weeks before; its normal range is ±32.3%". Tile: "Territories with a material change 0 of 8 like-for-like territories" |
| Triage plan (S07) | Southeast is Story 1 because "The question names this territory, so code always proposes it". The card gives the +20% and never says it is within the normal range. The other seven territories are listed under "Dropped by code" as "Within its normal range (code screen)" |
| Bottom line §1 (S08, S10, S21) | "Least sure: the Southeast change (up 20%); its confidence, Medium, is the lowest of this brief's stories." The change is the one thing the national summary singles out |
| §3.1 story (S08) | Headline "Southeast rose 20% on the comparison weeks, while the other territories were up 4.8%." Two lines under it the chart caption says "In the week of 2026-10-05, Southeast had 793 BXA TRx, inside its baseline band." |
| §5 Next checks (S08, S21) | "Southeast: confirm the promotion finding. Owner: sales leadership and marketing. Unlocks: whether to change call plans or campaign timing in the territory." |

Why it matters: a Brand Director reads §1 and §5 and nothing else. They are told a territory is moving and to consider call plans, on a change the product's own rule calls ordinary, and the chart under it says so. The "baseline band" is also the minimum to maximum of the same four weeks the change is measured against (529 to 799; Sep 28 was 799), so "inside its baseline band" is nearly true by construction, while the Overview's normal range (±32.3%) is a different, wider construct; the two never reconcile on screen. The same pattern appears for Pacific (`pacific-latest`: +3.1% against ±37.4%, a story with "Candidate drivers"), and the Overview drawer offers "Generate brief for Southeast" on a territory it has just called normal.

Recommendations: when the named territory is inside its normal range, say so in the first sentence of §1 and §3 and drop "Least sure" and the §5 action; carry the Overview status into the brief's story and the leadership view; use one definition of "normal" in the chart band and the Overview.

### H-2 (High, data misread; also unsupported claim): the promotion verdict is computed on weeks the brief does not state

| Where | What it says |
| :- | :- |
| Assumptions §6 (S08, S10) | "Comparison weeks: the four weeks before (2026-09-07 to 2026-09-28)." "Driver timing: Southeast: promotion, same week." |
| §3.1 verdict (S08) | "Promotion: supported as an association, same week. Aggregated calls averaged 61 a week against 40 in the reference weeks (51% higher)." "Reference weeks" is not defined anywhere on screen |
| Evidence (`southeast-latest` e36, e37) | The "40" is the average over 13 weeks, 2026-07-06 to 2026-09-28; the 51% is computed on that. Competitor check e39, e40 ("15% of the basket here against 14% elsewhere") uses the same 13 weeks. The stated four weeks are 2026-09-07 to 2026-09-28 |
| The brief's own chart (S08, second panel; `southeast-latest` e51) | Rep calls a week: 61, 56, 51, then 19, 15, 15, 26, 22 (Aug 3 to Aug 31), then 60, 48, 53, 48 (the four stated comparison weeks), then 61. The 13-week average of 40 is pulled down by the five low weeks |

Why it matters: on the weeks the brief states, 61 against the average of 60, 48, 53 and 48 (52.25) is about +17%, not +51%; the verdict "supported" and the story it drives rest on a baseline that contains the dip. A reader checking the Assumptions block cannot reproduce the figure. The same mismatch appears in `southeast-aug24` (stated window 2026-07-27 to 2026-08-17; evidence e36 uses 2026-05-25 to 2026-08-17) and `pacific-latest` (e38). Ten evidence records across the four brief cases use a longer window than the one stated (mechanical flag `comparison-window-differs-from-stated`; the 4-week pre-launch baseline of e72 is stated as such and is not counted).

Recommendations: use one window for every comparison in a brief, or state each window beside its figure ("against the 13 weeks 2026-07-06 to 2026-09-28"); have the check that writes "supported" run on the stated comparison weeks; add the comparison window to the evidence label.

### H-3 (High, missed event; also numeric mismatch): Briefing and Forecast describe the same Southeast fall differently

Southeast, week of 2026-08-24:

| Where | What it says |
| :- | :- |
| Forecast investigation (S28; `forecast-southeast-aug24`) | "Southeast rep coverage lapse (aggregated rep calls averaged 26 a week against a usual 50, 48.0% lower): Supported." Impact -213 TRx |
| Briefing for the same territory and week (`southeast-aug24`) | "Promotion: supported as an association, same week. Aggregated calls averaged 26 a week against 44 in the reference weeks (40% lower)." The word lapse does not appear; the story's candidate driver is "promotion" |
| Briefing, Oct 5 (S08, second panel) | The calls chart shows the same collapse (Aug 3 to Aug 31, 15 to 26 a week) and recovery; the brief reads the later level as "promotion ... 51% higher" and never names the lapse |

Why it matters: an analyst who opens both lanes gets two baselines (50 and 44) and two names for one event, and the Briefing's later "promotion supported" is largely the recovery from the lapse (see H-2). The two lanes should agree on what the usual level is and on what the event was.

Recommendations: one shared definition of the "usual" call level used by both lanes; when the Forecast lane has identified an episode for a territory and weeks, the Briefing's driver text should name it; add a cross-lane test on territory and weeks.

### H-4 (High, unsupported claim): the follow-up chat answers every question with the same text, and counts it

In the analyst's brief (S11) three different questions were asked: "What is this brief least sure of?", "Is the Southeast increase real or just noise?", "Which territory dropped the most and why?". Each got the same reply, the §1 Bottom line paragraph, followed by "Scripted, from this brief only" and "Was this answer right?". The header then read "Follow-ups, 3 of 20". The second and third questions were not answered; the user is told they have used three of twenty.

Why it matters: it looks like a conversation and is a lookup of one section. A user asking whether the increase is noise gets an answer that omits the in-range chart and the normal range, and may take it as the brief's considered view.

Recommendations: answer only questions the scripted lookup can match and say "I can't answer that from this brief" otherwise, without charging the quota; or route the question to the section it concerns (the chips "Ask about this" already do).

## 3. Content and copy issues (leadership-facing)

| # | Issue | Evidence |
| :- | :- | :- |
| C-1 (Low-Med, copy) | Raw plan identifier in the triage card: the Granularity line reads "Plan SYN_SOUTHEAST_COMMERCIAL_2, in Southeast." while the card title says "Commercial plan two in Southeast" | S07 (`raw-code-in-prose`) |
| C-2 (Med, copy) | ISO dates in prose next to long dates. Brief prose and tables use "2026-10-05", "(2026-09-07 to 2026-09-28)" and "Metacora (launched 2026-03-02)" while headers read "Oct 5, 2026"; the Director's summary has 28 ISO dates; the triage Time line reads "Week of 2026-10-05; baseline 2026-09-07 to 2026-09-28"; the Forecast chips and placeholder use "2026-08-24". At 390 px the dates wrap mid-date ("2026-09-" / "07") | S07, S08, S21, S26, S27, S53 |
| C-3 (Med, unsupported claim) | A draft sits under a footer that says it is approved: Leadership preview shows "Draft · Awaiting analyst review" and, at the end, "Every figure comes from the approved analyst brief. Evidence and source queries stay with the Commercial Analyst." | S10 (`approved-footer-over-draft`) |
| C-4 (Med, wrong grain) | A brief for one territory opens with the national figure: §1 for Southeast leads with "National BXA TRx 4,891" and the national change; the territory appears in the fourth sentence ("Least sure: the Southeast change") | S08, S21 |
| C-5 (Low-Med, copy) | "projected" on a figure that nothing projected: "National BXA TRx 4,891 projected, week of 2026-10-05" and "Projected national BXA TRx is 4,891", while §2 says "By territory, all observed" and "8 of 8 territories" report | S08 |
| C-6 (Med, data misread) | The question reader on New briefing understands ISO dates only. "Why did Southeast change in the week of Aug 24, 2026?" returns "No week was given, so this uses the latest closed week, 2026-10-05." The same question with "2026-08-24" is read correctly. The app displays the first format everywhere | S06; `POST /api/briefing/scope` with both phrasings |
| C-7 (Med, unsupported claim) | A Forecast answer that abstains still shows "Verification PASS: the parts plus the residual equal the miss ... (pass)", the tag "Draft — submit to Brand Manager · Code only", a "Create report" button with "1 item pinned for the report", and follow-up chips written for an answer with drivers ("Why was this driver accepted?", "Drop South Central from the controls and rerun", "Same question for Pacific") although the answer attributes nothing ("Attribution paused", "no explanation is offered until the feed is reloaded") | S34 (New England, week of 2026-05-04) |
| C-8 (Low, copy) | Brand Manager's empty state: "No approved reports yet. They appear here once the Brand Manager approves one." (the reader is the Brand Manager) | S38 |
| C-9 (Low, copy) | Unrounded number in the KPI query panel: "TRx, week over week 1.7262895174708914" | S02 (`unrounded-number`) |
| C-10 (Low-Med, copy) | "Was this answer right?" under the Director's static executive summary: the thing being voted on (the summary, a number, the analyst's review) is not clear, and no question can have been asked | S22 |
| C-11 (Low, copy) | Implementation language to users: "Scripted Instant. Runs the standard checks in a fixed order." (the Evaluation page reports a 1.3 s median, so "Instant" is loose); "Read by: keyword rules (no model is configured, or the model's reading was unusable)"; "Read by rules. Check the choices below"; "How the agent reads your question" | S04, S06, S16, S27 |
| C-12 (Med, copy) | Model and vendor names are visible to every role: "Claude Haiku, a small and fast model from Anthropic ... Haiku" (How it works, analyst); "Model without data (control) Gemma 3 4B" and "Model investigates (for comparison) · Qwen 3 4B" (Evaluation, all five roles including Director and Brand Manager); "Briefing agent Haiku" (Director's Evaluation) | S15, S16, S23, S36, S41 (`vendor-name-visible`, 12 hits) |
| C-13 (Low-Med, unsupported claim) | "Story two: competitor Metacora (launched 2026-03-02). This is a continuing story, week 31 since launch, still growing." The chart under it shows Metacora's basket share roughly flat (about 15%) since late August | S08 |
| C-14 (Low-Med, copy) | Plain-language gaps in leadership copy: "feed gate", "Withheld cuts are left out of every change and story", "Driver timing: ... same week", "delays of one and two weeks", "like for like", "Candidate drivers: promotion", "claims"; "reference weeks" is never defined (see H-2) | S10, S21 |

## 4. UI, UX and accessibility

| # | Finding | Severity |
| :- | :- | :- |
| U-1 (ui) | Two classification labels on one screen: header "Confidential" (analyst) against the card's "Data classification: Proprietary" in the Leadership preview, and the Forecast Reports tab ("Proprietary") over an article tagged "Confidential"; the label changes between Draft and Approved tabs without a reason on screen (S10, S14, S30, S31, S15) | Low-Med |
| U-2 (ui) | Week selects hold 104 options (Overview, New briefing First week, Forecast scope) with no search or grouping; the oldest week is 104 clicks or key presses from the newest (S01, S04, S27, S42) | Low-Med |
| U-3 (ui) | Footnote superscripts merge into the value for copy and paste: selecting the first KPI copies "4,89126" (4,891 with evidence 26); 129 such superscripts in one brief. The claim buttons are named correctly for screen readers ("4,891, evidence 26"), so the problem is plain-text copy and any reader that flattens the DOM. The Leadership view has no superscripts (S08, S46; `footnote-merges-into-value`) | Med |
| U-4 (ui) | Section headings read as one word in the accessibility tree: "§1Bottom line", "§3.1Southeast" (the number and title have no separator in the heading's text) (S08 aria) | Low |
| U-5 (ui) | At 390 px the account button shows only an icon (no visible name); its accessible name "Account: Ace" is intact. Also the tab "Approved briefings" wraps onto a second row (S49) | Low |
| U-6 (ui) | 390 px: the territory table's Basis column is clipped ("observ") in the Director's summary; 9 to 24 controls on landing and form screens are under 24 px; the Director's summary is 11,358 px of scroll, about thirteen phone screens, with tables and long dates broken across lines (S50, S53; `small-tap-targets` on 7 screens) | Low-Med |
| U-7 (ui) | Times have no time zone: "Approved Nov 27, 1:27 AM" and "Approved by the Commercial Analyst · Nov 27, 1:27 AM" (the stored time is 06:27 UTC; the browser was set to New York), next to the ISO "reviewed by the analyst on 2026-11-27" (S14, S20, S21) | Low |
| U-8 (ui) | The "Territories with a material change" tile reads "0 of 8" on the default (latest) week for both brands, so the first screen offers nothing to look at; it is not always 0 (23 of the last 60 BXA weeks and 11 of 60 BXC weeks had at least one material territory, by the app's own overview API) (S01, S44) | Low-Med |
| U-9 (ui) | Roles are hard to tell apart: the account menu shows only a first name and, in dev, "Development sign-in"; no username or role. `roles.json` gives the Briefing analyst and the Forecast analyst the same label "Commercial Analyst". [NEEDS CLARIFICATION: what the hosted account menu shows, since dev sign-in replaces it] (S19, S43) | Low-Med |
| U-10 (ui) | The Forecast attribution chart truncates driver names ("Southeast rep coverage la…") (S28) | Low |
| U-12 (ui) | On the brief page the vote bar ("Was this answer right?") and the follow-up composer are fixed over the content. After Reject… the required reason box opens under the vote bar, so the box's own buttons are hidden until the page is scrolled; once a follow-up exists the page shows two vote prompts at once (the page's and the answer's) (S12) | Low-Med |
| U-11 (ui) | An unnamed level-3 heading sits at the top of the Forecast report body in the leadership and Brand Manager views (accessibility tree: `heading [level=3]` with no name, before "Covers: ...") (S31, S32, S39, S56) | Low |

## 5. Setup, configuration and security

| # | Finding | Recommendation |
| :- | :- | :- |
| S-1 (Med, security) | No security response headers on `/`, `/api/health`, `/auth/login` or `/api/me`: none of Content-Security-Policy, Strict-Transport-Security, X-Frame-Options (or `frame-ancestors`), X-Content-Type-Options, Referrer-Policy, Permissions-Policy. The hosted app's `/` (read-only `curl -sI`, one request) also returned none of them: only `content-type`, `cache-control: no-cache`, `etag`, `vary: Origin`, `server: Google Frontend` | Add one middleware for the six headers (CSP with `frame-ancestors 'none'`, nosniff, `Referrer-Policy: same-origin`, HSTS on Cloud Run); test them in pytest on `/` and `/api/me` |
| S-2 (Med, security) | `GET /api/telemetry` and `/api/telemetry/usage` return 200 for all five logins, so the Evaluation page (usage counts, golden-set scores, model names) is open to both leader roles and the Forecast lane's roles alike (`api.role_matrix`; S23, S41) | Decide who needs it (analysts and tester), return 403 to the rest, and remove the nav item for them |
| S-3 (Low, run error) | A normal visit throws console 403s: `GET /api/forecast/drivers` returns 403 to the Briefing analyst and to the Director each time the Evaluation page opens (S16, S23). `console.json`, `network.json` | Fetch only what the role may read, or return an empty list |
| S-4 (Low, security) | Design-tool comments in the served HTML: `<!-- figma:head-start -->`, `head-end`, `body-start`, `body-end` (8 matches) | Strip them in the standalone build |
| S-5 (Low-Med, ui) | No list of stubbed or conditional features. The user meets them one by one: Agent team radio disabled ("Waits until an agent host is available", S04), "Revise" disabled with "Revising by request needs a language model on the server" (S30), "Read by: keyword rules (no model is configured ...)" (S27), "this app is not running the team itself" (S15), the 20-question follow-up limit (S11) | Add one "What is live in this version" panel, or say it beside each control |
| S-6 (Low, security) | Dev sign-in strings reach users in dev only ("Development sign-in", the button list of every role on `/auth/login`); the app refuses dev mode on Cloud Run. Nothing to fix; recorded so the next review checks the hosted login page for them | Check the hosted login page in the next hosted review |

## 6. Evaluation page observations

| # | Finding | Evidence |
| :- | :- | :- |
| E-1 (Med, copy) | A rate with no sample guard: "Approved 100% 1 of 1 reviewed" in the headline figures after a single approval; "Usability (SUS scale) – no responses yet" is handled, the approval rate is not | S16 |
| E-2 (Low-Med, copy) | The golden-set block says "Exported Nov 23, 2026 ... Latest: Forecast, scripted baseline, Oct 29, 2026" under a page whose version label is "v1"; a reader cannot tell which version of the app the scores describe, or that the Forecast row shows "–" for key facts and findings (the figures are drafts until Alvin and Sienna confirm, which the page does say elsewhere) | S36, S41 |
| E-3 (Low, copy) | Headline "Typical response (live use) 1.3 s scripted engine, median of live requests golden set: 1.9 s a brief" mixes two measurements in one line, one of which contradicts "Instant" (C-11) | S16 |

## 7. Coverage and limits of this review

**Covered, as each role, desktop 1280x800:** Briefing analyst: Overview, the KPI query panel, the Southeast territory drawer, New briefing (period, "Add a comparison", engine, "Ask a question to fill the form"), triage plan, full brief in the analyst and Leadership views (Southeast, week of Oct 5, 2026), the evidence drawer, the follow-up chat (one chip, two typed questions), the Reject dialog, Approve, the Approved list, How it works, Evaluation, Share feedback and the questionnaire, the account menu. Director: landing, executive summary, the vote, Evaluation, Share feedback. Forecast analyst: example chip, scope check, investigation (national, week of 2026-08-24), a follow-up, Create report, analyst and Leadership views, Submit to Brand Manager; a provisional-week question (New England, week of 2026-05-04); a typed Southeast question to the scope check; Evaluation. Brand Manager: Reports to review, the empty Approved tab, the report, Approve, the Approved tab, Evaluation. Tester: account menu, second brand BXC (Overview, triage, brief), View as Leadership, Forecast workspace landing.

**API checks (no screenshots):** response headers; the role matrix over nine routes for all five logins; leader payload leakage; the Director's forbidden routes; four briefs (Southeast latest week; Southeast week of 2026-08-24; Pacific latest week; Southeast over 2026-08-24 to 2026-09-07) cross-checked against their own Assumptions and the Overview; the same Southeast week through the Forecast lane; the question reader with two date formats; the count of material territories over 60 weeks for both brands.

**390 px pass:** landing screens of all five roles, plus New briefing and the territory drawer (analyst), the executive summary (Director), the report (Brand Manager), the account menu (tester). Not walked at 390 px: the Forecast investigation, the Evaluation page, the evidence drawer.

**Not done on purpose:** an Agent-team brief (no Anthropic key configured; the radio is disabled without a host, S04); signing in to the hosted app (only one read-only header request); the hosted Keycloak logins and their account labels; load, concurrency and session-expiry behaviour; a real screen reader (judged from accessibility snapshots only) and keyboard-only traversal beyond the skip link and dialog Escape handling; briefs saved by an older version (the local state folder started empty, so the "old briefs in an old format" check could not run; the skill now seeds it from the previous review); colour contrast measurement; the hosted app's Evaluation numbers.

**Run errors:** none in the final run (an earlier run's failed steps were script drift and are fixed). Console: two 403s (S-3). Failed requests: the same two.

## 8. Suggested next steps (priority order)

1. H-1 and H-2 together: carry the Overview's normal-range verdict into the brief, and make every comparison in a brief use the window it states. These two change what a leader reads and what the Assumptions claim.
2. H-3: one definition of the usual rep-call level across both lanes, and let the Briefing name an episode the Forecast has found.
3. H-4: stop the canned follow-up answer and stop counting it.
4. S-1 and S-2: security headers, and role-gate the Evaluation data; strip the figma comments (S-4) in the same change.
5. C-3, C-7, C-6, C-2: the footer under drafts, the abstained Forecast answer, the date reader, and one date format in prose.
6. U-3 (footnote copy), U-1 (one classification label), E-1 (sample guard), C-12 (model names by role).
7. The rest of sections 3 to 6, in table order.
8. Run the skill on the next version with a state folder seeded from this run's briefs.

## Tests to add

One line per finding: the test that would prove the fix.

- H-1: golden case (Briefing, a territory inside its normal range) with a scorer that fails when §1, the story headline or §5 present the change as a finding without "within its normal range"; plus a pytest that the brief's story status equals `overview.territories[].status` for the same week.
- H-2: pytest over `/api/briefing/query` that parses the stated comparison window from the Assumptions and fails if any non-chart evidence record's `DATE` set reaches before it; golden case with a dip inside a longer window.
- H-3: cross-lane pytest: for a territory and week where the Forecast lane returns a coverage-lapse driver, the Briefing brief for the same territory and week names it and uses the same baseline.
- H-4: pytest that two different questions to `/api/briefing/{id}/thread/ask` do not return identical answers, and that an unmatched question does not increment the follow-up count; Playwright check of the "n of 20" counter.
- C-1: pytest that no triage or brief text matches `[A-Z]+_[A-Z0-9]+_[A-Z0-9_]+`.
- C-2: Playwright check that no visible text on the brief, triage and Forecast screens matches `\d{4}-\d\d-\d\d` outside the evidence drawer; a copy lint over the claim-token templates.
- C-3: Playwright check that the Leadership preview of a draft does not contain "approved analyst brief".
- C-4: golden case (territory-scoped brief) with a scorer that fails when the first sentence of §1 is not about the named territory.
- C-5: pytest that "projected" appears in §1 only when at least one territory in the brief has basis other than "observed".
- C-6: pytest on `/api/briefing/scope` that "Aug 24, 2026", "24 Aug 2026" and "2026-08-24" resolve to the same week, and that an unparsed date is reported, not defaulted.
- C-7: Playwright check that an abstained Forecast run shows no "Verification PASS" wording, no driver chips and no "Create report" for an empty attribution; golden case FE (abstain) with a UI assertion.
- C-8: Playwright check of the Brand Manager's empty Approved tab text.
- C-9: pytest that overview query results shown in the panel are rounded to one decimal (no float with more than 4 decimals in the response text).
- C-10: Playwright check that the Director's summary carries a vote only if the label names its object.
- C-11: copy lint for "Instant", "keyword rules", "Read by" in user-visible strings.
- C-12: Playwright check per role that none of Gemma, Qwen, Claude, Haiku, Anthropic appears for the Director, Brand Manager and Forecast analyst.
- C-13: golden case or scorer that "still growing" is allowed only when the last four weeks of the series rise.
- C-14: copy lint listing banned jargon in leadership sections.
- U-1: Playwright check that one screen shows one classification label.
- U-2: Playwright check that week selects have at most 60 options or are searchable (a combobox role).
- U-3: Playwright check that `innerText` of a KPI value contains no trailing evidence digits (superscripts in `aria-hidden` with a separator).
- U-4: Playwright check that heading text for sections contains a space between number and title.
- U-5: Playwright screenshot assertion at 390 px that the account button shows text or the icon has a visible label.
- U-6: Playwright check at 390 px: `scrollWidth <= innerWidth` for the summary and no clipped table cell; tap targets of at least 24 px.
- U-7: Playwright check that approval times include a zone ("EST", "UTC").
- U-8: pytest that the Overview default week is the latest week with at least one non-normal territory, or that an empty state explains the zero.
- U-9: Playwright check that the account menu shows the role label and username.
- U-10: Playwright check that the chart labels are not truncated at 1280 px (use full label in the title).
- U-11: Playwright aria check that every heading has a name.
- U-12: Playwright check that after clicking Reject… the reason box and its confirm button are inside the viewport and not covered by another element (`elementFromPoint`).
- S-1: pytest that `/`, `/api/me` and `/auth/login` carry the six headers.
- S-2: pytest that `/api/telemetry` returns 403 for the Director, Brand Manager and Forecast analyst.
- S-3: Playwright check that opening How it works and Evaluation as each role produces no console error and no 4xx.
- S-4: pytest that `frontend/figma-make/dist/index.html` has no `figma:` text.
- S-5: Playwright check that a "what is live" panel lists every disabled control.
- S-6: Playwright check against the hosted login page (read-only) that no dev strings appear.
- E-1: pytest on `/api/telemetry/usage` that a rate with fewer than 5 reviews is returned with a sample note; Playwright check of the headline text.
- E-2: pytest that the telemetry snapshot carries the app version it was scored on and the page shows it.
- E-3: Playwright check that one headline tile states one measurement.

## Evidence index

Folder: `local/reviews/2026-11-27-v1/screens/`

- S01: `01-d-analyst-overview.png`
- S02: `02-d-analyst-kpi-query-panel.png`
- S03: `03-d-analyst-territory-drawer.png`
- S04: `04-d-analyst-new-briefing-form.png`
- S05: `05-d-analyst-new-briefing-comparison-added.png`
- S06: `06-d-analyst-form-filled-from-question.png`
- S07: `07-d-analyst-triage-plan.png`
- S08: `08-d-analyst-brief-analyst-view.png`
- S09: `09-d-analyst-evidence-drawer.png`
- S10: `10-d-analyst-brief-leadership-preview.png`
- S11: `11-d-analyst-follow-up-chat.png`
- S12: `12-d-analyst-reject-dialog.png`
- S13: `13-d-analyst-brief-approved.png`
- S14: `14-d-analyst-approved-list.png`
- S15: `15-d-analyst-how-it-works.png`
- S16: `16-d-analyst-evaluation.png`
- S17: `17-d-analyst-share-feedback.png`
- S18: `18-d-analyst-questionnaire.png`
- S19: `19-d-analyst-account-menu.png`
- S20: `20-d-director-landing.png`
- S21: `21-d-director-executive-summary.png`
- S22: `22-d-director-vote-under-static-summary.png`
- S23: `23-d-director-evaluation.png`
- S24: `24-d-director-share-feedback.png`
- S25: `25-d-director-questionnaire.png`
- S26: `26-d-forecast-analyst-landing.png`
- S27: `27-d-forecast-analyst-q1-scope-check.png`
- S28: `28-d-forecast-analyst-q1-investigation.png`
- S29: `29-d-forecast-analyst-q1-followup.png`
- S30: `30-d-forecast-analyst-report-analyst-view.png`
- S31: `31-d-forecast-analyst-report-leadership-preview.png`
- S32: `32-d-forecast-analyst-report-submitted.png`
- S33: `33-d-forecast-analyst-q2-reliability-scope-check.png`
- S34: `34-d-forecast-analyst-q2-reliability-investigation.png`
- S35: `35-d-forecast-analyst-q3-southeast-scope-check.png`
- S36: `36-d-forecast-analyst-evaluation.png`
- S37: `37-d-forecast-manager-landing.png`
- S38: `38-d-forecast-manager-approved-reports-before-any.png`
- S39: `39-d-forecast-manager-report-for-review.png`
- S40: `40-d-forecast-manager-approved-reports.png`
- S41: `41-d-forecast-manager-evaluation.png`
- S42: `42-d-tester-landing.png`
- S43: `43-d-tester-account-menu.png`
- S44: `44-d-tester-bxc-overview.png`
- S45: `45-d-tester-bxc-triage-plan.png`
- S46: `46-d-tester-bxc-brief-analyst-view.png`
- S47: `47-d-tester-view-as-leadership.png`
- S48: `48-d-tester-forecast-landing.png`
- S49: `49-m-analyst-landing.png`
- S50: `50-m-analyst-new-briefing-form.png`
- S51: `51-m-analyst-territory-drawer.png`
- S52: `52-m-director-landing.png`
- S53: `53-m-director-executive-summary.png`
- S54: `54-m-forecast-analyst-landing.png`
- S55: `55-m-forecast-manager-landing.png`
- S56: `56-m-forecast-manager-report.png`
- S57: `57-m-tester-landing.png`
- S58: `58-m-tester-account-menu.png`
