# Implementation Plan: Narrative and Renderer

**Spec**: [spec.md](spec.md) | **Branch**: `speckit-briefing` | **Date**: 2026-10-23 (replaces the 2026-10-16 plan for `007-narrative-renderer`)

## Summary

A constrained LLM writes section prose with claim tokens. Code builds every table and every disclosure: data health, KPIs, coverage labels, restatements, promotion context and glossary. A renderer resolves tokens against tool records with per-metric rounding. A fixed template and a length cap keep every brief in the Monday format.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Gemini API (structured output); Jinja2 for the template; Pydantic; core-002 (glossary, terms, wording map, functions); core-004 (records, claims)
**Storage**: `runtime.brief_claims`; drafts and rendered briefs as Markdown and HTML files keyed by `run_id`
**Testing**: pytest; golden-file render tests on the anchor weeks; scans for digits, banned and jargon terms, and every user-story "must not say"
**Target Platform**: Local; rendered for the review UI (brief-005)
**Project Type**: library
**Performance Goals**: Within the run's time cap; token budget from the semantic layer
**Constraints**: Writer input is the closed evidence pack, the continuity object and in-play definitions only
**Scale/Scope**: One brief per run, about 600 words plus tables

## Constitution Check

| Article | Status |
| :- | :- |
| Shared I Every number from a tool | Claim tokens; the renderer fills them. |
| Shared II People decide | The draft goes to review; nothing is sent. |
| Shared V Abstain | Low stories under "investigate next"; association wording for promotion. |
| Shared VI Synthetic data only | Only synthetic values and definitions reach Gemini (S14 review). |
| Briefing B-I One semantic layer | Glossary, wording map and term lists from core-002. |
| Briefing B-IV Traceable | Each claim stores its evidence IDs. |
| Briefing B-VI No individual identified | Code-built promotion table is territory-level; brief-004 scans. |

## Project Structure

```text
src/pharmagentics/narrative/
  template.py       sections, order, length limit
  tables.py         KPI table, data-health section, coverage labels, promotion context table
  writer.py         LLM call per section; structured output with tokens and a claims list
  tokens.py         parse, resolve, rounding
  renderer.py       fill tokens; fail on unresolved
  wording.py        confidence-to-wording map; association wording (from core-002)
  continuity.py     typed continuity object from episodic memory
  disclosures.py    restatement disclosure and footnotes
prompts/narrative/  versioned prompts with the STE style guide
tests/unit/narrative/  tests/integration/narrative/
```

## Key Design Points

- The writer returns, per section, text with `{{cNN}}` tokens plus a claims list naming each token's tool record and field.
- Every table and disclosure is code. The writer only references them.
- Rounding is per metric in the semantic layer; brief-004 reconciles the rendered value and the stated rounding.
- The wording map is data, so the verifier checks the same table.
- Method terms live in evidence notes reachable by click, never in prose.
- A revision pass takes flags or comments and redrafts only flagged sections.

## Complexity Tracking

None.
