"""Mechanical capture for the uat-review skill (.claude/skills/uat-review/SKILL.md).

Drives the LOCAL app (dev sign-in, a built frontend) as every role with Playwright, and writes under
local/reviews/<date>-<label>/ (git-ignored): numbered screenshots, aria snapshots of the key screens, console
messages, failed and 4xx/5xx requests, the app origin's response headers, the briefs the run generated, and one
observations.json index with mechanical flags for the reviewer to judge. It needs no secret and never touches
the hosted app.

  uv run python tests/ui/review_walkthrough.py --label v1 [--base http://127.0.0.1:8765] [--date 2026-11-27]

Start the app first (see the skill). Pages are located by accessible role and name. A step that fails is
recorded as a run error and the walkthrough goes on. Playwright needs `uv run playwright install chromium` once.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import BrowserContext, Page, TimeoutError as PWTimeout, sync_playwright

ROOT = Path(__file__).resolve().parents[2]

# role -> (dev sign-in user, accessible name of its button on /auth/login). Names follow roles.json and auth.DEV_USERS.
PERSONAS = {
    "analyst": ("dev-analyst", "Ace briefing-analyst, brand-bxa, brand-bxc"),
    "director": ("dev-director", "Diana briefing-director, brand-bxa, brand-bxc"),
    "forecast-analyst": ("dev-forecast-analyst", "Ace forecast-analyst, brand-bxa"),
    "forecast-manager": ("dev-forecast-manager", "Miranda forecast-manager, brand-bxa"),
    "tester": ("dev-tester", "Tester tester, brand-bxa, brand-bxc"),
}
HEADERS_WANTED = {
    "content-security-policy": "CSP",
    "strict-transport-security": "HSTS",
    "x-frame-options": "X-Frame-Options (or CSP frame-ancestors)",
    "x-content-type-options": "nosniff",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
}

RAW_CODE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,}\b")
ISO_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
LONG_FLOAT = re.compile(r"(?<![\d.])\d+\.\d{5,}\b")
VENDOR = re.compile(r"\b(Gemma|Qwen|Claude|Haiku|Anthropic|Ollama|Gemini|OpenAI|GPT-?\d|Llama|Mistral|MLflow|RAGAS)\b")
MOJIBAKE = re.compile("�|Ã.|â€")
SQL = re.compile(r"\bselect\b[^.]{0,200}\bfrom\b\s+\w+\.\w+", re.I)

SCAN_JS = r"""
() => {
  const q = (s, r = document) => Array.from(r.querySelectorAll(s));
  const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const name = el => (el.getAttribute('aria-label') || el.innerText || el.textContent || el.getAttribute('title') || '').trim();
  const sups = q('sup').filter(vis).map(s => {
    const prev = s.previousSibling ? (s.previousSibling.textContent || '') : '';
    const host = s.closest('button, a, p, li, dd, td') || s.parentElement;
    return {sup: s.textContent.trim(), prev: prev.slice(-12), joined: (host ? host.innerText : '').slice(0, 80),
            hidden_label: !!(s.getAttribute('aria-hidden') === 'true' || s.querySelector('.sr-only'))};
  });
  const selects = q('select').filter(vis).map(s => ({label: s.getAttribute('aria-label') ||
    (s.labels && s.labels[0] ? s.labels[0].innerText.split(/\r?\n/)[0] : '') || s.name || '', options: s.options.length}));
  const tabs = q('[role=tab]').filter(vis).map(t => ({name: name(t), selected: t.getAttribute('aria-selected') === 'true',
    disabled: t.disabled || t.getAttribute('aria-disabled') === 'true'}));
  const unnamed = q('button, a[href], [role=button]').filter(vis).filter(e => !name(e)).map(e => e.outerHTML.slice(0, 120));
  const emptyHeadings = q('h1,h2,h3,h4,h5,h6').filter(vis).filter(h => !h.innerText.trim()).length;
  const imgs = q('img, svg[role=img]').filter(vis).filter(i => !(i.getAttribute('alt') !== null || i.getAttribute('aria-label')
    || (i.querySelector && i.querySelector('title')))).map(i => i.outerHTML.slice(0, 100));
  const blocks = q('p, li, dd, td').filter(vis).map(e => e.innerText.trim()).filter(t => t.length > 30);
  const small = q('button, a[href], [role=tab], select, input').filter(vis).filter(e => {
    const r = e.getBoundingClientRect(); return r.width < 24 || r.height < 24; }).length;
  const acct = document.querySelector('button[aria-label^="Account"]');
  return {text: document.body.innerText, sups, selects, tabs, unnamed, emptyHeadings, imgs, blocks, small,
          overflowX: document.documentElement.scrollWidth > window.innerWidth + 1,
          scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth,
          account: acct ? {label: acct.getAttribute('aria-label'), text: acct.innerText.trim()} : null,
          lang: document.documentElement.lang, title: document.title};
}
"""
SCROLLER_JS = r"""
() => { let best = null, bh = 0;
  for (const el of document.querySelectorAll('*')) { const cs = getComputedStyle(el);
    if (/(auto|scroll)/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 20 && el.scrollHeight > bh)
      { best = el; bh = el.scrollHeight; } }
  return best ? {sh: best.scrollHeight, ch: best.clientHeight, inner: window.innerHeight} : null; }
