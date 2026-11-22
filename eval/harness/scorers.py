"""Scorers. Code checks run on every run; LLM judges run only with --judge and stay report-only
until their agreement with human labels is measured (Evaluation Pack open item 2)."""
from __future__ import annotations

import re
from dataclasses import replace

import duckdb
from mlflow.entities import Feedback
from mlflow.genai.scorers import scorer

from .numbers import Number, as_numbers, contains_phrase, extract, matches, parse_token, same, states, unique
from .paths import DATABASE
from .versions import data_fingerprint

# numbers_match_golden stays report-only: a system with evidence may state correct numbers the golden answer omits.
GATED = ("must_not_say", "governed_terms", "no_individual_rep", "claims_reconcile", "numbers_traced", "links_resolve",
         "sections_exist")


# core-011 FR-019: targets, report-only. Pooled key-fact recall (stated over all must facts) and finding recall
# (points over all possible points). FR-021: when these join GATED (FR-006), `over_word_budget` joins with them.
TARGETS: dict[str, float] = {"key_fact_recall": 0.85, "finding_recall": 0.90}
GATED_WHEN_REVIEWED = ("key_fact_recall", "finding_recall", "over_word_budget")  # not gated now; see FR-006, FR-021


def _answer(outputs) -> str:
    return (outputs.get("answer") or "") if isinstance(outputs, dict) else str(outputs or "")


def _golden(expectations) -> list:
    """The golden answer's numbers (unit known) plus fact values the text does not already carry. A fact value has
    no unit, so one that the text states exactly (22.5 beside "22.5%") is dropped in favour of the text's number."""
    stated = extract(expectations.get("expected_response", ""))
    exact = {(abs(n.value), n.decimals) for n in stated}
    facts = [f for f in as_numbers(expectations.get("golden_numbers", [])) if (abs(f.value), f.decimals) not in exact]
    return unique(stated) + facts


def _exacts(expectations) -> list[tuple[Number, float]]:
    """(written figure, exact value) for each numeric fact whose SQL ran (core-011 FR-016)."""
    return [(as_numbers([f["value"]])[0], f["exact"]) for f in expectations.get("fact_exact") or []
            if f.get("exact") is not None]


def _unit_ok(a: Number, b: Number) -> bool:
    return a.percent is None or b.percent is None or a.percent == b.percent


def _golden_stated(g: Number, found: list[Number], exacts) -> bool:
    """A golden number backed by a fact (it is the fact's exact value at its own precision, or the fact's written
    figure) is stated by any answer number that prints that exact value at the answer's precision; one no fact
    backs falls back to `matches`. So a golden "22.5%" (exact 22.45) is stated by "22%", and a brief that prints
    the true value is never failed by a figure the golden file rounded twice."""
    # A written figure backs g only when it is at least as precise: same() rounds to the coarser of the two, so a
    # fact written "1" would otherwise back a golden "0.656" and ask the answer for 1.
    backing = [e for written, e in exacts if states(g, e) or (written.decimals >= g.decimals and same(g, written))]
    if backing:
        return any(_unit_ok(g, n) and states(n, e) for n in found for e in backing)
    return any(matches(g, n) for n in found)


@scorer(name="numbers_match_golden",
        description="Share of numbers in the answer that match a golden number (EV-1.1 / FE-04 proxy).")
def numbers_match_golden(outputs, expectations) -> Feedback:
    found, golden = extract(_answer(outputs)), _golden(expectations)
    if not found:
        return Feedback(value=1.0, rationale="The answer states no numbers to check.")
    exacts = _exacts(expectations)
    unmatched = [n.text for n in found
                 if not any(matches(n, g) for g in golden) and not any(states(n, e) for _, e in exacts)]
    share = 1 - len(unmatched) / len(found)
    note = f"{len(found) - len(unmatched)} of {len(found)} numbers match the golden answer"
    return Feedback(value=round(share, 4), rationale=note + (f"; unmatched: {', '.join(unmatched)}" if unmatched else "."))


