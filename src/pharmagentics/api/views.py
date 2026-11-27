"""Views of one briefing (core-007 FR-002 to FR-006).

The leadership view is cut from the full answer by code: it keeps the memo's Bottom line with its KPI strip,
The numbers with its territory table, What changed and why with each story's card but without the
driver-check detail, the first paragraph of What the data can't tell us, Next checks and the Assumptions
(brief-003 FR-026, brief-008 FR-005), so each number it shows is already a claim of the same run. Caveats survive: the Bottom line leads
with any withheld cut and The numbers carries restatements. It carries no claims, evidence, query
text or trace. The Marketer (P4) gets this cut plus, on each territory story, the promotion read and, once, the
budget note (`marketer`).
"""
from __future__ import annotations

from pharmagentics.tools import lag_checks

from . import signoff

CHECKS_HEADER = "Checked, in this order:"
DROPPED_PREFIX = "Considered and dropped:"
HEADING = "## "
# Memo sections leaders do not see (brief-003 FR-026): the data's limits and the appendix.
LEADERSHIP_DROPS = ("What the data can't tell us", "Appendix")


def executive_summary(answer: str, sections: list[dict] | None = None) -> str:
    """Leaders get the title, Bottom line, The numbers, What changed and why without the checks, the first
    paragraph of the limits, Next checks and the Assumptions. With the memo's `sections` the cut is theirs, so
    folded detail never reaches the summary; a brief stored without them is cut from its flat text (every line
    but the checks, the dropped line and, from the memo on, the limits and the appendix)."""
    if sections and (cut := leadership_sections(sections)):
        keep = [x for x in answer.split("\n## ")[0].splitlines() if x.strip()]
        for s in cut:
            if "." not in s["number"]:
                keep.append(HEADING + s["title"])
            keep += [x for x in (s["text"] or "").splitlines() + (s.get("prose") or "").splitlines() if x.strip()]
            chart = s.get("chart")
            if chart:
                keep += [f"Chart: {chart['caption']}", chart["explanation"]]
        return "\n".join(keep)
    keep: list[str] = []
    in_checks = dropped_section = False
    for line in answer.splitlines():
        if not line.strip():
            continue
        if line.startswith(HEADING):
            dropped_section = line[len(HEADING):].strip() in LEADERSHIP_DROPS
            in_checks = False
            if not dropped_section:
                keep.append(line)
            continue
        if dropped_section:
            continue
        if line.startswith(CHECKS_HEADER):
            in_checks = True
            continue
        if in_checks and line.lstrip().startswith("- "):
            continue
        in_checks = False
        if line.startswith(DROPPED_PREFIX):
            continue
        keep.append(line)
    return "\n".join(keep)


LEADERSHIP_FIELDS = ("brief_id", "engine", "system", "brand_id", "territory_id", "week_start", "week_end",
                     "data_version", "abstained", "review_status", "reviewed_at", "definition", "definition_words")  # words, never args or SQL
LEADERSHIP_SECTIONS = ("1", "2", "3", "4", "5", "6")  # §4 in short, §6 as the Assumptions; story subsections follow §3
SECTION_FIELDS = ("number", "title", "text", "prose")  # allow-list: no claims, citations or evidence
KPI_FIELDS, ROW_FIELDS, CARD_FIELDS = ("label", "value", "detail", "direction"), ("cells", "basis"), ("headline", "confidence", "drivers_checked", "territory", "direction", "drivers_supported", "drivers_ruled_out")
TABLE_FIELDS = ("columns", "note")  # blocks (brief-008): values and labels only, never their citations or the detail
CHART_FIELDS = ("kind", "weeks", "caption", "explanation", "series", "band", "rows")  # no table, query or panel table


def _leader_text(text: str) -> str:
    keep, in_checks = [], False
    for line in text.splitlines():
        if line.startswith(CHECKS_HEADER):
            in_checks = True
            continue
        if in_checks and line.lstrip().startswith("- "):
            continue
        in_checks = False
        if not line.startswith(DROPPED_PREFIX):
            keep.append(line)
    return "\n".join(keep)


