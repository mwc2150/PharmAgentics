"""Release-wide promotion evidence from territory aggregates and governed TRx."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from . import memo, queries as q, splits, stages
from .registry import Registry, digits_outside_tokens

PUSH_RATIO = 1.5
LAPSE_RATIO = 0.70
LAPSE_WEEKS = 3
PROMO = "raw.promo_activity"
# A question about where money should go is answered from what the release can and cannot say about spend.
# Code decides this from the words, never a model (brief-008 FR-010).
_DOLLAR = re.compile(r"\b(?:next dollars?|dollars?|spend|budget|invest(?:ment|ing)?|ROI|return on investment|"
                     r"(?:re)?allocat\w*)\b", re.I)
_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}


def is_dollar_question(question: str) -> bool:
    """True for "Where should the next dollar go?" and its kin. A "Promotion review in X:" prefix is not read."""
    return bool(_DOLLAR.search(question.split(":", 1)[-1]))


@dataclass(frozen=True)
class Lapse:
    territory: str
    start: str
    end: str
    resumed: str | None


def _territories(reg: Registry, focus: str | None) -> list[str]:
    return [r[0] for r in reg.rows(f"select distinct territory_id from {PROMO} where product_id = 'BXA' order by 1")
            if focus in (None, "NATIONAL", r[0])]


def _cells(territory: str) -> str:
    return f"from {PROMO} where product_id = 'BXA' and territory_id = '{territory}'"


def lapses(reg: Registry, focus: str | None) -> list[Lapse]:
    found = []
    for territory in _territories(reg, focus):
        cells = _cells(territory)
        rows = reg.rows(f"""
            with low as (
                select week_start, date_diff('week', date '2000-01-03', week_start)
                    - row_number() over (order by week_start) as run
                {cells} and rep_calls_aggregated < {LAPSE_RATIO}
                    * (select median(rep_calls_aggregated) {cells})
            )
            select min(week_start)::varchar, max(week_start)::varchar
            from low group by run having count(*) >= {LAPSE_WEEKS} order by 1
        """)
        for start, end in rows:
            next_week = q.shift(end, 1)
            resumed = reg.scalar(f"select week_start::varchar {cells} and week_start = date '{next_week}' "
                                 f"and rep_calls_aggregated >= {LAPSE_RATIO} * (select median(rep_calls_aggregated) {cells})")
            found.append(Lapse(territory, start, end, resumed))
    return sorted(found, key=lambda event: (event.start, event.territory))



def _scope_sql(focus: str | None) -> str:
    return f" and territory_id = '{focus}'" if focus not in (None, "NATIONAL") else ""


def _runs_sql(focus: str | None) -> str:
    """Every lapse as a row (territory_id, first_week, last_week, n), the same rule as `lapses`, over all territories."""
    return f"""
        with cells as (
            select territory_id, week_start, rep_calls_aggregated,
                median(rep_calls_aggregated) over (partition by territory_id) as med
            from {PROMO} where product_id = 'BXA'{_scope_sql(focus)}
        ), low as (
            select territory_id, week_start, date_diff('week', date '2000-01-03', week_start)
                - row_number() over (partition by territory_id order by week_start) as run
            from cells where rep_calls_aggregated < {LAPSE_RATIO} * med
        ), runs as (
            select territory_id, min(week_start) as first_week, max(week_start) as last_week, count(*) as n
            from low group by territory_id, run having count(*) >= {LAPSE_WEEKS}
        )
    """


def _claim(reg: Registry, sql: str, fmt: str, **params) -> tuple[str, float]:
    """A claim token and the value behind it, so code can pick words (a plural, a direction) without a digit."""
    return reg.claim("lookup_promo", sql, fmt, **params), float(reg.scalar(sql) or 0)


def _weeks(token: str, value: float) -> str:
    return "none" if not value else f"{token} {'week' if value == 1 else 'weeks'}"


def _count_word(n: int) -> str:
    return _NUMBER_WORDS.get(n, "several")


def _push_rows(reg: Registry, focus: str | None) -> list[dict]:
    """One row a territory: the highest week as a multiple of the median for calls and impressions, and the longest
    run above the push line for calls or impressions, samples and speaker programs. Claims, with the values."""
    out = []
    for territory in _territories(reg, focus):
        cells, row = _cells(territory), {"territory": territory}
        longest = {}
        for key, column in (("calls", "rep_calls_aggregated"), ("digital", "digital_impressions"),
                            ("samples", "samples_units"), ("speakers", "speaker_programs")):
            median = f"(select median({column}) {cells})"
            # For sparse events, count a spike when the activity exceeds one and its normal level.
            floor = f"{PUSH_RATIO} * {median}" if key in ("calls", "digital") else f"greatest(1, {PUSH_RATIO} * {median})"
            longest[key] = f"""
                select coalesce(max(n), 0) from (
                    select count(*) n from (
                        select date_diff('week', date '2000-01-03', week_start)
                            - row_number() over (order by week_start) as run
                        {cells} and {column} > {floor}
                    ) group by run
                )
            """
            if key in ("calls", "digital"):
                row[f"{key}_peak"] = _claim(reg, f"select max({column}) / nullif({median}, 0) {cells}", "dec2",
                                            territory=territory, measure=column)
        row["push"] = _claim(reg, f"select greatest(coalesce(({longest['calls']}), 0), coalesce(({longest['digital']}), 0))",
                             "int", territory=territory, measure="calls or digital impressions", kind="longest push")
        for key, column in (("samples", "samples_units"), ("speakers", "speaker_programs")):
            row[key] = _claim(reg, longest[key], "int", territory=territory, measure=column, kind="longest spike")
        out.append(row)
    return out


def _table(rows: list[dict], threshold: str) -> dict | None:
    if not rows:
        return None
    columns = ["Territory", "Calls peak (times median)", "Digital peak (times median)", "Longest push", "Sample spike",
               "Speaker programs"]
    cells = lambda r: [q.name(r["territory"]), r["calls_peak"][0], r["digital_peak"][0], _weeks(*r["push"]),
                       _weeks(*r["samples"]), _weeks(*r["speakers"])]
    return {"columns": columns, "rows": [{"cells": cells(r), "basis": "observed"} for r in rows],
            "note": f"A push is a week above {threshold} times the territory's own median across the release."}


def _push_detail(rows: list[dict]) -> list[str]:
    lines = []
    for r in rows:
        lines.append(f"{q.name(r['territory'])}: aggregated calls peaked at {r['calls_peak'][0]} times the median and digital "
                     f"impressions at {r['digital_peak'][0]} times. Longest run above the push line: aggregated calls or digital "
                     f"impressions, {_weeks(*r['push'])}; samples, {_weeks(*r['samples'])}; speaker programs, {_weeks(*r['speakers'])}.")
    return lines


def _push_text(rows: list[dict], threshold: str) -> list[str]:
    if not rows:
        return []
    top_calls = max(rows, key=lambda r: r["calls_peak"][1])
    top_digital = max(rows, key=lambda r: r["digital_peak"][1])
    return [f"A push is a week when aggregated calls or digital impressions run above {threshold} times a territory's own median.",
            f"Aggregated calls peaked highest in {q.name(top_calls['territory'])} at {top_calls['calls_peak'][0]} times the median, "
            f"and digital impressions in {q.name(top_digital['territory'])} at {top_digital['digital_peak'][0]} times.",
            "Samples and speaker programs are sparse counts, so a spike is a week above one and above the push line."]


def _reportable(reg: Registry, weeks: list[str]) -> list[str]:
    return [r[0] for r in reg.rows(
        f"select territory_id from reporting.v_feed_health where week_start in {q._dates(weeks)} "
        f"and health_status = 'PASS' group by 1 having count(distinct week_start) = {len(weeks)} order by 1")]




def _direction(value: float, above: str, below: str) -> str:
    return below if value < 0 else above


def _segment_lines(reg: Registry, period: stages.Period, t: str) -> list[str]:
    """The channel and specialty movers of one lapse, in percent, against the four weeks before it (brief-010 FR-003).
    The lapse's own weeks first; a lapse longer than the four-week comparison is also read on its first four weeks, which
    is the window the golden answer reads (a coverage gap's early response, before the weeks that follow muddy it).
    A small cell is quoted with its flag here: this review is where cash is read as noisy rather than dropped."""
    lead = "Over the lapse"
    out = [splits.segment_line(reg, period, t, quote_small=True, lead=lead)]
    if len(period.weeks) > stages.BASELINE_WEEKS:
        out.append(splits.segment_line(reg, replace(period, weeks=period.weeks[:stages.BASELINE_WEEKS]), t, quote_small=True,
                                lead="In its first four weeks"))
    return [" ".join(x for x in out if x)] if any(out) else []


def _lapse_story(reg: Registry, p: stages.Period, lapse: Lapse, gaps: list[tuple[str, float]]) -> memo.StoryBlock:
    """One lapse as a short story: what calls and impressions did, what TRx did and what returned, a card, and the
    splits (readable, rounded) folded for analysts. A gap against peer trend, below zero, is appended to `gaps`."""
    t, name, brand = lapse.territory, q.name(lapse.territory), p.brand_id
    W = q.mondays(lapse.start, lapse.end)
    B = [q.shift(lapse.start, -i) for i in range(stages.BASELINE_WEEKS, 0, -1)]
    fields = {"territory": t, "lapse_start": lapse.start, "lapse_end": lapse.end}
    before = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", B, t), "int", **fields)
    during = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", W, t), "int", **fields)
    digital = reg.claim("lookup_promo", q.context_mean("promo_activity", "digital_impressions", W, t), "int", **fields)
    median = reg.claim("lookup_promo", f"select median(digital_impressions) {_cells(t)}", "int", **fields)
    lines = [f"From {lapse.start} to {lapse.end}, aggregated calls in {name} averaged {during} a week against {before} before. "
             f"Digital impressions averaged {digital} against a release median of {median}."]
    card = {"headline": f"{name}: aggregated calls fell from {before} to {during} a week.", "confidence": "Low",
            "drivers_checked": ["promotion"], "territory": t, "direction": "down",  # calls fell: the lapse itself
            "drivers_supported": [], "drivers_ruled_out": [], "cut": None}  # no TRx comparison: promotion is inconclusive
    detail: list[str] = []
    ok = _reportable(reg, B + W)
    peers = [other for other in ok if other != t]
    if t in ok and peers:
        period = replace(p, weeks=W, baseline=B, ok=ok)
        x, b = q.mean_weekly(W, terrs=[t], product=brand), q.mean_weekly(B, terrs=[t], product=brand)
        px, pb = q.mean_weekly(W, terrs=peers, product=brand), q.mean_weekly(B, terrs=peers, product=brand)
        change, peer = reg.scalar(q.pct_change(x, b)) or 0, reg.scalar(q.pct_change(px, pb)) or 0
        trx, base = reg.claim("get_metric", x, "int", **fields), reg.claim("get_metric", b, "int", **fields)
        pct = reg.claim("get_metric", q.pct_change(x, b), "pct1", **fields)
        peer_pct = reg.claim("get_metric", q.pct_change(px, pb), "pct1", scope="other territories", **fields)
        gap_sql = f"select {q.sub(x)} - {q.sub(b)} * (1 + {q.sub(q.pct_change(px, pb))} / 100)"
        gap_value = reg.scalar(gap_sql)  # None when the gap cannot be computed: promotion is then inconclusive
        below = gap_value is not None and gap_value < 0
        gap = reg.claim("get_metric", f"select abs({q.sub(gap_sql)})", "int", metric="weekly TRx gap vs peer trend", **fields)
        lines.append(f"{brand} TRx averaged {trx} a week during the lapse against {base} before ({stages.word(change)} {pct}), "
                     f"while the other territories were {stages.word(peer)} {peer_pct}. TRx ran {gap} a week "
                     f"{_direction(gap_value or 0, 'above', 'below')} the other territories' trend. This is an association.")
        if below:
            gaps.append((gap, abs(gap_value)))
        lines.extend(_segment_lines(reg, period, t))  # brief-010 FR-003
        verb = {"up": "rose", "down": "fell"}.get(stages.word(change), "held flat at")
        card.update(headline=f"{name}: aggregated calls fell from {before} to {during} a week, and {brand} TRx {verb} {pct}.",
                    confidence="Medium", direction=stages.word(change),  # the territory's own TRx move
                    # TRx below the other territories' trend is the association the brief tells (the gap it carries to the
                    # bottom line); TRx that kept pace with them rules the lapse out as the cause of a TRx move.
                    drivers_supported=["promotion"] if below else [],
                    drivers_ruled_out=["promotion"] if gap_value is not None and gap_value >= 0 else [])
        detail = splits.readable_lines(reg, period, t)
    else:
        lines.append("The feed gate leaves too little like-for-like TRx for this lapse.")
        card["direction"] = None  # no TRx claim was made, so the card names no direction
    if lapse.resumed:
        weeks = [lapse.end, lapse.resumed]
        ok = _reportable(reg, weeks)
        if t in ok:
            first, last = [reg.claim("get_metric", q.trx_sum([w], terrs=[t]), "int", week=w, territory=t) for w in weeks]
            line = f"When aggregated calls returned on {lapse.resumed}, {brand} TRx went from {first} to {last}"
            peers = [other for other in ok if other != t]
            if peers:
                change_sql = q.pct_change(q.trx_sum([weeks[1]], terrs=peers), q.trx_sum([weeks[0]], terrs=peers))
                move = reg.claim("get_metric", change_sql, "pct1", scope="other territories", weeks=weeks)
                line += f", while the other territories were {stages.word(reg.scalar(change_sql))} {move}"
            lines.append(line + ".")
    return memo.StoryBlock(f"promotion:{t}:{lapse.start}", f"{name} promotion lapse", lines, card=card, detail=detail)


def _stories(reg: Registry, p: stages.Period) -> tuple[list[memo.StoryBlock], list[tuple[str, float]]]:
    gaps: list[tuple[str, float]] = []
    if not p.promotion or (not p.promotion_review and p.focus in (None, "NATIONAL")):
        return [], gaps
    events = [lapse for lapse in lapses(reg, p.focus) if p.promotion_review or (
        lapse.start <= p.requested[-1] and (lapse.resumed or lapse.end) >= p.requested[0])]
    blocks = [_lapse_story(reg, p, lapse, gaps) for lapse in events]
    if not blocks and not p.promotion_review:
        blocks.append(memo.StoryBlock(f"promotion:{p.focus}", f"{q.name(p.focus)} promotion evidence",
                                     ["No detected coverage lapse or return overlaps the requested weeks."]))
    return blocks, gaps


def story_blocks(reg: Registry, p: stages.Period) -> list[memo.StoryBlock]:
    return _stories(reg, p)[0]


def _lapse_kpis(reg: Registry, focus: str | None, events: list[Lapse], threshold: str) -> tuple[list[dict], dict]:
    """The strip: territories with a lapse, the longest lapse in weeks, the push threshold. Counts come from the
    same rule as `lapses`, written as one query, so each tile is a claim."""
    runs, scope = _runs_sql(focus), _scope_sql(focus)
    count, _ = _claim(reg, runs + "select count(distinct territory_id) from runs", "int", scope=focus or "release", kind="territories with a lapse")
    total, total_n = _claim(reg, f"select count(distinct territory_id) from {PROMO} where product_id = 'BXA'{scope}", "int",
                            scope=focus or "release")
    weeks, w = _claim(reg, runs + "select coalesce(max(n), 0) from runs", "int", scope=focus or "release", kind="longest lapse in weeks")
    longest = max(events, key=lambda e: len(q.mondays(e.start, e.end))) if events else None
    tiles = [{"label": "Territories with a lapse", "value": count, "detail": f"of {total} reviewed", "direction": None},
             {"label": "Longest lapse, in weeks", "value": weeks,
              "detail": f"{q.name(longest.territory)}, {longest.start} to {longest.end}" if longest else "no lapse in this scope",
              "direction": None},
             {"label": "Push threshold", "value": threshold, "detail": "times a territory's median", "direction": None}]
    return tiles, {"count": count, "total": total, "total_n": total_n, "weeks": weeks, "w": w, "longest": longest}


def _bottom_line(dollar: bool, k: dict, rows: list[dict], threshold: str, corr: str, gaps: list[tuple[str, float]]) -> list[str]:
    """§1 answers the question asked. The reach question gets what the data can say about coverage; the dollar
    question gets what it cannot say about money, what a lapse cost, and the next step."""
    longest = k["longest"]
    sustained = [r for r in rows if r["push"][1] >= 2]
    if sustained:
        top = max(sustained, key=lambda r: r["push"][1])
        push = (f"A sustained push was recorded: aggregated calls or digital impressions stayed above {threshold} times the "
                f"median for {_weeks(*top['push'])} in {q.name(top['territory'])}.")
    else:
        push = (f"No territory held aggregated calls or digital impressions above {threshold} times its median for two "
                "weeks running, so no push was sustained.")
    if longest:
        lapse = (f"Aggregated calls fell well below normal for at least three weeks in {k['count']} of {k['total']} "
                 f"{'territory' if k['total_n'] == 1 else 'territories'}, longest in {q.name(longest.territory)} "
                 f"at {_weeks(k['weeks'], k['w'])}.")
    else:
        lapse = "No territory had a coverage lapse of three weeks or more in this scope."
    if not dollar:
        return [lapse, push, "The release counts calls and impressions by territory, so it shows where coverage lapsed, "
                "not which people were reached. Lapse and return comparisons describe associations in territory-level data."]
    lines = ["The release cannot say where the next dollar should go. It has no spend data, so it cannot rank channels or price a dollar.",
             f"Aggregated calls and digital impressions moved together (correlation {corr}), so the data cannot separate their effects.", push]
    if gaps:
        lo, hi = min(gaps, key=lambda g: g[1]), max(gaps, key=lambda g: g[1])
        size = lo[0] if lo is hi else f"{lo[0]} to {hi[0]}"
        lines.append(f"What the data does show is the cost of a coverage lapse: TRx ran about {size} a week below the other "
                     f"territories' trend in the {_count_word(len(gaps))} {'lapse' if len(gaps) == 1 else 'lapses'} with a like-for-like read. "
                     "This is an association, not a return on spend.")
    else:
        lines.append(lapse)
    lines.append("The next step is to discuss coverage backfill with sales operations at territory level.")
    return lines


def _appendix(reg: Registry, p: stages.Period, threshold: str) -> list[str]:
    ratio = reg.claim("lookup_promo", f"select {LAPSE_RATIO} from {PROMO} limit 1", "dec2", rule="lapse threshold")
    scope = p.note or f"{stages.describe(p)}."
    return memo.appendix(reg, p.brand_id) + [
        "Assumptions:",
        f"- Review scope: {scope} It reads aggregates by territory only, never an individual. Source: the Promotion review rule.",
        f"- Lapse: aggregated calls below {ratio} times a territory's own median for at least three weeks running. "
        "The comparison is the four weeks before the lapse, and the same weeks in the other territories whose feed passed the gate. Source: the Promotion review rule.",
        f"- Push: a week above {threshold} times the territory's median. Samples and speaker programs are sparse, so a spike is above one and above that line. Source: the Promotion review rule.",
        "- Like for like: changes use only territories whose feed passed the gate in every week compared. "
        "Withheld cuts are left out and never read as zero demand. Source: the feed gate."]


def render_review(reg: Registry, p: stages.Period) -> dict:
    threshold = reg.claim("lookup_promo", f"select {PUSH_RATIO} from {PROMO} limit 1", "dec2", rule="push threshold")
    rows = _push_rows(reg, p.focus)
    stories, gaps = _stories(reg, p)
    corr = reg.claim("lookup_promo", f"select corr(rep_calls_aggregated, digital_impressions) from {PROMO} "
                     f"where product_id = 'BXA'{_scope_sql(p.focus)}", "dec2", scope=p.focus or "release")
    tiles, k = _lapse_kpis(reg, p.focus, lapses(reg, p.focus), threshold)
    parts = memo.MemoParts(
        title=["# BXA Promotion review", f"Scope: {stages.describe(p)}. {q.name(p.focus or 'NATIONAL')}."],
        bottom_line=_bottom_line(is_dollar_question(p.question), k, rows, threshold, corr, gaps),
        numbers=_push_text(rows, threshold),
        limits=[f"The release has no spend data, so a dollar return and a channel ranking cannot be given. Aggregated calls and "
                f"digital impressions moved together (correlation {corr}), so neither channel's effect can be isolated.",
                "Confidence is Medium where a lapse aligns with reportable TRx. Aggregated activity leaves individual reach unknown."],
        next_checks=["Discuss coverage backfill with sales operations at territory level.",
                     "Owner: sales operations. Run a territory holdout with a planned comparison. "
                     "Re-read four weeks after any change to decide whether to change coverage or campaign timing."],
        appendix=_appendix(reg, p, threshold),
        stories=stories, story_notes=[] if stories else ["No sustained coverage lapse was found in this scope."],
        kpis=tiles, territory_table=_table(rows, threshold), details={"2": _push_detail(rows)})
    template, sections = memo.compose(parts)
    if (bad := digits_outside_tokens(template)):
        raise AssertionError(f"digit outside a claim token: {bad[:3]}")
    answer, citations = reg.render_cited(template)
    return {"answer": answer, "claims": reg.claims, "evidence": reg.evidence, "citations": citations,
            "sections": memo.render_sections(sections, reg.claims), "abstained": False}
