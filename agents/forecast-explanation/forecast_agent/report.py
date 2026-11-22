"""The analyst's report (fcst-002): pinned findings from any finished runs and follow-ups, drafted and revised by a
model on instruction, checked by code every time, submitted for the Brand Manager's review.

A finding is a snapshot of code numbers. Each number has a token such as {F1:miss} or {F2:D1}; tables are inserted
by code where the text says [[table F3]]. The model writes Markdown with tokens only; code fills every value. A
version is refused, and the last good one kept, when it has a stray digit or unknown token, names a driver or
territory no finding holds, states a finding's drivers without its residual, recommends a commercial action, or
uses a banned term. Without a model, code assembles the draft and only removing sections works."""
from __future__ import annotations

import asyncio
import os
import re
from typing import Annotated

from pharmagentics.tools.queries import TERRITORY_NAMES, name
from pharmagentics.tools.registry import FORMATS

from .prose import ACTIONS, BANNED, CATEGORIES

TOKEN = re.compile(r"\{(F\d+):([a-z0-9_]+)\}")
TABLE = re.compile(r"\[\[table (F\d+)\]\]")
KPIS = re.compile(r"\[\[kpis (F\d+)\]\]")
BLOCK = re.compile(r"\[\[block (F\d+) ([a-z_]+)\]\]")
CHART = re.compile(r"\[\[chart (F\d+) ([a-z]+)\]\]")
DEFAULT_CHART = {"run": ("waterfall", "territories", "trend", "weekly"), "weekly": ("weekly",), "chart": None, "explain": ()}
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
DRAFT_SECONDS = float(os.environ.get("FORECAST_REPORT_SECONDS", "600"))  # a local 4B model writes slowly
MAX_CHARS = 8000


def _fmt(value: float, kind: str) -> str:
    return FORMATS["pct1"](value) if kind == "pct" else FORMATS["int"](value)


# ---- findings ---------------------------------------------------------------------------------------------------

