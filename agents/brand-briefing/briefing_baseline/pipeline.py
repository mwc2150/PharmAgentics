"""Briefing lane, scripted baseline (Evaluation Pack §6): a fixed pipeline with a fixed order of
checks and a templated brief. No model. Stages follow the System Architecture spine:

1 load and pin -> 2 validation gate -> 3a competitive intelligence -> 4a fixed-order investigation
-> 5 template narrative (claim tokens) -> 6 verification (no digit outside a claim token).
"""
from __future__ import annotations

import statistics

from pharmagentics.tools import DEFAULT_DB, Registry
from pharmagentics.tools import queries as q
from pharmagentics.tools.checks import OWNER, access_events, confidence, launch_date, run_checks
from pharmagentics.tools.registry import digits_outside_tokens
from pharmagentics.tracing import finish, span

from pharmagentics.tools.window import parse

MATERIAL_CHANGE, MATERIAL_GAP, NOISE_Z, MAX_STORIES = 0.10, 0.08, 2.5, 4


def _word(change: float) -> str:
    return "up" if change > 0.5 else "down" if change < -0.5 else "flat"


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def answer(question: str, db=DEFAULT_DB) -> dict:
    reg = Registry(db)
    try:
        return _brief(reg, question)
    finally:
        reg.close()


def _brief(reg: Registry, question: str) -> dict:
    first, latest = reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
    ask = parse(question, first, latest)
    W = ask["weeks"]
    if not W:
        return _envelope(reg, f"That period is outside the release, which runs from {first} to {latest}. Nothing was run.", False)
    n_b = 4 if len(W) == 1 else min(len(W), 13)
    B = [w for w in (q.shift(W[0], -i) for i in range(n_b, 0, -1)) if w >= first]
    focus = ask["territory"]
    out: list[str] = []
    abstained = False

    with span("1_load_and_pin", inputs={"question": question}, data_version=reg.data_version) as sp:
        out.append(f"Brief for {'week of ' + W[0] if len(W) == 1 else 'weeks ' + W[0] + ' to ' + W[-1]}. "
                   f"Data version {reg.data_version}. Product: BXA. Territory questions use only cuts that pass the feed gate.")
        if ask["note"]:
            out.append(ask["note"])
        finish(sp, {"weeks": W, "baseline_weeks": B, "territory": focus, "data_version": reg.data_version})

    with span("2_validation_gate") as sp:
        weeks = sorted(set(W) | set(B))
        health = reg.rows(f"select week_start::varchar, territory_id, health_status, flag_reasons "
                          f"from reporting.v_feed_health where week_start in {q._dates(weeks)}")
        status = {(w, t): (h, r) for w, t, h, r in health}
        terrs = sorted({t for _, t in status})
        ok = [t for t in terrs if all(status.get((w, t), ("FLAG", ""))[0] == "PASS" for w in weeks)]
        out.append(_data_health(reg, W, terrs, status))
        out += _restatements(reg, W)  # EV-1.2
        finish(sp, {"like_for_like_territories": ok})

    with span("3a_competitive_intelligence") as sp:
        cal_rows = reg.rows(f"select week_start::varchar, holiday_name, business_days, plan_year_reset from raw.calendar "
                            f"where week_start in {q._dates(W)} and (holiday_flag = 1 or plan_year_reset = 1)")
        cal_weeks = {r[0] for r in cal_rows}
        # Calendar mode when calendar weeks make up half or more of the window; otherwise screen the other weeks.
        calendar = cal_rows if len(cal_weeks) * 2 >= len(W) else []
        if cal_weeks and not calendar:
            W = [w for w in W if w not in cal_weeks]
            out.append("Calendar weeks in this period are left out of the stories below, because lower volume there is expected.")
        out += _kpis(reg, W, B, ok, terrs, calendar)
        found, dropped = ([], []) if calendar else _screen(reg, W, B, ok, focus)
        finish(sp, {"calendar_mode": bool(calendar), "candidates": [f["territory"] for f in found]})

    with span("4a_investigation") as sp:
        if calendar:
            out.append("No story is opened for a calendar week. Expect a rebound in the next regular week.")
        else:
            if focus in terrs and focus not in ok:
                out.append(f"{q.name(focus)} has withheld cuts in these weeks, so no like-for-like story is given for it.")
            shown = 0
            for s in found[:MAX_STORIES]:
                shown += 1
                with span(f"story_{shown}_{s['territory']}", inputs={"territory": s["territory"], "kind": s["kind"]}) as story_sp:
                    text, abst = _story(reg, shown, s, W, B, ok)
                    finish(story_sp, {"abstained": abst})
                out.append(text)
                abstained |= abst
            comp = _competitor_story(reg, W, B, shown + 1)
            if comp:
                out.append(comp)
                shown += 1
            if shown == 0:
                out.append("Routine week. No material change was found, and territory swings stayed in their normal range.")
            elif dropped:
                n_drop = reg.claim("detect_changes", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} "
                                   f"and {q._in('territory_id', dropped)}", "int", scope="territories with no material change")
                out.append(f"Considered and dropped: {n_drop} territories moved within their normal range.")
        finish(sp, {"abstained": abstained})

    with span("5_narrative") as sp:
        template = "\n".join(x for x in out if x)
        finish(sp, {"template_chars": len(template), "claims": len(reg.claims)})

    with span("6_verification") as sp:
        bad = digits_outside_tokens(template)
        finish(sp, {"digits_outside_tokens": bad})
        if bad:
            raise AssertionError(f"digit outside a claim token: {bad[:3]}")
    return _envelope(reg, reg.render(template), abstained)


