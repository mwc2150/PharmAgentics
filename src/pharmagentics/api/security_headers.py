"""Security headers on every app response, API and static files alike (UAT review 5.1).

The policy is strict where the built UI allows it. `style-src` keeps 'unsafe-inline' for two real reasons: the
sonner toast library writes a <style> element at runtime, and the server-rendered sign-in pages carry their
stylesheet inline. Scripts stay 'self' only. The sign-in redirect to Keycloak is a plain 302 and the callback is a
GET, so the Referrer-Policy and the CSP never see it; the Keycloak origin is still allowed in `form-action`, taken
from PHARMAGENTICS_OIDC_ISSUER and never hard-coded, so a form that redirects there is not blocked.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import Request

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=()"
REFERRER_POLICY = "strict-origin-when-cross-origin"
HSTS = "max-age=31536000; includeSubDomains"


def keycloak_origin() -> str | None:
    """The scheme and host of the public sign-in realm URL, or None when the issuer is not configured."""
    parsed = urlparse(os.environ.get("PHARMAGENTICS_OIDC_ISSUER", "").strip())
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme in ("http", "https") and parsed.netloc else None


def content_security_policy() -> str:
    form_action = " ".join(["'self'", *filter(None, [keycloak_origin()])])
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        f"form-action {form_action}",
        "base-uri 'self'",
    ])


def arrived_over_https(request: Request) -> bool:
    """Cloud Run ends TLS and says so in X-Forwarded-Proto; a local request has the scheme itself."""
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return forwarded == "https" or (not forwarded and request.url.scheme == "https")


def headers_for(request: Request) -> dict[str, str]:
    out = {
        "Content-Security-Policy": content_security_policy(),
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": REFERRER_POLICY,
        "Permissions-Policy": PERMISSIONS_POLICY,
    }
    if arrived_over_https(request):
        out["Strict-Transport-Security"] = HSTS
    return out
