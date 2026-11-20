"""Release-wide promotion evidence from territory aggregates and governed TRx."""
from __future__ import annotations

from dataclasses import dataclass, replace

from . import memo, queries as q, splits, stages
from .registry import Registry, digits_outside_tokens

PUSH_RATIO = 1.5
LAPSE_RATIO = 0.70
LAPSE_WEEKS = 3
PROMO = "raw.promo_activity"
METRICS = {"rep_calls_aggregated": "aggregated calls", "digital_impressions": "digital impressions",
           "samples_units": "samples", "speaker_programs": "speaker programs"}


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


def _push_lines(reg: Registry, focus: str | None) -> tuple[list[str], bool]:
    threshold = reg.claim("lookup_promo", f"select {PUSH_RATIO} from {PROMO} limit 1", "dec2", rule="push threshold")
    lines = [f"Push threshold: above {threshold} times the territory's release median."]
    sustained = False
    for territory in _territories(reg, focus):
        cells = _cells(territory)
        fields = []
        for column, label in METRICS.items():
            median = f"(select median({column}) {cells})"
            # For sparse events, count a spike when the activity exceeds one and its normal level.
            floor = f"{PUSH_RATIO} * {median}" if column in ("rep_calls_aggregated", "digital_impressions") else (
                f"greatest(1, {PUSH_RATIO} * {median})")
            longest_sql = f"""
                select coalesce(max(n), 0) from (
                    select count(*) n from (
                        select date_diff('week', date '2000-01-03', week_start)
                            - row_number() over (order by week_start) as run
                        {cells} and {column} > {floor}
                    ) group by run
                )
            """
            longest = reg.claim("lookup_promo", longest_sql, "int", territory=territory, measure=column)
            if column in ("rep_calls_aggregated", "digital_impressions"):
                peak = reg.claim("lookup_promo", f"select max({column}) / nullif({median}, 0) {cells}", "dec2",
                                 territory=territory, measure=column)
                fields.append(f"{label} peaked at {peak} times median, longest push {longest} weeks")
                sustained |= reg.scalar(longest_sql) >= 2
            else:
                fields.append(f"{label} longest spike {longest} weeks")
        lines.append(f"- {q.name(territory)}. " + ". ".join(fields) + ".")
    return lines, sustained


def _reportable(reg: Registry, weeks: list[str]) -> list[str]:
    return [r[0] for r in reg.rows(
        f"select territory_id from reporting.v_feed_health where week_start in {q._dates(weeks)} "
        f"and health_status = 'PASS' group by 1 having count(distinct week_start) = {len(weeks)} order by 1")]


def _lapse_lines(reg: Registry, p: stages.Period, lapse: Lapse) -> list[str]:
    t = lapse.territory
    W = q.mondays(lapse.start, lapse.end)
    B = [q.shift(lapse.start, -i) for i in range(stages.BASELINE_WEEKS, 0, -1)]
    fields = {"territory": t, "lapse_start": lapse.start, "lapse_end": lapse.end}
    before = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", B, t), "int", **fields)
    during = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", W, t), "int", **fields)
    digital = reg.claim("lookup_promo", q.context_mean("promo_activity", "digital_impressions", W, t), "int", **fields)
    median = reg.claim("lookup_promo", f"select median(digital_impressions) {_cells(t)}", "int", **fields)
    lines = [f"{q.name(t)} lapse from {lapse.start} to {lapse.end}. Aggregated calls averaged {before} a week before "
             f"and {during} during. Digital impressions averaged {digital} against a release median of {median}."]
    ok = _reportable(reg, B + W)
    peers = [other for other in ok if other != t]
    if t in ok and peers:
        period = replace(p, weeks=W, baseline=B, ok=ok)
        lines.append(stages.territory_change(reg, period, t))
        actual, baseline = q.mean_weekly(W, terrs=[t]), q.mean_weekly(B, terrs=[t])
        peer_pct = q.pct_change(q.mean_weekly(W, terrs=peers), q.mean_weekly(B, terrs=peers))
        gap = reg.claim("get_metric", f"select {q.sub(actual)} - {q.sub(baseline)} * (1 + {q.sub(peer_pct)} / 100)",
                        "int", metric="weekly TRx gap vs peer trend", **fields)
        lines.append(f"Weekly TRx gap against the other territories' trend: {gap}. This is an association.")
        lines.extend(splits.story_lines(reg, period, t))
    else:
        lines.append("The feed gate leaves too little like-for-like TRx for this lapse.")
    if lapse.resumed:
        weeks = [lapse.end, lapse.resumed]
        ok = _reportable(reg, weeks)
        if t in ok:
            first, last = [reg.claim("get_metric", q.trx_sum([w], terrs=[t]), "int", week=w, territory=t) for w in weeks]
            lines.append(f"When aggregated calls returned on {lapse.resumed}, BXA TRx went from {first} to {last}.")
            peers = [other for other in ok if other != t]
            if peers:
                change_sql = q.pct_change(q.trx_sum([weeks[1]], terrs=peers), q.trx_sum([weeks[0]], terrs=peers))
                move = reg.claim("get_metric", change_sql, "pct1", scope="other territories", weeks=weeks)
                lines.append(f"The other territories were {stages.word(reg.scalar(change_sql))} {move} over the same weeks.")
    return lines


