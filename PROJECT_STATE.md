# Project state

A short summary of where the project stands, newest entry first. Detailed history is in `conversations/`. What each feature does and why is in `specs/`; the rules are in `.specify/memory/`.

_2026-11-22 (late night), core-011 follow-ups ready for review: exact-value scoring, targets, cuts, word budget (Michael, Claude Opus with a Sonnet packet)._
- Branch `feature/core-011-exact-values` (FR-016 to FR-021). Numbers are scored against each fact's exact value from its SQL, rounded half up to the precision the answer prints, so a brief that rounds the true value once (22.45 as "22%") is no longer failed by a golden figure rounded twice ("22.5"). Findings and cards take an optional `cut`; facts and findings an optional `needs` tag; targets live in `scorers.TARGETS`; every run logs `key_fact_recall_pooled`, `finding_recall_pooled`, `key_fact_target_met`, `finding_target_met` and `over_word_budget`; `eval insights` and the Evaluation page list below-target cases. The word budget is the longest anchor brief that prints on two A4 pages: 836 words analyst, 705 leader.
- Scripted run `ebb2952a8faf491cbffc5513c279d322` gated against `a5a4968270cb47af890796f2c2979c45`: exit 0, all seven 1.000. Against the targets: key facts 0.682 pooled (0.85), findings 0.529 pooled (0.90), two briefs over budget (C-001 915 words, C-016 930). Full suite 948 passed (10 subtests). `eval check` 180 of 180.
- Decided with Michael (grills, 2026-11-22 night): optimize for the targets, not plain recall; the golden review was done in the grill (21 at-target cases approved; three cases restated like-for-like; plan cuts; capability tags); golden and brief disagreed because of unstated assumptions, so every brief is built from an explicit **brief definition** of six analyst selectors (period, comparison, territories counted, measure, grain, relative to), and golden cases carry the same definition. That is brief-010 (`specs/brief-010-target-analyses/`, branch `feature/brief-010-targets`), building now: packets D-B (backend), D-U (form) and G (golden definitions and the review), then the national card, restatement detail, plan cuts and segment percent.
- Not done: `/code-review` on this branch; the Haiku agent run on it (scorer-only change, gated checks untouched). Handoff: `conversations/2026-11-22-core-011-follow-ups.md`.

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