"""


def compact_aria(text: str, keep_options: int = 3) -> str:
    """Playwright aria snapshot with long option lists (the 105-week selects) cut to a few lines."""
    out, n = [], 0
    for line in text.splitlines():
        if line.strip().startswith("- option"):
            n += 1
            if n == keep_options + 1:
                out.append(line.split("- option")[0] + "- option ... (more options omitted)")
            if n > keep_options:
                continue
        else:
            n = 0
        out.append(line)
    return "\n".join(out)


class Review:
    def __init__(self, base: str, out: Path, headed: bool):
        self.base, self.out, self.headed = base.rstrip("/"), out, headed
        for sub in ("screens", "aria", "briefs"):
            (out / sub).mkdir(parents=True, exist_ok=True)
        self.n = 0
        self.persona = "-"
        self.viewport = "desktop"
        self.screens: list[dict] = []
        self.flags: list[dict] = []
        self._flag_keys: set[tuple] = set()
        self.console: list[dict] = []
        self.network: list[dict] = []
        self.errors: list[dict] = []
        self.api: dict = {}
        self.notes: dict = {}
        self.page: Page | None = None

    # ---- recording -------------------------------------------------------------------------------------------
    def attach(self, page: Page) -> None:
        page.on("console", lambda m: self.console.append({
            "persona": self.persona, "viewport": self.viewport, "screen": self.n, "type": m.type, "text": m.text[:400],
            "url": m.location.get("url", "") if m.location else ""}) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: self.console.append({
            "persona": self.persona, "viewport": self.viewport, "screen": self.n, "type": "pageerror", "text": str(e)[:400]}))
        page.on("requestfailed", lambda r: self.network.append({
            "persona": self.persona, "viewport": self.viewport, "screen": self.n, "status": "failed",
            "method": r.method, "url": r.url, "error": (r.failure or "")[:120]}))
        page.on("response", lambda r: self.network.append({
            "persona": self.persona, "viewport": self.viewport, "screen": self.n, "status": r.status,
            "method": r.request.method, "url": r.url}) if r.status >= 400 else None)

    def flag(self, kind: str, detail: str, sample: str = "", screen: str = "") -> None:
        key = (kind, self.persona, sample or detail)
        if key in self._flag_keys:
            return
        self._flag_keys.add(key)
        self.flags.append({"kind": kind, "persona": self.persona, "viewport": self.viewport,
                           "screen": screen, "detail": detail, "sample": sample[:200]})

    def shot(self, page: Page, name: str, full: bool = False, aria: bool = True, scan: bool = True) -> str:
        self.n += 1
        label = f"{self.n:02d}-{self.viewport[:1]}-{self.persona}-{name}"
        png = self.out / "screens" / f"{label}.png"
        page.wait_for_timeout(350)
        restored = None
        if full:
            dims = page.evaluate(SCROLLER_JS)
            if dims:
                size = page.viewport_size
                restored = size
                page.set_viewport_size({"width": size["width"],
                                        "height": min(dims["inner"] + dims["sh"] - dims["ch"] + 8, 7000)})
                page.wait_for_timeout(500)
        page.screenshot(path=str(png))
        if restored:
            page.set_viewport_size(restored)
        entry = {"n": self.n, "persona": self.persona, "viewport": self.viewport, "name": name,
                 "png": png.relative_to(ROOT).as_posix(), "url": urlsplit(page.url).path}
        if aria:
            target = page.locator("[role=dialog]").last if page.locator("[role=dialog]").count() else page.locator("body")
            try:
                text = compact_aria(target.aria_snapshot(timeout=8000))
                (self.out / "aria" / f"{label}.txt").write_text(text, encoding="utf-8")
                entry["aria"] = (self.out / "aria" / f"{label}.txt").relative_to(ROOT).as_posix()
            except Exception as exc:  # noqa: BLE001
                entry["aria_error"] = str(exc)[:100]
        if scan:
            entry["scan"] = self.scan(page, label)
        self.screens.append(entry)
        print(f"  {label}", flush=True)
        return label

    # ---- mechanical flags ------------------------------------------------------------------------------------
    def scan(self, page: Page, screen: str) -> dict:
        d = page.evaluate(SCAN_JS)
        text = d["text"]
        for m in set(RAW_CODE.findall(text)):
            self.flag("raw-code-in-prose", "an internal identifier is visible", m, screen)
        iso = ISO_DATE.findall(text)
        if iso:
            self.flag("iso-date-in-text", f"{len(iso)} ISO date(s) on a screen that also uses long dates"
                      if re.search(r"\b[A-Z][a-z]{2} \d{1,2}, 20\d\d\b", text) else f"{len(iso)} ISO date(s)", iso[0], screen)
        for m in set(LONG_FLOAT.findall(text)):
            self.flag("unrounded-number", "a long float is visible", m, screen)
        for m in set(VENDOR.findall(text)):
            self.flag("vendor-name-visible", "a model or tool vendor name is visible", m, screen)
        if MOJIBAKE.search(text):
            self.flag("mojibake", "garbled characters", MOJIBAKE.search(text).group(0), screen)
        if "signed-off brief" in text and re.search(r"Draft|Awaiting analyst review|Awaiting Brand Manager|Waiting for the Insights Manager", text):
            self.flag("approved-footer-over-draft", "footer says the content is approved while the status says draft", "", screen)
        for t in d["tabs"]:
            if t["selected"] and t["disabled"]:
                self.flag("selected-tab-disabled", "a selected tab carries disabled", t["name"], screen)
        if d["emptyHeadings"]:
            self.flag("empty-heading", f"{d['emptyHeadings']} empty heading element(s)", "", screen)
        for u in d["unnamed"][:3]:
            self.flag("control-without-name", "a visible control has no accessible name", u, screen)
        for i in d["imgs"][:3]:
            self.flag("image-without-name", "an image or chart has no accessible name", i, screen)
        for s in d["selects"]:
            if s["options"] > 60:
                self.flag("long-select", f"a select with {s['options']} options", s["label"], screen)
        merged = [s for s in d["sups"] if re.search(r"[\d%]$", s["prev"]) and re.fullmatch(r"\d+", s["sup"])]
        if merged:
            m = merged[0]
            self.flag("footnote-merges-into-value", f"{len(merged)} superscript(s) follow a value with no separator; "
                      f"copied text reads '{m['joined']}'", m["joined"], screen)
        if d["overflowX"]:
            self.flag("horizontal-overflow", f"page is {d['scrollW']} px wide in a {d['innerW']} px viewport", "", screen)
        if self.viewport == "mobile" and d["small"]:
            self.flag("small-tap-targets", f"{d['small']} interactive element(s) under 24 px", "", screen)
        for block in d["blocks"]:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", block) if len(s.strip()) > 35]
            for s in {x for x in sentences if sentences.count(x) > 1}:
                self.flag("duplicate-sentence", "a sentence repeats inside one block", s, screen)
        prev = None
        for block in d["blocks"]:
            if prev and block == prev:
                self.flag("duplicate-sentence", "the same block appears twice in a row", block, screen)
            prev = block
        if d["account"]:
            self.notes.setdefault("account_button", {})[f"{self.persona}/{self.viewport}"] = d["account"]
        return {"selects": d["selects"], "tabs": d["tabs"], "sups": len(d["sups"]), "small_targets": d["small"],
                "account": d["account"], "title": d["title"], "lang": d["lang"]}

    def step(self, name: str, fn, *args) -> None:
        try:
            fn(*args)
        except Exception as exc:  # noqa: BLE001 - a failed step is a run error, not the end of the review
            self.errors.append({"persona": self.persona, "viewport": self.viewport, "step": name,
                                "error": f"{type(exc).__name__}: {str(exc).splitlines()[0][:240]}"})
            print(f"  ! {self.persona}/{self.viewport} {name}: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}", file=sys.stderr, flush=True)
            try:
                self.close_dialog(self.page)
            except Exception:  # noqa: BLE001
                pass

    # ---- helpers ---------------------------------------------------------------------------------------------
    def sign_in(self, ctx: BrowserContext, who: str) -> Page:
        self.persona = who
        page = ctx.new_page()
        self.page = page
        page.set_default_timeout(20000)
        self.attach(page)
        page.goto(f"{self.base}/auth/login")
        page.get_by_role("button", name=PERSONAS[who][1], exact=True).click()
        page.get_by_role("heading", level=1).first.wait_for(timeout=20000)
        page.wait_for_timeout(1200)
        return page

    def close_dialog(self, page: Page) -> None:
        """Close an open drawer or dialog: Escape first, then the scrim's own close button."""
        for _ in range(2):
            if not page.locator("[role=dialog]").count():
                return
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        if page.locator("[role=dialog]").count():
            page.get_by_role("button", name=re.compile(r"^Close")).first.click()
            page.wait_for_timeout(400)

    def to_nav(self, page: Page, name: str) -> None:
        page.get_by_role("navigation", name="Workspaces").get_by_role("button", name=re.compile(name)).click()
        page.wait_for_timeout(1500)

    def open_feedback(self, page: Page) -> None:
        page.get_by_role("button", name=re.compile(r"^Share feedback")).click()
        page.get_by_role("dialog").wait_for(timeout=8000)
        self.shot(page, "share-feedback")
        page.get_by_role("button", name="Or take the one-minute questionnaire").click()
        page.wait_for_timeout(800)
        self.shot(page, "questionnaire")
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        if page.get_by_role("dialog").count():
            page.get_by_role("button", name=re.compile(r"^Close")).first.click()

    def account_menu(self, page: Page) -> None:
        page.get_by_role("button", name=re.compile(r"^Account:")).click()
        page.wait_for_timeout(500)
        self.shot(page, "account-menu")
        page.keyboard.press("Escape")

    def generate_brief(self, page: Page, territory: str, shot_prefix: str = "", brand: str | None = None) -> None:
        page.get_by_role("tab", name="New briefing").click()
        page.wait_for_timeout(800)
        if brand:  # the brief's brand is a form field, separate from the Overview's toggle (2026-11-27)
            page.locator("form label", has_text="Brand").locator("select").first.select_option(label=brand)
        page.get_by_role("combobox", name="Territory").select_option(label=territory)
        page.get_by_role("button", name="Generate briefing").click()
        page.get_by_role("heading", name="What should this brief investigate?").wait_for(timeout=30000)
        self.shot(page, f"{shot_prefix}triage-plan", full=True)
        page.get_by_role("button", name="Approve plan and investigate").click()
        page.get_by_role("group", name="View").wait_for(timeout=60000)
        page.wait_for_timeout(800)