def finding_from_run(fid: str, run_id: str, report: dict, title: str | None = None) -> dict:
    """A snapshot of one run's report: its numbers as tokens and its words."""
    facts: dict[str, dict] = {}

    def fact(key: str, value, kind: str, means: str) -> None:
        if value is not None:
            facts[key] = {"value": float(value), "fmt": kind, "means": means}

    v = report.get("variance_trx")
    side = "below" if (v or 0) < 0 else "above"
    fact("forecast", report.get("forecast_trx"), "int", "forecast TRx")
    fact("actual", report.get("actual_trx"), "int", "actual TRx")
    fact("miss", v, "int", "miss in TRx (actual minus forecast)")
    if report.get("variance_pct") is not None:
        fact("miss_pct", 100 * report["variance_pct"], "pct", f"miss as a percent of forecast ({side} forecast)")
    fact("bias", report.get("bias_trx"), "int", "usual forecast bias in TRx")
    words, drivers, territories = [], set(), {report.get("territory_id") or "NATIONAL"}
    for i, d in enumerate(report.get("drivers", []), 1):
        label = d.get("label") or d["driver"]
        fact(f"d{i}", d["impact_trx"], "int", f"{label}: contribution in TRx")
        if v:
            fact(f"d{i}_share", 100 * d["impact_trx"] / v, "pct", f"{label}: share of the miss")
        words.append(f"d{i} is {label}, confidence {d['confidence']}: " + "; ".join(d.get("confidence_reasons", [])))
        drivers.add(d["driver"])
        territories.add(d.get("territory") or "")
        territories |= set(d.get("controls") or [])  # the comparison names its control territories
    if report.get("residual_trx") is not None:
        fact("residual", report["residual_trx"], "int", "unexplained residual in TRx")
        if v:
            fact("residual_share", 100 * report["residual_trx"] / v, "pct", "unexplained residual as a share of the miss")
    for c in report.get("candidates", []):
        if c.get("status") == "rejected" and c.get("reason"):
            words.append(f"Ruled out: {c['label']}: {c['reason']}")
        elif c.get("status") == "accepted" and c.get("reason"):
            words.append(f"Supported: {c['label']}: {c['reason']}")
    for i, d in enumerate(report.get("drivers", []), 1):
        how = ("the territory's miss beyond the rate of the control territories " + ", ".join(name(t) for t in d.get("controls") or [])
               + " over the same weeks, an association rather than proof of cause") if d.get("method") == "exposed_vs_control" else \
              "the brand's basket-share loss since the launch applied to the forecast, which assumes the basket would otherwise have matched the forecast"
        words.append(f"How d{i} ({d.get('label') or d['driver']}) was estimated: {how}")
    for sentence in re.split(r"(?<=\.)\s+", report.get("summary") or ""):
        if sentence and not re.search(r"\d", sentence):
            words.append(f"In plain words: {sentence}")
    for sp in report.get("splits") or []:
        top = sp["top"] if (sp["top"] or "").startswith("SYN_") else (sp["top"] or "").replace("_", " ").title()
        verdict = f"concentrated in {top}" if sp["verdict"] == "concentrated" else "broad, not in one segment"
        words.append(f"Where the unexplained gap sits: {name(sp['territory'])} by {sp['dimension']} is {verdict} (a location, not a cause)")
    for c in report.get("caveats", []):
        if not re.search(r"\d", c):
            words.append(f"Caveat: {c}")
    for c in report.get("what_to_check", []):
        words.append(f"To check ({c['owner']}): {c['question']}")
    if report.get("set_aside_weeks"):
        words.append("Weeks with a provisional actual were set aside: " + ", ".join(report["set_aside_weeks"]))
    if report.get("abstained"):
        words.append("The actual is provisional or the question is out of scope, so nothing was attributed.")
    table = None
    if report.get("intent") == "screen" and report.get("screen"):
        rows = report["screen"]
        table = {"kind": "screen", "rows": [{"label": name(r["territory"]), "miss": r["miss"], "pct": r["pct"],
                                             "beyond": r["beyond_peers"]} for r in rows]}
        territories |= {r["territory"] for r in rows}
    scope = report.get("scope") or {}
    label = f"{scope.get('territory_name', name(report.get('territory_id') or 'NATIONAL'))}, {scope.get('period') or ''}"
    for i, row in enumerate((report.get("screen") or [])[:5], 1):
        fact(f"t{i}_miss", row["miss"], "int", f"{name(row['territory'])}: miss in TRx")
        if row.get("pct") is not None:
            fact(f"t{i}_pct", row["pct"], "pct", f"{name(row['territory'])}: miss as a percent of its forecast")
        fact(f"t{i}_beyond", row["beyond_peers"], "int", f"{name(row['territory'])}: miss beyond what the other territories' rate predicts")
        words.append(f"t{i} is {name(row['territory'])}" + (", which stands out beyond its peers" if row.get("standout") and row["beyond_peers"] < 0 else ""))
        territories.add(row["territory"])
    charts = report.get("charts") or {}
    # The investigation's own sections, as verified passages; app hints ("Ask about ...") are not report text.
    blocks = [{"id": x["id"], "title": x["title"], "text": re.sub(r"\s*Ask about [^.]*\.", "", x["text"])}
              for x in report.get("sections") or [] if x["id"] not in ("summary", "audit") and x.get("text")]
    return {"id": fid, "kind": "run", "source": {"run_id": run_id}, "title": title or label, "charts": charts,
            "blocks": blocks, "intent": report.get("intent"),
            "charts_shown": [k for k in report.get("charts_shown") or [] if k in charts],
            "question": report.get("question"), "scope": label,
            "facts": facts, "words": words, "table": table, "drivers": sorted(drivers),
            "territories": sorted(t for t in territories if t)}


def finding_from_weekly(fid: str, run_id: str, followup: dict, parent: dict) -> dict:
    t = followup["table"]
    rows = [{"label": r["week"] + (" (provisional)" if r["provisional"] else ""), "miss": r["miss"], "pct": r["pct"]}
            for r in t["rows"]]
    return {"id": fid, "kind": "weekly", "source": {"run_id": run_id, "followup_id": followup["id"]},
            "title": f"Week by week: {name(t['territory'])}", "question": followup["question"],
            "scope": f"{name(t['territory'])}, {(parent.get('scope') or {}).get('period', '')}", "facts": {}, "words": [],
            "table": {"kind": "weekly", "rows": rows}, "drivers": [], "territories": [t["territory"]],
            "charts": {"weekly": {"kind": "bars", "title": f"Miss by week, {name(t['territory'])}", "unit": "TRx",
                                  "rows": [{"label": r["week"], "a": r["miss"], "flag": r["provisional"]} for r in t["rows"]],
                                  "series": ["Miss"]}}, "charts_shown": ["weekly"]}


