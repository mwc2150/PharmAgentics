"""Stage 1 to 3 steps of the spine, plus the story head and the competitor status, as plain functions.

The Briefing scripted baseline calls them in a fixed order; the MCP server (`pharmagentics.mcp`) exposes
them as tools an agent calls in the order it chooses. Same code in both, so the scripted baseline stays
the manager-off ablation (Briefing Architecture §9). The Forecast lane may reuse the period, feed health,
restatements and competitor status. Every number in returned text is a claim token `{cN}` filled by code.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import queries as q
from .brands import briefing_brand
from .checks import access_events, check_competitor_national, launch_date
from .definition import Definition, labels as definition_labels
from .lag_checks import national_ruled_out
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


def measure_label(col: str) -> str:
    return "new patients (NBRx)" if col == "nbrx" else "TRx"


def describe_comparison(c: Comparison | None, B: list[str]) -> str:
    """A comparison's weeks in words and dates, with no other digit (brief-007 FR-004)."""
    if not B:
        return "no earlier weeks, because the release starts with this period"
    if len(B) == 1:
        return f"the week of {B[0]}"
    if c is not None:
        if c.kind == "last_year":
            return f"the same weeks last year ({', '.join(B)})"
        if c.kind == "pre_launch":
            return f"the four weeks before Metacora launched ({B[0]} to {B[-1]})"
        return f"the weeks from {B[0]} to {B[-1]}"
    return f"the {_NUMBER.get(len(B), 'several')} weeks before ({B[0]} to {B[-1]})"


_NUMBER = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def comparison_tile(c: Comparison | None, B: list[str]) -> str:
    """The short label of a comparison, for a KPI tile or a table column."""
    if c is None or c.kind == "previous":
        return f"the previous {_NUMBER.get(len(B), 'several')} weeks" if len(B) != 1 else "the week before"
    return {"pre_launch": "the pre-launch weeks", "last_year": "the same weeks last year"}.get(c.kind, "the chosen weeks")


def comparison_since(c: Comparison | None, B: list[str]) -> str:
    """How a story headline says a change against an extra comparison: "down 2.2% since before Metacora launched"."""
    if c is not None and c.kind == "pre_launch":
        return "since before Metacora launched"
    if c is not None and c.kind == "last_year":
        return "on the same weeks last year"
    return f"on {comparison_tile(c, B)}"


def comparison_labels(c: Comparison | None, B: list[str]) -> dict:
    return {"comparison": f"{B[0]} to {B[-1]}" if B else None, "comparison_kind": c.kind if c is not None else "default"}


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
    extra_baselines: list[tuple[Comparison, list[str]]] = field(default_factory=list)  # each extra comparison and its weeks (FR-000e)
    ok_extra: list[list[str]] = field(default_factory=list)  # per extra comparison: reportable in every week of period and extra weeks
    ok_base_extra: list[list[str]] = field(default_factory=list)  # per extra comparison: reportable in every extra comparison week
    material: dict = field(default_factory=dict)  # territory -> beyond its normal range on the comparison weeks (screen)

    @property
    def col(self) -> str:
        """The metric column the story figures use: the primary measure (the first listed)."""
        return self.definition.primary_measure

    @property
    def extra_col(self) -> str | None:
        """The other measure when the definition lists both: shown beside the primary, never a second set of stories."""
        return next((m for m in self.definition.measure[1:]), None)

    @property
    def col_name(self) -> str:
        return "NBRx" if self.col == "nbrx" else "TRx"

    @property
    def measure_label(self) -> str:
        return measure_label(self.col)

    @property
    def extra_label(self) -> str | None:
        return measure_label(self.extra_col) if self.extra_col else None

    def has(self, grain: str) -> bool:
        return self.definition.has(grain)


