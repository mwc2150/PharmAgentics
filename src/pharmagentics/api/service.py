"""Adapter from a validated browser request to the existing scripted Briefing engine.

No SQL is accepted from callers. No evaluation data is imported. This is an MVP
backend seam; neither human approval nor saved history is implemented here.
"""
from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

from .schemas import BriefingQuery, BriefingResult, ReleaseContext
from pharmagentics.tools import events
from pharmagentics.tools.brands import BRIEFING_ENGINES, PRODUCTS
from pharmagentics.tools import definition as definitions
from pharmagentics.tools.definition import Definition
from pharmagentics.tools.window import Comparison, comparison_weeks

ROOT = Path(__file__).resolve().parents[3]
BRIEFING_DIR = ROOT / "agents" / "brand-briefing"
DB = ROOT / "local" / "pharmagentics.duckdb"
TERRITORIES = {
    "GREAT_LAKES": "Great Lakes", "MID_ATLANTIC": "Mid-Atlantic",
    "MOUNTAIN": "Mountain", "NEW_ENGLAND": "New England",
    "NORTHWEST": "Northwest", "PACIFIC": "Pacific",
    "SOUTHEAST": "Southeast", "SOUTH_CENTRAL": "South Central",
    "NATIONAL": "National",
}


class MissingDatabase(RuntimeError):
    pass


class OutsideRelease(ValueError):
    pass


def release_context() -> ReleaseContext:
    """Read available Monday weeks from the actual data release (not wall-clock time)."""
    if not DB.is_file():
        raise MissingDatabase("DuckDB has not been built. Run the data loader first.")
    from pharmagentics.tools import Registry

    reg = Registry(DB)
    try:
        week_rows = reg.rows(
            "SELECT DISTINCT week_start::varchar FROM raw.calendar ORDER BY 1"
        )
        territory_rows = reg.rows(
            "SELECT DISTINCT territory_id FROM raw.dim_territory ORDER BY 1"
        )
        product_rows = reg.rows(
            "SELECT DISTINCT product_id FROM raw.dim_product ORDER BY 1"
        )
    finally:
        reg.close()
    if not week_rows:
        raise MissingDatabase("DuckDB calendar is empty. Reload the synthetic release.")
    weeks = [date.fromisoformat(row[0]) for row in week_rows]
    # Only expose real, supported territories; don't imply district/plan-level UI.
    available_territories = [row[0] for row in territory_rows if row[0] in TERRITORIES and row[0] != "NATIONAL"]
    if not available_territories:
        raise MissingDatabase("No supported territories found in the data release.")
    # Release membership and engine support are distinct from the caller's grants.
    supported_products = [row[0] for row in product_rows if row[0] in BRIEFING_ENGINES]
    if not supported_products:
        raise MissingDatabase("The scripted Briefing brand is missing from the synthetic release.")
    return ReleaseContext(
        first_week=weeks[0], latest_week=weeks[-1],
        territory_ids=available_territories,
        available_weeks=weeks, product_ids=supported_products,
        brands=[{"id": b, "name": PRODUCTS[b], "engines": list(BRIEFING_ENGINES[b])} for b in supported_products],
    )


def current_data_version() -> str:
    """The pinned version of the loaded release; approved briefs from another version are not served."""
    if not DB.is_file():
        raise MissingDatabase("DuckDB has not been built. Run the data loader first.")
    from pharmagentics.tools import Registry

    reg = Registry(DB)
    try:
        return reg.data_version
    finally:
        reg.close()


def normalize_question(request: BriefingQuery) -> str:
    """Place *both* the ISO date and territory before ':' for window.parse().

    The existing parser only inspects text before the first colon. The UI does
    not rely on the LLM or the free-text question to choose its data scope.
    """
    label = TERRITORIES[request.territory_id]
    if request.intent == "promotion_review":
        return f"Promotion review in {label}: {request.question.strip()}"
    if request.week_end is not None and request.week_end > request.week_start:
        # window.parse reads "Weeks of A to B" as every Monday from A to B (brief-008 FR-007)
        return f"Weeks of {request.week_start.isoformat()} to {request.week_end.isoformat()} in {label}: {request.question.strip()}"
    return f"Week of {request.week_start.isoformat()} in {label}: {request.question.strip()}"


