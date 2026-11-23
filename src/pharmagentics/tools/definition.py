"""The brief definition (brief-010 FR-000a to FR-000c): the choices a brief is built from, stated before it is built.

Six selectors: the period (first and last week), the comparison, which territories a national figure counts, the
measure (TRx, NBRx or both), the grain (which levels get figures, stories and splits) and what a territory story's
change is set against. Each has a pre-selected value; the pre-selected definition reproduces the brief exactly as
it was before the definition existed. Metrics always come from the governed views: the data basis is not a choice.

`words` and `changed_words` say the definition in plain sentences for a reader (no IDs, no digits in the
sentences the memo prints); `labels` is what every claim records about the definition it was made under.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .window import Comparison

Grain = Literal["national", "territory", "plan", "channel", "specialty"]
GRAINS: tuple[str, ...] = ("national", "territory", "plan", "channel", "specialty")
TERRITORIES = ("like_for_like", "all_reportable", "projected")
MEASURES = ("trx", "nbrx", "both")
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


class Definition(BaseModel):
    """What a brief is built from. `None` for a week means the question's weeks (else the latest closed week);
    `None` for the comparison means the previous four weeks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_week: str | None = None
    last_week: str | None = None
    comparison: Comparison | None = None
    territories: Literal["like_for_like", "all_reportable", "projected"] = "like_for_like"
    measure: Literal["trx", "nbrx", "both"] = "trx"
    grain: list[Grain] = Field(default_factory=lambda: list(GRAINS))
    relative_to: Literal["other_territories", "national", "none"] = "other_territories"

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

    @field_validator("grain")
    @classmethod
    def _grain(cls, value):
        if not value:
            raise ValueError("Choose at least one level (national, territory, plan, channel or specialty).")
        return [g for g in GRAINS if g in value]  # canonical order, no repeats

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
        return cls(comparison=comparison)

    @classmethod
    def coerce(cls, definition: "Definition | dict | None", comparison: Comparison | None = None) -> "Definition":
        """What an engine receives (a model, its JSON, or nothing) plus the old `comparison` keyword, as one
        definition. A comparison already in the definition wins over the keyword."""
        if definition is None:
            return cls.from_comparison(comparison)
        d = definition if isinstance(definition, Definition) else cls.model_validate(definition)
        return d if d.comparison is not None or comparison is None else d.model_copy(update={"comparison": comparison})

    # -- reading ---------------------------------------------------------------------------------------
    def has(self, grain: str) -> bool:
        return grain in self.grain

    @property
    def is_pre_selected(self) -> bool:
        return (self.territories, self.measure, self.relative_to, self.grain) == ("like_for_like", "trx", "other_territories", list(GRAINS))

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


def comparison_words(c: Comparison | None) -> str:
    if c is None:
        return "the previous four weeks"
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
MEASURE_WORDS = {
    "trx": "Measure: total prescriptions (TRx).",
    "nbrx": "Measure: new patients (NBRx).",
    "both": "Measure: total prescriptions (TRx) beside new patients (NBRx).",
}
RELATIVE_WORDS = {
    "other_territories": "Territory changes are set against: the other territories.",
    "national": "Territory changes are set against: the national change.",
    "none": "Territory changes are set against: nothing, each is stated alone.",
}


def grain_words(d: Definition) -> str:
    return "Levels shown: " + _names(list(d.grain)) + "."


def words(d: Definition) -> list[str]:
    """The whole definition in plain sentences, one per selector, for a reader of either view."""
    out = []
    if d.first_week:
        last = d.last_week or d.first_week
        out.append(f"Period: the week of {d.first_week}." if last == d.first_week else f"Period: the weeks {d.first_week} to {last}.")
    out.append(f"Comparison: {comparison_words(d.comparison)}.")
    out += [TERRITORY_WORDS[d.territories], MEASURE_WORDS[d.measure], grain_words(d), RELATIVE_WORDS[d.relative_to]]
    return out


def changed_words(d: Definition) -> list[str]:
    """Only the selectors that differ from the pre-selected values: what the brief's Assumptions block adds."""
    base = Definition.pre_selected()
    out = []
    if d.territories != base.territories:
        out.append(TERRITORY_WORDS[d.territories])
    if d.measure != base.measure:
        out.append(MEASURE_WORDS[d.measure])
        if d.territories == "projected" and d.measure == "nbrx":
            out.append("The projected national is a TRx figure, so new patients (NBRx) are counted like for like.")
    if d.grain != base.grain:
        out.append(grain_words(d))
    if d.relative_to != base.relative_to:
        out.append(RELATIVE_WORDS[d.relative_to])
    return out


_SHORT = {"territories": {"all_reportable": "territories counted all reportable in each period", "projected": "territories counted as the projected national"},
          "measure": {"nbrx": "measure new patients (NBRx)", "both": "measure TRx beside new patients (NBRx)"},
          "relative_to": {"national": "territory changes set against national", "none": "territory changes set against nothing"}}


def assumption_sentence(d: Definition) -> str | None:
    """One short sentence for the memo's Assumptions block when the definition is not the pre-selected one (the form
    prints the whole definition in words itself); None when it is."""
    base = Definition.pre_selected()
    parts = [_SHORT[f][getattr(d, f)] for f in ("territories", "measure", "relative_to") if getattr(d, f) != getattr(base, f)]
    if d.grain != base.grain:
        parts.insert(2 if len(parts) > 2 else len(parts), "levels " + _names(list(d.grain)))
    return ("Brief definition, changed from the pre-selected values: " + "; ".join(parts) + ".") if parts else None


def labels(d: Definition, period: list[str], baseline: list[str]) -> dict:
    """What every claim records about the definition it was made under (the claim adds its own grain and cut)."""
    return {"territories": d.territories, "measure": d.measure, "relative_to": d.relative_to,
            "period": f"{period[0]} to {period[-1]}" if period else None,
            "comparison": f"{baseline[0]} to {baseline[-1]}" if baseline else None}
