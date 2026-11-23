"""Stages 5 and 6 for build 3 (brief-002 FR-026; Nov 6 traces C-018 and C-001).

Code writes every section. The writer adds the answer and one sentence per story; verification fails a
typed digit, a token no tool produced, a token from another story, and banned terms; one revision; what
still fails is dropped. Then the brief is assembled and rendered from the run's claims.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from pharmagentics.tools.registry import digits_outside_tokens

TOKEN = re.compile(r"\{c(\d+)\}")
BANNED = [(re.compile(r"surveillance", re.I), 'says "surveillance" (use "competitive intelligence")'),
          (re.compile(r"new patients?(?![^.]*\bNBRx\b)", re.I), 'says "new patients" about something other than NBRx')]


# What each number measures, written by code from the claim's own SQL, so the writer never has to guess a
# comparison (Nov 6 trace C-018; brief-002 FR-026). No counts: weeks are named by their dates.
_WEEK_SETS = re.compile(r"week_start in \(([^)]*)\)")
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
TOKEN_NUMBERS = re.compile(r"\{c(\d+)\}")
RELATIVE_WEEK = re.compile(r"\b(week before|last week|previous week|prior week|week earlier|week[- ]over[- ]week)\b", re.I)
YEAR_BACK = re.compile(r"\b(last year|year[- ]over[- ]year|a year ago|same week last year)\b", re.I)


def _span(weeks: list[str]) -> str:
    return f"the week of {weeks[0]}" if len(weeks) == 1 else f"the weeks {weeks[0]} to {weeks[-1]}"


def gloss(claim: dict, evidence: dict | None) -> dict:
    """{'text': what the number is, 'base_single': True when it compares with the single week before}."""
    query = (evidence or {}).get("query") or ""
    sets: list[list[str]] = []
    for group in _WEEK_SETS.findall(query):
        weeks = sorted(set(_ISO.findall(group)))
        if weeks and (not sets or sets[-1] != weeks):
            sets.append(weeks)
    scope = (evidence or {}).get("params") or {}
    params = ", ".join(f"{k} {v}" for k, v in scope.items())
    single, last_year = False, False
    if len(sets) >= 2 and claim["value"].endswith("%"):
        new, old = sets[0], sets[1]
        single = len(old) == 1 and len(new) == 1 and date.fromisoformat(old[0]) == date.fromisoformat(new[0]) - timedelta(days=7)
        text = f"a change: {_span(new)} against {_span(old)}" + (" (a week-over-week comparison)" if single else " (not week over week)")
        last_year = old == [(date.fromisoformat(w) - timedelta(weeks=52)).isoformat() for w in new]
        if last_year:
            text += " (same reporting weeks last year)"
    elif sets:
        text = f"a value for {_span(sets[0])}"
    else:
        text = "a value taken from the data"
    return {"text": text + (f" [{params}]" if params else ""), "base_single": single,
            "last_year": last_year, "small_cell": scope.get("small_cell", False)}


def glossary(shown: str, claims: list[dict], evidence: list[dict]) -> tuple[str, dict[str, dict]]:
    """Lines for the writer, one per token that appears in the sections, and the gloss data by token."""
    by_id = {e["id"]: e for e in evidence}
    seen = sorted({int(n) for n in TOKEN_NUMBERS.findall(shown) if 0 < int(n) <= len(claims)})
    data = {f"{{c{n}}}": gloss(claims[n - 1], by_id.get(claims[n - 1]["evidence_id"])) for n in seen}
    return "\n".join(f"{t} = {g['text']}" for t, g in data.items()), data


def tokens(text: str) -> set[str]:
    return {m.group(0) for m in TOKEN.finditer(text or "")}


# Reader-facing prose rules (brief-008 FR-004, FR-006): short sentences (ASD-STE100), one paragraph, no list, no
# raw IDs, no number spelled out by the model, no cause for a story that is not High, nothing from the folded detail.
MAX_WORDS = 25
BULLET = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+|\*\*|^\s*#{1,6}\s")
RAW_ID = re.compile(r"\b(?:(?:territory|competitor|cut):\w+|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|[A-Z]{5,}|[a-z]+(?:_[a-z0-9]+)+)\b")
NUMBER_WORDS = re.compile(r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                          r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundreds?|thousands?|millions?|billions?|"
                          r"percent|per cent|double[sd]?|triple[sd]?|twice|half)\b", re.I)
_CODE_PHRASES = re.compile(r"\b(?:\w+ weeks? (?:before|earlier)|four-brand|week of)\b", re.I)  # words code itself writes
CAUSAL = re.compile(r"\b(because|caused|causes|causing|drove|driven|drives|due to|led to|leads to|leading to|result of|"
                    r"resulted|responsible|reason (?:for|why)|is why|explains|explained by|thanks to|attributable|blamed?)\b", re.I)
FOLDED = re.compile(r"\b(splits?|by (?:plan|specialty|channel)|cuts of the change|considered and dropped|glossary)\b|\bmethod:", re.I)
REP = re.compile(r"\b(?i:reps?|representatives?)\s+(?:[A-Z][a-z]+|#)")
CONFIDENCE = re.compile(r"\bConfidence(?: for [^:]+)?:\s*(High|Medium|Low)\b")


def confidence(section: str) -> str | None:
    """The confidence a story's code section states ("Confidence for Southeast: Medium."), if any."""
    m = CONFIDENCE.search(section or "")
    return m.group(1) if m else None


