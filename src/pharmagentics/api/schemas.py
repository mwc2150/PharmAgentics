"""Strict, independent API contracts. Runtime packages must not import eval/."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pharmagentics.tools.definition import Definition
from pharmagentics.tools.window import Comparison


Territory = Literal[
    "GREAT_LAKES", "MID_ATLANTIC", "MOUNTAIN", "NEW_ENGLAND",
    "NORTHWEST", "PACIFIC", "SOUTHEAST", "SOUTH_CENTRAL", "NATIONAL",
]
Brand = Literal["BXA", "BXC"]


class BrandCapability(BaseModel):
    id: Brand
    name: str
    engines: list[Literal["scripted", "agent"]]


class TriageDecision(BaseModel):
    """P1's decision on a triage plan (brief-002 FR-023): the stories to investigate, in order."""
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(pattern=r"^t-[0-9a-f]{12}$")
    stories: list[str] = Field(default_factory=list, max_length=10)


class BriefingQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["weekly_brief", "promotion_review"] = "weekly_brief"
    brand_id: Brand = "BXA"
    territory_id: Territory = "PACIFIC"
    week_start: date
    week_end: date | None = None  # brief-008: the last week of a multi-week period; absent or equal = one week
    question: str = Field(default="What changed this week?", min_length=3, max_length=300)
    comparison: Comparison | None = None
    definition: Definition | None = None  # brief-010: what the brief is built from; absent = the pre-selected values
    triage: TriageDecision | None = None  # brief-002: absent = the code plan, unchanged behavior

    @field_validator("week_start", "week_end")
    @classmethod
    def reporting_week_must_start_on_monday(cls, value: date | None) -> date | None:
        if value is not None and value.weekday() != 0:
            raise ValueError("Reporting weeks must start on a Monday")
        return value

    @model_validator(mode="after")
    def last_week_not_before_first(self):
        if self.week_end is not None and self.week_end < self.week_start:
            raise ValueError("The last week comes before the first week")
        d = self.definition
        if d is not None and self.intent == "weekly_brief":
            if d.first_week and d.first_week != self.week_start.isoformat():
                raise ValueError("The definition's first week differs from the brief's week_start")
            if d.last_week and d.last_week != (self.week_end or self.week_start).isoformat():
                raise ValueError("The definition's last week differs from the brief's week_end")
            # the top-level `comparison` carries the primary alone; when both are given the definition wins
        return self


class BriefingScopeRequest(BaseModel):
    """brief-008: the typed question whose scope the analyst wants read before building (analysts only)."""
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=300)
    brand_id: Brand = "BXA"


class BriefingScope(BaseModel):
    """A proposed scope for the form. Nothing runs on it until the analyst confirms. `read_by` says who read it."""
    question: str
    week_start: date
    week_end: date
    territory_id: Territory | None = None  # None: the question names no territory, so the form keeps its choice
    comparison_weeks: int | None = Field(default=None, ge=1, le=13)  # None: no earlier week fits, so the default comparison applies
    promotion_review: bool = False
    definition: Definition | None = None  # brief-010: the proposed brief definition (period and comparison filled; the analyst confirms)
    notes: list[str] = Field(default_factory=list)
    read_by: Literal["model", "rules"]
    model: str | None = None  # the model that read it, when read_by is "model"


class Claim(BaseModel):
    value: str
    evidence_id: str
    labels: dict[str, Any] | None = None  # brief-010: the definition fields, grain and cut the claim was made under


class Evidence(BaseModel):
    id: str
    tool: str
    params: dict[str, Any] = Field(default_factory=dict)
    query: str | None = None
    result: Any = None
    data_version: str | None = None


class BriefingResult(BaseModel):
    """What the engine returns. The API adds brief_id, view and the review state (views.analyst)."""
    status: Literal["draft_requires_review"] = "draft_requires_review"
    review_status: Literal["not_submitted"] = "not_submitted"
    engine: Literal["scripted", "agent"] = "scripted"  # agent: posted by the owner's local worker (core-007 FR-028)
    system: str
    question: str
    brand_id: Brand = "BXA"
    territory_id: Territory
    week_start: date
    week_end: date | None = None  # brief-008: set only for a multi-week period
    comparison: Comparison | None = None
    definition: Definition | None = None  # brief-010: the effective definition (weeks and comparison filled in)
    definition_words: list[str] | None = None  # the same definition in plain sentences (both views)
    answer: str
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    data_version: str | None = None
    abstained: bool = False
    # brief-002 Phase A, analyst view only (never in the leadership allow-list):
    triage: dict[str, Any] | None = None  # TriageRecord: who made each triage call
    flow: list[dict[str, Any]] | None = None  # StageFlow: the seven stages, states and actors
    citations: list[dict[str, int]] | None = None  # where each claim value sits in `answer`: {start, end, claim}
    # brief-003: the memo's sections with charts and the data behind them; leaders get views.leadership_sections
    sections: list[dict[str, Any]] | None = None
    # brief-009, analyst view only: the run's event log (pharmagentics.tools.events) and, for each claim, the seq of the
    # event that produced it. Leaders get views.process_summary instead.
    events: list[dict[str, Any]] | None = None
    claim_events: list[int | None] | None = None


