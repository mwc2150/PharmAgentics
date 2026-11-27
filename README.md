# PharmAgentics v1

A multi-agent AI platform that helps pharma commercial teams see what moved a brand and why. One agent writes the weekly brand-performance briefing. The other explains forecast swings in plain language. Both run on a shared data layer and orchestration, and every number they state traces back to the data. v1 is the version we are demoing to the class.

**Team:** how to use, host, run and deploy the web app is in [docs/team/TEAM.md](docs/team/TEAM.md).

## Hosted app and logins

**App:** https://pharmagentics-app-18389319270.us-central1.run.app (synthetic data only; the first sign-in after a quiet spell takes 15 to 30 seconds while the sign-in service wakes up).

| Login | Password | Role |
| :- | :- | :- |
| `uat-briefing-analyst` | `1kS0UoPCUFR9aqw4` | Commercial Analyst (P1), Weekly briefing: runs a brief and sends it for sign-off |
| `uat-briefing-insights` | `Potk5cY8snyayrHb` | Insights Manager (P2), Weekly briefing: signs a brief off or returns it |
| `uat-briefing-director` | `J41a1R8lgkZUmkv2` | Brand Director (P3), Weekly briefing: signed-off briefs only |
| `uat-briefing-marketer` | `mZIJQCNASQgmhUXz` | Marketer (P4), Weekly briefing: signed-off briefs only |
| `uat-forecast-analyst` | `UHzTdiSH0hPIHmnC` | Commercial Analytics Analyst (CA), Forecast explanation |
| `uat-forecast-manager` | `eIaf0-YtGvg7nPca` | Brand Manager (BM), Forecast explanation |
| `uat-tester` | `BjpYK5HgqNCObxxL` | Test view: both lanes; "View as" in the account menu switches between Analyst (P1, CA), Insights Manager (P2), Leadership (P3, BM) and Marketer (P4) |

The same passwords work on the local stack (`deploy/make_env.py`, then `docker compose up --build`); they come from [`deploy/demo-credentials.env`](deploy/demo-credentials.env). They are shared on purpose: this is a class project on synthetic data. The service secrets in `deploy/.env.uat` are not, so keep that file out of git.

If you ran `env-pull` on 2026-11-19, run it again to get the right worker token: `uv run python deploy/gcp.py env-pull --project pharmagentics --account <you> --force`. Before `env-push` or `gcp.py keycloak`, check with Michael: those replace the live secrets for everyone.

## v1 at a glance

**Weekly briefing agent (Briefing lane).** An analyst picks a brand, a period and what to compare with, or types a question and lets the app read it into those choices. The agent team (Manager, Data Forensics, Driver Investigator, Writer) triages the changes, investigates the ones the analyst approves, and writes a memo of two pages at most: a KPI strip, a territory table, story cards with the drivers supported and ruled out, and the assumptions. Every number is a claim token filled by code from a governed query, so no digit comes from a language model. The analyst reviews and sends the memo for sign-off; the Insights Manager signs it off or returns it with a comment; the brand director and the marketer see an executive summary of signed-off briefings only.

**Forecast explanation agent (Forecast lane).** An analyst asks why the forecast missed. The agent reads the question into a scope, confirms it with the analyst, then splits the miss into driver contributions plus a residual that is reported, never absorbed into a driver. It can split an unexplained gap by channel, specialty and plan, chart its findings, answer follow-ups, and draft a report from pinned findings that the brand manager reviews. Code does all the arithmetic; the model only reads the question and words the result.

**Web app.** A React front end and a Python API over a shared DuckDB data layer. Sign-in is role based (analyst, leadership, tester). Analysts see the evidence behind every number; leaders do not. A live timeline shows what each agent did and links to the claims it produced. An Evaluation page shows the golden-set scores. The agents run on Claude Haiku 5.5 inside the app when the team key is set. The Forecast lane defaults to local Qwen 3 4B, and both lanes have a no-model mode.

**Evaluation harness.** 50 golden cases (32 Briefing, 18 Forecast), code checks, two controls and an optional local LLM judge, with every run, trace and span in MLflow. Every version of each agent answers the same cases. The Briefing targets are 0.85 for key-fact recall and 0.90 for finding recall. Both are report-only until two runs after the golden review, and judge scores never gate a merge.