def finding_from_drill(fid: str, run_id: str, followup: dict, parent: dict) -> dict:
    """Where a gap sits: its splits as a table and its segment chart (numbers from code)."""
    rows = []
    for sp in followup.get("splits") or []:
        for r in sp["rows"]:
            rows.append({"label": f"{r['segment']} ({sp['dimension']})", "miss": r["excess_trx"], "pct": r["change_pct"] or 0,
                         "peer": r["peer_change_pct"] or 0})
    t = followup.get("territory") or parent.get("territory_id") or "NATIONAL"
    verdicts = [f"{name(t)} by {sp['dimension']}: " + (f"concentrated in {sp['top']}" if sp["verdict"] == "concentrated" else "broad")
                for sp in followup.get("splits") or []]
    c = followup.get("chart")
    return {"id": fid, "kind": "drill", "source": {"run_id": run_id, "followup_id": followup["id"]},
            "title": f"Where the gap sits: {name(t)}", "question": followup["question"],
            "blocks": [{"id": "gap", "title": "Where the unexplained gap sits", "text": followup.get("answer") or ""}],
            "scope": f"{name(t)}, {(parent.get('scope') or {}).get('period', '')}", "facts": {},
            "words": verdicts + ["A split shows where a gap sits, not why."],
            "table": {"kind": "segments", "rows": rows}, "drivers": [], "territories": [t],
            "charts": {"segments": {k: v for k, v in c.items() if k != "id"}} if c else {}, "charts_shown": ["segments"] if c else []}


def finding_from_chart(fid: str, run_id: str, followup: dict, parent: dict) -> dict:
    """One chart a follow-up showed, with the run's numbers so text about it can use tokens."""
    base = finding_from_run(fid, run_id, parent)
    c = followup["chart"]
    return {**base, "kind": "chart", "blocks": [], "source": {"run_id": run_id, "followup_id": followup["id"]},
            "title": c["title"] if not re.search(r"\d", c["title"]) else base["title"],
            "charts": {c["id"]: {k: v for k, v in c.items() if k != "id"}}, "charts_shown": [c["id"]]}


def finding_from_explain(fid: str, run_id: str, followup: dict, parent: dict) -> dict:
    """An explanation: its sentences without digits (the numbers live in the run it explains)."""
    base = finding_from_run(fid, run_id, parent)
    lines = [ln for ln in (followup.get("answer") or "").splitlines() if ln.strip() and not re.search(r"\d", ln)]
    return {**base, "kind": "explain", "source": {"run_id": run_id, "followup_id": followup["id"]},
            "title": "An explanation" if re.search(r"\d", followup["question"]) else f"Explained: {followup['question']}",
            "question": followup["question"], "words": lines + base["words"],
            "blocks": [{"id": "explain", "title": "The explanation", "text": followup.get("answer") or ""}], "charts_shown": []}


# ---- rendering and checks ---------------------------------------------------------------------------------------

def _table(f: dict) -> str:
    t = f["table"]
    if t["kind"] == "segments":
        return "\n".join(f"- {r['label']}: {_fmt(r['pct'], 'pct')} {'down' if r['pct'] < 0 else 'up'} against "
                         f"{_fmt(r['peer'], 'pct')} {'down' if r['peer'] < 0 else 'up'} elsewhere; {_fmt(r['miss'], 'int')} TRx beyond peers"
                         for r in t["rows"])
    if t["kind"] == "screen":
        return "\n".join(f"- {r['label']}: miss {_fmt(r['miss'], 'int')} TRx ({_fmt(r['pct'] or 0, 'pct')} of forecast); "
                         f"beyond peers {_fmt(r['beyond'], 'int')}" for r in t["rows"])
    return "\n".join(f"- {r['label']}: {_fmt(r['miss'], 'int')} TRx ({_fmt(r['pct'] or 0, 'pct')})" for r in t["rows"])


OVERCLAIM = re.compile(r"\b(confirmed|prov(?:es|ed|en)|definitely|certainly|undoubtedly|clearly caused)\b", re.I)
LEVEL = re.compile(r"confidence (high|medium|low|inconclusive)")