def _assumptions(text: str) -> list[str]:
    """The Assumptions block of the Appendix text: its items, with the data version and the heading left out."""
    lines = text.splitlines()
    if "Assumptions:" not in lines:
        return []
    items = []
    for line in lines[lines.index("Assumptions:") + 1:]:
        if not line.startswith("- "):
            break
        items.append(line)
    return items


def _blocks(s: dict) -> dict:
    """The brief-008 blocks a leader sees: values and labels, no citations, no detail."""
    out = {}
    if s.get("kpis"):
        out["kpis"] = [{k: x.get(k) for k in KPI_FIELDS} for x in s["kpis"]]
    if s.get("territory_table"):
        t = s["territory_table"]
        out["territory_table"] = {**{k: t.get(k) for k in TABLE_FIELDS}, "rows": [{k: r.get(k) for k in ROW_FIELDS} for r in t["rows"]]}
    if s.get("card"):
        out["card"] = {k: s["card"].get(k) for k in CARD_FIELDS}
    return out


def leadership_sections(sections: list[dict] | None) -> list[dict] | None:
    """The memo sections a leader sees, cut by code from the analyst's: §1 with its KPI strip, §2 with its table
    and chart, §3 and its stories (cards) without the checks list or the evidence, §4 in its first paragraph, §5,
    and the Assumptions from §6. Allow-lists, so a new field never reaches a leader."""
    if not sections:
        return None
    out = []
    for s in sections:
        top = s["number"].split(".")[0]
        if top not in LEADERSHIP_SECTIONS:
            continue
        if top == "4":  # the short limits paragraph: no chart, no table, no gate detail
            first = (s.get("text") or "").split("\n")[0]
            out.append({"number": s["number"], "title": s["title"], "text": first, "prose": s.get("prose") or ""})
            continue
        if top == "6":
            items = _assumptions(s.get("text") or "")
            if items:
                out.append({"number": s["number"], "title": "Assumptions", "text": "\n".join(items), "prose": ""})
            continue
        cut = {k: s.get(k) for k in SECTION_FIELDS}
        cut.update(_blocks(s))
        cut["text"] = _leader_text(cut["text"] or "")
        if (s.get("card") or {}).get("cut"):  # a plan cut card (brief-010 FR-001): a leader reads its headline, nothing under it
            cut["text"], cut["prose"] = "", ""
        chart = s.get("chart")
        if chart:
            cut["chart"] = {k: chart.get(k) for k in CHART_FIELDS if k in chart}
            if chart.get("panel"):
                cut["chart"]["panel"] = {k: chart["panel"].get(k) for k in ("name", "unit", "driver", "points")}
        out.append(cut)
    return out


def process_summary(record: dict) -> str | None:
    """One line on how the brief was made, built by code for leaders (brief-009 FR-005): the engine, how many stories
    and checks, and whether the analyst reviewed it (no date: a UTC date reads a day late in the evening). It carries no step, tool, argument or prompt."""
    result = record["result"]
    who = "the agent team" if result.get("engine") == "agent" else "the scripted engine"
    events = result.get("events") or []
    if not events and not result.get("engine"):
        return None
    parts = []
    if events:
        stories = len({e["story"] for e in events if e.get("story")})
        checks = sum(e.get("step") in ("Check the data", "Test a driver") and (e.get("tool") or "").startswith("check_") for e in events)
        parts = [f"{stories} stor{'y' if stories == 1 else 'ies'}", f"{checks} check{'' if checks == 1 else 's'}"]
    line = f"Built by {who}" + (": " + ", ".join(parts) if parts else "")
    if signoff.state_of(record) == signoff.SIGNED_OFF and (record.get("signed_off_at") or record.get("reviewed_at")):
        line += "; reviewed by the analyst"  # the date is the viewer's own: the UI adds "on <date>" from reviewed_at, in local time
        if record.get("signed_off_at"):  # a brief approved before sign-off existed has no second step to report
            line += " and signed off by the Insights Manager"
    return line + "."


