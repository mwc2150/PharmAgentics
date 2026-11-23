# brief-008 integration handoff (2026-11-22, Claude Opus; usage nearly spent)

## Where things are
- Integration branch `feature/brief-008-readable-memo` (worktree `C:/Users/micha/test_agent_v1/PharmAgentics-memo`), based on `main` `b694c6e` (PRs #18 and #19 merged). Merged so far: packet M (memo blocks, paragraphs, leader cut), packet F (first and last week, N-week comparison, `/api/briefing/scope` with the Haiku reader, account menu), packet R (KPI strip, territory table, story cards, folded detail, print rules), plus `c0bc982` (week_end in the leader and published views). Packet handoffs: `docs/handoffs/2026-11-22-brief-008-packet-{M,F,R}.md`.
- Untracked in that worktree: `specs/brief-009-agent-transparency/plan.md` and `tasks.md` (packets E and T). Commit them with this handoff.
- Running when usage ran out: the scripted eval then the full suite on `c0bc982`. Logs are in Claude's session scratchpad: `eval_008.log` and `pytest_008.log` (the second ends with `CHAIN_DONE`). If they are gone, rerun both.
- Wave 2, in progress in their own worktrees (they may have stopped mid-task; check `git log` and their `docs/handoffs/2026-11-22-brief-008-packet-{G,W}.md`):
  - G: DONE at `3a3c9ac` on `feature/brief-008-promotion` (`pa-008-G`); merge it. Open: P4-Q5 still needs a "when to re-read" line in `memo.next_checks` (patch in its handoff); lapse gap range is 116 to 177.
  - W: DONE at `199393d` on `feature/brief-008-writer` (`pa-008-W`); 44 focused tests pass; merge it. Watch `6_verification` dropped/revised counts in the Haiku run (stricter prose checks).

## Next steps
1. Read the eval log: gate the new scripted run against `c65d888fe3e444adab380e509f497a88` (`uv run python -m eval gate <run> c65d888fe3e444adab380e509f497a88`); all seven gated checks must be 1.000. Recall is report-only; packet M changed split values, so compare per case (SC-003 floor 0.668; P4-Q6 should rise after G).
2. Check the full-suite result; fix failures.
3. Merge G and W (both done) (packet text is in `specs/brief-008-readable-memo/tasks.md`), merge them into the integration branch, rerun the focused tests, the scripted run and the gate.
4. Real-app check (I2): `PHARMAGENTICS_AUTH=dev` local app; the leader and analyst views of the five anchor briefs printed to A4 (two pages at most).
5. `/code-review` at medium, fix, push, open the PR (Michael merges). Then the Haiku agent run and gate; update `PROJECT_STATE.md`.
6. Then brief-009 packets E and T, as in its plan.