# ============================================================================================================
# Walkthroughs
# ============================================================================================================
def sign_off_queue(base: str) -> None:
    """Sign in as the dev Insights Manager over HTTP and sign off every brief sent for sign-off (brief-005)."""
    import http.cookiejar
    import urllib.parse
    import urllib.request

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.open(urllib.request.Request(f"{base}/auth/dev-login", data=urllib.parse.urlencode({"username": "dev-insights"}).encode(), method="POST"))
    for row in json.load(opener.open(f"{base}/api/briefing/queue")):
        if row["review_status"] == "sent":
            opener.open(urllib.request.Request(f"{base}/api/briefing/{row['brief_id']}/signoff", data=json.dumps({"decision": "signed_off"}).encode(),
                                               headers={"Content-Type": "application/json"}, method="POST")).read()


def analyst_desktop(r: Review, page: Page) -> None:
    r.step("overview", lambda: r.shot(page, "overview", full=True))

    def kpi():
        page.get_by_role("button", name=re.compile("Show the query")).first.click()
        page.get_by_role("dialog").wait_for(timeout=8000)
        r.shot(page, "kpi-query-panel")
        r.close_dialog(page)
    r.step("kpi-query-panel", kpi)

    def drawer():
        page.get_by_role("button", name=re.compile(r"^Southeast ")).first.click()
        page.get_by_role("dialog").wait_for(timeout=8000)
        r.shot(page, "territory-drawer", full=True)
        r.close_dialog(page)
    r.step("territory-drawer", drawer)

    def form():
        page.get_by_role("tab", name="New briefing").click()
        page.wait_for_timeout(800)
        r.shot(page, "new-briefing-form", full=True)
        page.get_by_role("button", name="Add a comparison").click()
        page.wait_for_timeout(500)
        r.shot(page, "new-briefing-comparison-added")
        engine = page.get_by_role("radio", name=re.compile(r"^Agent team"))
        r.notes["agent_team_radio"] = {"disabled": engine.is_disabled(), "name": engine.get_attribute("aria-label")
                                       or page.get_by_role("group", name="Engine").inner_text()[:400]}
        question = page.get_by_role("textbox", name="Ask a question to fill the form")
        question.fill("Why did Southeast change in the week of Aug 24, 2026?")
        page.get_by_role("button", name="Read", exact=True).click()
        page.wait_for_timeout(2500)
        r.shot(page, "form-filled-from-question")
        page.reload()
    r.step("new-briefing-form", form)

    def brief():
        r.generate_brief(page, "Southeast")
        r.shot(page, "brief-analyst-view", full=True)
        promo = page.locator("li", has_text="Promotion:").get_by_role("button").first
        promo.click()
        page.get_by_role("dialog").wait_for(timeout=8000)
        r.shot(page, "evidence-drawer")
        r.close_dialog(page)
    r.step("brief-analyst-view", brief)

    def leadership():
        page.get_by_role("button", name="Leadership preview").click()
        page.wait_for_timeout(1000)
        r.shot(page, "brief-leadership-preview", full=True)
        page.get_by_role("button", name="Analyst view").click()
    r.step("brief-leadership-preview", leadership)

    def chat():
        region = page.get_by_role("region", name="Follow-up questions")
        asked = ["What is this brief least sure of?", "Is the Southeast increase real or just noise?",
                 "Which territory dropped the most and why?"]
        page.get_by_role("button", name=asked[0]).click()
        page.wait_for_timeout(2500)
        for q in asked[1:]:
            page.get_by_role("textbox", name="Ask about this brief").fill(q)
            page.get_by_role("button", name="Send").click()
            page.wait_for_timeout(2500)
        items = region.locator("li").all_inner_texts()
        answers = []
        for q, item in zip(asked, items):
            answers.append({"question": q, "answer": item.replace(q, "", 1).strip()[:600]})
        same = len({a["answer"] for a in answers}) == 1 and len(answers) > 1
        r.api["followup_chat"] = {"answers": answers, "identical_for_different_questions": same,
                                  "counter": re.findall(r"Follow-ups, \d+ of \d+", region.inner_text())}
        if same:
            r.flag("followup-chat-canned", "three different questions returned the same text", answers[0]["answer"][:120])
        r.shot(page, "follow-up-chat", full=True)
    r.step("follow-up-chat", chat)

    def decide():
        page.get_by_role("button", name=re.compile(r"^Reject")).click()
        page.wait_for_timeout(600)
        r.shot(page, "reject-dialog")
        page.keyboard.press("Escape")
        cancel = page.get_by_role("button", name=re.compile(r"^Cancel"))
        if cancel.count():
            cancel.first.click()
        page.get_by_role("button", name="Send for sign-off").click()
        page.wait_for_timeout(2000)
        r.shot(page, "brief-sent")
        sign_off_queue(r.base)  # the Insights Manager (P2) signs it off, so the Director and the Marketer can open it
        page.reload()
        page.wait_for_timeout(1000)
        page.get_by_role("tab", name="Approved briefings").click()
        page.wait_for_timeout(1200)
        r.shot(page, "approved-list")
    r.step("approve-and-approved-list", decide)

    def how():
        page.get_by_role("tab", name="New briefing").click()
        page.get_by_role("button", name="How it works").click()
        page.wait_for_timeout(1000)
        r.shot(page, "how-it-works")
    r.step("how-it-works", how)

    r.step("evaluation", lambda: (r.to_nav(page, "Evaluation"), r.shot(page, "evaluation", full=True)))
    r.step("feedback", lambda: r.open_feedback(page))
    r.step("account-menu", lambda: r.account_menu(page))


