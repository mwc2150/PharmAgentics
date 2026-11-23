"""Continuing cards (brief-010 packet C, FR-012): a territory whose promotion lapse or plan access restriction is still
running in the brief's period gets a card, even when its change on the comparison weeks looks flat.

Against the weeks just before the period, a territory already inside a lapse looks unchanged, so the screen tells no
story. This card measures the territory (a lapse) or the plan (an access restriction) against the four weeks before the
event began, says so ("continuing since <week>"), and supports the event's driver. Code finds the events with the code
that already finds them (`promotion.lapses`, `checks.access_events`); every number is a claim token from a governed
query; nothing here reads a model.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import memo, promotion
from . import queries as q
from .checks import Check, access_events, confidence
from .lag_checks import run_checks
from .memo import DRIVER_NAMES, StoryBlock
from .registry import Registry
from .splits import SMALL_CELL, readable
from .stages import MATERIAL_CHANGE, measure_label, word

BASELINE_WEEKS = 4  # the level before the event: this many weeks before it began
MOST_CONTINUING = 2  # continuing cards a brief, largest change first
_STORY_KINDS = ("territory", "plan", "cut", "continuing")  # block ids a continuing card sits after


def continuing_id(event: dict) -> str:
    return f"continuing:{event['territory']}"


def _monday_on_or_after(iso: str) -> str:
    d = date.fromisoformat(iso)
    return (d + timedelta(days=-d.weekday() % 7)).isoformat()


def subject(event: dict) -> str:
    """What the card is about: the territory, or the plan in it (access)."""
    where = q.name(event["territory"])
    if not event["plan"]:
        return where
    name = readable(event["plan"])
    return f"{name[:1].upper()}{name[1:]} in {where}"


def _before(start: str) -> list[str]:
    return [q.shift(start, -i) for i in range(BASELINE_WEEKS, 0, -1)]


def _access_runs(reg: Registry, p, territory: str | None) -> list[dict]:
    """Every restriction as a run: {plan, territory, start (first week it bites), end (last week before relief, or None)}."""
    events = access_events(reg, territory, q.mondays(p.first, p.latest), brand_id=p.brand_id)
    runs, open_ = [], {}
    for e in sorted(events, key=lambda e: (e["plan"], e["month"])):
        if e["restricted"]:
            open_.setdefault(e["plan"], e)
        elif e["plan"] in open_:
            first = open_.pop(e["plan"])
            runs.append({"plan": e["plan"], "territory": e["territory"], "month": first["month"],
                         "start": _monday_on_or_after(first["month"]), "end": q.shift(_monday_on_or_after(e["month"]), -1)})
    runs += [{"plan": plan, "territory": e["territory"], "month": e["month"], "start": _monday_on_or_after(e["month"]), "end": None}
             for plan, e in open_.items()]
    return runs


def screen(reg: Registry, p, covered: set[str], cut_plans: set[str] = frozenset(), *, most: int | None = MOST_CONTINUING) -> list[dict]:
    """The events still running in the period, in territories with no regular story or cut card, largest first, at most
    two (FR-012). A lapse is running when it began before the period's first week, had run long enough to count by the
    period's last week, and had not ended before the period; an access restriction when it began before the first week
    and was not lifted before it. The territory (or the plan, for access) must have fallen against its own level before
    the event by at least the material change, and a plan must clear the small-cell floor. Makes no claim."""
    if not (p.weeks and p.baseline) or p.calendar or p.brand_id != "BXA" or p.promotion_review:
        return []
    W = p.weeks
    scratch = reg.scratch()  # the screen's reads are not this run's claims
    found = []
    focus = None if p.focus in (None, "NATIONAL") else p.focus
    if p.has("territory"):
        for lapse in promotion.lapses(scratch, focus):
            t = lapse.territory
            if (t in covered or t not in p.ok or not lapse.start < W[0] <= lapse.end
                    or q.shift(lapse.start, promotion.LAPSE_WEEKS - 1) > W[-1] or _before(lapse.start)[0] < p.first):
                continue
            x = scratch.scalar(q.mean_weekly(W, terrs=[t], product=p.brand_id, col=p.col))
            b = scratch.scalar(q.mean_weekly(_before(lapse.start), terrs=[t], product=p.brand_id, col=p.col))
            if not b or x is None or x / b - 1 > -MATERIAL_CHANGE:
                continue
            found.append({"kind": "lapse", "territory": t, "plan": None, "cut": None, "start": lapse.start, "end": lapse.end,
                          "impact": abs(x - b)})
    if p.has("plan"):
        for run in _access_runs(scratch, p, focus):
            t, plan = run["territory"], run["plan"]
            if (t in covered or t not in p.ok or plan in cut_plans or not run["start"] < W[0]
                    or (run["end"] is not None and run["end"] < W[0]) or _before(run["start"])[0] < p.first):
                continue
            B = _before(run["start"])
            x, b = (scratch.scalar(q.mean_weekly(w, plan=plan, product=p.brand_id, col=p.col)) for w in (W, B))
            tx, tb = (scratch.scalar(q.mean_weekly(w, plan=plan, product=p.brand_id)) for w in (W, B))
            if not b or x is None or x / b - 1 > -MATERIAL_CHANGE or min(tx or 0, tb or 0) < SMALL_CELL:
                continue
            found.append({"kind": "access", "territory": t, "plan": plan, "cut": f"plan:{plan}", "start": run["start"],
                          "end": run["end"], "month": run["month"], "impact": abs(x - b)})
    found.sort(key=lambda e: (-e["impact"], e["territory"]))
    out, seen = [], set()
    for e in found:  # one card a territory
        if e["territory"] not in seen:
            seen.add(e["territory"])
            out.append(e)
    return out if most is None else out[:most]


def _labels(event: dict) -> dict:
    """The claims of a continuing card are set against the four weeks before the event, not the brief's comparison weeks."""
    B = _before(event["start"])
    return {"comparison": f"{B[0]} to {B[-1]}", "comparison_kind": "before_event"}


