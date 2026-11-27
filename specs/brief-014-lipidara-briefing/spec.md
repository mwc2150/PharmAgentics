# brief-014: Lipidara (BXC) on the Briefing lane

**Spec ID**: brief-014-lipidara-briefing (Briefing lane)
**Created**: 2026-11-27 (v2; written after the code, invariants and acceptance tests only, per the v2 spec format)
**Branch**: feature/v2-assumptions-first
**Source**: Michael's v2 decisions of 2026-11-27 (Q4, Q21). core-010 (multi-brand access) is unchanged; this spec states what v2 adds for the second brand.

## Why

v1 briefed Cardiovela (BXA) with both engines and only partly supported Lipidara (BXC). v2 gives Lipidara the same Briefing lane: both engines, the lag-tested driver checks, the Promotion review, the question reader and its own golden cases, built like Cardiovela's.

## Invariants

- **I1. Same engine, any Briefing brand.** The scripted engine and the agent team (`BRIEFING_ENGINES["BXC"] = ("scripted", "agent")`) run BXC through the same checks as BXA; nothing in the Briefing code names BXA where the brand is a parameter. The Forecast lane stays BXA (it has no BXC series).
- **I2. Assumptions hold for every brand.** brief-011's invariants (I1 to I6) are asserted on every Lipidara golden case as on Cardiovela's.
- **I3. Golden cases.** 24 Lipidara cases (`eval/golden/briefing/BXC-P1-Q1` to `BXC-P4-Q6`), built like Cardiovela's from the same four personas' questions on Lipidara's data, in the repository, drafts until reviewed. `eval run --brand BXC|BXA|all` selects them; a run logs pooled metrics per brand (`briefing_scripted@BXC`).
- **I4. Gate per brand.** A Briefing change is gated on each brand it touches.

## Acceptance tests

- `tests/test_lipidara_engine.py` (I1: checks, lapses, the Promotion review, the question reader and the agent run take the brand).
- `tests/test_follows_assumptions.py::test_claims_read_only_stated_weeks` over both brands' cases (I2).
- `eval/tests/test_brand.py` (I3). `uv run python -m eval check` recomputes every Lipidara fact.
- 2026-11-27: `eval gate` on BXC passed (v2 run 20c2323f against the cases-only baseline 65245c85).