def leadership(record: dict) -> dict:
    """Build the leadership response from a stored brief. Allow-list, so a new field on the
    analyst result never reaches a leader by accident."""
    result = record["result"]
    out = {k: (record.get(k) if k in record else result.get(k)) for k in LEADERSHIP_FIELDS}
    out["review_status"] = signoff.state_of(record)
    out["reviewed_at"] = record.get("signed_off_at") or record.get("reviewed_at")  # for a leader: when it was signed off
    out["view"] = "leadership"
    out["process_summary"] = process_summary(record)
    out["summary"] = executive_summary(result["answer"], result.get("sections"))
    out["sections"] = leadership_sections(result.get("sections"))
    return out


BUDGET_NOTE = ("Where the next dollar should go is outside this brief: it has no spend data and no prescriber-level reach, so it cannot rank "
               "channels by return. Spend by channel and territory would answer it, and a planned pulse or holdout in a few territories would make "
               "a channel that never varies measurable.")
# The Marketer's promotion read (Michael, 2026-11-27, Q15): an explicit allow-list, so a new field of the check never reaches a leader.
PROMOTION_MEASURE_FIELDS = ("measure", "before", "after", "change", "direction")
PROMOTION_CHANNEL_FIELDS = ("channel", "before", "after", "change", "direction", "moved")
PROMOTION_EFFECT_FIELDS = ("low", "high", "word", "territories")  # never held_level, threshold or method


def marketer_promotion(promotion: dict) -> dict:
    """One story's promotion read for the Marketer: the verdict, the lag, new patients then TRx, the four channels, the range
    against territories without a promotion change (supported only) and the re-check date. Figures arrive filled by code."""
    out = {"verdict": promotion.get("verdict"), "lag_label": promotion.get("lag_label"),
           "new_patients": {k: (promotion.get("new_patients") or {}).get(k) for k in PROMOTION_MEASURE_FIELDS},
           "trx": {k: (promotion.get("trx") or {}).get(k) for k in PROMOTION_MEASURE_FIELDS},
           "channels": [{k: c.get(k) for k in PROMOTION_CHANNEL_FIELDS} for c in promotion.get("channels") or []]}
    effect = promotion.get("effect")
    if effect:
        out["effect"] = {k: effect.get(k) for k in PROMOTION_EFFECT_FIELDS}
        out["effect"]["phrase"] = lag_checks.effect_words(effect)  # said once, by code: a range, never a return
    if promotion.get("separable_from"):
        out["separable_from"] = list(promotion["separable_from"])
    out["recheck"] = promotion.get("recheck")
    return out


def marketer(record: dict) -> dict:
    """The Marketer's response (P4): the leadership cut, plus on each territory story the promotion read and, once, the
    budget note. No evidence, query text, claim token or trace: the promotion object is built field by field."""
    out = leadership(record)
    promotions = {s["number"]: (s.get("card") or {}).get("promotion") for s in record["result"].get("sections") or []}
    for s in out["sections"] or []:
        if s["number"].startswith("3.") and promotions.get(s["number"]):
            s["promotion"] = marketer_promotion(promotions[s["number"]])
    out["budget_note"] = BUDGET_NOTE
    return out


def leader_payload(record: dict, persona: str) -> dict:
    """The response for a reader of the leadership view, built in this one place per persona. P3 (Brand Director) reads
    the leadership cut; P4 (Marketer) reads it plus the promotion read of each story and the budget note; P1 and P2 get
    the leadership cut as a preview. No persona gets evidence, query text or a trace: `leadership` is an allow-list."""
    return marketer(record) if persona == "P4" else leadership(record)


REVIEW_STATE = {signoff.DRAFT: "IN_REVIEW", signoff.SENT: "IN_REVIEW", signoff.SIGNED_OFF: "PUBLISHED", signoff.RETURNED: "RETURNED",
                signoff.REJECTED: "RETURNED"}  # Briefing §6, stage 7: IN_REVIEW covers P1's review and P2's sign-off


def analyst(record: dict) -> dict:
    """The full response of the analyst view (P1; P2 reads it too, read-only), with the review state and its audit trail."""
    state = signoff.state_of(record)
    out = dict(record["result"])
    out.update(brief_id=record["brief_id"], view="analyst", review_status=state,
               reviewed_at=record.get("reviewed_at"), review_reason=record.get("review_reason"),
               signed_off_at=record.get("signed_off_at"), review_trail=signoff.trail(record), returned=signoff.returned_note(record))
    if out.get("flow"):
        flow = [dict(s) for s in out["flow"]]
        flow[-1]["states"] = ["IN_REVIEW"] if REVIEW_STATE[state] == "IN_REVIEW" else ["IN_REVIEW", REVIEW_STATE[state]]
        out["flow"] = flow
    return out


