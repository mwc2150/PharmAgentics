"""Stage 1 to 3 steps of the spine, plus the story head and the competitor status, as plain functions.

The Briefing scripted baseline calls them in a fixed order; the MCP server (`pharmagentics.mcp`) exposes
them as tools an agent calls in the order it chooses. Same code in both, so the scripted baseline stays
the manager-off ablation (Briefing Architecture §9). The Forecast lane may reuse the period, feed health,
restatements and competitor status. Every number in returned text is a claim token `{cN}` filled by code.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from . import queries as q
from .brands import briefing_brand
from .checks import access_events, launch_date
from .definition import Definition, labels as definition_labels
from .registry import Registry
from .window import Comparison, comparison_weeks, parse

MATERIAL_CHANGE, MATERIAL_GAP, NOISE_Z = 0.10, 0.08, 2.5
BASELINE_WEEKS = 4  # comparison weeks: the four weeks before the requested window, any length (brief-007 FR-001)
COVERAGE_FLOOR = 0.98  # the feed gate's panel coverage floor, as in sql/001_reporting_views.sql (LOW_OR_INVALID_COVERAGE)


def word(change: float) -> str:
    return "up" if change > 0.5 else "down" if change < -0.5 else "flat"


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def plural(n: float, one: str, many: str) -> str:
    return one if n == 1 else many


def claim_value(reg: Registry, token: str) -> float:
    """The number a claim token stands for (a count or a change), for choosing a singular or a plural."""
    return float(reg.claims[int(token[2:-1]) - 1]["value"].replace(",", "").rstrip("%"))


@dataclass
class Period:
    """What one run is about, resolved by code before any interpretation (stages 1 to 3 bookkeeping)."""

    question: str
    first: str  # first week in the release
    latest: str  # latest closed week
    requested: list[str]  # weeks the question asks about, inside the release
    baseline: list[str]  # the weeks before, for comparison
    weeks: list[str] = field(default_factory=list)  # requested weeks minus calendar weeks when those are a minority
    focus: str | None = None  # territory the question names, if any
    note: str | None = None  # how the period was chosen, when the question gave none
    status: dict = field(default_factory=dict)  # (week, territory) -> (health_status, flag_reasons)
    terrs: list[str] = field(default_factory=list)  # territories with feed metadata in these weeks
    ok: list[str] = field(default_factory=list)  # like for like: every week of period and baseline passes the gate
    calendar: list = field(default_factory=list)  # calendar rows when the period is in calendar mode
    brand_id: str = "BXA"
    calendar_note: str | None = None  # set when calendar weeks were left out of the stories
    promotion: bool = False
    promotion_review: bool = False
    comparison: Comparison | None = None
    baseline_source: str = "default"
    definition: Definition = field(default_factory=Definition)  # brief-010: what this brief is built from
    ok_cur: list[str] = field(default_factory=list)  # reportable in every week of the period (territories = all_reportable)
    ok_base: list[str] = field(default_factory=list)  # reportable in every comparison week

    @property
    def col(self) -> str:
        """The metric column the story figures use: nbrx for a new-patients brief, trx otherwise (both: trx first)."""
        return "nbrx" if self.definition.measure == "nbrx" else "trx"

    @property
    def col_name(self) -> str:
        return "NBRx" if self.col == "nbrx" else "TRx"

    @property
    def measure_label(self) -> str:
        return "new patients (NBRx)" if self.col == "nbrx" else "TRx"

    @property
    def also_nbrx(self) -> bool:
        return self.definition.measure == "both"

    def has(self, grain: str) -> bool:
        return self.definition.has(grain)


def resolve(reg: Registry, question: str, brand_id: str = "BXA", *, comparison: Comparison | None = None,
            definition: Definition | dict | None = None) -> Period:
    """The period of one run. `definition` (brief-010) is what the brief is built from; None is the pre-selected
    values, and the old `comparison` keyword maps into it."""
    brand_id = briefing_brand(brand_id)
    d = Definition.coerce(definition, comparison)
    comparison = d.comparison
    first, latest = reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
    ask = parse(question, first, latest, briefing=brand_id == "BXA")
    W, explicit, note = ask["weeks"], ask.get("explicit_week", False), ask["note"]
    if d.first_week:  # the analyst chose the weeks: they win over the question's
        chosen = q.mondays(d.first_week, d.last_week or d.first_week)
        W, explicit, note = [w for w in chosen if first <= w <= latest], True, None
    p = Period(brand_id=brand_id, question=question, first=first, latest=latest, requested=W, baseline=[], focus=ask["territory"], note=note,
               definition=d)
    p.promotion = ask.get("promotion", False)
    p.promotion_review = p.promotion and not (ask["explicit_week"] or explicit)
    p.comparison = comparison
    if comparison is not None:
        if p.promotion_review:
            raise ValueError("The release-wide Promotion review uses its own lapse comparison.")
        available = {r[0] for r in reg.rows("select week_start::varchar from raw.calendar")}
        p.baseline = comparison_weeks(comparison, W, available)
        p.baseline_source = "analyst's choice"
    if not W:
        reg.labels = definition_labels(d, W, p.baseline)
        return p
    if comparison is None:
        p.baseline = [w for w in (q.shift(W[0], -i) for i in range(BASELINE_WEEKS, 0, -1)) if w >= first]
    weeks = sorted(set(W) | set(p.baseline))
    previous = q.shift(W[-1], -1)
    health_weeks = sorted(set(weeks) | ({previous} if previous >= first else set()))
    health = reg.rows(f"select week_start::varchar, territory_id, health_status, flag_reasons "
                      f"from reporting.v_feed_health where week_start in {q._dates(health_weeks)}")
    p.status = {(w, t): (h, r) for w, t, h, r in health}
    p.terrs = sorted({t for _, t in p.status})
    p.ok = [t for t in p.terrs if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in weeks)]
    p.ok_cur = [t for t in p.terrs if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in W)]
    p.ok_base = [t for t in p.terrs if p.baseline and all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in p.baseline)]
    cal_rows = reg.rows(f"select week_start::varchar, holiday_name, business_days, plan_year_reset from raw.calendar "
                        f"where week_start in {q._dates(W)} and (holiday_flag = 1 or plan_year_reset = 1)")
    cal_weeks = {r[0] for r in cal_rows}
    # Calendar mode when calendar weeks make up half or more of the period; otherwise screen the other weeks.
    p.calendar = cal_rows if len(cal_weeks) * 2 >= len(W) else []
    p.weeks = list(W)
    if cal_weeks and not p.calendar and not p.promotion_review:
        p.weeks = [w for w in W if w not in cal_weeks]
        p.calendar_note = "Calendar weeks in this period are left out of the stories below, because lower volume there is expected."
    reg.labels = definition_labels(d, W, p.baseline)
    return p


def describe(p: Period) -> str:
    W = p.requested
    return "week of " + W[0] if len(W) == 1 else "weeks " + W[0] + " to " + W[-1]


def outside_release(p: Period) -> str:
    return f"That period is outside the release, which runs from {p.first} to {p.latest}. Nothing was run."


# Stage 2: validation gate --------------------------------------------------------------------------

def data_health(reg: Registry, p: Period) -> str:
    W, terrs, status = p.requested, p.terrs, p.status
    flagged = sorted((w, t, status[(w, t)][1]) for w in W for t in terrs if status.get((w, t), ("PASS", ""))[0] == "FLAG")
    if len(W) == 1:
        n_ok = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where week_start = DATE '{W[0]}' and health_status = 'PASS'", "int", week=W[0])
        total = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where week_start = DATE '{W[0]}'", "int", week=W[0])
        head = f"Data health: {n_ok} of {total} territories pass the feed gate for {W[0]}."
    else:
        n_bad = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where health_status = 'FLAG' and week_start in {q._dates(W)}", "int")
        one = claim_value(reg, n_bad) == 1
        head = f"Data health: {n_bad} territory-{'week is' if one else 'weeks are'} withheld across these weeks."
    if not flagged:
        return head + " No cut is withheld."
    lines = [head + " Withheld cuts are left out of every like-for-like figure and story, and never read as zero demand."]
    for w, t, reasons in flagged[:5]:
        names = ", ".join(q.REASONS.get(r, r.lower()) for r in reasons.split(";") if r)
        detail = []
        if "DUPLICATE_RX_KEYS" in reasons or "MISSING_RX_KEYS" in reasons or "ROW_COUNT_MISMATCH" in reasons:
            obs = reg.claim("validate_feed", q.feed(w, t, "observed_rows"), "int", week=w, territory=t)
            exp = reg.claim("validate_feed", q.feed(w, t, "expected_key_count"), "int", week=w, territory=t)
            detail.append(f"{obs} rows against {exp} expected")
        if "DUPLICATE_RX_KEYS" in reasons:
            detail.append(f"{reg.claim('validate_feed', q.feed(w, t, 'duplicate_key_count'), 'int', week=w, territory=t)} duplicate keys")
        if "MISSING_RX_KEYS" in reasons:
            detail.append(f"{reg.claim('validate_feed', q.feed(w, t, 'missing_key_count'), 'int', week=w, territory=t)} missing keys")
        if "LOW_OR_INVALID_COVERAGE" in reasons:
            floor = reg.claim("validate_feed", f"select {COVERAGE_FLOOR} from reporting.v_feed_health limit 1", "dec2",
                              scope="feed gate coverage floor, the LOW_OR_INVALID_COVERAGE rule in sql/001_reporting_views.sql")
            detail.append(f"panel coverage {reg.claim('validate_feed', q.feed(w, t, 'panel_coverage_ratio'), 'dec3', week=w, territory=t)} against a {floor} floor")
        if "LATE_OR_UNKNOWN_DELIVERY" in reasons:
            target = reg.claim("validate_feed", q.feed(w, t, "expected_lag_days"), "int", week=w, territory=t, scope="delivery target")
            detail.append(f"{reg.claim('validate_feed', q.feed(w, t, 'actual_lag_days'), 'dec2', week=w, territory=t)} days after week end "
                          f"against a target of {target} days")
        lines.append(f"- {q.name(t)}, week of {w}: not reportable ({names})" + (f"; {', '.join(detail)}." if detail else "."))
    if len(flagged) > 5:
        lines.append("- More withheld cuts exist; see the evidence list.")
    return "\n".join(lines)


def restatements(reg: Registry, p: Period) -> list[str]:
    W = p.requested
    rows = reg.rows(
        "select week_start::varchar, territory_id, min(revised_at)::varchar, any_value(revision_reason) from raw.restatement_log "
        f"where product_id = '{p.brand_id}' and (week_start in {q._dates(W)} or revised_at between DATE '{W[0]}' and DATE '{q.shift(W[-1], 1)}') "
        "group by 1, 2 order by 1, 2")
    out = []
    for w, t, when, reason in rows[:3]:
        base = f"from raw.restatement_log where product_id = '{p.brand_id}' and week_start = DATE '{w}' and territory_id = '{t}'"
        old = reg.claim("get_restatement", f"select sum(trx_prior) {base}", "int", week=w, territory=t)
        new = reg.claim("get_restatement", f"select sum(trx_revised) {base}", "int", week=w, territory=t)
        out.append(f"Restated: {q.name(t)} {p.brand_id} TRx for the week of {w} was {old} when first reported and is now {new} "
                   f"(restated {when}; reason: {reason.lower().replace('_', ' ')}). Quote the new value with this note.")
    return out


# Stage 3: competitive intelligence ----------------------------------------------------------------

_SCOPE = {"like_for_like": "like-for-like national", "all_reportable": "national over the territories reportable in the period",
          "projected": "projected national"}


def national_basis(p: Period, col: str) -> str:
    """Which territories a national figure counts, for this measure: the projected national is a TRx figure only."""
    mode = p.definition.territories
    return "like_for_like" if mode == "projected" and col != "trx" else mode


def national_sql(p: Period, col: str | None = None) -> tuple[str | None, str | None, list[str] | None, list[str] | None]:
    """(the period's mean weekly national, the comparison weeks', the territories each counts) under the definition's
    `territories`. A figure is None when no territory can be counted."""
    col = col or p.col
    W, B, brand = p.weeks, p.baseline, p.brand_id
    mode = national_basis(p, col)
    if mode == "projected":
        return q.projected_national(W, product=brand), (q.projected_national(B, product=brand) if B else None), None, None
    tc, tb = (p.ok_cur, p.ok_base) if mode == "all_reportable" else (p.ok, p.ok)
    cur = q.mean_weekly(W, terrs=tc, product=brand, col=col) if tc else None
    base = q.mean_weekly(B, terrs=tb, product=brand, col=col) if B and tb else None
    return cur, base, tc, tb


def _national_block(reg: Registry, p: Period, facts: dict, col: str, key: str) -> list[str]:
    """The national KPI line for one measure under the definition's `territories`. Claims are made in the order the
    pre-selected definition always made them."""
    W, B = p.weeks, p.baseline
    brand, mode = p.brand_id, national_basis(p, col)
    label = "TRx" if col == "trx" else "new patients (NBRx)"
    cur, base, tc, tb = national_sql(p, col)
    if cur is None:
        return [f"KPIs: no territory passes the feed gate in every one of these weeks, so no like-for-like national figure is given."
                if mode == "like_for_like" else
                "KPIs: no territory is reportable in every one of these weeks, so no national figure is given."]
    scope = _SCOPE[mode]
    n = None if mode == "projected" else reg.claim(
        "get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} and {q._in('territory_id', tc)}", "int")
    avg = reg.claim("get_metric", cur, "int", scope=scope)
    total = reg.claim("get_metric", "select count(*) from raw.dim_territory", "int")
    facts[key] = {"avg": avg, "n": n, "total": total, "basis": mode, "label": label}
    n_base = None
    if mode == "all_reportable" and base:
        n_base = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(B)} "
                           f"and {q._in('territory_id', tb)}", "int", scope="territories reportable in the comparison weeks")
        facts[key]["n_base"] = n_base
    lines = []
    if base:
        change = reg.scalar(q.pct_change(cur, base)) or 0
        pct = reg.claim("get_metric", q.pct_change(cur, base), "pct1", scope=scope)
        facts[key].update(pct=pct, word=word(change))
        if mode == "like_for_like":
            lines.append(f"KPIs: {brand} {label} averaged {avg} a week across {n} of {total} territories (like for like), "
                         f"{word(change)} {pct} against the comparison weeks.")
        elif mode == "all_reportable":
            lines.append(f"KPIs: {brand} {label} averaged {avg} a week across {n} of {total} territories reportable in these weeks, "
                         f"{word(change)} {pct} against the comparison weeks, when {n_base} of {total} were reportable (all reportable territories).")
        else:
            lines.append(f"KPIs: the projected national {brand} TRx averaged {avg} a week, {word(change)} {pct} against the projected "
                         "national of the comparison weeks.")
        if key == "avg" and mode == "like_for_like":
            # headline total over every reportable cut, which a withheld cut distorts
            all_cur, all_base = q.mean_weekly(W, product=brand, col=col), q.mean_weekly(B, product=brand, col=col)
            naive = reg.scalar(q.pct_change(all_cur, all_base)) or 0
            if len(tc) < len(p.terrs) and abs(naive - change) >= 5:
                p2 = reg.claim("get_metric", q.pct_change(all_cur, all_base), "pct1", scope="headline total of reportable cuts")
                lines.append(f"The headline total of reportable cuts is {word(naive)} {p2}, but that move comes mostly from withheld cuts, so it is a data artifact, not a business change.")
                facts["artifact"] = lines[-1]
    return lines


def kpis(reg: Registry, p: Period, facts: dict | None = None) -> list[str]:
    """Stage 3 lines. `facts`, when given, receives the same claims by name (avg, wow, changes, calendar), so the
    memo can build its territory table from them without a second claim for the same number. The definition's
    grain, territories and measure decide which national lines and territory changes exist (brief-010 FR-000c)."""
    facts = {} if facts is None else facts
    W, B, ok, terrs, calendar = p.weeks, p.baseline, p.ok, p.terrs, p.calendar
    lines: list[str] = []
    if p.has("national"):
        lines = _national_block(reg, p, facts, p.col, "avg")
        if "avg" not in facts:
            return lines
        if p.also_nbrx:
            lines += _national_block(reg, p, facts, "nbrx", "avg_nbrx")
    else:
        facts["no_national"] = True
    if len(W) == 1 and B and p.has("national"):
        lines += week_over_week(reg, p, facts)
    lines += territory_changes(reg, p, facts)
    cal_lines = []
    if calendar:
        for w, holiday, bd, reset in calendar[:3]:
            days = reg.claim("lookup_calendar", q.calendar(w, "business_days"), "int", week=w)
            tag = "plan-year reset" if reset and holiday == "NONE" else holiday.lower().replace("_", " ")
            cal_lines.append(f"Calendar effect: the week of {w} is {tag} with {days} business days, so a lower volume is expected.")
        earlier_w, earlier_b = [q.shift(w, -52) for w in W], [q.shift(w, -52) for w in B]
        if earlier_b and min(earlier_w + earlier_b) >= p.first and p.comparison is None and p.has("national") and ok:
            ly_cur, ly_base = q.mean_weekly(earlier_w, terrs=ok, product=p.brand_id), q.mean_weekly(earlier_b, terrs=ok, product=p.brand_id)
            ly = reg.scalar(q.pct_change(ly_cur, ly_base)) or 0
            cal_lines.append(f"The same weeks a year earlier were {word(ly)} {reg.claim('get_metric', q.pct_change(ly_cur, ly_base), 'pct1', scope='same weeks last year')}. This is a calendar effect, not a business event.")
    facts["calendar"] = cal_lines
    return lines + cal_lines


def week_over_week(reg: Registry, p: Period, facts: dict | None = None) -> list[str]:
    """A one-week period against the week before (§5.3): every reportable cut, then like for like on the
    territories that report both weeks, so a withheld cut cannot pass for a drop in demand."""
    facts = {} if facts is None else facts
    w = p.weeks[0]
    prev = q.shift(w, -1)
    if prev < p.first:
        return []

    def passes(week, t):
        return p.status.get((week, t), ("FLAG", ""))[0] == "PASS"

    both = [t for t in p.terrs if passes(w, t) and passes(prev, t)]
    now_all, prev_all = q.trx_sum([w], product=p.brand_id), q.trx_sum([prev], product=p.brand_id)
    change = reg.scalar(q.pct_change(now_all, prev_all)) or 0
    now_t, prev_t = reg.claim('get_metric', now_all, 'int', week=w), reg.claim('get_metric', prev_all, 'int', week=prev)
    pct_t = reg.claim('get_metric', q.pct_change(now_all, prev_all), 'pct1', scope='week over week, reportable cuts')
    facts["wow"] = {"now": now_t, "prev": prev_t, "pct": pct_t, "word": word(change)}
    lines = [f"Week over week, summed over reportable cuts: {p.brand_id} TRx is {now_t} "
             f"against {prev_t} the week before ({word(change)} {pct_t})."]
    if both and len(both) < len(p.terrs):
        now_b, prev_b = q.trx_sum([w], terrs=both, product=p.brand_id), q.trx_sum([prev], terrs=both, product=p.brand_id)
        ch = reg.scalar(q.pct_change(now_b, prev_b)) or 0
        n = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start = DATE '{w}' "
                      f"and {q._in('territory_id', both)}", "int", scope="territories reporting both weeks")
        noun = plural(claim_value(reg, n), "territory that reports", "territories that report")
        first, last = (reg.claim('get_metric', prev_b, 'int', week=prev, scope='like for like'),
                       reg.claim('get_metric', now_b, 'int', week=w, scope='like for like'))
        pct_b = reg.claim('get_metric', q.pct_change(now_b, prev_b), 'pct1', scope='week over week, like for like')
        facts["wow_both"] = {"n": n, "noun": noun, "from": first, "to": last, "pct": pct_b, "word": word(ch)}
        lines.append(f"On the {n} {noun} both weeks, {p.brand_id} TRx went from {first} to {last} ({word(ch)} {pct_b}).")
    return lines


def territory_changes(reg: Registry, p: Period, facts: dict | None = None) -> list[str]:
    """§2 (brief-007 FR-007): each territory's period on the comparison weeks and, for a one-week period only
    (brief-008 FR-011), its week on the week before. Only like-for-like territories get a change; a territory
    with a withheld week is named without one. `facts["changes"]` keeps each territory's claims for the table."""
    facts = {} if facts is None else facts
    facts["changes"] = []
    W, B = p.weeks, p.baseline
    if not W or not B or not p.terrs or not p.has("territory"):
        return []
    single = len(W) == 1
    last, prev = W[-1], q.shift(W[-1], -1)
    what = "Change by territory" if p.col == "trx" else f"Change in {p.measure_label} by territory"
    lines = [f"{what}, like for like: the week of {last} on the week before, and the period on the "
             "comparison weeks:" if single else f"{what}, like for like, on the comparison weeks:"]
    for t in sorted(p.terrs, key=q.name):
        if t not in p.ok:
            lines.append(f"- {q.name(t)}: no change is given, because a week compared failed the feed gate.")
            facts["changes"].append({"territory": t, "ok": False, "base": None, "wow": None})
            continue
        base_sql = q.pct_change(q.mean_weekly(W, terrs=[t], product=p.brand_id, col=p.col), q.mean_weekly(B, terrs=[t], product=p.brand_id, col=p.col))
        base = reg.claim("get_metric", base_sql, "pct1", territory=t, scope="against the comparison weeks")
        base_change = reg.scalar(base_sql) or 0
        entry = {"territory": t, "ok": True, "base": {"word": word(base_change), "token": base, "change": base_change}, "wow": None}
        if p.col == "nbrx" or p.also_nbrx:
            entry["level_nbrx"] = reg.claim("get_metric", q.mean_weekly(W, terrs=[t], product=p.brand_id, col="nbrx"), "int",
                                            territory=t, scope="new patients (NBRx)")
        weekly = ""
        if single:
            weekly = "week-over-week change withheld"
            if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in (last, prev)):
                wow_sql = q.pct_change(q.trx_sum([last], terrs=[t], product=p.brand_id, col=p.col),
                                       q.trx_sum([prev], terrs=[t], product=p.brand_id, col=p.col))
                wow = reg.claim("get_metric", wow_sql, "pct1", territory=t, scope="week over week")
                entry["wow"] = {"word": word(reg.scalar(wow_sql) or 0), "token": wow}
                weekly = f"{entry['wow']['word']} {wow} on the week before"
            weekly += "; "
        extra = ""
        if p.also_nbrx:  # new patients beside TRx (brief-010 FR-000c)
            nb_sql = q.pct_change(q.mean_weekly(W, terrs=[t], product=p.brand_id, col="nbrx"), q.mean_weekly(B, terrs=[t], product=p.brand_id, col="nbrx"))
            nb = reg.claim("get_metric", nb_sql, "pct1", territory=t, scope="against the comparison weeks, new patients (NBRx)")
            entry["nbrx"] = {"word": word(reg.scalar(nb_sql) or 0), "token": nb}
            extra = f"; new patients (NBRx) {entry['nbrx']['word']} {nb}"
        lines.append(f"- {q.name(t)}: {weekly}{entry['base']['word']} {base} on the comparison weeks{extra}.")
        facts["changes"].append(entry)
    return lines