def director_desktop(r: Review, page: Page) -> None:
    r.step("landing", lambda: r.shot(page, "landing"))

    def open_brief():
        page.get_by_role("button", name=re.compile(r"^BXA · ")).first.click()
        page.get_by_role("article").wait_for(timeout=15000)
        r.shot(page, "executive-summary", full=True)
        page.get_by_role("button", name="Thumbs up").click()
        page.wait_for_timeout(800)
        r.shot(page, "vote-under-static-summary")
    r.step("executive-summary", open_brief)
    r.step("evaluation", lambda: (r.to_nav(page, "Evaluation"), r.shot(page, "evaluation", full=True)))
    r.step("feedback", lambda: r.open_feedback(page))


def forecast_desktop(r: Review, page: Page) -> None:
    r.step("landing", lambda: r.shot(page, "landing"))

    def ask(chip: str, tag: str) -> None:
        page.get_by_role("button", name=chip).first.click()
        page.get_by_role("heading", name="How the agent reads your question").wait_for(timeout=15000)
        r.shot(page, f"{tag}-scope-check", full=True)
        page.get_by_role("button", name="Investigate").click()
        page.get_by_role("heading", name="Follow-up questions").wait_for(timeout=60000)
        r.shot(page, f"{tag}-investigation", full=True)

    def question_one():
        ask("Week of 2026-08-24: How much of the miss does each driver explain?", "q1")
        chips_before = [b for b in page.get_by_role("region").locator("button").all_inner_texts() if b]
        page.get_by_role("button", name="Why was this driver accepted?").click()
        page.wait_for_timeout(3500)
        r.shot(page, "q1-followup", full=True)
        r.api["forecast_followup_chips_after_run"] = [c for c in chips_before if re.search(r"Why|week by week|Plot|Split|Drop|Same question", c)]
    r.step("forecast-question-1", question_one)

    def report():
        page.get_by_role("button", name="Create report").click()
        page.get_by_role("tab", name="Reports", exact=True).wait_for(timeout=20000)
        page.get_by_role("button", name="Leadership preview").wait_for(timeout=20000)
        r.shot(page, "report-analyst-view", full=True)
        page.get_by_role("button", name="Leadership preview").click()
        page.wait_for_timeout(1000)
        r.shot(page, "report-leadership-preview", full=True)
        page.get_by_role("button", name="Analyst view").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="Submit to Brand Manager").click()
        page.wait_for_timeout(2000)
        r.shot(page, "report-submitted")
    r.step("report-and-submit", report)

    def question_two():
        page.get_by_role("tab", name="New explanation").click()
        page.get_by_role("button", name="All forecast questions").click() if page.get_by_role("button", name="All forecast questions").count() else None
        ask("Week of 2026-05-04, New England: Is the deviation reliable, or a data issue?", "q2-reliability")
    r.step("forecast-question-2-reliability", question_two)

    def question_three():
        page.get_by_role("tab", name="New explanation").click()
        if page.get_by_role("button", name="All forecast questions").count():
            page.get_by_role("button", name="All forecast questions").click()
        page.get_by_role("textbox", name="Your question").fill("Why did Southeast miss forecast in the week of 2026-08-24?")
        page.get_by_role("button", name="Read my question").click()
        page.get_by_role("heading", name="How the agent reads your question").wait_for(timeout=15000)
        r.shot(page, "q3-southeast-scope-check")
    r.step("forecast-question-3-southeast", question_three)
    r.step("evaluation", lambda: (r.to_nav(page, "Evaluation"), r.shot(page, "evaluation", full=True)))


