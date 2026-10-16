# Implementation Plan: Verifier

**Branch**: `008-verifier` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

Deterministic code checks run first and gate the brief. An optional LLM judge handles faithfulness and overclaiming, and only after its agreement with human labels is measured. One revision loop is allowed. Results are written per claim.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic, DuckDB (snapshot reads), spec 002 terms and wording rules, spec 005 evidence schema, spec 007 claim model; Gemini API for the judge
**Storage**: `brief_claims.verification_status`; `verification_result` table; judge labels file for agreement stats
**Testing**: pytest with planted-error fixtures; judge agreement script
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Code checks in seconds; judge within the token budget
**Constraints**: Code checks are deterministic. The judge never overrides a code failure. No answer-key access.
**Scale/Scope**: One brief per run, tens of claims

## Constitution Check

| Principle | Status |
|---|---|
| I Every number from a tool | Enforced here as the backstop to claim tokens. |
| IV Pinned data version | Reconciles to the pinned snapshot only. |
| V Traceable | Link resolution check. |
| IX No individual identified | Governance check. |
| XI Answer-key isolation | Verifier reads no ground truth. |
| XII Evaluation gate | A planted-error suite lives in the eval set. |

## Project Structure

```text
src/pharmagentics/verifier/
  tokens_check.py     token resolves; digits outside tokens
  reconcile.py        rendered values vs pinned snapshot with stated rounding
  evidence_check.py   story and numeric-claim coverage; link resolution
  wording_check.py    semantic-layer wording; causal-only-at-High
  governance.py       individual identification, banned terms, NRx vs NBRx
  judge.py            faithfulness and overclaiming judge; agreement gate
  agreement.py        judge vs human labels statistics
  verify.py           runs checks, sets status, drives one revision loop
tests/unit/verifier/  tests/integration/verifier/
```

## Key Design Points

- Check order: tokens, reconcile, evidence, wording, governance, judge. Any code failure is a failure regardless of the judge.
- Individual identification: a rule-based scan for names, IDs and single-person phrasing, plus the judge as a second look when trusted. The tools already aggregate rep data, so a hit here means a leak and is reported as a governance breach.
- Judge gate: `agreement.py` computes agreement on human-labeled briefs. If it is below the configured bar, `judge.py` runs in shadow mode and its output is logged but not scored.
- Failure tags come from the shared list and attach to each flag, so the failure catalog fills automatically.
- Revision: `verify.py` calls the writer once with flags. A second failure sets `VERIFICATION_FLAGGED`.

## Complexity Tracking

None.
