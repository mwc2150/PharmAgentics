"""Additive cuts of the reportable weekly TRx change in one territory story."""
from __future__ import annotations

from . import queries as q
from .checks import access_events
from .lag_checks import check_access
from .registry import Registry
from .stages import Period, measure_label, word

SPLITS = {"plan": "plan_id", "specialty": "hcp_specialty", "channel": "payer_channel"}
SMALL_CELL = 50


_NUMBERS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
_ENUMS = {"MEDICARE_PART_D": "Medicare Part D", "MEDICAID": "Medicaid"}


def readable(cut: str) -> str:
    """A plan, specialty or channel as a reader says it: SYN_SOUTHEAST_COMMERCIAL_1 is "Commercial plan one",
    PRIMARY_CARE is "primary care". No digit survives, so the brief's number check stays clean (brief-008 FR-004)."""
    text = cut or ""
    if text.startswith("SYN_"):
        text = text[4:]
        for key in sorted(q.TERRITORY_NAMES, key=len, reverse=True):
            if text.startswith(key + "_"):
                text = text[len(key) + 1:]
                break
        text, _, n = text.rpartition("_") if text.rsplit("_", 1)[-1].isdigit() else (text, "", "")
        channel = _ENUMS.get(text, text.replace("_", " ").lower().capitalize())
        return f"{channel} plan {_NUMBERS.get(int(n), 'next') if n else ''}".strip()
    return _ENUMS.get(text, text.replace("_", " ").lower()) if text.isupper() or "_" in text else text


def _cuts_sql(p: Period, territory: str, by: str) -> str:
    W, B = p.weeks, p.baseline
    col = SPLITS[by]
    # Use rounded cumulative deltas. Subtracting adjacent values makes displayed contributions add up to the displayed total.
    return f"""
        with cuts as (
            select coalesce({col}, 'Unclassified') as cut,
                coalesce(sum({p.col}) filter (where week_start in {q._dates(W)}), 0) / {len(W)}.0 as recent,
                coalesce(sum({p.col}) filter (where week_start in {q._dates(B)}), 0) / {len(B)}.0 as baseline
            from {q.RX}
            where product_id = '{p.brand_id}' and territory_id = '{territory}'
                and week_start in {q._dates(sorted(set(W) | set(B)))}
            group by 1
        ), ordered as (
            select *, recent - baseline as delta,
                row_number() over (order by abs(recent - baseline) desc, cut) as rank
            from cuts
        ), running as (
            select *, round(sum(delta) over (order by rank), 2) as cumulative
            from ordered
        ), contributions as (
            select *, cumulative - lag(cumulative, 1, 0) over (order by rank) as contribution
            from running
        )
    """


def split_change(reg: Registry, p: Period, territory: str, by: str) -> list[str]:
    if not p.has(by):
        return [f"Cuts of the change by {by} are not part of this brief: its levels leave them out."]
    if territory not in p.ok or not p.baseline:
        return ["The feed gate or comparison window leaves no reportable split."]
    ordered = _cuts_sql(p, territory, by)
    rows = reg.rows(ordered + "select rank, cut, least(recent, baseline) from ordered order by rank")
    if not rows or all(size < SMALL_CELL for _, _, size in rows):
        return [f"Cuts of the change by {by}: the change cannot be split at this size."]
    total = reg.claim("split_change", ordered + "select cumulative from running order by rank desc limit 1", "dec2",
                      territory=territory, by=by, measure=f"total weekly {p.col_name} change")
    lines = [f"Cuts of the change by {by}, weekly {p.measure_label}. Total: {total}."]
    for rank, cut, size in rows:
        token = reg.claim("split_change", ordered + f"select contribution from contributions where rank = {rank}", "dec2",
                          territory=territory, by=by, cut=cut, measure=f"weekly {p.col_name} change", small_cell=size < SMALL_CELL)
        label = " (small cell: noisy)" if size < SMALL_CELL else ""
        lines.append(f"- {cut}: {token}{label}.")
    return lines


def story_lines(reg: Registry, p: Period, territory: str) -> list[str]:
    return [line for dimension in SPLITS if p.has(dimension) for line in split_change(reg, p, territory, dimension)]


MOST_CUTS = 5


def readable_lines(reg: Registry, p: Period, territory: str) -> list[str]:
    """The story's splits for the folded detail (brief-008 FR-004): readable cut names, rounded TRx a week with
    the direction in a word, at most five cuts a split, small cells marked."""
    from .stages import word

    lines: list[str] = []
    for by in SPLITS:
        if not p.has(by):
            continue
        if territory not in p.ok or not p.baseline:
            return ["The feed gate or comparison window leaves no reportable split."]
        ordered = _cuts_sql(p, territory, by)
        rows = reg.rows(ordered + "select rank, cut, least(recent, baseline) from ordered order by rank")
        if not rows or all(size < SMALL_CELL for _, _, size in rows):
            lines.append(f"Cuts of the change by {by}: the change cannot be split at this size.")
            continue
        params = {"territory": territory, "by": by}
        total_sql = ordered + "select cumulative from running order by rank desc limit 1"
        total = reg.claim("split_change", ordered + "select abs(cumulative) from running order by rank desc limit 1", "int",
                          measure=f"total weekly {p.col_name} change", **params)
        lines.append(f"Cuts of the change by {by}, weekly {p.measure_label}. Total: {word(reg.scalar(total_sql) or 0)} {total} {p.measure_label} a week.")
        for rank, cut, size in rows[:MOST_CUTS]:
            sql = ordered + f"select contribution from contributions where rank = {rank}"
            token = reg.claim("split_change", ordered + f"select abs(contribution) from contributions where rank = {rank}", "int",
                              cut=cut, measure=f"weekly {p.col_name} change", small_cell=size < SMALL_CELL, **params)
            lines.append(f"- {readable(cut)[:1].upper()}{readable(cut)[1:]}: {word(reg.scalar(sql) or 0)} {token} {p.measure_label} a week"
                         + (" (small cell: noisy)." if size < SMALL_CELL else "."))
    return lines