def manager_desktop(r: Review, page: Page) -> None:
    r.step("landing", lambda: r.shot(page, "landing"))

    def empty_approved():
        page.get_by_role("tab", name="Approved reports").click()
        page.wait_for_timeout(800)
        r.shot(page, "approved-reports-before-any")
        page.get_by_role("tab", name="Reports to review").click()
    r.step("approved-reports-empty-state", empty_approved)

    def review():
        page.get_by_role("button", name=re.compile(r"Awaiting Brand Manager approval")).first.click()
        page.get_by_role("button", name="Approve", exact=True).wait_for(timeout=15000)
        r.shot(page, "report-for-review", full=True)
        page.get_by_role("button", name="Approve", exact=True).click()
        page.wait_for_timeout(1500)
        page.get_by_role("tab", name="Approved reports").click()
        page.wait_for_timeout(1000)
        r.shot(page, "approved-reports")
    r.step("review-and-approve", review)
    r.step("evaluation", lambda: (r.to_nav(page, "Evaluation"), r.shot(page, "evaluation", full=False)))


def tester_desktop(r: Review, page: Page) -> None:
    r.step("landing", lambda: r.shot(page, "landing"))
    r.step("account-menu", lambda: r.account_menu(page))

    def second_brand():
        page.get_by_role("combobox", name="Brand").select_option(label="Lipidara (BXC)")  # the Overview's toggle
        page.wait_for_timeout(2500)
        r.shot(page, "bxc-overview", full=True)
        r.generate_brief(page, "Pacific", "bxc-", brand="Lipidara (BXC)")
        r.shot(page, "bxc-brief-analyst-view", full=True)
    r.step("second-brand-bxc", second_brand)

    def switch_view():
        page.get_by_role("button", name=re.compile(r"^Account:")).click()
        page.get_by_role("menuitemradio", name="Leadership").click()
        page.wait_for_timeout(2000)
        r.shot(page, "view-as-leadership")
        page.get_by_role("button", name=re.compile(r"^Account:")).click()
        page.get_by_role("menuitemradio", name="Analyst").click()
        page.wait_for_timeout(1500)
    r.step("view-as-switch", switch_view)

    def forecast_tab():
        r.to_nav(page, "Forecast explanation")
        r.shot(page, "forecast-landing")
    r.step("forecast-workspace", forecast_tab)


