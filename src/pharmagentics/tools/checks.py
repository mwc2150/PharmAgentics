"""The fixed catalog of driver checks both lanes share. Each check computes a verdict by code:
supported, ruled_out or insufficient, with a sentence whose numbers are claim tokens."""
from __future__ import annotations

from dataclasses import dataclass

from . import queries as q
from .registry import Registry
from .brands import briefing_brand

DRIVERS = ("access", "promotion", "supply", "competitor", "data")
OWNER = {  # function to involve (Evaluation Pack EV-7.3)
    "access": "market access", "promotion": "sales leadership and marketing",
    "supply": "supply chain and trade", "competitor": "marketing and sales",
    "data": "the data vendor and commercial analytics",
}
DECISION = {  # what a next check unlocks (brief-003 §5 Next checks)
    "access": "whether the plan's coverage change needs a pull-through response",
    "promotion": "whether to change call plans or campaign timing in the territory",
    "supply": "whether to escalate supply with trade partners",
    "competitor": "whether to adjust the response to Metacora",
    "data": "whether the restated week changes any figure already reported",
    "unresolved": "whether to open a deeper review of the territory",
}


@dataclass
class Check:
    driver: str
    verdict: str  # supported | ruled_out | insufficient
    text: str  # template with claim tokens
    detail: dict | None = None


def access_events(reg: Registry, terr: str | None, weeks, brand_id: str = "BXA") -> list[dict]:
    """BXA plans whose tier, prior authorization, step therapy or coverage changed in the months of `weeks`."""
    brand_id = briefing_brand(brand_id)
    months = sorted({w[:7] + "-01" for w in weeks})
    sql = f"""
    with a as (select plan_id, territory_id, payer_channel, month, formulary_tier t, prior_authorization pa,
        step_therapy st, covered c, lag(formulary_tier) over w pt, lag(prior_authorization) over w ppa,
        lag(step_therapy) over w pst, lag(covered) over w pc
      from raw.access_status_monthly where product_id = '{brand_id}' window w as (partition by plan_id order by month))
    select plan_id, territory_id, payer_channel, month::varchar, t > pt or pa > ppa or st > pst or c < pc as restricted
    from a where pt is not null and (t <> pt or pa <> ppa or st <> pst or c <> pc)
      and month in ({",".join(f"DATE '{m}'" for m in months)})"""
    if terr and terr != "NATIONAL":
        sql += f" and territory_id = '{terr}'"
    return [dict(plan=r[0], territory=r[1], channel=r[2], month=r[3], restricted=bool(r[4])) for r in reg.rows(sql)]


def check_access(reg: Registry, terr: str, W, B, brand_id: str = "BXA", *, pct_format: str = "pct1") -> Check:
    events = access_events(reg, terr, W, brand_id=brand_id)
    if not events:
        return Check("access", "ruled_out", f"Access: ruled out. No {brand_id} access change in the {q.name(terr)} plans in these months.")
    e = events[0]
    plan_w, plan_b = q.mean_weekly(W, plan=e["plan"], product=brand_id), q.mean_weekly(B, plan=e["plan"], product=brand_id)
    change = reg.claim("get_plan_metric", q.pct_change(plan_w, plan_b), pct_format, plan=e["plan"], weeks=len(W))
    lives = reg.claim(
        "lookup_access_events",
        f"select 100.0 * (select max(covered_lives_weight) from raw.dim_plan where plan_id = '{e['plan']}') / "
        f"(select sum(covered_lives_weight) from raw.dim_plan where territory_id = '{terr}')", pct_format, plan=e["plan"])
    move = "added restrictions (tier, prior authorization or step therapy)" if e["restricted"] else "removed restrictions"
    trend = "fell" if e["restricted"] else "rose"
    from .splits import readable  # a reader's name for the plan (brief-008 FR-004); local: splits imports stages, which imports this

    return Check("access", "supported",
                 f"Access: supported. The {readable(e['plan'])} ({lives} of the territory's covered lives) {move} "
                 f"effective {e['month']}. {brand_id} volume on that plan {trend} {change}.", {"plan": e["plan"], "events": events})


