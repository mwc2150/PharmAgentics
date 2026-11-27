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


PROMO_CHANNELS = (("rep_calls_aggregated", "rep calls", "int"), ("digital_impressions", "digital impressions", "int"),
                  ("samples_units", "samples", "int"), ("speaker_programs", "speaker programs", "dec1"))
SPARSE_FLOOR = {"speaker_programs": 2.0}  # a sparse count (about one a week) moves only by this much a week, so noise is not a move
CONTROL_NAMES = {"access": "access", "competitor": "the competitor launch", "holiday": "the calendar"}  # what the line says


def _moved(column: str, now, before) -> bool:
    """Did one channel move enough to test: a change of PROMOTION_CHANGE_PCT or more against the comparison weeks (a
    channel that was zero and is not, moved), and, for a sparse count, by at least its floor a week."""
    if now is None or before is None:
        return False
    if abs(now - before) < SPARSE_FLOOR.get(column, 0.0):
        return False
    return now > 0 if before == 0 else abs(100 * (now / before - 1)) >= PROMOTION_CHANGE_PCT


def _promo_cuts(reg: Registry, terr: str, W, B, brand_id: str = "BXA") -> list[tuple]:
    """Per tested lag, every channel's average over the period and over the comparison weeks, both read that many weeks
    earlier: (lag, current, baseline, {column: (period level, comparison level)}). A window with a source week missing is
    left out, as `_lagged_levels` does for one column."""
    if not W or not B:
        return []
    columns = [c for c, _, _ in PROMO_CHANNELS]
    cuts = []
    for lag in DRIVER_LAGS:
        current, baseline = ([q.shift(w, -lag) for w in window] for window in (W, B))
        levels = []
        for window in (current, baseline):
            row = reg.rows(f"select count(distinct week_start) filter (where {columns[0]} is not null), "
                           f"{', '.join(f'avg({c})' for c in columns)} from raw.promo_activity where product_id = '{brand_id}' "
                           f"and territory_id = '{terr}' and week_start in {q._dates(window)}")[0]
            levels.append(row[1:] if row[0] == len(window) else None)
        if all(level is not None and level[0] is not None for level in levels):
            cuts.append((lag, current, baseline, {c: (levels[0][i], levels[1][i]) for i, c in enumerate(columns)}))
    return cuts


def _word(change: float | None) -> str:
    return "flat" if change is None else "up" if change > 0.5 else "down" if change < -0.5 else "flat"


def _verb(word: str, token: str) -> str:
    return {"up": f"rose {token}", "down": f"fell {token}"}.get(word, f"held flat ({token})")


def _outcome(reg: Registry, terr: str, W, B, brand_id: str, col: str) -> dict:
    """The territory's own weekly level and change on the period against the comparison weeks, for one measure: claims
    labelled with that measure, so a TRx figure is never read as a new-patient one."""
    x, b = q.mean_weekly(W, terrs=[terr], product=brand_id, col=col), q.mean_weekly(B, terrs=[terr], product=brand_id, col=col)
    change = reg.scalar(q.pct_change(x, b))
    fmt = "dec1" if col == "nbrx" else "int"
    with reg.under(measure=col):
        before = reg.claim("get_metric", b, fmt, territory=terr, scope="comparison weeks")
        after = reg.claim("get_metric", x, fmt, territory=terr, scope="period")
        pct = reg.claim("get_metric", q.pct_change(x, b), "pct", territory=terr)
    return {"measure": "NBRx" if col == "nbrx" else "TRx", "before": before, "after": after, "change": pct, "direction": _word(change)}


