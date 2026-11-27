"""The golden case model and loader. One YAML file per persona question."""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pharmagentics.tools.queries import TERRITORY_NAMES
from pharmagentics.tools.window import parse

from .numbers import as_numbers, extract, same
from .paths import GOLDEN_DIR
from .truth import exact_value

Lane = Literal["briefing", "forecast"]
Brand = Literal["BXA", "BXC"]  # the brand a case is about: Cardiovela or Lipidara (core-010); a case with no `brand:` is BXA
DEFAULT_BRAND: Brand = "BXA"
# core-011 FR-018: the capability a system must have to state a fact or reach a finding.
Needs = Literal["plan_cut", "segment_pct", "restatement", "national_card"]
CUT_KINDS = ("plan", "channel", "segment")  # core-011 FR-017: a cut below the territory, "<kind>:<name>"


class Fact(BaseModel):
    """A number or label from the story, with the read-only SQL that recomputes it."""

    id: str
    value: int | float | str
    sql: str
    role: Literal["must", "context"] = "context"  # core-011: must-state facts feed key_fact_recall
    tolerance: float | None = None  # relative, for values the source states roughly; None = stated precision
    reviewed: bool = True  # agent drafts write false until a person reviews them
    needs: Needs | None = None  # core-011 FR-018: a capability a system may lack; None = any system can state it


Driver = Literal["access", "promotion", "supply", "competitor", "data", "holiday", "none"]
# brief-010 FR-000d: what a finding is about; None means BXA TRx. `restated_figure` is a fact about the data record
# (a restatement), not the business (brief-010 FR-010).
Measure = Literal["trx", "nbrx", "bxa_share", "competitor_share", "restated_figure"]
GRAINS = ("national", "territory", "plan", "channel", "specialty")
PRE_LAUNCH = ("2026-02-02", "2026-02-23")  # the four weeks before Metacora launched (2026-03-02)


