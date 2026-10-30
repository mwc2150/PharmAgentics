# Brand-Performance Briefing Agent

The Briefing lane (Michael, Meghna): a weekly brand-performance brief that validates the data, finds material changes, tests competing explanations, and writes a brief in which every number is traceable.

## Built

`briefing_baseline/` is the **scripted baseline** (Evaluation Pack §6): a fixed pipeline with a fixed order of checks and a template brief. No model. Every number is a claim token filled by code from a stored SQL query, so the eval harness can re-run each one.

| Stage | Where |
| :- | :- |
| 1 load and pin; 2 validation gate; 3a competitive intelligence; 4a investigation; 5 narrative; 6 verification | `briefing_baseline/pipeline.py` |
| Question to weeks and territory | `src/pharmagentics/tools/window.py` (shared with the Forecast lane) |
| Driver checks (access, promotion, supply, competitor, data) and confidence rule | `src/pharmagentics/tools/checks.py` (shared) |
| Governed read-only data access, evidence items, claim tokens | `src/pharmagentics/tools/registry.py` (shared) |

Run it through the eval harness: `uv run python -m eval run --system briefing_scripted --lane briefing`. Not built yet: the low-code and agent versions, human review (stage 7), and a model-written narrative.

Agent code never imports `eval/`; the harness imports it.
