"""The Marketer (P4) view in the browser: the promotion panel under each territory story and the budget note, at 1280x800 and 390x844.

Drives the LOCAL app (dev sign-in, a built frontend, the scripted engine, no model) with Playwright and prints PASS/FAIL per
assertion; exit code 1 if any fails. As dev-analyst it creates three briefs (a supported promotion, an untestable one, one
within its normal range) and sends them; as dev-insights it signs them off; then dev-marketer opens each and dev-director
opens the same briefs. Screenshots go to local/marketer-view/ (git-ignored). It reuses the sign-in of review_walkthrough.py.

  uv run python tests/ui/check_marketer_view.py [--base http://127.0.0.1:8772]

Start the app first (see .claude/skills/uat-review/SKILL.md): PHARMAGENTICS_AUTH=dev, PHARMAGENTICS_STATIC_DIR=<built dist>,
PHARMAGENTICS_STATE_DIR=<an empty folder>.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # the arrow in the table

from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_walkthrough import PERSONAS, ROOT, Review, sign_off_queue  # noqa: E402

PERSONAS["marketer"] = ("dev-marketer", "Magdalena briefing-marketer, brand-bxa, brand-bxc")
VIEWPORTS = {"1280": {"width": 1280, "height": 800}, "390": {"width": 390, "height": 844}}

# name -> (the query, the list row to open, the verdict word, whether a supported effect line is expected)
CASES = {
    "supported": ({"territory_id": "SOUTHEAST", "week_start": "2026-08-24", "question": "How did BXA TRx move, and why?",
                   "comparison": {"kind": "custom", "start": "2026-07-06", "end": "2026-07-27"}}, "Southeast, week of Aug 24, 2026", "Supported", True),
    "not_testable": ({"territory_id": "GREAT_LAKES", "week_start": "2025-03-03", "question": "What moved?"}, "Great Lakes, week of Mar 3, 2025", "Not testable", False),
    "within_range": ({"territory_id": "SOUTHEAST", "week_start": "2026-10-05", "question": "What moved?"}, "Southeast, week of Oct 5, 2026", "Not credited", False),
}
ROWS = ["New patients (NBRx)", "TRx", "Rep calls", "Digital impressions", "Samples", "Speaker programs"]
BUDGET_START = "Where the next dollar should go is outside this brief: it has no spend data"
BANNED = re.compile(r"\b(ROI|return on investment|attribution|caused|surveillance)\b", re.I)

LAYOUT_JS = r"""
() => {
  const panel = document.querySelector('[data-testid=promotion-panel]');
  const region = panel && panel.querySelector('[role=region]');
  const table = region && region.querySelector('table');
  const cut = [];
  if (panel) for (const el of panel.querySelectorAll('p, h5, th, td, span')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || el.closest('.sr-only') || (el.closest('thead') && getComputedStyle(el.closest('thead')).position === 'absolute')) continue;  // screen-reader-only text is positioned off-screen on purpose
    const inRegion = region.contains(el);
    const limit = (inRegion ? region : panel).getBoundingClientRect();
    if (r.right > limit.right + 1 && !(inRegion && region.scrollWidth > region.clientWidth)) cut.push(el.innerText.trim().slice(0, 30));
    if (!inRegion && el.scrollWidth > el.clientWidth + 1) cut.push('clipped ' + el.innerText.trim().slice(0, 30));
  }
  return {found: !!panel, pageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
          regionScrolls: !!region && region.scrollWidth > region.clientWidth + 1,
          regionW: region ? region.clientWidth : 0, tableW: table ? table.scrollWidth : 0,
          panelRight: panel ? Math.round(panel.getBoundingClientRect().right) : 0, winW: window.innerWidth, cut};
}
"""


class Checks:
    def __init__(self) -> None:
        self.failed = 0

    def check(self, vp: str, name: str, ok: bool, detail: str = "") -> None:
        self.failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {vp}px  {name}" + (f"  [{detail}]" if detail else ""), flush=True)


def make_briefs(base: str) -> None:
    """As dev-analyst create the three briefs and send them; as dev-insights sign them off."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.open(urllib.request.Request(f"{base}/auth/dev-login", data=urllib.parse.urlencode({"username": "dev-analyst"}).encode(), method="POST"))

    def post(path: str, body: dict) -> dict:
        req = urllib.request.Request(f"{base}{path}", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        return json.load(opener.open(req, timeout=300))

    for name, (query, *_rest) in CASES.items():
        brief = post("/api/briefing/query", {"intent": "weekly_brief", "brand_id": "BXA", **query})
        try:
            post(f"/api/briefing/{brief['brief_id']}/review", {"decision": "sent"})
        except urllib.error.HTTPError as exc:  # 409: a rerun on the same state, the brief is already past the draft
            if exc.code != 409:
                raise
        print(f"  created and sent {name}: {brief['brief_id']}", flush=True)
    sign_off_queue(base)


def open_brief(page: Page, row: str) -> dict:
    """Open a brief from the list and return the JSON the server sent for it."""
    with page.expect_response(lambda x: "/api/briefing/b-" in x.url and "view=leadership" in x.url) as sent:
        page.get_by_role("button", name=re.compile(re.escape(row))).first.click()
    page.get_by_role("article").wait_for(timeout=20000)
    page.wait_for_timeout(900)
    return sent.value.json()


def back(page: Page) -> None:
    page.get_by_role("button", name=re.compile("All signed-off briefings")).click()
    page.wait_for_timeout(700)


def marketer_pass(r: Review, c: Checks, ctx, vp: str, out: Path) -> None:
    page = r.sign_in(ctx, "marketer")
    intro = page.locator("main").inner_text()
    c.check(vp, "landing intro says what the Marketer gets",
            "Signed-off briefings, with how promotion moved new patients and TRx in each story territory." in intro)
    for name, (_q, row, verdict, effect) in CASES.items():
        payload = open_brief(page, row)
        promo = next(x["promotion"] for x in payload["sections"] if x.get("promotion"))
        panels = page.get_by_test_id("promotion-panel")
        stories = sum(1 for x in payload["sections"] if x["number"].startswith("3.") and x.get("promotion"))
        c.check(vp, f"{name}: one promotion panel under each story the server gave a promotion read ({stories})", panels.count() == stories >= 1, f"{panels.count()} panels")
        panel = panels.first
        panel.scroll_into_view_if_needed()
        line = page.get_by_test_id("promotion-verdict").first.inner_text()
        c.check(vp, f"{name}: verdict line starts '{verdict}'", line.startswith(verdict), line)
        labels = [t.strip() for t in panel.locator("tbody th").all_inner_texts()]
        c.check(vp, f"{name}: rows are NBRx, TRx, then the four channels in order", labels == ROWS, str(labels))
        rows = panel.locator("tbody tr")
        marked = [t.strip() for t in panel.locator("tbody tr").filter(has=page.locator("span", has_text=re.compile(r"^moved$"))).locator("th").all_inner_texts()]
        expected = [x["channel"].capitalize() for x in promo["channels"] if x["moved"]]
        c.check(vp, f"{name}: the 'moved' marker is on exactly the channels the server says moved", marked == expected, f"shown {marked}, server {expected}")
        sent = [promo["new_patients"], promo["trx"], *promo["channels"]]
        texts = [t.replace(" ", " ") for t in rows.all_inner_texts()]
        c.check(vp, f"{name}: each row shows the server's before, after, direction and change, and nothing else",
                len(texts) == 6 and all(m["before"] in t and m["after"] in t and m["direction"] in t and (m["change"] or "") in t for m, t in zip(sent, texts)), "; ".join(" ".join(t.split()) for t in texts))
        meta = panel.inner_text()
        c.check(vp, f"{name}: the lag and a re-check date are stated", re.search(r"Read at the .+lag|same week", meta) is not None and re.search(r"Re-check after [A-Z][a-z]{2} \d{1,2}, 20\d\d", meta) is not None,
                re.findall(r"Re-check after [^.]*", meta)[0] if "Re-check" in meta else "no re-check")
        has_effect = page.get_by_test_id("promotion-effect").count()
        c.check(vp, f"{name}: effect line {'shown' if effect else 'absent'}", has_effect == (1 if effect else 0), f"{has_effect}")
        if effect:
            eff = page.get_by_test_id("promotion-effect").inner_text()
            c.check(vp, f"{name}: effect says 'Compared with N territories without a promotion change' and is a range, not a return",
                    re.search(r"Compared with \d+ territories without a promotion change: \d+ to \d+ (extra|fewer) TRx a week\.", eff) is not None and "not a return on spend" in eff, eff.replace("\n", " "))
        note = page.get_by_test_id("budget-note")
        c.check(vp, f"{name}: the budget note is shown once, after the stories", note.count() == 1 and BUDGET_START in note.inner_text(), f"{note.count()}")
        c.check(vp, f"{name}: the budget note comes after the promotion panel",
                page.evaluate("() => { const a = document.querySelector('[data-testid=promotion-panel]'), b = document.querySelector('[data-testid=budget-note]');"
                              " return !!(a && b && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)); }"))
        body = page.locator("article").inner_text()
        c.check(vp, f"{name}: no ROI, attribution or 'caused' wording; no claim token or query text", not BANNED.search(body) and "{c" not in body and not re.search(r"\bselect\b.*\bfrom\b", body, re.I),
                (BANNED.search(body) or [""])[0] if BANNED.search(body) else "")
        lay = page.evaluate(LAYOUT_JS)
        c.check(vp, f"{name}: the page does not scroll sideways and nothing is cut off", lay["found"] and not lay["pageOverflow"] and not lay["cut"] and lay["panelRight"] <= lay["winW"],
                f"table {lay['tableW']}px in a {lay['regionW']}px region (scrolls inside: {lay['regionScrolls']}), cut {lay['cut']}")
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(out / f"{vp}-marketer-{name}-panel.png"))
        page.get_by_test_id("budget-note").scroll_into_view_if_needed()
        page.screenshot(path=str(out / f"{vp}-marketer-{name}-budget.png"))
        back(page)
    page.close()


