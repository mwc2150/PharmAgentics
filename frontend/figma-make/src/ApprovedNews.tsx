// Newly approved briefings and Forecast reports: a dot on the "Approved" tab and on the sidebar item, and a "New"
// word on the rows, for anything approved since this browser last opened that list. What was last seen is kept per
// person and lane in localStorage (a convenience: a cleared browser simply starts with no dots). The first visit
// counts everything already approved as seen, and an approval made in this browser never lights its own dot.
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react"
import { listPublished, type Me } from "./agent/briefingApi"
import { listReports } from "./agent/forecastApi"

export type NewsLane = "briefing" | "forecast"
type Stamps = Record<NewsLane, string | null>
type News = { has: (lane: NewsLane) => boolean, seen: (lane: NewsLane) => string | null, latest: (lane: NewsLane) => string | null, markSeen: (lane: NewsLane, at?: string | null) => void }

const POLL_MS = 60_000
const later = (a: string | null | undefined, b: string | null | undefined) => !a ? b ?? null : !b ? a : Date.parse(a) >= Date.parse(b) ? a : b
const newest = (stamps: (string | null | undefined)[]) => stamps.reduce<string | null>((m, s) => later(m, s), null)
export const isNewer = (at: string | null | undefined, since: string | null) => !!at && !!since && Date.parse(at) > Date.parse(since)

const key = (who: string, lane: NewsLane) => `pa_seen_approved:${who}:${lane}`
const read = (who: string, lane: NewsLane) => { try { return window.localStorage.getItem(key(who, lane)) } catch { return null } }
const write = (who: string, lane: NewsLane, at: string) => { try { window.localStorage.setItem(key(who, lane), at) } catch { /* a convenience only */ } }

const Ctx = createContext<News>({has: () => false, seen: () => null, latest: () => null, markSeen: () => {}})
export const useApprovedNews = () => useContext(Ctx)

// The workspace on screen. The Shell keeps a visited workspace mounted but hidden, so a list cannot tell from its own
// lifetime whether anyone is looking at it.
export const ActiveWorkspace = createContext<"briefing" | "forecast" | "evaluation">("briefing")

// An approved list: (re)loads whenever it comes into view and whenever something new is approved while it is in
// view; marks what it shows as seen only while in view; `isNew` is true for rows approved since the previous look.
export function useApprovedList<T>(lane: NewsLane, enabled: boolean, load: () => Promise<T[]>, stamp: (x: T) => string | null | undefined) {
  const news = useApprovedNews()
  const active = useContext(ActiveWorkspace) === lane && enabled
  const [items, setItems] = useState<T[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [since, setSince] = useState(() => news.seen(lane))
  const inView = useRef(false)
  const latest = news.latest(lane)
  useEffect(() => {
    if (!active) { inView.current = false; return }
    if (!inView.current) { inView.current = true; setSince(news.seen(lane)) }
    let live = true
    load().then(xs => { if (!live) return; setItems(xs); setError(null); for (const x of xs) news.markSeen(lane, stamp(x)) })
      .catch(e => { if (live) setError(e instanceof Error ? e.message : String(e)) })
    return () => { live = false }
  }, [active, latest])  // eslint-disable-line react-hooks/exhaustive-deps
  return {items, error, isNew: (x: T) => isNewer(stamp(x), since)}
}

export function ApprovedNewsProvider({me, children}: {me: Me, children: ReactNode}) {
  const who = me.name || "me"
  const lanes = useRef<NewsLane[]>([...(me.lanes.briefing ? ["briefing" as const] : []), ...(me.lanes.forecast?.available ? ["forecast" as const] : [])])
  const [latest, setLatest] = useState<Stamps>({briefing: null, forecast: null})
  const [seen, setSeen] = useState<Stamps>(() => ({briefing: read(who, "briefing"), forecast: read(who, "forecast")}))
  const markSeen = useCallback((lane: NewsLane, at?: string | null) => {
    setSeen(s => {
      const next = later(s[lane], at ?? new Date().toISOString())
      if (next === s[lane] || !next) return s
      write(who, lane, next)
      return {...s, [lane]: next}
    })
  }, [who])
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
      for (const [lane, at] of got) {
        if (at === undefined) continue
        setLatest(l => ({...l, [lane]: at}))
        // First visit: what is already approved is not news; with nothing approved yet, the first approval will be.
        if (read(who, lane) === null) markSeen(lane, at ?? "1970-01-01T00:00:00.000Z")
      }
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
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// The dot itself: decoration; the words beside it are for screen readers.
export function NewDot({className = ""}: {className?: string}) {
  return <><span aria-hidden="true" className={`inline-block h-2 w-2 shrink-0 rounded-full bg-primary ${className}`}/><span className="sr-only">, newly approved</span></>
}
