"""Draft golden case files from docs/planning/user-stories.md.

An existing case file is never overwritten unless asked: facts, reviewed questions and hand
edits live in the case files, and the importer only seeds them (core-006 plan, user-story importer).
"""
from __future__ import annotations

import re

import yaml

from .paths import GOLDEN_DIR, REPO_ROOT, STORIES

STORY_RE = re.compile(r"^### \*\*((?:P[1-4]|CA|BM|FM)-Q[1-6]) · (.+?)\*\*\s*$")
PERSONA_RE = re.compile(r"^## \*\*(P[1-4]|CA|BM|FM) · (.+?)\*\*\s*$")
PART_RE = re.compile(r"^# \*\*Part ([AB])\.")
COVERAGE_RE = re.compile(r"^\| ((?:P[1-4]|CA|BM|FM)-Q[1-6]) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|")
ANSWER_RE = re.compile(r"^\s*-\s*\*\*Answer from the data(?: \((.*?)\))?\.\*\*\s*(.*)$")
GWT_RE = re.compile(r"\*\*Given\*\*(.*?)\*\*When\*\*(.*?)\*\*Then\*\*(.*)$")
QUOTED_RE = re.compile(r'["“]([^"”]+)["”]')
QUALIFIER_RE = re.compile(r"(without|with no|as if|from|for)\b")
EVAL_ID_RE = re.compile(r"\b(EV-\d\.\d|FE-\d{2})\b")
ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
MONTH_SPAN_RE = re.compile(rf"\b{MONTHS}(?: (?:to|–) {MONTHS})? \d{{4}}\b")

# Evaluation Pack §4 case taxonomy. Draft assignments; review before freezing.
BRIEFING_CATEGORY = {
    "P1-Q1": "data_artifact", "P1-Q2": "data_artifact", "P1-Q3": "null_week", "P1-Q4": "real_event",
    "P1-Q5": "compound_week", "P1-Q6": "real_event", "P2-Q1": "data_artifact", "P2-Q2": "real_event",
    "P2-Q3": "real_event", "P2-Q4": "real_event", "P2-Q5": "data_artifact", "P2-Q6": "stress",
    "P3-Q1": "real_event", "P3-Q2": "calendar_effect", "P3-Q3": "real_event", "P3-Q4": "multi_week",
    "P3-Q5": "real_event", "P3-Q6": "data_artifact", "P4-Q1": "real_event", "P4-Q2": "real_event",
    "P4-Q3": "stress", "P4-Q4": "compound_week", "P4-Q5": "compound_week", "P4-Q6": "stress",
}


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^\s*-\s+", "", line).replace("**", "")).strip()


def parse(text: str):
    stories, personas, coverage = {}, {}, {}
    part = persona = current = None
    for line in text.splitlines():
        if m := PART_RE.match(line):
            part, current = m.group(1), None
        elif m := PERSONA_RE.match(line):
            persona, current = f"{m.group(1)} {m.group(2)}", None
        elif m := STORY_RE.match(line):
            current = {"story": m.group(1), "question": m.group(2), "persona": persona,
                       "lane": "briefing" if part == "A" else "forecast", "lines": []}
            stories[m.group(1)] = current
        elif line.startswith("#"):
            current = None
        elif m := COVERAGE_RE.match(line):
            coverage[m.group(1)] = m.group(2).strip()
        elif current is not None:
            current["lines"].append(line)
    return stories, coverage


def _period(header: str | None, anchor: str) -> tuple[str | None, str | None]:
    if header:
        return header, None
    dates = ISO_RE.findall(anchor)
    if dates:
        return (f"week of {dates[0]}" if len(dates) == 1 else f"weeks of {', '.join(dates)}"), None
    if m := MONTH_SPAN_RE.search(anchor):
        return m.group(0), None
    return None, "The story states no period; add the weeks to the question before freezing."


def _must_not_say(text: str) -> dict:
    phrases, semantic = [], []
    for m in QUOTED_RE.finditer(text):
        phrase = m.group(1).strip().rstrip(",.;:")
        after = text[m.end():].lstrip(" ,")
        (semantic if QUALIFIER_RE.match(after) else phrases).append(phrase)
    return {"text": text, "phrases": phrases, "semantic": semantic}


def build_case(st: dict, number: int, anchor: str) -> dict:
    body = st["lines"]
    i_answer = next(i for i, line in enumerate(body) if ANSWER_RE.match(line))
    i_given = next(i for i, line in enumerate(body) if "**Given**" in line)
    header, first = ANSWER_RE.match(body[i_answer]).groups()
    parts = ([first.strip()] if first.strip() else []) + [_clean(x) for x in body[i_answer + 1:i_given] if x.strip()]
    given, when, then = (_clean(x) for x in GWT_RE.search(body[i_given]).groups())
    field = lambda marker: next(_clean(x.split(marker, 1)[1]) for x in body if marker in x)  # noqa: E731
    period, note = _period(header, anchor)
    lane = st["lane"]
    question = st["question"] if not period else f"{period[0].upper()}{period[1:]}: {st['question']}"
    return {
        "id": f"C-{number:03d}" if lane == "briefing" else f"F-{number:03d}",
        "lane": lane,
        "story": st["story"],
        "persona": st["persona"],
        "category": BRIEFING_CATEGORY.get(st["story"]) if lane == "briefing" else None,
        "scenario": None,
        "split": "dev",
        "status": "draft",
        "question": question,
        "review_note": note,
        "period": period,
        "anchor": anchor,
        "story_text": next((x.strip().strip("*") for x in body if x.startswith("*As ")), ""),
        "given": given,
        "when": when,
        "then": then,
        "reference_answer": "\n".join(parts),
        "must_not_say": _must_not_say(field("**Must not say**")),
        "action": field("**Action.**"),
        "eval_items": EVAL_ID_RE.findall(field("**Eval items**")),
        "facts": [],
        "source": f"{STORIES.relative_to(REPO_ROOT).as_posix()}#{st['story']}",
    }


class _Dumper(yaml.SafeDumper):
    pass


def _str(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str)


def dump(case: dict) -> str:
    return yaml.dump(case, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10_000)


def run(force: bool = False) -> list[str]:
    stories, coverage = parse(STORIES.read_text(encoding="utf8"))
    written, counters = [], {"briefing": 0, "forecast": 0}
    for story_id, st in stories.items():
        counters[st["lane"]] += 1
        path = GOLDEN_DIR / st["lane"] / f"{story_id}.yaml"
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(build_case(st, counters[st["lane"]], coverage.get(story_id, ""))), encoding="utf8")
        written.append(story_id)
    return written
