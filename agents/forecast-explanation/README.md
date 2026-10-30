# Forecast-Explanation Agent

Sienna & Alvin · PharmAgentics · v0.1 prototype

When weekly TRx forecast and actuals diverge, this agent explains **drivers, magnitude, confidence, and what to check**. It does not take commercial actions.

## Defaults locked for v1

- Streamlit brand-lead UI (English)
- Investigator talks to **Ollama** locally; API seam is left for a later OpenAI-compatible client
- Independent run, with an `InvestigationRequest` JSON handoff for the Briefing Agent
- Synthetic Week 18 case; remaining data is listed in `data/DATA_GAPS.md`

If Ollama is not running, use **stub** mode. The tools stay real; only the planner is scripted.

## Tonight's demo

```bash
cd forecast_explanation_agent
../.venv/bin/streamlit run app.py
```

Keep Investigator on `stub`. Then either click **Load briefing request** or ask the three questions:

1. Why did LUMINA miss in week 18?
2. How much of the miss is payer vs competitor?
3. What should we check next, and what is still unexplained?

Numbers come from DuckDB tables (`weekly_performance`, `commercial_events`). Ground truth stays in `eval_ground_truth` and is hidden unless you turn on the evaluator toggle.

## Forecast lane API (Figma Make Stage 4)

The 7-stage workbench stays in Figma Make. This process is Stage 4b plus pin, gate, detection, draft and `V = Σc + r`.

```bash
export PHARMAGENTICS_DATA_DIR=/path/to/PharmAgentics/data/agent_visible
../.venv/bin/python -m feagent.server
```

- `POST /forecast/runs` — full 7-stage payload the Make shell can render
- `POST /investigate` — `InvestigationReport` only
- `GET /forecast/cases` — the three Forecast-lane investigation cards
- `GET /demo` — browser smoke test

Make previews are HTTPS, so tunnel `:8787` (cloudflared or ngrok) before pasting the origin into Make.

## Run

From the repo root (`Forecast-explanation agent (Sienna & Alvin)`):

```bash
.venv/bin/pip install -r forecast_explanation_agent/requirements.txt
.venv/bin/pytest forecast_explanation_agent/tests
cd forecast_explanation_agent
../.venv/bin/streamlit run app.py
```

CLI handoff (same contract the Briefing Agent will post):

```bash
../.venv/bin/python -m feagent.api data/cases/week18_observable.json --mode stub
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

This machine already has Ollama up with `gpt-oss:20b`. Put that name in the sidebar (or `export OLLAMA_MODEL=gpt-oss:20b`). To use another model:

```bash
ollama pull llama3.1
export OLLAMA_MODEL=llama3.1
```

In the UI: set Investigator to `auto` or `ollama`. `auto` falls back to stub if the named model is missing.

## What is real vs placeholder

| Piece | v1 status |
| --- | --- |
| Investigation request schema | Stable handoff |
| Deterministic tools | Real on synthetic data |
| Stub investigator | Real playbook |
| Ollama investigator | Wired; needs a pulled model |
| Week 18 case | Placeholder with hidden ground truth |
| CMS / public calibration | Missing |
| Live Briefing Agent | Not wired; JSON contract only |
| Held-out evaluation suite | Not built |

## Layout

```
forecast_explanation_agent/
  app.py                 Streamlit UI
  feagent/               tools, investigator, Ollama client, request API
  data/cases/            observable case + evaluator-only ground truth
  data/DATA_GAPS.md      fields still to replace
  tests/                 Week 18 recovery checks
```
