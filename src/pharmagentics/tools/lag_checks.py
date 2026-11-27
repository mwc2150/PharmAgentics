"""Timing checks for Briefing over reportable TRx and aggregated driver context."""
from __future__ import annotations

from . import queries as q
from .checks import Check, access_events, check_competitor, check_data, context_baseline
from .brands import briefing_brand
from .registry import Registry

DRIVER_LAGS = (0, 1, 2)
PROMOTION_CHANGE_PCT = 30
LOW_FILL, FILL_CHANGE = 0.90, 0.02
LAG_LABELS = ("same week", "one-week lag", "two-week lag")


def check_access(reg: Registry, terr: str, W, B, *, plan: str | None = None, brand_id: str = "BXA") -> Check:
    """The access driver for a territory, or, with `plan`, for that one plan (brief-010 FR-001: a cut card's access
    verdict is its own plan's): an access change in the months of the period or the two weeks before it that lines up
    with the plan's reportable TRx."""
    if not W or not B:
        return Check("access", "insufficient", "Access: insufficient. No TRx comparison is available.")
    shifted = [q.shift(w, -lag) for lag in DRIVER_LAGS for w in W]
    events = access_events(reg, terr, shifted, brand_id=brand_id)
    if plan is not None:
        events = [e for e in events if e["plan"] == plan]
    if not events:
        where = "on this plan" if plan is not None else f"in the {q.name(terr)} plans"
        return Check("access", "ruled_out", f"Access: ruled out. No {brand_id} access change {where} in the tested months.")
    matched = []
    for event in events:
        change_sql = q.pct_change(q.mean_weekly(W, plan=event["plan"], product=brand_id), q.mean_weekly(B, plan=event["plan"], product=brand_id))
        pct = reg.scalar(change_sql)
        if pct is not None and (pct < 0 if event["restricted"] else pct > 0):
            matched.append((abs(pct), event))
    if not matched:
        return Check("access", "insufficient", "Access: inconclusive. No tested access change aligns with reportable plan TRx.")
    _, e = max(matched, key=lambda item: item[0])
    plan_w, plan_b = q.mean_weekly(W, plan=e["plan"], product=brand_id), q.mean_weekly(B, plan=e["plan"], product=brand_id)
    change = reg.claim("get_plan_metric", q.pct_change(plan_w, plan_b), "pct", plan=e["plan"], weeks=len(W))
    lives = reg.claim(
        "lookup_access_events",
        f"select 100.0 * (select max(covered_lives_weight) from raw.dim_plan where plan_id = '{e['plan']}') / "
        f"(select sum(covered_lives_weight) from raw.dim_plan where territory_id = '{terr}')", "pct", plan=e["plan"])
    move = "added restrictions (tier, prior authorization or step therapy)" if e["restricted"] else "removed restrictions"
    trend = "fell" if e["restricted"] else "rose"
    from .splits import readable  # a reader's name for the plan (brief-008 FR-004); local: splits imports stages, which imports this

    return Check("access", "supported",
                 f"Access: supported. The {readable(e['plan'])} ({lives} of the territory's covered lives) {move} "
                 f"effective {e['month']}. {brand_id} volume on that plan {trend} {change}. "
                 "The monthly source cannot distinguish a weekly lag.", {"plan": e["plan"], "events": events})


def _lagged_levels(reg: Registry, table: str, column: str, terr: str, W, B, brand_id: str = "BXA") -> list:
    """Source weeks can predate the release. Only aggregate comparisons with every source week present."""
    if not W or not B:
        return []
    cuts = []
    for lag in DRIVER_LAGS:
        current, baseline = ([q.shift(w, -lag) for w in window] for window in (W, B))
        values = []
        for window in (current, baseline):
            mean = reg.scalar(f"select case when count(distinct week_start) = {len(window)} "
                              f"then avg({column}) end from raw.{table} where product_id = '{brand_id}' "
                              f"and territory_id = '{terr}' and week_start in {q._dates(window)} and {column} is not null")
            values.append(mean)
        if all(value is not None for value in values):
            cuts.append((lag, current, baseline, *values))
    return cuts


def _trx_direction(reg: Registry, terr: str, W, B, brand_id: str = "BXA") -> float | None:
    weeks = sorted(set(W) | set(B))
    if not W or not B:
        return None
    n = reg.scalar(f"select count(*) from reporting.v_feed_health where territory_id = '{terr}' "
                   f"and week_start in {q._dates(weeks)} and health_status = 'PASS'")
    if n != len(weeks):
        return None
    return reg.scalar(q.pct_change(q.mean_weekly(W, terrs=[terr], product=brand_id), q.mean_weekly(B, terrs=[terr], product=brand_id)))