def figures(reg: Registry, p, event: dict) -> list[dict]:
    """For each measure the definition holds: the level a week in the period and in the four weeks before the event
    began, and the percent change, as claim tokens (the territory's for a lapse, the plan's for access)."""
    W, B, brand, t, plan = p.weeks, _before(event["start"]), p.brand_id, event["territory"], event["plan"]
    where = {"plan": plan} if plan else {"terrs": [t]}
    out = []
    for m in p.definition.measure:
        x, b = q.mean_weekly(W, product=brand, col=m, **where), q.mean_weekly(B, product=brand, col=m, **where)
        change = reg.scalar(q.pct_change(x, b)) or 0
        fmt = "dec1" if m == "nbrx" else "int"
        tool = "get_plan_metric" if plan else "get_metric"
        with reg.under(**({} if m == p.col else {"measure": m}), **_labels(event)):
            args = {"territory": t, "scope": f"since the event began, {measure_label(m)}", **({"plan": plan} if plan else {})}
            out.append({"measure": m, "label": measure_label(m), "word": word(change),
                        "before": reg.claim(tool, b, fmt, **args), "after": reg.claim(tool, x, fmt, **args),
                        "pct": reg.claim(tool, q.pct_change(x, b), "pct", **args)})
    return out


def _event_check(reg: Registry, p, event: dict) -> Check:
    """The event's own driver, supported by construction (the event is running): promotion for a lapse, access for a
    restriction, each against the four weeks before it began."""
    with reg.under(**_labels(event)):
        return _event_check_text(reg, p, event)


def _event_check_text(reg: Registry, p, event: dict) -> Check:
    B, t = _before(event["start"]), event["territory"]
    if event["kind"] == "lapse":
        weeks = q.mondays(event["start"], min(event["end"], p.weeks[-1]))
        a = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", weeks, t, product=p.brand_id), "int", territory=t)
        b = reg.claim("lookup_promo", q.context_mean("promo_activity", "rep_calls_aggregated", B, t, product=p.brand_id), "int", territory=t)
        pct = reg.claim("lookup_promo", q.pct_change(q.context_mean("promo_activity", "rep_calls_aggregated", weeks, t, product=p.brand_id),
                                                      q.context_mean("promo_activity", "rep_calls_aggregated", B, t, product=p.brand_id)),
                        "pct", territory=t)
        return Check("promotion", "supported",
                     f"Promotion: supported, as an association. Rep coverage lapsed on {event['start']}: aggregated rep calls averaged "
                     f"{a} a week from then, against {b} in the four weeks before ({pct} lower).")
    plan = event["plan"]
    x, b = q.mean_weekly(p.weeks, plan=plan, product=p.brand_id), q.mean_weekly(B, plan=plan, product=p.brand_id)
    pct = reg.claim("get_plan_metric", q.pct_change(x, b), "pct", plan=plan, territory=t)
    lives = reg.claim(
        "lookup_access_events",
        f"select 100.0 * (select max(covered_lives_weight) from raw.dim_plan where plan_id = '{plan}') / "
        f"(select sum(covered_lives_weight) from raw.dim_plan where territory_id = '{t}')", "pct", plan=plan)
    return Check("access", "supported",
                 f"Access: supported. The {readable(plan)} ({lives} of the territory's covered lives) added restrictions effective "
                 f"{event['month']}, still in force in these weeks. {p.brand_id} volume on that plan fell {pct} against the four weeks before.",
                 {"plan": plan})


