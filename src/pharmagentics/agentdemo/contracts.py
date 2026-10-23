"""Typed handoff objects for the brief-006 prototype (prototype forms of core-004)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

QType = Literal["what_changed", "why", "data_health", "metric", "competitor"]
Verdict = Literal["supported", "ruled_out", "insufficient", "context"]
Confidence = Literal["High", "Medium", "Low", "n/a"]


class QuestionIntent(BaseModel):
    question: str
    qtype: QType
    week: date
    window_weeks: int = 4
    territory: str | None = None
    product: str = "BXA"
    metric: Literal["trx", "nrx", "nbrx", "share"] = "trx"
    notes: list[str] = Field(default_factory=list)
    parsed_by: str = "rules"
    valid: bool = True
    error: str | None = None


class EvidenceItem(BaseModel):
    evidence_id: str
    run_id: str
    tool: str
    params: dict[str, Any]
    sql: str
    result: Any
    data_version: str
    span_id: str


class Claim(BaseModel):
    token: str
    label: str
    value: Any
    fmt: str
    display: str
    evidence_id: str


class Candidate(BaseModel):
    candidate_id: str
    kind: Literal["national", "territory_single", "territory_sustained", "competitor"]
    territory: str | None = None
    product: str = "BXA"
    week: date
    window_start: date
    actual: float
    baseline: float
    change_abs: float
    change_rel: float
    peer_rel: float | None = None
    gap: float | None = None
    direction: Literal["down", "up"]
    impact: float
    rule: str
    evidence_id: str
    extra: dict[str, Any] = Field(default_factory=dict)


class CheckResult(BaseModel):
    check_id: str
    specialist: str
    params: dict[str, Any]
    verdict: Verdict
    summary: str                     # code-written text; figures appear only as {{c#}} tokens
    evidence_ids: list[str]
    data: dict[str, Any] = Field(default_factory=dict)


class Story(BaseModel):
    story_id: str
    kind: Literal["territory", "national", "competitor"]
    title: str
    territory: str | None = None
    product: str = "BXA"
    candidate_ids: list[str] = Field(default_factory=list)
    week: date
    window_start: date
    direction: Literal["down", "up"] = "down"
    material: bool = True
    headline: str = ""               # tokenised one-liner describing the move
    checks: list[CheckResult] = Field(default_factory=list)
    label: str = "open"
    confidence: Confidence = "n/a"
    leading_driver: str | None = None
    closure_reason: str = ""
    investigate_next: list[str] = Field(default_factory=list)
    involve: list[str] = Field(default_factory=list)
    rounds: int = 0
    refused: list[str] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    role: Literal["P1", "P2"]
    decision: Literal["approve", "return"]
    comment: str = ""
    at: str


class Answer(BaseModel):
    run_id: str
    question: str
    intent: QuestionIntent
    mode: str
    llm: str
    state: str
    states: list[dict[str, Any]]
    pins: dict[str, Any]
    narrative: str
    narrative_source: str
    rendered: str
    claims: dict[str, Claim]
    stories: list[Story]
    data_health: dict[str, Any]
    kpis: list[str]
    verification: dict[str, Any]
    evidence: dict[str, EvidenceItem]
    reviews: list[ReviewDecision] = Field(default_factory=list)
    elapsed_ms: int = 0
    notices: list[str] = Field(default_factory=list)
