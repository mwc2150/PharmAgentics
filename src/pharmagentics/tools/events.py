"""The run event log (brief-009 FR-001 to FR-003, FR-007, FR-008).

One ordered list of events per run: who did what, with which tool, with what verdict, and which claims the
step produced. Both engines write it; the timeline in the UI and the leader's one-line process summary read it.
Recording is read-only: it never touches the answer, the claims or the evidence (FR-008).

Rules that keep it safe:
- Summaries are written by code from tool results. A claim token in a summary is filled from the run's claims
  (code values), never from model text. No event holds a model's prose.
- No event names a person: the Person actor is "the analyst", nothing more (FR-007).
- `claims` lists the claims a step produced, as indexes into the finished brief's `claims`. While a run is in
  progress it is empty; `finalize` fills it once the brief's claim list is known.
"""
from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from typing import Any, Callable

ACTORS = ("Manager", "Data Forensics", "Driver Investigator", "Writer", "Code", "Person")
KINDS = ("agent", "llm", "code", "person")
VERDICTS = ("supported", "ruled out", "inconclusive", "abstained", "done")
FIELDS = ("seq", "t", "actor", "kind", "step", "story", "tool", "args", "verdict", "summary", "claims", "prompt")
TOKEN = re.compile(r"\{c(\d+)\}")
MAX_EVENTS = 600           # a run holds far fewer; this bounds what a worker may post
MAX_TEXT = 300
_UNSET: Any = object()

# The actor behind each agent name the framework uses.
ACTOR_OF = {"data_forensics": "Data Forensics", "driver_investigator": "Driver Investigator", "manager": "Manager",
            "manager_triage": "Manager", "writer": "Writer", "reviser": "Writer"}
# Which step each MCP tool is.
TOOL_STEP = {"feed_health": "Check the data", "restatements": "Check the data", "national_kpis": "Read the national figures",
             "check_data": "Check the data", "screen_territories": "Screen territories", "territory_change": "Measure the change",
             "check_access": "Test a driver", "check_promotion": "Test a driver", "check_supply": "Test a driver",
             "check_competitor": "Test a driver", "competitor_status": "Check the competitor", "split_change": "Split the change",
             "story_confidence": "Close the story"}
_LABEL = re.compile(r"\b(?:Access|Promotion|Supply|Competitor launch|Data artifact): "
                    r"(supported|ruled out|inconclusive|insufficient|not ruled out|cannot be separated|not testable|not credited)")
_VERDICT = {"supported": "supported", "ruled out": "ruled out", "inconclusive": "inconclusive",
            "insufficient": "inconclusive", "not ruled out": "inconclusive", "cannot be separated": "inconclusive",
            "not testable": "inconclusive", "not credited": "inconclusive"}
_LINE = re.compile(r"^(?:Access|Promotion|Supply|Competitor launch|Data artifact):")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def tokens(text: str) -> list[int]:
    return [int(m.group(1)) for m in TOKEN.finditer(text or "")]


def tidy(text: str, limit: int = MAX_TEXT) -> str:
    one = " ".join((text or "").split())
    return one if len(one) <= limit else one[:limit - 1].rstrip() + "…"


def verdict_of(tool: str, text: str) -> str | None:
    """The verdict code computed for a tool result, read from the result's own words; None when it has none."""
    if tool == "story_confidence":
        return "done"
    if text.startswith("Already tested"):
        return None
    if "fail the feed gate in these weeks, so no like-for-like test" in text:
        return "abstained"
    m = _LABEL.search(text or "")
    return _VERDICT[m.group(1)] if m else None


def summary_line(tool: str, text: str) -> str:
    """The sentence a tool result is shown as: the check's own line, or the first line, with tokens still in."""
    if text.startswith("Already tested"):
        return "Refused: this check already ran in this run."
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    pick = next((x for x in lines if _LINE.match(x)), None)
    if pick is None and tool == "story_confidence":
        pick = lines[0] if lines else ""
    return pick or (lines[0] if lines else "")


