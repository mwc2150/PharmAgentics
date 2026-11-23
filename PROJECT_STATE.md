# Project state

A short summary of where the project stands, newest entry first. Detailed history is in `conversations/`. What each feature does and why is in `specs/`; the rules are in `.specify/memory/`.

_2026-11-23 (early morning), brief-010 ready to merge: the brief definition and the analyses the targets need (Michael, Claude Opus with Sonnet and Haiku packets)._
- Branch `feature/brief-010-targets` (PR #25): the six-selector brief definition; plan cut cards, segment and channel percent, restatement detail and data notes, a national card on every brief (TRx direction, holiday rule, story-territory ruled-out rule), continuing cards, the golden `intent` field. The word budget is no longer a target (Michael, 2026-11-23); it stays report-only.
- Scripted run `60927c3280374d748a44c55ca309b8d1` gated against `1b8eaaafd97f438f90e8b0e8528a4884`: exit 0, all seven 1.000. Finding recall pooled 1.000 (was 0.618), key facts pooled 1.000 (was 0.857), false drivers 0.074 (was 0.12).
- Haiku run `6f62d72ae3ba4327bd52d8145aac31be` (code `d3d01d5`) gated against `727bc0064e75480cbd73dca00748f56e`: exit 0, all seven 1.000, no run errors. Finding recall pooled 0.971 (target 0.90), key facts pooled 1.000, false drivers 0.074. One miss: P2-Q4's plan cut card, which the Manager left out. An earlier run `364c704c` on `1591779..cce5df9` crashed on 5 cases (a citation-index KeyError, fixed in `d3d01d5`). The four review fixes in `da4b00d` came after this run and are covered by tests.
- CI full suite green after 12 cross-packet fixes; `/code-review` medium: four important findings fixed. App check through the API in both views.
- Next: merge #25, then PR #26 (UI refresh; brief-010 already merged into it locally), then the repo reorg. Open: P4-Q3 and WIN-2 golden findings omit promotion for the Southeast gap (Michael). Handoff: `conversations/2026-11-23-brief-010-integration.md`.
_2026-11-23 (early), Briefing agent on Haiku: thinking-block 400s on newer Anthropic accounts, and an opt-in switch (Sienna, Claude Opus). On `main`._
- Found while recording the demo on Sienna's Anthropic key: the Briefing agent team often fails with HTTP 400 "Invalid `signature` in `thinking` block. The block is bound to a different conversation." Claude Haiku 5.5 thinks by default, and Magentic's orchestrator rewrites its own history (progress ledger reset), which Anthropic refuses on accounts held to the history-editing check; older accounts may not be held to it yet. The run then stalls ("Max reset count reached").
- Opt-in fix in `src/pharmagentics/llm.py`: `PHARMAGENTICS_ANTHROPIC_THINKING=off` makes `chat_options` send `thinking: {type: disabled}` to Claude (no thinking blocks). Unset, requests are unchanged. With it on, three Briefing agent runs and the demo recording completed with no errors. Tests: `tests/test_llm_options.py`.
- Open (Michael): decide whether the hosted and default setups should turn thinking off, or keep thinking and send the `thinking-binding-controls-2026-08-01` beta with `prefix_mismatch_behavior: drop_block`. Not measured on the golden set with the switch on. Handoff: `conversations/2026-11-23-haiku-thinking-blocks.md`.

_2026-11-23 (early), Forecast: Claude Haiku measured as an internal trial model; default stays local Qwen (Sienna, Claude Opus). Docs only, on `main`._
- No code change: the model is a server setting for trials, as in Briefing. `FORECAST_AGENT_MODEL=anthropic:claude-haiku-5-5` in the git-ignored `.env` (or exported before `docker compose up`) switches the Forecast lane to Haiku after a restart; unset is local Qwen 3 4B. Users never choose it. A per-question picker was built and then dropped at Sienna's request.
- Measured on the forty scope paraphrases, current reader: rules 37.5%, local Qwen 92.5% (`300ab924`, 10.5 s), Haiku 97.5% (`301b4800`, 1.9 s). Golden set with Haiku: `accf8a276cbb43d6bbb741a8edcc6164`, all seven gated 1.000, golden number recall 0.593, about 11 s a question; `eval gate` against `227ed3253e3d4e72b642075054f134f6` exit 0. fcst-002 SC-004 updated (its open item for a Haiku rerun is resolved). Data version unchanged.
- Open: Alvin to agree whether Haiku replaces Qwen once the designs are set; the hosted app would bill the team key (Michael). Handoff: `conversations/2026-11-22-fcst-haiku-option.md`.

_2026-11-22 (late night), brief-009 agent transparency ready for review (Claude Opus with Sonnet packets)._
- Branch `feature/brief-009-timeline`: packet E (each run records code-built events on both engines; the timeline fills in live from the full `progress` list on every poll; every claim links to the event that produced it; leaders get a one-line `process_summary` only) and packet T (the timeline, the How-it-works tab, `GET /api/briefing/agents` with prompt refs `<id>@sha256[:7]`), plus eleven `/code-review` fixes (progress saved on a 3 s beat, not once per event under the jobs lock; chunked worker posts; early-return briefs keep their events; leader review date in the viewer's local time).
- Scripted run `e4e5194e91254a5398daf2e58b66caa2` (after the fixes) and `104da6d2e59d424ca3e3716d6982396b` (before) gated against `a5a4968270cb47af890796f2c2979c45`: exit 0, all seven 1.000, answers unchanged (recall 0.682, findings 0.750, 656 words). Haiku run `be5f26cde73d4bf595ef44d32a97d488` against `727bc0064e75480cbd73dca00748f56e`: exit 0, all seven 1.000, no run errors, recall 0.682 (no numbers lost).
- Full suite 933 passed; the Forecast split follow-up test failed under load and passes alone (known flake). Live check on Haiku (dev auth): 25 events streamed, six actors, 82 of 82 claims linked to an event, leader view has no event keys and gets 403 on the job route.
- Next: merge after `feature/brief-008-polish` (PR #22); both touch `briefing_agent/__init__.py`. Handoff: `conversations/2026-11-22-brief-009-integration.md`.

_2026-11-22 (late night), core-011 follow-ups ready for review: exact-value scoring, targets, cuts, word budget (Michael, Claude Opus with a Sonnet packet)._
- Branch `feature/core-011-exact-values` (FR-016 to FR-021). Numbers are scored against each fact's exact value from its SQL, rounded half up to the precision the answer prints, so a brief that rounds the true value once (22.45 as "22%") is no longer failed by a golden figure rounded twice ("22.5"). Findings and cards take an optional `cut`; facts and findings an optional `needs` tag; targets live in `scorers.TARGETS`; every run logs `key_fact_recall_pooled`, `finding_recall_pooled`, `key_fact_target_met`, `finding_target_met` and `over_word_budget`; `eval insights` and the Evaluation page list below-target cases. The word budget is the longest anchor brief that prints on two A4 pages: 836 words analyst, 705 leader.
- Scripted run `ebb2952a8faf491cbffc5513c279d322` gated against `a5a4968270cb47af890796f2c2979c45`: exit 0, all seven 1.000. Against the targets: key facts 0.682 pooled (0.85), findings 0.529 pooled (0.90), two briefs over budget (C-001 915 words, C-016 930). Full suite 948 passed (10 subtests). `eval check` 180 of 180.
- Decided with Michael (grills, 2026-11-22 night): optimize for the targets, not plain recall; the golden review was done in the grill (21 at-target cases approved; three cases restated like-for-like; plan cuts; capability tags); golden and brief disagreed because of unstated assumptions, so every brief is built from an explicit **brief definition** of six analyst selectors (period, comparison, territories counted, measure, grain, relative to), and golden cases carry the same definition. That is brief-010 (`specs/brief-010-target-analyses/`, branch `feature/brief-010-targets`), building now: packets D-B (backend), D-U (form) and G (golden definitions and the review), then the national card, restatement detail, plan cuts and segment percent.
- Not done: `/code-review` on this branch; the Haiku agent run on it (scorer-only change, gated checks untouched). Handoff: `conversations/2026-11-22-core-011-follow-ups.md`.

_2026-11-22 (late night), brief-008 polish ready for review (Claude Opus with a Sonnet packet)._
- Branch `feature/brief-008-polish` (FR-014 to FR-018): the comparison phrase and the causal verb are code-filled tokens (`{cmp}`; `{link}` = "drove" at High, "moved with" below); Briefing percentages are whole from 10% up and one decimal below (Forecast keeps one decimal); Writer prompts state the limits the code checks; the reader records its scope proposal, so `scope_match` scores (0.821 on Haiku).
- Scripted run `ef64671bd20941cc804e19a665c971dc` gated against `a5a4968270cb47af890796f2c2979c45`: exit 0, all seven gated checks 1.000. Recall (pooled key facts) 0.682 -> 0.667: C-009 and C-022 gain from the comparison token; C-025 and C-028 lose because the brief now prints 22% for a backorder rate the data holds as 22.45, which the golden writes 22.5 (scored against the written figure, so rounded twice). The exact-value scorer (core-011 FR-016) fixes that on its own branch from `main`.
- Haiku run `5307588bff2240af8c7101930cca3c4a` gated against `727bc0064e75480cbd73dca00748f56e`: one asyncio `InvalidStateError` crash (P2-Q3, a concurrency flake with four workers), which cost `claims_reconcile` and `links_resolve` one case each (0.969); the case reruns clean alone (`51f0499570054ec6a2fcdf99f26ea4ad`, all gated checks 1.000). The other 31 cases pass every gated check.
- SC-006 not met: `needed_revision` 0.625 -> 0.531 (target 0.15). Causes: causal words below High confidence (8), the model wording the comparison itself (7), too many sentences (4), spelled-out numbers (2), one long sentence.
- Focused suite 371 passed. Next: code replaces a known comparison phrase with the `{cmp}` fill before the check; Michael decides how to handle causal words; brief-009 packet E resumes; then brief-010. Handoff: `conversations/2026-11-22-brief-008-polish.md`.

_2026-11-22 (night), core-011 eval revamp ready for review (Claude Opus with Sonnet packets)._
- Branch `feature/core-011-eval-revamp`: packets A (key-fact and finding recall, brevity, must-say), B (`eval insights`), C (per-case table on the Evaluation page, analysts and the tester only), D (golden facts and findings, `reviewed: false`), E (story cards carry territory, direction and the drivers supported and ruled out, both engines), F (scorer kinds code/agent/safety/ops, `scope_match`, "numbers lost by the agent", unit-aware matching) and G (golden definitions aligned to the case text or the house four weeks before), plus ten `/code-review` fixes.
- Decided with Michael (deterministic first): code fills whatever it can; agent checks score inference. "Recall" now means pooled key-fact recall.
- Scripted run `a5a4968270cb47af890796f2c2979c45` gated against `986836db`: exit 0, all seven gated checks 1.000. Recall (pooled key facts) 0.682; finding recall 0.750; false drivers 0.11 a case; must-say 0.429; golden-number recall 0.677 (unit-aware; was 0.607 on the old golden and matching).
- Haiku run `727bc0064e75480cbd73dca00748f56e` gated against `48565a28` (brief-008 I4, itself gated against `ae4c68b6`: recall 0.525 -> 0.703): exit 0, all seven at 1.000. Same recall and findings as scripted (no numbers lost); 774 words a brief against 656; needed revision 62.5% (the polish branch targets <= 15%).
- Full suite on A to E: 855 passed; one Forecast API test failed only under load and passes alone on this branch and on `main`. Later packets touched `eval/` and the Evaluation page only: eval, telemetry, frontend-scope tests 220 passed; `eval check` 180 of 180 facts; tsc and build clean.
- Next: Michael reviews the golden edits (review page) before `key_fact_recall` and `finding_recall` join `GATED` (FR-006); `feature/brief-008-polish` (FR-014 to FR-018) is in progress; then brief-010 (percent change by segment, channel and specialty; NBRx cuts; restatement detail; peer-trend counterfactual).

_2026-11-22 (evening), core-011 eval revamp planned (Michael, Claude)._
- `golden_number_recall` is 0.682 per case but 0.593 over all 167 golden numbers; about 12 misses are approximate golden wording and about 45 are analyses the system does not do. Decided: tag golden facts (must or context, exact values, SQL), score `key_fact_recall` and `finding_recall`, add `eval insights` and a per-case Evaluation view; 0.95 recall dropped as a goal; the missing analyses go to brief-010. Spec: `specs/core-011-eval-revamp/`. Packets A (Sonnet) and D, B (Haiku) start now; A, B and D are merged on the branch; brief-008 merged to `main` as PR #20, so C and E start now.

_2026-11-22 (evening), brief-008 readable memo merged as PR #20 (Claude Opus, Sonnet and Haiku packets)._

_2026-11-22 (late), review fixes for the Forecast lane and shared guards (Sienna, Claude Opus). Branch `fix/forecast-review-2026-11-22`, not committed or pushed._
- From the whole-repo review the same day. Forecast lane: a follow-up rerun's model-chosen territory and weeks are checked before anything runs (an unknown name used to answer "0.0% above forecast" from zero rows); the engine refuses an unknown cut, a non-ISO week and a payer channel the data lacks (it was put into SQL text); an investigation, follow-up or report draft lost to a restart now shows as failed and can be asked again, instead of staying "running" for ever; every change to a stored run is read, changed and saved under one lock, so a background save cannot overwrite a review. fcst-002 FR-016 and FR-017.
- Shared (please review, Michael and Meghna): `check_sql` now reads the relations from DuckDB's own parse, so quoted or spaced schemas, comments, unqualified names, `information_schema` and table functions (`read_csv`, `duckdb_tables`) are refused; `digits_outside_tokens` now refuses a word that starts with a digit ("12k", "3x", "300TRx", "2nd"), as brief-004 FR-002 already required. CI: the integration job runs the whole pytest suite (it ran only the unittest-style files, so 21 test files and every Forecast test were in no job); the eval job runs `eval check`.
- Full suite 848 passed (10 subtests), with no model reachable, as in CI. Gates on data version unchanged: `forecast_rules` `227ed3253e3d4e72b642075054f134f6` vs `e307d1aaf38d4cddab17f4a274b74790`, and `briefing_scripted` `4bf4fd7f5e104a48a935903aa8f4f79c` vs `360ca41f3af64e2490e42c8085c9a293` (both baselines run on unchanged `main` 758b4d0): exit 0, all seven gated checks 1.000, recall unchanged (0.592 and 0.703).
- Not done: the Haiku Briefing agent run on the stricter digit check; Python 3.11 not run locally (CI matrix covers it). Still open from the review: the eval gate passes a metric missing on one run, and `claims_reconcile` runs evidence SQL unguarded. Handoff: `conversations/2026-11-22-forecast-review-fixes.md`.

_2026-11-22 (evening), brief-008 readable memo ready for review (Claude Opus, Sonnet and Haiku packets)._
- Branch `feature/brief-008-readable-memo`: packets M (memo blocks, paragraphs, leader cut), F (first and last week, "previous N weeks", Haiku scope reader, account menu), R (KPI strip, territory table, story cards, print), G (Promotion review in blocks, the dollar question, P4-Q5 routing) and W (Writer paragraphs), plus integration fixes: multi-week period in the leader and published views, a re-read next check, readable plan names, print fit, and seven `/code-review` fixes (the form sends no comparison unless the analyst picks one, so app briefs match what the eval scores).
- Scripted run `12cb72c894dc4bfaba08d3e604448b53` gated against `c65d888fe3e444adab380e509f497a88`: exit 0, all seven gated checks at 1.000, no run errors. Golden-number recall (report-only) 0.668 -> 0.703; "How confident is the estimate" 0 -> 0.67; P4-Q6 stays 0 because its golden says "about 120 to 200" (core-011 makes that figure context). One case lost a single-week change that a 13-week brief no longer quotes (by design, FR-011).
- After the `/code-review` fixes: full suite 823 passed (10 subtests); final scripted run `986836db4e6b4362bf256905237e3368` gated against `c65d888f`: exit 0, all seven at 1.000, recall 0.703.
- Print (SC-002): the leader and analyst views of the five anchor briefs each print on two A4 pages, rendered through the API and the app's own memo component and CSS; the leader print keeps small charts, the analyst print keeps chart captions. Analyst a3 and a4 nearly fill page 2.
- Not done yet: the Haiku agent run and gate (I4); §1 and §2 still read one sentence per line (follow-up); brief-009 packets E and T. Handoffs: `conversations/2026-11-22-brief-008-*.md`.

_2026-11-22, Briefing: state after brief-007, and the plan for brief-008 and brief-009 (Michael, Claude)._
- `main` at `c704632` holds the memo brief (PR #13), brief-007 slice A (#16), slices B and C (#17, Codex) and core-010 multi-brand access (#15).
- Slices B and C merged without a scored run. They were checked afterwards on `8ddd84e`:
  - Scripted run `c65d888fe3e444adab380e509f497a88` (32 cases) gated against the memo baseline `a4df1c30339f4cafabd292bcae83a052`: exit 0, all seven gated checks at 1.000, no run errors.
  - The full suite passed: 697 tests and 10 subtests.
  - Golden-number recall (report-only) rose from 0.406 (memo) and 0.498 (slice A) to 0.668.
  - The Haiku agent run on B and C has not been done.
- Known gaps on `main`:
  - "Where should the next dollar go?" (P4-Q6) gets the same text as P4-Q1; recall 0.
  - P4-Q5 (draft) is routed to the Promotion review; recall 0.33 → 0.
  - Promotion review wording: "1 weeks", raw plan IDs, upper-case specialties, signed decimals.
  - The Promotion review's Assumptions block says "no earlier weeks", which is wrong for that review.
  - Multi-week briefs quote a single-week change in the territory table.
- Mentor feedback: the leadership brief reads as a wall of text. The memo's structure is right on both engines, but every section reaches the UI as lines of text in one block.
- Decided with Michael (grill, 2026-11-22). Next work, in order:
  1. This repo layout: `AGENTS.md`, `PROJECT_STATE.md` and `conversations/`. Specs and project state work together.
  2. brief-008, the readable memo:
     - Both views at most two pages, in natural-language paragraphs.
     - A KPI strip, a territory table, charts and story cards.
     - Leaders keep the assumptions and the limits.
     - The answer text the evals score is unchanged.
     - First and last week fields, plus a "previous N weeks" comparison (1 to 13, default 4).
     - Haiku proposes the question's scope, the analyst confirms it and code validates it. This needs Briefing constitution v1.1.0.
     - The account menu loses the lane list.
     - The gaps above are fixed.
  3. brief-009, agent transparency:
     - Four actors in the UI: Manager, Data Forensics, Driver Investigator, and Writer as an LLM step.
     - A live timeline for each run.
     - A "How it works" tab.
- How the work is built: Opus plans and reviews. Sonnet agents build work packets in their own worktrees, at most three at once, and never push. The full suite, the scripted gate and a code review run before each pull request.
- Open for Michael: FR-010 restatement window (brief-007); the SC-003 recall target of 0.60.
- Handoffs: `conversations/2026-11-20-brief-007-coordination.md`, `conversations/2026-11-20-brief-007-codex-handoff.md`.
