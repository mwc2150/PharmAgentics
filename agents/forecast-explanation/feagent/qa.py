from __future__ import annotations

from dataclasses import dataclass, field

from feagent.investigator import run_investigation
from feagent.llm import LLMClient
from feagent.schema import InvestigationReport, InvestigationRequest, ToolRecord

DEMO_QUESTIONS = [
    "Why did LUMINA miss in week 18?",
    "How much of the miss is payer vs competitor?",
    "What should we check next, and what is still unexplained?",
]

DRIVER_LABELS = {
    "payer_access": "payer access",
    "competitor_activity": "competitor activity",
}


@dataclass
class ChatAnswer:
    question: str
    intent: str
    markdown: str
    report: InvestigationReport
    evidence: list[ToolRecord] = field(default_factory=list)


def classify_intent(question: str) -> str:
    q = question.lower()
    if any(token in q for token in ("check", "next", "unexplained", "residual", "still")):
        return "next_checks"
    if any(token in q for token in ("payer", "competitor", "how much", "split", "versus", " vs ")):
        return "split"
    return "why_miss"


def answer_question(
    question: str,
    request: InvestigationRequest,
    mode: str = "stub",
    case_id: str = "week18",
    client: LLMClient | None = None,
    report: InvestigationReport | None = None,
) -> ChatAnswer:
    intent = classify_intent(question)
    if report is None:
        report = run_investigation(request, mode=mode, case_id=case_id, client=client)
    markdown = _format(intent, report)
    return ChatAnswer(
        question=question,
        intent=intent,
        markdown=markdown,
        report=report,
        evidence=report.evidence,
    )


def _format(intent: str, report: InvestigationReport) -> str:
    if intent == "split":
        return _format_split(report)
    if intent == "next_checks":
        return _format_checks(report)
    return _format_why(report)


def _event_labels(report: InvestigationReport) -> list[str]:
    label_by_tool = {rec.tool_id: rec.payload.get("label") for rec in report.evidence}
    labels = []
    for driver in report.drivers:
        label = next((label_by_tool.get(e) for e in driver.evidence_ids if label_by_tool.get(e)), None)
        if label:
            labels.append(label)
    return labels


def _format_why(report: InvestigationReport) -> str:
    drivers = _driver_lines(report)
    labels = _event_labels(report)
    events = (
        "Events that sit next to the miss: " + "; ".join(labels) + ".\n\n" if labels else ""
    )
    return (
        f"**{report.headline}**\n\n"
        f"Forecast was **{report.forecast_trx:,.0f} TRx**; actual was **{report.actual_trx:,.0f} TRx** "
        f"in week {report.week} ending {report.week_ending}.\n\n"
        f"{events}"
        f"{drivers}\n\n"
        f"**Unexplained residual: {report.residual_trx:,.0f} TRx.** "
        "Numbers come from deterministic tools (exposed vs named controls). "
        "Overlapping shocks are handled by excluding contaminated regions, not a joint model."
    )


def _format_split(report: InvestigationReport) -> str:
    payer = next((d for d in report.drivers if d.driver == "payer_access"), None)
    competitor = next((d for d in report.drivers if d.driver == "competitor_activity"), None)
    explained = sum(d.impact_trx for d in report.drivers)
    share = abs(explained / report.variance_trx) if report.variance_trx else 0
    payer_txt = (
        f"- **Payer access: {payer.impact_trx:,.0f} TRx** ({payer.confidence} confidence, {payer.method.replace('_', ' ')})"
        if payer
        else "- Payer access: not estimated"
    )
    competitor_txt = (
        f"- **Competitor activity: {competitor.impact_trx:,.0f} TRx** ({competitor.confidence} confidence, {competitor.method.replace('_', ' ')})"
        if competitor
        else "- Competitor activity: not estimated"
    )
    return (
        f"Of the **{report.variance_trx:,.0f} TRx** miss in week {report.week}:\n\n"
        f"{payer_txt}\n"
        f"{competitor_txt}\n"
        f"- **Unexplained residual: {report.residual_trx:,.0f} TRx**\n\n"
        f"Together the two drivers explain **{explained:,.0f} TRx** "
        f"({share:.0%} of the miss). The remainder should not be forced onto either driver."
    )


def _format_checks(report: InvestigationReport) -> str:
    items = "\n".join(
        f"- **{item.question}**  \n  {item.why} · _{item.owner}_"
        for item in report.what_to_check
    )
    caveats = "\n".join(f"- {c}" for c in report.caveats)
    return (
        f"**{report.residual_trx:,.0f} TRx** is still unexplained after payer and competitor estimates.\n\n"
        "What to check next:\n\n"
        f"{items}\n\n"
        f"Caveats:\n{caveats}"
    )


def _driver_lines(report: InvestigationReport) -> str:
    lines = []
    for driver in report.drivers:
        label = DRIVER_LABELS.get(driver.driver, driver.driver)
        lines.append(
            f"- **{label.title()}: {driver.impact_trx:,.0f} TRx** "
            f"({driver.confidence} confidence)"
        )
    return "\n".join(lines)