class ReleaseContext(BaseModel):
    first_week: date
    latest_week: date
    brand_id: Brand | None = "BXA"
    territory_ids: list[str]
    available_weeks: list[date] = Field(default_factory=list)
    product_ids: list[Brand] = Field(default_factory=lambda: ["BXA"])
    brands: list[BrandCapability] = Field(default_factory=lambda: [
        BrandCapability(id="BXA", name="Cardiovela", engines=["scripted", "agent"])])
    supported_intents: list[Literal["weekly_brief"]] = Field(default_factory=lambda: ["weekly_brief"])
    engine: Literal["scripted"] = "scripted"
    data_version: str | None = None  # the loaded release's pinned version (shown under Settings > About)


class ViewAs(BaseModel):
    """The test login's choice: the analyst roles (P1, CA), the Insights Manager (P2), the leadership roles (P3, BM) or the Marketer (P4)."""
    model_config = ConfigDict(extra="forbid")

    view: Literal["analyst", "insights", "leadership", "marketer"]


class ReviewRequest(BaseModel):
    """The analyst's decision on one brief (core-007 FR-010; brief-005): send it for sign-off, or reject it. A rejection needs a reason."""
    model_config = ConfigDict(extra="forbid")

    decision: Literal["sent", "rejected"]
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class ClaimFlag(BaseModel):
    """One claim the Insights Manager marks as wrong: its index in the brief's claims, and an optional note."""
    model_config = ConfigDict(extra="forbid")

    claim: int = Field(ge=0)
    note: str | None = Field(default=None, max_length=300)

    @field_validator("note")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class SignoffRequest(BaseModel):
    """The Insights Manager's decision on a brief sent for sign-off (brief-005). Returning needs a comment; flags are optional."""
    model_config = ConfigDict(extra="forbid")

    decision: Literal["signed_off", "returned"]
    comment: str | None = Field(default=None, max_length=1000)
    flags: list[ClaimFlag] = Field(default_factory=list, max_length=50)

    @field_validator("comment")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class InsightMark(BaseModel):
    """The participant marks that they have what they need (time to insight, FR-025)."""
    model_config = ConfigDict(extra="forbid")

    brief_id: str = Field(min_length=3, max_length=40)
    view: Literal["analyst", "leadership"]


class AgentJobRequest(BaseModel):
    """An agent job for the owner's local worker (core-007 FR-028; brief-002 Phase B)."""
    model_config = ConfigDict(extra="forbid")

    kind: Literal["triage", "brief"]
    query: BriefingQuery
    triage_job: str | None = Field(default=None, pattern=r"^j-[0-9a-f]{12}$")  # brief: the reviewed plan's job
    decision: TriageDecision | None = None  # brief: P1's decision on that plan


class WorkerPoll(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, max_length=120)
    worker: str = Field(default="worker", min_length=1, max_length=60, pattern=r"^[\w.@-]+$")  # which teammate's machine


class WorkerProgress(BaseModel):
    """New run events of a running job (brief-009). Cleaned against the event schema before they are stored."""
    model_config = ConfigDict(extra="forbid")

    events: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = Field(default=None, max_length=2000)


class ForecastRunRequest(BaseModel):
    """One Forecast explanation request. The engine and model are fixed by the server, never by the caller."""
    model_config = ConfigDict(extra="forbid")

    territory_id: Territory = "NATIONAL"
    week_start: date
    window_weeks: int = Field(default=1, ge=1, le=52)
    view: Literal["analyst", "leadership"] | None = None


class ForecastAsk(BaseModel):
    """A question for the Forecast agent (fcst-001). The scope card's edits may override the parsed territory and
    weeks. The engine and model are fixed by the server, never by the caller."""
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=400)
    territory_id: Territory | None = None
    week_from: date | None = None
    week_to: date | None = None
    intent: Literal["reliability", "screen", "where", "drivers", "attribution", "unknowns", "next_checks",
                    "assumptions", "audit", "communicate"] | None = None
    view: Literal["analyst", "leadership"] | None = None

    @field_validator("question")
    @classmethod
    def tidy(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("Ask a question of at least three characters.")
        return value


class ForecastFollowup(BaseModel):
    """A follow-up question on one finished Forecast question run."""
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=300)


class ForecastReview(BaseModel):
    """The Brand Manager's decision on a submitted Forecast run. Rejecting or returning needs a note."""
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected", "returned"]
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None