@scorer(name="golden_number_recall",
        description="Share of the golden answer's numbers that the answer states.")
def golden_number_recall(outputs, expectations) -> Feedback:
    golden, found = unique(extract(expectations.get("expected_response", ""))), extract(_answer(outputs))
    if not golden:
        return Feedback(value=1.0, rationale="The golden answer states no numbers.")
    exacts = _exacts(expectations)
    missing = [g.text for g in golden if not _golden_stated(g, found, exacts)]
    note = f"{len(golden) - len(missing)} of {len(golden)} golden numbers stated"
    return Feedback(value=round(1 - len(missing) / len(golden), 4),
                    rationale=note + (f"; missing: {', '.join(missing[:12])}" if missing else "."))


@scorer(name="must_not_say", description="None of the case's must-not-say phrases appears.")
def must_not_say(outputs, expectations) -> Feedback:
    text, phrases = _answer(outputs), expectations.get("must_not_say", [])
    hits = [p for p in phrases if contains_phrase(text, p)]
    if hits:
        return Feedback(value=False, rationale="Says: " + "; ".join(f'"{h}"' for h in hits))
    return Feedback(value=True, rationale=f"None of {len(phrases)} literal phrases appears.")


@scorer(name="governed_terms",
        description='No "surveillance"; "new patients" only for NBRx (EV-9.2).')
def governed_terms(outputs) -> Feedback:
    text, problems = _answer(outputs), []
    if re.search(r"\bsurveillance\b", text, re.I):
        problems.append('uses "surveillance"')
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if re.search(r"\bnew patients\b", sentence, re.I) and not re.search(r"\bNBRx\b|new-to-brand", sentence, re.I):
            problems.append(f'"new patients" not tied to NBRx: "{sentence.strip()[:120]}"')
    return Feedback(value=not problems, rationale="; ".join(problems) or "Governed wording.")


_REP = re.compile(
    r"\b(?:[Ss]ales\s+)?[Rr]ep(?:resentative)?s?\s+(?:named\s+)?"
    r"(?!(?:Calls?|Vacanc\w*|Activity|Coverage|Counts?|Visits?)\b)[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
    r"|\b[Rr]ep(?:resentative)?\s*(?:ID|Id|id|#|[Nn]o\.)\s*[\w-]+"
)


@scorer(name="no_individual_rep", description="No line names or numbers an individual rep (EV-9.1). Heuristic.")
def no_individual_rep(outputs) -> Feedback:
    hits = [m.group(0) for m in _REP.finditer(_answer(outputs))]
    return Feedback(value=not hits, rationale=("Points to a rep: " + "; ".join(hits)) if hits else "No rep-level line.")


_SECTION_REF = re.compile(r"§\s*(\d+(?:\.\d+)?)")


@scorer(name="sections_exist",
        description="Every section a follow-up cites exists in its brief (brief-006 FR-005, SC-002).")
def sections_exist(outputs) -> Feedback:
    outputs = outputs if isinstance(outputs, dict) else {}
    if outputs.get("follow_up_answer") is None:
        return Feedback(value=1.0, rationale="No follow-up in this case.")
    have = set(outputs.get("brief_sections") or [])
    cited = set(outputs.get("cited") or []) | set(_SECTION_REF.findall(outputs["follow_up_answer"]))
    missing = sorted(cited - have)
    return Feedback(value=0.0 if missing else 1.0,
                    rationale=f"Cites sections the brief does not have: {', '.join(missing)}." if missing
                    else f"Cites {', '.join(sorted(cited)) or 'no section'}; all exist.")


DETERMINISTIC = [numbers_match_golden, golden_number_recall, must_not_say, governed_terms, no_individual_rep,
                 sections_exist]


