# Implementation Plan: Narrative and Renderer

**Branch**: `007-narrative-renderer` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

## Summary

A constrained LLM writes section prose with claim tokens. Code builds the KPI table, glossary and footnotes. A renderer resolves tokens against evidence items and applies rounding. A fixed template and a length cap keep every brief in the Monday format.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Gemini API (structured output); Jinja2 or similar for the template; Pydantic; spec 002 glossary; spec 005 evidence schema
**Storage**: `brief_claims` table; drafts and rendered briefs stored as files keyed by run ID
**Testing**: pytest; golden-file render tests; scan tests for digits and banned terms
**Target Platform**: Local; briefs rendered to Markdown and HTML for the review UI
**Project Type**: library
**Performance Goals**: Draft and render within the run's time cap; token budget from the semantic layer
**Constraints**: Writer input is the closed evidence pack and the in-play metric definitions only. No raw tables.
**Scale/Scope**: One brief per run, about 600 words plus tables

## Constitution Check

| Principle | Status |
|---|---|
| I Every number from a tool | Claim tokens; renderer fills them. |
| II One semantic layer | Glossary and wording rules from the layer. |
| V Traceable | Each claim stores evidence IDs. |
| VIII People decide | Draft goes to review. |
| IX | Governance scan in spec 008, prompts forbid it. |
| X | Only synthetic data reaches the model, by policy; the data inventory review confirms. |

## Project Structure

```text
src/pharmagentics/narrative/
  template.py     sections, order, length limit
  kpi_table.py    code-built KPI table
  writer.py       LLM call per section, structured output with tokens
  tokens.py       claim token parse, resolve, rounding rules
  renderer.py     fill tokens; fail on unresolved
  wording.py      confidence-to-wording map (causal only at High)
  continuity.py   new vs continuing, improving vs worsening from memory
  footnotes.py    data-health footnote, restatement disclosure
prompts/narrative/   versioned prompt files
tests/unit/narrative/  tests/integration/narrative/
```

## Key Design Points

- The writer returns a structured section: text with `{{cNN}}` tokens plus a claims list. The claims list names each token's evidence ID and the metric field to show.
- Rounding rules are per metric in the semantic layer. The rendered number and the stated rounding are what spec 008 reconciles.
- The confidence-to-wording map is data, not prompt text, so the verifier checks the same table.
- Continuity comes from a query over prior runs' stories and claims (spec 006 memory). The writer gets a typed continuity object, not free text.
- A revision pass takes verifier flags or reviewer comments as input and redrafts only the flagged sections.
- STE: the prompt carries a short style guide. A style score is measured by human rubric and optionally the judge (spec 008).

## Complexity Tracking

None.
