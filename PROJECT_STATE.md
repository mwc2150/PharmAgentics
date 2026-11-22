# Project state

A short summary of where the project stands, newest entry first. Detailed history is in `conversations/`. What each feature does and why is in `specs/`; the rules are in `.specify/memory/`.

_2026-11-22 (night), repo layout PR-A: code map, nested CLAUDE.md, Repomix (Michael, Claude Opus with Haiku packets)._
- Branch `feature/repo-layout-a` (from `758b4d0`), additive only; decisions in `docs/adr/0004-repo-layout-and-context-map.md`.
- `AGENTS.md` 12.2k -> 5.1k characters. Hard rules unchanged; the Workflow and Build and run sections moved verbatim to `docs/guides/workflow.md` and `docs/guides/build-and-run.md`; Layout moved to the generated `docs/architecture/CODEMAP.md` (`uv run python -m pharmagentics.devtools.codemap`, about 4.9k tokens, `tests/test_codemap.py` fails when stale, never reads `eval/`).
- Nested `CLAUDE.md` (`@README.md` + folder rules) in `eval/`, `src/pharmagentics/`, `agents/brand-briefing/`, `agents/forecast-explanation/`, `deploy/`, `specs/`; new `docs/README.md`, `tests/README.md`, `conversations/archive/`.
- `repomix.config.json`: `npx repomix` writes a compressed pack to `local/repomix-pack.xml` (153 files, about 158k tokens; security check clean).
- Tests: `tests/test_codemap.py` + `eval/tests/test_isolation.py` 8 passed (pytest), codemap 3 passed (unittest). No system changed, so no eval run.
- Next: PR-B (move-only `git mv` of TEAM.md and the loose docs guides) and PR-C (link fixes, `sql/` -> `src/pharmagentics/data/sql/`, fixture regen, scripted gate) after core-011 merges and its worktrees are pruned. Handoff: `conversations/2026-11-22-repo-layout.md`.

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