def _channels(reg: Registry, terr: str, lag: int, current, baseline, levels: dict, brand_id: str) -> list[dict]:
    """All four channels, aggregated (never a rep), the period against the comparison weeks at one lag: claims and a flag
    for whether the channel moved by the rule that decides testability."""
    out = []
    for column, label, fmt in PROMO_CHANNELS:
        now, before = levels[column]
        if now is None or before is None:
            continue
        recent, earlier = (q.context_mean("promo_activity", column, window, terr, product=brand_id) for window in (current, baseline))
        out.append({"channel": label,
                    "before": reg.claim("lookup_promo", earlier, fmt, territory=terr, weeks=baseline),
                    "after": reg.claim("lookup_promo", recent, fmt, territory=terr, weeks=current),
                    "change": reg.claim("lookup_promo", q.pct_change(recent, earlier), "pct", territory=terr, lag=lag, channel=label) if before else None,
                    "direction": _word(100 * (now / before - 1)) if before else ("up" if now > 0 else "flat"),
                    "moved": _moved(column, now, before)})
    return out


def _held_level(reg: Registry, terr: str, W, B, current, baseline, brand_id: str) -> list[str]:
    """The other territories whose promotion activity held level on the same weeks (no channel moved, at the verdict's
    lag) and whose TRx is reportable in every week compared: the comparison group for the effect."""
    columns = [c for c, _, _ in PROMO_CHANNELS]
    both = sorted(set(current) | set(baseline))
    cur, base = q._dates(current), q._dates(baseline)
    cells = ", ".join(f"avg({c}) filter (where week_start in {cur}), avg({c}) filter (where week_start in {base})" for c in columns)
    rows = reg.rows(f"select territory_id, count(distinct week_start), {cells} from raw.promo_activity "
                    f"where product_id = '{brand_id}' and week_start in {q._dates(both)} and territory_id <> '{terr}' group by territory_id")
    weeks = sorted(set(W) | set(B))
    reportable = {r[0] for r in reg.rows(f"select territory_id from reporting.v_feed_health where week_start in {q._dates(weeks)} "
                                         f"and health_status = 'PASS' group by 1 having count(distinct week_start) = {len(weeks)}")}
    held = []
    for t, n, *values in rows:
        pairs = list(zip(values[0::2], values[1::2]))
        if n == len(both) and t in reportable and not any(_moved(c, now, before) for c, (now, before) in zip(columns, pairs)):
            held.append(t)
    return sorted(held)


def _effect_sql(terr: str, peers: list[str], W, B, brand_id: str, agg: str) -> str:
    """One value: the lowest (`min`) or highest (`max`) implied extra weekly TRx across the comparison territories. Each
    is the territory's period TRx less its comparison-weeks TRx scaled by that comparison territory's own change."""
    every = sorted(set(W) | set(B))
    return (f"with m as (select territory_id, sum(trx) filter (where week_start in {q._dates(W)}) / {len(W)}.0 as w, "
            f"sum(trx) filter (where week_start in {q._dates(B)}) / {len(B)}.0 as b from {q.RX} "
            f"where product_id = '{brand_id}' and week_start in {q._dates(every)} and {q._in('territory_id', [terr, *peers])} group by territory_id), "
            f"d as (select (select w from m where territory_id = '{terr}') - (select b from m where territory_id = '{terr}') * w / nullif(b, 0) as x "
            f"from m where territory_id <> '{terr}') select {agg}(case when abs(x) < 0.5 then 0 else x end) from d")


def _effect(reg: Registry, terr: str, W, B, current, baseline, brand_id: str) -> dict | None:
    """The territory's TRx against territories whose promotion held level over the same weeks (never ROI or attribution):
    extra TRx a week as a range, lowest to highest of the implied effect across those territories. None when no territory
    held level."""
    peers = _held_level(reg, terr, W, B, current, baseline, brand_id)
    if not peers:
        return None
    with reg.under(measure="trx"):
        low = reg.claim("get_metric", _effect_sql(terr, peers, W, B, brand_id, "min"), "int", territory=terr, scope="comparison territories")
        high = reg.claim("get_metric", _effect_sql(terr, peers, W, B, brand_id, "max"), "int", territory=terr, scope="comparison territories")
    n = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} "
                  f"and product_id = '{brand_id}' and {q._in('territory_id', peers)}", "int", scope="comparison territories")
    threshold = reg.claim("lookup_promo", f"select {PROMOTION_CHANGE_PCT} from raw.calendar limit 1", "pct", scope="promotion moved")
    return {"low": low, "high": high, "territories": n, "threshold": threshold, "held_level": peers}


