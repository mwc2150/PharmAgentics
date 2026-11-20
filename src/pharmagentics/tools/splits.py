"""Additive cuts of the reportable weekly TRx change in one territory story."""
from __future__ import annotations

from . import queries as q
from .registry import Registry
from .stages import Period

SPLITS = {"plan": "plan_id", "specialty": "hcp_specialty", "channel": "payer_channel"}
SMALL_CELL = 50


def split_change(reg: Registry, p: Period, territory: str, by: str) -> list[str]:
    if territory not in p.ok or not p.baseline:
        return ["The feed gate or comparison window leaves no reportable split."]
    W, B = p.weeks, p.baseline
    col = SPLITS[by]
    # Use rounded cumulative deltas. Subtracting adjacent values makes displayed contributions add up to the displayed total.
    ordered = f"""
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