def _checks(reg: Registry, p, event: dict) -> tuple[list[Check], Check]:
    """The usual checks on the period against the weeks before the event, with the event's own driver in place of the
    check that reads only the comparison weeks (the event began before them). Also returns that driver's check."""
    own = run_checks(reg, event["territory"], p.weeks, _before(event["start"]), brand_id=p.brand_id, use_selected_baseline=True)
    mine = _event_check(reg, p, event)
    return [mine if c.driver == mine.driver else c for c in own], mine


def card(p, event: dict, measures: list[dict], checks: list[Check]) -> dict:
    """The card (core-011 FR-017 shape): the territory, its cut (the plan, for access), the primary measure's direction
    and each measure's in `directions`, the drivers supported and ruled out, and `continuing`/`since` so the UI and a
    reader can tell it from a regular card."""
    supported, ruled_out = memo.driver_calls(checks)
    first = measures[0]
    subj = subject(event)
    verb = {"up": "rose from", "down": "fell from"}.get(first["word"], "held flat from")
    cause = "rep coverage lapse" if event["kind"] == "lapse" else "access restriction"
    headline = (f"{subj}, continuing since {event['start']}: {first['label']} {verb} {first['before']} to {first['after']} a week "
                f"({first['word']} {first['pct']}) against the four weeks before the {cause} began.")
    return {"headline": headline, "confidence": confidence(checks)[0], "drivers_checked": [DRIVER_NAMES[c.driver] for c in checks],
            "territory": event["territory"], "cut": event["cut"], "direction": first["word"],
            "directions": {m["measure"]: m["word"] for m in measures},
            "drivers_supported": supported, "drivers_ruled_out": ruled_out, "continuing": True, "since": event["start"]}


def block(reg: Registry, p, event: dict) -> tuple[StoryBlock, dict]:
    """A continuing card as a story block (§3, after the regular territory cards), and the entry §1 and §5 read
    ({territory, confidence, drivers, lags, checks}). The text reaches the scored answer (FR-009); every number is a claim token."""
    measures = figures(reg, p, event)
    checks, mine = _checks(reg, p, event)
    c = card(p, event, measures, checks)
    subj = subject(event)
    cause = "rep coverage lapse" if event["kind"] == "lapse" else "access restriction"
    lines = []
    for i, m in enumerate(measures):
        lead = (f"{subj} (continuing since {event['start']}): {p.brand_id} {m['label']}" if i == 0 else
                m["label"][:1].upper() + m["label"][1:])
        lines.append(f"{lead} averaged {m['after']} a week in these weeks against {m['before']} in the four weeks before the "
                     f"{cause} began ({m['word']} {m['pct']}).")
    lines.append(mine.text)
    level, lead = confidence(checks)
    lines.append(f"Confidence: {level}. Unresolved, investigate next. No driver is named." if level == "Low" else
                 f"Confidence: {level}. {'Leading driver' if level == 'High' else 'Candidate drivers'}: {lead}.")
    detail = ["Also checked, in this order:"] + [f"- {x.text}" for x in checks if x is not mine]
    detail.append(f"The event began before the comparison weeks, so the change is set against the four weeks before {event['start']}.")
    entry = {"territory": event["territory"], "confidence": level, "drivers": c["drivers_supported"], "lags": {}, "checks": checks}
    return StoryBlock(continuing_id(event), f"{subj} (continuing)", lines, card=c, detail=detail), entry


def place(blocks: list[StoryBlock], new: StoryBlock) -> None:
    """After the regular territory, plan and cut cards (and any continuing card already placed), before the competitor
    card; at the end when there is neither."""
    after = [i for i, b in enumerate(blocks) if b.card and b.id.partition(":")[0] in _STORY_KINDS]
    if after:
        blocks.insert(after[-1] + 1, new)
        return
    rival = next((i for i, b in enumerate(blocks) if b.id.partition(":")[0] == "competitor"), len(blocks))
    blocks.insert(rival, new)
