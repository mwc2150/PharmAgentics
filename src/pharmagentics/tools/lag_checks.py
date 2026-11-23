"""Timing checks for Briefing over reportable TRx and aggregated driver context."""
from __future__ import annotations

from . import queries as q
from .checks import Check, access_events, check_competitor, check_data, context_baseline
from .checks import run_checks as run_brand_checks
from .registry import Registry

DRIVER_LAGS = (0, 1, 2)
PROMOTION_CHANGE_PCT = 30
LOW_FILL, FILL_CHANGE = 0.90, 0.02
LAG_LABELS = ("same week", "one-week lag", "two-week lag")


def check_access(reg: Registry, terr: str, W, B, *, plan: str | None = None) -> Check:
    """The access driver for a territory, or, with `plan`, for that one plan (brief-010 FR-001: a cut card's access
    verdict is its own plan's): an access change in the months of the period or the two weeks before it that lines up
    with the plan's reportable TRx."""
    if not W or not B:
        return Check("access", "insufficient", "Access: insufficient. No TRx comparison is available.")
    shifted = [q.shift(w, -lag) for lag in DRIVER_LAGS for w in W]
    events = access_events(reg, terr, shifted)
    if plan is not None:
        events = [e for e in events if e["plan"] == plan]
    if not events:
        where = "on this plan" if plan is not None else f"in the {q.name(terr)} plans"
        return Check("access", "ruled_out", f"Access: ruled out. No BXA access change {where} in the tested months.")
    matched = []
    for event in events:
        change_sql = q.pct_change(q.mean_weekly(W, plan=event["plan"]), q.mean_weekly(B, plan=event["plan"]))
        pct = reg.scalar(change_sql)
        if pct is not None and (pct < 0 if event["restricted"] else pct > 0):
            matched.append((abs(pct), event))
    if not matched:
        return Check("access", "insufficient", "Access: inconclusive. No tested access change aligns with reportable plan TRx.")
    _, e = max(matched, key=lambda item: item[0])
    plan_w, plan_b = q.mean_weekly(W, plan=e["plan"]), q.mean_weekly(B, plan=e["plan"])
    change = reg.claim("get_plan_metric", q.pct_change(plan_w, plan_b), "pct1", plan=e["plan"], weeks=len(W))
    lives = reg.claim(
        "lookup_access_events",
        f"select 100.0 * (select max(covered_lives_weight) from raw.dim_plan where plan_id = '{e['plan']}') / "
        f"(select sum(covered_lives_weight) from raw.dim_plan where territory_id = '{terr}')", "pct1", plan=e["plan"])
    move = "added restrictions (tier, prior authorization or step therapy)" if e["restricted"] else "removed restrictions"
    trend = "fell" if e["restricted"] else "rose"
    from .splits import readable  # a reader's name for the plan (brief-008 FR-004); local: splits imports stages, which imports this

    return Check("access", "supported",
                 f"Access: supported. The {readable(e['plan'])} ({lives} of the territory's covered lives) {move} "
                 f"effective {e['month']}. BXA volume on that plan {trend} {change}. "
                 "The monthly source cannot distinguish a weekly lag.", {"plan": e["plan"], "events": events})


def _lagged_levels(reg: Registry, table: str, column: str, terr: str, W, B) -> list:
    """Source weeks can predate the release. Only aggregate comparisons with every source week present."""
    if not W or not B:
        return []
    cuts = []
    for lag in DRIVER_LAGS:
        current, baseline = ([q.shift(w, -lag) for w in window] for window in (W, B))
        values = []
        for window in (current, baseline):
            mean = reg.scalar(f"select case when count(distinct week_start) = {len(window)} "
                              f"then avg({column}) end from raw.{table} where product_id = 'BXA' "
                              f"and territory_id = '{terr}' and week_start in {q._dates(window)} and {column} is not null")
            values.append(mean)
        if all(value is not None for value in values):
            cuts.append((lag, current, baseline, *values))
    return cuts


def _trx_direction(reg: Registry, terr: str, W, B) -> float | None:
    weeks = sorted(set(W) | set(B))
    if not W or not B:
        return None
    n = reg.scalar(f"select count(*) from reporting.v_feed_health where territory_id = '{terr}' "
                   f"and week_start in {q._dates(weeks)} and health_status = 'PASS'")
    if n != len(weeks):
        return None
    return reg.scalar(q.pct_change(q.mean_weekly(W, terrs=[terr]), q.mean_weekly(B, terrs=[terr])))


