// Newly approved briefings and Forecast reports: a dot on the "Approved" tab and on the sidebar item, and a "New"
// word on the rows, for anything approved since this browser last opened that list. What was last seen is kept per
// person, view and lane in localStorage (a convenience: a cleared browser simply starts again). On a first visit,
// approvals from the last week count as new. An approval made in this view never lights its own dot; the tester's
// other view ("View as") keeps its own record, so the Leadership view still sees what the Analyst view approved.
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react"
import { listPublished, type Me } from "./agent/briefingApi"
import { listReports } from "./agent/forecastApi"

export type NewsLane = "briefing" | "forecast"
type Stamps = Record<NewsLane, string | null>
// Stamps are always the server's reviewed_at, never this browser's clock. `markOwn` is for an approval made here: it
// moves the mark only when nothing else is waiting to be seen, so it never swallows someone else's approval.
type News = { has: (lane: NewsLane) => boolean, seen: (lane: NewsLane) => string | null, latest: (lane: NewsLane) => string | null,
  markSeen: (lane: NewsLane, at: string | null | undefined) => void, markOwn: (lane: NewsLane, at: string | null | undefined) => void }

const POLL_MS = 60_000
const FIRST_VISIT_DAYS = 7
const later = (a: string | null | undefined, b: string | null | undefined) => !a ? b ?? null : !b ? a : Date.parse(a) >= Date.parse(b) ? a : b
const newest = (stamps: (string | null | undefined)[]) => stamps.reduce<string | null>((m, s) => later(m, s), null)
export const isNewer = (at: string | null | undefined, since: string | null) => !!at && !!since && Date.parse(at) > Date.parse(since)

const key = (who: string, lane: NewsLane) => `pa_seen_approved:${who}:${lane}`
const read = (who: string, lane: NewsLane) => { try { return window.localStorage.getItem(key(who, lane)) } catch { return null } }
const write = (who: string, lane: NewsLane, at: string) => { try { window.localStorage.setItem(key(who, lane), at) } catch { /* a convenience only */ } }

const Ctx = createContext<News>({has: () => false, seen: () => null, latest: () => null, markSeen: () => {}, markOwn: () => {}})
export const useApprovedNews = () => useContext(Ctx)

// The workspace on screen. The Shell keeps a visited workspace mounted but hidden, so a list cannot tell from its own
// lifetime whether anyone is looking at it.
export const ActiveWorkspace = createContext<"briefing" | "forecast" | "evaluation">("briefing")

// An approved list: (re)loads whenever it comes into view and whenever something new is approved while it is in
// view; marks what it shows as seen only while in view; `isNew` is true for rows approved since the previous look.
export function useApprovedList<T>(lane: NewsLane, enabled: boolean, load: () => Promise<T[]>, stamp: (x: T) => string | null | undefined) {
  const news = useApprovedNews()
  const shown = useContext(ActiveWorkspace) === lane
  const active = shown && enabled
  const [items, setItems] = useState<T[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [since, setSince] = useState(() => news.seen(lane))
  const wasShown = useRef(shown)
  const latest = news.latest(lane)
  // "New" holds for one visit to the workspace: opening a report and coming back keeps it; leaving the workspace ends it.
  useEffect(() => { if (shown && !wasShown.current) setSince(news.seen(lane)); wasShown.current = shown }, [shown])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!active) return
    let live = true
    load().then(xs => { if (!live) return; setItems(xs); setError(null); for (const x of xs) news.markSeen(lane, stamp(x)) })
      .catch(e => { if (live) setError(e instanceof Error ? e.message : String(e)) })
    return () => { live = false }
  }, [active, latest])  // eslint-disable-line react-hooks/exhaustive-deps
  return {items, error, isNew: (x: T) => isNewer(stamp(x), since)}
}

export function ApprovedNewsProvider({me, children}: {me: Me, children: ReactNode}) {
  const who = `${me.name || "me"}:${me.view_as ?? "own"}`
  const lanes = useRef<NewsLane[]>([...(me.lanes.briefing ? ["briefing" as const] : []), ...(me.lanes.forecast?.available ? ["forecast" as const] : [])])
  const [latest, setLatest] = useState<Stamps>({briefing: null, forecast: null})
  const [seen, setSeen] = useState<Stamps>(() => {
    const start = new Date(Date.now() - FIRST_VISIT_DAYS * 86_400_000).toISOString()
    const first = (lane: NewsLane) => { const at = read(who, lane); if (at) return at; write(who, lane, start); return start }
    return {briefing: first("briefing"), forecast: first("forecast")}
  })
  const latestRef = useRef(latest)
  latestRef.current = latest
  const advance = useCallback((lane: NewsLane, at: string | null | undefined, own: boolean) => {
    if (!at) return
    setSeen(s => {
      if (own && isNewer(latestRef.current[lane], s[lane])) return s
      const next = later(s[lane], at)
      if (next === s[lane] || !next) return s
      write(who, lane, next)
      return {...s, [lane]: next}
    })
  }, [who])
  const markSeen = useCallback((lane: NewsLane, at: string | null | undefined) => advance(lane, at, false), [advance])
  const markOwn = useCallback((lane: NewsLane, at: string | null | undefined) => advance(lane, at, true), [advance])
  useEffect(() => {
    let live = true
    const poll = async () => {
      if (document.visibilityState === "hidden") return
      const got = await Promise.all(lanes.current.map(async lane => {
        try {
          const at = lane === "briefing" ? newest((await listPublished()).map(b => b.reviewed_at))
            : newest((await listReports()).filter(r => r.review_status === "approved").map(r => r.reviewed_at))
          return [lane, at] as const
        } catch { return [lane, undefined] as const }  // a failed check keeps the last answer
      }))
      if (!live) return
      for (const [lane, at] of got) if (at !== undefined) setLatest(l => ({...l, [lane]: at}))
    }
    void poll()
    const timer = window.setInterval(() => void poll(), POLL_MS)
    const onVisible = () => { if (document.visibilityState === "visible") void poll() }
    document.addEventListener("visibilitychange", onVisible)
    return () => { live = false; window.clearInterval(timer); document.removeEventListener("visibilitychange", onVisible) }
  }, [who, markSeen])
  const value: News = {
    has: lane => isNewer(latest[lane], seen[lane]),
    seen: lane => seen[lane],
    latest: lane => latest[lane],
    markSeen,
    markOwn,
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// The dot itself: decoration; the words beside it are for screen readers.
export function NewDot({className = ""}: {className?: string}) {
  return <><span aria-hidden="true" className={`inline-block h-2 w-2 shrink-0 rounded-full bg-primary ${className}`}/><span className="sr-only">, newly approved</span></>
}
