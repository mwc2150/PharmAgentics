# Handoff: brief-007 slices B and C (for Codex)

Written 2026-11-20 for a coding agent that has not seen this work. Read this file, then `CLAUDE.md` (the project's only instruction file; `AGENTS.md` points to it), then `specs/brief-007-windows-and-evidence/spec.md`. The decisions below were made with Michael (Briefing lane owner); do not reopen them. If something is not covered here or in the spec, stop and leave a note in `tasks.md` instead of guessing.

## Status when you start

- Slice A of brief-007 (4-week default baseline, window named in the brief, per-territory change table, feed figures, Assumptions block) ships in the memo pull request from `feature/brief-memo-follow-ups`, together with brief-003 v3 and brief-006.
- **Start from `main` after that pull request has merged.** Slices B and C edit the same files as slice A (`src/pharmagentics/tools/memo.py`, `stages.py`, `checks.py`); branching earlier means conflicts. Create `feature/brief-007-slice-b` (then `-slice-c`, or one branch for both).
- After checking out: `uv sync`, then `uv run python src/pharmagentics/data/load_duckdb.py` (the memo work added the view `reporting.v_rx_projection`).
- Gate baselines (runs to compare against): the slice A runs recorded in `tasks.md` T007 of this spec. Copy the MLflow store from the memo worktree if your checkout has none, or re-run the scripted and agent runs on `main` first and gate against those.

## Rules that are easy to break

- **No digit in any brief comes from a model.** Every number is a claim token `{cN}` registered through `Registry.claim(tool, sql, fmt, **scope)` and filled by code. Prose a model writes goes through the token checks; a digit outside a token fails verification. Dates in `YYYY-MM-DD` form written by code are fine.
- **Governed data only.** Metrics come from `reporting.*` views over `data/agent_visible/`; `raw.promo_activity`, `raw.inventory_weekly`, `raw.feed_metadata`, `raw.restatement_log` and `raw.calendar` are read as context, as the existing checks do. Never read `raw` tables for TRx.
- **Never read `eval/` from `src/` or `agents/`**, and never read anything through `PHARMAGENTICS_EVAL_STORE`. `eval/tests/test_isolation.py` enforces the first.
- **No individual rep.** Promotion is read only from aggregated columns (`rep_calls_aggregated`, `rep_vacancy_count_aggregated`). No line may name or imply one rep (Briefing constitution B-VI).
- **No attribution or ROI model** (Briefing constitution, Promotion). The Promotion review states associations and limits; it never prices a dollar or ranks channels. Causal wording only at High confidence.
- Wording: "competitive intelligence", never "surveillance"; "new patients" only for NBRx; short sentences.
- **Never edit `src/` or the agent prompts while an agent eval run is going**: the agent's MCP server reloads `src/` for every case.
- Keep `frontend/figma-make/src/App.tsx` changes to a few lines; put new UI in new files and add them to the allow-list in `tests/test_frontend_scope.py`.
- Commit by path. Do not push, open a pull request or merge unless Michael asks. A merge to `main` deploys.

## Slice B: Promotion review and lag-tested drivers (User Stories 2 and 5; FR-005, FR-006, FR-011)

### B1. Recognise a promotion question (code, not the model)
- `src/pharmagentics/tools/window.py` `parse(question, first_week, latest_week)` returns weeks, territory and note. Add a `promotion` flag set when the question contains a campaign, promotion, reach, response, lift or spend term (keep the term list in one constant; test it against P4-Q1 to P4-Q6, and check that P1 to P3 questions stay unflagged).
- When `promotion` is set and the question names no week, the scope is the whole release (`raw.calendar` first to latest week), for the named territory or all territories. `stages.resolve` must not fall back to the latest week in that case. Record the scope choice in `Period.note` and in the Assumptions block.

### B2. The review (both engines, one builder)
Build it in a new module `src/pharmagentics/tools/promotion.py`, returning memo lines with claim tokens, and fit it into the fixed six-section outline (brief-003): §2 the push table, §3 one story per lapse (§3.1, §3.2 …), §4 why return cannot be priced, §5 the experiment. Contents, from the spec and the golden references (`eval/golden/briefing/P4-Q*.yaml`; read them as the target, never from agent code):
- **Push**: per territory, the highest ratio of weekly `rep_calls_aggregated` and `digital_impressions` to that territory's release median, and how many consecutive weeks stayed above it; samples and speaker programs as single-week spikes. Golden P4-Q1: "never exceed 1.5 times their territory median; sample spikes last a single week".
- **Lapse**: a run of weeks in which a territory's aggregated calls fell well below its median (derive the threshold and minimum run from the data; the two lapses are Great Lakes, about 48 to about 20 calls a week, 2026-02 to 2026-04, and Southeast, 2026-08). Put the thresholds beside `MATERIAL_CHANGE` in `stages.py`. For each lapse: calls before and during; digital impressions against their median (Great Lakes 915 against 1,652); the territory's TRx change against the 4 weeks before, beside the other territories' change (−16.5% against +1.1%; reuse `stages.territory_change`); the gap in TRx a week (about 120 to 200); and the return week (Great Lakes 503 to 730 TRx when calls returned on 2026-04-13). Label the link "an association".
- **Limits** (§4): no spend data in the release; calls and digital impressions moved together (state their correlation over the release as a claim), so the channels cannot be separated or priced. Week 3 of the course: a media-mix model is the wrong tool without spend that varies.
- **Experiment** (§5): a territory holdout of promotion, with owner sales operations and the decision it unlocks; plus "discuss coverage backfill with sales operations at territory level" (P4-Q6, P3-Q5).
- Scripted engine: `agents/brand-briefing/briefing_baseline/pipeline.py` calls the builder when `p.promotion` and no week. Agent engine: expose it as one MCP tool in `src/pharmagentics/mcp_server/server.py` (pattern: `brief_sections`, `memo_close`) and route to it in `agents/brand-briefing/briefing_agent/prompts/manager_triage.md` / `manager.md`. The writer only adds prose; numbers stay code-built.

### B3. Lag-tested driver checks (FR-011)
- `src/pharmagentics/tools/checks.py`: `check_promotion`, `check_supply` and `check_access` compare driver weeks `W` with baseline `B`. Test the driver at lags 0, 1 and 2 weeks (shift the driver's weeks back by k with `queries.shift`) and use the lag at which the driver's change lines up with the TRx change; say which in the check line ("…, read with a one-week lag") or that none lines up. The data shows at most a weak one-week lag (Great Lakes calls against TRx: 0.42 at lag 0, 0.46 at lag 1; Southeast strongest at lag 0), so lag 0 must remain a normal outcome.
- Keep the constitution rule: never credit a driver whose activity did not change in the window or the tested lags.
- Add the lag to the Assumptions block.

### B tests and gate
- Unit tests next to `tests/test_tools.py`: question flagging, release-wide scope, lapse detection on Great Lakes and Southeast, every review number a claim, no "ROI"/"return on investment" figure, no rep wording.
- `uv run pytest`, then `uv run python -m eval run --system briefing_scripted --lane briefing` and, with `MLFLOW_GENAI_EVAL_MAX_WORKERS=4`, `uv run python -m eval run --system briefing_agent --lane briefing --model anthropic:claude-haiku-5-5` (key in the git-ignored `.env`; about $0.02 a brief). Gate each with `uv run python -m eval gate <new run> <baseline run>`: exit 0, every gated check 1.000. Report golden-number recall on P4-Q1 to P4-Q6 before and after (report-only).

## Slice C: window picker and story splits (User Stories 1 and 3; FR-002, FR-003, FR-008, FR-014)

### C1. Comparison window chosen by the analyst
- API: add an optional `comparison` to `BriefingQuery` and `AgentJobRequest` in `src/pharmagentics/api/schemas.py`: `{"kind": "previous", "weeks": N}`, `{"kind": "last_year"}` or `{"kind": "custom", "start": week, "end": week}`. Validate in code: custom weeks must end before the requested window and lie inside the release; last year must exist in the release; N between 1 and 13. Refuse with a reason before any brief is built.
- Pass it through the service and the agent job to `stages.resolve(reg, question, comparison=None)`, which sets `Period.baseline` and a `Period.baseline_source` ("default" or "analyst's choice"); the Assumptions block (slice A) reads the source. The model never sets it: the MCP server takes it from the job, not from a tool argument.
- UI: a new `frontend/figma-make/src/ComparisonPicker.tsx` beside the week and territory pickers on New briefing (`App.tsx` near lines 340, 402, 763 — a few lines only), analysts only; leaders get no picker (`src/pharmagentics/api/roles.json`, server-side check too). Add the file to `tests/test_frontend_scope.py`. Dark theme only.
- A follow-up that asks to change the window offers a new brief with that window (brief-006 FR-007 pattern); the current brief is never rewritten.
- Harness: let a golden case carry `comparison` and pass it to both systems in `eval/harness/systems.py`. Draft two cases (FR-014): one "same weeks last year" (P3-Q2's holiday weeks are a natural fit) and one custom window, with SQL facts, `status: draft`, `source: specs/brief-007-windows-and-evidence/spec.md#FR-014`. Michael labels them; run `uv run python -m eval check` to recompute their facts. Note them in `eval/golden/CHANGELOG.md`.

### C2. Story splits (FR-008)
- `split_change(self, territory, by)` exists in `src/pharmagentics/mcp_server/server.py` (line ~270; `SMALL_CELL = 50` at line 41) and is only reachable by the agent. Move its body into a shared function under `src/pharmagentics/tools/` so the scripted engine can call it too, and add plan, specialty and channel splits to each territory story's lines (§3.x) on both engines.
- Contributions must add up to the story's change (SC-006); cells under the floor are marked "small cell: noisy" or suppressed; call them "cuts of the change", never segments of prescribers (HCP segmentation is a use case the Proposal dropped).

### C tests and gate
- API tests for picker validation and the leader block; a test that the agent cannot set the window; split sums; `tests/test_frontend_scope.py`.
- Build the frontend (`npx tsc --noEmit -p tsconfig.app.json` and `npx vite build --config vite.config.standalone.ts` in `frontend/figma-make`).
- Real-app check: `PHARMAGENTICS_AUTH=dev` local app, and the Bombadil spec in WSL if available (`tests/ui/run_bombadil.py`; see `deploy/README.md`).
- Same eval gate as slice B.

## Open items to leave for Michael (do not decide)

- FR-010: the restatement window. Every restatement in this release landed 98 days after its week; the spec lists three options.
- SC-003: recall target 0.60 on the 24 single-turn cases (report-only).
- P2-Q6 (the version scorecard) is out of brief-007.

## When done

Tick the tasks in `specs/brief-007-windows-and-evidence/tasks.md` (add B and C tasks there in the same style), write the run IDs and gate output beside them, and leave a short summary for Michael at the top of this file.
