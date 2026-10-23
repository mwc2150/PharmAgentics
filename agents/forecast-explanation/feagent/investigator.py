from __future__ import annotations

import json
from typing import Any

from feagent.config import MAX_INVESTIGATOR_STEPS, OLLAMA_MODEL
from feagent.llm import LLMClient, OllamaClient, parse_json_message
from feagent.schema import (
    CheckItem,
    DriverEstimate,
    InvestigationReport,
    InvestigationRequest,
    ToolRecord,
)
from feagent.tools import TOOL_SPECS, run_tool


SYSTEM_PROMPT = """You are the Forecast-Explanation Investigator for a pharmaceutical brand.
You explain forecast-versus-actual TRx variance. You do not make commercial decisions.

Rules:
- Cite only numbers returned by tools. Never invent TRx figures.
- If controls are weak, evidence conflicts, or data are missing, abstain or mark confidence inconclusive.
- Overlapping drivers must not be forced into a fully additive story.
- When finished, return action=final with a report object.

Reply with ONLY JSON, one of:
{"action":"tool","name":"<tool_name>","arguments":{...}}
{"action":"final","report":{...}}

final.report fields:
headline (string),
drivers (list of {driver, impact_trx, confidence, method, evidence_ids, notes}),
what_to_check (list of {question, why, owner}),
caveats (list of strings),
abstained (boolean)

Tools:
""" + json.dumps(TOOL_SPECS, indent=2)


def run_investigation(
    request: InvestigationRequest,
    mode: str = "auto",
    case_id: str = "week18",
    client: LLMClient | None = None,
) -> InvestigationReport:
    if mode == "stub":
        return run_stub(request, case_id)
    if mode == "ollama":
        return run_ollama(request, case_id, client)
    if mode == "auto":
        ollama = client or OllamaClient()
        ok, _reason = ollama.available()
        if ok:
            try:
                return run_ollama(request, case_id, ollama)
            except Exception:
                return run_stub(request, case_id)
        return run_stub(request, case_id)
    raise ValueError(f"Unknown investigator mode: {mode}")


def run_stub(request: InvestigationRequest, case_id: str = "week18") -> InvestigationReport:
    evidence: list[dict[str, Any]] = []

    quantified = run_tool("validate_and_quantify", {"week": request.week, "case_id": case_id})
    evidence.append(quantified)
    q = quantified["payload"]
    if not q.get("ok"):
        raise RuntimeError(q.get("error") or "validate_and_quantify failed")

    if q.get("actual_is_provisional"):
        residual = float(q["variance_trx"])
        headline = (
            f"{q['brand']} actual is provisional in week ending {q['week_ending']}; "
            "attribution is paused."
        )
        return _report(
            request,
            q,
            headline,
            [],
            residual,
            [
                CheckItem(
                    question="Re-run this cut after a complete feed lands.",
                    why="The forecast table marks the actual provisional; a miss here is not a demand shock.",
                    owner="Commercial analytics",
                )
            ],
            [
                "Provisional actuals are withheld from driver attribution (FE-01 to FE-03).",
                "Do not report a percent miss on a failed cut.",
            ],
            evidence,
            investigator_mode="stub",
            model=None,
            abstained=True,
        )

    deltas = run_tool("get_region_deltas", {"week": request.week, "case_id": case_id})
    evidence.append(deltas)

    events = run_tool("list_candidate_events", {"week": request.week, "case_id": case_id})
    evidence.append(events)

    driver_impacts: dict[str, float] = {}
    driver_rows: list[DriverEstimate] = []
    for event in events["payload"]["events"]:
        contrast = run_tool(
            "compare_exposed_control",
            {"event_id": event["event_id"], "week": request.week, "case_id": case_id},
        )
        evidence.append(contrast)
        payload = contrast["payload"]
        if not payload.get("ok") or payload.get("estimated_total_trx") is None:
            continue
        impact = float(payload["estimated_total_trx"])
        driver_impacts[payload["driver"]] = impact
        driver_rows.append(
            DriverEstimate(
                driver=payload["driver"],
                impact_trx=impact,
                confidence="high" if payload["control_regions"] else "inconclusive",
                method=payload["method"],
                evidence_ids=[contrast["tool_id"]],
                notes=payload.get("notes") or payload["label"],
            )
        )

    recon = run_tool(
        "reconcile_attribution",
        {"variance_trx": q["variance_trx"], "driver_impacts": driver_impacts},
    )
    evidence.append(recon)
    residual = float(recon["payload"]["residual_trx"])

    headline = (
        f"{q['brand']} missed forecast by {abs(q['variance_trx']):,.0f} {q['metric']} "
        f"({q['variance_pct']:.0%}) in week ending {q['week_ending']}."
    )
    checks = [
        CheckItem(
            question="Confirm Plan Alpha's week-17 formulary change with market access.",
            why="Payer contrast recovers most of the miss, but the event calendar is still synthetic.",
            owner="Market access",
        ),
        CheckItem(
            question="Validate Rivalza launch timing and Midwest exposure with competitive intelligence.",
            why="Competitor estimate uses West as control; a national launch would remove that control.",
            owner="Brand analytics",
        ),
        CheckItem(
            question="Inspect the unexplained residual before treating it as noise.",
            why=f"{residual:,.0f} {q['metric']} remains after payer and competitor estimates.",
            owner="Forecasting",
        ),
    ]
    caveats = [
        "Numbers are from deterministic tools on a synthetic case.",
        "v1 identification excludes contaminated regions rather than jointly modeling overlapping shocks.",
        "Public CMS calibration has not been applied yet.",
    ]
    return _report(
        request,
        q,
        headline,
        driver_rows,
        residual,
        checks,
        caveats,
        evidence,
        investigator_mode="stub",
        model=None,
        abstained=False,
    )


