"""Scripted follow-ups on a brief (brief-006 FR-004; Session 2026-11-20). No model, no new query.

The scripted engine answers only from the brief it is asked about: its sections, claims and evidence. It serves the
suggested questions (chips); free text goes to the agent when a model is configured (threads.py, 2026-11-27). In order:

1. which section: the pinned chip, else "§3.1" in the text, else the Bottom line;
2. out of scope (another territory with no story here, another product, another week): say what the brief covers
   and offer a brief for the other scope; no number;
3. "why" about a projected or estimated territory: no driver can be named for that cut (brief-003 FR-023);
4. a split or a number the brief does not hold: say so and offer the agent;
5. otherwise: restate the section, citing it.

Every number in an answer is one of the brief's own claim values; section references are identifiers.
"""
from __future__ import annotations

import re

from .queries import TERRITORY_NAMES
from .brands import PRODUCTS
from .window import Comparison

SECTION_REF = re.compile(r"§\s*(\d(?:\.\d+)?)")
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NEW_NUMBER = re.compile(r"\b(split|break\s?down|breakdown|by plan|by specialty|by channel|by payer|per plan|which plans?|"
                        r"how many|how much|what about|compare|versus|vs\.?)\b", re.I)
_BASELINE = re.compile(r"\b(comparison(?: window)?|baseline|compare)\b", re.I)
_LAST_YEAR = re.compile(r"\b(?:same (?:weeks? )?last year|same weeks? (?:a|one) year ago)\b", re.I)
_PREVIOUS = re.compile(r"\b(?:previous|prior|preceding|last) (\d{1,2}) weeks?\b", re.I)
WHY = re.compile(r"\b(why|cause[sd]?|driver|drove|reason|explain)\b", re.I)
REP = re.compile(r"\b(which|what|name|named|who)\b[^.?!]*\b(reps?|representatives?|salespeople|sales ?person)\b|"
                 r"\b(reps?|representatives?)\b[^.?!]*\b(name|names|named|who|which)\b", re.I)
SUGGESTIONS = {  # per section kind, phrased so the scripted engine can answer them (brief-006 FR-006)
    "1": ["What is this brief least sure of?", "Restate the bottom line"],
    "2": ["Which territories are projected or estimated?", "Restate the numbers"],
    "3": ["What did the checks find?", "Split this by plan"],
    "4": ["Why is a cut withheld?", "Restate the data limits"],
    "5": ["Who owns the next checks?", "Restate the next checks"],
}


def is_suggested(question: str) -> bool:
    """True when the question is one of the code-written suggestions (a chip), so the scripted engine answers it."""
    asked = " ".join((question or "").split()).lower()
    return any(asked == " ".join(t.split()).lower() for texts in SUGGESTIONS.values() for t in texts)


def suggestions(sections: list[dict]) -> dict[str, list[str]]:
    """Two code-written suggestions for each section, by its kind (story subsections share §3's)."""
    out = {}
    for s in sections:
        kind = s["number"].split(".")[0]
        if kind in SUGGESTIONS:
            out[s["number"]] = SUGGESTIONS[kind]
    return out


def _labelled(sections: list[dict], number: str) -> dict[str, str]:
    """Territories §2 marks as projected or estimated: name -> basis."""
    two = next((s for s in sections if s["number"] == number), None)
    found = {}
    for line in ((two or {}).get("text", "") + "\n" + (two or {}).get("detail", "")).splitlines():  # levels are folded (brief-008)
        m = re.match(r"(?:- )?([A-Za-z \-]+): .*\((projected|estimated)\b", line)
        if m:
            found[m.group(1).strip()] = m.group(2)
    return found


def _story_territories(sections: list[dict]) -> set[str]:
    return {s["title"] for s in sections if s["number"].startswith("3.")}


def _scope(result: dict) -> tuple[str, str, str]:
    return result.get("brand_id", "BXA"), result.get("territory_id", "NATIONAL"), str(result.get("week_start", ""))


def _pick(result: dict, idx: list[int]) -> tuple[list[dict], list[dict]]:
    claims = [result["claims"][i] for i in idx if 0 <= i < len(result.get("claims", []))]
    ids = {c["evidence_id"] for c in claims}
    return claims, [e for e in result.get("evidence", []) if e["id"] in ids]


def _comparison_offer(question: str, brand: str, territory: str, week: str) -> dict | None:
    """Keep changes to comparison windows within a new brief's scope."""
    choice = None
    if _LAST_YEAR.search(question):
        choice = {"kind": "last_year"}
    elif _BASELINE.search(question):
        dates = ISO.findall(question)
        if len(dates) == 2:
            choice = {"kind": "custom", "start": dates[0], "end": dates[1]}
        elif match := _PREVIOUS.search(question):
            choice = {"kind": "previous", "weeks": int(match[1])}
        elif re.search(r"\b(?:change|replace|different|custom|set|choose)\b", question, re.I):
            return {"brand": brand, "territory": territory, "week": week, "choose_comparison": True}
    if choice is None:
        return None
    offer = {"brand": brand, "territory": territory, "week": week, "choose_comparison": True}
    try:
        return {**offer, "comparison": Comparison.model_validate(choice).model_dump(mode="json", exclude_none=True)}
    except ValueError:
        return offer