def style(piece: str, max_sentences: int | None = None) -> list[str]:
    """Wording rules that need no data: one short paragraph, no list or markup, no raw ID, no spelled-out number,
    no rep named, nothing from the folded detail."""
    text = (piece or "").strip()
    if not text:
        return []
    out = []
    if "\n" in text or BULLET.search(text):
        out.append("is a list, has line breaks or markup (write one plain paragraph)")
    if (ids := RAW_ID.findall(text)):
        out.append(f"shows raw IDs or enum names {', '.join(dict.fromkeys(ids[:3]))} (use the readable name)")
    if (words := NUMBER_WORDS.findall(_CODE_PHRASES.sub("", text))):
        out.append(f"spells out numbers {', '.join(dict.fromkeys(w.lower() for w in words[:3]))} (use a claim token or no number)")
    if REP.search(text):
        out.append("names an individual rep")
    if (folded := FOLDED.search(text)):
        out.append(f'restates folded detail ("{folded.group(0)}"); splits, method and dropped cuts stay folded')
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", text) if x]
    if (long := [x for x in sentences if len(x.split()) > MAX_WORDS]):
        out.append(f"has a sentence of {len(long[0].split())} words (keep each to at most {MAX_WORDS})")
    if max_sentences and len(sentences) > max_sentences:
        out.append(f"has {len(sentences)} sentences (at most {max_sentences})")
    return out


def problems(piece: str, allowed: set[str], n_claims: int, glosses: dict[str, dict] | None = None,
             *, causal_ok: bool | None = None, max_sentences: int | None = None) -> list[str]:
    """What fails in one piece of writer prose. `causal_ok=False` rejects causal wording (the story is not High);
    `None` skips that check."""
    out = []
    if (bad := digits_outside_tokens(piece)):
        out.append(f"typed numbers {', '.join(bad[:5])}")
    used = tokens(piece)
    invented = sorted(t for t in used if not 0 < int(t[2:-1]) <= n_claims)
    if invented:
        out.append(f"tokens no tool produced {', '.join(invented)}")
    foreign = sorted(t for t in used - allowed if t not in invented)
    if foreign:
        out.append(f"tokens from another part of the brief {', '.join(foreign)}")
    out += [why for rx, why in BANNED if rx.search(piece or "")]
    out += style(piece, max_sentences)
    if causal_ok is False and (m := CAUSAL.search(piece or "")):
        out.append(f'says "{m.group(0)}", but confidence is not High (say "association", not cause)')
    if glosses is not None:  # wording: a comparison is described only as the glossary states it
        if RELATIVE_WEEK.search(piece or "") and not any(glosses.get(t, {}).get("base_single") for t in used):
            out.append('compares with "the week before", but none of its numbers is a week-over-week comparison '
                       "(describe it as the glossary does)")
        if YEAR_BACK.search(piece or "") and not any(glosses.get(t, {}).get("last_year") for t in used):
            out.append("compares with last year, but no number in this brief does")
        if any(glosses.get(t, {}).get("small_cell") for t in used):
            out.append("uses a noisy small-cell figure in a summary sentence")
    return out


