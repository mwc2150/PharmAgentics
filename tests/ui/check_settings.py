"""Settings and light theme check (2026-11-27): drives the LOCAL app (dev sign-in, a built frontend) with Playwright.

  uv run python tests/ui/check_settings.py [--base http://127.0.0.1:8765] [--out local/settings-check]

Start the app first (dev sign-in, PHARMAGENTICS_STATIC_DIR pointing at the build). It asserts what the Settings workspace
promises (the gear, the theme and its persistence, no flash, the New briefing defaults for the analyst only, the date
style, the evidence footnotes, density, reduced motion, storage that throws), takes light and dark screenshots of the
main screens at 1280x800 and 390x844 into <out>/ (git-ignored), and measures text contrast on every screen in both themes
with a small in-page scan (no axe in this repo). Results go to <out>/results.json; the exit code is 1 if an assertion fails.
Nothing here changes the hosted app or needs a secret.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_walkthrough import PERSONAS  # noqa: E402  (sign-in names, shared with the UAT walkthrough)

ROOT = Path(__file__).resolve().parents[2]
RESULTS: list[dict] = []
CONTRAST: list[dict] = []
SHOTS: list[str] = []
DESKTOP = {"width": 1280, "height": 800}
PHONE = {"width": 390, "height": 844}


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append({"assertion": name, "ok": bool(ok), "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""), flush=True)
    return bool(ok)


def sign_in(ctx: BrowserContext, base: str, who: str) -> Page:
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(f"{base}/auth/login")
    page.get_by_role("button", name=PERSONAS[who][1], exact=True).click()
    page.get_by_role("heading", level=1).first.wait_for(timeout=20000)
    page.wait_for_timeout(1200)
    return page


def new_ctx(browser, viewport: dict, theme: str | None = None, scheme: str = "dark", extra_init: str | None = None) -> BrowserContext:
    """A fresh browser profile. `theme` pre-saves the Settings choice (what a person who picked it would have)."""
    ctx = browser.new_context(viewport=viewport, color_scheme=scheme, reduced_motion="no-preference")
    if theme:
        ctx.add_init_script(f"try{{ if(!localStorage.getItem('pa-settings')) localStorage.setItem('pa-settings', JSON.stringify({{theme:'{theme}'}})) }}catch(e){{}}")
    if extra_init:
        ctx.add_init_script(extra_init)
    return ctx


def attr(page: Page, name: str) -> str | None:
    return page.evaluate("n => document.documentElement.getAttribute(n)", name)


def saved(page: Page) -> dict:
    return page.evaluate("() => { try { return JSON.parse(localStorage.getItem('pa-settings') || '{}') } catch (e) { return null } }") or {}


def open_settings(page: Page) -> None:
    page.get_by_role("button", name=re.compile(r"^Settings")).click()  # the gear sits at the bottom of the sidebar, outside the Workspaces list
    page.get_by_role("heading", name="Appearance", level=2).wait_for(timeout=10000)
    page.wait_for_timeout(500)


def choose(page: Page, group: str, label: str) -> None:
    page.get_by_role("group", name=group).get_by_text(label, exact=True).click()
    page.wait_for_timeout(250)


def to_lane(page: Page, name: str) -> None:
    page.get_by_role("navigation", name="Workspaces").get_by_role("button", name=re.compile(f"^{name}")).click()
    page.wait_for_timeout(1500)


# ---- contrast ---------------------------------------------------------------------------------------------------
CONTRAST_JS = r"""
() => {
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const g = cv.getContext('2d', {willReadFrequently: true});
  const rgba = css => { g.clearRect(0,0,1,1); g.fillStyle = '#000'; g.fillStyle = css; g.fillRect(0,0,1,1);
    const d = g.getImageData(0,0,1,1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (f, b) => { const a = f[3]; return [f[0]*a + b[0]*(1-a), f[1]*a + b[1]*(1-a), f[2]*a + b[2]*(1-a), 1]; };
  const lin = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const L = c => 0.2126*lin(c[0]) + 0.7152*lin(c[1]) + 0.0722*lin(c[2]);
  const ratio = (a, b) => { const x = L(a), y = L(b); return (Math.max(x,y) + 0.05) / (Math.min(x,y) + 0.05); };
  const page = rgba(getComputedStyle(document.documentElement).colorScheme.includes('light') ? '#ffffff' : '#000000');
  const bgOf = el => { const chain = []; for (let e = el; e; e = e.parentElement) chain.push(e);
    let base = rgba(getComputedStyle(document.body).backgroundColor); if (base[3] < 1) base = over(base, page);
    let unknown = false;
    for (const e of chain.reverse()) { const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') unknown = true;
      const c = rgba(cs.backgroundColor); if (c[3] > 0) base = over(c, base); }
    return {bg: base, unknown}; };
  const opacityOf = el => { let o = 1; for (let e = el; e; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity); return o; };
  const out = [], seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const t = n.textContent.trim(); if (!t) continue;
    const el = n.parentElement; if (!el || seen.has(el)) continue; seen.add(el);
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || cs.visibility === 'hidden' || cs.display === 'none') continue;
    if (el.closest('[hidden], [inert], .sr-only, script, style, option, [disabled], [aria-disabled="true"]')) continue;
    if (r.bottom < 0 || r.right < 0) continue;
    const {bg, unknown} = bgOf(el);
    let fg = rgba(cs.color); const op = opacityOf(el); fg[3] *= op; fg = over(fg, bg);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    const need = large ? 3 : 4.5, got = ratio(fg, bg);
    if (got < need) out.push({text: t.slice(0, 50), ratio: Math.round(got * 100) / 100, need, size, unknown,
      tag: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0, 3).join('.') : '')});
  }
  return out;
}
"""


def scan_contrast(page: Page, theme: str, viewport: str, screen: str) -> int:
    found = page.evaluate(CONTRAST_JS)
    for f in found:
        CONTRAST.append({"theme": theme, "viewport": viewport, "screen": screen, **f})
    return len(found)


def snap(page: Page, out: Path, theme: str, vp: str, name: str, full: bool = False) -> None:
    page.wait_for_timeout(700)
    path = out / f"{theme}-{vp}-{name}.png"
    page.screenshot(path=str(path), full_page=False)  # the app scrolls inside its own region, so the viewport is the picture
    SHOTS.append(path.name)
    scan_contrast(page, theme, vp, name)


# ---- the assertions ---------------------------------------------------------------------------------------------
def assertions(browser, base: str) -> None:
    # 1. Defaults, no flash, persistence --------------------------------------------------------------------------
    flash = """
      (() => { const seq = []; window.__themeSeq = seq; window.__atDcl = null;
        const note = () => { const v = document.documentElement && document.documentElement.getAttribute('data-theme');
          if (v && seq[seq.length - 1] !== v) seq.push(v); };
        // the document has no root element yet when this runs, so watch the document itself
        new MutationObserver(note).observe(document, {attributes: true, subtree: true, attributeFilter: ['data-theme']});
        document.addEventListener('DOMContentLoaded', () => { note(); window.__atDcl = document.documentElement.getAttribute('data-theme'); }); })();
    """
    ctx = new_ctx(browser, DESKTOP, extra_init=flash)
    page = sign_in(ctx, base, "analyst")
    check("default theme with nothing saved is dark (build default)", attr(page, "data-theme") == "dark", f"data-theme={attr(page, 'data-theme')}")
    check("colour-scheme follows the theme", page.evaluate("document.documentElement.style.colorScheme") == "dark")

    # 2. the gear: collapsed, expanded, then the sections
    nav = page.get_by_role("navigation", name="Workspaces")
    gear = page.get_by_role("button", name=re.compile(r"^Settings"))
    check("gear is in the collapsed rail, below the workspace items", gear.is_visible() and
          gear.bounding_box()["y"] > nav.get_by_role("button", name=re.compile("^Evaluation")).bounding_box()["y"])
    gear.click()
    page.get_by_role("heading", name="Appearance", level=2).wait_for()
    check("analyst: gear opens Settings (collapsed rail)", page.get_by_role("heading", level=1).first.inner_text() == "Settings"
          and page.title().startswith("Settings"), page.title())
    page.keyboard.press("Control+b")
    page.wait_for_timeout(500)
    check("gear shows its label when the sidebar is expanded", page.get_by_role("complementary", name="Sidebar").get_by_text("Settings", exact=True).is_visible())
    check("gear is the current page in the nav", page.get_by_role("button", name=re.compile("^Settings")).get_attribute("aria-current") == "page")
    page.keyboard.press("Control+b")

    # 3. theme choices set data-theme and persist across reload
    for label, want in (("Light", "light"), ("Dark", "dark")):
        choose(page, "Theme", label)
        page.reload(); page.get_by_role("heading", level=1).first.wait_for(); page.wait_for_timeout(600)
        check(f"theme {label}: data-theme={want} and saved in localStorage after reload",
              attr(page, "data-theme") == want and saved(page).get("theme") == want, f"attr={attr(page, 'data-theme')} saved={saved(page).get('theme')}")
        open_settings(page)
    choose(page, "Theme", "Light")
    page.reload(); page.get_by_role("heading", level=1).first.wait_for()
    seq = page.evaluate("window.__themeSeq"); dcl = page.evaluate("window.__atDcl")
    first_paint = page.evaluate("(performance.getEntriesByType('paint').find(p => p.name === 'first-paint') || {startTime: null}).startTime")
    check("no flash: data-theme set before DOMContentLoaded and never flips during load", dcl == "light" and seq == ["light"], f"atDCL={dcl} sequence={seq} firstPaint={first_paint}")
    open_settings(page)
    choose(page, "Theme", "Match system")
    page.emulate_media(color_scheme="light"); page.wait_for_timeout(400)
    a = attr(page, "data-theme")
    page.emulate_media(color_scheme="dark"); page.wait_for_timeout(400)
    b = attr(page, "data-theme")
    check("Match system follows prefers-color-scheme live (light then dark)", (a, b) == ("light", "dark") and saved(page).get("theme") == "system", f"{a},{b}")
    toast_theme = lambda: toast_theme_of(page)
    check("toasts follow the app theme (dark)", toast_theme() == "dark", f"data-sonner-theme={toast_theme()}")
    choose(page, "Theme", "Light")
    check("toasts follow the app theme (light)", toast_theme() == "light", f"data-sonner-theme={toast_theme()}")
    choose(page, "Theme", "Dark")

    # 4. New briefing defaults: analyst only, and they set the form after a reload
    check("analyst sees New briefing defaults", page.get_by_role("heading", name="New briefing defaults", level=2).is_visible())
    brand_select = page.get_by_label("Default brand")
    options = brand_select.locator("option").all_inner_texts()
    values = brand_select.locator("option").evaluate_all("els => els.map(e => e.value)")
    other = [v for v in values if v != values[0]][:1]
    check("default brand lists the brands the API lists for this user", len(values) >= 2, str(options))
    if other:
        brand_select.select_option(other[0])
        page.reload(); page.get_by_role("heading", level=1).first.wait_for(); page.wait_for_timeout(800)
        page.get_by_role("tab", name="New briefing").click(); page.wait_for_timeout(800)
        form_brand = page.locator("form label", has_text="Brand").locator("select").first.input_value()
        check("default brand sets the New briefing form's initial brand after reload", form_brand == other[0], f"form={form_brand} want={other[0]}")
        overview_brand = page.get_by_role("tab", name="Overview")
        page.get_by_role("tab", name="Overview").click(); page.wait_for_timeout(800)
        ov = page.locator("select").first.input_value()
        check("default brand does not change the Overview's own brand", ov == values[0], f"overview={ov} first={values[0]}")
    open_settings(page)
    page.get_by_label("Default brand").select_option(values[0])
    page.wait_for_timeout(200)
    engine_group = page.get_by_role("group", name="Default engine")
    agent_offered = engine_group.get_by_text("Agent team", exact=True).count() > 0
    check("default engine offers Agent team only for a brand whose engines include agent", agent_offered, f"first brand {values[0]}")
    if other:
        page.get_by_label("Default brand").select_option(other[0])
        offered_other = page.get_by_role("group", name="Default engine").get_by_text("Agent team", exact=True).count() > 0
        engines = page.evaluate("fetch('/api/briefing/context').then(r => r.json()).then(c => Object.fromEntries(c.brands.map(b => [b.id, b.engines])))")
        check("agent option follows each brand's engines", offered_other == ("agent" in engines.get(other[0], [])), json.dumps(engines))
        page.get_by_label("Default brand").select_option(values[0])
    if agent_offered:
        choose(page, "Default engine", "Agent team")
        page.reload(); page.get_by_role("heading", level=1).first.wait_for(); page.wait_for_timeout(800)
        page.get_by_role("tab", name="New briefing").click(); page.wait_for_timeout(800)
        radio = page.get_by_role("radio", name=re.compile(r"^Agent team"))
        check("default engine Agent team is the form's initial engine after reload", radio.is_checked())
        open_settings(page)
        choose(page, "Default engine", "Scripted")
    ctx.close()

    # 5. other roles: gear works, no briefing defaults
    for who in ("director", "forecast-analyst"):
        ctx = new_ctx(browser, DESKTOP)
        page = sign_in(ctx, base, who)
        open_settings(page)
        check(f"{who}: gear opens Settings", page.get_by_role("heading", level=1).first.inner_text() == "Settings")
        check(f"{who}: no New briefing defaults", page.get_by_role("heading", name="New briefing defaults").count() == 0)
        check(f"{who}: Appearance, Reading and About are there", all(page.get_by_role("heading", name=h, level=2).count() == 1 for h in ("Appearance", "Reading", "About")))
        about = page.get_by_test_id("about-version").inner_text()
        check(f"{who}: About shows the app version and release weeks", bool(about) and bool(re.search(r"\d{4}", page.get_by_test_id("about-weeks").inner_text())), f"version={about}")
        if who == "director":
            check("director: About shows the data version", bool(re.search(r"\w", page.get_by_test_id("about-data-version").inner_text())) and page.get_by_test_id("about-data-version").inner_text() not in ("Loading…", "Unavailable"),
                  page.get_by_test_id("about-data-version").inner_text())
        check(f"{who}: About lists keyboard shortcuts", page.get_by_text("Collapse or expand the sidebar").is_visible())
        choose(page, "Theme", "Light")
        check(f"{who}: choosing Light sets data-theme", attr(page, "data-theme") == "light")
        ctx.close()
    ctx = new_ctx(browser, DESKTOP)
    page = sign_in(ctx, base, "tester")
    open_settings(page)
    check("tester (analyst view): New briefing defaults are shown", page.get_by_role("heading", name="New briefing defaults", level=2).is_visible())
    ctx.close()

    # 6. date style, footnotes, density, reduced motion
    ctx = new_ctx(browser, DESKTOP)
    page = sign_in(ctx, base, "analyst")
    greeting = lambda: page.locator("p", has_text=re.compile(r"across \d+ territories, week of")).first.inner_text()
    before = greeting()
    open_settings(page)
    choose(page, "Date style", "2026-10-05")
    about_weeks = page.get_by_test_id("about-weeks").inner_text()
    page.get_by_role("navigation", name="Workspaces").get_by_role("button", name=re.compile("^Weekly briefing")).click(); page.wait_for_timeout(900)
    after = greeting()
    check("date style: long form by default", bool(re.search(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", before)), before)
    check("date style: ISO changes a visible week label", bool(re.search(r"\d{4}-\d{2}-\d{2}", after)) and after != before, after)
    check("date style: About release weeks follow it", bool(re.search(r"\d{4}-\d{2}-\d{2} to \d{4}-\d{2}-\d{2}", about_weeks)), about_weeks)
    page.reload(); page.get_by_role("heading", level=1).first.wait_for(); page.wait_for_timeout(900)
    check("date style persists across reload", bool(re.search(r"\d{4}-\d{2}-\d{2}", greeting())), greeting())
    open_settings(page); choose(page, "Date style", "Oct 5, 2026")

    # footnotes: make a brief, then flip the setting
    page.get_by_role("navigation", name="Workspaces").get_by_role("button", name=re.compile("^Weekly briefing")).click(); page.wait_for_timeout(900)
    generate_brief(page)
    fn = lambda: page.evaluate("() => { const e = [...document.querySelectorAll('.pa-fn')].filter(x => x.closest('[hidden]') === null); return {n: e.length, shown: e.filter(x => getComputedStyle(x).display !== 'none').length} }")
    f1 = fn()
    check("footnotes shown by default: the superscripts are visible in the analyst brief", f1["n"] > 0 and f1["shown"] == f1["n"], str(f1))
    page.get_by_role("button", name=re.compile("^Settings")).click()
    page.get_by_role("heading", name="Appearance", level=2).wait_for()
    choose(page, "Evidence footnote numbers", "Hide")
    allfn = page.evaluate("() => { const e = [...document.querySelectorAll('.pa-fn')]; return {n: e.length, shown: e.filter(x => getComputedStyle(x).display !== 'none').length} }")
    check("footnotes Hide: every superscript is display:none", allfn["n"] > 0 and allfn["shown"] == 0, str(allfn))
    btn = page.evaluate("() => { const b = [...document.querySelectorAll('button')].filter(x => x.querySelector('.pa-fn')); return {n: b.length, named: b.filter(x => /evidence \\d+/.test(x.getAttribute('aria-label') || '')).length, tab: b.filter(x => x.tabIndex >= 0 && !x.disabled).length} }")
    check("footnotes Hide: the claim buttons stay focusable and named 'value, evidence N'", btn["n"] > 0 and btn["named"] == btn["n"] and btn["tab"] == btn["n"], str(btn))
    check("footnotes setting persists", saved(page).get("footnotes") == "hide")
    choose(page, "Evidence footnote numbers", "Show")

    choose(page, "Density", "Compact")
    pad = lambda: page.evaluate("() => { const e = [...document.querySelectorAll('section.pa-panel')].find(x => x.getClientRects().length); return e ? parseFloat(getComputedStyle(e).paddingTop) : null }")
    check("density Compact sets html[data-density] and tightens panel padding", attr(page, "data-density") == "compact" and (pad() or 99) < 20, f"padding={pad()}")
    choose(page, "Density", "Comfortable")
    check("density Comfortable restores the padding", attr(page, "data-density") == "comfortable" and (pad() or 0) >= 20, f"padding={pad()}")

    choose(page, "Reduce motion", "On")
    anim = page.evaluate("() => { const e = document.querySelector('.pa-stagger > *'); return e ? getComputedStyle(e).animationName : 'none' }")
    check("reduce motion On sets html[data-motion=on] and stops animations", attr(page, "data-motion") == "on" and anim == "none", f"animation={anim}")
    choose(page, "Reduce motion", "Off")
    check("reduce motion Off sets html[data-motion=off]", attr(page, "data-motion") == "off")
    choose(page, "Reduce motion", "Follow system")
    check("reduce motion Follow system", attr(page, "data-motion") == "system")
    page.reload(); page.get_by_role("heading", level=1).first.wait_for()
    check("density and motion attributes are applied before first paint after reload", attr(page, "data-density") == "comfortable" and attr(page, "data-motion") == "system")
    ctx.close()
    # reduced motion from the system
    ctx = browser.new_context(viewport=DESKTOP, reduced_motion="reduce")
    page = sign_in(ctx, base, "analyst")
    anim = page.evaluate("() => { const e = document.querySelector('.pa-stagger > *'); return e ? getComputedStyle(e).animationName : 'none' }")
    check("Follow system honours prefers-reduced-motion: reduce", anim == "none", f"animation={anim}")
    ctx.close()

    # 7. storage that throws: the app still loads, with the default theme
    ctx = new_ctx(browser, DESKTOP, extra_init="Object.defineProperty(window, 'localStorage', {get() { throw new Error('blocked') }})")
    errs: list[str] = []
    page = ctx.new_page(); page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(f"{base}/auth/login"); page.get_by_role("button", name=PERSONAS["analyst"][1], exact=True).click()
    page.get_by_role("heading", level=1).first.wait_for(timeout=20000)
    open_settings(page); choose(page, "Theme", "Light")
    check("storage blocked: the app loads, the choice still applies for the page view, and nothing throws",
          attr(page, "data-theme") == "light" and not errs, "; ".join(errs)[:200])
    ctx.close()

    # 8. phone: the gear is in the mobile nav
    ctx = new_ctx(browser, PHONE)
    page = sign_in(ctx, base, "analyst")
    page.get_by_role("button", name="Expand the sidebar").click()
    dlg = page.get_by_role("dialog", name="Navigation")
    dlg.wait_for()
    dlg.get_by_role("button", name=re.compile("^Settings")).click()
    page.get_by_role("heading", name="Appearance", level=2).wait_for()
    check("phone: the gear in the navigation drawer opens Settings and closes the drawer", page.get_by_role("dialog").count() == 0 and page.get_by_role("heading", level=1).first.inner_text() == "Settings")
    check("phone: no horizontal scroll on Settings", not page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"))
    ctx.close()


def toast_theme_of(page: Page) -> str | None:
    """Sends a suggestion (to the local test state) so a toast shows, and reads the theme sonner drew it with."""
    page.get_by_role("button", name=re.compile(r"^Account:")).click()
    page.get_by_role("menuitem", name="Suggest an improvement").click()
    page.get_by_role("textbox", name="Your suggestion").fill("Settings check: toast colour")
    page.get_by_role("button", name="Send", exact=True).click()
    page.locator("[data-sonner-toaster]").first.wait_for(state="attached", timeout=8000)
    theme = page.evaluate("() => document.querySelector('[data-sonner-toaster]')?.getAttribute('data-sonner-theme')")
    page.wait_for_timeout(300)
    return theme


def generate_brief(page: Page, territory: str = "Southeast") -> None:
    page.get_by_role("tab", name="New briefing").click()
    page.wait_for_timeout(800)
    page.get_by_role("combobox", name="Territory").select_option(label=territory)
    page.get_by_role("button", name="Generate briefing").click()
    page.get_by_role("heading", name="What should this brief investigate?").wait_for(timeout=30000)
    page.get_by_role("button", name="Approve plan and investigate").click()
    page.get_by_role("group", name="View").wait_for(timeout=60000)
    page.wait_for_timeout(800)


# ---- the screenshots --------------------------------------------------------------------------------------------
def screens(browser, base: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        for vp, size in (("1280x800", DESKTOP), ("390x844", PHONE)):
            print(f"-- screenshots: {theme} {vp}", flush=True)
            ctx = new_ctx(browser, size, theme=theme, scheme="dark" if theme == "dark" else "light")
            page = sign_in(ctx, base, "analyst")
            snap(page, out, theme, vp, "overview")
            page.get_by_role("tab", name="New briefing").click(); page.wait_for_timeout(900)
            snap(page, out, theme, vp, "new-briefing-form")
            generate_brief(page)
            snap(page, out, theme, vp, "analyst-brief")
            page.get_by_role("button", name="Leadership preview").click(); page.wait_for_timeout(1000)
            snap(page, out, theme, vp, "leadership-brief")
            page.get_by_role("button", name="Analyst view").click()
            if vp == "390x844":
                page.get_by_role("button", name="Expand the sidebar").click(); page.wait_for_timeout(500)
                page.get_by_role("dialog", name="Navigation").get_by_role("button", name=re.compile("^Evaluation")).click()
            else:
                to_lane(page, "Evaluation")
            page.wait_for_timeout(2500)
            snap(page, out, theme, vp, "evaluation")
            if vp == "390x844":
                page.get_by_role("button", name="Expand the sidebar").click(); page.wait_for_timeout(500)
                page.get_by_role("dialog", name="Navigation").get_by_role("button", name=re.compile("^Settings")).click()
            else:
                open_settings(page)
            page.wait_for_timeout(800)
            snap(page, out, theme, vp, "settings")
            ctx.close()
            ctx = new_ctx(browser, size, theme=theme, scheme="dark" if theme == "dark" else "light")
            page = sign_in(ctx, base, "forecast-analyst")
            page.wait_for_timeout(1500)
            snap(page, out, theme, vp, "forecast-landing")
            ctx.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--out", default=str(ROOT / "local" / "settings-check"))
    ap.add_argument("--skip-screens", action="store_true")
    ap.add_argument("--skip-asserts", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            if not args.skip_asserts:
                assertions(browser, args.base)
            if not args.skip_screens:
                screens(browser, args.base, out)
        finally:
            browser.close()
    summary: dict[str, dict] = {}
    for c in CONTRAST:
        key = f"{c['theme']} {c['viewport']}"
        summary.setdefault(key, {}).setdefault(c["screen"], 0)
        summary[key][c["screen"]] += 1
    (out / "results.json").write_text(json.dumps({"assertions": RESULTS, "screenshots": SHOTS, "contrast_failures": CONTRAST, "contrast_summary": summary}, indent=1), encoding="utf-8")
    failed = [r for r in RESULTS if not r["ok"]]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} assertions passed; {len(SHOTS)} screenshots; contrast failures by screen: {json.dumps(summary)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
