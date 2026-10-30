"""Forecast lane, scripted baseline BL-0 (Personas & Eval Design 3.6): a fixed investigation sequence,
validate -> localize -> predefined driver checks -> reconcile -> template explanation. No model.

Draft for Alvin and Sienna to confirm: it follows their attribution contract, V = A - F = sum of driver
contributions + residual, and quantifies a driver only where one comparison identifies it.
"""
from __future__ import annotations

from pharmagentics.tools import DEFAULT_DB, Registry
from pharmagentics.tools import queries as q
from pharmagentics.tools.checks import OWNER, confidence, launch_date, run_checks
from pharmagentics.tools.registry import digits_outside_tokens
from pharmagentics.tools.window import parse
from pharmagentics.tracing import finish, span

LOCAL = ("access", "promotion", "supply")


def answer(question: str, db=DEFAULT_DB) -> dict:
    reg = Registry(db)
    try:
        return _explain(reg, question)
    finally:
        reg.close()


def _word(v: float) -> str:
    return "above" if v > 0 else "below"


def _explain(reg: Registry, question: str) -> dict:
    first, latest = reg.rows("select min(week_start)::varchar, max(week_start)::varchar from raw.calendar")[0]
    ask = parse(question, first, latest)
    W = ask["weeks"]
    if not W:
        return _env(reg, f"That period is outside the release, which runs from {first} to {latest}. Nothing was run.", False)
    cut = ask["territory"] or "NATIONAL"
    n_b = 4 if len(W) == 1 else min(len(W), 13)
    B = [w for w in (q.shift(W[0], -i) for i in range(n_b, 0, -1)) if w >= first]
    out: list[str] = []
    abstained = False

    with span("1_load_and_pin", inputs={"question": question}, data_version=reg.data_version) as sp:
        issue = reg.fact("get_forecast_version", f"select min(forecast_issue_week)::varchar from {q.FVA} where week_start = DATE '{W[0]}' "
                         f"and territory_id = '{cut}' and product_id = 'BXA'")
        out.append(f"Forecast explanation for {q.name(cut)}, {'week of ' + W[0] if len(W) == 1 else 'weeks ' + W[0] + ' to ' + W[-1]}. "
                   f"Data version {reg.data_version}. Locked forecast issued {issue}, four weeks ahead.")
        if ask["note"]:
            out.append(ask["note"])
        finish(sp, {"cut": cut, "weeks": W, "forecast_issue_week": issue})

    with span("2_validation") as sp:
        provisional = reg.scalar(f"select coalesce(max(actual_is_provisional), 0) from {q.FVA} where product_id = 'BXA' "
                                 f"and territory_id = '{cut}' and week_start in {q._dates(W)}") or 0
        bad = reg.rows("select week_start::varchar, territory_id, flag_reasons from reporting.v_feed_health "
                       f"where health_status = 'FLAG' and week_start in {q._dates(W)}"
                       + ("" if cut == "NATIONAL" else f" and territory_id = '{cut}'"))
        finish(sp, {"provisional": bool(provisional), "flagged_cuts": len(bad)})

    with span("3b_variance_screen") as sp:
        f = q.fva_sum("forecast_trx", W, cut)
        a = q.fva_sum("actual_trx", W, cut)
        v = q.fva_sum("variance_trx", W, cut)
        vpct = f"select 100.0 * ({q.sub(v)}) / nullif(({q.sub(f)}), 0)"
        V = reg.scalar(v) or 0
        fc, ac = reg.claim("get_forecast", f, "int", cut=cut), reg.claim("get_forecast", a, "int", cut=cut)
        vc = reg.claim("get_forecast", v, "int", cut=cut)
        pc = reg.claim("get_forecast", vpct, "pct1", cut=cut)
        out.append(f"Miss: forecast {fc}, actual {ac}. Signed variance (actual minus forecast) is {vc} TRx, {pc} {_word(V)} forecast "
                   f"(percent of forecast).")
        finish(sp, {"variance_trx": V})

    if provisional:
        with span("4b_investigation") as sp:
            lines = ["The actual for this cut is provisional, so the miss is not settled. This report names no driver and makes no attribution until the feed is reloaded."]
            for w, t, reasons in bad[:4]:
                lines.append(f"- {q.name(t)}, week of {w}: " + ", ".join(q.REASONS.get(r, r.lower()) for r in reasons.split(";") if r) + ".")
            lines.append(f"Next: ask {OWNER['data']} for the reload, then re-queue this case.")
            out += lines
            abstained = True
            finish(sp, {"paused": True})
        return _finish(reg, out, abstained)

    with span("4b_investigation") as sp:
        lead, concentrated = _localize(reg, out, W, cut)
        focus = lead or cut
        checks = run_checks(reg, focus, W, B) if focus != "NATIONAL" else []
        if checks:
            out.append(f"Drivers checked for {q.name(focus)}, in this order:")
            out += [f"- {c.text}" for c in checks]
        contributions = _attribute(reg, out, W, cut, lead if concentrated else None, checks, V)
        finish(sp, {"lead_territory": lead, "contributions": contributions})

    with span("5_explanation") as sp:
        level_text, abstained = _confidence(checks, contributions, concentrated)
        out.append(level_text)
        out += _follow_ups(reg, W, contributions, checks, lead if concentrated else None)
        out.append("This report changes no forecast.")
        finish(sp, {"abstained": abstained})
    return _finish(reg, out, abstained)