def period_weeks(request: BriefingQuery) -> list[str]:
    """The reporting weeks of the request, first to last, as ISO dates (one week unless week_end is later)."""
    last = request.week_end or request.week_start
    return [(request.week_start + timedelta(weeks=i)).isoformat() for i in range((last - request.week_start).days // 7 + 1)]


class StalePlan(ValueError):
    """The triage decision names a plan that code no longer builds (brief-002; HTTP 409)."""


class BadDecision(ValueError):
    """The triage decision names a story the plan does not propose (brief-002 FR-023; HTTP 400)."""


def launch_week() -> str | None:
    """The competitor's launch week, read from the release (the pre-launch comparison and its words need it)."""
    from pharmagentics.tools import Registry
    from pharmagentics.tools.checks import launch_date

    reg = Registry(DB)
    try:
        return launch_date(reg)
    finally:
        reg.close()


def definition_words(definition: Definition) -> list[str]:
    needs = any(c.kind == "pre_launch" for c in definition.comparison)
    return definitions.words(definition, launch_week() if needs else None)


def effective_definition(request: BriefingQuery) -> Definition:
    """The definition a request is built from, complete: the brief's weeks and comparison filled in (the Promotion review
    is release-wide, so it takes neither) and every other field as chosen or pre-selected."""
    d = Definition.coerce(request.definition, request.comparison)
    if request.intent == "promotion_review":
        return d
    return d.model_copy(update={"first_week": request.week_start.isoformat(),
                                "last_week": (request.week_end or request.week_start).isoformat()})


def engine_options(request: BriefingQuery) -> dict:
    """The keywords the scripted engine is called with: the definition when the request carries one, else the old
    `comparison` keyword (or nothing), so a request without a definition is the call it always was."""
    if request.definition is not None:
        return {"definition": effective_definition(request)}
    return {"comparison": request.comparison} if request.comparison is not None else {}


def effective_comparison(request: BriefingQuery) -> Comparison | None:
    return effective_definition(request).primary_comparison


def _check_scope(request: BriefingQuery) -> None:
    bounds = release_context()
    if request.brand_id not in bounds.product_ids:
        raise OutsideRelease("Brand not present in the supported synthetic data release.")
    if request.week_start not in bounds.available_weeks or (request.week_end or request.week_start) not in bounds.available_weeks:
        raise OutsideRelease(
            f"Requested week is outside the synthetic data release "
            f"({bounds.first_week.isoformat()} to {bounds.latest_week.isoformat()})."
        )
    if request.territory_id not in bounds.territory_ids:
        raise OutsideRelease("Territory not present in the supported synthetic data release.")
    if request.intent == "promotion_review" and request.brand_id != "BXA":
        raise OutsideRelease("The release-wide Promotion review is available for BXA.")
    if (chosen := effective_definition(request).comparison):
        if request.intent == "promotion_review":
            raise OutsideRelease("The release-wide Promotion review uses its own lapse comparison.")
        try:
            for each in chosen:  # every comparison, the primary and the extras
                comparison_weeks(each, period_weeks(request), {week.isoformat() for week in bounds.available_weeks},
                                 launch=launch_week() if each.kind == "pre_launch" else None)
        except ValueError as exc:
            raise OutsideRelease(str(exc)) from exc
    # Import the existing lane directly, exactly as eval/harness/systems.py does.
    # Do not import eval/ from runtime code or reconstruct KPI logic here.
    path = str(BRIEFING_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)


def _traceable(claims: list, evidence: list) -> str | None:
    evidence_by_id = {e["id"]: e for e in evidence}
    if any(c["evidence_id"] not in evidence_by_id for c in claims):
        raise RuntimeError("The briefing returned an untraceable claim.")
    versions = {e.get("data_version") for e in evidence if e.get("data_version")}
    if len(versions) > 1:
        raise RuntimeError("The briefing returned evidence from multiple data versions.")
    return next(iter(versions), None)


def _matching_brand(expected: str, result: dict) -> None:
    # Existing BXA workers predate the explicit brand field; BXC must always name it.
    if result.get("brand_id", "BXA") != expected:
        raise RuntimeError("The engine returned a different brand from the request.")


def _matching_definition(expected: Definition, result: dict) -> None:
    """The engine must have built the brief from the definition asked for: the selectors that change the figures."""
    raw = result.get("definition")
    if raw is None:
        return
    got = Definition.model_validate(raw)
    fields = ("territories", "measure", "grain", "relative_to")
    if any(getattr(got, f) != getattr(expected, f) for f in fields) or got.extra_comparisons != expected.extra_comparisons:
        raise RuntimeError("The worker returned a different brief definition from the request.")


def _matching_comparison(expected: Comparison | None, result: dict) -> None:
    raw = result.get("comparison")
    actual = Comparison.model_validate(raw) if raw is not None else None
    if actual != expected:
        raise RuntimeError("The worker returned a different comparison window from the request.")


def run_triage(request: BriefingQuery) -> dict:
    """Stages 1 to 3 and the code triage plan for P1 (brief-002 US8)."""
    _check_scope(request)
    from briefing_baseline.pipeline import triage

    options = engine_options(request)
    plan = triage(normalize_question(request), db=DB, brand_id=request.brand_id, **options)
    _matching_brand(request.brand_id, plan)
    _traceable(plan["claims"], plan["evidence"])
    plan.update(brand_id=request.brand_id, territory_id=request.territory_id, week_start=request.week_start.isoformat())
    if request.week_end is not None:
        plan["week_end"] = request.week_end.isoformat()
    return plan


def run_briefing(request: BriefingQuery) -> BriefingResult:
    _check_scope(request)
    question = normalize_question(request)
    definition = effective_definition(request)
    options = engine_options(request)
    extra = {}
    log = events.EventLog()  # brief-009: the scripted run's steps, actor Code; recording changes nothing in the brief
    if request.triage is None:
        from briefing_baseline.pipeline import answer

        raw = answer(question, db=DB, brand_id=request.brand_id, events=log, **options)
    else:
        from briefing_baseline import pipeline

        try:
            out = pipeline.run_with_plan(question, request.triage.model_dump(), db=DB, brand_id=request.brand_id, events=log, **options)
        except pipeline.StalePlan as exc:
            raise StalePlan(str(exc)) from exc
        except ValueError as exc:
            raise BadDecision(str(exc)) from exc
        raw, extra = out["envelope"], {"triage": out["triage"], "flow": out["flow"]}

    _matching_brand(request.brand_id, raw)
    claims = raw.get("claims", [])
    evidence = raw.get("evidence", [])
    if log.events:
        extra["events"], extra["claim_events"] = log.finalize(len(claims))
    return BriefingResult(
        system=raw["system"], question=question,
        brand_id=request.brand_id, territory_id=request.territory_id,
        week_start=request.week_start, week_end=request.week_end, comparison=definition.primary_comparison,
        definition=definition, definition_words=definition_words(definition),
        answer=raw["answer"], claims=claims, evidence=evidence,
        data_version=_traceable(claims, evidence),
        abstained=bool(raw.get("abstained", False)), citations=raw.get("citations"), sections=raw.get("sections"), **extra,
    )


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUMBER = re.compile(r"(?<![\w.-])-?\d[\d,.]*%?")


def untraced_numbers(answer: str, claims: list[dict], data_version: str | None) -> list[str]:
    """Numbers in a brief's text that are not one of its claim values (core-007 FR-027). Dates, the data
    version and identifiers with letters (plan IDs) are not numbers."""
    text = _DATE.sub(" ", answer.replace(data_version, " ") if data_version else answer)
    values = {c["value"] for c in claims}
    return [n for n in (m.group(0).rstrip(".,") for m in _NUMBER.finditer(text)) if n and n not in values]


def accept_agent_brief(query: BriefingQuery, posted: dict) -> BriefingResult:
    """A brief posted by the worker, admitted only if it is traceable on this app's data version (FR-027)."""
    from .brand_access import require_engine

    require_engine(query.brand_id, "agent")
    env = posted.get("envelope") or {}
    _matching_brand(query.brand_id, env)
    definition = effective_definition(query)
    _matching_comparison(definition.primary_comparison, env)
    _matching_definition(definition, env)
    claims, evidence = env.get("claims") or [], env.get("evidence") or []
    version = _traceable(claims, evidence)
    if version != current_data_version():
        raise RuntimeError(f"The agent ran on data version {version}, not this app's {current_data_version()}. "
                           "If the data files only differ in line endings (a Windows checkout), see TEAM.md, "
                           "\"Data version mismatch\".")
    if (bad := untraced_numbers(env.get("answer", ""), claims, version)):
        raise RuntimeError(f"Numbers with no claim behind them: {', '.join(bad[:5])}.")
    return BriefingResult(
        engine="agent", system=str(env.get("system", "briefing_agent")), question=normalize_question(query),
        brand_id=query.brand_id, territory_id=query.territory_id, week_start=query.week_start, week_end=query.week_end,
        comparison=definition.primary_comparison, definition=definition, definition_words=definition_words(definition),
        answer=env.get("answer", ""), claims=claims, evidence=evidence, data_version=version,
        abstained=bool(env.get("abstained", False)), triage=posted.get("triage"), flow=posted.get("flow"),
        sections=env.get("sections"), events=events.clean(posted.get("events")) or None,
        claim_events=events.clean_claim_events(posted.get("claim_events"), len(claims)),
        citations=_valid_citations(env.get("answer", ""), claims, env.get("citations")),
    )


def _valid_citations(answer: str, claims: list[dict], spans) -> list[dict] | None:
    """Keep a posted citation only if it points at its claim's value in the text."""
    ok = [s for s in spans or [] if isinstance(s, dict) and 0 <= s.get("claim", -1) < len(claims)
          and answer[s.get("start", 0):s.get("end", 0)] == claims[s["claim"]]["value"]]
    return ok or None


# ---- Reading a typed question into a proposed scope (brief-008 FR-008, constitution B-II v1.1.0) ---------------
# A model may propose the weeks, territory, comparison length and promotion flag. Code validates every field
# against the release; any failure, and every run without a configured Anthropic model, falls back to the code
# parser (tools/window.parse). Nothing runs on a proposal: the analyst confirms the form, then builds as usual.

DEFAULT_COMPARISON_WEEKS = 4
SCOPE_SECONDS = 25.0
AGENTS_DIR = ROOT / "agents" / "brand-briefing"


def scope_model() -> str | None:
    """The Anthropic model that may propose a scope, or None: PHARMAGENTICS_AGENT_MODEL must be an anthropic: model
    and ANTHROPIC_API_KEY must be set. Evals never reach this (they do not call the route)."""
    import os

    from pharmagentics.llm import load_env

    load_env()
    spec = os.environ.get("PHARMAGENTICS_AGENT_MODEL", "").strip()
    return spec if spec.startswith("anthropic:") and spec.partition(":")[2] and os.environ.get("ANTHROPIC_API_KEY") else None


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def calendar_to_weeks(start: str, end: str) -> list[str]:
    """Calendar dates to Monday weeks: a span under a week is the week holding it; a longer span is every week
    whose Monday falls inside it. Raises ValueError for anything that is not an ordered pair of dates."""
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    if b < a:
        raise ValueError("The last week comes before the first week.")
    if (b - a).days < 7:
        return [_monday(a).isoformat()]
    a, b = a + timedelta(days=(7 - a.weekday()) % 7), _monday(b)
    return [(a + timedelta(weeks=i)).isoformat() for i in range((b - a).days // 7 + 1)] if a <= b else []


def _clamp_weeks(count: int, first: str, available: set[str]) -> int:
    """The longest comparison up to `count` weeks that lies inside the release before `first`; 0 when none fits."""
    day = date.fromisoformat(first)
    fit = 0
    while fit < count and (day - timedelta(weeks=fit + 1)).isoformat() in available:
        fit += 1
    return fit


def validate_scope(proposal: dict, release: ReleaseContext, brand_id: str) -> dict:
    """Check a model's proposal against the release and return the form values. Raises ValueError on anything
    unusable: dates that are not dates, weeks outside the release, an unknown territory, a comparison that is not a
    whole number from 1 to 13, a promotion flag that is not a boolean.
    A comparison that reaches before the release is shortened with a note (None when no earlier week exists)."""
    available = {w.isoformat() for w in release.available_weeks}
    weeks = calendar_to_weeks(str(proposal.get("period_start", "")), str(proposal.get("period_end", "")))
    if not weeks or any(w not in available for w in weeks):
        raise ValueError("The proposed weeks are outside the release.")
    territory = str(proposal.get("territory") or "").strip().upper().replace(" ", "_").replace("-", "_")
    if territory in ("", "NATIONAL"):
        territory = ""
    elif territory not in release.territory_ids:
        raise ValueError("The proposed territory is not in the release.")
    count = proposal.get("comparison_weeks", DEFAULT_COMPARISON_WEEKS)
    if count is None:
        count = DEFAULT_COMPARISON_WEEKS
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 13:
        raise ValueError("The comparison must be a whole number of weeks from 1 to 13.")
    notes: list[str] = []
    fit = _clamp_weeks(count, weeks[0], available)
    if fit < count:  # a reading that is otherwise valid is kept; its comparison is shortened, not refused
        notes.append(_shortened_note(fit, weeks[0]))
    count = fit or None
    promotion = proposal.get("promotion_review", False)
    if not isinstance(promotion, bool) or (promotion and brand_id != "BXA"):
        raise ValueError("The proposed promotion flag is not usable.")
    return {"week_start": weeks[0], "week_end": weeks[-1], "territory_id": territory or None,
            "comparison_weeks": count, "promotion_review": promotion, "notes": notes,
            "definition": proposed_definition(weeks[0], weeks[-1], count, promotion, proposal, notes)}


_NBRX = re.compile(r"\b(new patients?|new-to-brand|nbrx)\b", re.I)
_PRE_LAUNCH = re.compile(r"\b(before (?:metacora|the competitor|competitor|the launch|launch)\b|pre-?launch)", re.I)
_TRX = re.compile(r"\b(trx|total prescriptions?|total scripts?)\b", re.I)


def _question_words(question: str) -> dict:
    """What the question's own words name (rules; no model): new patients or NBRx (with or without TRx), and a comparison
    with the weeks before Metacora launched."""
    out: dict = {}
    if _NBRX.search(question):
        out["measure"] = ["trx", "nbrx"] if _TRX.search(question) else ["nbrx"]
    if _PRE_LAUNCH.search(question):
        out["comparison"] = "pre_launch"
    return out


def proposed_definition(first: str, last: str, comparison_weeks: int | None, promotion: bool, words: dict, notes: list[str]) -> dict | None:
    """The brief definition the form is filled with: the period and comparison the reader found, and any measure,
    territories, levels or relative_to the question's words or the model proposed. An unusable proposed value is left at
    its pre-selected value with a note, never an error. None for the release-wide Promotion review."""
    if promotion:
        return None
    fields: dict = {"first_week": first, "last_week": last}
    if comparison_weeks:
        fields["comparison"] = [{"kind": "previous", "weeks": comparison_weeks}]
    if words.get("comparison") == "pre_launch":  # only for a period that starts on or after the competitor launch
        launch = launch_week()
        if launch is not None and first >= launch:
            fields["comparison"] = [{"kind": "pre_launch"}]
        else:
            notes.append("The pre-launch comparison needs a period that starts on or after the competitor launch, so the form keeps the previous weeks.")
    for name, allowed in (("measure", definitions.MEASURES), ("territories", definitions.TERRITORIES), ("relative_to", definitions.RELATIVE)):
        value = words.get(name)
        if value is None:
            continue
        values = ["trx", "nbrx"] if value == "both" else value if isinstance(value, list) else [value]
        if values and len(set(values)) == len(values) and all(v in allowed for v in values):
            fields[name] = values
        else:
            notes.append(f"The proposed {name.replace('_', ' ')} is not one the form offers, so it keeps its pre-selected value.")
    grain = words.get("grain")
    if grain is not None:
        if isinstance(grain, list) and grain and all(g in definitions.GRAINS for g in grain):
            fields["grain"] = grain
        else:
            notes.append("The proposed levels are not usable, so the form keeps its pre-selected levels.")
    return Definition.model_validate(fields).to_json()


def _shortened_note(fit: int, first: str) -> str:
    if fit == 0:
        return f"There are no earlier weeks in the release before {first}, so the brief uses the default comparison."
    return f"Only {fit} earlier week{' exists' if fit == 1 else 's exist'} before {first}, so the comparison is shortened."


def rules_scope(question: str, release: ReleaseContext, brand_id: str) -> dict:
    """The code parser's reading of the question (tools/window.parse): the whole text is read, colons included."""
    from pharmagentics.tools.window import parse

    first, latest = release.first_week.isoformat(), release.latest_week.isoformat()
    got = parse(question.replace(":", " ,"), first, latest, briefing=True)
    notes = [got["note"]] if got["note"] else []
    promotion = bool(got["promotion"]) and brand_id == "BXA"
    weeks = got["weeks"]
    if not weeks or (promotion and not got["explicit_week"]):
        weeks = [latest]
        if got["requested"] and not got["weeks"]:
            notes.append(f"The weeks in the question are outside the release, so this uses the latest closed week, {latest}.")
    available = {w.isoformat() for w in release.available_weeks}
    count = _clamp_weeks(DEFAULT_COMPARISON_WEEKS, weeks[0], available)
    if count < DEFAULT_COMPARISON_WEEKS:
        notes.append(_shortened_note(count, weeks[0]))
    else:
        notes.append(f"The comparison is the previous {count} weeks unless you change it.")
    if not got["territory"]:
        notes.append("No territory was named, so the form keeps the territory you chose.")
    if got["promotion"] and not promotion:
        notes.append("The Promotion review is available for BXA only.")
    words = _question_words(question)
    return {"week_start": weeks[0], "week_end": weeks[-1], "territory_id": got["territory"],
            "comparison_weeks": count or None, "promotion_review": promotion, "notes": notes,
            "definition": proposed_definition(weeks[0], weeks[-1], count or None, promotion, words, notes)}


def _ask_model(spec: str, question: str, release: ReleaseContext, brand_id: str) -> dict:
    """One tool call to the model, through briefing_agent.reader. Returns its raw proposal (unchecked)."""
    if str(AGENTS_DIR) not in sys.path:
        sys.path.insert(0, str(AGENTS_DIR))
    from briefing_agent.reader import propose

    return propose(question, spec=spec, first=release.first_week.isoformat(), latest=release.latest_week.isoformat(),
                   territories=list(release.territory_ids), brand_id=brand_id, seconds=SCOPE_SECONDS)


def read_briefing_scope(question: str, brand_id: str) -> dict:
    """The proposed scope for a typed question: the model's when one is configured and its proposal passes every
    check, else the code parser's. The reply names who read it."""
    release = release_context()
    if brand_id not in release.product_ids:
        raise OutsideRelease("Brand not present in the supported synthetic data release.")
    question = " ".join(question.split())
    spec = scope_model()
    if spec:
        try:
            checked = validate_scope(_ask_model(spec, question, release, brand_id), release, brand_id)
        except Exception:  # noqa: BLE001 - no usable reading from the model: the rules read it
            checked = None
        if checked:
            span = checked["week_start"] if checked["week_start"] == checked["week_end"] else f"{checked['week_start']} to {checked['week_end']}"
            return {"question": question, **checked, "read_by": "model", "model": spec.partition(":")[2],
                    "notes": [f"Read by the model as {span}; code checked every field.", *checked["notes"]]}
    return {"question": question, **rules_scope(question, release, brand_id), "read_by": "rules", "model": None}