def _controls(reg: Registry, terr: str, W, B, brand_id: str, use_selected_baseline: bool) -> list[str]:
    """The controls promotion is judged after: the drivers among access, competitor and the calendar that are supported
    for this territory and these weeks, as card ids (access, competitor, holiday). Run on a scratch registry with the
    same calls and weeks as the story's own checks, so they state no number and the verdicts equal the story's. A data
    artifact is not read here: a flagged feed leaves promotion inconclusive before this runs (no complete TRx)."""
    scratch = reg.scratch()
    ref = B if use_selected_baseline else context_baseline(W, B)
    found = []
    if check_access(scratch, terr, W, B, brand_id=brand_id).verdict == "supported":
        found.append("access")
    if check_competitor(scratch, terr, W, ref, brand_id, exact_comparison=use_selected_baseline, pct_format="pct").verdict == "supported":
        found.append("competitor")
    if B and 2 * int(reg.scalar(f"select count(*) from raw.calendar where week_start in {q._dates(B)} "
                               "and (holiday_flag = 1 or plan_year_reset = 1)") or 0) >= len(B):  # the period's own calendar-mode rule
        found.append("holiday")
    return found


def _names(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def check_promotion(reg: Registry, terr: str, W, B, brand_id: str = "BXA", *, use_selected_baseline: bool = False) -> Check:
    """Promotion against the brief's stated comparison weeks B, the same weeks as TRx (assumptions first): a longer,
    unstated window can hold a lapse and turn a recovery into a push. A lapse still running gets a continuing card.

    Controls first: where a control (access, competitor, the calendar) is also supported for these weeks, the verdict is
    `not_separable`. A promotion that did not move in any channel at any tested lag is `not_testable`, never `ruled_out`
    (that is promotion that moved with TRx not following). The direction test stays on rep calls against TRx. Every
    verdict but `insufficient` carries `detail["promotion"]`: the structure the story card shows (new patients first, then
    TRx, then all four channels at the verdict's lag, the effect against comparable territories, the re-check date)."""
    cuts = _promo_cuts(reg, terr, W, B, brand_id)
    trx = _trx_direction(reg, terr, W, B, brand_id)
    if not cuts or trx is None:
        return Check("promotion", "insufficient", "Promotion: insufficient. No complete TRx and promotion comparison is available.")
    calls = PROMO_CHANNELS[0][0]
    matches = [c for c in cuts if c[3][calls][1] and abs(100 * (c[3][calls][0] / c[3][calls][1] - 1)) >= PROMOTION_CHANGE_PCT
               and (c[3][calls][0] - c[3][calls][1]) * trx > 0]
    moving = [c for c in cuts if any(_moved(col, *c[3][col]) for col, _, _ in PROMO_CHANNELS)]
    lag, current, baseline, levels = (matches or moving or cuts)[0]  # the lag the verdict rests on; else the first where a channel moved
    avg, prior = levels[calls]
    channels = _channels(reg, terr, lag, current, baseline, levels, brand_id)
    pct, a, b = channels[0]["change"], channels[0]["after"], channels[0]["before"]
    recheck = q.shift(W[-1], len(B))  # the period's last week plus as many weeks as the comparison
    name = q.name(terr)
    nbrx, trx_fig = _outcome(reg, terr, W, B, brand_id, "nbrx"), _outcome(reg, terr, W, B, brand_id, "trx")
    base = {"lag": lag, "lag_label": LAG_LABELS[lag], "tested": list(LAG_LABELS), "new_patients": nbrx, "trx": trx_fig,
            "channels": channels, "recheck": recheck}
    # New patients lead, then TRx as the follow-through; the verdict's own direction test is TRx's.
    outcome = (f"New patients (NBRx) in {name} {_verb(nbrx['direction'], nbrx['change'])} and TRx "
               f"{_verb(trx_fig['direction'], trx_fig['change'])} on the comparison weeks.")
    tail = f"Re-check after {recheck}."
    if not matches:
        if not any(_moved(c, *cut[3][c]) for cut in cuts for c, _, _ in PROMO_CHANNELS):
            return Check("promotion", "not_testable", "Promotion: not testable; activity held level, so its effect cannot be measured this period. "
                         f"All four channels stayed near their comparison-week levels at every tested lag. {tail}",
                         {"promotion": {**base, "verdict": "not_testable", "effect": None}})
        moved = [ch["channel"] for ch in channels if ch["moved"]]
        moved_note = f" {_names(moved)[:1].upper()}{_names(moved)[1:]} moved, and TRx did not follow." if moved else ""
        return Check("promotion", "ruled_out", f"Promotion: ruled out. No tested lag lines up with TRx. {outcome} "
                     f"Aggregated calls averaged {a} a week against {b} in the comparison weeks{_lag_note(lag)}.{moved_note} {tail}",
                     {"promotion": {**base, "verdict": "ruled_out", "effect": None}})
    direction = "lower" if avg < prior else "higher"
    lapse = _lapse_in(reg, terr, baseline, brand_id) if avg > prior else None
    lapse = lapse if lapse and lapse[1] < current[-1] else None  # calls came back inside the period: recovery
    calls_line = f"Aggregated calls averaged {a} a week against {b} in the comparison weeks{_lag_note(lag)}"
    separable = _controls(reg, terr, W, B, brand_id, use_selected_baseline)
    if separable:  # a control moved in the same weeks: the TRx change cannot be credited to promotion
        names = _names([CONTROL_NAMES[c] for c in separable])
        recovery = f" This is recovery after the promotion lapse of {lapse[0]} to {lapse[1]}, not a push." if lapse else ""
        return Check("promotion", "not_separable", f"Promotion: cannot be separated from {names} in these weeks. {outcome} "
                     f"{calls_line} ({pct} {direction}), {LAG_LABELS[lag]}.{recovery} {tail}",
                     {"promotion": {**base, "verdict": "not_separable", "separable_from": separable, "effect": None}})
    effect = _effect(reg, terr, W, B, current, baseline, brand_id)
    against = (f"Compared with territories without a promotion change, this implies {effect['low']} to {effect['high']} extra TRx a week."
               if effect else "No other territory held its promotion level in these weeks, so no comparison with other territories is given.")
    structure = {**base, "verdict": "supported", "effect": effect and {
        **effect, "method": "the lowest to the highest implied extra weekly TRx across the comparison territories"}}
    if lapse:  # the comparison holds a lapse: calls coming back is recovery, not a push (mentor review 2.1)
        return Check("promotion", "supported", f"Promotion: supported as recovery after the promotion lapse of {lapse[0]} to "
                     f"{lapse[1]}, {LAG_LABELS[lag]}. {outcome} {calls_line}, which include lapse weeks ({pct} {direction}). {against} {tail}",
                     {"lag": lag, "lapse": lapse, "promotion": structure})
    return Check("promotion", "supported", f"Promotion: supported as an association, {LAG_LABELS[lag]}. {outcome} "
                 f"{calls_line} ({pct} {direction}). {against} {tail}", {"lag": lag, "promotion": structure})


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
            check_promotion(reg, terr, W, B, brand_id, use_selected_baseline=use_selected_baseline),
            check_supply(reg, terr, W, B, brand_id),
            check_competitor(reg, terr, W, ref, brand_id, exact_comparison=use_selected_baseline, pct_format="pct")]


def national_ruled_out(story_checks) -> list[str]:
    """Drivers ruled out nationally (brief-010 FR-006, packet NC): access, promotion or supply is ruled out unless a
    territory that has its own story card in this brief supports it or cannot rule it out (inconclusive, insufficient
    or never tested). `story_checks` holds each story territory's checks, as a list or a {driver: Check} dict, exactly
    the ones the brief ran for its cards, so no check runs again and no claim is added. A territory without a story
    does not keep a driver off the list; a brief with no story territory rules all three out."""
    verdicts = [{c.driver: c.verdict for c in (checks.values() if isinstance(checks, dict) else checks)} for checks in story_checks]
    return [d for d in ("access", "promotion", "supply") if all(v.get(d) == "ruled_out" for v in verdicts)]
