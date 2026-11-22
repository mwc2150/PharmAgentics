"""The golden case model and loader. One YAML file per persona question."""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import Literal

import yaml
from pydantic import BaseModel

from pharmagentics.tools.queries import TERRITORY_NAMES
from pharmagentics.tools.window import Comparison, parse

from .paths import GOLDEN_DIR

Lane = Literal["briefing", "forecast"]


class Fact(BaseModel):
    """A number or label from the story, with the read-only SQL that recomputes it."""

    id: str
    value: int | float | str
    sql: str
    role: Literal["must", "context"] = "context"  # core-011: must-state facts feed key_fact_recall
    tolerance: float | None = None  # relative, for values the source states roughly; None = stated precision
    reviewed: bool = True  # agent drafts write false until a person reviews them


Driver = Literal["access", "promotion", "supply", "competitor", "data", "holiday", "none"]


class Finding(BaseModel):
    """A conclusion a first-pass analyst should reach on the case (core-011 FR-002), scored on the story cards."""

    id: str
    territory: str  # territory ID or NATIONAL
    direction: Literal["up", "down", "flat"] | None = None
    drivers_supported: list[Driver] = []
    drivers_ruled_out: list[Driver] = []
    withheld: bool = False  # the cut must be withheld, with no story for it
    reviewed: bool = True


class MustSay(BaseModel):
    """Key terms a decision or trust answer must carry (core-011, Q3 of the 2026-11-22 review). Each entry is one
    phrase, or alternatives separated by "|"; matched like must-not-say phrases (words in order, a little slack)."""

    phrases: list[str] = []
    reviewed: bool = True


class Scope(BaseModel):
    """What the agent should decide a question is about (core-011 packet F). A field left None is not checked.
    `territory` is an ID such as SOUTHEAST, or ALL for every territory; `comparison` is the case's comparison dict,
    None meaning the default; `intent` is "brief" or "promotion_review"."""

    territory: str | None = None
    week_start: str | None = None
    week_end: str | None = None
    comparison: dict | None = None
    intent: Literal["brief", "promotion_review"] | None = None


_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_PREFIX = re.compile(r"^(?:Weeks? of|Brief of)\s+\d{4}-\d{2}-\d{2}")
_ANCHOR = "2025-01-06"  # any Monday: parse() only needs one to decide whether a question is a promotion question


def _monday(text: str) -> str:
    d = date.fromisoformat(text)
    return (d - timedelta(days=d.weekday())).isoformat()


def derive_scope(question: str, comparison: dict | None = None) -> Scope:
    """The scope a question's own prefix states: "Week of D[, Territory]:", "Weeks of A to B[, Territory]:",
    "Weeks of A and B:", "Brief of D:". A question with no such prefix states no week and no territory, so those
    stay None (not checked). Intent is "brief" when the prefix names a week, "promotion_review" when it names none
    and the shared parser reads a promotion question (the same rule the stages use), and None otherwise."""
    head = question.split(":", 1)[0] if ":" in question else ""
    dates = _DATE.findall(head) if _PREFIX.match(head) else []
    territory = week_start = week_end = intent = None
    if dates:
        mondays = sorted(_monday(d) for d in dates)
        week_start, week_end = mondays[0], mondays[-1]
        territory = next((tid for tid, label in TERRITORY_NAMES.items()
                          if tid != "NATIONAL" and re.search(rf"\b{re.escape(label)}\b", head, re.I)), "ALL")
        intent = "brief"
    elif parse(question, _ANCHOR, _ANCHOR, briefing=True)["promotion"]:
        intent = "promotion_review"
    return Scope(territory=territory, week_start=week_start, week_end=week_end, comparison=comparison, intent=intent)


class MustNotSay(BaseModel):
    text: str
    phrases: list[str] = []  # checked by code: any appearance fails the case
    semantic: list[str] = []  # quoted but context-dependent ("... without the plan"); judge only


class FollowUp(BaseModel):
    """A second turn on the brief the first question produced (brief-006 FR-013)."""

    question: str
    section: str | None = None  # the section an analyst pinned ("3.1"), if any
    then: str
    must_not_say: MustNotSay | None = None


class Case(BaseModel):
    id: str
    lane: Lane
    story: str
    persona: str
    category: str | None = None  # Evaluation Pack §4 taxonomy (Briefing)
    scenario: str | None = None  # TC-01 to TC-12 (Forecast); Alvin and Sienna assign
    split: Literal["dev", "held_out"] = "dev"
    status: Literal["draft", "frozen"] = "draft"
    question: str
    review_note: str | None = None
    period: str | None = None
    anchor: str | None = None
    story_text: str
    given: str
    when: str
    then: str
    reference_answer: str
    must_not_say: MustNotSay
    must_say: MustSay | None = None
    action: str | None = None
    eval_items: list[str]
    facts: list[Fact] = []
    findings: list[Finding] = []
    follow_up: FollowUp | None = None  # two-turn cases (brief-006 FR-013)
    comparison: Comparison | None = None
    scope: Scope | None = None  # explicit expected scope; absent, expectations() derives it from the question prefix
    source: str

    def inputs(self) -> dict:
        """What the system under test receives: the question, and the follow-up for a two-turn case."""
        return {"question": self.question, "follow_up": self.follow_up.question if self.follow_up else None,
                "section": self.follow_up.section if self.follow_up else None,
                **({"comparison": self.comparison.model_dump(mode="json", exclude_none=True)} if self.comparison else {})}

    def expected_scope(self) -> Scope:
        comparison = self.comparison.model_dump(mode="json", exclude_none=True) if self.comparison else None
        if self.scope is None:
            return derive_scope(self.question, comparison)
        return self.scope if self.scope.comparison is not None or comparison is None else self.scope.model_copy(
            update={"comparison": comparison})

    def expectations(self) -> dict:
        """What the scorers compare against. Only `expected_response` reaches an LLM judge."""
        later = self.follow_up.must_not_say.phrases if self.follow_up and self.follow_up.must_not_say else []
        return {
            "expected_response": self.reference_answer,
            "case_id": self.id,
            "story": self.story,
            "lane": self.lane,
            "must_not_say": self.must_not_say.phrases + later,
            "golden_numbers": [f.value for f in self.facts if isinstance(f.value, (int, float))],
            "key_facts": [{"id": f.id, "value": f.value, "tolerance": f.tolerance} for f in self.facts
                          if f.role == "must" and isinstance(f.value, (int, float))],
            "findings": [f.model_dump() for f in self.findings],
            "must_say": self.must_say.phrases if self.must_say else [],
            "scope": self.expected_scope().model_dump(),
            "eval_items": self.eval_items,
        }


def case_files(lane: str | None = None):
    lanes = [lane] if lane and lane != "all" else ["briefing", "forecast"]
    return sorted(p for name in lanes for p in (GOLDEN_DIR / name).glob("*.yaml"))


def load_cases(lane: str | None = None, stories: list[str] | None = None) -> list[Case]:
    cases = [Case.model_validate(yaml.safe_load(p.read_text(encoding="utf8"))) for p in case_files(lane)]
    if stories:
        wanted = {s.upper() for s in stories}
        cases = [c for c in cases if c.story in wanted or c.id in wanted]
    return sorted(cases, key=lambda c: c.id)


def golden_fingerprint(lane: str | None = None) -> str:
    digest = hashlib.sha256()
    for path in case_files(lane):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
