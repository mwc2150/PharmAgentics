"""The Briefing workspace keeps the Overview and New briefing apart (brief-015, Michael 2026-11-27).

The Overview is for exploring; New briefing does the work. Changing the Overview's brand or week never changes the
form, the form never changes the Overview, the brand is a field of the form, the tab-row brand toggle shows on the
Overview only, and the Overview's "Generate brief for <territory>" is the one link: it carries its brand, territory and
week to the form. Drives the LOCAL app (dev sign-in, a built frontend) with Playwright and prints PASS/FAIL per check;
exit code 1 if any fails. No model and no secret are needed.

  uv run python tests/ui/check_workspace_split.py [--base http://127.0.0.1:8765]
"""
from __future__ import annotations

import argparse
import re
import sys

from playwright.sync_api import Page, sync_playwright

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, what: str) -> None:
    RESULTS.append((ok, what))
    print(f"{'PASS' if ok else 'FAIL'}  {what}")


def run(page: Page, base: str) -> None:
    page.goto(base + "/auth/login")
    page.request.post(base + "/auth/dev-login", form={"username": "dev-analyst"})
    page.goto(base + "/")
    page.wait_for_load_state("networkidle")
    toggle = lambda: page.get_by_role("tablist", name="Weekly briefing").locator("xpath=..").get_by_label("Brand")  # noqa: E731
    overview_week = lambda: page.locator("label", has_text=re.compile(r"^Week")).locator("select").first  # noqa: E731
    form = lambda: page.locator("form").first  # noqa: E731
    brand_field = lambda: form().locator("label", has_text="Brand").locator("select").first  # noqa: E731

    def form_state() -> tuple[str, str, str, str]:
        page.get_by_role("tab", name="New briefing").click()
        page.wait_for_timeout(500)
        territory = form().locator("label", has_text="Territory").locator("select").first
        return (brand_field().input_value(), form().get_by_label("First week", exact=True).input_value(),
                form().get_by_label("Last week", exact=True).input_value(), territory.input_value())

    check(toggle().count() == 1, "Overview: the tab-row brand toggle is shown")
    start = form_state()
    check(toggle().count() == 0, "New briefing: no tab-row brand toggle; the brand is a form field")
    check(brand_field().count() == 1, "New briefing: the form has a Brand field")

    page.get_by_role("tab", name="Overview").click()
    page.wait_for_timeout(500)
    other = "BXC" if start[0] == "BXA" else "BXA"
    toggle().select_option(other)
    page.wait_for_timeout(800)
    overview_week().select_option("2026-08-24")
    page.wait_for_load_state("networkidle")
    check(form_state() == start, f"Changing the Overview's brand ({other}) and week leaves the form as it was {start}")

    form().get_by_label("First week", exact=True).select_option("2026-06-01")
    page.wait_for_timeout(300)
    page.get_by_role("tab", name="Overview").click()
    page.wait_for_timeout(800)
    check((toggle().input_value(), overview_week().input_value()) == (other, "2026-08-24"),
          "Changing the form's first week leaves the Overview's brand and week as they were")

    page.get_by_role("button", name=re.compile("Pacific")).first.click()
    page.wait_for_timeout(800)
    page.get_by_role("button", name=re.compile(r"Generate brief for Pacific")).click()
    page.wait_for_timeout(800)
    territory = form().locator("label", has_text="Territory").locator("select").first
    got = (brand_field().input_value(), form().get_by_label("First week", exact=True).input_value(),
           form().get_by_label("Last week", exact=True).input_value(), territory.input_value())
    check(got == (other, "2026-08-24", "2026-08-24", "PACIFIC"),
          f"The Overview's 'Generate brief for Pacific' carries its brand, week and territory to the form {got}")

    page.get_by_role("tab", name="Approved").click()
    page.wait_for_timeout(400)
    check(toggle().count() == 0, "Approved briefings: no brand toggle (the lists show every brand)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    args = ap.parse_args()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            run(browser.new_page(viewport={"width": 1280, "height": 900}), args.base.rstrip("/"))
        finally:
            browser.close()
    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
