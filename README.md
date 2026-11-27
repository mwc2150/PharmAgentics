# PharmAgentics v2

A multi-agent AI platform that helps pharma commercial teams see what moved a brand and why. One agent writes the weekly brand-performance briefing. The other explains forecast swings in plain language. Both run on a shared data layer and orchestration, and every number they state traces back to the data. v2 is the current version, built on the feedback from the v1 class demo.

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

## v2 at a glance

**Weekly briefing agent (Briefing lane).** Two brands, Cardiovela (BXA) and Lipidara (BXC). An analyst picks a brand, a period and what to compare with, or types a question and lets the app read it into those choices. The agent team (Manager, Data Forensics, Driver Investigator, Writer) triages the changes, investigates the ones the analyst approves, and writes a memo of two pages at most: a KPI strip, a territory table, story cards with the drivers supported and ruled out, and the assumptions. The brief follows its stated assumptions: it compares only with the weeks it names, and credits nothing inside the normal range. Every number is a claim token filled by code from a governed query, so no digit comes from a language model. The Commercial Analyst sends the memo for sign-off; the Insights Manager signs it off or returns it with a comment; the Brand Director and the Marketer see an executive summary of signed-off briefings only, and the Marketer also gets a promotion read under each territory story.

**Forecast explanation agent (Forecast lane).** An analyst asks why the forecast missed. The agent reads the question into a scope, confirms it with the analyst, then splits the miss into driver contributions plus a residual that is reported, never absorbed into a driver. It can split an unexplained gap by channel, specialty and plan, chart its findings, answer follow-ups, and draft a report from pinned findings that the Brand Manager reviews. Code does all the arithmetic; the model only reads the question and words the result.

**Web app.** A React front end and a Python API over a shared DuckDB data layer. Sign-in is role based, with seven UAT logins (below). An Overview workspace shows the week by territory and starts a brief or a forecast explanation from it. Analysts see the evidence behind every number; leaders do not. A live timeline shows what each agent did and links to the claims it produced. An Evaluation page shows the golden-set scores. The agents run on Claude Haiku 5.5 inside the app when the team key is set, with prompt caching; an agent brief costs about a cent. The Forecast lane defaults to local Qwen 3 4B, and both lanes have a no-model mode.

**Evaluation harness.** 75 golden cases (57 Briefing: 33 Cardiovela and 24 Lipidara; 18 Forecast), code checks, two controls and an optional local LLM judge, with every run, trace and span in MLflow. Every version of each agent answers the same cases, and every run reports its tokens and estimated cost. The Briefing targets are 0.85 for key-fact recall and 0.90 for finding recall. Both are report-only until two runs after the golden review, and judge scores never gate a merge.

Latest golden-set scores, from `src/pharmagentics/api/telemetry.json` (exported 2026-11-27 19:24 UTC). Briefing lane, three passes for the agent:

| Brand | System | Run started (UTC) | Key-fact recall (pooled) | Finding recall (pooled) | Cost a brief |
| :- | :- | :- | :- | :- | :- |
| Cardiovela, 33 cases | Scripted baseline, no model | 2026-11-27 18:31 | 1.000 | 1.000 | $0 |
| Cardiovela, 33 cases | Agent on Claude Haiku 5.5 | 2026-11-27 18:54 | 1.000 | 0.971 | $0.013 |
| Lipidara, 24 cases | Scripted baseline, no model | 2026-11-27 18:33 | 0.780 | 0.714 | $0 |
| Lipidara, 24 cases | Agent on Claude Haiku 5.5 | 2026-11-27 18:34 | 0.780 | 0.714 | $0.007 |

Cardiovela is at or above both targets. Lipidara is under them on both engines; the gaps are listed in `docs/handoffs/2026-11-27-lipidara-cases.md`, and its golden cases are drafts until reviewed. These are development (golden) scores: the held-out results are not in yet (due 2026-12-04). The Forecast golden cases stay drafts until Alvin and Sienna confirm them.

**Deployment.** Docker Compose locally. In the cloud, Google Cloud Run on the free tiers with Keycloak for sign-in and Cloud Storage for approvals and usage events. A push to `main` deploys the app after CI passes; Keycloak deploys by hand with `deploy/gcp.py keycloak`.

## What's new in v2 (2026-11-24 to 2026-11-27)

### Weekly briefing

- The brief follows its Assumptions: no comparison window it does not state, nothing credited inside the normal range, and a promotion lapse the period falls in is named (brief-011).
- Lipidara (BXC) joins Cardiovela, with lag-tested driver checks, the lapse rule, the Promotion review, plan and continuing cards by brand, and 24 new golden cases (brief-014).
- Two-step sign-off: the Commercial Analyst sends, and the Insights Manager signs off or returns the brief with a comment and flags on single claims. A review history keeps every step (brief-012).
- The promotion verdict tests controls first, says "not testable" where no channel moved, reads new patients first and covers four channels. The Marketer sees that read under each territory story, with a budget note (brief-013).
- Two tabs: New briefing, with six example questions and **Your briefing questions** (every brief started from a question) under the form, and **Your briefings**, sorted into Approved, Needs you, With the reviewer and a Rejected fold. A brief made and left stays there to open.
- Follow-ups: free text goes to the agent (up to 20 per brief); the suggested questions stay scripted and free. The Insights Manager can ask follow-ups on a brief sent for sign-off.
- The question reader takes written dates (Aug 24, 2026; 24 Aug 2026; 8/24/2026).

### Forecast explanation

- Tabs New explanation and **Your reports** (the Brand Manager: Reports), with the same sections as Your briefings; questions and reports are listed together.
- "Explain the forecast miss" on an Overview territory fills the question in for roles with Forecast access. The engine, access and logins are unchanged.

### Evaluation

- The Evaluation page names each Briefing run's brand (Briefing agent · Cardiovela, · Lipidara).
- Every run logs its tokens and estimated cost; How it works shows what a brief costs. Prompt caching cut a Cardiovela agent brief from $0.030 to $0.025 in a two-case test, with the same scores.
- A UAT review of v1 (`docs/reviews/2026-11-27-uat-review-v1.md`, 39 findings) and a `uat-review` skill to repeat it.

### Web app

- **Overview**, its own workspace and the first item in the sidebar: the week's figures by territory, each with its queries, and a drawer that offers "Brief this week" or "Explain the forecast miss". The Commercial Analyst and the Insights Manager open it; the Director and the Marketer see who to ask for access.
- **Settings**: light or dark theme (dark by default), density, motion, date style, footnotes, and a default brand and engine, kept per browser.
- **Recents** at the foot of the sidebar: the last six things each role works on, with All briefings and All reports beside it.
- Motion: page transitions, tile headings, figures that roll in and charts that draw as they scroll into view. Reduced motion turns it off.
- Hover text sits beside the pointer instead of under it; the data classification is a small chip with a four-step level meter.
- The sign-in and sign-out pages match the app and say v2, and all seven UAT logins work on the hosted app.

### Platform and deployment

- Prompt caching for the agent's tool loops (`PHARMAGENTICS_ANTHROPIC_CACHE=off` turns it off).
- `GET /api/briefing/mine` lists a login's own briefs in every state; the Overview has its own role action (`overview`).
- Security headers, the approval rate counted over decided briefs only, and readable plan names, from the UAT review.

Earlier changes, v1 included, are in the dated handoffs in [`docs/handoffs/`](docs/handoffs/).

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
