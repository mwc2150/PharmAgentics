import { useMemo, useState } from "react"
import type { Claim, RunEvent } from "./agent/briefingApi"

// brief-009 FR-004: the timeline of how a brief was built. It reads the run's event log (plan.md): live from the job's
// `progress` while the brief builds, then from the brief's saved `events`. Findings link to the claims they produced
// in the memo, and a claim opened in the memo names its producer through `producers`. Every word and number shown
// here was written by the server's code from a tool result; the UI adds none.

// An outlined word, never a filled pill (DESIGN.md).
const chip = "rounded-md border px-2 py-0.5 text-xs font-medium"
export const KIND_STYLE: Record<RunEvent["kind"], string> = {
  agent: "border-edge text-ink",
  llm: "border-amberline text-amber",
  code: "border-edge text-ink",
  person: "border-human/60 text-human",
}
export const KIND_NAME: Record<RunEvent["kind"], string> = { agent: "Agent", llm: "LLM step", code: "Code", person: "Person" }
const VERDICT: Record<string, [string, string]> = {
  supported: ["Supported", "bg-okbg text-ok"],
  "ruled out": ["Ruled out", "bg-paper text-muted border border-rule"],
  inconclusive: ["Inconclusive", "bg-amberbg text-amber"],
  abstained: ["Abstained", "bg-amberbg text-amber"],
  done: ["Done", "bg-paper text-muted border border-rule"],
}
// A check is a test of the data or of a driver. Counted exactly as the server counts it for leaders (views.process_summary).
export const countChecks = (events: RunEvent[]) =>
  events.filter(e => (e.step === "Check the data" || e.step === "Test a driver") && (e.tool ?? "").startsWith("check_")).length
export const FIRST_STEPS = 5  // steps shown per actor in a group before the rest fold

