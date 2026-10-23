"""Claim tokens and the renderer (FR-008).

The narrator writes {{c#}} tokens. Code owns every value and its formatting.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .contracts import Claim

TOKEN_RE = re.compile(r"\{\{\s*(c\d+)\s*\}\}")
MINUS = "\u2212"


def fmt_value(value: Any, fmt: str) -> str:
    if value is None:
        return "n/a"
    if fmt == "int":
        return f"{round(float(value)):,}"
    if fmt == "int_signed":
        v = round(float(value))
        return f"+{v:,}" if v > 0 else (f"{MINUS}{abs(v):,}" if v < 0 else "0")
    if fmt == "pct":
        return f"{float(value) * 100:.1f}%"
    if fmt == "pct_signed":
        v = float(value) * 100
        return f"+{v:.1f}%" if v > 0.05 else (f"{MINUS}{abs(v):.1f}%" if v < -0.05 else "0.0%")
    if fmt == "pts_signed":
        v = float(value) * 100
        return f"+{v:.1f} pts" if v > 0.05 else (f"{MINUS}{abs(v):.1f} pts" if v < -0.05 else "0.0 pts")
    if fmt == "ratio":
        return f"{float(value):.2f}"
    if fmt == "dec1":
        return f"{float(value):,.1f}"
    if fmt == "date":
        return value.isoformat() if isinstance(value, date) else str(value)
    return str(value)


class ClaimBook:
    """All claims of one run. Tokens are unique per run."""

    def __init__(self) -> None:
        self.claims: dict[str, Claim] = {}

    def add(self, label: str, value: Any, fmt: str, evidence_id: str) -> str:
        token = f"c{len(self.claims) + 1}"
        if isinstance(value, date):
            value = value.isoformat()
        self.claims[token] = Claim(token=token, label=label, value=value, fmt=fmt,
                                   display=fmt_value(value, fmt), evidence_id=evidence_id)
        return "{{" + token + "}}"

    def sign(self, token: str) -> str:
        claim = self.claims.get(token)
        if claim is None or not isinstance(claim.value, (int, float)) or claim.fmt in ("date", "text"):
            return "n/a"
        return "negative" if claim.value < 0 else ("positive" if claim.value > 0 else "zero")


def render(text: str, claims: dict[str, Claim]) -> str:
    return TOKEN_RE.sub(lambda m: claims[m.group(1)].display if m.group(1) in claims else m.group(0), text)


def tokens_in(text: str) -> list[str]:
    return TOKEN_RE.findall(text)