# core-011: key facts, findings and brevity. Report-only until two runs after the golden review (FR-006).
# "Not scored" is Feedback(value=None): MLflow leaves a None value out of `<scorer>/mean` (aggregation.py), so a
# case with nothing to check never counts as 1.0 or 0.0.
def _not_scored(why: str) -> Feedback:
    return Feedback(value=None, rationale=f"Not scored: {why}.")


def fact_stated(fact: dict, found: list[Number]) -> bool:
    """A must-state fact is stated when an extracted number prints the fact's exact value (from its SQL) at the
    number's own precision (core-011 FR-016), or, with no exact value, matches the written figure at its stated
    precision; or within its relative tolerance when one is set."""
    value, tolerance, exact = fact["value"], fact.get("tolerance"), fact.get("exact")
    target = [replace(t, percent=fact.get("percent")) for t in as_numbers([value])]
    if exact is not None:
        if any(_unit_ok(n, t) and states(n, exact) for n in found for t in target):
            return True
    elif any(matches(n, t) for n in found for t in target):
        return True
    if tolerance is None:
        return False
    unit = fact.get("percent")
    return any(abs(abs(n.value) - abs(value)) <= tolerance * abs(value) for n in found
               if unit is None or n.percent == unit)


def key_fact_counts(outputs, expectations) -> tuple[int, list[str], int]:
    """(stated, missing ids, total) over the case's must-state numeric facts."""
    facts = expectations.get("key_facts") or []
    found = extract(_answer(outputs))
    missing = [f["id"] for f in facts if not fact_stated(f, found)]
    return len(facts) - len(missing), missing, len(facts)


@scorer(name="key_fact_recall",
        description="Share of the case's must-state facts that the answer states (core-011 FR-003). Report only.")
def key_fact_recall(outputs, expectations) -> Feedback:
    stated, missing, total = key_fact_counts(outputs, expectations)
    if not total:
        return _not_scored("the case has no must-state facts")
    note = f"{stated} of {total} must-state facts stated"
    return Feedback(value=round(stated / total, 4), rationale=note + (f"; missing: {', '.join(missing)}" if missing else "."))


def _cards(outputs) -> list[dict]:
    """Story cards that name a territory: `card` on sections numbered 3.N (core-011 plan)."""
    sections = outputs.get("sections") if isinstance(outputs, dict) else None
    cards = []
    for section in sections or []:
        card = section.get("card") if isinstance(section, dict) else None
        if isinstance(card, dict) and card.get("territory") and str(section.get("number", "")).startswith("3."):
            cards.append(card)
    return cards


def _territory(value) -> str:
    return str(value or "").strip().upper()


def _cut(value) -> str | None:
    """A cut below the territory ("plan:P1", "channel:retail", "segment:..."), compared without case or edge space.
    A missing key, None or empty text is no cut: the card or finding is about the whole territory (FR-017)."""
    text = str(value or "").strip().lower()
    return text or None


def _finding_points(finding: dict, cards: list[dict]) -> tuple[int, int, list[str]]:
    """(points, possible, notes) for one expected finding. A finding with a cut is met only by a card with the same
    territory and cut; a finding without one only by a card with no cut (core-011 FR-017)."""
    same_territory = [c for c in cards if _territory(c["territory"]) == _territory(finding["territory"])
                      and _cut(c.get("cut")) == _cut(finding.get("cut"))]
    if finding.get("withheld"):
        return (0 if same_territory else 1), 1, ([] if not same_territory else [f"{finding['id']}: should be withheld"])
    direction = finding.get("direction")
    supported, ruled_out = finding.get("drivers_supported") or [], finding.get("drivers_ruled_out") or []
    possible = 1 + len(supported) + len(ruled_out)
    where = finding["territory"] + (f" ({finding['cut']})" if _cut(finding.get("cut")) else "")
    best, notes = 0, [f"{finding['id']}: no {direction or 'any'}-direction card for {where}"]
    for card in same_territory:
        if direction is not None and card.get("direction") != direction:
            continue
        have_s, have_r = card.get("drivers_supported") or [], card.get("drivers_ruled_out") or []
        points = 1 + sum(d in have_s for d in supported) + sum(d in have_r for d in ruled_out)
        if points > best:
            best = points
            lost = [f"supported {d}" for d in supported if d not in have_s] + [f"ruled out {d}" for d in ruled_out if d not in have_r]
            notes = [f"{finding['id']}: missing {', '.join(lost)}"] if lost else []
    return best, possible, notes