def normalize(reply: dict, story_ids) -> dict:
    """Match the writer's story keys to story ids leniently ('PACIFIC' or 'Pacific' for 'territory:PACIFIC')."""
    ids = [s for s in story_ids if s != "_sections"]
    out = {}
    for key, sentence in (reply.get("stories") or {}).items():
        k = str(key).strip()
        match = k if k in ids else next((i for i in ids if i.split(":", 1)[-1].lower() == k.lower().replace(" ", "_").replace("-", "_")), k)
        out[match] = sentence
    return {**reply, "stories": out}


ANSWER_SENTENCES, STORY_SENTENCES, CHART_SENTENCES = 4, 5, 3


def check(reply: dict, story_tokens: dict[str, set[str]], n_claims: int,
          glosses: dict[str, dict] | None = None, confidences: dict[str, str | None] | None = None) -> dict[str, list[str]]:
    """Problems per piece: 'answer' and each story id. With `confidences` (story id to its stated confidence), a
    story's prose may use causal wording only when that confidence is High, and the answer only when every story is."""
    reply = normalize(reply, story_tokens)
    every = set().union(*story_tokens.values(), story_tokens.get("_sections", set()))
    found = {}
    answer_causal = None if confidences is None else bool(confidences) and all(c == "High" for c in confidences.values())
    if (p := problems(str(reply.get("answer", "")), every, n_claims, glosses, causal_ok=answer_causal,
                      max_sentences=ANSWER_SENTENCES)):
        found["answer"] = p
    for sid, sentence in (reply.get("stories") or {}).items():
        if sid not in story_tokens:
            continue  # an entry for a story this brief does not have is discarded, not revised (small models invent them)
        causal = None if confidences is None else confidences.get(sid) == "High"
        if (p := problems(str(sentence), story_tokens[sid], n_claims, glosses, causal_ok=causal,
                          max_sentences=STORY_SENTENCES)):
            found[sid] = p
    return found


def clean(reply: dict, story_tokens: dict[str, set[str]], n_claims: int,
          glosses: dict[str, dict] | None = None, confidences: dict[str, str | None] | None = None) -> tuple[str, dict[str, str], list[str]]:
    """Keep only the pieces that pass; report what was dropped."""
    reply = normalize(reply, story_tokens)
    bad = check(reply, story_tokens, n_claims, glosses, confidences)
    answer = "" if "answer" in bad else str(reply.get("answer", "")).strip()
    stories = {sid: str(s).strip() for sid, s in (reply.get("stories") or {}).items()
               if sid in story_tokens and sid != "_sections" and sid not in bad and str(s).strip()}
    dropped = [f"{k}: {'; '.join(v)}" for k, v in bad.items()]
    return answer, stories, dropped


def sections_text(sections: dict, close: dict, stories: list[dict]) -> str:
    """What the writer sees: the memo's code sections, each story labelled with its id."""
    parts = ["[title]", *sections["title"], "[bottom line, by code]", *close["bottom_line"]]
    if close.get("kpis"):  # shown as tiles above the bottom line: the reader sees them, so the answer need not repeat them
        parts += ["[figure tiles, shown above the bottom line]",
                  *(f"{k['label']}: {k['value']}" + (f" ({k['detail']})" if k.get("detail") else "") for k in close["kpis"])]
    parts += ["[the numbers]", *sections["numbers"]]
    table = sections.get("territory_table")
    if table:  # per-territory figures sit in a table; only territories that are not plainly observed are named here
        odd = [f"{r['cells'][0]} ({r['basis']})" for r in table["rows"] if r.get("basis") not in (None, "observed")]
        parts += ["[territory table, shown under the numbers: one row per territory]"] + ([f"Not observed: {', '.join(odd)}."] if odd else [])
    parts += ["[what the data can't tell us]", *sections["limits"]]
    for s in stories:
        parts += [f"[story {s['id']}]", s["section"]]
    for key, chart in chart_targets(close, stories).items():
        parts += [f"[chart {key}]", f"Caption: {chart['caption']}", f"Explanation, by code: {chart['explanation']}"]
    return "\n".join(parts)