def story_blocks(reg: Registry, p: stages.Period) -> list[memo.StoryBlock]:
    if not p.promotion:
        return []
    if not p.promotion_review and p.focus in (None, "NATIONAL"):
        return []
    events = [lapse for lapse in lapses(reg, p.focus) if p.promotion_review or (
        lapse.start <= p.requested[-1] and (lapse.resumed or lapse.end) >= p.requested[0])]
    blocks = [memo.StoryBlock(f"promotion:{lapse.territory}:{lapse.start}", f"{q.name(lapse.territory)} promotion lapse",
                              _lapse_lines(reg, p, lapse)) for lapse in events]
    if not blocks and not p.promotion_review:
        blocks.append(memo.StoryBlock(f"promotion:{p.focus}", f"{q.name(p.focus)} promotion evidence",
                                     ["No detected coverage lapse or return overlaps the requested weeks."]))
    return blocks


def render_review(reg: Registry, p: stages.Period) -> dict:
    push, sustained = _push_lines(reg, p.focus)
    stories = story_blocks(reg, p)
    terr = f" and territory_id = '{p.focus}'" if p.focus not in (None, "NATIONAL") else ""
    corr = reg.claim("lookup_promo", f"select corr(rep_calls_aggregated, digital_impressions) from {PROMO} "
                     f"where product_id = 'BXA'{terr}", "dec2", scope=p.focus or "release")
    parts = memo.MemoParts(
        title=["# BXA Promotion review", f"Scope: {stages.describe(p)}. {q.name(p.focus or 'NATIONAL')}."],
        bottom_line=["A sustained push was recorded." if sustained else
                     "Aggregated calls and digital impressions show no sustained push above the threshold.",
                     "Lapse and return comparisons describe associations in territory-level data."],
        numbers=push,
        limits=["The release has no spend data. A dollar return and a channel ranking require spend and independent variation.",
                f"The release correlation between aggregated calls and digital impressions is {corr}. "
                "Their movements cannot isolate the effect of either channel.",
                "Confidence is Medium where a lapse aligns with reportable TRx. Aggregated activity leaves individual reach unknown."],
        next_checks=["Discuss coverage backfill with sales operations at territory level.",
                     "Owner: sales operations. Run a territory holdout with a planned comparison. "
                     "Re-read after four weeks to decide whether to change coverage or campaign timing."],
        appendix=memo.appendix(reg, p=p) + [f"- Review scope: {p.note}",
                                         "- Lapse comparison: four prior weeks and the same weeks in reportable peers."],
        stories=stories, story_notes=[] if stories else ["No sustained coverage lapse was found in this scope."])
    template, sections = memo.compose(parts)
    if (bad := digits_outside_tokens(template)):
        raise AssertionError(f"digit outside a claim token: {bad[:3]}")
    answer, citations = reg.render_cited(template)
    return {"answer": answer, "claims": reg.claims, "evidence": reg.evidence, "citations": citations,
            "sections": memo.render_sections(sections, reg.claims), "abstained": False}
