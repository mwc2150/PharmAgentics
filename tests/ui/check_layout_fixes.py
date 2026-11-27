"""Layout checks for the UAT findings U-12 (brief page), U-6 and U-5 (390 px), docs/reviews/2026-11-27-uat-review-v1.md.

Drives the LOCAL app (dev sign-in, a built frontend) with Playwright at 390x844 and 1280x800 and prints PASS/FAIL per
assertion; exit code 1 if any fails. Screenshots go to local/layout-fixes/<tag>/ (git-ignored). It reuses the sign-in
and brief helpers of review_walkthrough.py and needs no secret.

  uv run python tests/ui/check_layout_fixes.py --tag after [--base http://127.0.0.1:8771]

Start the app first (see .claude/skills/uat-review/SKILL.md). The scripted engine is used, so no model is needed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_walkthrough import ROOT, Review, sign_off_queue  # noqa: E402

VIEWPORTS = {"390": {"width": 390, "height": 844}, "1280": {"width": 1280, "height": 800}}

# Is the element fully inside the window, and is it the topmost thing at its centre and at its four corners?
VISIBLE_JS = r"""
el => {
  const r = el.getBoundingClientRect();
  const inside = r.top >= 0 && r.left >= 0 && r.bottom <= window.innerHeight && r.right <= window.innerWidth;
  const hit = (x, y) => { const t = document.elementFromPoint(x, y); return !!t && (t === el || el.contains(t)); };
  const pts = [[r.left + r.width / 2, r.top + r.height / 2], [r.left + 8, r.top + 8], [r.right - 8, r.top + 8],
               [r.left + 8, r.bottom - 8], [r.right - 8, r.bottom - 8]];
  return {inside, top: Math.round(r.top), bottom: Math.round(r.bottom), h: window.innerHeight,
          topmost: pts.every(p => hit(p[0], p[1]))};
}
"""
PROMPTS_JS = r"""
() => Array.from(document.querySelectorAll('*')).filter(e => e.children.length === 0 && e.textContent.trim() === 'Was this answer right?')
  .filter(e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; }).length
"""
TABLE_JS = r"""
() => {
  const region = document.querySelector('[role=region][aria-label="Territory figures"]');
  if (!region) return {found: false};
  const scrolls = el => { for (let p = el; p; p = p.parentElement) { const o = getComputedStyle(p).overflowX;
    if ((o === 'auto' || o === 'scroll') && p.scrollWidth > p.clientWidth + 1) return true; } return false; };
  const cells = Array.from(region.querySelectorAll('th, td'));
  const clipped = cells.filter(c => c.scrollWidth > c.clientWidth + 1).map(c => c.innerText.trim());
  // a cell is cut off when its right edge lies beyond the nearest scroll-or-clip ancestor that does not scroll
  const cut = [];
  for (const c of cells) { const cr = c.getBoundingClientRect();
    for (let p = c.parentElement; p; p = p.parentElement) { const o = getComputedStyle(p).overflowX;
      if (o === 'visible') continue; const pr = p.getBoundingClientRect();
      if ((o === 'hidden' || o === 'clip') && cr.right > pr.right + 1) cut.push(c.innerText.trim());
      break; } }
  const t = region.querySelector('table');
  const basisAt = Array.from(region.querySelectorAll('thead th')).findIndex(h => h.innerText.trim().toLowerCase() === 'basis');
  const basis = basisAt < 0 ? [] : Array.from(region.querySelectorAll('tbody tr')).map(r => r.cells[r.cells.length - 1].innerText.trim());
  return {found: true, clipped, cut, basis, regionScrolls: region.scrollWidth > region.clientWidth + 1,
          regionW: region.clientWidth, tableW: t.scrollWidth, winW: window.innerWidth, pageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
          scrollingAncestor: scrolls(region.querySelector('th, td'))};
}
"""
SMALL_JS = r"""
() => Array.from(document.querySelectorAll('button, a[href], [role=tab], select, input, textarea, [role=radio], [role=checkbox]'))
  .filter(e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && !e.closest('.sr-only'); })
  .filter(e => { const r = e.getBoundingClientRect(); return r.width < 24 || r.height < 24; })
  .map(e => { const r = e.getBoundingClientRect(); return (e.getAttribute('aria-label') || e.innerText || e.id || e.tagName).trim().slice(0, 30)
    + ' ' + Math.round(r.width) + 'x' + Math.round(r.height); })
