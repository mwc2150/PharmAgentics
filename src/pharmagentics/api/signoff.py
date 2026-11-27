"""Two-step sign-off of a brief (brief-005): the review states, who may move a brief and who may see it.

P1 reviews and sends a brief for sign-off; P2 signs it off or returns it with a comment (and flags on single claims);
only a signed-off brief reaches P3 and P4. This module is the whole rule set, as data and pure functions, so the
routes, the lists and the state-machine test all read the same table. A brief stored before sign-off existed keeps
its three-valued `review_status` (pending, approved, rejected) and is read through LEGACY: an approved brief counts
as signed off, so a Director's list never empties. Stored records are never rewritten to say so.
"""
from __future__ import annotations

from fastapi import HTTPException

DRAFT, SENT, SIGNED_OFF, RETURNED, REJECTED = "draft", "sent", "signed_off", "returned", "rejected"
STATES = (DRAFT, SENT, SIGNED_OFF, RETURNED, REJECTED)
LEGACY = {"pending": DRAFT, "approved": SIGNED_OFF, "rejected": REJECTED}
# What an older release of the app reads from a record written by this one (rollback safety): only a signed-off
# brief looks approved, so nothing becomes visible to leaders by a rollback.
MIRROR = {DRAFT: "pending", SENT: "pending", RETURNED: "pending", SIGNED_OFF: "approved", REJECTED: "rejected"}

# action -> (the role action it needs, the states it may start from, the state it ends in)
TRANSITIONS: dict[str, tuple[str, frozenset[str], str]] = {
    "send": ("review", frozenset({DRAFT, RETURNED, REJECTED}), SENT),
    "reject": ("review", frozenset({DRAFT, SENT, RETURNED}), REJECTED),
    "sign_off": ("signoff", frozenset({SENT}), SIGNED_OFF),
    "return": ("signoff", frozenset({SENT}), RETURNED),
}
DONE = {"send": "sent", "reject": "rejected", "sign_off": "signed_off", "return": "returned"}  # the trail's and the UAT event's word
WORDS = {"send": "sent for sign-off", "reject": "rejected", "sign_off": "signed off", "return": "returned"}


def state_of(record: dict) -> str:
    """The review state of a stored brief, new or from before sign-off."""
    return record.get("review_state") or LEGACY[record["review_status"]]


def outcome(role_actions: tuple[str, ...], role_states: tuple[str, ...], state: str, action: str) -> int:
    """The HTTP status of `action` ("read" or a TRANSITIONS key) by a role on a brief in `state`.
    403: the role lacks the right. 404: the role may not see a brief in this state (so it does not know it exists).
    409: the brief is in the wrong state for the action. 200: allowed."""
    needed = "read" if action == "read" else TRANSITIONS[action][0]
    if needed not in role_actions:
        return 403
    if state not in role_states:
        return 404
    if action != "read" and state not in TRANSITIONS[action][1]:
        return 409
    return 200


def require(role, record: dict, action: str) -> str:
    """Raise the 403, 404 or 409 that `outcome` names; otherwise return the state the brief moves to."""
    code = outcome(role.actions, role.states, state_of(record), action)
    if code == 403:
        raise HTTPException(status_code=403, detail=f"The {role.label} role cannot {WORDS[action]} a briefing.")
    if code == 404:
        raise HTTPException(status_code=404, detail="No such briefing.")
    if code == 409:
        raise HTTPException(status_code=409, detail=f"This briefing is {STATE_WORDS[state_of(record)]}; it cannot be {WORDS[action]} now.")
    return TRANSITIONS[action][2]


STATE_WORDS = {DRAFT: "a draft", SENT: "waiting for sign-off", SIGNED_OFF: "signed off", RETURNED: "returned to the analyst",
               REJECTED: "rejected"}


def trail(record: dict) -> list[dict]:
    """The record's audit trail, oldest first. A brief from before sign-off gets one entry from its old review fields."""
    if record.get("review_trail"):
        return list(record["review_trail"])
    if record.get("reviewed_at") and record.get("review_status") in ("approved", "rejected"):
        return [{"at": record["reviewed_at"], "by": record.get("reviewed_by"), "persona": "P1", "action": record["review_status"],
                 "from": "draft", "to": LEGACY[record["review_status"]], "comment": record.get("review_reason"), "legacy": True}]
    return []


def returned_note(record: dict) -> dict | None:
    """The comment and flags of the latest return, while the brief is returned: what the analyst reads before rerunning."""
    if state_of(record) != RETURNED:
        return None
    last = next((e for e in reversed(trail(record)) if e.get("action") == "returned"), None)
    return {k: last.get(k) for k in ("at", "comment", "flags")} if last else None
