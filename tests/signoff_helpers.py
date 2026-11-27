"""Test helpers for the two-step sign-off (brief-005): send a brief for sign-off and have the Insights Manager sign it off.

Not a test file. A test that needs a brief the Brand Director can read calls `approve(analyst, brief_id)`.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from pharmagentics.api.app import app


def sign_in(username: str) -> TestClient:
    client = TestClient(app)
    assert client.post("/auth/dev-login", data={"username": username}, follow_redirects=False).status_code == 303
    return client


def send(analyst: TestClient, brief_id: str):
    return analyst.post(f"/api/briefing/{brief_id}/review", json={"decision": "sent"})


def approve(analyst: TestClient, brief_id: str, insights: TestClient | None = None) -> dict:
    """The analyst sends the brief for sign-off and the Insights Manager signs it off. Returns the signed-off brief."""
    assert send(analyst, brief_id).status_code == 200
    response = (insights or sign_in("dev-insights")).post(f"/api/briefing/{brief_id}/signoff", json={"decision": "signed_off"})
    assert response.status_code == 200, response.text
    return response.json()