def mobile_pass(r: Review, browser) -> None:
    r.viewport = "mobile"
    for who in PERSONAS:
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True,
                                  timezone_id="America/New_York", locale="en-US")
        try:
            page = r.sign_in(ctx, who)
            r.step("landing", lambda: r.shot(page, "landing", full=True))
            if who == "analyst":
                r.step("new-briefing", lambda: (page.get_by_role("tab", name="New briefing").click(), r.shot(page, "new-briefing-form", full=True)))
                r.step("territory-drawer", lambda: (page.get_by_role("tab", name="Overview").click(),
                                                    page.get_by_role("button", name=re.compile(r"^Southeast ")).first.click(),
                                                    page.get_by_role("dialog").wait_for(timeout=8000), r.shot(page, "territory-drawer", full=True)))
            if who == "director":
                r.step("executive-summary", lambda: (page.get_by_role("button", name=re.compile(r"^BXA · ")).first.click(),
                                                     page.get_by_role("article").wait_for(timeout=15000), r.shot(page, "executive-summary", full=True)))
            if who == "forecast-manager":
                r.step("report", lambda: (page.get_by_role("button", name=re.compile(r"Cardiovela forecast performance")).first.click(),
                                          page.wait_for_timeout(1500), r.shot(page, "report", full=True)))
            if who == "tester":
                r.step("account-menu", lambda: r.account_menu(page))
        finally:
            ctx.close()
    r.viewport = "desktop"


# ============================================================================================================
# Non-browser checks: headers, role matrix, payload leakage, brief cross-checks, cross-lane
# ============================================================================================================
def api_checks(r: Review, base: str, ctxs: dict[str, BrowserContext], out: Path) -> None:
    anon = ctxs["_anon"].request
    headers = {}
    for path in ("/", "/api/health", "/auth/login"):
        resp = anon.get(base + path)
        headers[path] = {k.lower(): v for k, v in resp.headers.items()}
    me = ctxs["analyst"].request.get(base + "/api/me")
    headers["/api/me (signed in)"] = {k.lower(): v for k, v in me.headers.items()}
    root = headers["/"]
    missing = []
    for h, label in HEADERS_WANTED.items():
        present = h in root or (h == "x-frame-options" and "frame-ancestors" in root.get("content-security-policy", ""))
        if not present:
            missing.append(label)
    (out / "headers.json").write_text(json.dumps({"origin": base, "headers": headers, "missing_on_root": missing}, indent=1), encoding="utf-8")
    if missing:
        r.flag("security-headers-missing", "response headers missing on /: " + ", ".join(missing), "", "headers")
    html = anon.get(base + "/").text()
    comments = re.findall(r"<!--(.*?)-->", html, re.S)
    r.notes["html_comments"] = [c.strip()[:200] for c in comments]
    fig = [c.strip()[:120] for c in comments if "figma" in c.lower()] + re.findall(r"figma:[^\s<\"']{0,80}", html)
    if fig:
        r.flag("design-tool-comments-in-served-html", f"{len(fig)} design-tool comment(s) in the served HTML", fig[0], "/")

    # role matrix: what each login may read
    probes = ["/api/me", "/api/telemetry", "/api/telemetry/usage", "/api/briefing/overview", "/api/briefing/published",
              "/api/forecast/reports", "/api/feedback/responses", "/api/classification", "/api/agent/status"]
    matrix = {}
    for who in PERSONAS:
        matrix[who] = {p: ctxs[who].request.get(base + p).status for p in probes}
    r.api["role_matrix"] = matrix
    open_eval = [w for w, row in matrix.items() if row["/api/telemetry"] == 200]
    r.notes["evaluation_data_readable_by"] = open_eval
    if len(open_eval) == len(PERSONAS):
        r.flag("evaluation-open-to-every-role", "/api/telemetry answers 200 for every login", "", "api")

    # leadership payloads carry no evidence, claims or SQL
    leak = []
    d = ctxs["director"].request
    pub = d.get(base + "/api/briefing/published").json()
    for item in pub[:2]:
        resp = d.get(f"{base}/api/briefing/{item['brief_id']}")
        body = resp.text()
        keys = list(resp.json().keys()) if resp.ok else []
        bad_keys = [k for k in keys if k in ("evidence", "claims", "claim_events", "events", "trace", "flow")]
        if bad_keys or SQL.search(body):
            leak.append({"brief": item["brief_id"], "keys": bad_keys, "sql": bool(SQL.search(body))})
    m = ctxs["forecast-manager"].request
    reps = m.get(base + "/api/forecast/reports")
    if reps.ok:
        for item in (reps.json() if isinstance(reps.json(), list) else reps.json().get("reports", []))[:2]:
            rid = item.get("report_id") or item.get("id") or item.get("rid")
            if rid:
                body = m.get(f"{base}/api/forecast/reports/{rid}").text()
                if SQL.search(body) or '"evidence"' in body:
                    leak.append({"report": rid, "sql": bool(SQL.search(body)), "evidence_key": '"evidence"' in body})
    r.api["leader_payload_leaks"] = leak
    # briefs saved by an older version keep their old format: compare every approved brief's shape. A fresh state
    # folder holds only this run's briefs; seed it with the previous review's (see SKILL.md) to catch old formats.
    formats = []
    for item in pub:
        j = d.get(f"{base}/api/briefing/{item['brief_id']}").json()
        formats.append({"brief_id": item["brief_id"], "reviewed_at": item.get("reviewed_at"), "keys": sorted(j.keys()),
                        "top_sections": [s.get("title") for s in j.get("sections", []) if "." not in str(s.get("number", ""))]})
    r.api["director_brief_formats"] = formats
    if len({(tuple(f["keys"]), tuple(f["top_sections"])) for f in formats}) > 1:
        r.flag("briefs-in-different-formats", f"{len(formats)} approved briefs do not share one structure (keys or top-level sections)",
               ", ".join(f["brief_id"] for f in formats)[:150], "api")
    if leak:
        r.flag("leader-view-carries-evidence", "a leadership payload holds evidence, claims or SQL", json.dumps(leak)[:200], "api")
    # forbidden routes for the director
    bodies = {"/api/briefing/query": {"week_start": "2026-10-05", "territory_id": "SOUTHEAST"},
              "/api/briefing/scope": {"question": "Why did Southeast change this week?"},
              "/api/briefing/triage": {"week_start": "2026-10-05", "territory_id": "SOUTHEAST"}}
    forb = {p: d.post(base + p, data=b).status for p, b in bodies.items()}
    forb["GET /api/briefing/overview"] = d.get(base + "/api/briefing/overview").status
    r.api["director_forbidden_routes"] = forb