def finding_counts(outputs, expectations) -> tuple[int, int, list[str]]:
    """(points, possible, notes) over the case's expected findings. A case with no findings is (0, 0, []); a case
    whose answer has no story cards scores 0 of everything possible (it is not scored in `finding_recall`, but a
    run's pooled share counts it, as a crashed case counts in the pooled key facts)."""
    findings, cards = expectations.get("findings") or [], _cards(outputs)
    got = possible = 0
    notes: list[str] = []
    for finding in findings:
        points, worth, why = _finding_points(finding, cards)
        got, possible = got + points, possible + worth
        notes += why
    return got, possible, notes


@scorer(name="finding_recall",
        description="Points for each expected finding the story cards reach (territory, cut, direction, drivers) (core-011 FR-004). Report only.")
def finding_recall(outputs, expectations) -> Feedback:
    findings = expectations.get("findings") or []
    if not findings:
        return _not_scored("the case has no expected findings")
    if not _cards(outputs):
        return _not_scored("the answer has no story cards with a territory")
    got, possible, notes = finding_counts(outputs, expectations)
    return Feedback(value=round(got / possible, 4),
                    rationale=f"{got} of {possible} points over {len(findings)} findings" + (f"; {'; '.join(notes)}" if notes else "."))


@scorer(name="false_drivers",
        description="Supported drivers on story cards, for territories the case has a finding for, that no finding lists (core-011 FR-004). Report only.")
def false_drivers(outputs, expectations) -> Feedback:
    findings, cards = expectations.get("findings") or [], _cards(outputs)
    if not findings:
        return _not_scored("the case has no expected findings")
    if not cards:
        return _not_scored("the answer has no story cards with a territory")
    expected: dict[tuple, set] = {}
    for f in findings:
        expected.setdefault((_territory(f["territory"]), _cut(f.get("cut"))), set()).update(f.get("drivers_supported") or [])
    # Only territories (and cuts) the case has a finding for: a correct story the golden answer does not mention is
    # not a wrong attribution. A cut card is held to the finding with the same cut, a whole-territory card to the one without.
    extra = [f"{card['territory']}{' (' + card['cut'] + ')' if _cut(card.get('cut')) else ''}: {d}" for card in cards
             if (_territory(card["territory"]), _cut(card.get("cut"))) in expected
             for d in card.get("drivers_supported") or []
             if d not in expected[(_territory(card["territory"]), _cut(card.get("cut")))]]
    return Feedback(value=len(extra), rationale=("Unexpected supported drivers: " + "; ".join(extra)) if extra else "No unexpected driver.")


def _trajectory(outputs) -> dict:
    return (outputs or {}).get("trajectory") or {}


def _words(text) -> int:
    return len(re.findall(r"\S+", text)) if isinstance(text, str) else 0


def count_words(sections: list[dict]) -> int:
    """Words a reader sees without unfolding anything: each section's `text` and the writer's `prose`, card headlines,
    territory-table cells, KPI tile `value` and `detail`, and chart `caption` and `explanation`. The folded `detail`
    of a section is left out."""
    total = 0
    for section in sections:
        total += _words(section.get("text")) + _words(section.get("prose"))
        total += _words((section.get("card") or {}).get("headline"))
        total += sum(_words(k.get("value")) + _words(k.get("detail")) for k in section.get("kpis") or [])
        chart = section.get("chart") or {}
        total += _words(chart.get("caption")) + _words(chart.get("explanation"))
        for row in (section.get("territory_table") or {}).get("rows") or []:
            total += sum(_words(cell) for cell in row.get("cells") or [])
    return total