def _series(reg, brand_id="BXA"):
    rows = reg.rows(f"select week_start::varchar, territory_id, sum(trx) from {q.RX} where product_id = '{briefing_brand(brand_id)}' group by 1, 2")
    s: dict[str, dict[str, float]] = {}
    for w, t, x in rows:
        s.setdefault(t, {})[w] = float(x)
    return s


def screen(reg: Registry, p: Period, details: dict | None = None):
    """Territories whose change is beyond their own normal noise and beyond their peers' change.
    `details`, when given, receives each screened territory's change, gap and threshold."""
    W, ok, focus = p.weeks, p.ok, p.focus
    if not p.has("territory"):  # the brief's grain leaves territory stories out (brief-010 FR-000c)
        return [], []
    series = _series(reg, p.brand_id)
    B = p.baseline
    if p.comparison is None and len(p.requested) > 1:
        # The materiality screen compares every territory over the same reportable weeks.
        preceding = (q.shift(p.requested[0], -i) for i in range(min(len(p.requested), 13), 0, -1))
        B = [w for w in preceding if w >= p.first and all(w in series[t] for t in ok)]
    flagged_cal = {w for (w,) in reg.rows("select week_start::varchar from raw.calendar where holiday_flag = 1 or plan_year_reset = 1")}
    found, quiet = [], []
    for t in ok:
        if not B:
            continue
        x, b = _mean([series[t][w] for w in W]), _mean([series[t][w] for w in B])
        peers_x = sum(_mean([series[o][w] for w in W]) for o in ok if o != t)
        peers_b = sum(_mean([series[o][w] for w in B]) for o in ok if o != t)
        change, gap = x / b - 1, x / b - peers_x / peers_b if peers_b else 0
        hist = sorted(w for w in series[t] if w < W[0] and w not in flagged_cal)[-60:]
        devs = [series[t][w] / _mean([series[t][p] for p in hist[max(0, i - 4):i]]) - 1 for i, w in enumerate(hist) if i >= 4]
        sigma = max(statistics.pstdev(devs), 0.04) if len(devs) > 8 else 0.08
        threshold = max(MATERIAL_CHANGE, NOISE_Z * sigma / min(len(W), 3) ** 0.5)
        material = abs(change) >= threshold and abs(gap) >= MATERIAL_GAP
        if details is not None:
            details[t] = {"change": change, "gap": gap, "threshold": threshold}
        if material or t == focus:
            found.append({"territory": t, "kind": "territory", "impact": abs(x - b), "change": change})
        else:
            quiet.append(t)
    if (not focus or focus == "NATIONAL") and p.has("plan"):
        for e in access_events(reg, None, W, brand_id=p.brand_id):
            t = e["territory"]
            if t in ok and not any(s["territory"] == t for s in found) and B:
                plan_change = reg.scalar(q.pct_change(q.mean_weekly(W, plan=e["plan"], product=p.brand_id), q.mean_weekly(B, plan=e["plan"], product=p.brand_id)))
                if plan_change is not None and abs(plan_change) >= 15:
                    found.append({"territory": t, "kind": "plan", "impact": abs(reg.scalar(q.mean_weekly(W, plan=e["plan"], product=p.brand_id)) - reg.scalar(q.mean_weekly(B, plan=e["plan"], product=p.brand_id))), "plan": e["plan"]})
                    quiet = [x for x in quiet if x != t]
    found.sort(key=lambda s: -s["impact"])
    return found, quiet


