"""The weekly brief as a memo with a fixed outline (brief-003 User Story 2, FR-004, FR-020, FR-021).

    §1 Bottom line · §2 The numbers · §3 What changed and why (§3.1, §3.2 …) · §4 What the data can't tell us
    · §5 Next checks · §6 Appendix

Code builds every section and every number; the writer (agent) or nothing (scripted) adds prose: the §1
answer and one sentence per story. Both Briefing engines compose through `compose`, so they emit the same
skeleton. Headings carry no digits (research R6): section numbers live in the structured `sections`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import queries as q
from . import stages
from .checks import DECISION, OWNER, launch_date
from .lag_checks import LAG_LABELS
from .projection import Projection, _label, method_lines
from .registry import Registry
from . import splits
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
    card: dict | None = None  # brief-008: {headline, confidence, drivers_checked}; tokens allowed in the headline
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


def compose(parts: MemoParts) -> tuple[str, list[dict]]:
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


def _like_for_like(reg: Registry, p, facts: dict | None = None) -> str:
    W, B, ok = p.weeks, p.baseline, p.ok
    if not ok:
        return "No like-for-like change is given: no territory passes the feed gate in every week compared."
    if not B:
        return "No like-for-like change is given: the release has no earlier weeks to compare with."
    cur, base = q.mean_weekly(W, terrs=ok, product=p.brand_id), q.mean_weekly(B, terrs=ok, product=p.brand_id)
    change = reg.scalar(q.pct_change(cur, base)) or 0
    n = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} "
                  f"and {q._in('territory_id', ok)}", "int")
    total = reg.claim("get_metric", "select count(*) from raw.dim_territory", "int")
    pct = reg.claim("get_metric", q.pct_change(cur, base), "pct1", scope="like-for-like national")
    if facts is not None:
        facts["like"] = {"n": n, "total": total, "pct": pct, "word": stages.word(change)}
    return f"Like for like on {n} of {total} territories, {p.brand_id} TRx is {stages.word(change)} {pct} against {comparison_text(p)}."


def comparison_text(p) -> str:
    """The comparison weeks in words and dates, with no other digit (brief-007 FR-004)."""
    B = p.baseline
    if not B:
        return "no earlier weeks, because the release starts with this period"
    if len(B) == 1:
        return f"the week of {B[0]}"
    if p.comparison is not None:
        if p.comparison.kind == "last_year":
            return f"the same weeks last year ({', '.join(B)})"
        return f"the weeks from {B[0]} to {B[-1]}"
    return f"the {_WORDS.get(len(B), 'several')} weeks before ({B[0]} to {B[-1]})"


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
        x, b = q.mean_weekly(p.weeks, terrs=[t], product=p.brand_id), q.mean_weekly(p.baseline, terrs=[t], product=p.brand_id)
        change = reg.scalar(q.pct_change(x, b)) or 0
        pct = reg.claim("get_metric", q.pct_change(x, b), "pct1", territory=t)
        return (f"Least sure: the {q.name(t)} change ({stages.word(change)} {pct}); its confidence, {s['confidence']}, "
                "is the lowest of this brief's stories.")
    if len(p.weeks) == 1 and p.baseline:
        w = p.weeks[0]
        prev = q.shift(w, -1)
        sql = q.pct_change(q.trx_sum([w], product=p.brand_id), q.trx_sum([prev], product=p.brand_id))
        change = reg.scalar(sql) or 0
        pct = reg.claim("get_metric", sql, "pct1", scope="week over week, reportable cuts")
        return (f"Least sure: the week-over-week change ({stages.word(change)} {pct}), "
                "because it compares one week with one week.")
    if p.ok and p.baseline:
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
    if proj.national is None:
        lines.append("This period cannot be reported nationally: no territory's feed can be read.")
    elif len(W) == 1:
        lines.append(f"Projected national {p.brand_id} TRx is {proj.national} for the week of {W[0]}.")
    else:
        lines.append(f"Projected national {p.brand_id} TRx averaged {proj.national} a week from {W[0]} to {W[-1]}.")
    facts["national"], facts["brand"] = proj.national, p.brand_id
    lines.append(_like_for_like(reg, p, facts))
    share = reg.claim("compare_competitors", q.share(W, p.brand_id), "pct1", product=p.brand_id)
    facts["share"] = share
    lines.append(f"{p.brand_id} held {share} of the four-brand market basket.")
    launched = launch_date(reg)
    if launched is not None and launched <= W[-1] and p.brand_id == "BXA":
        pre = [q.shift(launched, -i) for i in range(4, 0, -1)]
        facts["pre"] = reg.claim("compare_competitors", q.share(pre, p.brand_id), "pct1", product=p.brand_id, weeks="before launch")
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


def appendix(reg: Registry, brand_id: str = "BXA", *, p=None, proj: Projection | None = None) -> list[str]:
    """§6 text: the data version and the Assumptions block. The method and the glossary are folded (compose)."""
    brand_id = briefing_brand(p.brand_id if p is not None else brand_id)
    lines = [f"Data version {reg.data_version}. Product: {brand_id} ({PRODUCTS[brand_id]}), synthetic data."]
    return lines + (assumptions(p, proj) if p is not None else [])


def assumptions(p, proj: Projection | None) -> list[str]:
    """The Assumptions block (brief-007 FR-012; the Week 6 assumption book): each assumption with its source, in
    at most five items (brief-008 FR-004)."""
    source = "the brief's default rule, the four weeks before the period" if p.comparison is None else p.baseline_source
    fewer = (f" The release starts on {p.first}, so fewer weeks exist."
             if p.comparison is None and p.baseline and len(p.baseline) < stages.BASELINE_WEEKS else "")
    lines = ["Assumptions:", f"- Comparison weeks: {comparison_text(p)}. Source: {source}.{fewer}"]
    lines.append("- Like for like: changes use only territories whose feed passed the gate in every week compared. "
                 "Withheld cuts are left out of every change and story, and never read as zero demand."
                 + (" Calendar weeks are left out of the stories." if p.calendar_note else "") + " Source: the feed gate.")
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


def next_checks(p, stories: list[dict], competitor: bool) -> list[str]:
    """§5 (research R10): one line per territory story ({territory, confidence, drivers}), per withheld cut,
    and for a continuing competitor story."""
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
    """The §2 territory table (brief-008 FR-001): TRx, the change on the comparison weeks and, for a one-week
    period only (FR-011), the change on the week before. Values are claim tokens already in the detail."""
    if proj.national is None:
        return None
    single, changes = len(proj.weeks) == 1, {c["territory"]: c for c in facts.get("changes", [])}
    has_change = bool(p.baseline) and bool(changes)
    columns = ["Territory", f"{p.brand_id} TRx" + ("" if single else " a week")]
    if has_change and single:
        columns.append("On the week before")
    if has_change:
        columns.append("On the comparison weeks")
    columns.append("Basis")
    rows = []
    for r in proj.rows:
        c = changes.get(r.territory) or {}
        cells = [q.name(r.territory), r.token]
        if has_change and single:
            cells.append(_change_cell(c.get("wow")))
        if has_change:
            cells.append(_change_cell(c.get("base")))
        rows.append({"cells": cells + [r.basis], "basis": r.basis})
    shown = {r.territory for r in proj.rows}
    for t in sorted(set(p.terrs) - shown, key=q.name):
        rows.append({"cells": [q.name(t)] + ["withheld"] * (len(columns) - 1), "basis": "withheld"})
    notes = []
    if has_change:
        notes.append(f"Change is against {comparison_text(p)}.")
        if any(not c["ok"] for c in changes.values()):
            notes.append("No change is given where a week compared failed the feed gate.")
    if any(r.basis != "observed" for r in proj.rows):
        notes.append("A projected or estimated level is an assumption, not an observed count.")
    return {"columns": columns, "rows": rows, "note": " ".join(notes) or None}


def numbers(proj: Projection, facts: dict, restatement_lines: list[str], p=None) -> dict:
    """§2 as {lines, detail, territory_table}: the scope line, short sentences on the like-for-like change, the
    week over week (a one-week period only), the largest moves, any data artifact, calendar effects and
    restatements (research R7). The territory levels and changes are the table; the same claims, one sentence
    a territory, are the folded detail so the scored answer keeps every number."""
    lines = [scope_line(p, proj)] if p is not None else []
    brand = proj.brand_id
    if proj.national is None:
        lines.append("No projected national is given: no territory in these weeks can be read.")
    avg = facts.get("avg")
    if avg is None:
        lines.append("No like-for-like national figure is given: no territory passes the feed gate in every one of these weeks.")
    elif avg.get("pct"):
        lines.append(f"Like for like, {brand} TRx averaged {avg['avg']} a week across {avg['n']} of {avg['total']} territories, "
                     f"{avg['word']} {avg['pct']} against the comparison weeks.")
    else:
        lines.append(f"Like for like, {brand} TRx averaged {avg['avg']} a week across {avg['n']} of {avg['total']} territories.")
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
    if proj.national is not None:
        single, changes = len(proj.weeks) == 1, {c["territory"]: c for c in facts.get("changes", [])}
        marked = any(r.basis != "observed" for r in proj.rows)
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
            detail.append(f"{q.name(r.territory)}: {r.token} {brand} TRx a week{_label(r, single)}" + (f"; {'; '.join(parts)}." if parts else "."))
    return {"lines": lines, "detail": detail, "territory_table": territory_table(p, proj, facts) if p is not None else None}


# Blocks of §1 and the story cards (brief-008 FR-001) -------------------------------------------------------

def kpis(p, proj: Projection, facts: dict) -> list[dict]:
    """The §1 KPI strip, in order: national TRx, the like-for-like change, the basket share, territories
    reportable. Each value is a claim already in §1's text; a tile with no claim behind it is left out."""
    W, tiles = proj.weeks, []
    if facts.get("national"):
        when = f"projected, week of {W[0]}" if len(W) == 1 else f"projected, a week, {W[0]} to {W[-1]}"
        tiles.append({"label": f"National {p.brand_id} TRx", "value": facts["national"], "detail": when, "direction": None})
    like = facts.get("like")
    if like:
        tiles.append({"label": "Change on the comparison weeks", "value": like["pct"],
                      "detail": f"like for like, against {comparison_text(p)}", "direction": like["word"]})
    if facts.get("share"):
        tiles.append({"label": f"{p.brand_id} basket share", "value": facts["share"],
                      "detail": "of the four-brand basket" + (f", against {facts['pre']} before launch" if facts.get("pre") else ""),
                      "direction": facts.get("share_word")})
    if like:
        tiles.append({"label": "Territories reportable", "value": like["n"], "detail": f"of {like['total']}, like for like",
                      "direction": None})
    return tiles


