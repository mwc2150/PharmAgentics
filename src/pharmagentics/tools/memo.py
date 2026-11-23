"""The weekly brief as a memo with a fixed outline (brief-003 User Story 2, FR-004, FR-020, FR-021).

    §1 Bottom line · §2 The numbers · §3 What changed and why (§3.1, §3.2 …) · §4 What the data can't tell us
    · §5 Next checks · §6 Appendix

Code builds every section and every number; the writer (agent) or nothing (scripted) adds prose: the §1
answer and one sentence per story. Both Briefing engines compose through `compose`, so they emit the same
skeleton. Headings carry no digits (research R6): section numbers live in the structured `sections`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from . import queries as q
from . import stages
from .checks import DECISION, OWNER, confidence, launch_date
from .lag_checks import LAG_LABELS
from .projection import Projection, _label, method_lines
from .registry import Registry
from . import definition, splits
from .brands import PRODUCTS, briefing_brand

HEADINGS = [("1", "Bottom line"), ("2", "The numbers"), ("3", "What changed and why"),
            ("4", "What the data can't tell us"), ("5", "Next checks"), ("6", "Appendix")]
EMPTY = {"1": "Nothing can be reported for this period.", "2": "No figure can be given for this period.",
         "3": "No material change was found, and territory swings stayed in their normal range.",
         "4": "Nothing in this period limits the figures above.", "5": "No check is open.", "6": ""}
HEADING_PREFIX = "## "
TOKEN = re.compile(r"\{c(\d+)\}")
_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
_RANK = {"Low": 0, "Medium": 1, "High": 2}

METHOD = ("Method: like-for-like figures use only territories whose feed passed the gate in every week compared. "
          "The projected national divides each territory's observed TRx by its panel coverage, and estimates a "
          "territory that cannot be read from its recent share of national. Changes, stories and drivers use "
          "like-for-like cuts only.")
DRIVER_NAMES = {"data": "data quality", "access": "access", "promotion": "promotion", "supply": "supply", "competitor": "competitor"}

# What a reader needs to know about each term the brief uses (from GLOSSARY.md; no digits).
GLOSSARY = {
    "like for like": "Like for like: a comparison that uses only territories whose feed passed its checks in every week compared.",
    "panel coverage": "Panel coverage: the share of a territory's expected prescription records that arrived in a given week.",
    "projected national": "Projected national: national TRx built territory by territory, each territory's observed TRx divided by its panel coverage, summed.",
    "estimated": "Estimated territory: a territory whose coverage is too low to project, or whose count failed its checks, filled from its own recent share of national and labelled as estimated, an assumption.",
    "withheld cut": "Withheld cut: a territory or week whose data failed its checks, so no story or driver is given for it.",
}


@dataclass
class StoryBlock:
    id: str
    title: str
    lines: list[str]  # head line, checks, closing confidence; no "Next:" (it lives in §5)
    prose: str = ""  # one sentence by the writer; empty for the scripted engine
    chart: dict | None = None  # tools/charts.story or charts.competitor (slice 2)
    card: dict | None = None  # brief-008: {headline, confidence, drivers_checked}, plus core-011 {territory, direction, drivers_supported, drivers_ruled_out, cut (None: the whole territory)}; tokens allowed in the headline
    detail: list[str] = field(default_factory=list)  # folded under "Show detail" (analysts only), after the story


@dataclass
class MemoParts:
    title: list[str]
    bottom_line: list[str]
    numbers: list[str]
    limits: list[str]
    next_checks: list[str]
    appendix: list[str]
    stories: list[StoryBlock] = field(default_factory=list)
    story_notes: list[str] = field(default_factory=list)  # calendar, left out, considered and dropped, routine
    answer: str = ""  # §1 prose
    charts: dict[str, dict] = field(default_factory=dict)  # section number -> chart (tools/charts, slice 2)
    kpis: list[dict] = field(default_factory=list)  # brief-008 blocks: §1 tiles, §2 territory table, folded details
    territory_table: dict | None = None
    details: dict[str, list[str]] = field(default_factory=dict)  # section number -> folded lines (analysts only)


def chart_lines(chart: dict | None) -> list[str]:
    """A chart in the flattened answer: its caption and explanation, so the gated scorers check their numbers."""
    return [f"Chart: {chart['caption']}", chart["explanation"]] if chart else []


# The analyst view's word budget (core-011 FR-020): the words a reader sees unfolded in the longest anchor brief that
# printed on two A4 pages. `eval.harness.scorers.WORD_BUDGET["analyst"]` holds the same number (a test keeps them equal;
# src never imports eval).
WORD_BUDGET = 836


def _words(text) -> int:
    return len(re.findall(r"\S+", text)) if isinstance(text, str) else 0


def visible_words(sections: list[dict]) -> int:
    """The words a reader sees without unfolding anything, over `compose`'s sections: the same count as the scorer's
    `count_words` (text, prose, card headline, KPI tiles, chart caption and explanation, table cells; not the detail).
    A claim token counts as the one word its value is."""
    total = 0
    for s in sections:
        total += _words(" ".join(s.get("lines") or [])) + _words(s.get("prose"))
        total += _words((s.get("card") or {}).get("headline"))
        total += sum(_words(k.get("value")) + _words(k.get("detail")) for k in s.get("kpis") or [])
        chart = s.get("chart") or {}
        total += _words(chart.get("caption")) + _words(chart.get("explanation"))
        total += sum(_words(c) for r in (s.get("territory_table") or {}).get("rows") or [] for c in r.get("cells") or [])
    return total


def _shrinkable(block: StoryBlock) -> bool:
    """A territory story's card (its id is `territory:<id>` or `plan:<id>`) can shrink to its headline; a cut, national,
    restatement or promotion card never does (brief-010 FR-008)."""
    return bool(block.card) and block.id.partition(":")[0] in ("territory", "plan") and any(block.lines)


def compose(parts: MemoParts) -> tuple[str, list[dict]]:
    """`_compose`, then the budget (brief-010 FR-008): when the analyst view's words would exceed the budget, territory
    cards shrink to their headline, longest first, until it fits or none is left. The lines move to the folded detail,
    so nothing leaves the scored answer, and the flattened answer is the one the unshrunk brief has, word for word (only
    where a reader finds the text changes). Nothing is ever dropped, and a cut card is never shrunk."""
    template, sections = _compose(parts)
    if visible_words(sections) <= WORD_BUDGET:
        return template, sections
    stories = list(parts.stories)
    for i in sorted((i for i, b in enumerate(stories) if _shrinkable(b)), key=lambda i: -_words(" ".join(stories[i].lines))):
        b = stories[i]
        stories[i] = replace(b, lines=[], detail=[x for x in b.lines if x] + list(b.detail))
        _, sections = _compose(replace(parts, stories=stories))
        if visible_words(sections) <= WORD_BUDGET:
            break
    return template, sections


def _compose(parts: MemoParts) -> tuple[str, list[dict]]:
    """The token template (flattened answer) and the sections, each {number, title, lines, prose} plus, when
    present, the brief-008 blocks: kpis (§1), territory_table (§2), card and detail. Text, then detail, goes into
    the answer, so folding changes what is shown and never what is scored (FR-002)."""
    body = {"1": parts.bottom_line, "2": parts.numbers, "3": parts.story_notes, "4": parts.limits,
            "5": parts.next_checks, "6": parts.appendix}
    prose = {"1": parts.answer}
    details = {k: [x for x in v if x] for k, v in parts.details.items()}
    seen = "\n".join(parts.title + [x for n, _ in HEADINGS for x in body[n] + details.get(n, [])] + [parts.answer]
                     + [x for s in parts.stories for x in s.lines + s.detail + [s.prose]]).lower()
    glossary = [d for term, d in GLOSSARY.items() if term in seen]
    details["6"] = [METHOD] + (["Glossary:"] + [f"- {d}" for d in glossary] if glossary else []) + details.get("6", [])
    out, sections = list(parts.title), []

    def with_detail(section: dict, number: str) -> dict:
        if details.get(number):
            section["detail"] = "\n".join(details[number])
        return section

    for number, title in HEADINGS:
        lines = [x for x in body[number] if x]
        if number == "3":
            out.append(HEADING_PREFIX + title)
            for s in parts.stories:
                story_lines = [x for x in s.lines if x]
                out += story_lines[:1] + ([s.prose] if s.prose else []) + story_lines[1:] + chart_lines(s.chart) + [x for x in s.detail if x]
            if not lines and not parts.stories:
                lines = [EMPTY["3"]]
            out += lines + details.get("3", [])
            sections.append(with_detail({"number": number, "title": title, "lines": lines, "prose": ""}, "3"))
            for i, s in enumerate(parts.stories, 1):
                item = {"number": f"3.{i}", "title": s.title, "lines": [x for x in s.lines if x], "prose": s.prose, "chart": s.chart}
                if s.card:
                    item["card"] = s.card
                if any(s.detail):
                    item["detail"] = "\n".join(x for x in s.detail if x)
                sections.append(item)
            continue
        if not lines and not prose.get(number) and EMPTY[number]:
            lines = [EMPTY[number]]
        out.append(HEADING_PREFIX + title)
        chart = parts.charts.get(number)
        out += lines + ([prose[number]] if prose.get(number) else []) + chart_lines(chart) + details.get(number, [])
        item = with_detail({"number": number, "title": title, "lines": lines, "prose": prose.get(number, ""), "chart": chart}, number)
        if number == "1" and parts.kpis:
            item["kpis"] = parts.kpis
        if number == "2" and parts.territory_table:
            item["territory_table"] = parts.territory_table
        sections.append(item)
    return "\n".join(out), sections


def render_sections(sections: list[dict], claims: list[dict], index: dict[int, int] | None = None) -> list[dict]:
    """Fill each section's tokens, with where each claim sits (inline citations). `claims` are the claims the
    tokens number; `index` maps a token number to its position in the envelope's claims when the envelope keeps
    only the claims it uses (the agent). Blocks are filled the same way: `value_citation` (a span list),
    `cell_citations` (one span list per cell), `headline_citations` and `detail_citations`; a tile's detail and a
    table's note are filled without citations."""
    from .registry import cite

    def fill(text: str) -> tuple[str, list[dict]]:
        return cite(text, claims, index)

    out = []
    for s in sections:
        text, prose, chart = "\n".join(s["lines"]), s["prose"], s.get("chart")
        extra = (chart["caption"] + "\n" + chart["explanation"]) if chart else ""
        table, card = s.get("territory_table"), s.get("card")
        blocks = [s.get("detail", "")] + [f"{k.get('value', '')}\n{k.get('detail') or ''}" for k in s.get("kpis", [])]
        if table:
            blocks += [c for r in table["rows"] for c in r["cells"]] + [table.get("note") or ""]
        if card:
            blocks.append(card["headline"])
        used = list(dict.fromkeys(int(n) for n in TOKEN.findall("\n".join([text, prose, extra] + blocks))))
        refs = [index[n] if index is not None else n - 1 for n in used
                if 0 < n <= len(claims) and (index is None or n in index)]
        (t, t_spans), (pr, p_spans) = fill(text), fill(prose)
        item = {"number": s["number"], "title": s["title"], "text": t, "prose": pr, "claims": refs,
                "text_citations": t_spans, "prose_citations": p_spans, "chart": None}
        if chart:
            explanation, e_spans = fill(chart["explanation"])
            item["chart"] = {**chart, "caption": fill(chart["caption"])[0], "explanation": explanation,
                             "explanation_citations": e_spans}
        if s.get("detail"):
            item["detail"], item["detail_citations"] = fill(s["detail"])
        if s.get("kpis"):
            item["kpis"] = []
            for k in s["kpis"]:
                value, spans = fill(k["value"])
                item["kpis"].append({**k, "value": value, "value_citation": spans, "detail": fill(k.get("detail") or "")[0] or None})
        if table:
            rows = []
            for r in table["rows"]:
                filled = [fill(c) for c in r["cells"]]
                rows.append({**r, "cells": [f[0] for f in filled], "cell_citations": [f[1] for f in filled]})
            item["territory_table"] = {**table, "rows": rows, "note": fill(table["note"])[0] if table.get("note") else None}
        if card:
            headline, h_spans = fill(card["headline"])
            item["card"] = {**card, "headline": headline, "headline_citations": h_spans}
        out.append(item)
    return out


