"""Turn a question into the weeks and territory it asks about. Rule-based: no model. Shared by both lanes."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .queries import TERRITORY_NAMES, iso, mondays, shift

_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_SPAN = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?: to (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)? (\d{4})\b")
_PROMOTION = re.compile(
    r"\b(?:campaigns?|promotions?|promotional|reach(?:ed|ing)?|respond(?:ed|ing)?|response|"
    r"lift|spend|next dollar|return on investment|ROI)\b", re.I
)


class Comparison(BaseModel):
    """An analyst's explicit comparison choice, independent of the question text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["previous", "last_year", "custom", "pre_launch"]  # pre_launch: the four weeks before Metacora launched
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
        elif self.start is not None or self.end is not None or (self.weeks is None) != (self.kind in ("last_year", "pre_launch")):
            raise ValueError("Previous comparison needs a week count. Last year and pre-launch take no extra fields.")
        return self


PRE_LAUNCH_WEEKS = 4


def comparison_weeks(choice: Comparison, requested: list[str], available: set[str], launch: str | None = None) -> list[str]:
    """The comparison weeks of an explicit choice. `launch` is the competitor's launch week from the data, needed only for
    the pre-launch comparison (the four weeks before it)."""
    if not requested:
        raise ValueError("Choose a reporting window inside the release before setting its comparison.")
    if choice.kind == "pre_launch":
        if launch is None:
            raise ValueError("No competitor launch is recorded in the release, so there are no pre-launch weeks to compare with.")
        if requested[0] < launch:
            raise ValueError(f"The pre-launch comparison needs a period that starts on or after the competitor launch ({launch}).")
        weeks = [shift(launch, -i) for i in range(PRE_LAUNCH_WEEKS, 0, -1)]
    elif choice.kind == "last_year":
        weeks = [shift(w, -52) for w in requested]
    elif choice.kind == "previous":
        weeks = [shift(requested[0], -i) for i in range(choice.weeks, 0, -1)]
    else:
        weeks = mondays(choice.start.isoformat(), choice.end.isoformat())
    if weeks[-1] >= requested[0]:
        raise ValueError("The comparison must end before the reporting window starts.")
    if any(w not in available for w in weeks):
        raise ValueError("The selected comparison is outside the data release. Select another or use the default.")
    return weeks


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def parse(question: str, first_week: str, latest_week: str, *, briefing: bool = False) -> dict:
    head = question.split(":", 1)[0]
    dates = _ISO.findall(head)
    promotion = briefing and bool(_PROMOTION.search(question))
    explicit_week = bool(dates or _SPAN.search(head))
    note = None
    if len(dates) >= 2 and " to " in head:
        weeks = mondays(iso(_monday(date.fromisoformat(dates[0]))), iso(_monday(date.fromisoformat(dates[-1]))))
    elif dates:
        weeks = sorted({iso(_monday(date.fromisoformat(d))) for d in dates})
    elif m := _SPAN.search(head):
        start_m, end_m, year = _MONTHS[m.group(1).lower()], _MONTHS[(m.group(2) or m.group(1)).lower()], int(m.group(3))
        start = date(year, start_m, 1)
        end = date(year + (end_m == 12), end_m % 12 + 1, 1) - timedelta(days=1)
        start += timedelta(days=(7 - start.weekday()) % 7)  # first Monday on or after the 1st
        weeks = mondays(iso(start), iso(_monday(end)))
    elif promotion:
        weeks = mondays(first_week, latest_week)
        note = f"No week was given. The Promotion review covers the full release from {first_week} to {latest_week}."
    else:
        weeks = [latest_week]
        note = f"No week was given, so this uses the latest closed week, {latest_week}."
    inside = [w for w in weeks if first_week <= w <= latest_week]
    territory = next((tid for tid, label in TERRITORY_NAMES.items() if re.search(rf"\b{re.escape(label)}\b", head, re.I)), None)
    parsed = {"weeks": inside, "requested": weeks, "territory": territory, "note": note}
    if briefing:
        parsed.update(promotion=promotion, explicit_week=explicit_week)
    return parsed