def bottom_detail(facts: dict) -> list[str]:
    """§1's folded line: the share before launch, which the basket tile quotes."""
    return [f"Before Metacora launched, {facts['brand']} held {facts['pre']} of the four-brand basket."] if facts.get("pre") else []


def _verb(word: str, token: str, rose: str = "rose", fell: str = "fell") -> str:
    return {"up": f"{rose} {token}", "down": f"{fell} {token}"}.get(word, f"held flat ({token})")


def story_card(name: str, facts: dict, confidence: str, drivers: list[str]) -> dict:
    """A territory story's card: the headline from the head's own claims, the confidence, the drivers checked."""
    peers = {"up": f"up {facts['peer_pct']}", "down": f"down {facts['peer_pct']}"}.get(facts["peer_word"], f"flat ({facts['peer_pct']})")
    return {"headline": f"{name} {_verb(facts['word'], facts['pct'])} on the comparison weeks, while the other territories were {peers}.",
            "confidence": confidence, "drivers_checked": [DRIVER_NAMES.get(d, d) for d in drivers]}


def competitor_card(p, facts: dict) -> dict:
    return {"headline": f"Metacora holds {facts['bxe']} of the four-brand basket, and {p.brand_id} holds {facts['bxa']}.",
            "confidence": "Medium", "drivers_checked": []}


def story_detail(reg: Registry, p, territory: str) -> list[str]:
    """The splits, readable and rounded, for the story's folded detail."""
    return splits.readable_lines(reg, p, territory)