# Code-built sections -----------------------------------------------------------------------------

def title_lines(p) -> list[str]:
    return [f"Brief for {stages.describe(p)}. Product: {p.brand_id}."] + ([p.note] if p.note else [])


def withheld(p) -> list[tuple[str, str]]:
    """(week, territory) cuts in the requested weeks that failed the feed gate."""
    return sorted((w, t) for w in p.requested for t in p.terrs if p.status.get((w, t), ("PASS", ""))[0] == "FLAG")


def _owner(t: str) -> str:
    """A territory's possessive: "New England's", "Great Lakes'"."""
    name = q.name(t)
    return name + ("'" if name.endswith("s") else "'s")


def _warning(p, proj: Projection) -> str | None:
    cuts = withheld(p)
    if not cuts:
        return None
    if len(p.requested) > 1 or len(cuts) > 2:
        return ("Data warning: some territory-weeks in this period failed the feed gate. They are labelled in "
                "The numbers, and no story is given for them.")
    parts = []
    for w, t in cuts:
        row = proj.row(t)
        if row is not None and row.basis == "projected":
            parts.append(f"{_owner(t)} feed for {w} is incomplete, so its TRx is projected from panel coverage, an assumption")
        else:
            parts.append(f"{_owner(t)} feed for {w} failed its checks, so its TRx is estimated from its recent "
                         "share of national, an assumption")
    return "Data warning: " + "; ".join(parts) + ". No story is given for " + ("it." if len(cuts) == 1 else "them.")