def kpis_used(template: str, findings: dict[str, dict]) -> dict[str, dict]:
    """The forecast, actual and miss boxes the UI draws for each [[kpis F1]] marker."""
    out = {}
    for fid, key in BLOCK.findall(template):
        if fid not in findings or key not in {b["id"] for b in findings[fid].get("blocks") or []}:
            problems.append(f"[[block {fid} {key}]] is not a passage of a pinned finding")
    if "(figure)" in template:
        problems.append("a masked figure was copied; use the tokens for numbers")
    for fid in KPIS.findall(template):
        f = findings.get(fid)
        if f and {"forecast", "actual", "miss"} <= set(f["facts"]):
            out[fid] = {k: f["facts"][k]["value"] for k in ("forecast", "actual", "miss", "miss_pct") if k in f["facts"]}
            out[fid]["scope"] = f["scope"]
    return out


def blocks_used(template: str, findings: dict[str, dict]) -> dict[str, dict]:
    """The investigation's own verified passages the UI shows for each [[block F1 attribution]] marker."""
    out = {}
    for fid, key in BLOCK.findall(template):
        b = next((b for b in (findings.get(fid) or {}).get("blocks") or [] if b["id"] == key), None)
        if b:
            out[f"{fid} {key}"] = {"title": b["title"], "text": b["text"]}
    return out


def charts_used(template: str, findings: dict[str, dict]) -> dict[str, dict]:
    """The chart data the UI draws for each marker in a version."""
    return {f"{fid} {kind}": findings[fid]["charts"][kind] for fid, kind in CHART.findall(template)
            if fid in findings and kind in (findings[fid].get("charts") or {})}


def render(template: str, findings: dict[str, dict]) -> str:
    template = re.sub(r"(\{F\d+:[a-z0-9_]*(?:pct|share)\})\s*(?:%|percent\b)", r"\1", template)
    text = TOKEN.sub(lambda m: _fmt(findings[m.group(1)]["facts"][m.group(2)]["value"],
                                    findings[m.group(1)]["facts"][m.group(2)]["fmt"]), template)
    return TABLE.sub(lambda m: _table(findings[m.group(1)]), text)


def sections(rendered: str) -> tuple[str, list[dict]]:
    """The title (a first line starting with '# ') and the '## ' sections."""
    title, out, cur = "Forecast report", [], None
    for line in rendered.splitlines():
        if line.startswith("# ") and not out and cur is None:
            title = line[2:].strip()
        elif line.startswith("## "):
            cur = {"title": line[3:].strip(), "text": ""}
            out.append(cur)
        elif cur is not None:
            cur["text"] += line + "\n"
        elif line.strip():
            cur = {"title": "", "text": line + "\n"}
            out.append(cur)
    for s in out:
        s["text"] = s["text"].strip()
    return title, out


