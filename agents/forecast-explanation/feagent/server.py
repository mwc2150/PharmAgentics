"""HTTP seam for the Figma Make Forecast lane (stage 4b)."""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from feagent import config
from feagent.api import handle_investigation_request
from feagent.pipeline import FORECAST_LANE_CASES, run_forecast_pipeline
from feagent.shared_world import available as shared_available

app = FastAPI(title="Forecast-Explanation Agent", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "lane": "forecast",
        "shared_world": shared_available(),
        "stage4": "agentic investigator (stub or ollama)",
    }


@app.get("/forecast/cases")
def forecast_cases() -> dict[str, Any]:
    return {"lane": "forecast", "cases": FORECAST_LANE_CASES}


@app.post("/investigate")
def investigate(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        run = run_forecast_pipeline(payload, mode=payload.get("mode") or "stub")
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run["report"]


@app.post("/forecast/runs")
def forecast_run(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return run_forecast_pipeline(payload, mode=payload.get("mode") or "stub")
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    return """<!doctype html>
<meta charset="utf-8">
<title>Forecast lane · stage 4</title>
<body style="font-family:sans-serif;max-width:720px;margin:2rem auto">
<h1>Forecast lane</h1>
<p>POST /forecast/runs for the national miss card.</p>
<pre id="out">loading…</pre>
<script>
fetch('/forecast/runs', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    request_id: 'fcst_nat_2026-08-24',
    source: 'manual',
    brand: 'BXA Cardiovela',
    week_start: '2026-08-24',
    territory_id: 'NATIONAL',
    metric: 'TRx',
    mode: 'stub'
  })
}).then(r => r.json()).then(j => {
  document.getElementById('out').textContent = JSON.stringify({
    fingerprint: j.fingerprint,
    status: j.workflow_status,
    stages: (j.stages||[]).map(s => s.id + '. ' + s.name + ' · ' + s.status + ' · ' + s.summary),
    headline: j.report && j.report.headline,
    variance_trx: j.report && j.report.variance_trx,
    residual_trx: j.report && j.report.residual_trx,
    abstained: j.report && j.report.abstained
  }, null, 2);
}).catch(e => document.getElementById('out').textContent = String(e));
</script>
</body>
"""


def main() -> None:
    # handle_investigation_request imported so the CLI contract stays in the package.
    _ = handle_investigation_request
    uvicorn.run(
        "feagent.server:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