# Plan cuts (brief-010 FR-001, FR-002): the plans a territory's number hides ------------------------------------------

CUT_FLOOR = 10.0  # percent: a plan that moves against its territory counts only when its own change reaches this
MOST_CUT_CARDS = 2  # cut cards a brief, largest change first


def _cut_sql(p: Period, territory: str) -> str:
    """Per plan of a territory: the primary measure's weekly mean on the comparison weeks and the period, then the
    plan's TRx a week on each (its size, for the small-cell floor, whatever the measure)."""
    W, B, col = p.weeks, p.baseline, p.col
    return f"""
        select coalesce(plan_id, 'Unclassified'),
            coalesce(sum({col}) filter (where week_start in {q._dates(W)}), 0) / {len(W)}.0,
            coalesce(sum({col}) filter (where week_start in {q._dates(B)}), 0) / {len(B)}.0,
            coalesce(sum(trx) filter (where week_start in {q._dates(W)}), 0) / {len(W)}.0,
            coalesce(sum(trx) filter (where week_start in {q._dates(B)}), 0) / {len(B)}.0
        from {q.RX}
        where product_id = '{p.brand_id}' and territory_id = '{territory}' and week_start in {q._dates(sorted(set(W) | set(B)))}
        group by 1"""


def screen_cuts(reg: Registry, p: Period, territories: list[str]) -> list[dict]:
    """The plans worth a card, in the brief's story territories, largest change first, at most two (FR-001). A plan
    is flagged when its direction (the primary measure, outside the flat band and beyond CUT_FLOOR) runs against its
    territory's, or when the access check supports an access change on that plan in or just before the period (the
    access driver sits there; the check reads the months of the period and the two weeks before it). A plan whose
    TRx a week is below SMALL_CELL on either side is never quoted, so it gets no card. Makes no claim: the card's own
    figures do (`cut_figures`). Only for BXA, the brand whose plans the access data covers."""
    if not (p.has("plan") and p.weeks and p.baseline) or p.calendar or p.brand_id != "BXA":
        return []
    found = []
    for t in dict.fromkeys(territories):
        if t not in p.ok:
            continue
        rows = reg.rows(_cut_sql(p, t))
        total_now, total_then = sum(r[1] for r in rows), sum(r[2] for r in rows)
        if not total_then:
            continue
        direction = word(100 * (total_now / total_then - 1))
        events = {e["plan"] for e in access_events(reg, t, [q.shift(w, -lag) for lag in (0, 1, 2) for w in p.weeks], brand_id=p.brand_id)}
        scratch = reg.scratch()  # the check's own claims are not this run's
        for plan, now, then, now_trx, then_trx in rows:
            if not then or plan == "Unclassified" or min(now_trx, then_trx) < SMALL_CELL:
                continue
            change = 100 * (now / then - 1)
            against = (word(change) != "flat" and direction != "flat" and word(change) != direction and abs(change) >= CUT_FLOOR)
            access = plan in events and check_access(scratch, t, p.weeks, p.baseline, plan=plan).verdict == "supported"
            if against or access:
                found.append({"territory": t, "plan": plan, "cut": f"plan:{plan}", "against": against,
                              "access": access, "direction": word(change), "impact": abs(now - then)})
    found.sort(key=lambda c: (-c["impact"], c["plan"]))
    return found[:MOST_CUT_CARDS]


def plan_territory(reg: Registry, plan: str) -> str | None:
    return reg.scalar(f"select territory_id from raw.dim_plan where plan_id = '{plan}'")


def cut_figures(reg: Registry, p: Period, territory: str, plan: str) -> dict:
    """A cut's claims (FR-002): for each measure the definition holds, the plan's level a week before and after on
    the comparison weeks and the percent change, labelled grain "plan" and cut `plan:<id>` (an extra measure also
    labelled with its own); and the territory's own change on the primary measure. Tokens and words, no number."""
    W, B, brand = p.weeks, p.baseline, p.brand_id
    measures = []
    for m in p.definition.measure:
        x, b = q.mean_weekly(W, plan=plan, product=brand, col=m), q.mean_weekly(B, plan=plan, product=brand, col=m)
        change = reg.scalar(q.pct_change(x, b)) or 0
        fmt = "dec1" if m == "nbrx" else "int"
        with reg.under(**({} if m == p.col else {"measure": m})):
            args = {"territory": territory, "plan": plan, "scope": "the plan, " + measure_label(m)}
            measures.append({"measure": m, "label": measure_label(m), "word": word(change),
                             "before": reg.claim("get_plan_metric", b, fmt, **args),
                             "after": reg.claim("get_plan_metric", x, fmt, **args),
                             "pct": reg.claim("get_plan_metric", q.pct_change(x, b), "pct1", **args)})
    tx, tb = q.mean_weekly(W, terrs=[territory], product=brand, col=p.col), q.mean_weekly(B, terrs=[territory], product=brand, col=p.col)
    t_change = reg.scalar(q.pct_change(tx, tb)) or 0
    t_pct = reg.claim("get_metric", q.pct_change(tx, tb), "pct1", territory=territory, scope="the territory, " + measure_label(p.col))
    return {"measures": measures, "territory_word": word(t_change), "territory_pct": t_pct}