def check_promotion(reg: Registry, terr: str, W, B, *, source_baseline=None) -> Check:
    reference = B if source_baseline is None else source_baseline
    cuts = _lagged_levels(reg, "promo_activity", "rep_calls_aggregated", terr, W, reference)
    trx = _trx_direction(reg, terr, W, B)
    if not cuts or trx is None:
        return Check("promotion", "insufficient", "Promotion: insufficient. No complete TRx and promotion comparison is available.")
    matches = [c for c in cuts if c[4] and abs(100 * (c[3] / c[4] - 1)) >= PROMOTION_CHANGE_PCT
               and (c[3] - c[4]) * trx > 0]
    lag, current, baseline, avg, prior = (matches or cuts)[0]
    recent = q.context_mean("promo_activity", "rep_calls_aggregated", current, terr)
    earlier = q.context_mean("promo_activity", "rep_calls_aggregated", baseline, terr)
    a = reg.claim("lookup_promo", recent, "int", territory=terr, weeks=current)
    b = reg.claim("lookup_promo", earlier, "int", territory=terr, weeks=baseline)
    if not matches:
        return Check("promotion", "ruled_out", f"Promotion: ruled out. No tested lag lines up with TRx. "
                     f"Aggregated calls averaged {a} a week against {b} in the reference weeks.")
    pct = reg.claim("lookup_promo", q.pct_change(recent, earlier), "pct1", territory=terr, lag=lag)
    direction = "lower" if avg < prior else "higher"
    return Check("promotion", "supported", f"Promotion: supported as an association, {LAG_LABELS[lag]}. "
                 f"Aggregated calls averaged {a} a week against {b} in the reference weeks ({pct} {direction}).",
                 {"lag": lag})


def check_supply(reg: Registry, terr: str, W, B) -> Check:
    cuts = _lagged_levels(reg, "inventory_weekly", "inventory_fill_rate", terr, W, B)
    trx = _trx_direction(reg, terr, W, B)
    if not cuts or trx is None:
        return Check("supply", "insufficient", "Supply: insufficient. No complete TRx and inventory comparison is available.")
    matches = [c for c in cuts if trx < 0 and c[3] < LOW_FILL and c[4] - c[3] >= FILL_CHANGE]
    lag, current, baseline, _avg, _prior = (matches or cuts)[0]
    f = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "inventory_fill_rate", current, terr),
                  "dec2", territory=terr, weeks=current)
    if not matches:
        return Check("supply", "ruled_out", f"Supply: ruled out. No tested lag lines up with TRx. BXA inventory fill averaged {f}.")
    previous = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "inventory_fill_rate", baseline, terr),
                         "dec2", territory=terr, weeks=baseline)
    back = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "distribution_backorder_rate", current, terr, 100),
                     "pct1", territory=terr, weeks=current)
    return Check("supply", "supported", f"Supply: supported, {LAG_LABELS[lag]}. BXA inventory fill averaged {f} against "
                 f"{previous} in the comparison weeks, with {back} of orders backordered.", {"lag": lag})


def run_checks(reg: Registry, terr: str, W, B, *, brand_id: str = "BXA",
               use_selected_baseline: bool = False) -> list[Check]:
    if brand_id != "BXA":
        return run_brand_checks(reg, terr, W, B, brand_id, use_selected_baseline=use_selected_baseline)
    ref = B if use_selected_baseline else context_baseline(W, B)
    return [check_data(reg, terr, W, B), check_access(reg, terr, W, B), check_promotion(reg, terr, W, B, source_baseline=ref),
            check_supply(reg, terr, W, B), check_competitor(reg, terr, W, ref, exact_comparison=use_selected_baseline)]


def national_ruled_out(reg: Registry, terrs: list[str], W, B, *, brand_id: str = "BXA", use_selected_baseline: bool = False) -> list[str]:
    """Drivers ruled out nationally (brief-010 FR-006): access, promotion or supply, when every reportable territory's
    own check rules it out on the brief's weeks. The same checks the territory stories run, on a scratch registry so
    no claim or evidence is added; a territory whose check is inconclusive or supported keeps the driver off the list."""
    if not terrs:
        return []
    scratch = reg.scratch()
    verdicts = [{c.driver: c.verdict for c in run_checks(scratch, t, W, B, brand_id=brand_id, use_selected_baseline=use_selected_baseline)}
                for t in terrs]
    return [d for d in ("access", "promotion", "supply") if all(v.get(d) == "ruled_out" for v in verdicts)]