def chart_targets(close: dict, stories: list[dict]) -> dict[str, dict]:
    """The charts the writer may explain, by key: "2", "4" and each story id (brief-003 FR-024)."""
    charts = close.get("charts") or {}
    out = {k: charts[k] for k in ("2", "4") if charts.get(k)}
    for s in stories:
        if s["id"].startswith("cut:"):  # a plan cut card has no chart of its own
            continue
        chart = charts.get("competitor") if s["id"].startswith("competitor:") else (charts.get("stories") or {}).get(s.get("territory") or "")
        if chart:
            out[s["id"]] = chart
    return out


def chart_explanations(reply: dict, close: dict, stories: list[dict], n_claims: int,
                       glosses: dict[str, dict] | None = None) -> tuple[dict[str, str], list[str]]:
    """The writer's chart lines that pass the same checks as its sentences, using only that chart's tokens.
    A failing line is not revised: the chart keeps the explanation code wrote."""
    targets, kept, dropped = chart_targets(close, stories), {}, []
    for key, line in (reply.get("charts") or {}).items():
        key, line = str(key).strip(), str(line).strip()
        if key not in targets or not line:
            continue
        allowed = tokens(targets[key]["caption"] + "\n" + targets[key]["explanation"])
        bad = problems(line, allowed, n_claims, glosses, max_sentences=CHART_SENTENCES)
        if bad:
            dropped.append(f"chart {key}: {'; '.join(bad)}")
        else:
            kept[key] = line
    return kept, dropped


def section_tokens(sections: dict, close: dict) -> set[str]:
    """Tokens the answer may use besides the stories': the title, bottom line, numbers and limits."""
    tiles = [f"{k.get('value', '')} {k.get('detail') or ''}" for k in close.get("kpis") or []]
    return tokens("\n".join(sections["title"] + close["bottom_line"] + sections["numbers"] + sections["limits"] + tiles))


def _story_title(sid: str) -> str:
    from pharmagentics.tools.queries import name

    kind, _, key = sid.partition(":")
    return "Competitor Metacora" if kind == "competitor" else name(key)


def place_cuts(stories: list[dict], cuts: list[dict]) -> list[dict]:
    """Each plan cut card after its territory's story (and after the cut cards already placed there), else at the end
    of the stories: the §3 order of brief-010 (the territory story, then its cut cards)."""
    out = list(stories)
    for cut in cuts:
        after = [i for i, s in enumerate(out) if s.get("territory") == cut["territory"]]
        out.insert(after[-1] + 1 if after else len(out), cut)
    return out


