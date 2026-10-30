"""What every system under test returns. Scorers read this, never the system's internals (black-box rule)."""
from __future__ import annotations

from pydantic import BaseModel


class Evidence(BaseModel):
    id: str
    tool: str
    params: dict = {}
    query: str | None = None
    result: object = None
    data_version: str | None = None


class Claim(BaseModel):
    value: str
    evidence_id: str


class AnswerEnvelope(BaseModel):
    system: str
    answer: str
    claims: list[Claim] = []
    evidence: list[Evidence] = []
    abstained: bool = False