def resolve(reg: Registry, question: str, brand_id: str = "BXA", *, comparison: Comparison | None = None,
            definition: Definition | dict | None = None) -> Period:
    """The period of one run. `definition` (brief-010) is what the brief is built from; None is the pre-selected
    values, and the old `comparison` keyword maps into it."""
    brand_id = briefing_brand(brand_id)
    d = Definition.coerce(definition, comparison)
    comparison = d.primary_comparison
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
    if d.comparison:
        if p.promotion_review:
            raise ValueError("The release-wide Promotion review uses its own lapse comparison.")
        available = {r[0] for r in reg.rows("select week_start::varchar from raw.calendar")}
        launch = launch_date(reg) if any(c.kind == "pre_launch" for c in d.comparison) else None
        weeks_for = [comparison_weeks(c, W, available, launch=launch) for c in d.comparison]
        if comparison is not None:
            p.baseline = weeks_for[0]
            p.baseline_source = "analyst's choice"
        p.extra_baselines = list(zip(d.comparison[1:], weeks_for[1:]))
    if not W:
        reg.labels = definition_labels(d, W, p.baseline)
        return p
    if comparison is None:
        p.baseline = [w for w in (q.shift(W[0], -i) for i in range(BASELINE_WEEKS, 0, -1)) if w >= first]
    weeks = sorted(set(W) | set(p.baseline))
    previous = q.shift(W[-1], -1)
    extra_weeks = {w for _, B in p.extra_baselines for w in B}
    health_weeks = sorted(set(weeks) | extra_weeks | ({previous} if previous >= first else set()))
    health = reg.rows(f"select week_start::varchar, territory_id, health_status, flag_reasons "
                      f"from reporting.v_feed_health where week_start in {q._dates(health_weeks)}")
    p.status = {(w, t): (h, r) for w, t, h, r in health}
    p.terrs = sorted({t for _, t in p.status})
    p.ok = [t for t in p.terrs if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in weeks)]
    p.ok_cur = [t for t in p.terrs if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in W)]
    p.ok_base = [t for t in p.terrs if p.baseline and all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in p.baseline)]
    for _, B in p.extra_baselines:
        p.ok_base_extra.append([t for t in p.terrs if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in B)])
        p.ok_extra.append([t for t in p.ok_cur if t in p.ok_base_extra[-1]])
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
        detail, tie_out = [], None
        if "DUPLICATE_RX_KEYS" in reasons or "MISSING_RX_KEYS" in reasons or "ROW_COUNT_MISMATCH" in reasons:
            obs = reg.claim("validate_feed", q.feed(w, t, "observed_rows"), "int", week=w, territory=t)
            exp = reg.claim("validate_feed", q.feed(w, t, "expected_key_count"), "int", week=w, territory=t)
            detail.append(f"{obs} rows against {exp} expected")
        if "DUPLICATE_RX_KEYS" in reasons:
            detail.append(f"{reg.claim('validate_feed', q.feed(w, t, 'duplicate_key_count'), 'int', week=w, territory=t)} duplicate keys")
            tie_out = duplicate_tie_out(reg, p, w, t)
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
        lines.append(f"- {q.name(t)}, week of {w}: not reportable ({names})" + (f"; {', '.join(detail)}." if detail else ".")
                     + (f" {tie_out}" if tie_out else ""))
    if len(flagged) > 5:
        lines.append("- More withheld cuts exist; see the evidence list.")
    return "\n".join(lines)


def duplicate_tie_out(reg: Registry, p: Period, week: str, terr: str) -> str | None:
    """brief-010 FR-004: what a naive sum of a duplicated feed overstates. The raw sum and the deduplicated figure
    are data-quality tie-outs, labelled as such, never metrics (the gate withholds the cut, so no metric is read)."""
    base = (f"from reporting.v_rx_duplicate_tieout where week_start = DATE '{week}' and territory_id = '{terr}' "
            f"and product_id = '{p.brand_id}'")
    if not reg.scalar(f"select count(*) {base}"):
        return None
    where = {"week": week, "territory": terr}
    raw = reg.claim("validate_feed", f"select naive_trx {base}", "int", scope="raw, before deduplication (data-quality tie-out)", **where)
    once = reg.claim("validate_feed", f"select deduplicated_trx {base}", "int", scope="each duplicated key counted once (data-quality tie-out)", **where)
    over = reg.claim("validate_feed", f"select naive_trx - deduplicated_trx {base}", "int", scope="overstatement of the raw sum (data-quality tie-out)", **where)
    pct = reg.claim("validate_feed", f"select 100.0 * (naive_trx - deduplicated_trx) / deduplicated_trx {base}", "pct",
                    scope="overstatement of the raw sum (data-quality tie-out)", **where)
    return (f"Raw, before deduplication, {q.name(terr)} {p.brand_id} TRx sums to {raw}; with each duplicated key counted once it is {once}, "
            f"so the raw sum overstates it by {over} TRx ({pct}). Do not quote the raw sum.")