def check_promotion(reg: Registry, terr: str, W, B, brand_id: str = "BXA", *, pct_format: str = "pct1") -> Check:
    a = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", W, terr, product=brand_id), "int", territory=terr)
    b = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", B, terr, product=brand_id), "int", territory=terr)
    change = (reg.scalar(q.pct_change(q.context_mean("promo_activity", "rep_calls_aggregated", W, terr, product=brand_id),
                                      q.context_mean("promo_activity", "rep_calls_aggregated", B, terr, product=brand_id))) or 0)
    if change <= -30:
        pct = reg.claim("lookup_promo", q.pct_change(q.context_mean("promo_activity", "rep_calls_aggregated", W, terr, product=brand_id),
                                                      q.context_mean("promo_activity", "rep_calls_aggregated", B, terr, product=brand_id)), pct_format, territory=terr)
        return Check("promotion", "supported",
                     f"Promotion: supported, as an association. Aggregated rep calls averaged {a} a week against {b} in the "
                     f"comparison weeks ({pct} lower). Method: this territory's weeks before, compared with the same weeks elsewhere.")
    return Check("promotion", "ruled_out", f"Promotion: ruled out. Aggregated rep calls held at {a} a week against {b} in the comparison weeks.")


def check_supply(reg: Registry, terr: str, W, B, brand_id: str = "BXA", *, pct_format: str = "pct1") -> Check:
    fill = reg.scalar(q.context_mean("inventory_weekly", "inventory_fill_rate", W, terr, product=brand_id))
    f = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "inventory_fill_rate", W, terr, product=brand_id), "dec2", territory=terr)
    if fill is not None and fill < 0.90:
        back = reg.claim("lookup_inventory", q.context_mean("inventory_weekly", "distribution_backorder_rate", W, terr, 100, product=brand_id), pct_format, territory=terr)
        return Check("supply", "supported", f"Supply: supported. {brand_id} inventory fill averaged {f} (close to full supply is normal), with {back} of orders backordered.")
    return Check("supply", "ruled_out", f"Supply: ruled out. {brand_id} inventory fill averaged {f}.")


def launch_date(reg: Registry) -> str | None:
    return reg.scalar("select min(effective_start)::varchar from raw.market_basket where product_id = 'BXE'")


def check_competitor(reg: Registry, terr: str, W, B, brand_id: str = "BXA", *, exact_comparison: bool = False,
                     pct_format: str = "pct1") -> Check:
    """Was Metacora already stronger here before the change? Shares inside the affected weeks are not
    compared: when {brand_id} volume drops, competitor share rises mechanically."""
    launched = launch_date(reg)
    if launched is None or launched > W[-1]:
        return Check("competitor", "ruled_out", f"Competitor launch: ruled out. Metacora did not launch until {launched}.")
    if exact_comparison and (not B or B[-1] < launched):
        return Check("competitor", "insufficient",
                     f"Competitor launch: inconclusive. The chosen comparison ends before Metacora launched on {launched}.")
    ref = competitor_weeks(W, B, launched, exact_comparison)
    here, elsewhere = q.share(ref, "BXE", terrs=[terr]), q.share(ref, "BXE", exclude=terr)
    gap = (reg.scalar(here) or 0) - (reg.scalar(elsewhere) or 0)
    h = reg.claim("compare_competitors", here, pct_format, territory=terr, weeks="before the change")
    e = reg.claim("compare_competitors", elsewhere, pct_format, scope="other territories", weeks="before the change")
    if abs(gap) < 3:
        return Check("competitor", "ruled_out",
                     f"Competitor launch: ruled out as a local cause. Before the change Metacora held {h} of the basket here against {e} elsewhere.")
    return Check("competitor", "supported",
                 f"Competitor launch: supported. Before the change Metacora held {h} of the basket here against {e} elsewhere.")


def competitor_weeks(W, B, launched: str, exact: bool) -> list[str]:
    """The weeks the competitor check reads Metacora's share over: the chosen comparison when the analyst picked one,
    else the weeks since launch inside B (the context weeks), else the period itself. One function, so the check
    and the Assumptions sentence that states its weeks cannot disagree."""
    return list(B) if exact else [w for w in B if w >= launched] or list(W)