def check(template: str, findings: dict[str, dict], require_all: bool = False) -> list[str]:
    """Why a version may not be shown; empty when it may. With require_all, every pinned finding must appear (one of
    its tokens, its table or its chart): the report is drafted from all pinned content, and unpinning is how to drop one."""
    problems = []
    if require_all:
        cited = ({fid for fid, _ in TOKEN.findall(template)} | set(TABLE.findall(template))
                 | {fid for fid, _ in CHART.findall(template)} | set(KPIS.findall(template))
                 | {fid for fid, _ in BLOCK.findall(template)})
        for fid, f in findings.items():
            if fid not in cited:
                problems.append(f"{fid} ({f['title']}) is pinned but missing; use its tokens, table or chart")
    if not template.strip() or len(template) > MAX_CHARS * 2:
        problems.append("the report is empty or too long")
    for fid, key in TOKEN.findall(template):
        if fid not in findings or key not in findings[fid]["facts"]:
            problems.append(f"{{{fid}:{key}}} is not a token of a pinned finding")
    for fid in TABLE.findall(template):
        if fid not in findings or not findings[fid].get("table"):
            problems.append(f"[[table {fid}]] is not a table of a pinned finding")
    for fid, key in BLOCK.findall(template):
        if fid not in findings or key not in {b["id"] for b in findings[fid].get("blocks") or []}:
            problems.append(f"[[block {fid} {key}]] is not a passage of a pinned finding")
    if "(figure)" in template:
        problems.append("a masked figure was copied; use the tokens for numbers")
    for fid in KPIS.findall(template):
        if fid not in findings or not {"forecast", "actual", "miss"} <= set(findings[fid]["facts"]):
            problems.append(f"[[kpis {fid}]] needs a finding with a forecast, an actual and a miss")
    for fid, kind in CHART.findall(template):
        if fid not in findings or kind not in (findings[fid].get("charts") or {}):
            problems.append(f"[[chart {fid} {kind}]] is not a chart of a pinned finding")
    bare = DATE.sub(" ", BLOCK.sub(" ", KPIS.sub(" ", CHART.sub(" ", TABLE.sub(" ", TOKEN.sub(" ", template))))))
    if re.search(r"\d", bare):
        problems.append("a number is typed outside a token; every figure must be a token")
    used = set(TOKEN.findall(template))
    for fid, f in findings.items():
        if any(fid == u[0] and re.fullmatch(r"d\d+(_share)?", u[1]) for u in used) and "residual" in f["facts"] \
                and (fid, "residual") not in used and (fid, "residual_share") not in used:
            problems.append(f"{fid}'s drivers are stated without its unexplained residual")
    # Each driver's confidence word must sit next to its figure, and no other level may: a level stated for the wrong
    # driver is as wrong as none. The window runs from the figure's line (or the previous driver figure) to the next
    # driver figure or heading.
    marks = [(m.start(), m.end(), m.group(1), m.group(2)) for m in TOKEN.finditer(template) if re.fullmatch(r"d\d+", m.group(2))]
    heads = [m.start() for m in re.finditer(r"(?m)^#+ ", template)]
    for i, (start, end, fid, key) in enumerate(marks):
        if fid not in findings:
            continue
        word = next((m.group(1) for w in findings[fid]["words"] if w.startswith(f"{key} is ") for m in [LEVEL.search(w)] if m), None)
        if not word:
            continue
        line_start = template.rfind("\n", 0, start) + 1
        lo = max([line_start] + [marks[i - 1][1]] if i else [line_start])
        hi = min([marks[i + 1][0] if i + 1 < len(marks) else len(template)] + [h for h in heads if h > end] + [end + 400])
        window = (template[lo:start] + template[end:hi]).lower()
        others = {"high", "medium", "low", "inconclusive"} - {word}
        if not re.search(rf"\b{word}\b", window) or any(re.search(rf"\b{o}\b", window) for o in others):
            problems.append(f"{{{fid}:{key}}} needs its own confidence ({word}) beside it, and no other level")
    # Confidence stated in words: any clause that names a driver and speaks of confidence must give that driver's own
    # level and no other ("we are confident in the Metacora launch" for a medium driver is refused).
    levels = {}
    for f in findings.values():
        for k in [k for k in f["facts"] if re.fullmatch(r"d\d+", k)]:
            word = _level(f, k)
            key = f["facts"][k]["means"].split(":")[0].split()[0].strip(",")
            if word and len(key) > 3:
                levels.setdefault(key, set()).add(word)
    for clause in re.split(r"[.;,]|\band\b|\bbut\b|\bwhile\b", TOKEN.sub(" ", template)):
        if not re.search(r"\b(confiden\w*|certain\w*|sure|high|medium|low|inconclusive)\b", clause, re.I):
            continue
        for key, own in levels.items():
            if re.search(rf"\b{re.escape(key)}\b", clause):
                said = {w for w in ("high", "medium", "low", "inconclusive") if re.search(rf"\b{w}\b", clause, re.I)}
                if not said & own or said - own:
                    problems.append(f"the confidence stated for {key} is not its own ({' or '.join(sorted(own))})")
    if OVERCLAIM.search(template):
        problems.append("it overstates certainty (confirmed, proves, definitely); say the confidence level instead")
    if any(p.search(template) for p in ACTIONS):
        problems.append("it recommends a commercial action")
    if BANNED.search(template):
        problems.append("it uses a banned term")
    allowed_drivers = {d for f in findings.values() for d in f["drivers"]}
    # Owner names and the split dimension are not driver claims: "Market access" checks a finding, "payer channel"
    # says where a gap sits.
    scrubbed = re.sub(r"(?i)\b(market access|payer channels?|sales leadership and marketing|supply chain and trade)\b", " ", template)
    for driver, pattern in CATEGORIES.items():
        if pattern.search(scrubbed) and driver not in allowed_drivers:
            problems.append(f"it names a {driver} driver that no pinned finding holds")
    allowed_t = {t for f in findings.values() for t in f["territories"]}
    for tid, label in TERRITORY_NAMES.items():
        if tid != "NATIONAL" and re.search(rf"\b{re.escape(label)}\b", template) and tid not in allowed_t:
            problems.append(f"it names {label}, which no pinned finding covers")
    return list(dict.fromkeys(problems))


