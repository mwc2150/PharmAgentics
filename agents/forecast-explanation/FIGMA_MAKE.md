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
- `workflow_status` → "Processing Complete — Pending Human Approval", or "Verification Failed — Needs Review" when stage 6 fails
- `stages[5].result.checks` → the verification checks (each has `id`, `status` pass / warn / fail, `detail`); `stages[5].status` is COMPLETE, FLAG or FAIL
- `report.drivers[*].confidence` and `report.drivers[*].confidence_reasons` → confidence label and why it is capped
- `report.window_weeks` → how many weeks the request covers (1 unless the card asks for more)
- `report.drivers[*].method` is `forecast_error_difference_vs_named_controls`: the driver's TRx is the exposed regions' forecast error (actual minus forecast) beyond what the control regions' forecast error implies. The older baseline-change number is kept only as a cross-check inside the evidence (`baseline_change_*`) and is not shown as the answer.
- `stages[5].result.checks` may contain `estimator_agreement:<driver>` with status `warn`: the two estimates disagree by more than a quarter of the miss, so show the driver with a caution.

## Cards that cover more than one week

Use the request body from `GET {BASE}/forecast/cases` for each card, unchanged. The Mid-Atlantic card (CA-Q5) must send `"window_weeks": 13`; without it the agent explains only the first week (V = -34) instead of the 13-week miss (V = -730). Send `window_weeks` only on cards that need it; the default is 1.

## Status values and errors

- Stage `status` is one of `COMPLETE`, `FLAG`, `FAIL`, `ABSTAINED`, `PENDING`. Stage 2 is `FLAG` and stage 4 is `ABSTAINED` when the actual is provisional (New England card); stage 6 is `FLAG` when it has warnings and `FAIL` when a check fails; stage 7 is always `PENDING`.
- **`workflow_status` does not change for an abstained run**: it still reads "Processing Complete — Pending Human Approval". Decide the banner from `report.abstained` and the stage statuses, not from that sentence alone.
- Bad input returns HTTP 400 with `{"detail": "<message>"}` (unknown territory or week, `window_weeks` outside 1-52, a window that runs past the data, a missing `request_id`). A body that is not a JSON object returns 422. Show `detail` as the error text.
- Steps to start the server, open the tunnel and test the three cards: `Claude/2026-10-30-sienna-handoff.md`.

Do not POST briefing cards to this endpoint. Briefing stays in its own lane. Neither agent calls the other (S1).
