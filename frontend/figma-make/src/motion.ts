// Motion helpers (Michael, 2026-11-27: "a smoother, rich feel"). Everything here asks motionReduced() first, so the
// Settings choice and the system's reduced-motion setting turn it off; without the browser feature it does nothing.
import { useLayoutEffect, useRef, type RefObject } from "react"
import { flushSync } from "react-dom"
import { motionReduced } from "./userSettings"

type Transition = { updateCallbackDone: Promise<void>, finished: Promise<void> }
type Start = (update: () => void | Promise<void>) => Transition

/** The View Transitions API when motion is allowed, else null. */
function starter(): Start | null {
  if (typeof document === "undefined" || motionReduced()) return null
  const d = document as Document & { startViewTransition?: Start }
  return typeof d.startViewTransition === "function" ? d.startViewTransition.bind(d) : null
}

/** The name a brief's heading and the list row it was opened from share, so the title moves from one to the other. */
export const BRIEF_TITLE = "pa-brief-title"
/** The same for a forecast question: the list row's question moves into the run's page. */
export const RUN_TITLE = "pa-run-title"

/** A state change shown as a page transition: a short crossfade, and elements that share a view-transition-name move
    into place. Without the API, or with reduced motion, the change just happens. */
export function pageChange(update: () => void): void {
  const start = starter()
  if (!start) { update(); return }
  start(() => flushSync(update))
}

/** A DOM-only change (no React state), such as the theme attribute, shown as a crossfade. */
export function domChange(update: () => void): void {
  const start = starter()
  if (!start) { update(); return }
  start(update)
}

export type Settled<T> = { ok: true, value: T } | { ok: false, error: unknown }

/** Opens something that loads (a brief from a list). A load that answers within `wait` ms goes straight from the list to
    the page in one transition, the clicked row's title (`from`) moving into the page's heading; a slower one shows the
    loading state at once and the page arrives when it is ready. `reset` puts the loading state up; `show` takes the result. */
export async function openInTransition<T>(request: Promise<T>, reset: () => void, show: (r: Settled<T>) => void,
    from?: Element | null, wait = 350, name = BRIEF_TITLE): Promise<void> {
  const settled: Promise<Settled<T>> = request.then(value => ({ ok: true as const, value }), error => ({ ok: false as const, error }))
  const start = starter()
  if (!start) { reset(); show(await settled); return }
  if (from instanceof HTMLElement) from.style.viewTransitionName = name
  let early: Settled<T> | null = null
  const t = start(async () => {
    early = await Promise.race([settled, new Promise<null>(r => setTimeout(() => r(null), wait))])
    flushSync(() => { reset(); if (early) show(early) })
  })
  await t.updateCallbackDone.catch(() => { /* the update ran; a skipped animation changes nothing */ })
  if (from instanceof HTMLElement) from.style.viewTransitionName = ""
  if (!early) show(await settled)
}

/** A chart that draws its lines the first time it scrolls into view. Lines carry class "pa-line" (and pathLength 1),
    points "pa-dot", bars "pa-bar". Until script marks the chart ready nothing is hidden, so a chart never stays blank
    (print, no script). The same marks hold a block's padlock numbers (RollIn) until it is seen. `threshold`: the share
    that must show; a tall table needs only a sliver. */
export function useDrawOnView<T extends Element>(threshold = 0.2): RefObject<T | null> {
  const ref = useRef<T>(null)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el || motionReduced() || typeof IntersectionObserver === "undefined") return
    el.classList.add("pa-drawready")
    const io = new IntersectionObserver(entries => {
      if (entries.some(e => e.isIntersecting)) { el.classList.add("pa-inview"); io.disconnect() }
    }, { threshold })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return ref
}