class Comparison(BaseModel):
    """The comparison choice, as `pharmagentics.tools.window.Comparison` plus the eval-only kind `pre_launch` (the four
    weeks before Metacora launched, 2026-02-02 to 2026-02-23; takes no extra fields)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["previous", "last_year", "custom", "pre_launch"]
    weeks: int | None = Field(default=None, strict=True, ge=1, le=13)
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if self.kind == "custom":
            if self.weeks is not None or self.start is None or self.end is None:
                raise ValueError("Custom comparison needs a start and end week.")
            if self.start.weekday() or self.end.weekday() or self.start > self.end:
                raise ValueError("Custom comparison needs ordered Monday reporting weeks.")
        elif self.kind == "previous":
            if self.weeks is None or self.start is not None or self.end is not None:
                raise ValueError("Previous comparison needs a week count.")
        elif self.weeks is not None or self.start is not None or self.end is not None:
            raise ValueError(f"A {self.kind} comparison takes no extra fields.")
        return self

    def for_engine(self) -> "Comparison":
        """The comparison the shared window parser knows: `pre_launch` is the custom window it names."""
        if self.kind != "pre_launch":
            return self
        return Comparison(kind="custom", start=date.fromisoformat(PRE_LAUNCH[0]), end=date.fromisoformat(PRE_LAUNCH[1]))


DEFAULT_COMPARISON = Comparison(kind="previous", weeks=4)  # the house comparison: the four weeks before the period


class Definition(BaseModel):
    """The brief definition a case is written under (brief-010 FR-000a and FR-000e, plan.md "The brief definition"). The
    eval-side twin of `pharmagentics.tools.definition.Definition`, with the same JSON names; the eval package never
    imports from `src/` for its own models. A week left None means the question's weeks, else the latest closed week.
    Every field but the period is a list: the first value is the primary (golden facts and finding directions follow it),
    a bare value or object is read as a one-item list, `measure: both` as [trx, nbrx], and a comparison of None or []
    means the previous four weeks."""

    model_config = ConfigDict(extra="forbid")

    first_week: str | None = None
    last_week: str | None = None
    comparison: list[Comparison] = []
    territories: list[Literal["like_for_like", "all_reportable", "projected"]] = ["like_for_like"]
    measure: list[Literal["trx", "nbrx"]] = ["trx"]
    grain: list[Literal["national", "territory", "plan", "channel", "specialty"]] = list(GRAINS)
    relative_to: list[Literal["other_territories", "national", "none"]] = ["other_territories"]

    @model_validator(mode="before")
    @classmethod
    def _lists(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for key in ("comparison", "territories", "measure", "grain", "relative_to"):
            if key not in data:
                continue
            value = data[key]
            if value is None:
                value = []
            elif not isinstance(value, (list, tuple)):
                value = [value]
            if key == "measure":
                value = [m for v in value for m in (["trx", "nbrx"] if v == "both" else [v])]
            seen: list = []
            for v in value:  # a repeated value adds nothing
                if v not in seen:
                    seen.append(v)
            if seen or key == "comparison":
                data[key] = seen
            else:
                raise ValueError(f"{key} needs at least one value")
        return data

    @property
    def primary_comparison(self) -> Comparison | None:
        return self.comparison[0] if self.comparison else None

    @property
    def explicit_comparison(self) -> Comparison | None:
        """The primary comparison when it is a choice: None for none or the house default (previous four weeks),
        which the engines read as "no choice made" (a release-wide Promotion review refuses an explicit one)."""
        c = self.primary_comparison
        return None if c is None or c == DEFAULT_COMPARISON else c

    def payload(self, *, engine: bool = False) -> dict:
        """The JSON with every field (lists), comparisons without their Nones. `engine=True` is what a system
        receives: a comparison list that is only the house default goes as [], which means the same thing."""
        out = self.model_dump(mode="json")
        choices = [] if engine and self.comparison == [DEFAULT_COMPARISON] else self.comparison
        out["comparison"] = [c.model_dump(mode="json", exclude_none=True) for c in choices]
        return out


class Finding(BaseModel):
    """A conclusion a first-pass analyst should reach on the case (core-011 FR-002), scored on the story cards."""

    id: str
    territory: str  # territory ID or NATIONAL
    direction: Literal["up", "down", "flat"] | None = None
    drivers_supported: list[Driver] = []
    drivers_ruled_out: list[Driver] = []
    withheld: bool = False  # the cut must be withheld, with no story for it
    reviewed: bool = True
    cut: str | None = None  # core-011 FR-017: "plan:<id>", "channel:<name>" or "segment:<name>"; None = the whole territory
    needs: Needs | None = None  # core-011 FR-018
    measure: Measure | None = None  # brief-010 FR-000d: None = BXA TRx

    @field_validator("cut")
    @classmethod
    def _cut_form(cls, value: str | None) -> str | None:
        if value is None:
            return value
        kind, _, name = value.partition(":")
        if kind not in CUT_KINDS or not name.strip():
            raise ValueError(f"cut must be one of {', '.join(k + ':<name>' for k in CUT_KINDS)}, not {value!r}")
        return value


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



def fact_percent(fact_id: str, value: float, reference: str) -> bool | None:
    """A fact's unit, so "42 TRx" never states a 42% fact (core-011 Q10). The reference answer decides when it
    states the value at the fact's own precision in one unit; otherwise an id ending in `_pct` is a percent and
    anything else is unknown (matches either)."""
    target = as_numbers([value])[0]
    kinds = {n.percent for n in extract(reference) if n.decimals == target.decimals and same(n, target)}
    if len(kinds) == 1:
        return kinds.pop()
    return True if fact_id.endswith("_pct") else None


class Case(BaseModel):
    id: str
    lane: Lane
    brand: Brand = DEFAULT_BRAND  # which brand's data the case is about; the systems receive it as `brand_id`
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
    definition: Definition | None = None  # brief-010 FR-000d; an old top-level `comparison:` is read into it
    intent: Literal["brief", "promotion_review"] = "brief"  # the app's request intent; "promotion_review" sends the
    # Promotion review question form (systems.briefing_question), so a question with no campaign word still gets one
    scope: Scope | None = None  # explicit expected scope; absent, expectations() derives it from the question prefix
    source: str

    @model_validator(mode="before")
    @classmethod
    def _old_comparison(cls, data):
        """Files written before brief-010 carry a top-level `comparison:`; it becomes `definition.comparison`."""
        if isinstance(data, dict) and "comparison" in data:
            data = dict(data)
            comparison = data.pop("comparison")
            definition = dict(data.get("definition") or {})
            if comparison is not None and not definition.get("comparison"):
                definition["comparison"] = comparison
            if definition:
                data["definition"] = definition
        return data

    @property
    def comparison(self) -> Comparison | None:
        """The comparison the case makes a choice of (None: the house default), as the old `comparison:` field was."""
        return self.definition.explicit_comparison if self.definition else None

    def inputs(self) -> dict:
        """What the system under test receives: the question, and the follow-up for a two-turn case."""
        return {"question": self.question, "follow_up": self.follow_up.question if self.follow_up else None,
                "section": self.follow_up.section if self.follow_up else None, "intent": self.intent,
                **({"brand": self.brand} if self.brand != DEFAULT_BRAND else {}),  # BXA rows stay as they always were
                **({"comparison": self.comparison.for_engine().model_dump(mode="json", exclude_none=True)} if self.comparison else {}),
                **({"definition": self.definition.payload(engine=True)} if self.definition else {})}

    def expected_scope(self) -> Scope:
        comparison = self.comparison.model_dump(mode="json", exclude_none=True) if self.comparison else None
        if self.scope is None:
            derived = derive_scope(self.question, comparison)
            return derived.model_copy(update={"intent": "promotion_review"}) if self.intent == "promotion_review" else derived
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
            "key_facts": [{"id": f.id, "value": f.value, "exact": exact_value(f.sql), "tolerance": f.tolerance,
                           "percent": fact_percent(f.id, f.value, self.reference_answer), "reviewed": f.reviewed,
                           "needs": f.needs} for f in self.facts
                          if f.role == "must" and isinstance(f.value, (int, float))],
            # core-011 FR-016: the exact value behind each numeric fact, so a number is scored against the data,
            # not against a figure the golden file already rounded.
            "fact_exact": [{"value": f.value, "exact": exact_value(f.sql)} for f in self.facts
                           if isinstance(f.value, (int, float)) and not isinstance(f.value, bool)],
            "findings": [f.model_dump() for f in self.findings],
            "must_say": self.must_say.phrases if self.must_say else [],
            "scope": self.expected_scope().model_dump(),
            "definition": self.definition.payload() if self.definition else None,
            "eval_items": self.eval_items,
        }


def case_files(lane: str | None = None):
    lanes = [lane] if lane and lane != "all" else ["briefing", "forecast"]
    return sorted(p for name in lanes for p in (GOLDEN_DIR / name).glob("*.yaml"))


def _brand_of(path) -> str:
    """The `brand:` a case file states (a top-level line), BXA when it has none. Read as text so a fingerprint never parses YAML."""
    match = re.search(r"^brand:\s*(\w+)\s*$", path.read_text(encoding="utf8"), flags=re.M)
    return match.group(1) if match else DEFAULT_BRAND


def _brand_files(lane: str | None, brand: str | None):
    return [p for p in case_files(lane) if brand in (None, "all") or _brand_of(p) == brand]


def load_cases(lane: str | None = None, stories: list[str] | None = None, brand: str | None = DEFAULT_BRAND) -> list[Case]:
    """The golden cases of one lane (default all) and one brand. `brand` defaults to BXA, so every caller written before
    Lipidara reads exactly the cases it always did; pass "BXC" for Lipidara or "all" (or None) for every brand."""
    cases = [Case.model_validate(yaml.safe_load(p.read_text(encoding="utf8"))) for p in _brand_files(lane, brand)]
    if stories:
        wanted = {s.upper() for s in stories}
        cases = [c for c in cases if c.story in wanted or c.id in wanted]
    return sorted(cases, key=lambda c: c.id)


def golden_fingerprint(lane: str | None = None, brand: str | None = DEFAULT_BRAND) -> str:
    """Hash of the case files of one brand (default BXA), so adding Lipidara cases never changes a Cardiovela run's version."""
    digest = hashlib.sha256()
    for path in _brand_files(lane, brand):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]
