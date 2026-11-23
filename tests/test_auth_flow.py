"""Sign-out, a failed sign-in callback and UI caching (core-007 FR-011 to FR-015; 2026-11-23 fixes).

Keycloak keeps no database, so it makes new signing keys whenever it wakes from idle: a sign-out that sent the old
ID token as a hint was refused and left the person on Keycloak's error page. A stale sign-in page (two tabs, the
back button) made the callback fail with a bare 500. And with no Cache-Control on the UI page, browsers kept
showing the previous release after a deploy.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from pharmagentics.api import auth
from pharmagentics.api.app import app


class FakeKeycloak:
    client_id = "pharmagentics-app"

    def __init__(self, fail_callback: Exception | None = None, fail_metadata: bool = False):
        self.fail_callback, self.fail_metadata = fail_callback, fail_metadata

    async def load_server_metadata(self):
        if self.fail_metadata:
            raise ConnectionError("keycloak is waking up")
        return {"end_session_endpoint": "https://kc.example/realms/pharmagentics/protocol/openid-connect/logout"}

    async def authorize_access_token(self, request):
        if self.fail_callback:
            raise self.fail_callback
        return {"userinfo": {"sub": "u1", "name": "Tester", "roles": ["tester"]}, "id_token": "x.y.z"}


@pytest.fixture
def oidc(monkeypatch, tmp_path):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "oidc")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    fake = FakeKeycloak()
    monkeypatch.setattr(auth, "_client", lambda: fake)
    return fake


def test_sign_out_sends_no_id_token_hint_and_returns_to_the_signed_out_page(oidc):
    c = TestClient(app)
    assert c.get("/auth/callback", follow_redirects=False).status_code == 303
    assert c.get("/api/me").status_code == 200
    r = c.get("/auth/logout", follow_redirects=False)
    assert r.status_code == 303
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert url.netloc == "kc.example" and "id_token_hint" not in q
    assert q["client_id"] == ["pharmagentics-app"]
    assert q["post_logout_redirect_uri"][0].endswith("/auth/signed-out")
    assert c.get("/api/me").status_code == 401  # the app session is gone whatever Keycloak does next


def test_signed_out_page_offers_a_fresh_sign_in(oidc):
    r = TestClient(app).get("/auth/signed-out")
    assert r.status_code == 200 and 'href="/auth/login"' in r.text and r.headers["cache-control"] == "no-store"


def test_sign_out_when_keycloak_is_unreachable_still_signs_out(oidc):
    oidc.fail_metadata = True
    c = TestClient(app)
    c.get("/auth/callback", follow_redirects=False)
    r = c.get("/auth/logout", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/auth/signed-out"
    assert c.get("/api/me").status_code == 401


def test_a_failed_callback_offers_sign_in_again_instead_of_a_500(oidc):
    from authlib.integrations.base_client.errors import MismatchingStateError
    oidc.fail_callback = MismatchingStateError()
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/auth/callback?state=old&code=x", follow_redirects=False)
    assert r.status_code == 400 and 'href="/auth/login"' in r.text
    assert c.get("/api/me").status_code == 401


def test_ui_page_is_revalidated_and_hashed_assets_are_kept(monkeypatch):
    from starlette.responses import HTMLResponse, Response

    @app.get("/__cache_probe.html", include_in_schema=False)
    async def _page():
        return HTMLResponse("<!doctype html><p>ui</p>")

    @app.get("/assets/__cache_probe.js", include_in_schema=False)
    async def _asset():
        return Response("1", media_type="text/javascript")

    @app.get("/__cache_probe.svg", include_in_schema=False)
    async def _logo():
        return Response("<svg/>", media_type="image/svg+xml")

    try:
        c = TestClient(app)
        assert c.get("/__cache_probe.html").headers["cache-control"] == "no-cache"
        assert "immutable" in c.get("/assets/__cache_probe.js").headers["cache-control"]
        assert c.get("/__cache_probe.svg").headers["cache-control"] == "no-cache"  # a fixed-name file such as the logo
    finally:
        app.router.routes[:] = [r for r in app.router.routes if "__cache_probe" not in getattr(r, "path", "")]
