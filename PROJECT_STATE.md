# Project state

A short summary of where the project stands, newest entry first. Detailed history is in `conversations/`. What each feature does and why is in `specs/`; the rules are in `.specify/memory/`.

_2026-11-22 (later), brief-008 in progress (Claude Opus, Sonnet packets)._
- Integration branch `feature/brief-008-readable-memo` holds packets M, F and R plus the leader period fix; not pushed. Scripted eval and full suite were running at handoff; G and W in their own worktrees. Handoff and next steps: `conversations/2026-11-22-brief-008-integration.md`.

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