def check_promotion(reg: Registry, terr: str, W, B, brand_id: str = "BXA") -> Check:
    """Promotion against the brief's stated comparison weeks B, the same weeks as TRx (assumptions first): a longer,
    unstated window can hold a lapse and turn a recovery into a push. A lapse still running gets a continuing card."""
    cuts = _lagged_levels(reg, "promo_activity", "rep_calls_aggregated", terr, W, B, brand_id)
    trx = _trx_direction(reg, terr, W, B, brand_id)
    if not cuts or trx is None:
        return Check("promotion", "insufficient", "Promotion: insufficient. No complete TRx and promotion comparison is available.")
    matches = [c for c in cuts if c[4] and abs(100 * (c[3] / c[4] - 1)) >= PROMOTION_CHANGE_PCT
               and (c[3] - c[4]) * trx > 0]
    lag, current, baseline, avg, prior = (matches or cuts)[0]
    recent = q.context_mean("promo_activity", "rep_calls_aggregated", current, terr, product=brand_id)
    earlier = q.context_mean("promo_activity", "rep_calls_aggregated", baseline, terr, product=brand_id)
    a = reg.claim("lookup_promo", recent, "int", territory=terr, weeks=current)
    b = reg.claim("lookup_promo", earlier, "int", territory=terr, weeks=baseline)
    if not matches:
        return Check("promotion", "ruled_out", f"Promotion: ruled out. No tested lag lines up with TRx. "
                     f"Aggregated calls averaged {a} a week against {b} in the comparison weeks{_lag_note(lag)}.")
    pct = reg.claim("lookup_promo", q.pct_change(recent, earlier), "pct", territory=terr, lag=lag)
    direction = "lower" if avg < prior else "higher"
    lapse = _lapse_in(reg, terr, baseline, brand_id) if avg > prior else None
    lapse = lapse if lapse and lapse[1] < current[-1] else None  # calls came back inside the period: recovery
    if lapse:  # the comparison holds a lapse: calls coming back is recovery, not a push (mentor review 2.1)
        return Check("promotion", "supported", f"Promotion: supported as recovery after the promotion lapse of {lapse[0]} to "
                     f"{lapse[1]}, {LAG_LABELS[lag]}. Aggregated calls averaged {a} a week against {b} in the comparison "
                     f"weeks{_lag_note(lag)}, which include lapse weeks ({pct} {direction}).", {"lag": lag, "lapse": lapse})
    return Check("promotion", "supported", f"Promotion: supported as an association, {LAG_LABELS[lag]}. "
                 f"Aggregated calls averaged {a} a week against {b} in the comparison weeks{_lag_note(lag)} ({pct} {direction}).",
                 {"lag": lag})


def _lapse_in(reg: Registry, terr: str, weeks, brand_id: str = "BXA") -> tuple[str, str] | None:
    """The territory's promotion lapse (the Promotion review's rule) with a week inside `weeks`, as (start, end)."""
    from .promotion import lapses  # local: promotion imports memo, which imports this module
    return next(((e.start, e.end) for e in lapses(reg, terr, brand_id) if any(e.start <= w <= e.end for w in weeks)), None)


def _lag_note(lag: int) -> str:
    """With a lag, both windows sit that many weeks earlier than the period and the comparison weeks."""
    return f", each shifted {'one week' if lag == 1 else 'two weeks'} earlier" if lag else ""


def check_supply(reg: Registry, terr: str, W, B, brand_id: str = "BXA") -> Check:
    cuts = _lagged_levels(reg, "inventory_weekly", "inventory_fill_rate", terr, W, B, brand_id)
    trx = _trx_direction(reg, terr, W, B, brand_id)
    if not cuts or trx is None:
        return Check("supply", "insufficient", "Supply: insufficient. No complete TRx and inventory comparison is available.")
    matches = [c for c in cuts if trx < 0 and c[3] < LOW_FILL and c[4] - c[3] >= FILL_CHANGE]
    lag, current, baseline, _avg, _prior = (matches or cuts)[0]
    f = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "inventory_fill_rate", current, terr, product=brand_id),
                  "dec2", territory=terr, weeks=current)
    if not matches:
        return Check("supply", "ruled_out", f"Supply: ruled out. No tested lag lines up with TRx. {brand_id} inventory fill averaged {f}.")
    previous = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "inventory_fill_rate", baseline, terr, product=brand_id),
                         "dec2", territory=terr, weeks=baseline)
    back = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "distribution_backorder_rate", current, terr, 100, product=brand_id),
                     "pct", territory=terr, weeks=current)
    return Check("supply", "supported", f"Supply: supported, {LAG_LABELS[lag]}. {brand_id} inventory fill averaged {f} against "
                 f"{previous} in the comparison weeks, with {back} of orders backordered.", {"lag": lag})


def run_checks(reg: Registry, terr: str, W, B, *, brand_id: str = "BXA",
               use_selected_baseline: bool = False) -> list[Check]:
    brand_id = briefing_brand(brand_id)
    ref = B if use_selected_baseline else context_baseline(W, B)  # competitor only; its weeks are stated (memo.assumptions)
    return [check_data(reg, terr, W, B, brand_id), check_access(reg, terr, W, B, brand_id=brand_id),
            check_promotion(reg, terr, W, B, brand_id), check_supply(reg, terr, W, B, brand_id),
            check_competitor(reg, terr, W, ref, brand_id, exact_comparison=use_selected_baseline, pct_format="pct")]


def national_ruled_out(story_checks) -> list[str]:
    """Drivers ruled out nationally (brief-010 FR-006, packet NC): access, promotion or supply is ruled out unless a
    territory that has its own story card in this brief supports it or cannot rule it out (inconclusive, insufficient
    or never tested). `story_checks` holds each story territory's checks, as a list or a {driver: Check} dict, exactly
    the ones the brief ran for its cards, so no check runs again and no claim is added. A territory without a story
    does not keep a driver off the list; a brief with no story territory rules all three out."""
    verdicts = [{c.driver: c.verdict for c in (checks.values() if isinstance(checks, dict) else checks)} for checks in story_checks]
    return [d for d in ("access", "promotion", "supply") if all(v.get(d) == "ruled_out" for v in verdicts)]
