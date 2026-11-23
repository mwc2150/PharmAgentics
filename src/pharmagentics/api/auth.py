"""Sign-in (core-007 FR-011 to FR-015). The server holds the session; the browser only gets a
signed, HTTP-only cookie, so no token reaches the frontend code.

PHARMAGENTICS_AUTH selects the mode:
- "oidc" (default): authorization-code flow with PKCE against Keycloak. Needs
  PHARMAGENTICS_OIDC_ISSUER (the public realm URL), PHARMAGENTICS_OIDC_CLIENT_ID and
  PHARMAGENTICS_OIDC_CLIENT_SECRET. PHARMAGENTICS_OIDC_METADATA_URL optionally points at an
  internal address for the discovery document (docker-compose: http://keycloak:8080/...).
- "dev": stand-in identities, one per role, for local work and tests. Refused on Cloud Run.
"""
from __future__ import annotations

import html
import logging
import os
from urllib.parse import urlencode
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import brand_access, rbac

router = APIRouter()
logger = logging.getLogger(__name__)

# The display name is the persona's first name (the app greets by it; brief-008 FR-012 shows the name only):
# Ace is the analyst in both lanes, Diana the Brand Director, Miranda the Brand Manager. The roles tell the
# stand-ins apart on the sign-in page.
DEV_USERS = {
    "dev-analyst": ("Ace", ["briefing-analyst", "brand-bxa"]),
    "dev-director": ("Diana", ["briefing-director", "brand-bxa"]),
    "dev-analyst-multibrand": ("Ace", ["briefing-analyst", "brand-bxa", "brand-bxc"]),
    "dev-director-multibrand": ("Diana", ["briefing-director", "brand-bxa", "brand-bxc"]),
    "dev-analyst-no-brands": ("Ace", ["briefing-analyst"]),
    "dev-forecast-analyst": ("Ace", ["forecast-analyst", "brand-bxa"]),
    "dev-forecast-manager": ("Miranda", ["forecast-manager", "brand-bxa"]),
    # Like uat-tester in the Keycloak realm: both lanes, switching between the analyst and the leadership view.
    "dev-tester": ("Tester", ["tester", "brand-bxa", "brand-bxc"]),
    "dev-norole": ("No role", []),
}


def mode() -> str:
    m = os.environ.get("PHARMAGENTICS_AUTH", "oidc")
    if m == "dev" and os.environ.get("K_SERVICE"):
        raise RuntimeError("PHARMAGENTICS_AUTH=dev is refused on Cloud Run; use oidc.")
    return m


_oauth = None


def _client():
    global _oauth
    if _oauth is None:
        from authlib.integrations.starlette_client import OAuth

        issuer = os.environ.get("PHARMAGENTICS_OIDC_ISSUER", "").rstrip("/")
        client_id = os.environ.get("PHARMAGENTICS_OIDC_CLIENT_ID")
        secret = os.environ.get("PHARMAGENTICS_OIDC_CLIENT_SECRET")
        if not (issuer and client_id and secret):
            raise HTTPException(status_code=503, detail="Sign-in is not configured on this server.")
        oauth = OAuth()
        oauth.register(
            "keycloak", client_id=client_id, client_secret=secret,
            server_metadata_url=os.environ.get("PHARMAGENTICS_OIDC_METADATA_URL")
            or f"{issuer}/.well-known/openid-configuration",
            # Keycloak scales to zero and needs about 16 s to start (core-007 SC-004 allows 60 s with a cold start),
            # so wait longer than httpx's default of 5 s.
            client_kwargs={"scope": "openid profile", "code_challenge_method": "S256", "timeout": 50.0},
        )
        _oauth = oauth
    return _oauth.keycloak


def _set_user(request: Request, sub: str, name: str, roles: list[str]) -> None:
    known = rbac.known_role_names()
    request.session.clear()
    request.session["user"] = {"sub": sub, "name": name, "roles": [r for r in roles if r in known],
                               "brand_grants": [r for r in roles if r in brand_access.GRANTS]}


