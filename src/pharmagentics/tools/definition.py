"""The brief definition (brief-010 FR-000a to FR-000e): the choices a brief is built from, stated before it is built.

Six selectors: the period (first and last week), the comparison, which territories a national figure counts, the
measure (TRx and/or NBRx), the grain (which levels get figures, stories and splits) and what a territory story's
change is set against. Every selector except the period takes a list of one or more values; the first is the
primary. The primary drives the stories, the cards and the direction a finding is scored against; each extra value
adds labelled figures beside the primary, never a second set of stories. A single value, a bare string or object
(and the string "both" for the measure) is read as a list. The pre-selected definition (one value each, the house
comparison) reproduces the brief exactly as it was before the definition existed. Metrics always come from the
governed views: the data basis is not a choice.

`words` and `changed_words` say the definition in plain sentences for a reader (no IDs, no digits in the
sentences the memo prints); `labels` is what every claim records about the definition it was made under.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .queries import shift
from .window import Comparison

Grain = Literal["national", "territory", "plan", "channel", "specialty"]
GRAINS: tuple[str, ...] = ("national", "territory", "plan", "channel", "specialty")
TERRITORIES = ("like_for_like", "all_reportable", "projected")
MEASURES = ("trx", "nbrx")
RELATIVE = ("other_territories", "national", "none")

_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen"}


def _iso_monday(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    try:
        day = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD).") from exc
    if day.weekday():
        raise ValueError(f"{field} must be a Monday reporting week.")
    return day.isoformat()


def _as_list(value, *, empty=None):
    """A single value (a string, an object, a model) is a one-item list; None is the empty list or `empty`."""
    if value is None:
        return list(empty) if empty is not None else []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]


class Definition(BaseModel):
    """What a brief is built from. `None` for a week means the question's weeks (else the latest closed week); an empty
    `comparison` means the house comparison (the previous four weeks). The first value of a list is the primary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_week: str | None = None
    last_week: str | None = None
    comparison: list[Comparison] = Field(default_factory=list)
    territories: list[Literal["like_for_like", "all_reportable", "projected"]] = Field(default_factory=lambda: ["like_for_like"])
    measure: list[Literal["trx", "nbrx"]] = Field(default_factory=lambda: ["trx"])
    grain: list[Grain] = Field(default_factory=lambda: list(GRAINS))
    relative_to: list[Literal["other_territories", "national", "none"]] = Field(default_factory=lambda: ["other_territories"])

    @field_validator("first_week", "last_week", mode="before")
    @classmethod
    def _as_text(cls, value):
        return value.isoformat() if isinstance(value, date) else value

    @field_validator("first_week")
    @classmethod
    def _first(cls, value):
        return _iso_monday(value, "first_week")

    @field_validator("last_week")
    @classmethod
    def _last(cls, value):
        return _iso_monday(value, "last_week")

    @field_validator("comparison", mode="before")
    @classmethod
    def _comparison_list(cls, value):
        return _as_list(value)

    @field_validator("measure", mode="before")
    @classmethod
    def _measure_list(cls, value):
        if value == "both":
            return ["trx", "nbrx"]
        return _as_list(value, empty=["trx"])

    @field_validator("territories", mode="before")
    @classmethod
    def _territories_list(cls, value):
        return _as_list(value, empty=["like_for_like"])

    @field_validator("relative_to", mode="before")
    @classmethod
    def _relative_list(cls, value):
        return _as_list(value, empty=["other_territories"])

    @field_validator("grain", mode="before")
    @classmethod
    def _grain_list(cls, value):
        return _as_list(value, empty=GRAINS)

    @field_validator("comparison", "territories", "measure", "grain", "relative_to")
    @classmethod
    def _no_repeats(cls, value, info):
        if len(set(map(repr, value))) != len(value):
            raise ValueError(f"{info.field_name} lists a value twice.")
        if info.field_name != "comparison" and not value:
            raise ValueError(f"Choose at least one value for {info.field_name}.")
        return [g for g in GRAINS if g in value] if info.field_name == "grain" else value

    @model_validator(mode="after")
    def _weeks(self):
        if self.last_week is not None and self.first_week is None:
            raise ValueError("last_week needs a first_week.")
        if self.first_week and self.last_week and self.last_week < self.first_week:
            raise ValueError("The last week comes before the first week.")
        return self

    # -- construction ----------------------------------------------------------------------------------
    @classmethod
    def pre_selected(cls) -> "Definition":
        return cls()

    @classmethod
    def from_comparison(cls, comparison: Comparison | None) -> "Definition":
        """The old `comparison` keyword as a definition: every other field pre-selected."""
        return cls(comparison=[comparison] if comparison is not None else [])

    @classmethod
    def coerce(cls, definition: "Definition | dict | None", comparison: Comparison | None = None) -> "Definition":
        """What an engine receives (a model, its JSON, or nothing) plus the old `comparison` keyword, as one
        definition. A comparison already in the definition wins over the keyword."""
        if definition is None:
            return cls.from_comparison(comparison)
        d = definition if isinstance(definition, Definition) else cls.model_validate(definition)
        return d if d.comparison or comparison is None else d.model_copy(update={"comparison": [comparison]})

    # -- reading: the primary value of each field and the extras beside it ---------------------------------
    def has(self, grain: str) -> bool:
        return grain in self.grain

    @property
    def primary_comparison(self) -> Comparison | None:
        return self.comparison[0] if self.comparison else None

    @property
    def extra_comparisons(self) -> list[Comparison]:
        return self.comparison[1:]

    @property
    def territory_rule(self) -> str:
        return self.territories[0]

    @property
    def primary_measure(self) -> str:
        return self.measure[0]

    @property
    def relative(self) -> str:
        return self.relative_to[0]

    @property
    def is_pre_selected(self) -> bool:
        return (self.territories, self.measure, self.relative_to, self.grain) == (["like_for_like"], ["trx"], ["other_territories"], list(GRAINS))

    def validate_release(self, first: str, latest: str, available: set[str] | None = None) -> None:
        """Raise ValueError when a chosen week is not a reporting week of the release."""
        for name in ("first_week", "last_week"):
            week = getattr(self, name)
            if week is not None and not (first <= week <= latest and (available is None or week in available)):
                raise ValueError(f"The {name.replace('_', ' ')} {week} is outside the release, which runs from {first} to {latest}.")

    def to_json(self) -> dict:
        return self.model_dump(mode="json")


