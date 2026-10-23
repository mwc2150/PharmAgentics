# Paste into Figma Make (Forecast lane)

Keep the workbench. Do not re-implement the Investigator.

When someone clicks a **FORECAST LANE** card, or **Run** on Forecast explanation, POST the case JSON to the Forecast agent and fill the 7-stage inspector from the response.

Base URL: replace with the HTTPS tunnel to Alvin's `python -m feagent.server` (port 8787).

```
POST {BASE}/forecast/runs
Content-Type: application/json

{
  "request_id": "fcst_nat_2026-08-24",
  "source": "manual",
  "brand": "BXA Cardiovela",
  "week_start": "2026-08-24",
  "territory_id": "NATIONAL",
  "metric": "TRx",
  "mode": "stub"
}
```

Map the JSON:

- `stages[0..6]` → Pipeline Inspector (status + summary)
- `report.headline` → Executive Explanation
- `report.drivers` → attribution table
- `report.residual_trx` → residual / V = Σc + r
- `report.what_to_check` → checks
- `report.abstained` → pause attribution (New England provisional card)
- `workflow_status` → Processing Complete — Pending Human Approval

Do not POST briefing cards to this endpoint. Briefing stays in its own lane. Neither agent calls the other (S1).