def leader_words(sections: list[dict]) -> int:
    """The same count over the leader's cut of the memo (the server's own cut, `views.leadership_sections`)."""
    from pharmagentics.api.views import leadership_sections

    return count_words(leadership_sections(sections) or [])


# Word budget per view (core-011 FR-020): the largest `brief_words` among the anchor briefs that printed on two A4
# pages (brief-008 I2; the five anchors of brief-008 SC-002), rounded down to 50. MEASURED_ANCHORS holds the counts
# (analyst, leader) from the scripted engine on data day1-v1 at 2026-11-22; `test_word_budget.py` recomputes them.
MEASURED_ANCHORS: dict[str, tuple[int, int]] = {
    "P1-Q2": (622, 584), "P1-Q3": (394, 361), "P1-Q6": (498, 464), "P3-Q5": (688, 559), "P4-Q1": (836, 705)}
WORD_BUDGET: dict[str, int] = {"analyst": 800, "leader": 700}  # largest anchor 836 and 705, rounded down to 50


@scorer(name="brief_words",
        description="Words a reader sees unfolded: section text and writer prose, card headlines, table cells, KPI tiles, chart captions and explanations; not the folded detail (core-011 FR-005). The rationale also gives the leader view and the budget. Report only.")
def brief_words(outputs) -> Feedback:
    """The analyst view's count is the value; the rationale carries the leader view's count and each view's budget."""
    sections = outputs.get("sections") if isinstance(outputs, dict) else None
    if not sections:
        return _not_scored("the answer has no sections")
    total, leader = count_words(sections), leader_words(sections)
    over = [f"{view} {words} over {WORD_BUDGET[view]}" for view, words in (("analyst", total), ("leader", leader))
            if words > WORD_BUDGET[view]]
    return Feedback(value=total, rationale=f"{total} words across {len(sections)} sections, excluding detail; "
                    f"leader view {leader}; budget {WORD_BUDGET['analyst']} analyst, {WORD_BUDGET['leader']} leader"
                    + (f"; over budget: {', '.join(over)}." if over else "."))


@scorer(name="must_say_recall",
        description="Share of the case's must-say phrases the answer carries (core-011). Report only.")
def must_say_recall(outputs, expectations) -> Feedback:
    phrases = expectations.get("must_say") or []
    if not phrases:
        return _not_scored("the case has no must-say phrases")
    text = _answer(outputs)
    missing = [p for p in phrases if not any(contains_phrase(text, alt.strip()) for alt in p.split("|") if alt.strip())]
    note = f"{len(phrases) - len(missing)} of {len(phrases)} must-say phrases"
    return Feedback(value=round(1 - len(missing) / len(phrases), 4),
                    rationale=note + (f"; missing: {'; '.join(missing)}" if missing else "."))


SCOPE_FIELDS = ("territory", "week_start", "week_end", "comparison", "intent")


def _scope_value(field: str, value):
    """Comparable form of one scope field: territory IDs upper-case, dates as ISO text, comparison without its Nones."""
    if value is None:
        return None
    if field == "territory":
        return str(value).strip().upper()
    if field == "comparison":
        return {k: str(v) for k, v in dict(value).items() if v is not None} or None
    return str(value).strip()


@scorer(name="scope_match",
        description="Share of the case's expected scope fields (territory, weeks, comparison, intent) the agent's scope proposal "
                    "matches (core-011 packet F). Report only; not scored until a run records scope_proposal.")