# The app's theme (DESIGN.md) for the pages the server renders itself. Fonts and the mark come from the UI's static
# files on the same origin; system fonts stand in if they are absent.
_PAGE_CSS = """
@font-face{font-family:"Space Grotesk";font-weight:300 700;font-display:swap;src:url("/fonts/space-grotesk-latin.woff2") format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-weight:100 700;font-display:swap;src:url("/fonts/ibm-plex-sans-latin.woff2") format("woff2")}
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;padding:48px 16px;background:#101117;color:#f3f3f3;
  font:15px/1.5 "IBM Plex Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
main{width:100%;max-width:440px;background:#1b1d27;border:1px solid #373a52;border-radius:22px;box-shadow:0 5px 0 #3a3e58;padding:32px}
.mark{display:block;width:56px;height:56px;margin-bottom:24px}
h1{margin:0;font:700 28px/1.25 "Space Grotesk",system-ui,sans-serif;letter-spacing:-0.02em}
h1 span{background:#2a8c7c;color:#0b0c10;padding:0.05em 0.4em 0.1em;border-radius:8px}
p{margin:14px 0 0;color:#a6aabf;font-size:14px}
form{margin-top:20px;display:grid;gap:12px}
button{display:block;width:100%;padding:12px 16px;border:1px solid #8a8ea6;border-radius:14px;background:transparent;color:#f3f3f3;
  text-align:left;font:500 15px/1.4 inherit;font-family:inherit;cursor:pointer;box-shadow:0 3px 0 #3a3e58;
  transition:background-color .15s,transform .15s,box-shadow .15s}
button:hover{background:#101117}
button:active{transform:translateY(2px);box-shadow:0 1px 0 #3a3e58}
button:focus-visible{outline:2px solid #2a8c7c;outline-offset:2px}
small{display:block;margin-top:2px;color:#a6aabf;font-size:12px;font-weight:400}
@media (prefers-reduced-motion:reduce){button{transition:none}button:active{transform:none}}
"""


def _page(title: str, body: str, *, head: str = "", status_code: int = 200, headers: dict[str, str] | None = None) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101117">{head}
<title>{html.escape(title)} · PharmAgentics</title><link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" href="/favicon.ico" sizes="any"><style>{_PAGE_CSS}</style></head>
<body><main><img class="mark" src="/pa-mark.svg" alt="PharmAgentics" width="56" height="56">{body}</main></body></html>""",
                        status_code=status_code, headers=headers)


@router.get("/auth/login", include_in_schema=False)
async def login(request: Request):
    if mode() == "dev":
        buttons = "".join(
            f'<button name="username" value="{html.escape(u)}">{html.escape(n)}'
            f'<small>{html.escape(", ".join(r) or "no role")}</small></button>'
            for u, (n, r) in DEV_USERS.items())
        return _page("Development sign-in", f"""<h1><span>Development sign-in</span></h1>
<p>Stand-in identities for local work. The deployed app signs in through Keycloak instead.</p>
<form method="post" action="/auth/dev-login">{buttons}</form>""")
    redirect_uri = str(request.url_for("auth_callback"))
    client = _client()  # a 503 here means sign-in is not configured, which is not a cold start
    try:
        return await client.authorize_redirect(request, redirect_uri)
    except Exception:  # noqa: BLE001 - any failure to reach Keycloak (timeouts, refused connections; the transport's types vary)
        logger.warning("Sign-in service unreachable; showing the retry page", exc_info=True)
        return _starting_page()


def _starting_page() -> HTMLResponse:
    """The sign-in service did not answer in time (a cold start that ran long): retry instead of a bare 500."""
    return _page("Starting sign-in", """<h1>Starting the sign-in service</h1>
<p>It sleeps when nobody is using it and takes a few seconds to wake. This page retries by itself.</p>""",
                 head='<meta http-equiv="refresh" content="5">',
                 status_code=503, headers={"Retry-After": "5", "Cache-Control": "no-store"})


@router.post("/auth/dev-login", include_in_schema=False)
async def dev_login(request: Request, username: str = Form(...)):
    if mode() != "dev" or username not in DEV_USERS:
        raise HTTPException(status_code=404)
    name, roles = DEV_USERS[username]
    _set_user(request, username, name, roles)
    return RedirectResponse("/", status_code=303)


@router.get("/auth/callback", name="auth_callback", include_in_schema=False)
async def callback(request: Request):
    if mode() != "oidc":
        raise HTTPException(status_code=404)
    token = await _client().authorize_access_token(request)  # validates the ID token (issuer, audience, signature, nonce)
    claims = token.get("userinfo") or {}
    _set_user(request, claims["sub"], claims.get("name") or claims.get("preferred_username", ""), list(claims.get("roles", [])))
    request.session["id_token"] = token.get("id_token")
    return RedirectResponse("/", status_code=303)


@router.get("/auth/logout", include_in_schema=False)
async def logout(request: Request):
    id_token = request.session.get("id_token")
    request.session.clear()
    if mode() != "oidc":
        return RedirectResponse("/", status_code=303)
    client = _client()
    metadata = await client.load_server_metadata()
    params = {"post_logout_redirect_uri": str(request.base_url), "client_id": client.client_id}
    if id_token:
        params["id_token_hint"] = id_token
    return RedirectResponse(f"{metadata['end_session_endpoint']}?{urlencode(params)}", status_code=303)