def _localize(reg, out, W, cut):
    """Split a national miss by territory; tie the territories back to the total (FE-05, FE-06)."""
    if cut != "NATIONAL":
        return cut, True
    rows = reg.rows(f"select territory_id, sum(variance_trx), sum(forecast_trx) from {q.FVA} where product_id = 'BXA' "
                    f"and territory_id <> 'NATIONAL' and week_start in {q._dates(W)} group by 1 order by 2")
    total_v = sum(r[1] for r in rows)
    total_f = sum(r[2] for r in rows)
    if not rows or total_v >= 0:
        out.append("No territory leads the miss.")
        return None, False
    top, tv, tf = rows[0]
    share_v, share_f = tv / total_v, tf / total_f
    concentrated = share_v >= 1.5 * share_f
    t_var = reg.claim("get_region_deltas", q.fva_sum("variance_trx", W, top), "int", territory=top)
    t_pct = reg.claim("get_region_deltas", f"select 100.0 * ({q.sub(q.fva_sum('variance_trx', W, top))}) / nullif(({q.sub(q.fva_sum('forecast_trx', W, top))}), 0)", "pct1", territory=top)
    s_v = reg.claim("get_region_deltas", f"select 100.0 * ({q.sub(q.fva_sum('variance_trx', W, top))}) / nullif(({q.sub(q.fva_sum('variance_trx', W))}), 0)", "pct1", territory=top)
    s_f = reg.claim("get_region_deltas", f"select 100.0 * ({q.sub(q.fva_sum('forecast_trx', W, top))}) / nullif(({q.sub(q.fva_sum('forecast_trx', W))}), 0)", "pct1", territory=top)
    tie = reg.claim("get_region_deltas", f"select coalesce(sum(variance_trx), 0) from {q.FVA} where product_id = 'BXA' "
                    f"and territory_id <> 'NATIONAL' and week_start in {q._dates(W)}", "int")
    n_miss = reg.claim("get_region_deltas", f"select count(*) from (select territory_id from {q.FVA} where product_id = 'BXA' and territory_id <> 'NATIONAL' "
                       f"and week_start in {q._dates(W)} group by 1 having sum(variance_trx) < 0)", "int")
    shape = "concentrated" if concentrated else "broad"
    out.append(f"Where: the miss is {shape}. {q.name(top)} is {t_var} TRx ({t_pct} of its forecast) and holds {s_v} of the national miss "
               f"with {s_f} of the forecast. {n_miss} territories are below forecast. The territories sum to {tie} TRx, which ties to the national figure.")
    return top, concentrated