def rewritten_pass(r: Review, c: Checks, ctx, vp: str, out: Path) -> None:
    """The two verdicts no scripted brief reaches today (ruled_out; not_separable is rare) are drawn from a payload the browser
    rewrites in flight. These checks test only the wording the client puts on a verdict the server would send."""
    page = r.sign_in(ctx, "marketer")
    row = CASES["supported"][1]
    want = {"ruled_out": ("Ruled out: a channel moved and TRx did not follow.", None),
            "not_separable": ("Cannot be separated: from access and the competitor launch, which moved in the same weeks.", ["access", "competitor"]),
            "not_separable_cal": ("Cannot be separated: from the calendar, which moved in the same weeks.", ["holiday"])}
    for name, (line, sep) in want.items():
        def make(verdict: str, sep: list[str] | None):
            def rewrite(route) -> None:
                resp = route.fetch()
                body = resp.json()
                for x in body["sections"]:
                    if x.get("promotion"):
                        x["promotion"].update(verdict=verdict)
                        x["promotion"].pop("effect", None)
                        if sep:
                            x["promotion"]["separable_from"] = sep
                route.fulfill(response=resp, json=body)
            return rewrite
        rewrite = make(name.split("_cal")[0], sep)
        page.route(re.compile(r".*/api/briefing/b-[0-9a-f]+\?view=leadership"), rewrite)
        open_brief(page, row)
        got = page.get_by_test_id("promotion-verdict").first.inner_text()
        c.check(vp, f"rewritten payload {name}: verdict line reads '{line}'", got == line and page.get_by_test_id("promotion-effect").count() == 0, got)
        page.screenshot(path=str(out / f"{vp}-marketer-rewritten-{name}.png"))
        back(page)
        page.unroute(re.compile(r".*/api/briefing/b-[0-9a-f]+\?view=leadership"))
    page.close()