# ---- drafting ---------------------------------------------------------------------------------------------------

INTENT_LABEL = {"reliability": "Is the miss real", "screen": "The largest gaps", "where": "Where the miss sits",
                "drivers": "What drove the miss", "attribution": "How much each driver explains",
                "unknowns": "What remains unexplained", "next_checks": "What to check next",
                "assumptions": "Whether forecast assumptions need review", "audit": "Whether the findings reproduce",
                "communicate": "The explanation in brief"}
BLOCK_ORDER = ("data", "miss", "screen", "where", "attribution", "confidence", "candidates", "unknowns", "gap", "assumptions",
               "explain")


LEAD_IN = {  # code's opening line for a chapter when no model writes one; the passages below carry the detail
    "screen": "These are the territories with the largest misses over the period, each beside its miss beyond the rate the others share.",
    "where": "The miss is broken down by territory below, and the territories tie back to the national figure.",
    "attribution": "The miss splits into the usual forecast bias, the drivers below and an unexplained residual.",
    "drivers": "The candidate drivers found in the data were each tested against the territories they did not touch.",
    "unknowns": "Part of the miss has no identified driver; what is known and what is not is set out below.",
    "reliability": "Before explaining the miss, the data behind it was checked.",
    "assumptions": "The forecast's error before and after the competitor launch is compared below.",
    "next_checks": "The open questions and who should answer them are set out below.",
    "audit": "How the figures were produced and checked is set out below.",
    "communicate": "The explanation is summarized below.",
    "run": "The investigation's findings are set out below.",
    "weekly": "The miss week by week is shown below.",
    "drill": "Where the unexplained gap sits, segment by segment, is shown below; a location, not a cause.",
    "explain": "The reasoning behind this finding is set out below.",
    "chart": "",
}


def _chapter_title(f: dict) -> str:
    """A report heading named by subject and scope, never by the question that produced it."""
    if f["kind"] in ("run", "rerun"):
        return f"{INTENT_LABEL.get(f.get('intent') or '', 'The investigation')}: {f['scope']}"
    subject = {"weekly": "The miss week by week", "drill": "Where the unexplained gap sits",
               "explain": "The reasoning behind the findings", "chart": "In a chart"}.get(f["kind"], "Further detail")
    return f"{subject}: {f['scope']}"


def _plain_sentences(text: str, limit: int = 2) -> list[str]:
    """Digit-free sentences of a verified passage (code's own wording, safe to restate)."""
    out = []
    for line in text.splitlines():
        for sent in re.split(r"(?<=\.)\s+", line.lstrip("- ").strip()):
            if sent and not re.search(r"\d", sent) and len(sent) > 30 and not sent.endswith(":"):
                out.append(sent)
    return out[:limit]


def _notes(findings: list[dict], prefix: str) -> list[str]:
    seen, out = set(), []
    for f in findings:
        for w in f["words"]:
            if w.startswith(prefix) and not re.search(r"\d", w) and w not in seen:
                seen.add(w)
                out.append(w[len(prefix):] if prefix.endswith(": ") else w)
    return out


def _level(f: dict, k: str) -> str:
    return next((m.group(1) for w in f["words"] if w.startswith(f"{k} is ") for m in [LEVEL.search(w)] if m), "")


def _lead(findings: list[dict]) -> dict | None:
    return next((f for f in findings if {"forecast", "actual", "miss"} <= set(f["facts"])), None)


def code_prose(findings: list[dict]) -> dict[str, str]:
    """Code's own sentences for every paragraph (without a model, and for any paragraph a model got wrong)."""
    lead = _lead(findings)
    plain = [w.split(": ", 1)[1] for w in (lead["words"] if lead else []) if w.startswith("In plain words: ")]
    out = {"summary": " ".join(plain), "key_points": "", "conclusion": ""}
    if lead and not out["summary"]:
        fid = lead["id"]
        out["summary"] = (f"Over {lead['scope']}, Cardiovela's actual TRx came in at {{{fid}:actual}} against a forecast of "
                          f"{{{fid}:forecast}}, a miss of {{{fid}:miss}} TRx.")
    for f in findings:
        out[f["id"]] = LEAD_IN.get(f.get("intent") if f["kind"] in ("run", "rerun") else f["kind"], LEAD_IN["run"])
    if _notes(findings, "To check ("):
        out["conclusion"] = "The checks below would confirm or overturn these findings; none of them changes the forecast by itself."
    return out