def brief_checks(r: Review, base: str, ctxs: dict[str, BrowserContext], out: Path) -> None:
    """Cross-checks of each generated brief against its own Assumptions block, and against the Overview."""
    a = ctxs["analyst"].request
    ctx = a.get(base + "/api/briefing/context").json()
    latest = ctx["latest_week"]
    ov = a.get(f"{base}/api/briefing/overview?week={latest}").json()
    status = {t["label"]: t["status"] for t in ov["territories"]}
    cases = [("SOUTHEAST", latest, None, "southeast-latest"), ("SOUTHEAST", "2026-08-24", None, "southeast-aug24"),
             ("PACIFIC", latest, None, "pacific-latest"), ("SOUTHEAST", "2026-08-24", "2026-09-07", "southeast-aug24-sep7")]
    results = []
    for terr, wk, wk_end, tag in cases:
        body = {"week_start": wk, "territory_id": terr}
        if wk_end:
            body["week_end"] = wk_end
        resp = a.post(base + "/api/briefing/query", data=body)
        if not resp.ok:
            results.append({"case": tag, "error": f"{resp.status} {resp.text()[:160]}"})
            continue
        brief = resp.json()
        (out / "briefs" / f"{tag}.json").write_text(json.dumps(brief, indent=1), encoding="utf-8")
        results.append(check_one(tag, brief, status if wk == latest else None))
    r.api["brief_checks"] = results
    for res in results:
        for f in res.get("flags", []):
            r.flag(f["kind"], f["detail"], f.get("sample", ""), f"brief:{res['case']}")


def check_one(tag: str, brief: dict, overview_status: dict | None) -> dict:
    text = brief.get("answer", "")
    flags: list[dict] = []
    win = re.search(r"\((\d{4}-\d\d-\d\d) to (\d{4}-\d\d-\d\d)\)", text)
    stated = [win.group(1), win.group(2)] if win else None
    period = [brief["week_start"], brief.get("week_end") or brief["week_start"]]
    dated: list[dict] = []
    for ev in brief.get("evidence", []):
        dates = sorted(set(re.findall(r"DATE '(\d{4}-\d\d-\d\d)'", ev.get("query", ""))))
        if not dates:
            dates = sorted(set(ev.get("params", {}).get("weeks", []) or []))
        if dates:
            dated.append({"id": ev["id"], "tool": ev["tool"], "first": dates[0], "last": dates[-1], "n": len(dates)})
    if stated:
        for e in dated:
            if e["tool"].startswith("chart_") or e["tool"] in ("validate_feed", "project_national", "detect_changes"):
                continue
            if e["first"] < stated[0] <= e["last"] <= stated[1] and e["n"] > 1:
                flags.append({"kind": "comparison-window-differs-from-stated",
                              "detail": f"evidence {e['id']} ({e['tool']}) uses {e['n']} weeks, {e['first']} to {e['last']}; "
                                        f"the brief states {stated[0]} to {stated[1]}",
                              "sample": f"{e['id']}:{e['first']}..{e['last']}"})
    sections = brief.get("sections", [])
    for s in sections:
        body = " ".join(str(s.get(k) or "") for k in ("text", "prose"))
        chart = json.dumps(s.get("chart") or "")
        if "inside its baseline band" in chart or "inside its baseline band" in body:
            if re.search(r"\b(rose|fell|up|down|increase|decline)\b", body) and not re.search(r"normal range|baseline band|within", body):
                flags.append({"kind": "story-vs-chart-caption",
                              "detail": f"section '{s.get('title')}' states a change as a finding; its chart says the week sits inside "
                                        "its baseline band, and the prose never says so",
                              "sample": s.get("title", "")})
        if overview_status and s.get("title") in overview_status and overview_status[s["title"]] != "material":
            flags.append({"kind": "story-for-territory-the-overview-calls-normal",
                          "detail": f"the Overview marks {s['title']} '{overview_status[s['title']]}' for the latest week, "
                                    "yet the brief carries a story for it",
                          "sample": s["title"]})
    for code in set(RAW_CODE.findall(json.dumps(brief.get("triage") or "") + text)):
        flags.append({"kind": "raw-code-in-prose", "detail": "an internal identifier in brief or triage text", "sample": code})
    iso = ISO_DATE.findall(text)
    if iso:
        flags.append({"kind": "iso-date-in-text", "detail": f"{len(iso)} ISO dates in the brief's own prose", "sample": iso[0]})
    drivers = [x.strip() for x in text.splitlines() if re.search(r"^-?\s*(Promotion|Access|Supply|Competitor launch|Data artifact):|Candidate drivers", x)]
    return {"case": tag, "brief_id": brief.get("brief_id"), "period": period, "stated_comparison": stated,
            "evidence_dates": dated, "driver_lines": drivers, "flags": flags}