def dropped_count(reg: Registry, p: Period, dropped: list[str]) -> str:
    return reg.claim("detect_changes", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(p.weeks)} "
                     f"and {q._in('territory_id', dropped)}", "int", scope="territories with no material change")


def dropped_line(reg: Registry, p: Period, dropped: list[str]) -> str:
    n = dropped_count(reg, p, dropped)
    return f"Considered and dropped: {n} {plural(claim_value(reg, n), 'territory moved', 'territories moved')} within their normal range."


# Stage 4 helpers: the story head and the competitor status -----------------------------------------

def territory_change(reg: Registry, p: Period, t: str, facts: dict | None = None) -> str:
    """A story's head. The measure sets the figures (NBRx beside TRx for both); `relative_to` sets what the change is
    set against: the other territories, the national change under the definition's territories, or nothing."""
    W, B, col, brand = p.weeks, p.baseline, p.col, p.brand_id
    x, b = q.mean_weekly(W, terrs=[t], product=brand, col=col), q.mean_weekly(B, terrs=[t], product=brand, col=col)
    change = reg.scalar(q.pct_change(x, b)) or 0
    mean_x, mean_b = reg.claim('get_metric', x, 'int', territory=t), reg.claim('get_metric', b, 'int', territory=t)
    pct = reg.claim('get_metric', q.pct_change(x, b), 'pct1', territory=t)
    kind, peer_word, peer_pct, tail = p.definition.relative_to, None, None, ""
    if kind == "other_territories":
        peers = [o for o in p.ok if o != t]
        px, pb = q.mean_weekly(W, terrs=peers, product=brand, col=col), q.mean_weekly(B, terrs=peers, product=brand, col=col)
        peer = reg.scalar(q.pct_change(px, pb)) or 0
        peer_pct, peer_word = reg.claim('get_metric', q.pct_change(px, pb), 'pct1', scope='other territories'), word(peer)
        tail = f", while the other territories were {peer_word} {peer_pct}"
    elif kind == "national":
        nx, nb, _, _ = national_sql(p)
        if nx and nb:
            peer = reg.scalar(q.pct_change(nx, nb)) or 0
            peer_pct, peer_word = reg.claim('get_metric', q.pct_change(nx, nb), 'pct1', scope='national'), word(peer)
            tail = f", while national was {peer_word} {peer_pct}"
        else:
            kind = "none"
    if facts is not None:
        facts.update(pct=pct, word=word(change), peer_pct=peer_pct, peer_word=peer_word, relative=kind)
    text = f"{q.name(t)}. {brand} {p.measure_label} averaged {mean_x} a week against {mean_b} before ({word(change)} {pct}){tail}."
    if p.also_nbrx:
        nx_, nb_ = q.mean_weekly(W, terrs=[t], product=brand, col="nbrx"), q.mean_weekly(B, terrs=[t], product=brand, col="nbrx")
        n_change = reg.scalar(q.pct_change(nx_, nb_)) or 0
        n_x, n_b = reg.claim('get_metric', nx_, 'int', territory=t, scope='new patients (NBRx)'), reg.claim('get_metric', nb_, 'int', territory=t, scope='new patients (NBRx)')
        n_pct = reg.claim('get_metric', q.pct_change(nx_, nb_), 'pct1', territory=t, scope='new patients (NBRx)')
        if facts is not None:
            facts.update(nbrx_pct=n_pct, nbrx_word=word(n_change))
        text += f" New patients (NBRx) averaged {n_x} a week against {n_b} before ({word(n_change)} {n_pct})."
    return text