Latest golden-set scores, from `src/pharmagentics/api/telemetry.json` (exported 2026-11-23 18:17 UTC). Briefing lane, 32 cases, one run each:

| System | Run started (UTC) | Key-fact recall (pooled) | Finding recall (pooled) |
| :- | :- | :- | :- |
| Scripted baseline, no model | 2026-11-23 17:29 | 1.000 | 1.000 |
| Agent on Claude Haiku 5.5 | 2026-11-23 08:49 | 1.000 | 0.971 |

Both are at or above the targets. The Haiku run missed one finding, the plan cut card in P2-Q4. The telemetry file has no run of the Forecast agent; the only Forecast run on record is the scripted baseline from 2026-10-30. The Forecast golden cases stay drafts until Alvin and Sienna confirm them.

**Deployment.** Docker Compose locally. In the cloud, Google Cloud Run on the free tiers with Keycloak for sign-in and Cloud Storage for approvals and usage events. A push to `main` deploys after CI passes.

## What's new (2026-11-22 to 2026-11-23)

### Weekly briefing

- The briefing is now a two-page memo you can read straight through: paragraphs, a KPI strip, a territory table, story cards and folded detail. The leader's view is a shorter cut of the same memo. Both print on two A4 pages.
- Choose the first and last week, and compare with the previous N weeks, last year or named weeks. Holiday weeks stay out of the period and are stated as an assumption.
- Type a question and press "Read my question". The app proposes the weeks, comparison and intent, and the analyst checks or edits them.
- The form sets what the brief counts: territories, measure (TRx, NBRx or both), grain and what to compare against. The choices print under Assumptions in the memo.
- New analyses: cut cards for plan and channel, percent movers by channel and specialty, restatement detail, data notes, a national TRx card with a competitive-intelligence reading, and cards for promotion lapses and access restrictions still running.
- The Promotion review is rewritten: one tested driver, a verdict either way, and no direction when the feed gate blocks TRx.
- Code fills the wording that matters. The comparison phrase and the causal verb ("drove" at High confidence, "moved with" below) come from tokens, and percentages print whole from 10% and with one decimal below.
- A live timeline shows each agent's steps while a brief runs, with links to the claims each step produced. Approved briefs show the same steps folded.
- A running brief stays visible when you switch tabs or lanes, and "Start a new briefing" sits next to the analyst and leadership toggle.
- A switch (`PHARMAGENTICS_ANTHROPIC_THINKING=off`) turns off Haiku's thinking blocks, which fixes agent runs that failed on newer Anthropic accounts.

### Forecast explanation

- Reports are built from pinned findings. Pin the investigation and its follow-ups, and the report drafts and redrafts itself, with every paragraph checked by code.
- Each answer offers charts: contributions from forecast to actual, territory misses against peers, miss by week, and forecast and actual by week. The model picks which help; code draws them.
- "Where the unexplained gap sits" splits a gap that has no driver by payer channel, specialty and plan. It says where the gap is, never why.
- Qwen 3 4B stays the default. Claude Haiku can be tried internally with `FORECAST_AGENT_MODEL`: it reads 97.5% of 40 paraphrased questions fully right, against 92.5% for Qwen and 37.5% for keyword rules.
- Review fixes: follow-ups check their territory and weeks before running, the engine refuses unknown cuts and bad dates, and stuck runs and drafts are marked failed instead of spinning.

### Evaluation

- Briefing answers are scored on key facts and expected findings, not only on number matches. Numbers are compared at the precision the answer prints, and a percent is never matched by a count.
- New report-only scores: key-fact recall, finding recall, false drivers, must-say phrases, scope match and brief length. Pooled recall counts crashed cases as misses.
- `eval insights` compares a run with the last clean one and lists what fell below target.
- The golden cases were aligned to the comparisons the app uses, and key facts and findings were drafted for the Briefing cases. They are marked `reviewed: false` until Michael reviews them.
- The Evaluation page shows a per-case table, the key facts and findings found in the newest runs, and plain model names.

### Web app

