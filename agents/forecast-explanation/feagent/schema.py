from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


InvestigatorMode = Literal["stub", "ollama", "auto"]
Confidence = Literal["high", "medium", "low", "inconclusive"]
RequestSource = Literal["manual", "briefing_agent"]


def to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)


@dataclass
class InvestigationRequest:
    """Handoff contract from the Briefing Agent, Figma Make, or a manual trigger."""

    request_id: str
    source: RequestSource
    brand: str
    week: int
    week_ending: str
    metric: str = "TRx"
    notes: str | None = None
    forecast: float | None = None
    actual: float | None = None
    week_start: str | None = None
    territory_id: str = "NATIONAL"
    product_id: str = "BXA"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvestigationRequest":
        week = payload.get("week")
        week_start = payload.get("week_start")
        week_ending = payload.get("week_ending")
        if week is None and not week_start:
            raise ValueError("InvestigationRequest needs week or week_start")
        return cls(
            request_id=str(payload["request_id"]),
            source=payload.get("source", "manual"),
            brand=str(payload.get("brand") or "BXA Cardiovela"),
            week=int(week) if week is not None else 0,
            week_ending=str(week_ending or week_start or ""),
            metric=payload.get("metric", "TRx"),
            notes=payload.get("notes"),
            forecast=_opt_float(payload.get("forecast")),
            actual=_opt_float(payload.get("actual")),
            week_start=str(week_start) if week_start else None,
            territory_id=str(payload.get("territory_id") or "NATIONAL"),
            product_id=str(payload.get("product_id") or "BXA"),
        )


@dataclass
class DriverEstimate:
    driver: str
    impact_trx: float
    confidence: Confidence
    method: str
    evidence_ids: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CheckItem:
    question: str
    why: str
    owner: str


@dataclass
class ToolRecord:
    tool_id: str
    name: str
    arguments: dict[str, Any]
    payload: dict[str, Any]


@dataclass
class InvestigationReport:
    request_id: str
    brand: str
    week: int
    week_ending: str
    headline: str
    forecast_trx: float
    actual_trx: float
    variance_trx: float
    variance_pct: float
    drivers: list[DriverEstimate]
    residual_trx: float
    what_to_check: list[CheckItem]
    caveats: list[str]
    evidence: list[ToolRecord]
    investigator_mode: str
    model: str | None = None
    abstained: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _opt_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