def restated_window(p: Period) -> tuple[str, str]:
    """The brief's period as dates: its first week's Monday to its last week's Sunday."""
    return p.requested[0], q.iso(date.fromisoformat(p.requested[-1]) + timedelta(days=6))


def restatements(reg: Registry, p: Period, facts: list | None = None) -> list[str]:
    """brief-010 FR-005. A brief reports a restatement when the restated week is inside its period OR the
    restatement was published (its restated date) inside its period. Each is stated with the signed-off and
    restated TRx and the change, largest change first, three at most. `facts`, when given, receives each one's claims
    (territory, week, tokens, direction) for the restatement card; the numbers stay claim tokens."""
    first, last = restated_window(p)
    base = (f"from reporting.v_restatements where product_id = '{p.brand_id}' and (week_start in {q._dates(p.requested)} "
            f"or restated_at between DATE '{first}' and DATE '{last}')")
    rows = reg.rows(f"select week_start::varchar, territory_id, restated_at::varchar, reason {base} "
                    "order by abs(trx_restated - trx_signed_off) desc, week_start, territory_id, restated_at")
    out = []
    for w, t, when, reason in rows[:3]:
        one = f"{base} and week_start = DATE '{w}' and territory_id = '{t}' and restated_at = DATE '{when}'"
        sel = lambda expr: f"select {expr} {one}"  # noqa: E731
        scope = {"week": w, "territory": t}
        old = reg.claim("get_restatement", sel("trx_signed_off"), "int", **scope)
        new = reg.claim("get_restatement", sel("trx_restated"), "int", **scope)
        delta = reg.claim("get_restatement", sel("abs(trx_restated - trx_signed_off)"), "int", **scope)
        pct = reg.claim("get_restatement", sel("100.0 * abs(trx_restated - trx_signed_off) / trx_signed_off"), "pct", **scope)
        diff = reg.scalar(sel("trx_restated - trx_signed_off")) or 0
        direction = "up" if diff > 0 else "down" if diff < 0 else "flat"
        out.append(f"Restated: {q.name(t)} {p.brand_id} TRx for the week of {w} was {old} when first reported and is now {new}, "
                   f"{direction} {delta} TRx ({pct}). It was restated {when}; reason: {reason.lower().replace('_', ' ')}. "
                   "Quote the new value with this note.")
        if facts is not None:
            facts.append({"territory": t, "week": w, "restated_on": when, "old": old, "new": new, "change": delta, "pct": pct,
                          "direction": direction, "size": abs(diff)})
    return out


# Stage 3: competitive intelligence ----------------------------------------------------------------

_SCOPE = {"like_for_like": "like-for-like national", "all_reportable": "national over the territories reportable in the period",
          "projected": "projected national"}
_RULE_TILE = {"like_for_like": "Change, like for like", "all_reportable": "Change, all reportable territories",
              "projected": "Change, projected national"}


def national_basis(p: Period, col: str, rule: str | None = None) -> str:
    """Which territories a national figure counts, for this measure: the projected national is a TRx figure only."""
    mode = rule or p.definition.territory_rule
    return "like_for_like" if mode == "projected" and col != "trx" else mode