"""
HEADER_JS = r"""
() => {
  const acct = document.querySelector('button[aria-label^="Account"]');
  let nameShown = '';
  if (acct) for (const s of acct.querySelectorAll('span')) { const r = s.getBoundingClientRect(), cs = getComputedStyle(s);
    if (r.width > 0 && cs.display !== 'none' && s.textContent.trim()) nameShown = s.textContent.trim(); }
  const tabs = Array.from(document.querySelectorAll('[role=tab]')).filter(t => t.getBoundingClientRect().width > 0)
    .map(t => { const r = t.getBoundingClientRect(); return {name: t.innerText.trim(), top: Math.round(r.top), h: Math.round(r.height), left: Math.round(r.left), right: Math.round(r.right)}; });
  return {account: acct ? acct.getAttribute('aria-label') : null, nameShown, tabs, winW: window.innerWidth,
          pageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1};
}
"""


PLACE_JS = r"""
el => {  // scroll so the element's bottom edge sits just above the sticky bars (the dock and the follow-up bar)
  const dock = document.querySelector('.pa-dock'); const bar = dock ? dock.parentElement : null;
  const barH = bar ? bar.getBoundingClientRect().height : 0;
  let sc = el.parentElement; while (sc && !(/(auto|scroll)/.test(getComputedStyle(sc).overflowY) && sc.scrollHeight > sc.clientHeight)) sc = sc.parentElement;
  const r = el.getBoundingClientRect(); const target = window.innerHeight - barH - 6;
  if (sc) sc.scrollTop += r.bottom - target;
  return {barH: Math.round(barH), bottomNow: Math.round(el.getBoundingClientRect().bottom), window: window.innerHeight};
}
"""


class Checks:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def check(self, vp: str, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((f"{vp}px {name}", bool(ok), detail))
        print(f"  {'PASS' if ok else 'FAIL'}  {vp}px  {name}" + (f"  [{detail}]" if detail else ""), flush=True)


def shot(page: Page, out: Path, name: str) -> None:
    page.wait_for_timeout(300)
    page.screenshot(path=str(out / f"{name}.png"))


def analyst_pass(r: Review, c: Checks, ctx, vp: str, out: Path, territory: str) -> None:
    page = r.sign_in(ctx, "analyst")
    # U-5 / U-6 on the Weekly briefing and the form (the Overview, its own workspace since 2026-11-27, is the landing)
    r.to_nav(page, "Weekly briefing")
    h = page.evaluate(HEADER_JS)
    first = "Ace"
    c.check(vp, "account button shows the first name", first in h["nameShown"], f"visible text '{h['nameShown']}', label '{h['account']}'")
    approved = [t for t in h["tabs"] if t["name"].startswith("Your")]
    others = [t for t in h["tabs"] if not t["name"].startswith("Your")]
    one_line = bool(approved) and all(t["h"] == approved[0]["h"] for t in others) and all(t["top"] == approved[0]["top"] for t in others)
    c.check(vp, "Your briefings tab on one line, in the row of its sibling tabs", one_line, f"tabs {[(t['name'], t['top'], t['h']) for t in h['tabs']]}")
    c.check(vp, "no horizontal page overflow on the landing", not h["pageOverflow"])
    small = page.evaluate(SMALL_JS)
    if vp == "390": c.check(vp, "landing: every control at least 24x24", not small, "; ".join(small))
    shot(page, out, f"{vp}-landing")
    page.get_by_role("tab", name="New briefing").click()
    page.wait_for_timeout(900)
    small = page.evaluate(SMALL_JS)
    if vp == "390": c.check(vp, "New briefing form: every control at least 24x24", not small, "; ".join(small))
    shot(page, out, f"{vp}-new-briefing")

    r.generate_brief(page, territory)
    shot(page, out, f"{vp}-brief")
    # U-12: one vote prompt at a time, also once a follow-up exists (asked first: the open thread is what makes the bars tall)
    before = page.evaluate(PROMPTS_JS)
    c.check(vp, "before a follow-up: at most one 'Was this answer right?' on screen", before <= 1, f"{before} shown")
    region = page.get_by_role("region", name="Follow-up questions")
    chip = region.get_by_role("button", name=re.compile(r"\?$")).first
    chip.click()
    page.wait_for_timeout(2500)
    after = page.evaluate(PROMPTS_JS)
    c.check(vp, "after a follow-up: at most one 'Was this answer right?' on screen", after <= 1, f"{after} shown")
    shot(page, out, f"{vp}-followup")
    # the one that remains must be usable: vote on it, and the page-level one may then return
    if after == 1:
        bars = page.evaluate("() => { const d = document.querySelector('.pa-dock'); const b = d && d.parentElement; return b ? Math.round(b.getBoundingClientRect().height) : 0 }")
        print(f"       (floating bars are {bars} px tall of {page.viewport_size['height']})")
    # U-12: the reject box must be seen whole and be the topmost thing under its own points
    reject = page.get_by_role("button", name=re.compile(r"^Reject…"))
    placed = reject.evaluate(PLACE_JS)  # the reader has scrolled to Reject… with the bars below it
    page.wait_for_timeout(300)
    try:
        reject.click(timeout=4000)  # Playwright refuses a covered target
        c.check(vp, "Reject… can be clicked from where the reader scrolled to it", True)
    except Exception as exc:  # noqa: BLE001
        c.check(vp, "Reject… can be clicked from where the reader scrolled to it", False, str(exc).splitlines()[0][:100])
        reject.evaluate("el => el.click()")  # carry on, to see where the box lands
    page.wait_for_timeout(900)
    box = page.get_by_role("textbox", name=re.compile(r"^Reason for rejecting"))
    confirm = page.get_by_role("button", name="Reject briefing")
    print(f"       (Reject… placed with its bottom at {placed['bottomNow']} of {placed['window']} px, bars {placed['barH']} px)")
    for label, loc in (("reason textbox", box), ("Reject briefing button", confirm)):
        v = loc.evaluate(VISIBLE_JS)
        c.check(vp, f"{label} fully inside the window", v["inside"], f"top {v['top']}, bottom {v['bottom']}, window {v['h']}")
        c.check(vp, f"{label} is topmost at its centre and corners", v["topmost"])
    shot(page, out, f"{vp}-reject-open")
    box.fill("Layout check: the reason box must be reachable.")
    try:
        confirm.click(timeout=4000)  # Playwright refuses a covered target
        page.get_by_text(re.compile(r"^Rejected ")).first.wait_for(timeout=8000)
        c.check(vp, "Reject briefing can be clicked and takes effect", True)
        c.check(vp, "the floating bars are back after the reason box closes", not page.evaluate("() => document.documentElement.hasAttribute('data-bars-parked')"))
    except Exception as exc:  # noqa: BLE001
        c.check(vp, "Reject briefing can be clicked and takes effect", False, str(exc).splitlines()[0][:100])
        confirm.evaluate("el => el.click()")  # carry on, so the Director pass has a brief to read
        page.wait_for_timeout(1000)
    # the reviewer's send-for-sign-off for the Director pass (a rejected brief can still be sent)
    page.get_by_role("button", name="Send for sign-off").evaluate("el => el.click()")  # not a check: only sets up the Director pass
    page.wait_for_timeout(1200)


def director_pass(r: Review, c: Checks, ctx, vp: str, out: Path, base: str) -> None:
    sign_off_queue(base)
    page = r.sign_in(ctx, "director")
    page.get_by_role("button", name=re.compile(r"^BXA · ")).first.click()
    page.get_by_role("article").wait_for(timeout=15000)
    page.wait_for_timeout(800)
    page.get_by_role("region", name="Territory figures").scroll_into_view_if_needed()
    t = page.evaluate(TABLE_JS)
    c.check(vp, "leadership summary has a territory table", t["found"])
    if t["found"]:
        c.check(vp, "no territory-table cell is clipped (scrollWidth > clientWidth) or cut off by a hidden edge", not t["clipped"] and not t["cut"],
                f"clipped {t['clipped']}, cut {t['cut']}")
        c.check(vp, "territory table needs no sideways scrolling (all text readable at once)", not t["regionScrolls"],
                f"region {t['regionW']}px, table {t['tableW']}px")
        c.check(vp, "Basis cells fully readable", bool(t["basis"]) and all(re.fullmatch(r"[A-Za-z—-]+", b or "") for b in t["basis"]), f"{t['basis']}")
        c.check(vp, "no horizontal page overflow on the summary", not t["pageOverflow"])
    shot(page, out, f"{vp}-director-summary")
    h = page.evaluate(HEADER_JS)
    c.check(vp, "director: account button shows the first name", "Diana" in h["nameShown"], f"'{h['nameShown']}'")


def landing_pass(r: Review, c: Checks, ctx, vp: str, out: Path, who: str) -> None:
    page = r.sign_in(ctx, who)
    page.wait_for_timeout(1200)
    h = page.evaluate(HEADER_JS)
    first = {"director": "Diana", "forecast-analyst": "Ace", "forecast-manager": "Miranda", "tester": "Tester"}[who]
    c.check(vp, f"{who}: account button shows the first name", first in h["nameShown"], f"'{h['nameShown']}'")
    small = page.evaluate(SMALL_JS)
    if vp == "390":
        c.check(vp, f"{who}: landing: every control at least 24x24", not small, "; ".join(small))
    c.check(vp, f"{who}: no horizontal page overflow on the landing", not h["pageOverflow"])
    shot(page, out, f"{vp}-landing-{who}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default="http://127.0.0.1:8771")
    ap.add_argument("--tag", default="after")
    ap.add_argument("--viewports", default="390,1280")
    args = ap.parse_args()
    out = ROOT / "local" / "layout-fixes" / args.tag
    out.mkdir(parents=True, exist_ok=True)
    c = Checks()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp in args.viewports.split(","):
            print(f"-- {vp} px", flush=True)
            r = Review(args.base, out, False)
            opts = dict(viewport=VIEWPORTS[vp], timezone_id="America/New_York", locale="en-US")
            if vp == "390":
                opts.update(device_scale_factor=2, has_touch=True)
            # a brief and its thread persist per (brand, territory, week): one territory per viewport, and a fresh state
            # folder per run, so a rejected or answered brief from an earlier pass does not change this one
            terr = {"390": "Southeast", "1280": "Mountain"}[vp]
            jobs = [("analyst", lambda ctx: analyst_pass(r, c, ctx, vp, out, terr)),
                    ("director", lambda ctx: director_pass(r, c, ctx, vp, out, args.base))]
            jobs += [(w, (lambda w: lambda ctx: landing_pass(r, c, ctx, vp, out, w))(w)) for w in ("forecast-analyst", "forecast-manager", "tester")]
            for who, fn in jobs:
                ctx = browser.new_context(**opts)
                try:
                    fn(ctx)
                except Exception as exc:  # noqa: BLE001
                    c.check(vp, f"{who} pass ran to the end", False, f"{type(exc).__name__}: {str(exc).splitlines()[0][:160]}")
                finally:
                    ctx.close()
        browser.close()
    failed = [x for x in c.results if not x[1]]
    print(f"\n{len(c.results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
