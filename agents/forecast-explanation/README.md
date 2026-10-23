# Forecast-Explanation Agent

Sienna & Alvin · custom Forecast lane demo (DuckDB + Q&A)

When weekly TRx forecast and actuals diverge, this agent explains **drivers, magnitude, confidence, and what to check**. It does not take commercial actions.

This folder is the Forecast column. It is **not** wired to the Briefing Magentic loop. It uses a local LUMINA Week 18 DuckDB projection so the demo can run tonight. It does **not** replace Meghna's 14-table world in `data/agent_visible/`. Tools will retarget `forecast_vs_actual_weekly` after that world is the case source (System S3).

## Defaults locked for v1

- Streamlit brand-lead UI (English)
- Investigator talks to **Ollama** locally; API seam is left for a later OpenAI-compatible client
- Independent run, with an `InvestigationRequest` JSON handoff for the Briefing Agent
- Synthetic Week 18 case; remaining data is listed in `data/DATA_GAPS.md`

If Ollama is not running, use **stub** mode. The tools stay real; only the planner is scripted.

## Demo

From this folder:

```bash
python -m pip install -r requirements.txt
python -m pytest tests
streamlit run app.py
```

Keep Investigator on `stub`. Then either click **Load briefing request** or ask the three questions:

1. Why did LUMINA miss in week 18?
2. How much of the miss is payer vs competitor?
3. What should we check next, and what is still unexplained?

Numbers come from DuckDB tables (`weekly_performance`, `commercial_events`). Ground truth stays in `eval_ground_truth` and is hidden unless you turn on the evaluator toggle.

## CLI handoff

Same contract the Briefing Agent will post:

```bash
python -m feagent.api data/cases/week18_observable.json --mode stub
```

That file contains `default_request`. For a standalone request file, pass JSON with:

```json
{
  "request_id": "req_lumina_w18",
  "source": "briefing_agent",
  "brand": "LUMINA",
  "week": 18,
  "week_ending": "2026-05-08",
  "metric": "TRx",
  "notes": "Material TRx miss flagged for investigation."
}
```

## Ollama

```bash
ollama pull llama3.1
export OLLAMA_MODEL=llama3.1
```

In the UI: set Investigator to `auto` or `ollama`. `auto` falls back to stub if the named model is missing.

## What is real vs placeholder

| Piece | v1 status |
| --- | --- |
| Investigation request schema | Stable handoff |
| Deterministic tools | Real on the LUMINA projection |
| Stub investigator | Real playbook |
| Ollama investigator | Wired; needs a pulled model |
| Week 18 case | Placeholder with hidden ground truth |
| Shared 14-table world | Not queried yet |
| Live Briefing Agent | Not wired; JSON contract only |
| Held-out evaluation suite | Not built |

## Layout

```
agents/forecast-explanation/
  app.py                 Streamlit UI
  feagent/               tools, investigator, Ollama client, request API
  data/cases/            observable case + evaluator-only ground truth
  data/DATA_GAPS.md      fields still to replace
  tests/                 Week 18 recovery checks
```