def assemble(sections: dict, close: dict, stories: list[dict], answer: str, sentences: dict[str, str],
             left_out: list[str], dropped_line: str, chart_lines: dict[str, str] | None = None) -> tuple[str, list[dict]]:
    """The memo (brief-003): code sections from the MCP session, the writer's answer as §1 prose and its story
    sentences as §3 prose, composed by the same code as the scripted brief."""
    from pharmagentics.tools import memo

    targets = {k: dict(c, explanation=(chart_lines or {}).get(k) or c["explanation"])
               for k, c in chart_targets(close, stories).items()}
    cards, folded = close.get("story_cards") or {}, close.get("story_details") or {}
    key = lambda s: (s["id"] if s["id"].startswith("cut:") else "competitor" if s["id"].startswith("competitor:")  # noqa: E731
                     else (s.get("territory") or ""))
    blocks = [memo.StoryBlock(s["id"], s.get("title") or _story_title(s["id"]),memo.without_next(s["section"]).split("\n"),
                              sentences.get(s["id"], ""), chart=targets.get(s["id"]), card=cards.get(key(s)),
                              detail=folded.get(key(s), [])) for s in stories]
    notes: list[str] = []
    dropped: list[str] = []  # folded under §3's detail
    if sections.get("calendar"):
        notes.append("No story is opened for a calendar week. Expect a rebound in the next regular week.")
        blocks = []
    else:
        notes += left_out
        if not stories and not left_out:
            notes.append("Routine week. No material change was found, and territory swings stayed in their normal range.")
        elif dropped_line:
            dropped.append(dropped_line)
    if close.get("national_story"):  # packet NC: the national TRx card, when no competitor story carries it
        blocks.append(memo.StoryBlock(**close["national_story"]))
    blocks.extend(memo.StoryBlock(**story) for story in sections.get("restatement_stories", []))  # brief-010 FR-005
    blocks.extend(memo.StoryBlock(**story) for story in sections.get("promotion_stories", []))
    parts = memo.MemoParts(title=sections["title"], bottom_line=close["bottom_line"], numbers=sections["numbers"],
                           limits=sections["limits"], next_checks=close["next_checks"],
                           appendix=sections["appendix"] + close.get("driver_timing", []),
                           stories=blocks, story_notes=notes, answer=answer,
                           charts={k: targets[k] for k in ("2", "4") if k in targets},
                           kpis=close.get("kpis") or [], territory_table=sections.get("territory_table"),
                           details={"1": (close.get("details") or {}).get("1", []), "2": (sections.get("details") or {}).get("2", []),
                                    "3": dropped, "4": (sections.get("details") or {}).get("4", [])})
    return memo.compose(parts)


def render(template: str, claims: list[dict]) -> tuple[str, list[dict], list[dict], dict[int, int]]:
    """Fill tokens from the run's claims; return the text, the claims it uses (in order of use), where each sits
    in the text (inline citations, indexed into the used claims) and the token-number-to-used-index map."""
    from pharmagentics.tools.registry import cite

    used = list(dict.fromkeys(int(m.group(1)) for m in TOKEN.finditer(template) if 0 < int(m.group(1)) <= len(claims)))
    index = {n: i for i, n in enumerate(used)}
    text, spans = cite(template, claims, index=index)
    return text, [claims[n - 1] for n in used], spans, index


def flow(base: list[dict], plan: dict, record: dict, tools: list[str], revised: bool, model: str) -> list[dict]:
    """The Phase A stage flow with the agents named (brief-002 US7 scenario 2)."""
    out = [dict(s) for s in base]
    agent = lambda name: {"kind": "agent", "name": name}  # noqa: E731
    s4 = out[3]
    if s4["states"]:
        actors = [{"kind": "code", "name": "triage rules (screen, caps, withheld cuts, continuing stories)"},
                  agent(f"manager (triage plan, {model})")]
        if record.get("reviewed_by_person"):
            actors.append({"kind": "human", "name": "Commercial Analyst (plan review)"})
        actors += [agent("manager (coordinates each story)"), agent("Data Forensics"), agent("Driver Investigator")]
        s4 = dict(s4, actors=actors)
        called = sorted(set(tools))
        s4["note"] = (s4["note"].replace(" The analyst changed the code plan.", "")
                      + (" Plan flagged: " + " ".join(plan.get("flags", [])) if plan.get("flagged") else "")
                      + (f" Tools called: {', '.join(called)}." if called else ""))
        out[3] = s4
    out[4] = dict(out[4], actors=[{"kind": "code", "name": "brief sections (claim tokens)"},
                                  {"kind": "llm", "name": f"writer: answer and one sentence per story ({model})"}],
                  note="Code writes every section; the writer adds the answer and one sentence per story.")
    actors6 = [{"kind": "code", "name": "number, token and wording checks"}]
    if revised:
        actors6.append({"kind": "llm", "name": "one revision of failing sentences"})
    out[5] = dict(out[5], actors=actors6)
    return out
