import { useEffect, useRef } from "react"

/** Hover text that sits beside the pointer and follows it (Michael, 2026-11-27): the browser's own tooltip opens
 *  under the cursor, which covers its first words. One layer for the whole app, mounted once in main.tsx.
 *
 *  It shows an element's `title` (taken off the element while the pointer is on it, so the browser's tooltip does not
 *  open too, and put back when the pointer leaves) or its `data-tip` (chart marks and option notes, whose text lives
 *  nowhere else on hover). Mouse only: touch has no hover, and the keyboard keeps each component's own focus text.
 *  The tip is aria-hidden: assistive technology reads the element's own label and description, as before. */
const DELAY = 350, GAP_X = 14, GAP_Y = 20, EDGE = 8

export function HoverTips() {
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const tip = box.current
    if (!tip) return
    let el: Element | null = null, taken: string | null = null, timer = 0, shownAt = 0, x = 0, y = 0
    const place = () => {
      const w = tip.offsetWidth, h = tip.offsetHeight
      let left = x + GAP_X, top = y + GAP_Y
      if (left + w > window.innerWidth - EDGE) left = Math.max(EDGE, x - GAP_X - w)  // flip left of the pointer
      if (top + h > window.innerHeight - EDGE) top = Math.max(EDGE, y - GAP_Y / 2 - h)  // flip above it
      tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`
    }
    const text = (e: Element) => e.getAttribute("data-tip") || taken || ""
    const show = () => { if (!el) return; const t = text(el); if (!t) return; tip.textContent = t; tip.hidden = false; place(); shownAt = Date.now() }
    const hide = () => { window.clearTimeout(timer); if (!tip.hidden) { tip.hidden = true; shownAt = Date.now() } }
    const release = () => {
      hide()
      if (el && taken !== null && el.isConnected && !el.hasAttribute("title")) el.setAttribute("title", taken)
      el = null; taken = null
    }
    const over = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return
      const found = (e.target as Element | null)?.closest?.("[data-tip],[title]") ?? null
      if (found === el) return
      release()
      if (!found) return
      el = found; x = e.clientX; y = e.clientY
      if (found.hasAttribute("title")) { taken = found.getAttribute("title"); found.removeAttribute("title") }
      // A tip already open moves straight to the next element, as the browser's own tooltips do.
      if (!tip.hidden || Date.now() - shownAt < 400) show(); else timer = window.setTimeout(show, DELAY)
    }
    const move = (e: PointerEvent) => { if (e.pointerType !== "mouse" || !el) return; x = e.clientX; y = e.clientY; if (!tip.hidden) place() }
    const leaveDoc = (e: PointerEvent) => { if (!e.relatedTarget) release() }
    document.addEventListener("pointerover", over)
    document.addEventListener("pointermove", move, { passive: true })
    document.addEventListener("pointerout", leaveDoc)
    document.addEventListener("pointerdown", hide)  // a click closes it, as the browser's does; leaving and coming back reopens it
    document.addEventListener("keydown", hide)
    window.addEventListener("scroll", hide, { capture: true, passive: true })
    window.addEventListener("blur", release)
    return () => {
      document.removeEventListener("pointerover", over)
      document.removeEventListener("pointermove", move)
      document.removeEventListener("pointerout", leaveDoc)
      document.removeEventListener("pointerdown", hide)
      document.removeEventListener("keydown", hide)
      window.removeEventListener("scroll", hide, { capture: true })
      window.removeEventListener("blur", release)
      release()
    }
  }, [])
  return <div ref={box} hidden aria-hidden="true" className="pa-hovertip pointer-events-none fixed left-0 top-0 z-[100] w-max max-w-xs rounded-lg border border-rule bg-paper px-2.5 py-1.5 text-xs leading-snug text-ink shadow-lg print:hidden"/>
}
