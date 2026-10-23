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
    """Handoff contract from the Briefing Agent or a manual trigger."""

    request_id: str
    source: RequestSource
    brand: str
    week: int
    week_ending: str
    metric: str = "TRx"
    notes: str | None = None
    forecast: float | None = None
    actual: float | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvestigationRequest":
        return cls(
            request_id=str(payload["request_id"]),
            source=payload.get("source", "manual"),
            brand=payload["brand"],
            week=int(payload["week"]),
            week_ending=str(payload["week_ending"]),
            metric=payload.get("metric", "TRx"),
            notes=payload.get("notes"),
            forecast=_opt_float(payload.get("forecast")),
            actual=_opt_float(payload.get("actual")),
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