def answer(result: dict, question: str, section: str | None = None) -> dict:
    """One scripted turn. `result` is the stored brief (its `sections`, `claims` and `evidence`)."""
    sections = result.get("sections") or []
    by_number = {s["number"]: s for s in sections}
    ref = section or (m.group(1) if (m := SECTION_REF.search(question or "")) else None) or "1"
    brand, territory, week = _scope(result)
    names = {v: k for k, v in TERRITORY_NAMES.items() if k != "NATIONAL"}
    here = TERRITORY_NAMES.get(territory, territory)
    text = question or ""
    base = {"engine": "scripted", "claims": [], "evidence": [], "cited": [], "offer": None}

    if ref not in by_number:
        listed = ", ".join(f"§{s['number']} {s['title']}" for s in sections)
        return {**base, "kind": "no_section", "answer": f"This brief has no §{ref}. Its sections are: {listed}."}

    stories = _story_territories(sections)
    other_terr = next((n for n in names if re.search(rf"\b{re.escape(n)}\b", text, re.I) and n != here and n not in stories), None)
    other_prod = next((code for code, nm in PRODUCTS.items() if code != brand and re.search(rf"\b{code}\b", text)), None) or \
        next((code for code, nm in PRODUCTS.items() if code != brand and code != "BXE" and re.search(rf"\b{nm}\b", text, re.I)), None)
    other_week = next((d for d in ISO.findall(text) if d != week), None)
    if offer := _comparison_offer(text, other_prod or brand, names.get(other_terr, territory), week):
        return {**base, "kind": "out_of_scope", "offer": offer,
                "answer": "Generate a new brief with that comparison window. The current brief keeps its original comparison."}
    if other_terr or other_prod or other_week:
        offer = {"brand": other_prod or brand, "territory": names.get(other_terr, territory) if other_terr else territory,
                 "week": other_week or week}
        label = " · ".join(x for x in (offer["brand"], TERRITORY_NAMES.get(offer["territory"], offer["territory"]),
                                       f"week of {offer['week']}"))
        return {**base, "kind": "out_of_scope", "offer": offer,
                "answer": f"This brief covers {brand}, {here}, week of {week}, and stays as it is. "
                          f"Generate a brief for {label} to answer that."}

    if REP.search(text):  # Briefing B-VI: no line identifies an individual rep
        return {**base, "kind": "no_individual", "cited": [ref],
                "answer": "The brief never names or singles out an individual rep. Promotion activity is aggregated "
                          "by territory before anyone sees it; ask about the territory instead."}

    labelled = _labelled(sections, "2")
    if WHY.search(text):
        named = next((n for n in labelled if re.search(rf"\b{re.escape(n)}\b", text, re.I)), None)
        if named:
            return {**base, "kind": "no_driver", "cited": ["4"] if "4" in by_number else [],
                    "answer": f"No driver can be named for {named}: its level in this brief is {labelled[named]}, "
                              "an assumption, not an observed count. See §4."}

    s = by_number[ref]
    if match := re.search(r"\bby (plan|specialty|channel)\b", text, re.I):
        dimension = match[1].lower()
        prefix = f"Cuts of the change by {dimension}"
        lines = ((s.get("text") or "") + "\n" + (s.get("detail") or "")).splitlines()  # the splits are folded (brief-008)
        for i, line in enumerate(lines):
            if line.startswith(prefix):
                block = [line]
                for row in lines[i + 1:]:
                    if not row.startswith("- "):
                        break
                    block.append(row)
                claims, evidence = _pick(result, s.get("claims") or [])
                evidence = [e for e in evidence if e["tool"] == "split_change" and e["params"].get("by") == dimension]
                ids = {e["id"] for e in evidence}
                return {**base, "kind": "restate", "cited": [ref], "evidence": evidence,
                        "claims": [c for c in claims if c["evidence_id"] in ids],
                        "answer": f"§{ref} {s['title']}:\n" + "\n".join(block)}
    if NEW_NUMBER.search(text):
        return {**base, "kind": "not_in_brief", "cited": [ref], "offer": {"agent": True},
                "answer": f"That number is not in this brief. The scripted engine answers only from the brief's own "
                          f"numbers (§{ref} {s['title']}); where the agent is configured, type the question to run a new query."}

    claims, evidence = _pick(result, s.get("claims") or [])
    body = "\n".join(x for x in (s.get("text"), s.get("prose")) if x)
    return {**base, "kind": "restate", "cited": [ref], "claims": claims, "evidence": evidence,
            "answer": f"§{ref} {s['title']}:\n{body}" if body else f"§{ref} {s['title']} has no text."}
