"""core-007 deployment guards that run without Google Cloud."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gcp", ROOT / "deploy" / "gcp.py")
gcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gcp)

ENV = {"PHARMAGENTICS_OIDC_CLIENT_SECRET": "s3cret", "UAT_PASSWORD_BRIEFING_ANALYST": "a", "UAT_PASSWORD_BRIEFING_DIRECTOR": "d",
       "UAT_PASSWORD_BRIEFING_INSIGHTS": "i", "UAT_PASSWORD_BRIEFING_MARKETER": "m",
       "UAT_PASSWORD_FORECAST_ANALYST": "fa", "UAT_PASSWORD_FORECAST_MANAGER": "fm",
       "UAT_PASSWORD_TESTER": "t"}


def test_realm_in_repo_holds_no_secret_values():
    realm = json.loads((ROOT / "deploy" / "keycloak" / "realm-pharmagentics.json").read_text(encoding="utf-8"))
    client = realm["clients"][0]
    assert client["secret"] == "${PHARMAGENTICS_OIDC_CLIENT_SECRET}"
    for user in realm["users"]:
        assert all(c["value"].startswith("${UAT_PASSWORD_") for c in user["credentials"])
    assert realm["registrationAllowed"] is False  # FR-012: no self-registration


SHARED_LOGINS = {"uat-briefing-analyst": "UAT_PASSWORD_BRIEFING_ANALYST", "uat-briefing-insights": "UAT_PASSWORD_BRIEFING_INSIGHTS",
                 "uat-briefing-director": "UAT_PASSWORD_BRIEFING_DIRECTOR", "uat-briefing-marketer": "UAT_PASSWORD_BRIEFING_MARKETER",
                 "uat-forecast-analyst": "UAT_PASSWORD_FORECAST_ANALYST", "uat-forecast-manager": "UAT_PASSWORD_FORECAST_MANAGER",
                 "uat-tester": "UAT_PASSWORD_TESTER"}


def test_versioned_demo_credentials_contain_only_the_shared_uat_passwords():
    values = {}
    for line in (ROOT / "deploy" / "demo-credentials.env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    assert set(values) == set(SHARED_LOGINS.values())  # never a service secret
    assert all(values.values())


def test_each_shared_password_belongs_to_its_realm_account():
    realm = json.loads((ROOT / "deploy" / "keycloak" / "realm-pharmagentics.json").read_text(encoding="utf-8"))
    users = {u["username"]: u for u in realm["users"]}
    for account, key in SHARED_LOGINS.items():
        assert users[account]["credentials"][0]["value"] == "${" + key + "}"


def test_the_realm_has_exactly_the_seven_uat_logins_with_their_roles_and_brand_grants():
    """Session 2026-11-27: four Briefing logins, two Forecast logins and the tester. Every Briefing login and the tester hold
    both brands; Forecast logins keep BXA only. The two multibrand logins are gone (per-user grants are tested with fabricated principals)."""
    realm = json.loads((ROOT / "deploy" / "keycloak" / "realm-pharmagentics.json").read_text(encoding="utf-8"))
    users = {u["username"]: u for u in realm["users"]}
    assert set(users) == set(SHARED_LOGINS) and len(users) == 7
    both = ["brand-bxa", "brand-bxc"]
    assert {n: u["realmRoles"] for n, u in users.items()} == {
        "uat-briefing-analyst": ["briefing-analyst", *both], "uat-briefing-insights": ["briefing-insights", *both],
        "uat-briefing-director": ["briefing-director", *both], "uat-briefing-marketer": ["briefing-marketer", *both],
        "uat-forecast-analyst": ["forecast-analyst", "brand-bxa"], "uat-forecast-manager": ["forecast-manager", "brand-bxa"],
        "uat-tester": ["tester", *both]}


def test_the_stand_in_logins_mirror_the_realm_grants():
    """Dev sign-in follows the realm (the multibrand and no-brands stand-ins are test fixtures, not UAT logins)."""
    from pharmagentics.api import auth

    realm = json.loads((ROOT / "deploy" / "keycloak" / "realm-pharmagentics.json").read_text(encoding="utf-8"))
    for user in realm["users"]:
        dev = "dev-" + user["username"].removeprefix("uat-").replace("briefing-", "")
        dev = {"dev-forecast-analyst": "dev-forecast-analyst", "dev-forecast-manager": "dev-forecast-manager"}.get(dev, dev)
        assert sorted(auth.DEV_USERS[dev][1]) == sorted(user["realmRoles"]), dev


def test_make_env_lists_the_same_accounts_as_the_realm():
    spec = importlib.util.spec_from_file_location("make_env", ROOT / "deploy" / "make_env.py")
    make_env = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(make_env)
    assert make_env.DEMO_ACCOUNTS == SHARED_LOGINS
    assert all(make_env.DEMO_PASSWORDS[k] for k in SHARED_LOGINS.values())


def test_realm_roles_match_the_policy():
    realm = json.loads((ROOT / "deploy" / "keycloak" / "realm-pharmagentics.json").read_text(encoding="utf-8"))
    policy = json.loads((ROOT / "src" / "pharmagentics" / "api" / "roles.json").read_text(encoding="utf-8"))
    assert {r["name"] for r in realm["roles"]["realm"]} == set(policy["roles"]) | {policy["test_role"]["name"], "brand-bxa", "brand-bxc"}


def test_render_realm_fills_every_placeholder():
    text = gcp.render_realm(ENV, "https://app.example")
    assert "${" not in text
    realm = json.loads(text)
    assert realm["clients"][0]["redirectUris"] == ["https://app.example/auth/callback"]


def test_render_realm_refuses_a_missing_password():
    with pytest.raises(SystemExit, match="UAT_PASSWORD_BRIEFING_DIRECTOR"):
        gcp.render_realm({k: v for k, v in ENV.items() if k != "UAT_PASSWORD_BRIEFING_DIRECTOR"}, "https://app.example")


def test_dockerignore_is_an_allow_list_that_keeps_eval_out():
    lines = [l.strip() for l in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert lines[0] == "*"
    assert not any(l.startswith("!") and ("eval" in l or "SoT" in l or ".env" in l) for l in lines)


def test_failed_event_write_does_not_stop_the_briefing(monkeypatch, tmp_path):
    from pharmagentics.api import store

    class Broken:
        def write(self, key, text):
            raise OSError("bucket unreachable")

    with patch.object(store, "backend", return_value=Broken()):
        store.record_event("requested", user="u-x")  # must not raise