def _data_health(reg, W, terrs, status) -> str:
    flagged = sorted((w, t, status[(w, t)][1]) for w in W for t in terrs if status.get((w, t), ("PASS", ""))[0] == "FLAG")
    if len(W) == 1:
        n_ok = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where week_start = DATE '{W[0]}' and health_status = 'PASS'", "int", week=W[0])
        total = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where week_start = DATE '{W[0]}'", "int", week=W[0])
        head = f"Data health: {n_ok} of {total} territories pass the feed gate for {W[0]}."
    else:
        n_bad = reg.claim("validate_feed", f"select count(*) from reporting.v_feed_health where health_status = 'FLAG' and week_start in {q._dates(W)}", "int")
        head = f"Data health: {n_bad} territory-weeks are withheld across these weeks."
    if not flagged:
        return head + " No cut is withheld."
    lines = [head + " Withheld cuts are left out of every figure below and never read as zero demand:"]
    for w, t, reasons in flagged[:5 if len(W) > 1 else 8]:
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
            detail.append(f"panel coverage {reg.claim('validate_feed', q.feed(w, t, 'panel_coverage_ratio'), 'dec3', week=w, territory=t)}")
        if "LATE_OR_UNKNOWN_DELIVERY" in reasons:
            detail.append(f"{reg.claim('validate_feed', q.feed(w, t, 'actual_lag_days'), 'dec2', week=w, territory=t)} days after week end")
        lines.append(f"- {q.name(t)}, week of {w}: not reportable ({names})" + (f"; {', '.join(detail)}." if detail else "."))
    if len(flagged) > 5 and len(W) > 1:
        lines.append("- More withheld cuts exist; see the evidence list.")
    return "\n".join(lines)


def _restatements(reg, W) -> list[str]:
    rows = reg.rows(
        "select week_start::varchar, territory_id, min(revised_at)::varchar, any_value(revision_reason) from raw.restatement_log "
        f"where product_id = 'BXA' and (week_start in {q._dates(W)} or revised_at between DATE '{W[0]}' and DATE '{q.shift(W[-1], 1)}') "
        "group by 1, 2 order by 1, 2")
    out = []
    for w, t, when, reason in rows[:3]:
        base = f"from raw.restatement_log where product_id = 'BXA' and week_start = DATE '{w}' and territory_id = '{t}'"
        old = reg.claim("get_restatement", f"select sum(trx_prior) {base}", "int", week=w, territory=t)
        new = reg.claim("get_restatement", f"select sum(trx_revised) {base}", "int", week=w, territory=t)
        out.append(f"Restated: {q.name(t)} BXA TRx for the week of {w} was {old} when first reported and is now {new} "
                   f"(restated {when}; reason: {reason.lower().replace('_', ' ')}). Quote the new value with this note.")
    return out


def _kpis(reg, W, B, ok, terrs, calendar) -> list[str]:
    if not ok:
        return ["KPIs: no territory passes the feed gate in every one of these weeks, so no like-for-like national figure is given."]
    cur, base = q.mean_weekly(W, terrs=ok), q.mean_weekly(B, terrs=ok) if B else None
    n = reg.claim("get_metric", f"select count(distinct territory_id) from {q.RX} where week_start in {q._dates(W)} and {q._in('territory_id', ok)}", "int")
    avg = reg.claim("get_metric", cur, "int", scope="like-for-like national")
    total = reg.claim("get_metric", "select count(*) from raw.dim_territory", "int")
    lines = []
    if base:
        change = reg.scalar(q.pct_change(cur, base)) or 0
        pct = reg.claim("get_metric", q.pct_change(cur, base), "pct1", scope="like-for-like national")
        lines.append(f"KPIs: BXA TRx averaged {avg} a week across {n} of {total} territories (like for like), "
                     f"{_word(change)} {pct} against the weeks before.")
        # headline total over every reportable cut, which a withheld cut distorts
        all_cur, all_base = q.mean_weekly(W), q.mean_weekly(B)
        naive = reg.scalar(q.pct_change(all_cur, all_base)) or 0
        if len(ok) < len(terrs) and abs(naive - change) >= 5:
            p2 = reg.claim("get_metric", q.pct_change(all_cur, all_base), "pct1", scope="headline total of reportable cuts")
            lines.append(f"The headline total of reportable cuts is {_word(naive)} {p2}, but that move comes mostly from withheld cuts, so it is a data artifact, not a business change.")
    if calendar:
        for w, holiday, bd, reset in calendar[:3]:
            days = reg.claim("lookup_calendar", q.calendar(w, "business_days"), "int", week=w)
            tag = "plan-year reset" if reset and holiday == "NONE" else holiday.lower().replace("_", " ")
            lines.append(f"Calendar effect: the week of {w} is {tag} with {days} business days, so a lower volume is expected.")
        ly_cur, ly_base = q.mean_weekly([q.shift(w, -52) for w in W], terrs=ok), q.mean_weekly([q.shift(w, -52) for w in B], terrs=ok) if B else None
        if ly_base:
            ly = reg.scalar(q.pct_change(ly_cur, ly_base)) or 0
            lines.append(f"The same weeks a year earlier were {_word(ly)} {reg.claim('get_metric', q.pct_change(ly_cur, ly_base), 'pct1', scope='same weeks last year')}. This is a calendar effect, not a business event.")
    return lines