def national_sql(p: Period, col: str | None = None, rule: str | None = None,
                 extra: int | None = None) -> tuple[str | None, str | None, list[str] | None, list[str] | None]:
    """(the period's mean weekly national, the comparison weeks', the territories each counts) under a `territories`
    rule (the primary unless given), a measure and a comparison (the primary unless `extra` indexes an extra one). A
    figure is None when no territory can be counted."""
    col = col or p.col
    W, brand = p.weeks, p.brand_id
    B, ok, ok_base = (p.baseline, p.ok, p.ok_base) if extra is None else (p.extra_baselines[extra][1], p.ok_extra[extra], p.ok_base_extra[extra])
    mode = national_basis(p, col, rule)
    if mode == "projected":
        return q.projected_national(W, product=brand), (q.projected_national(B, product=brand) if B else None), None, None
    tc, tb = (p.ok_cur, ok_base) if mode == "all_reportable" else (ok, ok)
    cur = q.mean_weekly(W, terrs=tc, product=brand, col=col) if tc else None
    base = q.mean_weekly(B, terrs=tb, product=brand, col=col) if B and tb else None
    return cur, base, tc, tb


def _national_block(reg: Registry, p: Period, facts: dict, col: str, key: str, *, rule: str | None = None,
                    extra: int | None = None) -> list[str]:
    """The national KPI line for one measure, territories rule and comparison. The primary of each is the brief's own
    figure (`facts[key]`); an extra value adds a labelled figure beside it (`facts["avg_extra"]`), never a second story.
    Claims are made in the order the pre-selected definition always made them."""
    W = p.weeks
    brand, mode = p.brand_id, national_basis(p, col, rule)
    label = measure_label(col)
    cmp_, B = (p.comparison, p.baseline) if extra is None else p.extra_baselines[extra]
    vs = "the comparison weeks" if extra is None else describe_comparison(cmp_, B)
    cur, base, tc, tb = national_sql(p, col, rule, extra)
    if cur is None:
        return [] if key != "avg" else [
            "KPIs: no territory passes the feed gate in every one of these weeks, so no like-for-like national figure is given."
            if mode == "like_for_like" else
            "KPIs: no territory is reportable in every one of these weeks, so no national figure is given."]
    labels = {"territories": rule or p.definition.territory_rule, "measure": col}
    if extra is not None:
        labels.update(comparison_labels(cmp_, B))
    scope = _SCOPE[mode]
    entry = {"basis": mode, "label": label, "vs": vs}
    with reg.under(**labels):
        n = None if mode == "projected" else reg.claim(
            "get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} and {q._in('territory_id', tc)}", "int")
        avg = reg.claim("get_metric", cur, "int", scope=scope)
        total = reg.claim("get_metric", "select count(*) from raw.dim_territory", "int")
        entry.update(avg=avg, n=n, total=total)
        n_base = None
        if mode == "all_reportable" and base:
            n_base = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(B)} "
                               f"and {q._in('territory_id', tb)}", "int", scope="territories reportable in the comparison weeks")
            entry["n_base"] = n_base
        lines = []
        if base:
            change = reg.scalar(q.pct_change(cur, base)) or 0
            pct = reg.claim("get_metric", q.pct_change(cur, base), "pct", scope=scope)
            entry.update(pct=pct, word=word(change))
            if mode == "like_for_like":
                lines.append(f"KPIs: {brand} {label} averaged {avg} a week across {n} of {total} territories (like for like), "
                             f"{word(change)} {pct} against {vs}.")
            elif mode == "all_reportable":
                lines.append(f"KPIs: {brand} {label} averaged {avg} a week across {n} of {total} territories reportable in these weeks, "
                             f"{word(change)} {pct} against {vs}, when {n_base} of {total} were reportable (all reportable territories).")
            else:
                lines.append(f"KPIs: the projected national {brand} TRx averaged {avg} a week, {word(change)} {pct} against the projected "
                             f"national of {vs}.")
            if key == "avg" and mode == "like_for_like" and extra is None and rule is None:
                # headline total over every reportable cut, which a withheld cut distorts
                all_cur, all_base = q.mean_weekly(W, product=brand, col=col), q.mean_weekly(B, product=brand, col=col)
                naive = reg.scalar(q.pct_change(all_cur, all_base)) or 0
                if len(tc) < len(p.terrs) and abs(naive - change) >= 5:
                    p2 = reg.claim("get_metric", q.pct_change(all_cur, all_base), "pct", scope="headline total of reportable cuts")
                    lines.append(f"The headline total of reportable cuts is {word(naive)} {p2}, but that move comes mostly from withheld cuts, so it is a data artifact, not a business change.")
                    facts["artifact"] = lines[-1]
                    if abs(naive - change) >= MATERIAL_GAP * 100:  # brief-010 FR-011: the house gap, in points
                        dropped = [t for t in p.terrs if t not in tc]
                        facts["data_artifact"] = {
                            "brand": brand, "label": label, "col": col, "total_word": word(naive), "total_pct": p2, "like_word": word(change),
                            "like_pct": pct, "n": n, "noun": plural(claim_value(reg, n), "territory that reports", "territories that report"), "both": "both weeks" if len(W) == 1 and len(B) == 1 else "both periods",
                            "dropped": [q.name(t) for t in sorted(dropped, key=q.name)]}
    if extra is not None:
        entry["tile"] = f"Change against {comparison_tile(cmp_, B)}"
    elif rule is not None:
        entry["tile"] = _RULE_TILE[mode]
    elif key != "avg":
        entry["tile"] = f"Change in {label}"
    if key == "avg":
        facts["avg"] = entry
    else:
        entry["kind"] = "measure" if col != p.col else ("comparison" if extra is not None else "rule")
        facts.setdefault("avg_extra", []).append(entry)
    return lines


