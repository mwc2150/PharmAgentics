"""Additive cuts of the reportable weekly TRx change in one territory story."""
from __future__ import annotations

from . import queries as q
from .registry import Registry
from .stages import Period

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
                coalesce(sum(trx) filter (where week_start in {q._dates(W)}), 0) / {len(W)}.0 as recent,
                coalesce(sum(trx) filter (where week_start in {q._dates(B)}), 0) / {len(B)}.0 as baseline
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
    if territory not in p.ok or not p.baseline:
        return ["The feed gate or comparison window leaves no reportable split."]
    ordered = _cuts_sql(p, territory, by)
    rows = reg.rows(ordered + "select rank, cut, least(recent, baseline) from ordered order by rank")
    if not rows or all(size < SMALL_CELL for _, _, size in rows):
        return [f"Cuts of the change by {by}: the change cannot be split at this size."]
    total = reg.claim("split_change", ordered + "select cumulative from running order by rank desc limit 1", "dec2",
                      territory=territory, by=by, measure="total weekly TRx change")
    lines = [f"Cuts of the change by {by}, weekly TRx. Total: {total}."]
    for rank, cut, size in rows:
        token = reg.claim("split_change", ordered + f"select contribution from contributions where rank = {rank}", "dec2",
                          territory=territory, by=by, cut=cut, measure="weekly TRx change", small_cell=size < SMALL_CELL)
        label = " (small cell: noisy)" if size < SMALL_CELL else ""
        lines.append(f"- {cut}: {token}{label}.")
    return lines


def story_lines(reg: Registry, p: Period, territory: str) -> list[str]:
    return [line for dimension in SPLITS for line in split_change(reg, p, territory, dimension)]


MOST_CUTS = 5


def readable_lines(reg: Registry, p: Period, territory: str) -> list[str]:
    """The story's splits for the folded detail (brief-008 FR-004): readable cut names, rounded TRx a week with
    the direction in a word, at most five cuts a split, small cells marked."""
    from .stages import word

    lines: list[str] = []
    for by in SPLITS:
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
                          measure="total weekly TRx change", **params)
        lines.append(f"Cuts of the change by {by}, weekly TRx. Total: {word(reg.scalar(total_sql) or 0)} {total} TRx a week.")
        for rank, cut, size in rows[:MOST_CUTS]:
            sql = ordered + f"select contribution from contributions where rank = {rank}"
            token = reg.claim("split_change", ordered + f"select abs(contribution) from contributions where rank = {rank}", "int",
                              cut=cut, measure="weekly TRx change", small_cell=size < SMALL_CELL, **params)
            lines.append(f"- {readable(cut)[:1].upper()}{readable(cut)[1:]}: {word(reg.scalar(sql) or 0)} {token} TRx a week"
                         + (" (small cell: noisy)." if size < SMALL_CELL else "."))
    return lines