def _like_for_like(reg: Registry, p, facts: dict | None = None, col: str | None = None, key: str = "like", *,
                   rule: str | None = None, extra: int | None = None) -> str:
    """§1's national change under a territories rule, a measure and a comparison (the primary of each unless given:
    the pre-selected definition makes today's sentence and today's claims). An extra value's sentence is labelled with
    what it is set against and recorded in `facts["like_extra"]` for the KPI strip."""
    W = p.weeks
    col = col or p.col
    label = stages.measure_label(col)
    mode = stages.national_basis(p, col, rule)
    cmp_, B = (p.comparison, p.baseline) if extra is None else p.extra_baselines[extra]
    cur, base, tc, tb = stages.national_sql(p, col, rule, extra)
    if cur is None:
        return ("No like-for-like change is given: no territory passes the feed gate in every week compared." if mode == "like_for_like" else
                "No national change is given: no territory is reportable in every week of the period.")
    if not B or base is None:
        return "No like-for-like change is given: the release has no earlier weeks to compare with." if not B else \
            "No national change is given: no territory is reportable in every comparison week."
    vs = comparison_text(p) if extra is None else stages.describe_comparison(cmp_, B)
    change = reg.scalar(q.pct_change(cur, base)) or 0
    labels = {"territories": rule or p.definition.territory_rule, "measure": col}
    if extra is not None:
        labels.update(stages.comparison_labels(cmp_, B))
    scope = {"like_for_like": "like-for-like national", "all_reportable": "national over the territories reportable in the period",
             "projected": "projected national"}[mode]
    with reg.under(**labels):
        n = None if mode == "projected" else reg.claim(
            "get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} and {q._in('territory_id', tc)}", "int")
        total = reg.claim("get_metric", "select count(*) from raw.dim_territory", "int")
        pct = reg.claim("get_metric", q.pct_change(cur, base), "pct", scope=scope)
        entry = {"n": n, "total": total, "pct": pct, "word": stages.word(change), "basis": mode, "label": label, "vs": vs}
        if col != "trx" or col != p.col:  # an observed level the KPI strip shows (TRx has the projected national)
            entry["avg"] = reg.claim("get_metric", cur, "int", scope=scope)
        if mode == "like_for_like":
            text = f"Like for like on {n} of {total} territories, {p.brand_id} {label} is {stages.word(change)} {pct} against {vs}."
        elif mode == "projected":
            text = f"The projected national {p.brand_id} TRx is {stages.word(change)} {pct} against the projected national of {vs}."
        else:
            n_base = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(B)} "
                               f"and {q._in('territory_id', tb)}", "int", scope="territories reportable in the comparison weeks")
            entry["n_base"] = n_base
            text = (f"On the {n} of {total} territories reportable in these weeks, {p.brand_id} {label} is {stages.word(change)} {pct} against "
                    f"{vs}, when {n_base} of {total} were reportable.")
    if facts is not None:
        if extra is None and rule is None and col == p.col:
            facts[key] = entry
        else:
            entry["kind"] = "comparison" if extra is not None else "rule" if rule is not None else "measure"
            entry["tile"] = (f"Change against {stages.comparison_tile(cmp_, B)}" if extra is not None else
                             _RULE_TILES[mode] if rule is not None else f"Change in {label}")
            facts.setdefault("like_extra", []).append(entry)
    return text


_RULE_TILES = {"like_for_like": "Change, like for like", "all_reportable": "Change, all reportable territories",
               "projected": "Change, projected national"}


def comparison_text(p) -> str:
    """The comparison weeks in words and dates, with no other digit (brief-007 FR-004)."""
    return stages.describe_comparison(p.comparison, p.baseline)