def kpis(reg: Registry, p: Period, facts: dict | None = None) -> list[str]:
    """Stage 3 lines. `facts`, when given, receives the same claims by name (avg, wow, changes, calendar), so the
    memo can build its territory table from them without a second claim for the same number. The definition's
    grain, territories and measure decide which national lines and territory changes exist (brief-010 FR-000c); each
    extra value of a list adds a labelled figure beside the primary (FR-000e)."""
    facts = {} if facts is None else facts
    W, B, ok, terrs, calendar = p.weeks, p.baseline, p.ok, p.terrs, p.calendar
    lines: list[str] = []
    if p.has("national"):
        lines = _national_block(reg, p, facts, p.col, "avg")
        if "avg" not in facts:
            return lines
        for rule in p.definition.territories[1:]:
            lines += _national_block(reg, p, facts, p.col, "avg_rule", rule=rule)
        for j in range(len(p.extra_baselines)):
            lines += _national_block(reg, p, facts, p.col, "avg_cmp", extra=j)
        if p.extra_col:
            lines += _national_block(reg, p, facts, p.extra_col, "avg_measure")
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
            cal_lines.append(f"The same weeks a year earlier were {word(ly)} {reg.claim('get_metric', q.pct_change(ly_cur, ly_base), 'pct', scope='same weeks last year')}. This is a calendar effect, not a business event.")
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
    pct_t = reg.claim('get_metric', q.pct_change(now_all, prev_all), 'pct', scope='week over week, reportable cuts')
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
        pct_b = reg.claim('get_metric', q.pct_change(now_b, prev_b), 'pct', scope='week over week, like for like')
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
        base = reg.claim("get_metric", base_sql, "pct", territory=t, scope="against the comparison weeks")
        base_change = reg.scalar(base_sql) or 0
        entry = {"territory": t, "ok": True, "base": {"word": word(base_change), "token": base, "change": base_change}, "wow": None}
        if p.col != "trx":  # the table's level column is the observed level, not the projection
            entry["level"] = reg.claim("get_metric", q.mean_weekly(W, terrs=[t], product=p.brand_id, col=p.col), "int",
                                       territory=t, scope=p.measure_label)
        if p.extra_col:
            with reg.under(measure=p.extra_col):
                entry["level_x"] = reg.claim("get_metric", q.mean_weekly(W, terrs=[t], product=p.brand_id, col=p.extra_col), "int",
                                             territory=t, scope=p.extra_label)
        weekly = ""
        if single:
            weekly = "week-over-week change withheld"
            if all(p.status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in (last, prev)):
                wow_sql = q.pct_change(q.trx_sum([last], terrs=[t], product=p.brand_id, col=p.col),
                                       q.trx_sum([prev], terrs=[t], product=p.brand_id, col=p.col))
                wow = reg.claim("get_metric", wow_sql, "pct", territory=t, scope="week over week")
                entry["wow"] = {"word": word(reg.scalar(wow_sql) or 0), "token": wow}
                weekly = f"{entry['wow']['word']} {wow} on the week before"
            weekly += "; "
        extra = ""
        if p.extra_col:  # the other measure beside the primary (brief-010 FR-000e)
            nb_sql = q.pct_change(q.mean_weekly(W, terrs=[t], product=p.brand_id, col=p.extra_col),
                                  q.mean_weekly(B, terrs=[t], product=p.brand_id, col=p.extra_col))
            with reg.under(measure=p.extra_col):
                nb = reg.claim("get_metric", nb_sql, "pct", territory=t, scope=f"against the comparison weeks, {p.extra_label}")
            entry["xm"] = {"word": word(reg.scalar(nb_sql) or 0), "token": nb}
            extra += f"; {p.extra_label} {entry['xm']['word']} {nb}"
        entry["xc"] = []
        for j, (cmp_, Bx) in enumerate(p.extra_baselines):  # each extra comparison beside the primary
            if t not in p.ok_extra[j]:
                entry["xc"].append(None)
                continue
            x_sql = q.pct_change(q.mean_weekly(W, terrs=[t], product=p.brand_id, col=p.col), q.mean_weekly(Bx, terrs=[t], product=p.brand_id, col=p.col))
            with reg.under(**comparison_labels(cmp_, Bx)):
                tok = reg.claim("get_metric", x_sql, "pct", territory=t, scope=f"against {comparison_tile(cmp_, Bx)}")
            entry["xc"].append({"word": word(reg.scalar(x_sql) or 0), "token": tok, "since": comparison_since(cmp_, Bx),
                                "tile": comparison_tile(cmp_, Bx)})
            extra += f"; {entry['xc'][-1]['word']} {tok} {entry['xc'][-1]['since']}"
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
    B = screen_weeks(reg, p, series)
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
        p.material[t] = material
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