const titleCase = (s: string) => s.toLowerCase().split(/[_\s]+/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")
function storyTitle(key: string, titles?: Record<string, string>): string {
  return titles?.[key] ?? titleCase(key.includes(":") ? key.split(":").slice(1).join(":") : key)
}

type Group = { key: string, title: string, events: RunEvent[] }
export function groupEvents(events: RunEvent[], titles?: Record<string, string>): Group[] {
  const groups = new Map<string, Group>()
  let sawStory = false
  for (const e of [...events].sort((a, b) => a.seq - b.seq)) {
    const key = e.story ?? (sawStory ? "_after" : "_before")
    if (e.story) sawStory = true
    let g = groups.get(key)
    if (!g) {
      g = { key, title: e.story ? storyTitle(e.story, titles) : key === "_before" ? "Plan" : "Write-up and review", events: [] }
      groups.set(key, g)
    }
    g.events.push(e)
  }
  return [...groups.values()]
}

// The events that produced a source record: those whose claim indexes point at a claim citing that evidence ID.
export function producers(events: RunEvent[] | null | undefined, claims: Claim[], evidenceId: string): RunEvent[] {
  const indexes = new Set(claims.flatMap((c, i) => c.evidence_id === evidenceId ? [i] : []))
  return (events ?? []).filter(e => e.claims.some(i => indexes.has(i)))
}

// Scroll the memo to a claim's number and mark it for a moment; a claim that is folded away or not in the memo opens its source instead.
export function jumpToClaim(claim: Claim | undefined, openSource?: (evidenceId: string) => void) {
  if (!claim) return
  const title = `Source ${claim.evidence_id}: open the query behind ${claim.value}`
  const el = Array.from(document.querySelectorAll<HTMLElement>(".pa-cite")).find(b => b.title === title && b.getClientRects().length > 0)
  if (!el) { openSource?.(claim.evidence_id); return }
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches
  el.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" })
  el.focus({ preventScroll: true })
  el.classList.add("bg-primarybg", "ring-2", "ring-primary")
  window.setTimeout(() => el.classList.remove("bg-primarybg", "ring-2", "ring-primary"), 2000)
}

function Row({ e, claims, onJump }: { e: RunEvent, claims?: Claim[], onJump: (c: Claim | undefined) => void }) {
  const verdict = e.verdict ? VERDICT[e.verdict] ?? [e.verdict, "bg-paper text-muted border border-rule"] : null
  const argText = e.args && Object.keys(e.args).length ? Object.entries(e.args).map(([k, v]) => `${k}=${String(v)}`).join(", ") : null
  return <li id={`event-${e.seq}`} className="grid gap-x-3 gap-y-1 py-2.5 sm:grid-cols-[148px_1fr]">
    <div className="flex flex-wrap items-start gap-1.5 sm:flex-col sm:items-start">
      <span className={`${chip} ${KIND_STYLE[e.kind]}`}>{e.actor}</span>
      <span className="text-[11px] text-muted">{KIND_NAME[e.kind]}</span>
    </div>
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-sm font-medium">{e.step}</span>
        {e.tool && <span className="rounded border border-rule bg-paper px-1.5 py-0.5 font-mono text-[11px] text-muted" title={argText ?? undefined}>{e.tool}{argText ? `(${argText})` : ""}</span>}
        {verdict && <span className={`${chip} ${verdict[1]}`}>{verdict[0]}</span>}
      </div>
      {e.summary && <p className="mt-1 text-sm text-muted">{e.summary}</p>}
      {(e.claims.length > 0 || e.prompt) && <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        {e.claims.length > 0 && <span className="flex flex-wrap items-center gap-1.5 text-muted">Produced
          {e.claims.map(i => claims?.[i]
            ? <button key={i} type="button" onClick={() => onJump(claims[i])} title="Show this number in the brief"
                className="rounded-sm font-medium text-primary underline decoration-primary/40 decoration-dotted underline-offset-4 hover:bg-primarybg focus:bg-primarybg focus:outline-none">{claims[i].value}</button>
            : <span key={i}>claim {i + 1}</span>)}
        </span>}
        {e.prompt && <span className="font-mono text-[11px] text-muted" title="The prompt file and version this step ran on">{e.prompt}</span>}
      </div>}
    </div>
  </li>
}

export function Timeline({ events, claims, live = false, titles, onOpenSource }: {
  events: RunEvent[], claims?: Claim[], live?: boolean, titles?: Record<string, string>, onOpenSource?: (evidenceId: string) => void
}) {
  const groups = useMemo(() => groupEvents(events, titles), [events, titles])
  const [open, setOpen] = useState<Record<string, boolean>>({})  // "<group>|<actor>" unfolded
  const last = events.length ? events.reduce((a, b) => b.seq > a.seq ? b : a) : null
  const produced = events.reduce((n, e) => n + e.claims.length, 0)
  const checks = countChecks(events)
  return <section aria-label="How this brief was built" className="rounded-xl border border-rule bg-sheet px-6 py-5">
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <h3 className="text-sm font-semibold">{live ? "Building the brief" : "How this brief was built"}</h3>
      <span className="text-xs text-muted">{events.length} step{events.length === 1 ? "" : "s"}{checks ? ` · ${checks} check${checks === 1 ? "" : "s"}` : ""}{produced ? ` · ${produced} number${produced === 1 ? "" : "s"} produced` : ""}</span>
    </div>
    {live && <p role="status" aria-live="polite" className="mt-2 flex items-center gap-2 text-xs text-muted">
      <span aria-hidden="true" className="h-2 w-2 shrink-0 rounded-full bg-primary pa-pulse"/>
      {last ? `Now: ${last.actor}, ${last.step.toLowerCase()}` : "Waiting for the first step…"}
    </p>}
    {!events.length && !live && <p className="mt-3 text-sm text-muted">No steps were recorded for this brief.</p>}
    <div className="mt-2 divide-y divide-rule">
      {groups.map(g => {
        const seen: Record<string, number> = {}
        const hidden: Record<string, number> = {}
        const shown = g.events.filter(e => {
          const n = seen[e.actor] = (seen[e.actor] ?? 0) + 1
          if (n <= FIRST_STEPS || open[`${g.key}|${e.actor}`]) return true
          hidden[e.actor] = (hidden[e.actor] ?? 0) + 1
          return false
        })
        return <div key={g.key} className="py-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted">{g.key.startsWith("_") ? g.title : `Story: ${g.title}`}</h4>
          <ol className="divide-y divide-rule/60">{shown.map(e => <Row key={e.seq} e={e} claims={claims} onJump={c => jumpToClaim(c, onOpenSource)}/>)}</ol>
          {Object.entries(hidden).map(([actor, n]) => <button key={actor} type="button" onClick={() => setOpen(o => ({ ...o, [`${g.key}|${actor}`]: true }))}
            className="mt-1 text-xs font-medium text-primary underline-offset-4 hover:underline">Show {n} more {actor} step{n === 1 ? "" : "s"}</button>)}
        </div>
      })}
    </div>
  </section>
}