def scope_match(outputs, expectations) -> Feedback:
    expected = expectations.get("scope") or {}
    checked = [f for f in SCOPE_FIELDS if expected.get(f) is not None]
    proposal = _trajectory(outputs).get("scope_proposal")
    if not isinstance(proposal, dict):
        return _not_scored("the run recorded no scope proposal")
    if not checked:
        return _not_scored("the case states no expected scope")
    wrong = []
    for f in checked:
        want, got = _scope_value(f, expected[f]), _scope_value(f, proposal.get(f))
        if want != got:
            wrong.append(f"{f}: expected {want}, got {got}")
    return Feedback(value=round((len(checked) - len(wrong)) / len(checked), 4),
                    rationale=f"{len(checked) - len(wrong)} of {len(checked)} scope fields match"
                              + (f"; {'; '.join(wrong)}" if wrong else "."))


REPORT_ONLY = [key_fact_recall, finding_recall, false_drivers, brief_words, must_say_recall, scope_match]


def _claims(outputs):
    outputs = outputs if isinstance(outputs, dict) else {}
    return outputs.get("claims") or [], {e["id"]: e for e in outputs.get("evidence") or []}


@scorer(name="claims_reconcile",
        description="Share of claims whose evidence query, re-run on the data, gives the claimed value (EV-1.1).")
def claims_reconcile(outputs) -> Feedback:
    claims, evidence = _claims(outputs)
    if not claims:
        return Feedback(value=0.0, rationale="The answer carries no claims.")
    bad = []
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        for c in claims:
            e = evidence.get(c["evidence_id"])
            want = parse_token(c["value"])
            if not e or not e.get("query") or want is None:
                bad.append(f"{c['value']}: no usable evidence")
                continue
            row = con.execute(e["query"]).fetchone()
            got = row[0] if row else None
            if got is None or not same(want, Number(float(got), 12, False, str(got))):
                bad.append(f"{c['value']} but the data gives {got}")
    ok = len(claims) - len(bad)
    return Feedback(value=round(ok / len(claims), 4),
                    rationale=f"{ok} of {len(claims)} claims reconcile" + (f"; failed: {'; '.join(bad[:8])}" if bad else "."))


_UNFILLED = re.compile(r"\{c\d+\}")


@scorer(name="numbers_traced",
        description="Share of numbers in the answer text that are filled claims with evidence (EV-6.1).")
def numbers_traced(outputs) -> Feedback:
    claims, _ = _claims(outputs)
    text = _answer(outputs)
    # A claim token left in the text is a number no code filled: a model wrote a token that does not exist.
    unfilled = _UNFILLED.findall(text)
    found = extract(_UNFILLED.sub(" ", text))
    total = len(found) + len(unfilled)
    if not total:
        return Feedback(value=1.0, rationale="The answer states no numbers.")
    known = [n for n in (parse_token(c["value"]) for c in claims) if n]
    loose = [n.text for n in found if not any(same(n, k) for k in known)] + unfilled
    return Feedback(value=round(1 - len(loose) / total, 4),
                    rationale=f"{total - len(loose)} of {total} numbers trace to a claim"
                              + (f"; untraced: {', '.join(loose[:8])}" if loose else "."))


@scorer(name="links_resolve",
        description="Every claim links to an evidence item pinned to the data version of the run (EV-6.2).")
def links_resolve(outputs) -> Feedback:
    claims, evidence = _claims(outputs)
    if not claims:
        return Feedback(value=0.0, rationale="The answer carries no claims.")
    pinned = data_fingerprint()
    bad = [c["value"] for c in claims
           if c["evidence_id"] not in evidence or evidence[c["evidence_id"]].get("data_version") != pinned]
    return Feedback(value=round(1 - len(bad) / len(claims), 4),
                    rationale=f"{len(claims) - len(bad)} of {len(claims)} claims link to evidence on data version {pinned}"
                              + (f"; broken: {', '.join(bad[:8])}" if bad else "."))


EVIDENCE = [claims_reconcile, numbers_traced, links_resolve]


# Trajectory: white-box and report-only, never gated. For agent systems that return `trajectory`.
@scorer(name="tool_calls", description="MCP tool calls the agents made (report only).")
def tool_calls(outputs) -> Feedback:
    tools = _trajectory(outputs).get("tools", [])
    return Feedback(value=len(tools), rationale=" > ".join(tools) or "No tool call.")