def _against(reg: Registry, p: Period, t: str, kind: str, col: str) -> tuple[str, str] | None:
    """(word, token) for a territory's change set against the other territories or the national change; None for "none"
    or when no national figure can be given."""
    W, B, brand = p.weeks, p.baseline, p.brand_id
    if kind == "other_territories":
        peers = [o for o in p.ok if o != t]
        px, pb = q.mean_weekly(W, terrs=peers, product=brand, col=col), q.mean_weekly(B, terrs=peers, product=brand, col=col)
        sql, scope = q.pct_change(px, pb), "other territories"
    elif kind == "national":
        nx, nb, _, _ = national_sql(p)
        if not (nx and nb):
            return None
        sql, scope = q.pct_change(nx, nb), "national"
    else:
        return None
    with reg.under(relative_to=kind):
        token = reg.claim("get_metric", sql, "pct", scope=scope)
    return word(reg.scalar(sql) or 0), token


def screen_weeks(reg: Registry, p: Period, series: dict | None = None) -> list[str]:
    """The weeks the materiality screen compares with (brief-007 FR-001): the comparison weeks, except a multi-week
    period on the default comparison, which is screened against as many weeks before it as it is long, up to 13, that
    every like-for-like territory reports. The Assumptions state these weeks whenever they differ (assumptions first)."""
    if p.comparison is None and len(p.requested) > 1:
        series = series if series is not None else _series(reg, p.brand_id)
        preceding = (q.shift(p.requested[0], -i) for i in range(min(len(p.requested), 13), 0, -1))
        return [w for w in preceding if w >= p.first and all(w in series[t] for t in p.ok)]
    return list(p.baseline)


def within_normal_range(reg: Registry, p: Period, t: str) -> bool:
    """True for the territory the question names when the screen finds its change inside its normal range: it has a
    story only because it was asked about, and the brief says so rather than presenting the change as material."""
    if t != p.focus:
        return False
    if t not in p.material:
        screen(reg, p)
    return p.material.get(t) is False