def layout(findings: list[dict], prose: dict[str, str], title: str) -> str:
    """A report: executive summary with the boxes, one chapter per pinned finding (its interpretation, the
    investigation's verified passages and its chart), conclusions with who checks what, and a note on method."""
    lead = _lead(findings)
    scopes = list(dict.fromkeys(f["scope"] for f in findings))
    out = [f"# {title}", f"Covers: {'; '.join(scopes)}. Brand: Cardiovela (BXA). Measure: TRx against the locked four-week-ahead forecast."]
    out.append("## Executive summary")
    if lead:
        out.append(f"[[kpis {lead['id']}]]")
    if prose.get("summary"):
        out.append(prose["summary"].strip())
    for line in (prose.get("key_points") or "").splitlines():
        line = line.strip().lstrip("-• ").strip()
        if line:
            out.append(f"- {line}")
    for f in findings:
        out.append(f"## {_chapter_title(f)}")
        if prose.get(f["id"]):
            out.append(prose[f["id"]].strip())
        ids = [b["id"] for b in f.get("blocks") or []]
        for key in sorted(ids, key=lambda k: BLOCK_ORDER.index(k) if k in BLOCK_ORDER else len(BLOCK_ORDER)):
            if key == "miss" and f is lead:
                continue  # the boxes already show it
            if key == "data" and "every cut" in next(b["text"] for b in f["blocks"] if b["id"] == "data").lower():
                continue  # nothing to report: all data final
            if key == "checks":
                continue  # gathered under conclusions
            out.append(f"[[block {f['id']} {key}]]")
        for k in [k for k in f.get("charts_shown") or [] if k in (f.get("charts") or {})][:2]:
            out.append(f"[[chart {f['id']} {k}]]")
        if not ids and not f.get("charts_shown") and f.get("table"):
            out.append(f"[[table {f['id']}]]")
    checks = [f"- {w.replace('To check (', '').replace('): ', ': ', 1)}" for w in _notes(findings, "To check (")]
    if prose.get("conclusion") or checks:
        out.append("## Conclusions and next steps")
        if prose.get("conclusion"):
            out.append(prose["conclusion"].strip())
        out += checks
    caveats = _notes(findings, "Caveat: ")
    out.append("## About this report\n" + " ".join(caveats + [
        "Every figure comes from a stored query on the synthetic release, and the passages under each chapter are the "
        "investigation's own verified text. This report changes no forecast."]))
    return "\n".join(out)


def code_draft(findings: list[dict], title: str) -> str:
    """The report code assembles without a model."""
    return layout(findings, code_prose(findings), title)


PROMPT = """You write the prose of a forecast-miss report for a pharmaceutical Brand Manager, for Cardiovela (BXA), a
fictional brand. Code places the figures, the investigation's verified passages and the charts; you write the words a
reader needs around them, in full sentences and plain business language. Write it as a report: never mention questions,
follow-ups, the analyst or this tool; state findings directly ("Southeast missed most", not "the analyst asked..."):
- summary: an executive summary of four to six sentences: how big the miss was, what explains most of it and how
  sure we are, what is still unexplained, and what should happen next.
- key_points: two to four short lines, one per line, each a key finding.
- chapters: one paragraph of three to five sentences per pinned finding, each on its own line starting with its id
  and a colon (for example "F1: ..."): what the finding shows and why it matters. For a ranking, name the territories
  that matter and say what stands out.
- conclusion: two or three sentences that draw the findings together and say who should check what.
Each finding has its own period and place: say which one you mean, and never apply one finding's driver split or
shares to another finding's period. Use only the pinned findings, their notes and their passages. Every number must be one of the given tokens, written
exactly (for example {F1:miss}); never type a digit yourself (dates as YYYY-MM-DD are fine); the passages show numbers
as (figure), which you must never copy. Percent tokens already include the % sign. When you name a driver's size or
how sure we are about it, give its own confidence word (high, medium, low or inconclusive) in the same sentence; never
write "confirmed", "proves" or "definitely". Name no cause, territory or product the findings do not hold, recommend
no action on price, budget, targeting or the forecast, and do not use the words "surveillance" or "new patients". An
unexplained gap's location is not its cause. Call write_report once."""