def competitor_status(reg: Registry, p: Period, lead: str = "Competitor Metacora", facts: dict | None = None) -> str | None:
    """Metacora (BXE) as a continuing story: weeks since launch, direction, and the basket shares."""
    W = p.weeks
    launched = launch_date(reg)
    if launched is None or launched > W[-1]:
        return None
    share_w = q.share(W, "BXE")
    if (reg.scalar(share_w) or 0) < 5:
        return None
    pre = [q.shift(launched, -i) for i in range(4, 0, -1)]
    since = reg.claim("compare_competitors", f"select datediff('week', DATE '{launched}', week_start) from raw.calendar "
                      f"where week_start = DATE '{W[-1]}'", "int")
    earlier = [q.shift(w, -8) for w in W]
    trend = (reg.scalar(share_w) or 0) - (reg.scalar(q.share(earlier, "BXE")) or 0)
    direction = "still growing" if trend > 1 else "now flat" if trend > -1 else "declining"
    bxe = reg.claim("compare_competitors", share_w, "pct1", product="BXE")
    bxa = reg.claim("compare_competitors", q.share(W, p.brand_id), "pct1", product=p.brand_id)
    bxa_pre = reg.claim("compare_competitors", q.share(pre, p.brand_id), "pct1", product=p.brand_id, weeks="before launch")
    if facts is not None:
        facts.update(bxe=bxe, bxa=bxa, pre=bxa_pre)
    return (f"{lead} (launched {launched}). This is a continuing story, week {since} since launch, {direction}. "
            f"Metacora held {bxe} of the four-brand basket and {p.brand_id} held {bxa}, against {bxa_pre} for {p.brand_id} in the four weeks before launch. "
            f"Confidence: Medium. The share loss is measured; its effect on volume is not separated from other drivers. Next: involve marketing and sales.")