def _attribute(reg, out, W, cut, lead, checks, V):
    """V = competitor + local driver + residual. A driver is quantified only where one comparison identifies it."""
    parts: list[tuple[str, str]] = []
    launched = launch_date(reg)
    f_nat = q.sub(q.fva_sum("forecast_trx", W))
    supported = [c for c in checks if c.verdict == "supported" and c.driver in LOCAL]
    if launched and launched <= W[-1] and cut == "NATIONAL":
        pre = [q.shift(launched, -i) for i in range(4, 0, -1)]
        # Measured on the other territories when a local driver is quantified, so the two are not double counted.
        away = lead if (lead and supported) else None
        loss = (f"(({q.sub(q.share(W, 'BXA', exclude=away))}) / nullif(({q.sub(q.share(pre, 'BXA', exclude=away))}), 0) - 1)")
        sql = f"select {f_nat} * {loss}"
        if (reg.scalar(sql) or 0) < 0:
            parts.append(("Competitor Metacora share gain", sql))
    if lead and supported and cut == "NATIONAL":
        rate = (f"({q.sub(q.fva_peers('variance_trx', W, lead))}) / nullif(({q.sub(q.fva_peers('forecast_trx', W, lead))}), 0)")
        sql = f"select ({q.sub(q.fva_sum('variance_trx', W, lead))}) - ({q.sub(q.fva_sum('forecast_trx', W, lead))}) * {rate}"
        if (reg.scalar(sql) or 0) < 0:
            parts.append((f"{q.name(lead)} {supported[0].driver} gap", sql))
    if not parts:
        out.append("Attribution: no driver is identified by a suitable comparison, so none is quantified. The whole miss stays unexplained.")
        return []
    residual = f"select ({q.sub(q.fva_sum('variance_trx', W))}) - " + " - ".join(f"({q.sub(sql)})" for _, sql in parts)
    lines = ["Attribution (signed TRx, actual minus forecast; contributions plus residual equal the miss):"]
    for label, sql in parts:
        lines.append(f"- {label}: {reg.claim('reconcile_attribution', sql, 'int', driver=label)}. Method: share loss or gap against the other territories over the same weeks; an association, not proof of cause.")
    lines.append(f"- Unexplained residual: {reg.claim('reconcile_attribution', residual, 'int', driver='residual')}. It is shown, not spread across drivers.")
    out += lines
    return [label for label, _ in parts]


def _confidence(checks, contributions, concentrated):
    if not contributions:
        return "Confidence: Low. Unresolved, investigate next. No driver is named.", True
    parts = []
    if any(c.startswith("Competitor") for c in contributions):
        parts.append("competitor share gain, Medium (it assumes basket volume would otherwise have matched the forecast)")
    if checks:
        level, lead = confidence(checks)
        if level != "Low" and any(not c.startswith("Competitor") for c in contributions):
            parts.append(f"local driver ({lead}), {level}")
    return "Confidence by driver: " + "; ".join(parts) + ". The residual is an open unknown.", False


def _follow_ups(reg, W, contributions, checks, lead) -> list[str]:
    launched = launch_date(reg)
    lines = ["Next checks:"]
    if any(c.startswith("Competitor") for c in contributions) and launched:
        pre = reg.claim("get_forecast", f"select 100.0 * sum(variance_trx) / nullif(sum(forecast_trx), 0) from {q.FVA} where product_id = 'BXA' "
                        f"and territory_id = 'NATIONAL' and week_start < DATE '{launched}'", "pct1", window="before launch")
        post = reg.claim("get_forecast", f"select 100.0 * sum(variance_trx) / nullif(sum(forecast_trx), 0) from {q.FVA} where product_id = 'BXA' "
                         f"and territory_id = 'NATIONAL' and week_start >= DATE '{launched}' and week_start <= DATE '{W[-1]}'", "pct1", window="since launch")
        lines.append(f"- Forecasting: review the competitor assumption. The national miss averaged {pre} of forecast before launch and {post} since.")
    for c in checks:
        if c.verdict == "supported" and c.driver in LOCAL and lead:
            lines.append(f"- {OWNER[c.driver].capitalize()}: confirm the {c.driver} finding for {q.name(lead)} and whether it has ended.")
    lines.append("- Commercial analytics: split the unexplained residual by plan and specialty.")
    return lines


def _finish(reg, out, abstained):
    template = "\n".join(x for x in out if x)
    bad = digits_outside_tokens(template)
    if bad:
        raise AssertionError(f"digit outside a claim token: {bad[:3]}")
    return _env(reg, reg.render(template), abstained)


def _env(reg: Registry, text: str, abstained: bool) -> dict:
    return {"system": "forecast_scripted", "answer": text, "claims": reg.claims, "evidence": reg.evidence, "abstained": abstained}
