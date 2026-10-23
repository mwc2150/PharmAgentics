# Implementation Plan: Verifier

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `008-verifier`)

## Summary

Deterministic code checks run first and gate the brief: tokens, reconciliation, evidence, disclosures and coverage, wording, governance. An optional judge checks faithfulness and overclaiming, in shadow mode until its agreement is measured. One revision loop is allowed. Results are written per claim with a failure tag.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic; DuckDB (pinned-snapshot reads through core-003); core-002 terms, wording map, small-cell floor; core-004 records and claims; Gemini API for the judge
**Storage**: `brief_claim.verification_status`; `runtime.verification_result`; a labels file for agreement statistics
**Testing**: pytest with planted-error fixtures built from the user stories' "must not say" phrases
**Target Platform**: Local
**Project Type**: library
**Performance Goals**: Code checks in seconds; judge within the token budget
**Constraints**: Code checks are deterministic. The judge never overrides a code failure. No answer-key access
**Scale/Scope**: One brief per run, tens of claims

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | Backstop to claim tokens. |
| Shared V Abstain | Causal wording gate; promotion only with a supported verdict. |
| Briefing B-III Pinned version | Reconciles to the pinned snapshot only. |
| Briefing B-IV Traceable | Link resolution check. |
| Briefing B-VI No individual identified | Governance check. |
| Shared III | Reads no ground truth. |

## Project Structure

```text
src/pharmagentics/verifier/
  tokens_check.py     tokens resolve; digits outside tokens
  reconcile.py        rendered values vs pinned snapshot with stated rounding
  evidence_check.py   story and claim coverage; link resolution
  disclosure_check.py restatement disclosure; coverage labels
  wording_check.py    per-metric wording; causal only at High; association for promotion; jargon
  governance.py       individual identification; banned terms; NRx vs NBRx; small-cell generalization
  judge.py  agreement.py
  verify.py           runs checks in order, sets status, drives one revision
tests/unit/verifier/  tests/integration/verifier/
```

## Key Design Points

- **Order**: tokens, reconcile, evidence, disclosure and coverage, wording, governance, judge. Any code failure fails the brief regardless of the judge.
- **Planted-error suite**: one fixture per user-story "must not say" phrase in the Briefing stories (for example "Great Lakes BXA TRx was 670", "BXA fell 18% nationally", "Metacora caused…", "promotion caused a 120 TRx lift", "cash patients respond most to promotion"), plus wrong number, stray digit, missing token, missing evidence, rep name, banned term.
- **Individual identification**: rule-based scan for names, IDs and single-person phrasing; the judge as a second look when trusted. A hit is a leak from upstream and is tagged governance breach.
- **Judge gate**: below the bar, `judge.py` runs in shadow mode; output is logged, not scored.
- **Revision**: `verify.py` calls stage 5 once with flags; a second failure sets VERIFICATION_FLAGGED.

## Complexity Tracking

None.