def director_pass(r: Review, c: Checks, ctx, vp: str, out: Path) -> None:
    page = r.sign_in(ctx, "director")
    for name, (_q, row, _v, _e) in CASES.items():
        open_brief(page, row)
        c.check(vp, f"director {name}: no promotion panel and no budget note",
                page.get_by_test_id("promotion-panel").count() == 0 and page.get_by_test_id("budget-note").count() == 0)
        if name == "supported":
            page.screenshot(path=str(out / f"{vp}-director-{name}.png"))
        back(page)
    page.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8772")
    args = ap.parse_args()
    out = ROOT / "local" / "marketer-view"
    out.mkdir(parents=True, exist_ok=True)
    c = Checks()
    print("setting up", flush=True)
    make_briefs(args.base)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp, size in VIEWPORTS.items():
            print(f"{vp}px", flush=True)
            ctx = browser.new_context(viewport=size)
            r = Review(args.base, out / f"review-{vp}", False)
            marketer_pass(r, c, ctx, vp, out)
            ctx.close()
            ctx = browser.new_context(viewport=size)
            rewritten_pass(Review(args.base, out / f"review-{vp}", False), c, ctx, vp, out)
            ctx.close()
            ctx = browser.new_context(viewport=size)
            director_pass(Review(args.base, out / f"review-{vp}", False), c, ctx, vp, out)
            ctx.close()
        browser.close()
    print("ALL PASS" if not c.failed else f"{c.failed} FAILED")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
