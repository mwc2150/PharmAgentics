"""Turn a question into the weeks and territory it asks about. Rule-based: no model. Shared by both lanes."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .queries import TERRITORY_NAMES, iso, mondays

_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_SPAN = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*(?: to (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)? (\d{4})\b")


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def parse(question: str, first_week: str, latest_week: str) -> dict:
    head = question.split(":", 1)[0]
    dates = _ISO.findall(head)
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
    else:
        weeks = [latest_week]
        note = f"No week was given, so this uses the latest closed week, {latest_week}."
    inside = [w for w in weeks if first_week <= w <= latest_week]
    territory = next((tid for tid, label in TERRITORY_NAMES.items() if re.search(rf"\b{re.escape(label)}\b", head, re.I)), None)
    return {"weeks": inside, "requested": weeks, "territory": territory, "note": note}