- Dark theme with a seafoam accent, Space Grotesk and IBM Plex Sans type, and the refreshed Pa logo with "v1" beside the name.
- Accessibility pass: keyboard patterns for tabs and menus, a skip link, focus traps in drawers, reduced-motion and forced-colour support, and no axe violations on the screens checked.
- One landing page per lane with a greeting by name, the brand picker beside the classification label, and sign-in pages in the same theme.
- A feedback card above the question bar: vote on an answer, then rate the session, each with an optional note.
- A notification dot marks newly approved briefings and forecast reports, on the tabs and in the sidebar.
- A five-question questionnaire (UMUX-Lite) collects responses. They export to the committed spreadsheet `feedback/class-demo-feedback.xlsx`, and testers get a "Questionnaire responses" panel.

### Platform and deployment

- The governed reporting views are stored as tables at load. A scripted brief now takes about 2 seconds at the median instead of 20, with the same answers.
- Sign-out survives a Keycloak restart, a failed sign-in callback offers "Sign in" again, and the app no longer shows a stale page after a deploy.
- Keycloak deploys are pinned to the realm version they were given, so the sign-in secret no longer drifts out of sync.
- `gcp.py telemetry` can read several MLflow stores, so one export covers runs from more than one checkout.
- The SQL guard rejects table functions and unqualified names, and CI runs the whole test suite.

### Repo

- `docs/handoffs/` replaces `conversations/` and `PROJECT_STATE.md`. The status command and the code map are generated, not committed.
- `docs/open-items.md` holds the known open work, `docs/guides/` the how-tos and `docs/team/` the team guide.
- `AGENTS.md` is shorter, and each main folder has its own `CLAUDE.md`. Golden-set changes go in `eval/golden/changes/`.
- New specs: `brief-008` (readable memo), `brief-009` (agent timeline), `brief-010` (target analyses) and `core-011` (eval revamp).

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
`uv sync` in the repository root. It installs Python 3.12 if needed and every
dependency pinned in `uv.lock`, the same on Windows, macOS and Linux. Python 3.11+
is the supported floor. Run commands through uv.

## Quick start

```powershell
uv run python src/pharmagentics/data/load_duckdb.py     # build the DuckDB database
uv run python src/pharmagentics/data/check_duckdb.py    # data checks
uv run pytest                                           # data, tools and eval tests
uv run python -m eval check                             # validate the golden cases
uv run python -m eval run --system briefing_scripted --lane briefing
uv run python -m eval ui                                # MLflow dashboard, http://127.0.0.1:5000
```

See [DuckDB first-run instructions](docs/guides/duckdb-first-run.md) for installation, data checks and example queries, [build and run](docs/guides/build-and-run.md) for every command, and [the eval harness](eval/README.md) for every check and result.

## Layout

| Path | Holds |
| :- | :- |
| `src/pharmagentics/` | Shared data layer and orchestration: data loader and checks, governed tools, MCP server, web API and roles, tracing |
| `agents/brand-briefing/` | Briefing lane: scripted baseline, low-code build and the agent team |
| `agents/forecast-explanation/` | Forecast lane: scripted baseline and the question-driven agent |
| `eval/` | Golden set, scorers, controls and the MLflow store |
| `frontend/figma-make/` | The web UI (React, Vite) |
| `deploy/` | Docker Compose, Keycloak realm, Google Cloud scripts, local agent worker |
| `feedback/` | Questionnaire responses from the class demo, exported to `class-demo-feedback.xlsx` |
| `specs/` | Spec Kit specs for each component |
| `docs/handoffs/` | One dated handoff per branch or session |
| `docs/guides/` | Build and run, workflow, DuckDB first run, UAT guides |
| `docs/team/` | Team guide for using, hosting and deploying the web app |
| `docs/planning/` | Markdown copies of the source documents |
| `data/agent_visible/` | The 14-table synthetic release |

## Ground rules

- The answer key and held-out cases live outside this repository. Agent code never reads `eval/`.
- Agents read data only through the governed views, never raw tables.
- No output line identifies an individual rep.
- "Competitive intelligence", never "surveillance". "New patients" only for NBRx.

`AGENTS.md` holds the full instructions for coding agents (`CLAUDE.md` imports it); `uv run python -m pharmagentics.devtools.status` prints where the project stands, from the handoffs in `docs/handoffs/`.