def _series(reg):
    rows = reg.rows(f"select week_start::varchar, territory_id, sum(trx) from {q.RX} where product_id = 'BXA' group by 1, 2")
    s: dict[str, dict[str, float]] = {}
    for w, t, x in rows:
        s.setdefault(t, {})[w] = float(x)
    return s


def _screen(reg, W, B, ok, focus):
    """Territories whose change is beyond their own normal noise and beyond their peers' change."""
    series = _series(reg)
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
        material = abs(change) >= max(MATERIAL_CHANGE, NOISE_Z * sigma / min(len(W), 3) ** 0.5) and abs(gap) >= MATERIAL_GAP
        if material or t == focus:
            found.append({"territory": t, "kind": "territory", "impact": abs(x - b), "change": change})
        else:
            quiet.append(t)
    if not focus or focus == "NATIONAL":
        for e in access_events(reg, None, W):
            t = e["territory"]
            if t in ok and not any(s["territory"] == t for s in found) and B:
                plan_change = reg.scalar(q.pct_change(q.mean_weekly(W, plan=e["plan"]), q.mean_weekly(B, plan=e["plan"])))
                if plan_change is not None and abs(plan_change) >= 15:
                    found.append({"territory": t, "kind": "plan", "impact": abs(reg.scalar(q.mean_weekly(W, plan=e["plan"])) - reg.scalar(q.mean_weekly(B, plan=e["plan"]))), "plan": e["plan"]})
                    quiet = [x for x in quiet if x != t]
    found.sort(key=lambda s: -s["impact"])
    return found, quiet


def _story(reg, n, s, W, B, ok):
    t = s["territory"]
    checks = run_checks(reg, t, W, B)
    level, lead = confidence(checks)
    x, b = q.mean_weekly(W, terrs=[t]), q.mean_weekly(B, terrs=[t])
    peers = [o for o in ok if o != t]
    px, pb = q.mean_weekly(W, terrs=peers), q.mean_weekly(B, terrs=peers)
    change = reg.scalar(q.pct_change(x, b)) or 0
    peer = reg.scalar(q.pct_change(px, pb)) or 0
    head = (f"Story {_ord(n)}: {q.name(t)}. BXA TRx averaged {reg.claim('get_metric', x, 'int', territory=t)} a week against "
            f"{reg.claim('get_metric', b, 'int', territory=t)} before ({_word(change)} {reg.claim('get_metric', q.pct_change(x, b), 'pct1', territory=t)}), "
            f"while the other territories were {_word(peer)} {reg.claim('get_metric', q.pct_change(px, pb), 'pct1', scope='other territories')}.")
    lines = [head, "Checked, in this order:"] + [f"- {c.text}" for c in checks]
    supported = [c for c in checks if c.verdict == "supported"]
    abstain = level == "Low"
    if abstain:
        lines.append(f"Confidence: {level}. Unresolved, investigate next. No driver is named. Next: split {q.name(t)} by plan and specialty, and ask sales leadership for local context.")
    else:
        verb = "Leading driver" if level == "High" else "Candidate drivers"
        owner = ", ".join(OWNER[c.driver] for c in supported)
        lines.append(f"Confidence: {level}. {verb}: {lead}. Next: involve {owner}.")
    return "\n".join(lines), abstain


def _ord(n: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}[n]


def _competitor_story(reg, W, B, n) -> str | None:
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
    bxa = reg.claim("compare_competitors", q.share(W, "BXA"), "pct1", product="BXA")
    bxa_pre = reg.claim("compare_competitors", q.share(pre, "BXA"), "pct1", product="BXA", weeks="before launch")
    return (f"Story {_ord(n)}: competitor Metacora (launched {launched}). This is a continuing story, week {since} since launch, {direction}. "
            f"Metacora held {bxe} of the four-brand basket and BXA held {bxa}, against {bxa_pre} for BXA in the four weeks before launch. "
            f"Confidence: Medium. The share loss is measured; its effect on volume is not separated from other drivers. Next: involve marketing and sales.")


def _envelope(reg: Registry, text: str, abstained: bool) -> dict:
    return {"system": "briefing_scripted", "answer": text, "claims": reg.claims, "evidence": reg.evidence, "abstained": abstained}