def asked_note(reg: Registry, p: Period, t: str) -> str:
    """The sentence a story or §1 adds for a territory asked about whose change is inside its normal range."""
    return (f" {q.name(t)} moved within its normal range; it is reported because the question asks about it."
            if within_normal_range(reg, p, t) else "")


def territory_change(reg: Registry, p: Period, t: str, facts: dict | None = None) -> str:
    """A story's head. The primary measure sets the figures and each extra measure adds its own sentence; the primary
    `relative_to` sets what the change is set against (the other territories, the national change, or nothing) and each
    extra adds its figure beside it; each extra comparison adds the territory's change against it (FR-000e)."""
    W, B, col, brand = p.weeks, p.baseline, p.col, p.brand_id
    x, b = q.mean_weekly(W, terrs=[t], product=brand, col=col), q.mean_weekly(B, terrs=[t], product=brand, col=col)
    change = reg.scalar(q.pct_change(x, b)) or 0
    mean_x, mean_b = reg.claim('get_metric', x, 'int', territory=t), reg.claim('get_metric', b, 'int', territory=t)
    pct = reg.claim('get_metric', q.pct_change(x, b), 'pct', territory=t)
    kind, peer_word, peer_pct, tail, extras = p.definition.relative, None, None, "", []
    got = _against(reg, p, t, kind, col)
    if got:
        peer_word, peer_pct = got
        tail = f", while {'the other territories were' if kind == 'other_territories' else 'national was'} {peer_word} {peer_pct}"
    else:
        kind = "none"
    for more in p.definition.relative_to[1:]:  # an extra value adds its figure beside the primary
        if (extra := _against(reg, p, t, more, col)):
            extras.append({"kind": more, "word": extra[0], "pct": extra[1]})
            tail += f" and {'the other territories were' if more == 'other_territories' else 'national was'} {extra[0]} {extra[1]}"
    text = f"{q.name(t)}. {brand} {p.measure_label} averaged {mean_x} a week against {mean_b} before ({word(change)} {pct}){tail}."
    if facts is not None:
        facts.update(pct=pct, word=word(change), peer_pct=peer_pct, peer_word=peer_word, relative=kind, relative_extra=extras,
                     xm=None, xc=[])
    if p.extra_col:
        nx_, nb_ = q.mean_weekly(W, terrs=[t], product=brand, col=p.extra_col), q.mean_weekly(B, terrs=[t], product=brand, col=p.extra_col)
        n_change = reg.scalar(q.pct_change(nx_, nb_)) or 0
        with reg.under(measure=p.extra_col):
            n_x = reg.claim('get_metric', nx_, 'int', territory=t, scope=p.extra_label)
            n_b = reg.claim('get_metric', nb_, 'int', territory=t, scope=p.extra_label)
            n_pct = reg.claim('get_metric', q.pct_change(nx_, nb_), 'pct', territory=t, scope=p.extra_label)
        if facts is not None:
            facts["xm"] = {"word": word(n_change), "pct": n_pct, "label": p.extra_label}
        text += f" {p.extra_label[:1].upper()}{p.extra_label[1:]} averaged {n_x} a week against {n_b} before ({word(n_change)} {n_pct})."
    for j, (cmp_, Bx) in enumerate(p.extra_baselines):
        if t not in p.ok_extra[j]:
            continue
        sql = q.pct_change(x, q.mean_weekly(Bx, terrs=[t], product=brand, col=col))
        with reg.under(**comparison_labels(cmp_, Bx)):
            tok = reg.claim('get_metric', sql, 'pct', territory=t, scope=f"against {comparison_tile(cmp_, Bx)}")
        since = comparison_since(cmp_, Bx)
        if facts is not None:
            facts["xc"].append({"word": word(reg.scalar(sql) or 0), "pct": tok, "since": since})
        text += f" It is {word(reg.scalar(sql) or 0)} {tok} {since}."
    return text + asked_note(reg, p, t)