_COUNT = {**_WORDS, 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen"}


def comparison_phrase(p) -> str | None:
    """The comparison as a short phrase a sentence can carry (brief-008 FR-014): code fills it into the writer's
    `{cmp}` token, so the model never words the comparison. None when there is no earlier week to compare with.
    No digit except the dates of a single week or a custom window."""
    B = p.baseline
    if not B:
        return None
    if len(B) == 1:
        return f"the week of {B[0]}"
    kind = p.comparison.kind if p.comparison is not None else "previous"
    if kind == "last_year":
        return "the same weeks last year"
    if kind == "custom":
        return f"the weeks from {B[0]} to {B[-1]}"
    return f"the previous {_COUNT.get(len(B), 'several')} weeks"


def _least_sure(reg: Registry, p, proj: Projection, stories: list[dict]) -> str | None:
    """Research R8: estimated territory, else projected, else the lowest-confidence story's change, else the
    change built on the fewest prescriptions. The competitor story is left out: its share is measured."""
    single = len(proj.weeks) == 1
    for basis in ("estimated", "projected"):
        ts = proj.territories(basis)
        if ts:
            row = proj.row(ts[0])
            if single and basis == "projected":
                why = f"is an assumption, projected from panel coverage of {row.coverage}"
            elif single:
                why = "is an assumption, estimated from its recent share of national, because its feed failed its checks"
            else:
                why = (f"rests on an assumption: it is {basis} for the week{'s' if len(row.weeks) > 1 else ''} "
                       f"of {', '.join(sorted(row.weeks))}")
            amount = f"TRx of {row.token}" if single else f"TRx, {row.token} a week,"
            return f"Least sure: {_owner(ts[0])} {amount} {why}."
    if stories:
        s = min(stories, key=lambda s: _RANK.get(s["confidence"], 0))
        t = s["territory"]
        x, b = q.mean_weekly(p.weeks, terrs=[t], product=p.brand_id, col=p.col), q.mean_weekly(p.baseline, terrs=[t], product=p.brand_id, col=p.col)
        change = reg.scalar(q.pct_change(x, b)) or 0
        pct = reg.claim("get_metric", q.pct_change(x, b), "pct", territory=t)
        return (f"Least sure: the {q.name(t)} change ({stages.word(change)} {pct}); its confidence, {s['confidence']}, "
                "is the lowest of this brief's stories.")
    if len(p.weeks) == 1 and p.baseline and p.has("national"):
        w = p.weeks[0]
        prev = q.shift(w, -1)
        sql = q.pct_change(q.trx_sum([w], product=p.brand_id), q.trx_sum([prev], product=p.brand_id))
        change = reg.scalar(sql) or 0
        pct = reg.claim("get_metric", sql, "pct", scope="week over week, reportable cuts")
        return (f"Least sure: the week-over-week change ({stages.word(change)} {pct}), "
                "because it compares one week with one week.")
    if p.ok and p.baseline and p.has("national"):
        return "Least sure: the like-for-like change, the only change this brief states."
    return None


def bottom_line(reg: Registry, p, proj: Projection, stories: list[dict], restated: bool, facts: dict | None = None) -> list[str]:
    """§1 in FR-021 order, after a data warning or restatement note when there is one. `stories` are the
    territory stories in brief order: {territory, confidence}. `facts` receives the claims the KPI strip reuses."""
    facts = {} if facts is None else facts
    lines = [x for x in [_warning(p, proj)] if x]
    if restated:
        lines.append("Data note: an earlier week was restated. The new value and the reason are in The numbers.")
    W = proj.weeks
    facts["brand"] = p.brand_id
    if not p.has("national"):
        lines.append("National figures are not part of this brief: its levels leave them out.")
    else:
        if proj.national is None:
            lines.append("This period cannot be reported nationally: no territory's feed can be read.")
        elif len(W) == 1:
            lines.append(f"Projected national {p.brand_id} TRx is {proj.national} for the week of {W[0]}.")
        else:
            lines.append(f"Projected national {p.brand_id} TRx averaged {proj.national} a week from {W[0]} to {W[-1]}.")
        facts["national"] = proj.national
        lines.append(_like_for_like(reg, p, facts))
        for rule in p.definition.territories[1:]:  # each extra value adds its figure beside the primary (FR-000e)
            lines.append(_like_for_like(reg, p, facts, rule=rule))
        for j in range(len(p.extra_baselines)):
            lines.append(_like_for_like(reg, p, facts, extra=j))
        if p.extra_col:
            lines.append(_like_for_like(reg, p, facts, col=p.extra_col))
        share = reg.claim("compare_competitors", q.share(W, p.brand_id), "pct", product=p.brand_id)
        facts["share"] = share
        lines.append(f"{p.brand_id} held {share} of the four-brand market basket.")
        launched = launch_date(reg)
        if launched is not None and launched <= W[-1] and p.brand_id == "BXA":
            pre = [q.shift(launched, -i) for i in range(4, 0, -1)]
            facts["pre"] = reg.claim("compare_competitors", q.share(pre, p.brand_id), "pct", product=p.brand_id, weeks="before launch")
            facts["share_word"] = stages.word((reg.scalar(q.share(W, p.brand_id)) or 0) - (reg.scalar(q.share(pre, p.brand_id)) or 0))
    least = _least_sure(reg, p, proj, stories)
    if least:
        lines.append(least)
    return lines


def limits(p, proj: Projection, health: str, reg: Registry | None = None) -> dict:
    """§4 as {lines, detail}. The first line is the short paragraph leaders read: data health, and whether the
    focus territory is withheld. The gate detail, the focus territory's feed figures, how the projection was
    built and the comparison-week range go to the folded detail (brief-008 FR-005)."""
    head, *gate = health.split("\n")
    first = head
    if p.focus in p.terrs and p.focus not in p.ok:
        first += f" {q.name(p.focus)} has withheld cuts in these weeks, so no like-for-like story is given for it."
    lines = [first] + ([p.calendar_note] if p.calendar_note else [])
    detail = gate + (_feed_figures(reg, p, proj) if reg is not None else []) + method_lines(proj)
    return {"lines": lines, "detail": detail}


def _feed_figures(reg: Registry, p, proj: Projection) -> list[str]:
    lines, W = [], p.requested
    if p.focus in p.terrs:
        where = f"from reporting.v_feed_health where territory_id = '{p.focus}' and week_start in {q._dates(W)}"
        got = reg.claim("validate_feed", f"select sum(received_rows) {where}", "int", territory=p.focus)
        want = reg.claim("validate_feed", f"select sum(expected_rows) {where}", "int", territory=p.focus)
        cov = reg.claim("validate_feed", f"select min(panel_coverage_ratio) {where}", "dec3", territory=p.focus)
        lines.append(f"Feed for {q.name(p.focus)} in these weeks: {got} rows received against {want} expected; "
                     f"lowest panel coverage {cov}.")
    if len(proj.weeks) == 1 and p.baseline:
        for basis in ("projected", "estimated"):
            for t in proj.territories(basis):
                weekly = (f"select week_start, sum(trx) s from {q.RX} where product_id = '{p.brand_id}' and territory_id = '{t}' "
                          f"and week_start in {q._dates(p.baseline)} group by 1")
                if not reg.scalar(f"select count(*) from ({weekly})"):
                    continue
                low = reg.claim("get_metric", f"select min(s) from ({weekly})", "int", territory=t, scope="comparison weeks")
                high = reg.claim("get_metric", f"select max(s) from ({weekly})", "int", territory=t, scope="comparison weeks")
                lines.append(f"{q.name(t)}'s observed {p.brand_id} TRx ranged from {low} to {high} a week in the comparison weeks, "
                             f"which is what its {basis} level stands in for.")
    return lines


def appendix(reg: Registry, brand_id: str = "BXA", *, p=None, proj: Projection | None = None, restated: bool = False) -> list[str]:
    """§6 text: the data version and the Assumptions block. The method and the glossary are folded (compose)."""
    brand_id = briefing_brand(p.brand_id if p is not None else brand_id)
    lines = [f"Data version {reg.data_version}. Product: {brand_id} ({PRODUCTS[brand_id]}), synthetic data."]
    return lines + (assumptions(p, proj, restated) if p is not None else [])


def assumptions(p, proj: Projection | None, restated: bool = False) -> list[str]:
    """The Assumptions block (brief-007 FR-012; the Week 6 assumption book): each assumption with its source, in
    at most five items (brief-008 FR-004)."""
    source = "the brief's default rule, the four weeks before the period" if p.comparison is None else p.baseline_source
    fewer = (f" The release starts on {p.first}, so fewer weeks exist."
             if p.comparison is None and p.baseline and len(p.baseline) < stages.BASELINE_WEEKS else "")
    lines = ["Assumptions:", f"- Comparison weeks: {comparison_text(p)}. Source: {source}.{fewer}"]
    lines.append("- Like for like: changes use only territories whose feed passed the gate in every week compared. "
                 "Withheld cuts are left out of every change and story, and never read as zero demand."
                 + (" Calendar weeks are left out of the stories." if p.calendar_note else " Holiday weeks are left out.")
                 + (" A restatement is reported when the restated week is inside the period or the restatement was published inside it."
                    if restated else "")
                 + (" Source: the feed gate and the vendor's restatement record." if restated else " Source: the feed gate.")
                 + (f" {changed}" if (changed := definition.assumption_sentence(p.definition)) else ""))
    marked = [r.territory for r in proj.rows if r.basis != "observed"] if proj else []
    if marked:
        lines.append(f"- Not observed: {', '.join(q.name(t) for t in marked)} "
                     f"{'is' if len(marked) == 1 else 'are'} projected or estimated, not counted. Source: panel coverage "
                     "and each territory's recent share of national.")
    if p.brand_id == "BXA":
        lines.append("- Drivers: the checks evaluate the same week and delays of one and two weeks. "
                     "A supported timing requires activity to move with reportable TRx. Monthly access data cannot identify a weekly lag.")
    return lines


def scope_line(p, proj: Projection | None = None) -> str:
    """The one line leaders see about the period and its comparison (brief-007 FR-012)."""
    marked = proj is not None and any(r.basis != "observed" for r in proj.rows)
    return (f"Scope: {stages.describe(p)}, compared with {comparison_text(p)}."
            + (" Levels marked projected or estimated are assumptions." if marked else ""))


def driver_timing(stories: list[dict]) -> list[str]:
    """One Assumptions item for every story's lag, so the block stays within five items."""
    found = [f"{q.name(story['territory'])}: " + ", ".join(f"{driver}, {LAG_LABELS[lag]}" for driver, lag in story["lags"].items())
             for story in stories if story.get("lags")]
    return [f"- Driver timing: {'; '.join(found)}. Source: recorded activity and reportable TRx."] if found else []


def _line(subject: str, action: str, owner: str, decision: str) -> str:
    return f"- {subject}: {action}. Owner: {owner}. Unlocks: {decision}."


_REREAD = re.compile(r"when will we know|know more|firm(?:s|ed)? up", re.I)


def next_checks(p, stories: list[dict], competitor: bool) -> list[str]:
    """§5 (research R10): one line per territory story ({territory, confidence, drivers}), per withheld cut,
    for a continuing competitor story, and a re-read line when the question asks when more will be known."""
    lines = []
    for s in stories:
        name = q.name(s["territory"])
        drivers = [d for d in s.get("drivers", []) if d in OWNER]
        if s["confidence"] == "Low" or not drivers:
            lines.append(_line(name, "split by plan and specialty, and ask for local context", "sales leadership",
                               DECISION["unresolved"]))
        else:
            owners = ", ".join(dict.fromkeys(OWNER[d] for d in drivers))
            decisions = "; ".join(DECISION[d] for d in drivers)
            lines.append(_line(name, f"confirm the {' and '.join(drivers)} finding", owners, decisions))
    cuts = withheld(p)
    if len(cuts) > 2:
        lines.append(_line("Withheld cuts", "re-run when the corrected feeds land, and disclose each restated week",
                           OWNER["data"], DECISION["data"]))
    for w, t in (cuts if len(cuts) <= 2 else []):
        lines.append(_line(f"{q.name(t)}, week of {w}", "re-run when the corrected feed lands, and disclose the restated week",
                           OWNER["data"], DECISION["data"]))
    if competitor:
        lines.append(_line("Metacora", "track the basket shares each week", OWNER["competitor"], DECISION["competitor"]))
    if _REREAD.search(p.question or ""):
        lines.append(_line("Re-read", "re-run this brief four weeks after any change, when the comparison weeks have caught up",
                           "commercial analytics", "whether the estimate has firmed up"))
    return lines


def without_next(closing: str) -> str:
    """A story's closing line without its "Next: …" clause, which moves to §5."""
    return re.sub(r"\s*Next: [^.]*\.", "", closing).rstrip()


def _movers(changes: list[dict]) -> str | None:
    """One sentence for the territory changes: the largest fall and the largest rise on the comparison weeks."""
    rows = [c for c in changes if c.get("base")]
    falls = sorted((c for c in rows if c["base"]["word"] == "down"), key=lambda c: c["base"]["change"])
    rises = sorted((c for c in rows if c["base"]["word"] == "up"), key=lambda c: -c["base"]["change"])
    parts = []
    if falls:
        parts.append(f"{q.name(falls[0]['territory'])} fell most (down {falls[0]['base']['token']})")
    if rises:
        parts.append(f"{q.name(rises[0]['territory'])} rose most (up {rises[0]['base']['token']})")
    if not parts:
        return "No territory moved beyond a flat change against the comparison weeks." if rows else None
    return "Against the comparison weeks, " + " and ".join(parts) + "."


def _change_cell(change: dict | None) -> str:
    return f"{change['word']} {change['token']}" if change else "not given"


def territory_table(p, proj: Projection, facts: dict) -> dict | None:
    """The §2 territory table (brief-008 FR-001): the level, the change on the comparison weeks and, for a one-week
    period only (FR-011), the change on the week before. Values are claim tokens already in the detail. The primary
    measure sets the level and change columns; each extra measure adds a level and a change column, each extra comparison
    a change column (FR-000e). A brief without the territory level has no table."""
    if proj.national is None or not p.has("territory"):
        return None
    single, changes = len(proj.weeks) == 1, {c["territory"]: c for c in facts.get("changes", [])}
    has_change = bool(p.baseline) and bool(changes)
    observed = p.col != "trx"  # a projection is a TRx level only
    suffix = "" if single else " a week"
    columns = ["Territory", f"{p.brand_id} {p.measure_label}{suffix}"]
    if p.extra_col:
        columns.append(f"{p.brand_id} {p.extra_label}{suffix}")
    if has_change and single:
        columns.append("On the week before")
    if has_change:
        columns.append("On the comparison weeks")
        if p.extra_col:
            columns.append(f"{p.extra_label[:1].upper()}{p.extra_label[1:]}, on the comparison weeks")
        columns += [f"On {stages.comparison_tile(c, B)}" for c, B in p.extra_baselines]
    columns.append("Basis")
    rows = []
    for r in proj.rows:
        c = changes.get(r.territory) or {}
        cells = [q.name(r.territory), (c.get("level") or "not given") if observed else r.token]
        if p.extra_col:
            cells.append(c.get("level_x") or "not given")
        if has_change and single:
            cells.append(_change_cell(c.get("wow")))
        if has_change:
            cells.append(_change_cell(c.get("base")))
            if p.extra_col:
                cells.append(_change_cell(c.get("xm")))
            cells += [_change_cell(x) for x in (c.get("xc") or [None] * len(p.extra_baselines))]
        rows.append({"cells": cells + [r.basis], "basis": r.basis})
    shown = {r.territory for r in proj.rows}
    for t in sorted(set(p.terrs) - shown, key=q.name):
        rows.append({"cells": [q.name(t)] + ["withheld"] * (len(columns) - 1), "basis": "withheld"})
    notes = []
    if has_change:
        notes.append(f"Change is against {comparison_text(p)}.")
        if any(not c["ok"] for c in changes.values()):
            notes.append("No change is given where a week compared failed the feed gate.")
    if observed or p.extra_col:
        notes.append("New patients (NBRx) are observed counts, so a projected or estimated territory shows none."
                     if "nbrx" in p.definition.measure else "A TRx level beside new patients is observed, not projected.")
    if any(r.basis != "observed" for r in proj.rows):
        notes.append("A projected or estimated level is an assumption, not an observed count.")
    return {"columns": columns, "rows": rows, "note": " ".join(notes) or None}


def _avg_sentence(avg: dict, brand: str, lead: str = "Like for like, ") -> str:
    """§2's sentence for the national average under a territories rule, a measure and a comparison (the pre-selected
    ones are today's sentence)."""
    label = avg.get("label", "TRx")
    basis = avg.get("basis", "like_for_like")
    vs = avg.get("vs", "the comparison weeks")
    if basis == "projected":
        return (f"The projected national {brand} TRx averaged {avg['avg']} a week, {avg['word']} {avg['pct']} against the projected national "
                f"of {vs}." if avg.get("pct") else f"The projected national {brand} TRx averaged {avg['avg']} a week.")
    if basis == "all_reportable":
        base = f", when {avg['n_base']} of {avg['total']} were reportable" if avg.get("n_base") else ""
        change = f", {avg['word']} {avg['pct']} against {vs}{base}." if avg.get("pct") else "."
        return f"For all reportable territories, {brand} {label} averaged {avg['avg']} a week across {avg['n']} of {avg['total']} territories reportable in these weeks{change}"
    if avg.get("pct"):
        return (f"{lead}{brand} {label} averaged {avg['avg']} a week across {avg['n']} of {avg['total']} territories, "
                f"{avg['word']} {avg['pct']} against {vs}.")
    return f"{lead}{brand} {label} averaged {avg['avg']} a week across {avg['n']} of {avg['total']} territories."


def numbers(proj: Projection, facts: dict, restatement_lines: list[str], p=None) -> dict:
    """§2 as {lines, detail, territory_table}: the scope line, short sentences on the like-for-like change, the
    week over week (a one-week period only), the largest moves, any data artifact, calendar effects and
    restatements (research R7). The territory levels and changes are the table; the same claims, one sentence
    a territory, are the folded detail so the scored answer keeps every number."""
    lines = [scope_line(p, proj)] if p is not None else []
    brand = proj.brand_id
    if proj.national is None and not facts.get("no_national"):
        lines.append("No projected national is given: no territory in these weeks can be read.")
    avg = facts.get("avg")
    if facts.get("no_national"):
        lines.append("National figures are not part of this brief: its levels leave them out.")
    elif avg is None:
        lines.append("No like-for-like national figure is given: no territory passes the feed gate in every one of these weeks.")
    else:
        lines.append(_avg_sentence(avg, brand))
        lines += [_avg_sentence(x, brand) for x in facts.get("avg_extra", [])]
    if (wow := facts.get("wow")):
        lines.append(f"Week over week, {brand} TRx is {wow['now']} against {wow['prev']} the week before ({wow['word']} {wow['pct']}).")
    if (both := facts.get("wow_both")):
        lines.append(f"On the {both['n']} {both['noun']} both weeks, {brand} TRx went from {both['from']} to {both['to']} "
                     f"({both['word']} {both['pct']}).")
    if (moved := _movers(facts.get("changes", []))):
        lines.append(moved)
    if facts.get("artifact"):
        lines.append(facts["artifact"])
    lines += facts.get("calendar", []) + restatement_lines
    detail: list[str] = []
    if proj.national is not None and (p is None or p.has("territory")):
        single, changes = len(proj.weeks) == 1, {c["territory"]: c for c in facts.get("changes", [])}
        marked = any(r.basis != "observed" for r in proj.rows)
        observed = p is not None and p.col != "trx"
        detail.append("By territory, observed unless marked; a projected or estimated level is an assumption, not an "
                      "observed count." if marked else "By territory, all observed.")
        for r in proj.rows:
            c = changes.get(r.territory)
            parts = []
            if c and not c["ok"]:
                parts.append("no change is given, because a week compared failed the feed gate")
            elif c:
                if c.get("wow"):
                    parts.append(f"{c['wow']['word']} {c['wow']['token']} on the week before")
                elif single:
                    parts.append("the week-over-week change is withheld")
                parts.append(f"{c['base']['word']} {c['base']['token']} on the comparison weeks")
                if c.get("xm"):
                    parts.append(f"{p.extra_label} {c['xm']['word']} {c['xm']['token']} on the comparison weeks")
                parts += [f"{x['word']} {x['token']} {x['since']}" for x in (c.get("xc") or []) if x]
            if observed:
                level = (c or {}).get("level")
                detail.append(f"{q.name(r.territory)}: {level or 'no count'} {brand} {p.measure_label} a week" + (f"; {'; '.join(parts)}." if parts else "."))
                continue
            also = f" ({c['level_x']} {brand} {p.extra_label} a week)" if c and c.get("level_x") else ""
            detail.append(f"{q.name(r.territory)}: {r.token} {brand} TRx a week{_label(r, single)}{also}" + (f"; {'; '.join(parts)}." if parts else "."))
    return {"lines": lines, "detail": detail, "territory_table": territory_table(p, proj, facts) if p is not None else None}


# Blocks of §1 and the story cards (brief-008 FR-001) -------------------------------------------------------

def kpis(p, proj: Projection, facts: dict) -> list[dict]:
    """The §1 KPI strip, in order: national level, the like-for-like change, the basket share, territories
    reportable. Each value is a claim already in §1's text; a tile with no claim behind it is left out. A primary
    measure of new patients (NBRx) shows the NBRx level and change; each extra value adds labelled tiles beside the
    primary (FR-000e)."""
    W, tiles = proj.weeks, []
    like = facts.get("like")
    observed = p.col != "trx"
    extras = facts.get("like_extra", [])
    if observed:
        if like and like.get("avg"):
            tiles.append({"label": f"National {p.brand_id} {p.measure_label}", "value": like["avg"],
                          "detail": "a week, like for like" if len(W) > 1 else "like for like", "direction": None})
    elif facts.get("national"):
        when = f"projected, week of {W[0]}" if len(W) == 1 else f"projected, a week, {W[0]} to {W[-1]}"
        tiles.append({"label": f"National {p.brand_id} TRx", "value": facts["national"], "detail": when, "direction": None})
    if p.extra_col and (more := next((x for x in extras if x.get("kind") == "measure"), None)) and more.get("avg"):
        tiles.append({"label": f"National {p.brand_id} {p.extra_label}", "value": more["avg"], "detail": "a week, like for like",
                      "direction": None})
    if like:
        basis = like.get("basis", "like_for_like")
        how = {"like_for_like": "like for like", "all_reportable": "all reportable territories", "projected": "projected national"}[basis]
        tiles.append({"label": "Change on the comparison weeks" if not observed else f"Change in {p.measure_label}",
                      "value": like["pct"], "detail": f"{how}, against {comparison_text(p)}", "direction": like["word"]})
    for x in extras:
        how = {"like_for_like": "like for like", "all_reportable": "all reportable territories", "projected": "projected national"}[x["basis"]]
        tiles.append({"label": x["tile"], "value": x["pct"], "detail": f"{how}, against {x['vs']}", "direction": x["word"]})
    if facts.get("share"):
        tiles.append({"label": f"{p.brand_id} basket share", "value": facts["share"],
                      "detail": "of the four-brand basket" + (f", against {facts['pre']} before launch" if facts.get("pre") else ""),
                      "direction": facts.get("share_word")})
    if like and like.get("n"):
        detail = f"of {like['total']}, like for like" if like.get("basis", "like_for_like") == "like_for_like" else \
            f"of {like['total']} in these weeks, and {like['n_base']} in the comparison weeks"
        tiles.append({"label": "Territories reportable", "value": like["n"], "detail": detail, "direction": None})
    return tiles


def bottom_detail(facts: dict) -> list[str]:
    """§1's folded line: the share before launch, which the basket tile quotes."""
    return [f"Before Metacora launched, {facts['brand']} held {facts['pre']} of the four-brand basket."] if facts.get("pre") else []


def _verb(word: str, token: str, rose: str = "rose", fell: str = "fell") -> str:
    return {"up": f"{rose} {token}", "down": f"{fell} {token}"}.get(word, f"held flat ({token})")


def driver_calls(checks) -> tuple[list[str], list[str]]:
    """(supported, ruled out) driver ids from the checks' verdicts, in the order run. An inconclusive check
    ("insufficient") is in neither list. The ids are the eval's (access, promotion, supply, competitor, data)."""
    return ([c.driver for c in checks if c.verdict == "supported"], [c.driver for c in checks if c.verdict == "ruled_out"])


def story_card(name: str, facts: dict, confidence: str, drivers: list[str], *, territory: str | None = None,
               checks=(), measure: str = "trx") -> dict:
    """A territory story's card: the headline from the head's own claims, the confidence, the drivers checked, and
    (core-011) the territory id, its own direction and the drivers the checks supported or ruled out, all by code.
    The headline says what the change is set against (the primary `relative_to`: the other territories, national, or
    nothing); each extra comparison adds "..., down X since before Metacora launched" and each extra measure its own
    sentence (FR-000e). The direction is the primary's."""
    supported, ruled_out = driver_calls(checks)
    kind = facts.get("relative", "other_territories")
    subject = f"{name} new patients (NBRx)" if measure == "nbrx" else name

    def clause(kind: str, word: str, pct: str) -> str:
        peers = {"up": f"up {pct}", "down": f"down {pct}"}.get(word, f"flat ({pct})")
        return f"{'the other territories were' if kind == 'other_territories' else 'national was'} {peers}"

    tail = ""
    if kind != "none" and facts.get("peer_word") is not None:
        tail = f", while {clause(kind, facts['peer_word'], facts['peer_pct'])}"
    for x in facts.get("relative_extra", []):
        tail += f" and {clause(x['kind'], x['word'], x['pct'])}"
    for x in facts.get("xc", []):
        tail += f", {x['word']} {x['pct']} {x['since']}" if x["word"] != "flat" else f", flat ({x['pct']}) {x['since']}"
    headline = f"{subject} {_verb(facts['word'], facts['pct'])} on the comparison weeks{tail}."
    if facts.get("xm"):
        x = facts["xm"]
        headline += f" {x['label'][:1].upper()}{x['label'][1:]} {_verb(x['word'], x['pct'])}."
    return {"headline": headline,
            "confidence": confidence, "drivers_checked": [DRIVER_NAMES.get(d, d) for d in drivers],
            "territory": territory, "direction": facts["word"], "drivers_supported": supported, "drivers_ruled_out": ruled_out, "cut": None}


def competitor_card(p, facts: dict) -> dict:
    """The competitor story is a national card (brief-010 FR-006): territory NATIONAL, no cut, the national competitor
    check's verdict, and the direction of BXA's basket share on the comparison weeks (house flat band) with each
    measure's direction in `directions` (bxa_share, competitor_share; no trx, national TRx lives in the KPI strip). `facts` comes from competitor_status."""
    d = facts.get("directions") or {}
    # The headline keeps its measured length: MEASURED_ANCHORS (the word budget) counts it.
    headline = f"Metacora holds {facts['bxe']} of the four-brand basket, and {p.brand_id} holds {facts['bxa']}."
    check = facts.get("check")
    supported, ruled_out = driver_calls([check] if check else [])
    ruled_out += [x for x in facts.get("ruled_out") or [] if x not in ruled_out]  # access, promotion, supply: every territory ruled it out
    return {"headline": headline, "confidence": "Medium",
            "drivers_checked": [DRIVER_NAMES[x] for x in ["competitor"] + [r for r in ruled_out if r != "competitor"]],
            "territory": "NATIONAL", "direction": d.get("bxa_share"), "directions": dict(d), "drivers_supported": supported,
            "drivers_ruled_out": ruled_out, "cut": None}


_DRIVER_ORDER = ("data", "access", "promotion", "supply", "competitor")


def cut_checks(reg: Registry, p, territory: str, plan: str, checks=None) -> list:
    """The checks a cut card stands on (brief-010 FR-001): the territory story's own, with the access check scoped to
    the plan (an access change on this plan, lined up with its TRx). Data, promotion, supply and competitor have no
    plan scope, so the card reuses the territory's verdicts. `checks` are the story's, when it ran them; otherwise
    the same checks run here."""
    from .lag_checks import check_access, run_checks

    complete = bool(checks) and {c.driver for c in checks} >= set(_DRIVER_ORDER)
    own = list(checks) if complete else run_checks(reg, territory, p.weeks, p.baseline, brand_id=p.brand_id,
                                                    use_selected_baseline=p.comparison is not None)
    with reg.under(measure="trx"):  # the access check reads TRx whatever the primary measure
        access = check_access(reg, territory, p.weeks, p.baseline, plan=plan)
    by = {c.driver: c for c in own}
    by["access"] = access
    return [by[d] for d in _DRIVER_ORDER if d in by]


def cut_card(p, territory: str, plan: str, figures: dict, checks: list) -> dict:
    """A plan cut card (core-011 FR-017; brief-010 FR-001): the territory, the cut `plan:<id>`, the plan's direction on
    the primary measure and on each measure the definition holds (`directions`), the drivers its checks support or rule
    out, and a headline with claim tokens and the plan's readable name. Built by code."""
    supported, ruled_out = driver_calls(checks)
    first = figures["measures"][0]
    where, name = q.name(territory), splits.readable(plan)
    name = name[:1].upper() + name[1:]
    verb = {"up": "rose from", "down": "fell from"}.get(first["word"], "held flat from")
    against = figures["territory_word"] != first["word"] and "flat" not in (first["word"], figures["territory_word"])
    peers = {"up": f"rose {figures['territory_pct']}", "down": f"fell {figures['territory_pct']}"}.get(
        figures["territory_word"], f"held flat ({figures['territory_pct']})")
    headline = (f"{name} in {where} {verb} {first['before']} to {first['after']} {first['label']} a week "
                f"({first['word']} {first['pct']}){', while' if against else ', and'} {where} {peers}.")
    return {"headline": headline, "confidence": confidence(checks)[0], "drivers_checked": [DRIVER_NAMES[c.driver] for c in checks],
            "territory": territory, "cut": f"plan:{plan}", "direction": first["word"],
            "directions": {m["measure"]: m["word"] for m in figures["measures"]},
            "drivers_supported": supported, "drivers_ruled_out": ruled_out}


def cut_block(reg: Registry, p, cut: dict, checks=None) -> StoryBlock:
    """A cut card as a story block (§3, after its territory's story): the plan's level before and after and its change
    for each measure the definition holds, its closing confidence, and the checks folded under the card. The text
    reaches the scored answer (FR-009); every number is a claim token."""
    territory, plan = cut["territory"], cut["plan"]
    figures = splits.cut_figures(reg, p, territory, plan)
    done = cut_checks(reg, p, territory, plan, checks)
    card = cut_card(p, territory, plan, figures, done)
    where, name = q.name(territory), splits.readable(plan)
    name = name[:1].upper() + name[1:]
    lines = []
    for i, m in enumerate(figures["measures"]):
        lead = f"{name} in {where}: {p.brand_id} {m['label']}" if i == 0 else m["label"][:1].upper() + m["label"][1:]
        lines.append(f"{lead} averaged {m['after']} a week on the comparison weeks against {m['before']} before ({m['word']} {m['pct']}).")
    level, lead = confidence(done)
    lines.append(f"Confidence: {level}. Unresolved, investigate next. No driver is named." if level == "Low" else
                 f"Confidence: {level}. {'Leading driver' if level == 'High' else 'Candidate drivers'}: {lead}.")
    detail = ["Checked for this plan, in this order:"] + [f"- {c.text}" for c in done]
    detail.append(f"Data, promotion, supply and competitor have no plan-level test, so they carry the {where} verdicts.")
    return StoryBlock(f"cut:{plan}", f"{name} in {where}", lines, card=card, detail=detail)


def story_detail(reg: Registry, p, territory: str) -> list[str]:
    """The splits, readable and rounded, for the story's folded detail."""
    return splits.readable_lines(reg, p, territory)


def restatement_block(restated: list[dict]) -> StoryBlock | None:
    """brief-010 FR-005: one card for the restated territory-week with the largest change (at most one a brief).
    `restated` is `stages.restatements(..., facts)`: each item holds claim tokens. The card is about the data, not a
    business move: drivers supported ["data"], direction the restatement's (up when the restated TRx is higher),
    cut None (the whole territory). A scorer matches it by territory like any card."""
    if not restated:
        return None
    r = max(restated, key=lambda x: x["size"])
    name = q.name(r["territory"])
    moved = {"up": f"up {r['pct']}", "down": f"down {r['pct']}"}.get(r["direction"], "unchanged")
    card = {"headline": f"{name} TRx for the week of {r['week']} was restated from {r['old']} to {r['new']} ({moved}).",
            "confidence": "High", "drivers_checked": [DRIVER_NAMES["data"]],
            "territory": r["territory"], "direction": r["direction"], "drivers_supported": ["data"],
            "drivers_ruled_out": [], "cut": None}
    line = (f"Data story: {name} restated its week of {r['week']} on {r['restated_on']}, from {r['old']} to {r['new']} TRx "
            f"({moved}). Confidence: High. Leading driver: data.")
    return StoryBlock(f"restatement:{r['territory']}:{r['week']}", f"{name} restatement", [line], card=card)