@scorer(name="llm_calls", description="Model calls across manager and specialists (report only).")
def llm_calls(outputs) -> Feedback:
    t = _trajectory(outputs)
    tokens = t.get("tokens", {})
    return Feedback(value=t.get("llm_calls", 0),
                    rationale=f"{tokens.get('input', 0)} input and {tokens.get('output', 0)} output tokens; {t.get('model', '?')}.")


@scorer(name="seconds", description="Wall time of one answer (report only).")
def seconds(outputs) -> Feedback:
    return Feedback(value=_trajectory(outputs).get("seconds", 0.0))


@scorer(name="hit_cap", description="The team hit its round cap and the brief came from the reports so far (report only).")
def hit_cap(outputs) -> Feedback:
    why = _trajectory(outputs).get("capped")
    return Feedback(value=bool(why), rationale=f"Stopped early: {why}." if why else "Finished within its caps.")


@scorer(name="needed_revision", description="The draft had digits outside claim tokens and got one revision (report only).")
def needed_revision(outputs) -> Feedback:
    t = _trajectory(outputs)
    left = t.get("digits_outside_tokens") or []
    return Feedback(value=bool(t.get("revised")), rationale=("Still outside tokens: " + ", ".join(left[:8])) if left else None)


TRAJECTORY = [tool_calls, llm_calls, seconds, hit_cap, needed_revision]


# What each check tells you (Michael, 2026-11-22): code checks are things code can produce deterministically, so
# a miss is a code defect; agent checks measure the agent's own inference and are where agent work aims; safety
# checks guard wording; ops are run counters. A new scorer must be added here (a test enforces it).
KIND: dict[str, str] = {
    "golden_number_recall": "code", "numbers_match_golden": "code", "key_fact_recall": "code",
    "claims_reconcile": "code", "numbers_traced": "code", "links_resolve": "code", "sections_exist": "code",
    "finding_recall": "agent", "false_drivers": "agent", "must_say_recall": "agent", "needed_revision": "agent",
    "brief_words": "agent", "scope_match": "agent", "judge_factual_correctness": "agent",
    "must_not_say": "safety", "governed_terms": "safety", "no_individual_rep": "safety",
    "tool_calls": "ops", "llm_calls": "ops", "seconds": "ops", "hit_cap": "ops",
}


# How a score is read: "share" (0 to 1, shown as a percent; the default), "count" (a whole number), "flag" (0 or 1, yes/no).
UNIT: dict[str, str] = {
    "false_drivers": "count", "brief_words": "count", "tool_calls": "count", "llm_calls": "count", "seconds": "count",
    "needed_revision": "flag", "hit_cap": "flag",
}


def unit_of(name: str) -> str:
    return UNIT.get(name, "share")


def kind_of(name: str) -> str:
    """The kind of a scorer by name; any judge or RAGAS score is an agent check, an unknown name is too."""
    return KIND.get(name, "agent")


def judge_scorers(model: str) -> list:
    """RAGAS judges on `model` (e.g. ollama:/gemma3:4b). The judge sees only the question, the answer
    text and the golden answer: MLflow would otherwise join every expectation into RAGAS's reference."""
    from mlflow.genai.scorers.ragas import FactualCorrectness

    factual = FactualCorrectness(model=model)

    @scorer(name="judge_factual_correctness",
            description=f"RAGAS FactualCorrectness against the golden answer (EV-1.3), judged by {model}.")
    def judge_factual_correctness(inputs, outputs, expectations) -> Feedback:
        fb = factual(inputs=inputs, outputs=_answer(outputs),
                     expectations={"expected_response": expectations["expected_response"]})
        if fb.error:
            return Feedback(error=fb.error)
        return Feedback(value=fb.value, rationale=fb.rationale)

    return [judge_factual_correctness]