def competitor_assumption(reg: Registry, W, B, *, exact: bool) -> str | None:
    """The Assumptions sentence for the competitor check's weeks (assumptions first: a check that reads other weeks
    than the comparison states them). B is what run_checks passes the check: the context weeks unless chosen."""
    launched = launch_date(reg)
    if exact or not W or launched is None or launched > W[-1]:
        return None  # a chosen comparison is read as stated; its own story line says when it predates the launch
    weeks = competitor_weeks(W, B, launched, exact)
    span = f"the week of {weeks[0]}" if len(weeks) == 1 else f"{weeks[0]} to {weeks[-1]}"
    return f"Metacora's local share: {span}."


COMPETITOR_FLOOR = 5.0  # basket share (points) below which Metacora is not a national story


def check_competitor_national(reg: Registry, W) -> Check:
    """The national competitor check (brief-010 FR-006): is Metacora a material part of the basket on the brief's
    weeks? Supported once it has launched and holds at least the floor; ruled out before launch or below it.
    The text states no number, so it adds no claim; the card's own claims carry the shares."""
    launched = launch_date(reg)
    if launched is None or launched > W[-1]:
        return Check("competitor", "ruled_out", "Competitor launch: ruled out. Metacora had not launched in these weeks.")
    if (reg.scalar(q.share(W, "BXE")) or 0) < COMPETITOR_FLOOR:
        return Check("competitor", "ruled_out", "Competitor launch: ruled out. Metacora's basket share is below the floor for a national story.")
    return Check("competitor", "supported", "Competitor launch: supported. Metacora holds a material share of the basket.")


def check_data(reg: Registry, terr: str, W, B, brand_id: str = "BXA") -> Check:
    weeks = sorted(set(W) | set(B))
    flagged = reg.scalar(f"select count(*) from reporting.v_feed_health where territory_id = '{terr}' and health_status = 'FLAG' "
                         f"and week_start in {q._dates(weeks)}")
    if flagged:
        n = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where territory_id = '{terr}' "
                      f"and health_status = 'FLAG' and week_start in {q._dates(weeks)}", "int", territory=terr)
        return Check("data", "insufficient", f"Data artifact: not ruled out. {n} {q.name(terr)} cut(s) in these weeks fail the feed gate.")
    return Check("data", "ruled_out", f"Data artifact: ruled out. Every {q.name(terr)} cut in these weeks passes the feed gate.")


def confidence(checks: list[Check]) -> tuple[str, str]:
    """High: one supported, every other ruled out. Medium: one supported with others open, or several
    supported. Low: none supported, so the agent abstains. Promotion alone is an association: Medium at most."""
    supported = [c for c in checks if c.verdict == "supported"]
    if not supported:
        return "Low", "unresolved, investigate next"
    if len(supported) == 1 and all(c.verdict == "ruled_out" for c in checks if c is not supported[0]):
        level = "Medium" if supported[0].driver == "promotion" else "High"
    else:
        level = "Medium"
    return level, " and ".join(c.driver for c in supported)


def context_baseline(W, B) -> list[str]:
    """Reference weeks for context checks: at least 13, so a gap already under way in the last few weeks
    cannot hide itself in its own baseline."""
    return B if len(B) >= 13 else [q.shift(W[0], -i) for i in range(13, 0, -1)]


def run_checks(reg: Registry, terr: str, W, B, brand_id: str = "BXA", *,
               use_selected_baseline: bool = False, pct_format: str = "pct1") -> list[Check]:
    ref = B if use_selected_baseline else context_baseline(W, B)  # competitor only; its weeks are stated (memo.assumptions)
    return [check_data(reg, terr, W, B, brand_id), check_access(reg, terr, W, B, brand_id, pct_format=pct_format),
            check_promotion(reg, terr, W, B, brand_id, pct_format=pct_format), check_supply(reg, terr, W, B, brand_id, pct_format=pct_format),
            check_competitor(reg, terr, W, ref, brand_id, exact_comparison=use_selected_baseline, pct_format=pct_format)]