def _mask(text: str) -> str:
    """A passage with its numbers masked (dates kept), so the model reads the reasoning but takes numbers from tokens."""
    parts = re.split(r"(\b\d{4}-\d{2}-\d{2}\b)", text)
    return "".join(p if DATE.fullmatch(p) else re.sub(r"-?\d[\d,]*(\.\d+)?%?", "(figure)", p) for p in parts)


def _brief(findings: list[dict]) -> str:
    parts = []
    for f in findings:
        facts = "\n".join(f"  {{{f['id']}:{k}}} = {v['means']}" for k, v in f["facts"].items())
        words = "\n".join(f"  - {w}" for w in f["words"] if not re.search(r"\d", w))
        table = f"\n  table available: [[table {f['id']}]] ({f['table']['kind']})" if f.get("table") else ""
        from .charts import DESCRIBE
        for k in (f.get("charts") or {}):
            table += f"\n  chart available: [[chart {f['id']} {k}]] ({DESCRIBE.get(k, k)})"
        passages = "\n".join(f"  [{b['title']}] " + _mask(b["text"]).replace("\n", " ") for b in f.get("blocks") or [])
        parts.append(f"{f['id']}: {_chapter_title(f)} (question: {f.get('question')})\n tokens:\n{facts}\n notes:\n{words}{table}"
                     + (f"\n passages (numbers masked):\n{passages}" if passages else ""))
    return "\n\n".join(parts)


def model_prose(findings: list[dict], spec: str, instruction: str | None, current: dict | None) -> tuple[dict, list[str]]:
    """The model's paragraphs, each checked on its own; a refused paragraph falls back to code's."""
    from agent_framework import Agent, tool

    from pharmagentics.llm import chat_client

    from .models import options

    by_id = {f["id"]: f for f in findings}
    base = code_prose(findings)
    got: dict = {}

    @tool
    def write_report(summary: Annotated[str, "Executive summary, four to six sentences"],
                     key_points: Annotated[str, "Two to four key findings, one per line"],
                     chapters: Annotated[str, "One paragraph per finding, each line starting with its id, e.g. F1: ..."],
                     conclusion: Annotated[str, "Two or three sentences: what it adds up to, and who checks what"]) -> str:
        """Submit the report's prose."""
        got.update(summary=summary, key_points=key_points, chapters=chapters, conclusion=conclusion)
        return "Received. Stop."

    task = "Pinned findings:\n\n" + _brief(findings)
    if current:
        task += "\n\nCurrent prose (keep what the request does not change):\n" + "\n".join(f"{k}: {v}" for k, v in current.items() if v)
    task += "\n\nRequest: " + (instruction or "Write the report's prose from these findings.")
    agent = Agent(client=chat_client(spec), name="report_writer", instructions=PROMPT, tools=[write_report],
                  default_options=options(spec, len(PROMPT) + len(task)))
    try:
        asyncio.run(asyncio.wait_for(agent.run(task), timeout=DRAFT_SECONDS))
    except Exception as exc:  # noqa: BLE001 - code's prose stands
        return dict(current or base), [f"the model failed ({type(exc).__name__})"]
    if not got:
        return dict(current or base), ["the model returned no prose"]
    proposed = {"summary": got.get("summary"), "key_points": got.get("key_points"), "conclusion": got.get("conclusion")}
    for m in re.finditer(r"(?m)^\s*(F\d+)\s*[:.-]\s*(.+)$", str(got.get("chapters") or "")):
        proposed[m.group(1)] = m.group(2)
    out, refused = {}, []
    for key in ["summary", "key_points", "conclusion"] + [f["id"] for f in findings]:
        raw = str(proposed.get(key) or "")
        text = "\n".join(" ".join(x.split()) for x in raw.splitlines() if x.strip()) if key == "key_points" else " ".join(raw.split())
        problems = check(text, by_id) if text else []
        if text and not problems:
            out[key] = text
        else:
            out[key] = (current or {}).get(key) or base.get(key, "")
            if problems:
                refused.append(f"{key}: {problems[0]}")
    return out, refused


def model_draft(findings: list[dict], spec: str, instruction: str | None, current: dict | None, title: str = "Forecast miss report"):
    """A whole version from the model's prose and code's layout. Returns (template, prose, refused paragraphs)."""
    prose, refused = model_prose(findings, spec, instruction, current)
    return layout(findings, prose, title), prose, refused