class EventLog:
    """Ordered events of one run. Thread-safe; `on_event` sees each event as it is recorded (the worker posts it)."""

    def __init__(self, on_event: Callable[[dict], None] | None = None, seed: list[dict] | None = None):
        self._lock = threading.Lock()
        self.events: list[dict] = []
        self._raw: dict[int, list[int]] = {}   # seq -> registry token numbers this step produced (first mention)
        self._seen: set[int] = set()
        self.on_event = on_event
        self.story: str | None = None
        self.prompts: dict[str, str] = {}      # logical prompt name -> "file@hash"
        self.claims: list[dict] = []           # the run's claims so far, for filling tokens in summaries
        self.fetch: Callable[[], Any] | None = None  # async: returns the run's claims (agent engine)
        self.done_marker = ""
        self.defer = False                     # True while a timed section runs: summaries are filled after it, by `resolve`
        self._pending: dict[int, str] = {}     # seq -> raw summary (tokens still in) of an event emitted while `defer` was on
        for e in seed or []:
            self.events.append(dict(e, claims=[]))

    # recording -----------------------------------------------------------------------------------
    @property
    def next_seq(self) -> int:
        return (self.events[-1]["seq"] + 1) if self.events else 1

    def emit(self, actor: str, kind: str, step: str, *, story: Any = _UNSET, tool: str | None = None, args: dict | None = None,
             verdict: str | None = None, summary: str = "", text: str = "", prompt: str | None = None) -> dict:
        """Record one event. `text` is the tool or section text the step produced: its claim tokens are the claims
        this step produced (a token already mentioned by an earlier step belongs to that step)."""
        assert actor in ACTORS and kind in KINDS, (actor, kind)
        with self._lock:
            seq = self.next_seq
            fresh = [n for n in dict.fromkeys(tokens(text)) if n not in self._seen]
            self._seen.update(fresh)
            self._raw[seq] = fresh
            event = {"seq": seq, "t": now(), "actor": actor, "kind": kind, "step": step,
                     "story": self.story if story is _UNSET else story, "tool": tool,
                     "args": dict(args) if args else None, "verdict": verdict, "summary": tidy(self.fill(summary)),
                     "claims": [], "prompt": prompt}
            self.events.append(event)
            if self.defer and tokens(summary):
                self._pending[seq] = summary
        if self.on_event:
            try:
                self.on_event(dict(event))
            except Exception:  # noqa: BLE001 - reporting progress must never break the run
                pass
        return event

    def replay(self) -> None:
        """Hand the seeded events (from the triage job) to `on_event`, so a live timeline starts at step one."""
        for e in list(self.events):
            if self.on_event:
                try:
                    self.on_event(dict(e))
                except Exception:  # noqa: BLE001
                    pass

    def fill(self, text: str) -> str:
        """Claim tokens in `text` as the run's own values; a token whose value is not known yet reads "a figure"."""
        def value(m: re.Match) -> str:
            n = int(m.group(1))
            return self.claims[n - 1]["value"] if 0 < n <= len(self.claims) else "a figure"
        return TOKEN.sub(value, text or "")

    async def refresh(self, text: str) -> None:
        """Make sure the claims named in `text` are known (agent engine: asks the run for them). Never raises."""
        if self.fetch is None or not tokens(text) or max(tokens(text)) <= len(self.claims):
            return
        try:
            got = await self.fetch()
            if got and len(got) >= len(self.claims):
                self.claims = got
        except Exception:  # noqa: BLE001 - an unfilled token reads "a figure"; the run goes on
            pass

    async def resolve(self) -> None:
        """Fill the summaries of events recorded while `defer` was on, from the run's claims (one fetch, outside the
        timed section). Until then a summary shows the values known when it was recorded, else "a figure". Never raises."""
        with self._lock:
            waiting = dict(self._pending)
        if not waiting:
            return
        try:
            got = await self.fetch() if self.fetch is not None else None
            if got and len(got) >= len(self.claims):
                self.claims = got
        except Exception:  # noqa: BLE001
            pass
        with self._lock:
            for e in self.events:
                raw = waiting.get(e["seq"])
                if raw is not None:
                    e["summary"] = tidy(self.fill(raw))
                    self._pending.pop(e["seq"], None)

    def public(self) -> list[dict]:
        with self._lock:
            return [dict(e) for e in self.events]

    # finishing -----------------------------------------------------------------------------------
    def finalize(self, n_claims: int, index: dict[int, int] | None = None) -> tuple[list[dict], list[int | None]]:
        """The events with `claims` as indexes into the finished brief's claims, and, for each brief claim, the seq
        of the event that produced it (None when no step did). `index` maps a token number to its place in the
        brief's claim list; None means token n is claim n-1 (the scripted brief keeps every claim)."""
        with self._lock:
            done: list[dict] = []
            owner: list[int | None] = [None] * n_claims
            for e in self.events:
                mine = []
                for n in self._raw.get(e["seq"], []):
                    i = (n - 1) if index is None else index.get(n)
                    if i is not None and 0 <= i < n_claims and owner[i] is None:
                        owner[i] = e["seq"]
                        mine.append(i)
                done.append(dict(e, claims=sorted(mine)))
            return done, owner


# the server's side: what a worker may post --------------------------------------------------------------
def clean(events: Any) -> list[dict]:
    """Allow-list of a posted event list: known fields only, known actors and kinds, bounded text. Anything else is
    dropped, so a worker cannot put free-form data into a brief."""
    out: list[dict] = []
    for e in events if isinstance(events, list) else []:
        if not isinstance(e, dict) or e.get("actor") not in ACTORS or e.get("kind") not in KINDS or not isinstance(e.get("seq"), int):
            continue
        item = {k: e.get(k) for k in FIELDS}
        for k in ("t", "step", "story", "tool", "summary", "prompt"):
            item[k] = tidy(str(item[k]), 200) if item[k] is not None else None
        item["step"] = item["step"] or ""
        item["summary"] = item["summary"] or ""
        item["verdict"] = item["verdict"] if item["verdict"] in VERDICTS else None
        args = item["args"]
        item["args"] = {str(k)[:40]: tidy(str(v), 80) for k, v in list(args.items())[:6]} if isinstance(args, dict) and args else None
        item["claims"] = [c for c in (item["claims"] or []) if isinstance(c, int) and c >= 0][:50]
        out.append(item)
        if len(out) >= MAX_EVENTS:
            break
    return out


def clean_claim_events(owner: Any, n_claims: int) -> list[int | None] | None:
    if not isinstance(owner, list) or len(owner) != n_claims:
        return None
    return [x if isinstance(x, int) and not isinstance(x, bool) else None for x in owner]
