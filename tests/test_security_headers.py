"""Security headers on every response: the page, an API route and a static file (UAT review 5.1)."""
from __future__ import annotations

import pytest
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from starlette.routing import Mount

from pharmagentics.api.app import app

ALWAYS = ("Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PHARMAGENTICS_AUTH", "dev")
    monkeypatch.setenv("PHARMAGENTICS_STATE_DIR", str(tmp_path))
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "index.html").write_text("<!doctype html><title>x</title>")
    (tmp_path / "ui" / "app.js").write_text("1")
    mount = Mount("/", app=StaticFiles(directory=tmp_path / "ui", html=True), name="ui-test")
    app.router.routes.append(mount)
    yield TestClient(app)
    app.router.routes.remove(mount)


def _check(r):
    for name in ALWAYS:
        assert name in r.headers, name
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert r.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    csp = r.headers["Content-Security-Policy"]
    for part in ("default-src 'self'", "script-src 'self'", "img-src 'self' data:", "connect-src 'self'",
                 "frame-ancestors 'none'", "base-uri 'self'"):
        assert part in csp
    assert "script-src 'self' 'unsafe" not in csp


@pytest.mark.parametrize("path", ["/", "/app.js", "/api/health", "/api/me", "/auth/login", "/nothing-here"])
def test_every_response_carries_the_headers(client, path):
    _check(client.get(path))


def test_hsts_only_over_https(client):
    assert "Strict-Transport-Security" not in client.get("/api/health").headers
    assert "Strict-Transport-Security" not in client.get("/api/health", headers={"X-Forwarded-Proto": "http"}).headers
    for path in ("/", "/app.js", "/api/health"):
        r = client.get(path, headers={"X-Forwarded-Proto": "https"})
        assert r.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Strict-Transport-Security" in TestClient(app, base_url="https://testserver").get("/api/health").headers


def test_form_action_allows_the_configured_keycloak_origin_only(client, monkeypatch):
    monkeypatch.delenv("PHARMAGENTICS_OIDC_ISSUER", raising=False)
    assert "form-action 'self';" in client.get("/api/health").headers["Content-Security-Policy"] + ";"
    monkeypatch.setenv("PHARMAGENTICS_OIDC_ISSUER", "https://kc.example/realms/pharmagentics")
    assert "form-action 'self' https://kc.example;" in client.get("/api/health").headers["Content-Security-Policy"] + ";"