def run_ollama(
    request: InvestigationRequest,
    case_id: str = "week18",
    client: LLMClient | None = None,
) -> InvestigationReport:
    client = client or OllamaClient()
    ok, reason = client.available()
    if not ok:
        raise RuntimeError(reason)

    evidence: list[dict[str, Any]] = []
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "Investigate this forecast miss.",
                    "request": request.__dict__,
                    "case_id": case_id,
                    "instruction": "Start with validate_and_quantify.",
                }
            ),
        },
    ]

    quantified: dict[str, Any] | None = None
    for _ in range(MAX_INVESTIGATOR_STEPS):
        raw = client.complete(messages)
        messages.append({"role": "assistant", "content": raw})
        parsed = parse_json_message(raw)
        action = parsed.get("action")
        if action == "tool":
            name = parsed["name"]
            arguments = dict(parsed.get("arguments") or {})
            arguments.setdefault("case_id", case_id)
            result = run_tool(name, arguments)
            evidence.append(result)
            if name == "validate_and_quantify":
                quantified = result["payload"]
            messages.append({"role": "user", "content": json.dumps({"tool_result": result})})
            continue
        if action == "final":
            if quantified is None:
                quantified = run_tool(
                    "validate_and_quantify", {"week": request.week, "case_id": case_id}
                )["payload"]
            return _report_from_model(
                request, quantified, parsed.get("report") or {}, evidence, client.model
            )
        raise RuntimeError(f"Unexpected model action: {parsed}")

    raise RuntimeError("Investigator exceeded MAX_INVESTIGATOR_STEPS without a final report")


def ollama_status(model: str | None = None) -> dict[str, Any]:
    client = OllamaClient(model=model or OLLAMA_MODEL)
    try:
        installed = client.list_models()
        ok, detail = client.available()
    except Exception as exc:
        return {
            "ok": False,
            "detail": f"Ollama not reachable at {client.host}: {exc}",
            "host": client.host,
            "model": client.model,
            "installed": [],
        }
    return {
        "ok": ok,
        "detail": detail,
        "host": client.host,
        "model": client.model,
        "installed": installed,
    }


def _report_from_model(
    request: InvestigationRequest,
    quantified: dict[str, Any],
    draft: dict[str, Any],
    evidence: list[dict[str, Any]],
    model: str,
) -> InvestigationReport:
    drivers = [
        DriverEstimate(
            driver=row["driver"],
            impact_trx=float(row["impact_trx"]),
            confidence=row.get("confidence", "low"),
            method=row.get("method", "model_interpreted_tool_output"),
            evidence_ids=list(row.get("evidence_ids") or []),
            notes=row.get("notes", ""),
        )
        for row in draft.get("drivers", [])
    ]
    impacts = {d.driver: d.impact_trx for d in drivers}
    recon = run_tool(
        "reconcile_attribution",
        {"variance_trx": quantified["variance_trx"], "driver_impacts": impacts},
    )
    evidence.append(recon)
    checks = [
        CheckItem(
            question=item.get("question", ""),
            why=item.get("why", ""),
            owner=item.get("owner", "Brand analytics"),
        )
        for item in draft.get("what_to_check", [])
    ]
    return _report(
        request,
        quantified,
        draft.get("headline")
        or f"{quantified['brand']} week {quantified['week']} variance {quantified['variance_trx']:,.0f}",
        drivers,
        float(recon["payload"]["residual_trx"]),
        checks,
        list(draft.get("caveats") or []),
        evidence,
        investigator_mode="ollama",
        model=model,
        abstained=bool(draft.get("abstained", False)),
    )


def _report(
    request: InvestigationRequest,
    quantified: dict[str, Any],
    headline: str,
    drivers: list[DriverEstimate],
    residual: float,
    checks: list[CheckItem],
    caveats: list[str],
    evidence: list[dict[str, Any]],
    investigator_mode: str,
    model: str | None,
    abstained: bool,
) -> InvestigationReport:
    return InvestigationReport(
        request_id=request.request_id,
        brand=quantified["brand"],
        week=quantified["week"],
        week_ending=quantified["week_ending"],
        headline=headline,
        forecast_trx=float(quantified["forecast"]),
        actual_trx=float(quantified["actual"]),
        variance_trx=float(quantified["variance_trx"]),
        variance_pct=float(quantified["variance_pct"]),
        drivers=drivers,
        residual_trx=residual,
        what_to_check=checks,
        caveats=caveats,
        evidence=[ToolRecord(**row) for row in evidence],
        investigator_mode=investigator_mode,
        model=model,
        abstained=abstained,
    )