def _competitor_reading(reg: Registry, p: Period) -> dict:
    """What the national card reads of the competitor off the comparison weeks (brief-010 FR-006): the competitor
    check's verdict and the direction of each share (points, inside the house flat band). Directions only, no number
    is stated, so no claim is added. Empty `directions` when the brief has no comparison weeks."""
    W, B = p.weeks, p.baseline
    out: dict = {"check": check_competitor_national(reg, W), "directions": {}}
    if not B:
        return out
    for key, product in (("bxa_share", p.brand_id), ("competitor_share", "BXE")):
        now, then = reg.scalar(q.share(W, product)), reg.scalar(q.share(B, product))
        if now is None or then is None:
            continue
        out["directions"][key] = word(now - then)
    return out


def calendar_weeks_of(reg: Registry, weeks: list[str]) -> int:
    """How many of these weeks are holiday or plan-year-reset weeks (the flags the period's calendar mode reads)."""
    if not weeks:
        return 0
    return int(reg.scalar(f"select count(*) from raw.calendar where week_start in {q._dates(weeks)} "
                          f"and (holiday_flag = 1 or plan_year_reset = 1)") or 0)


def holiday_effect(reg: Registry, p: Period) -> bool:
    """The holiday driver (brief-010 packet NC): the period's weeks are calendar weeks (the period's own calendar mode,
    half or more of them) and the primary comparison weeks are not (fewer than half). Holiday weeks against last year's
    same holiday weeks carry no holiday effect, since both sides have it."""
    if not p.calendar or not p.baseline:
        return False
    return calendar_weeks_of(reg, p.baseline) * 2 < len(p.baseline)


def national_trx_direction(reg: Registry, p: Period) -> str | None:
    """Direction of national BXA TRx on the comparison weeks: the territories the brief counts (`territories`), the
    primary comparison, the house flat band. None without comparison weeks or a countable territory. No claim."""
    cur, base, _, _ = national_sql(p, "trx")
    if not (cur and base):
        return None
    return word(reg.scalar(q.pct_change(cur, base)) or 0)


def national_reading(reg: Registry, p: Period, story_checks, comp: dict | None = None, kpi: dict | None = None,
                     *, data_artifact: bool = False) -> dict | None:
    """The national card's facts, every brief (brief-010 FR-006, packet NC): national TRx direction, the competitor
    reading when Metacora has one (`comp` is `competitor_status`'s facts), the holiday driver and the drivers ruled
    out nationally from the checks of the territories that have a story (`story_checks`). None when the brief has no
    national direction to state. `kpi` is the KPI strip's own national facts: its percent token is reused, so the card
    adds no claim. `data_artifact`: the brief carries the national data-artifact card (FR-011), which then owns the
    national TRx direction, so this card states none (it would pin a data artifact on the competitor)."""
    trx = None if data_artifact else national_trx_direction(reg, p)
    reading = dict(comp or {})
    if comp:
        reading.update(_competitor_reading(reg, p))
    directions = dict(reading.get("directions") or {})
    if trx:
        directions["trx"] = trx
    if not directions:
        return None
    reading["directions"] = directions
    reading["trx"] = trx
    if kpi and trx and p.col == "trx" and kpi.get("pct"):
        reading["trx_pct"] = kpi["pct"]
    reading["holiday"] = holiday_effect(reg, p)
    reading["ruled_out"] = [] if p.calendar else national_ruled_out(story_checks)  # a calendar week opens no story, so no driver was tested
    return reading


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
    bxe = reg.claim("compare_competitors", share_w, "pct", product="BXE")
    bxa = reg.claim("compare_competitors", q.share(W, p.brand_id), "pct", product=p.brand_id)
    bxa_pre = reg.claim("compare_competitors", q.share(pre, p.brand_id), "pct", product=p.brand_id, weeks="before launch")
    if facts is not None:
        facts.update(bxe=bxe, bxa=bxa, pre=bxa_pre)
    return (f"{lead} (launched {launched}). This is a continuing story, week {since} since launch, {direction}. "
            f"Metacora held {bxe} of the four-brand basket and {p.brand_id} held {bxa}, against {bxa_pre} for {p.brand_id} in the four weeks before launch. "
            f"Confidence: Medium. The share loss is measured; its effect on volume is not separated from other drivers. Next: involve marketing and sales.")