# -- words ---------------------------------------------------------------------------------------------

def _names(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def comparison_words(c: Comparison | None, launch: str | None = None) -> str:
    """The comparison in words. `launch` (the competitor's launch week from the data) lets the pre-launch comparison name its dates."""
    if c is None:
        return "the previous four weeks"
    if c.kind == "pre_launch":
        if launch is None:
            return "the four weeks before Metacora launched"
        first, last = shift(launch, -4), shift(launch, -1)
        return f"the four weeks before Metacora launched ({first} to {last})"
    if c.kind == "last_year":
        return "the same weeks last year"
    if c.kind == "previous":
        n = c.weeks or 4
        return f"the previous {_NUMBER_WORDS.get(n, 'several')} week{'' if n == 1 else 's'}"
    return f"the weeks from {c.start.isoformat()} to {c.end.isoformat()}"


TERRITORY_WORDS = {
    "like_for_like": "Territories counted: like for like, only territories reportable in both periods.",
    "all_reportable": "Territories counted: every territory reportable in each period, counted separately for the period "
                      "and for the comparison.",
    "projected": "Territories counted: the projected national figure, which fills in territories whose feed is incomplete.",
}
TERRITORY_SHORT = {"like_for_like": "like for like", "all_reportable": "every territory reportable in each period",
                   "projected": "the projected national"}
MEASURE_NAMES = {"trx": "total prescriptions (TRx)", "nbrx": "new patients (NBRx)"}
MEASURE_SHORT = {"trx": "TRx", "nbrx": "new patients (NBRx)"}
RELATIVE_NAMES = {"other_territories": "the other territories", "national": "the national change",
                  "none": "nothing, each is stated alone"}
RELATIVE_SHORT = {"other_territories": "the other territories", "national": "national", "none": "nothing"}


def territory_words(d: Definition) -> str:
    extra = f" Also shown: {_names([TERRITORY_SHORT[t] for t in d.territories[1:]])}." if len(d.territories) > 1 else ""
    return TERRITORY_WORDS[d.territories[0]] + extra


def measure_words(measures: list[str]) -> str:
    more = f" beside {_names([MEASURE_NAMES[m] for m in measures[1:]])}" if len(measures) > 1 else ""
    return f"Measure: {MEASURE_NAMES[measures[0]]}{more}."


def relative_words(values: list[str]) -> str:
    return "Territory changes are set against: " + _names([RELATIVE_NAMES[v] for v in values]) + "."


def grain_words(d: Definition) -> str:
    return "Levels shown: " + _names(list(d.grain)) + "."


def words(d: Definition, launch: str | None = None) -> list[str]:
    """The whole definition in plain sentences, one per selector, for a reader of either view. A list is said with its
    primary first and the extra values beside it."""
    out = []
    if d.first_week:
        last = d.last_week or d.first_week
        out.append(f"Period: the week of {d.first_week}." if last == d.first_week else f"Period: the weeks {d.first_week} to {last}.")
    names = [comparison_words(c, launch) for c in d.comparison] or [comparison_words(None)]
    out.append(f"Comparison: {names[0]}." + (f" Also shown against {_names(names[1:])}." if len(names) > 1 else ""))
    out.append("Holiday weeks are left out.")
    out += [territory_words(d), measure_words(d.measure), grain_words(d), relative_words(d.relative_to)]
    return out


def prompt_words(d: Definition) -> str:
    """What the Manager and the Writer are told about how the brief counts: the territories, measure, levels and what a
    change is set against, one line each. No period and no comparison length, so no number word reaches the writer."""
    lines = [territory_words(d), measure_words(d.measure), grain_words(d), relative_words(d.relative_to)]
    if d.extra_comparisons:
        lines.append("Figures are also shown against the other comparisons the analyst chose; the stories follow the first.")
    return "\n".join("- " + x for x in lines)


def changed_words(d: Definition) -> list[str]:
    """Only the selectors that differ from the pre-selected values, in words."""
    base = Definition.pre_selected()
    out = []
    if d.territories != base.territories:
        out.append(territory_words(d))
    if d.measure != base.measure:
        out.append(measure_words(d.measure))
        if "projected" in d.territories and d.measure[0] == "nbrx":
            out.append("The projected national is a TRx figure, so new patients (NBRx) are counted like for like.")
    if d.grain != base.grain:
        out.append(grain_words(d))
    if d.relative_to != base.relative_to:
        out.append(relative_words(d.relative_to))
    return out


def assumption_sentence(d: Definition) -> str | None:
    """One short sentence for the memo's Assumptions block when the definition is not the pre-selected one (the form
    prints the whole definition in words itself); None when it is."""
    base = Definition.pre_selected()
    parts = []
    if d.territories != base.territories:
        parts.append("territories counted " + _names([TERRITORY_SHORT[t] for t in d.territories]))
    if d.measure != base.measure:
        parts.append("measure " + _names([MEASURE_SHORT[m] for m in d.measure]))
    if d.grain != base.grain:
        parts.append("levels " + _names(list(d.grain)))
    if d.relative_to != base.relative_to:
        parts.append("territory changes set against " + _names([RELATIVE_SHORT[v] for v in d.relative_to]))
    if d.extra_comparisons:
        parts.append("also compared with " + _names([comparison_words(c) for c in d.extra_comparisons]))
    return ("Brief definition, changed from the pre-selected values: " + "; ".join(parts) + ".") if parts else None


def labels(d: Definition, period: list[str], baseline: list[str]) -> dict:
    """What every claim records about the definition it was made under: the value of each field it used (the primary
    unless the claim belongs to an extra value, which overrides it). The claim adds its own grain and cut."""
    c = d.primary_comparison
    return {"territories": d.territories[0], "measure": d.measure[0], "relative_to": d.relative_to[0],
            "period": f"{period[0]} to {period[-1]}" if period else None,
            "comparison": f"{baseline[0]} to {baseline[-1]}" if baseline else None,
            "comparison_kind": c.kind if c is not None else "default"}
