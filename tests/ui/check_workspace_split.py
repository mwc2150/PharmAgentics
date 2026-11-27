"""The Overview is its own workspace, apart from the Weekly briefing (brief-015, Michael 2026-11-27).

The Overview is for exploring; the Weekly briefing does the work, in two tabs: New briefing and Your briefings.
Changing the Overview's brand or week never changes the form, the form never changes the Overview, the brand is a
field of the form, and the Overview's "Brief this week" on a territory is the one link: it carries its brand,
territory and week to the form. Your briefings lists Approved, then Needs you, then With the reviewer. Every fold on
an approved brief shows a chevron that turns down when open. Drives the LOCAL app (dev sign-in, a built frontend)
with Playwright and prints PASS/FAIL per check; exit code 1 if any fails. No model and no secret are needed.

  uv run python tests/ui/check_workspace_split.py [--base http://127.0.0.1:8765]
"""
from __future__ import annotations

import argparse
import re
import sys

from playwright.sync_api import Page, sync_playwright

RESULTS: list[tuple[bool, str]] = []
FOLDS_JS = r"""() => [...document.querySelectorAll('summary')].filter(s => s.offsetParent).map(s => {
  const b = getComputedStyle(s, '::before');
  return {chevron: (b.maskImage || b.webkitMaskImage || '').startsWith('url(') && b.width !== 'auto', turned: b.transform !== 'none'}
})"""


def check(ok: bool, what: str) -> None:
    RESULTS.append((ok, what))
    print(f"{'PASS' if ok else 'FAIL'}  {what}")


def run(page: Page, base: str) -> None:
    page.goto(base + "/auth/login")
    page.request.post(base + "/auth/dev-login", form={"username": "dev-analyst"})
    page.goto(base + "/")
    page.wait_for_load_state("networkidle")
    workspace = lambda name: page.get_by_role("navigation", name="Workspaces").get_by_role("button", name=name)  # noqa: E731
    toggle = lambda: page.get_by_role("tablist", name="Weekly briefing").locator("xpath=..").get_by_label("Brand")  # noqa: E731
    overview_brand = lambda: page.locator("main label:visible", has_text=re.compile(r"^Brand")).locator("select").first  # noqa: E731
    overview_week = lambda: page.locator("main label:visible", has_text=re.compile(r"^Week")).locator("select").first  # noqa: E731
    form = lambda: page.locator("form").first  # noqa: E731
    brand_field = lambda: form().locator("label", has_text="Brand").locator("select").first  # noqa: E731

    def go(name: str) -> None:
        workspace(name).click()
        page.wait_for_timeout(700)

    def form_state() -> tuple[str, str, str, str]:
        go("Weekly briefing")
        page.get_by_role("tab", name="New briefing").click()
        page.wait_for_timeout(500)
        territory = form().locator("label", has_text="Territory").locator("select").first
        return (brand_field().input_value(), form().get_by_label("First week", exact=True).input_value(),
                form().get_by_label("Last week", exact=True).input_value(), territory.input_value())

    check(page.locator("header h1").inner_text() == "Overview" and workspace("Overview").get_attribute("aria-current") == "page",
          "The analyst opens on the Overview, the first workspace in the sidebar")
    check(overview_brand().count() == 1 and overview_week().count() == 1, "Overview: its own brand and week selectors")
    start = form_state()
    tabs = [t.splitlines()[0].strip() for t in page.get_by_role("tab").all_inner_texts()]
    check(tabs == ["New briefing", "Your briefings"], f"Weekly briefing: two tabs, New briefing and Your briefings {tabs}")
    check(toggle().count() == 0 and brand_field().count() == 1, "New briefing: no tab-row brand toggle; the brand is a form field")

    go("Overview")
    other = "BXC" if start[0] == "BXA" else "BXA"
    overview_brand().select_option(other)
    page.wait_for_timeout(800)
    overview_week().select_option("2026-08-24")
    page.wait_for_load_state("networkidle")
    check(form_state() == start, f"Changing the Overview's brand ({other}) and week leaves the form as it was {start}")

    form().get_by_label("First week", exact=True).select_option("2026-06-01")
    page.wait_for_timeout(300)
    go("Overview")
    check((overview_brand().input_value(), overview_week().input_value()) == (other, "2026-08-24"),
          "Changing the form's first week leaves the Overview's brand and week as they were")

    page.locator("main button:visible", has_text="Pacific").first.click()
    page.wait_for_timeout(800)
    page.get_by_role("dialog").get_by_role("button", name="Brief this week").click()
    page.wait_for_timeout(900)
    territory = form().locator("label", has_text="Territory").locator("select").first
    got = (brand_field().input_value(), form().get_by_label("First week", exact=True).input_value(),
           form().get_by_label("Last week", exact=True).input_value(), territory.input_value())
    check(page.locator("header h1").inner_text() == "Weekly briefing" and got == (other, "2026-08-24", "2026-08-24", "PACIFIC"),
          f"The Overview's 'Brief this week' on Pacific opens the form with its brand, week and territory {got}")

    page.get_by_role("tab", name="Your briefings").click()
    page.wait_for_timeout(1000)
    heads = [h.strip() for h in page.locator("#briefing-panel h3").all_inner_texts()]
    check(heads[:3] == ["Approved", "Needs you", "With the reviewer"], f"Your briefings: Approved, then Needs you, then With the reviewer {heads}")
    check(toggle().count() == 0, "Your briefings: no brand toggle (the lists show every brand)")

    # Every fold shows that it folds (Michael, 2026-11-27): a chevron before each summary, turned down when open.
    page.locator("#briefing-panel li button").first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    folds = page.evaluate(FOLDS_JS)
    check(bool(folds) and all(f["chevron"] for f in folds), f"An approved brief: every fold shows a chevron ({len(folds)} folds)")
    page.locator("summary:visible").first.click()
    page.wait_for_timeout(400)
    turned = page.evaluate(FOLDS_JS)[0]["turned"]
    check(turned and not folds[0]["turned"], "Opening a fold turns its chevron down")


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