def cross_lane(r: Review, base: str, ctxs: dict[str, BrowserContext], out: Path) -> None:
    """Briefing and Forecast on the same territory and weeks: record what each lane says, flag a driver one names that the other omits."""
    f = ctxs["forecast-analyst"].request
    resp = f.post(base + "/api/forecast/ask", data={"question": "Why did Southeast miss forecast in the week of 2026-08-24?",
                                                    "territory_id": "SOUTHEAST", "week_from": "2026-08-24"})
    if not resp.ok:
        r.api["cross_lane"] = {"error": f"{resp.status} {resp.text()[:160]}"}
        return
    rid = resp.json().get("run_id")
    run = {}
    for _ in range(60):
        run = f.get(f"{base}/api/forecast/runs/{rid}").json()
        if run.get("job_status") in ("done", "failed"):
            break
        time.sleep(1)
    report = run.get("report") or (run.get("result") or {}).get("report") or {}
    (out / "briefs" / "forecast-southeast-aug24.json").write_text(json.dumps(run, indent=1)[:400000], encoding="utf-8")
    forecast_text = json.dumps(report)
    drivers = [f"{d.get('label')} ({d.get('impact_trx')} TRx, {d.get('confidence')})" for d in (report.get("drivers") or [])][:8]
    forecast_answer = run.get("answer") or ""
    briefing = next((c for c in r.api.get("brief_checks", []) if c.get("case") == "southeast-aug24"), {})
    brief_json = out / "briefs" / "southeast-aug24.json"
    brief_text = json.loads(brief_json.read_text(encoding="utf-8")).get("answer", "") if brief_json.is_file() else ""
    r.api["cross_lane"] = {"forecast_headline": report.get("headline"), "forecast_drivers": drivers, "forecast_miss": report.get("variance_pct"),
                           "forecast_investigated": [x for x in forecast_answer.splitlines() if x.startswith("- ")][:6],
                           "briefing_driver_lines": briefing.get("driver_lines", []), "territory": "SOUTHEAST", "week": "2026-08-24"}
    fb = re.search(r"averaged (\d+) a week against a usual (\d+)", forecast_answer)
    bb = re.search(r"Promotion:[^\n]*averaged (\d+) a week against (\d+)", brief_text)
    if fb and bb:
        r.api["cross_lane"]["rep_calls"] = {"forecast": {"week": int(fb.group(1)), "baseline": int(fb.group(2))},
                                            "briefing": {"week": int(bb.group(1)), "baseline": int(bb.group(2))}}
        if fb.group(2) != bb.group(2):
            r.flag("lanes-disagree", f"the same rep-call fact has two baselines: Forecast 'a usual {fb.group(2)}', "
                   f"Briefing '{bb.group(2)} in the reference weeks' (Southeast, week of 2026-08-24)", "rep calls baseline", "cross-lane")
    if re.search(r"coverage lapse", forecast_text, re.I) and not re.search(r"lapse", brief_text, re.I):
        r.flag("lanes-name-event-differently", "Forecast names a Southeast rep coverage lapse for 2026-08-24; the Briefing for the same "
               "territory and week calls the same fall in calls 'promotion supported as an association' and never says lapse", "lapse", "cross-lane")


# ============================================================================================================
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--label", required=True, help="version label, e.g. v1")
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--no-mobile", action="store_true")
    args = ap.parse_args()
    out = ROOT / "local" / "reviews" / f"{args.date}-{args.label}"
    out.mkdir(parents=True, exist_ok=True)
    r = Review(args.base, out, args.headed)
    started = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        opts = {"viewport": {"width": 1280, "height": 800}, "timezone_id": "America/New_York", "locale": "en-US"}
        ctxs: dict[str, BrowserContext] = {"_anon": browser.new_context(**opts)}
        pages: dict[str, Page] = {}
        runners = {"analyst": analyst_desktop, "director": director_desktop, "forecast-analyst": forecast_desktop,
                   "forecast-manager": manager_desktop, "tester": tester_desktop}
        # the order matters: the analyst approves a brief for the director; the forecast analyst submits for the manager
        for who in ("analyst", "director", "forecast-analyst", "forecast-manager", "tester"):
            print(f"-- {who} (desktop)")
            ctxs[who] = browser.new_context(**opts)
            try:
                pages[who] = r.sign_in(ctxs[who], who)
            except Exception as exc:  # noqa: BLE001
                r.errors.append({"persona": who, "viewport": "desktop", "step": "sign-in", "error": str(exc).splitlines()[0][:200]})
                continue
            runners[who](r, pages[who])
        r.persona = "-"
        r.step("api-checks", api_checks, r, args.base, ctxs, out)
        r.step("brief-checks", brief_checks, r, args.base, ctxs, out)
        r.step("cross-lane", cross_lane, r, args.base, ctxs, out)
        if not args.no_mobile:
            print("-- mobile 390 px pass")
            r.step("mobile-pass", mobile_pass, r, browser)
        for c in ctxs.values():
            c.close()
        browser.close()

    (out / "console.json").write_text(json.dumps(r.console, indent=1), encoding="utf-8")
    (out / "network.json").write_text(json.dumps(r.network, indent=1), encoding="utf-8")
    obs = {"label": args.label, "date": args.date, "app": args.base, "viewport_desktop": "1280x800", "viewport_mobile": "390x844",
           "timezone": "America/New_York", "seconds": round(time.time() - started),
           "screens": r.screens, "flags": r.flags, "run_errors": r.errors,
           "console_messages": len(r.console), "network_failures": len(r.network),
           "api": r.api, "notes": r.notes,
           "not_done": ["Agent-team brief: needs an Anthropic key and is skipped unless one is configured",
                        "Hosted app: never signed in to or changed"]}
    (out / "observations.json").write_text(json.dumps(obs, indent=1), encoding="utf-8")
    print(f"{len(r.screens)} screens, {len(r.flags)} mechanical flags, {len(r.errors)} run errors, "
          f"{len(r.console)} console messages, {len(r.network)} failed requests -> {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
