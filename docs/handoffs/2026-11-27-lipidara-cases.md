---
branch: packet/lipidara-cases
lane: briefing
next: Michael reads docs/planning/user-stories-lipidara.md and reviews the 24 BXC cases (all reviewed: false); then merge, copy the stories into the master Google Doc, and decide whether a BXC agent build comes next
---

# 24 Lipidara (BXC) Briefing golden cases and the brand-aware harness

Based on `origin/main` 09cb1ed. Nothing pushed, no pull request. Model (Haiku, Ollama) evaluations were not run; the engine (`src/`, `agents/`) is untouched.

## What changed
- `docs/planning/user-stories-lipidara.md`: 24 stories, BXC-P1-Q1 to BXC-P4-Q6, in the format of `user-stories.md`. A draft for Michael to copy into the master doc. Every figure comes from SQL over the `reporting` views.
- `eval/golden/briefing/BXC-*.yaml`: 24 cases, ids C-033 to C-056, `brand: BXC`, draft, every fact and finding `reviewed: false`. 59 must facts, 161 context facts, 18 findings. Change record: `eval/golden/changes/2026-11-27-lipidara-cases.md`.
- Harness (`eval/` only): `brand` on a case (default BXA); `load_cases` and `golden_fingerprint` default to BXA; `eval run --brand BXA|BXC|all`; each system declares `brands` (only `reference` and `briefing_scripted` support BXC); an unsupported case is skipped and recorded (`skipped_cases`, `cases_skipped`), never run, scored or counted as an error; a BXC or mixed run is its own system row (`briefing_scripted@BXC`), a mixed run adds `_bxa` and `_bxc` pooled metrics; `eval import-stories --brand BXC` drafts from the Lipidara stories and never overwrites; `eval check` covers all brands and now flags a duplicate id. Tests: `eval/tests/test_brand.py` (43 tests, including the positive control on every Lipidara golden answer).

## Results
- `eval check`: 56 Briefing and 18 Forecast cases, 24 of them Lipidara; 401 of 401 facts recompute.
- `uv run pytest eval`: 261 passed.
- BXA proof: `briefing_scripted` on the Briefing lane, before the harness change on the branch base, run `720d14105df74d71aa7f98406d767350`; after, with `--brand BXA`, run `562610393835492ab2b09733794fae89`. Every metric is identical, `golden_version` is identical (4145b1d7e08e), the only differing param is `code_version` (dirty tree). `eval gate 562610393835492ab2b09733794fae89 720d14105df74d71aa7f98406d767350` exits 0.
- First Lipidara reading, untuned (no engine change): run `98be9351d11f4cb4bd842e0f46b6f0df` (`briefing_scripted@BXC`, 24 cases): `key_fact_recall_pooled` 0.763 (45 of 59), `finding_recall_pooled` 0.700 (35 of 50), `must_not_say` 1.000, `run_errors` 0. An earlier BXC run (`e7a8aa59bcc04260a0eead125bce4c8a`) had the same recalls and `must_not_say` 0.958; it is superseded because the P3-Q2 must-not-say phrase was reworded as judge-only (the correct brief states the drop).
- What the untuned engine misses on Lipidara: no plan-level card for the Mid-Atlantic Medicare Part D plan (P1-Q4, P2-Q4, P3-Q5, P4-Q4: the plan has no access change for BXC, only for the competitor), promotion and plan figures in P4-Q3, the June share figures in P3-Q3, and the `data` ruled-out driver in P2-Q2.

## Open issues for Michael
1. Competitor access context (Cardiovela's tier change on the Mid-Atlantic plan) is cited in five cases; core-010 does not say whether it is permitted in a BXC workspace.
2. Only `briefing_scripted` runs BXC. The agent and low-code builds still raise for BXC, and `--brand BXC` skips their cases.
3. `eval gate` compares the `<scorer>/mean` metrics, which MLflow averages over every case in a run, so gate BXA-only runs against BXA-only baselines. A mixed run is for reading, not gating.
4. A BXC or mixed run is a separate system row so it never replaces Cardiovela's latest scores in `eval export-telemetry` or `eval insights`; the Lipidara rows are not in the hosted Evaluation page.