# Forecast leadership view: an executive summary. No stage trace, evidence, tool calls or check detail.
FORECAST_LEADERSHIP_REPORT = ("headline", "brand", "territory_id", "week", "week_ending", "window_weeks", "forecast_trx",
                              "actual_trx", "variance_trx", "variance_pct", "residual_trx", "caveats", "abstained",
                              "question", "intent", "summary", "week_start", "bias_trx", "out_of_scope", "charts_shown")
# Sections of a question run a leader may read: no data forensics, decision log, comparisons or audit trail.
FORECAST_LEADERSHIP_SECTIONS = {"summary", "miss", "where", "screen", "attribution", "unknowns", "checks", "assumptions", "gap"}


def forecast_leadership(run: dict) -> dict:
    """Allow-list, so a new field on the analyst run never reaches a leader by accident."""
    report = run["report"]
    out = {k: run.get(k) for k in ("run_id", "lane", "workflow_status", "dataset_release")}
    out["report"] = {k: report.get(k) for k in FORECAST_LEADERSHIP_REPORT}
    out["report"]["drivers"] = [{k: d[k] for k in ("driver", "label", "impact_trx", "confidence") if k in d} for d in report["drivers"]]
    if report.get("charts"):  # chart data only, no evidence ids
        out["report"]["charts"] = {k: {f: v for f, v in c.items() if f != "evidence"} for k, c in report["charts"].items()
                                   if k in (report.get("charts_shown") or [])}
    if "sections" in report:
        out["report"]["sections"] = [{k: x[k] for k in ("id", "title", "text")} for x in report["sections"]
                                     if x["id"] in FORECAST_LEADERSHIP_SECTIONS]
    out["report"]["what_to_check"] = [{k: c.get(k) for k in ("question", "why", "owner")} for c in report["what_to_check"]]
    out["report"]["verification"] = {"verdict": (report.get("verification") or {}).get("verdict")}
    return out


def forecast_record(record: dict, view: str) -> dict:
    """A stored Forecast run for one view, with its review state. The analyst also sees who did what (pseudonyms)."""
    narrative = record.get("narrative")
    out = {"view": view, "forecast_run_id": record["run_id"], "review_status": record["review_status"],
           "kind": record.get("kind", "form"), "job_status": record.get("job_status", "done"),
           "reviewed_at": record["reviewed_at"], "review_note": record["review_note"],
           "report_model": record.get("report_model", "none"), "writer_status": record.get("writer_status", "skipped")}
    if view == "leadership":  # the writer's notes for the analyst never reach a leader
        leadership_narrative = {k: v for k, v in narrative.items() if k != "analyst_notes"} if narrative else None
        return {**out, "narrative": leadership_narrative, **forecast_leadership(record["result"])}
    return {**out, "narrative": narrative, "writer_attempts": record.get("writer_attempts", []),
            "progress": record.get("progress", []), "job_error": record.get("job_error"),
            "followups": record.get("followups", []), "parent_run_id": (record.get("request") or {}).get("parent"),
            "pins": record.get("pins", []), "report_id": record.get("report_id"),
            "submitted_at": record["submitted_at"], "history": record["history"], **record["result"]}


def forecast_summary(record: dict) -> dict:
    """One row of a list: enough to pick a run, no evidence."""
    report, request = record["result"]["report"], record["request"]
    return {"forecast_run_id": record["run_id"], "territory_id": report.get("territory_id") or request.get("territory_id"),
            "week_start": report.get("week_start") or request.get("week_start"),
            "window_weeks": report.get("window_weeks") or request.get("window_weeks"), "question": request.get("question"),
            "job_status": record.get("job_status", "done"), "variance_trx": report["variance_trx"], "abstained": report["abstained"],
            "headline": report["headline"], "review_status": record["review_status"], "created_at": record["created_at"],
            "reviewed_at": record["reviewed_at"]}
