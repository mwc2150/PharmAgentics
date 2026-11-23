import { createContext, useContext, useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react"
import { Toaster, toast } from "sonner"
import { BrandMark, Icon, Notice, modelName, plainModels, useModalFocus, type IconName } from "./agent/primitives"
import { TelemetryWorkspace } from "./Telemetry"
import { ForecastChart, type ChartSpec } from "./ForecastCharts"
import { Overview } from "./Overview"
import { Memo } from "./Memo"
import { Timeline, producers, KIND_NAME } from "./Timeline"
import { HowItWorks } from "./HowItWorks"
import { ComparisonPicker, comparisonsError } from "./ComparisonPicker"
import { PeriodPicker, periodError, periodWeeks, readByLabel, useQuestionReader } from "./BriefingScope"
import { DEFAULT_CHOICES, DefinitionPicker, choicesError, type DefinitionChoices, type DefinitionField } from "./BriefDefinition"
import { MessageBar, type Chip } from "./MessageBar"
import { sharedFromLocation } from "./agent/threadApi"
import { AnswerFeedback, FeedbackDock, FeedbackProvider, ShareFeedbackLink, useFeedbackActions } from "./Feedback"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup, DropdownMenuRadioItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "./components/ui/dropdown-menu"
import {
  getContext, getBriefing, getMe, getTriage, listPublished, openBrief, reviewBrief, NotSignedIn,
  getAgentStatus, submitAgentJob, waitAgentJob, agentPlan, agentBrief, getClassification, setViewAs,
  type AgentStatus, type AgentJob, type Classification,
  type BriefDefinition, type BriefingResult, type Claim, type Comparison, type Evidence, type LeadershipBrief, type Me, type PublishedBrief, type ReleaseContext, type RunEvent,
  type Stage, type TriageDecision, type TriagePlan, type TriageRecord,
} from "./agent/briefingApi"
import {
  addReportRun, askFollowup, askForecast, forecastContext, createReport, draftReport, listReports, openReport, pinFollowup,
  removeReportRun, restoreReportVersion, reviewReport, submitReport, unpinFollowup, type ReportSummary, type ReportView, forecastScope, listForecasts, openForecast, reviewForecast, submitForecast,
  type ForecastContext, type ForecastRun, type ForecastScope, type ForecastSummary,
} from "./agent/forecastApi"

// The backend implements a scripted WEEKLY BRIEF with role-based views (core-007). The server
// decides what each role receives; this UI only renders it. No mock data, no fake approvals.
function labelTerritory(id: string): string {
  return id.toLowerCase().split("_").map(s => s[0].toUpperCase() + s.slice(1)).join(" ").replace("Mid Atlantic", "Mid-Atlantic")
}
function labelWeek(iso: string): string {
  const [y,m,d] = iso.split("-").map(Number)
  return new Date(Date.UTC(y,m-1,d)).toLocaleDateString("en-US", {year:"numeric",month:"short",day:"numeric",timeZone:"UTC"})
}
function periodLabel(start: string, end?: string | null): string {
  return end && end > start ? `weeks ${labelWeek(start)} to ${labelWeek(end)}` : `week of ${labelWeek(start)}`
}
function labelTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString("en-US", {month:"short",day:"numeric",hour:"numeric",minute:"2-digit"}) : "—"
}
// The server's one-line process summary ends "; reviewed by the analyst." with no date (a UTC date reads a day late in
// the evening); the date is added here from reviewed_at, in the viewer's own time zone.
function processLine(line: string, reviewedAt: string | null): string {
  const d = reviewedAt ? new Date(reviewedAt) : null
  if (!d || Number.isNaN(d.getTime())) return line
  return line.replace(/; reviewed by the analyst\.$/, `; reviewed by the analyst on ${d.toLocaleDateString("en-CA")}.`)
}
function dataText(input: unknown): string {
  return input === null || input === undefined ? "—" : typeof input === "string" ? input : JSON.stringify(input, null, 2)
}
const message = (e: unknown) => e instanceof Error ? e.message : String(e)
// Status and actor tags: an outlined word, never a filled pill.
const chip = "rounded-md border px-2 py-0.5 text-xs font-medium"
// One vocabulary for every screen: the primary action, a secondary action, a field, its label, a panel.
const BTN = "inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-onprimary shadow-[0_4px_0_var(--color-primarydeep)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-primaryhover active:translate-y-[3px] active:shadow-[0_1px_0_var(--color-primarydeep)] disabled:cursor-not-allowed disabled:bg-rule disabled:text-muted disabled:shadow-none"
const BTN2 = "inline-flex items-center justify-center gap-2 rounded-lg border border-edge px-5 py-2.5 text-sm font-medium text-ink shadow-[0_3px_0_var(--color-slab)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-paper active:translate-y-[2px] active:shadow-[0_1px_0_var(--color-slab)] disabled:cursor-not-allowed disabled:text-muted disabled:shadow-none"
const FIELD = "w-full min-w-0 rounded-lg border border-edge bg-paper px-3.5 py-2.5 text-sm text-ink placeholder:text-muted disabled:opacity-60"
const LABEL = "flex flex-col gap-1.5 text-xs font-medium text-muted"
const PANEL = "pa-panel rounded-xl border border-rule bg-sheet"
const REVIEW_CHIP = {
  pending: [`${chip} border-edge text-ink`, "Draft · Awaiting analyst review"],
  approved: [`${chip} border-ok text-ok`, "Approved · Visible to the Brand Director"],
  rejected: [`${chip} border-edge text-warn`, "Rejected · Hidden from the Brand Director"],
} as const

function EvidenceDrawer({result, selectedId, onClose}: {result: BriefingResult, selectedId: string, onClose: () => void}) {
  const made = (id: string) => producers(result.events, result.claims, id)
  const [id, setId] = useState(selectedId)
  useEffect(() => setId(selectedId), [selectedId])
  const drawer = useRef<HTMLElement>(null)
  useModalFocus(drawer, onClose)
  const claims = result.claims.filter(c=>c.evidence_id===id)
  const selected = result.evidence.find(e=>e.id===id)
  return <div className="fixed inset-0 z-40 flex justify-end">
    <button className="absolute inset-0 bg-black/60" aria-label="Close evidence" onClick={onClose}/>
    <aside ref={drawer} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Source evidence" className="relative z-10 flex h-full w-full max-w-xl flex-col border-l border-rule bg-sheet pa-slide">
      <div className="flex items-start justify-between border-b border-rule p-5">
        <div><div className="text-xs uppercase tracking-widest text-muted">Governed evidence</div><h2 className="mt-1 text-lg font-semibold">Source records</h2><p className="mt-1 text-xs text-muted">{result.evidence.length} evidence records · pinned version {result.data_version ?? "unavailable"}</p></div>
        <button onClick={onClose} aria-label="Close evidence panel" className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-paper hover:text-ink"><Icon name="close" className="h-5 w-5"/></button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="border-b border-rule p-3">
          {result.evidence.map(ev=><button key={ev.id} onClick={()=>setId(ev.id)} aria-current={id===ev.id} className={`flex w-full items-start gap-3 rounded-xl p-3 text-left text-sm ${id===ev.id?"bg-primarybg font-medium":"hover:bg-paper"}`}>
            <span className="font-mono text-xs text-primaryink">{ev.id}</span><span className="min-w-0 flex-1">{ev.tool}<span className="block text-xs text-muted">{result.claims.filter(c=>c.evidence_id===ev.id).map(c=>c.value).join(", ") || "Context evidence"}</span></span>
          </button>)}
        </div>
        {selected && <div className="space-y-4 p-5">
          <div className="rounded-xl bg-paper p-4"><p className="text-xs text-muted">Claim values linked to this record</p><p className="mt-1 font-mono text-sm">{claims.length?claims.map(c=>c.value).join(" · "):"Context only"}</p>
            {made(id).map(e=><p key={e.seq} className="mt-2 text-xs text-muted">Produced by <span className="font-medium text-ink">{e.actor}</span> ({KIND_NAME[e.kind]}) · {e.step}{e.tool ? ` · ${e.tool}` : ""}</p>)}</div>
          <div className="space-y-3 text-sm">
            <dl className="grid grid-cols-[90px_1fr] gap-3"><dt className="text-muted">Tool</dt><dd className="break-all font-mono text-xs">{selected.tool}</dd>
            <dt className="text-muted">Version</dt><dd className="break-all font-mono text-xs">{selected.data_version ?? "Not supplied"}</dd>
            <dt className="text-muted">Value</dt><dd className="break-all font-mono text-xs">{dataText(selected.result)}</dd></dl>
            {selected.query && <div><div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Source SQL</div><pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-xl bg-paper p-3 font-mono text-xs leading-relaxed">{selected.query}</pre></div>}
            <div><div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">Tool arguments</div><pre className="overflow-x-auto whitespace-pre-wrap rounded-xl bg-paper p-3 font-mono text-xs">{JSON.stringify(selected.params ?? {}, null, 2)}</pre></div>
          </div>
        </div>}
      </div>
    </aside>
  </div>
}

// The test login switches between the analyst roles (P1, CA) and the leadership roles (P3, BM) of both lanes.
// The page reloads after a switch: which app and which Forecast view to show are decided once, from /api/me.
function ViewAsSwitch({me}: {me: Me}) {
  const [busy,setBusy] = useState(false)
  const change = async (view: string) => {
    if (busy || view === me.view_as || (view !== "analyst" && view !== "leadership")) return
    setBusy(true)
    try { await setViewAs(view); window.location.reload() }
    catch (e) { toast.error(message(e), {duration: Infinity}); setBusy(false) }  // an error stays until it is dismissed
  }
  return <>
    <DropdownMenuSeparator/>
    <DropdownMenuLabel className="text-[11px] font-semibold uppercase tracking-[0.05em] text-muted">Test view</DropdownMenuLabel>
    <DropdownMenuRadioGroup value={me.view_as ?? "analyst"} onValueChange={v=>void change(v)}>
      <DropdownMenuRadioItem value="analyst" disabled={busy}>Analyst</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="leadership" disabled={busy}>Leadership</DropdownMenuRadioItem>
    </DropdownMenuRadioGroup>
  </>
}

function AccountMenu({me}: {me: Me}) {
  const {openSurvey, openSuggest, signOut, surveyDone} = useFeedbackActions()
  const name = me.name.trim() || "Account"  // brief-008 FR-012: the name only, never a lane or role list
  return <DropdownMenu>
    <DropdownMenuTrigger aria-label={`Account: ${name}`} className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-ink transition hover:bg-paper">
      <Icon name="user" className="h-5 w-5 text-muted sm:hidden"/><span className="hidden max-w-[240px] truncate sm:inline">{name}</span>
      <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-muted" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" className="w-72">
      <DropdownMenuLabel><span className="block truncate text-sm font-medium">{name}</span><span className="block text-xs font-normal text-muted">{me.auth_mode==="dev" ? "Development sign-in" : "Signed in"}</span></DropdownMenuLabel>
      {me.tester && <ViewAsSwitch me={me}/>}
      <DropdownMenuSeparator/>
      <DropdownMenuItem onSelect={openSuggest}>Suggest an improvement</DropdownMenuItem>
      <DropdownMenuItem onSelect={openSurvey}><span className="flex-1">Platform questionnaire</span><span className="text-[11px] text-muted">{surveyDone ? "Update" : "1 min"}</span></DropdownMenuItem>
      <DropdownMenuItem onSelect={signOut}>Sign out</DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
}

// Data classification of a tab or view (core-009): a quiet text label from classification.json, the way a
// document carries its marking. Only Sensitive, the highest level, takes a colour. No enforcement here.
let classificationCache: Promise<Classification | null> | null = null
function useClassification(): Classification | null {
  const [c,setC] = useState<Classification | null>(null)
  useEffect(()=>{
    classificationCache ??= getClassification().catch(()=>null)
    let live = true
    void classificationCache.then(v=>{ if (live) setC(v) })
    return ()=>{ live = false }
  },[])
  return c
}
function ClassLabel({tab}: {tab: string}) {
  const c = useClassification()
  const id = c?.tabs[tab]
  const level = c?.levels.find(l=>l.id===id)
  if (!level) return null
  return <span title={`${level.label}: ${level.description}`} className={`whitespace-nowrap font-sans text-[11px] font-medium uppercase tracking-[0.06em] ${level.id === "sensitive" ? "text-neg" : "text-muted"}`}>
    <span className="sr-only">Data classification: </span>{level.label}
  </span>
}

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : value.toLocaleString("en-US", { maximumFractionDigits: 1 })
}

function forecastReviewLabel(status: string): string {
  if (status === "not_submitted") return "Draft — submit to Brand Manager"
  if (status === "pending_review") return "Awaiting Brand Manager approval"
  if (status === "approved") return "Approved"
  if (status === "returned") return "Returned — revise and resubmit"
  if (status === "rejected") return "Not approved"
  return status.replace(/_/g, " ")
}

// A status tag: a word in an outline (with a check mark when it means approved), never a filled coloured pill.
const TAG = "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium"
// A note that something was withheld or unresolved: plain words with a small warning icon, no pill and no fill
const Flag = ({children, className = ""}: {children: ReactNode, className?: string}) => <p className={`flex items-center gap-1.5 text-xs font-medium text-ink ${className}`}><Icon name="warning" className="h-3.5 w-3.5 shrink-0 text-amber"/>{children}</p>

function ForecastReport({run}: {run: ForecastRun}) {
  const report = run.report
  return <div className="space-y-4">
    <article className="pa-panel rounded-xl border border-rule bg-sheet p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted">
        <span>{forecastReviewLabel(run.review_status)}{report.investigator_mode ? ` · ${report.investigator_mode === "ollama" ? "Agent (local model)" : "Scripted"}` : ""} · written report coming soon</span>
        <ClassLabel tab={`forecast.view.${run.view}`}/>
      </div>
      {report.abstained && <Flag className="mt-3">Attribution paused</Flag>}
      <h2 className="mt-3 text-2xl">{report.headline}</h2>
      <p className="mt-1.5 text-sm text-muted">{labelTerritory(report.territory_id)} · week ending {labelWeek(report.week_ending)} · {report.window_weeks}-week window</p>
      <dl className="mt-5 grid grid-cols-3 divide-x divide-rule border-y border-rule">{[["Forecast",report.forecast_trx],["Actual",report.actual_trx],["Variance",report.variance_trx]].map(([label,value])=><div key={String(label)} className="px-4 py-3 first:pl-0"><dt className="text-xs text-muted">{label} TRx</dt><dd className="mt-0.5 font-display text-2xl font-bold tabular-nums">{formatNumber(value as number | null)}</dd></div>)}</dl>
      {report.variance_pct !== null && report.variance_pct !== undefined && <p className="mt-3 text-sm text-muted tabular-nums">Variance {(report.variance_pct * 100).toFixed(1)}% · residual {formatNumber(report.residual_trx)} TRx · verification {report.verification?.verdict ?? "—"}</p>}
    </article>
    <section className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">Drivers</h3>{report.drivers.length ? <ul className="mt-2 divide-y divide-rule">{report.drivers.map(d=><li key={d.driver} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5 text-sm"><span className="capitalize">{d.driver}</span><span className="tabular-nums text-muted"><span className="text-ink">{formatNumber(d.impact_trx)} TRx</span> · {d.confidence}</span></li>)}</ul> : <p className="mt-2 text-sm text-muted">No driver attribution is shown because the data-quality gate paused this run.</p>}</section>
    {!!report.caveats.length && <Notice tone="warn" title="Caveats" className="p-6"><ul className="mt-2 list-disc space-y-1 pl-5">{report.caveats.map(c=><li key={c}>{c}</li>)}</ul></Notice>}
    {!!report.what_to_check.length && <section className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">What to check next</h3><ul className="mt-2 divide-y divide-rule">{report.what_to_check.map(c=><li key={c.question} className="py-3 text-sm"><p className="font-medium">{c.question}</p><p className="mt-1 text-muted">{c.why}</p><p className="mt-1 text-xs text-muted">Owner: <span className="text-ink">{c.owner}</span></p></li>)}</ul></section>}
    {run.view === "analyst" && run.stages && <section className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">How this explanation was made</h3><ol className="mt-2 divide-y divide-rule">{run.stages.map(s=><li key={s.stage} className="flex items-baseline justify-between gap-3 py-2 text-sm"><span><span className="mr-2 tabular-nums text-muted">{s.stage}</span>{s.name}</span><span className="text-xs text-muted">{s.status}</span></li>)}</ol></section>}
  </div>
}


// A question run (fcst-001): the answer is code-written sections; the analyst also sees how the agent decided.
// Seconds since `since` (an ISO time or a mount time), ticking every second while `on`.
function useElapsed(on: boolean, since?: string | null): number {
  const [start] = useState(() => Date.now())
  const [, tick] = useState(0)
  useEffect(()=>{ if (!on) return; const t = setInterval(()=>tick(x=>x + 1), 1000); return ()=>clearInterval(t) }, [on])
  const from = since ? Date.parse(since) : start
  return Math.max(0, Math.round((Date.now() - (Number.isNaN(from) ? start : from)) / 1000))
}

// The investigation's steps, as a checklist: each step once, running or done with its time.
function StepList({progress}: {progress: { tool: string; args: Record<string, unknown>; result: string }[]}) {
  const steps: { name: string; how: string; done?: string }[] = []
  for (const p of progress) {
    if (p.tool !== "step") continue
    const name = String(p.args.step ?? "")
    const cur = steps.find(x=>x.name === name)
    if (p.result.startsWith("done")) { if (cur) cur.done = p.result.replace("done in ", "") } else if (!cur) steps.push({name, how: p.result})
  }
  const tools = progress.filter(p=>p.tool !== "step")
  return <ol className="space-y-1.5 text-sm">{steps.map(x=><li key={x.name} className="flex items-baseline justify-between gap-3"><span className={x.done ? "text-muted" : "text-ink"}>{x.done ? "✓ " : "… "}{x.name}<span className="ml-2 text-xs text-muted">{x.how}</span></span><span className="text-xs tabular-nums text-muted">{x.done ?? "running"}</span></li>)}
    {!!tools.length && <li className="text-xs text-muted">{tools.length} investigator tool call{tools.length === 1 ? "" : "s"}</li>}</ol>
}

type Kpis = { forecast: number; actual: number; miss: number; miss_pct?: number; scope: string }
function KpiBoxes({k}: {k: Kpis}) {
  return <div className="my-2"><dl className="grid grid-cols-3 divide-x divide-rule border-y border-rule">{([["Forecast", k.forecast], ["Actual", k.actual], ["Miss", k.miss]] as const).map(([label, value])=><div key={label} className="px-4 py-3 first:pl-0"><dt className="text-xs text-muted">{label} TRx</dt><dd className="mt-0.5 font-display text-2xl font-bold tabular-nums">{formatNumber(value)}</dd></div>)}</dl>
    <p className="mt-1.5 text-xs text-muted">{k.scope}{k.miss_pct !== undefined ? ` · ${Math.abs(k.miss_pct).toFixed(1)}% ${k.miss < 0 ? "below" : "above"} forecast` : ""}</p></div>
}

function SectionText({text, charts, kpis, passages}: {text: string, charts?: Record<string, ChartSpec>, kpis?: Record<string, Kpis>, passages?: Record<string, { title: string; text: string }>}) {
  const out: ReactNode[] = []
  let items: string[] = []
  const flush = () => { if (items.length) { out.push(<ul key={`u${out.length}`} className="list-disc space-y-1 pl-5">{items.map((t,i)=><li key={i}>{t}</li>)}</ul>); items = [] } }
  text.split("\n").forEach((line, i) => {
    // The investigation's own verified passage, inserted by code: shown as a quoted block with its heading.
    const passage = /^\s*\[\[block (F\d+) ([a-z_]+)\]\]\s*$/.exec(line)
    if (passage) { flush(); const p = passages?.[`${passage[1]} ${passage[2]}`]; if (p) out.push(<div key={`b${i}`} className="border-l-2 border-rule pl-4"><p className="text-xs font-medium uppercase tracking-[0.06em] text-muted">{p.title}</p><SectionText text={p.text}/></div>); return }
    const boxes = /^\s*\[\[kpis (F\d+)\]\]\s*$/.exec(line)
    if (boxes) { flush(); const k = kpis?.[boxes[1]]; if (k) out.push(<KpiBoxes key={`k${i}`} k={k}/>); return }
    const marker = /^\s*\[\[chart (F\d+) ([a-z]+)\]\]\s*$/.exec(line)
    if (marker) { flush(); const spec = charts?.[`${marker[1]} ${marker[2]}`]; if (spec) out.push(<ForecastChart key={`c${i}`} spec={spec}/>); return }
    if (line.startsWith("- ")) items.push(line.slice(2)); else { flush(); if (line.trim()) out.push(<p key={`p${i}`}>{line}</p>) } })
  flush()
  return <div className="mt-2 space-y-3 text-sm leading-relaxed">{out}</div>
}

const ENGINE_LABEL = (mode?: string) => !mode ? "" : mode === "rules" ? "Rules investigation" : mode === "code" ? "Code only" : mode.startsWith("agent") ? `Agent · ${mode.replace(/^agent \(|\)$/g, "").replace(/\) with rules fallback$/, " · rules fallback")}` : mode
const CONF_TONE: Record<string, string> = { high: "text-ink", medium: "text-ink", low: "text-amber", inconclusive: "text-amber" }


// ---- Reports (fcst-002): the report on the left, the findings to pin on the right ---------------------------------
let pendingReport: string | null = null  // a report just created or opened from a run, shown when the Reports tab mounts
let pendingRun: string | null = null     // a run to open when the workbench mounts (from a report's "back to the question")

const KIND_LABEL: Record<string, string> = { run: "investigation", rerun: "rerun", weekly: "week by week", explain: "explanation", chart: "chart", drill: "where the gap sits" }

function ReportEditor({id, analyst, canPreview, onBack, onOpenRun}: {id: string, analyst: boolean, canPreview: boolean, onBack: () => void, onOpenRun: (runId: string) => void}) {
  const [r,setR] = useState<ReportView | null>(null)
  const [runs,setRuns] = useState<ForecastSummary[]>([])
  const [addRun,setAddRun] = useState("")
  const [instruction,setInstruction] = useState("")
  const [note,setNote] = useState("")
  const [preview,setPreview] = useState(false)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState<string | null>(null)
  const autoDrafted = useRef<string | null>(null)
  const act = async (f: () => Promise<ReportView | void>) => { setBusy(true); setError(null); try { const v = await f(); if (v) setR(v) } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  const editable = analyst && !preview && !!r && (r.review_status === "not_submitted" || r.review_status === "returned")
  const drafting = r?.job?.status === "drafting"
  const draftSecs = useElapsed(drafting, r?.job?.started_at)
  useEffect(()=>{ void act(()=>openReport(id, preview)) }, [id, preview])
  useEffect(()=>{ if (!editable) return; listForecasts().then(rs=>setRuns(rs.filter(x=>x.job_status === "done" && x.question))).catch(()=>{}) }, [editable])
  useEffect(()=>{ if (!drafting) return; const t = setInterval(()=>{ openReport(id).then(setR).catch(()=>{}) }, 2000); return ()=>clearInterval(t) }, [drafting, id])
  // The report follows its pins: when they changed, it redrafts by itself (once per change).
  useEffect(()=>{ if (!r || !editable || drafting || !r.stale) return; const key = `${r.version}:${(r.findings ?? []).map(f=>f.id).join(",")}`; if (autoDrafted.current === key) return; autoDrafted.current = key; void act(()=>draftReport(id)) }, [r?.stale, r?.version, drafting, editable])
  if (!r) return <div className="space-y-3"><button className="flex items-center gap-1.5 text-sm text-primaryink hover:underline" onClick={onBack}><Icon name="back" className="h-4 w-4"/>All reports</button>{error ? <Notice tone="error" role="alert">{error}</Notice> : <ListSkeleton/>}</div>
  const unpin = async (runId: string, fid?: string) => { if (!fid) return; setBusy(true); setError(null); try { await unpinFollowup(runId, fid); setR(await openReport(id)) } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  const reportPane = <div className="min-w-0 space-y-4">
    <article className="pa-panel rounded-xl border border-rule bg-sheet p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-muted"><span>{forecastReviewLabel(r.review_status)}{r.version ? ` · version ${r.version}` : ""}{r.author ? ` · ${r.author === "model" ? "drafted by the model" : r.author === "code" ? "assembled by code" : "edited"}` : ""}</span><ClassLabel tab={analyst && !preview ? "forecast.view.analyst" : "forecast.view.leadership"}/></div>
      <h2 className="mt-2 text-2xl">{r.title}</h2>
      {!!r.sources.length && <p className="mt-1 text-xs text-muted">From: {r.sources.map(s=>s.scope).join(" · ")}</p>}
      {r.review_note && <Notice tone="warn" title="Brand Manager review note" className="mt-3">{r.review_note}</Notice>}
    </article>
    {drafting && <div role="status" className="rounded-xl border border-rule bg-paper px-5 py-4 text-sm text-ink">{r.job?.step ?? "Drafting"}{r.model ? ` (${modelName(r.model)})` : ""}<span aria-hidden="true"> · {draftSecs} s</span>. Code places every figure, table and chart and checks each paragraph before it appears.{r.model?.startsWith("ollama:") ? " A local model takes a minute or two." : ""}</div>}
    {r.job?.status === "failed" && r.job.message && <Notice tone="error" role="alert">{r.job.message} The last good version is kept.</Notice>}
    {!r.sections.length && !drafting && <p className="text-sm text-muted">No draft yet.</p>}
    {r.sections.map((sec,i)=><section key={i} className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">{sec.title}</h3><SectionText text={sec.text} charts={r.charts} kpis={r.kpis} passages={r.blocks}/></section>)}
    {editable && <section className={`${PANEL} space-y-3 p-5`}>
      <form onSubmit={e=>{ e.preventDefault(); const t = instruction.trim(); if (t) void act(async()=>{ const v = await draftReport(id, t); setInstruction(""); return v }) }} className="flex flex-col gap-2 sm:flex-row">
        <input value={instruction} onChange={e=>setInstruction(e.target.value)} maxLength={500} disabled={busy || drafting || !r.model} placeholder={r.model ? "Ask for a revision, e.g. shorter, lead with the Southeast, put the chart first" : "Revising by request needs a language model on the server"} className={`${FIELD} flex-1`}/>
        <button type="submit" disabled={busy || drafting || !r.model || !instruction.trim()} className={BTN2}>Revise</button>
      </form>
      {!!r.versions?.length && <details><summary className="cursor-pointer text-xs text-muted">Versions ({r.versions.length})</summary><ol className="mt-2 space-y-1 text-xs">{[...r.versions].reverse().map(v=><li key={v.n} className="flex flex-wrap items-baseline justify-between gap-2"><span><span className="tabular-nums">{v.n}</span> · {v.author} · {v.instruction ?? "first draft"}</span>{v.n !== r.version && <button type="button" disabled={busy || drafting} onClick={()=>void act(()=>restoreReportVersion(id, v.n))} className="text-primaryink hover:underline">Restore</button>}</li>)}</ol></details>}
      <div className="flex justify-end border-t border-rule pt-4"><button type="button" disabled={busy || drafting || !r.version || !!r.stale} onClick={()=>void act(()=>submitReport(id))} className={BTN}>Submit to Brand Manager</button></div>
    </section>}
    {!analyst && r.review_status === "pending_review" && <section className={`${PANEL} p-5`}>
      <label className={LABEL}>Review note (needed to return or reject)<textarea value={note} onChange={e=>setNote(e.target.value)} className={`${FIELD} mt-0.5`} rows={3}/></label>
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <button disabled={busy || !note.trim()} onClick={()=>void act(()=>reviewReport(id, "rejected", note))} className={BTN2}>Reject</button>
        <button disabled={busy || !note.trim()} onClick={()=>void act(()=>reviewReport(id, "returned", note))} className={BTN2}>Return</button>
        <button disabled={busy} onClick={()=>void act(()=>reviewReport(id, "approved", note))} className={BTN}>Approve</button>
      </div>
    </section>}
  </div>
  const sourceIds = (r.runs ?? []).map(x=>x.run_id)
  const contentsPane = <aside className="min-w-0 space-y-4 lg:sticky lg:top-4 lg:self-start">
    <section className={`${PANEL} p-5`}>
      <h3 className="text-sm font-semibold">Report contents</h3>
      <p className="mt-1 text-xs text-muted">Everything pinned on the question pages. The report is drafted from all of it and updates when the pins change.</p>
      {(r.runs ?? []).map(run=><div key={run.run_id} className="mt-4">
        <div className="flex items-baseline justify-between gap-2"><p className="min-w-0 text-xs font-medium text-muted">{run.question}</p>
          <span className="flex shrink-0 gap-3 text-xs"><button type="button" onClick={()=>onOpenRun(run.run_id)} className="text-primaryink hover:underline">Pin more</button>{run.run_id !== sourceIds[0] && <button type="button" disabled={busy || drafting} onClick={()=>void act(()=>removeReportRun(id, run.run_id))} className="text-muted hover:text-ink">Remove</button>}</span></div>
        <ul className="mt-1 divide-y divide-rule text-sm">{(r.findings ?? []).filter(f=>f.source.run_id === run.run_id).map(f=><li key={f.id} className="flex items-baseline justify-between gap-3 py-2"><span className="min-w-0"><span className="mr-2 text-xs text-muted">{f.id}</span>{f.kind === "run" ? "The investigation" : f.question ?? f.title}<span className="block text-xs text-muted">{KIND_LABEL[f.kind] ?? f.kind} · {f.scope}</span></span>{f.kind !== "run" && editable && <button type="button" disabled={busy || drafting} onClick={()=>void unpin(f.source.run_id, f.source.followup_id)} className="shrink-0 text-xs text-muted hover:text-ink">Unpin</button>}</li>)}</ul>
      </div>)}
      {editable && runs.filter(x=>!sourceIds.includes(x.forecast_run_id)).length > 0 && <div className="mt-5 flex flex-col gap-2 border-t border-rule pt-4 sm:flex-row">
        <select value={addRun} onChange={e=>setAddRun(e.target.value)} disabled={busy} className={`${FIELD} flex-1`}><option value="">Add another question's pinned content…</option>{runs.filter(x=>!sourceIds.includes(x.forecast_run_id)).map(x=><option key={x.forecast_run_id} value={x.forecast_run_id}>{x.question}</option>)}</select>
        <button type="button" disabled={busy || !addRun} onClick={()=>void act(async()=>{ const v = await addReportRun(id, addRun); setAddRun(""); return v })} className={BTN2}>Add</button>
      </div>}
    </section>
  </aside>
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3"><button disabled={busy} className="flex items-center gap-1.5 text-sm text-primaryink hover:underline" onClick={onBack}><Icon name="back" className="h-4 w-4"/>All reports</button>{canPreview && <ViewToggle value={preview ? "leadership" : "analyst"} busy={busy} onChange={v=>setPreview(v === "leadership")}/>}</div>
    {error && <Notice tone="error" role="alert">{error}</Notice>}
    {/* Contents left, report right (like source and preview); on a phone the report comes first. */}
    {editable ? <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]"><div className="order-2 min-w-0 lg:order-1">{contentsPane}</div><div className="order-1 min-w-0 lg:order-2">{reportPane}</div></div> : reportPane}
  </div>
}

function ForecastReports({me, onOpenRun, approvedOnly=false}: {me: Me, onOpenRun: (runId: string) => void, approvedOnly?: boolean}) {
  const r = me.lanes.forecast
  const analyst = !!r?.actions.includes("run")
  const canPreview = analyst && !!r?.views.includes("leadership")
  const [rows,setRows] = useState<ReportSummary[] | null>(null)
  const [open,setOpen] = useState<string | null>(()=>{ const p = pendingReport; pendingReport = null; return p })
  const [error,setError] = useState<string | null>(null)
  useEffect(()=>{ if (!open) listReports().then(rs=>setRows(approvedOnly ? rs.filter(x=>x.review_status === "approved") : rs)).catch(e=>setError(message(e))) }, [open, approvedOnly])
  if (open) return <ReportEditor id={open} analyst={analyst} canPreview={canPreview} onBack={()=>setOpen(null)} onOpenRun={onOpenRun}/>
  return <div className="space-y-6">
    {error && <Notice tone="error" role="alert">{error}</Notice>}
    {analyst && !approvedOnly && <p className="text-sm text-muted">A report starts from a question: investigate it under New explanation, pin the follow-ups you want, then choose Create report. The model drafts from everything pinned, you ask for revisions, and code checks every number before the Brand Manager sees it.</p>}
    <section><h3 className="text-sm font-semibold">{approvedOnly ? "Approved reports" : analyst ? "Your reports" : "Reports"}</h3>{rows === null ? <div className="mt-2"><ListSkeleton/></div> : rows.length ? <ul className={`${PANEL} pa-stagger mt-2 divide-y divide-rule`}>{(analyst ? rows : [...rows].sort((a,b)=>Number(b.review_status === "pending_review") - Number(a.review_status === "pending_review"))).map(x=><li key={x.id}><button onClick={()=>setOpen(x.id)} className="group flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left transition-colors hover:bg-paper/60"><span className="min-w-0"><span className="block text-sm">{x.title}</span><span className="mt-0.5 block text-xs text-muted tabular-nums">{x.findings} pinned item{x.findings === 1 ? "" : "s"}{x.version ? ` · version ${x.version}` : ""} · {forecastReviewLabel(x.review_status)}</span></span><Icon name="chevronRight" className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-primaryink"/></button></li>)}</ul> : <p className="mt-2 text-sm text-muted">{approvedOnly ? "No approved reports yet. They appear here once the Brand Manager approves one." : analyst ? "No reports yet." : "Nothing has been submitted yet."}</p>}</section>
  </div>
}

const FOLLOWUP_EXAMPLES = ["Why was this driver accepted?", "Show it week by week", "Plot it by territory", "Split the gap by plan and specialty", "Drop South Central from the controls and rerun", "Same question for Pacific"]

const PINNABLE_OPS = new Set(["rerun", "weekly", "explain", "chart", "drill"])

function ForecastFollowups({run, onAsk, onOpen, onPin}: {run: ForecastRun, onAsk: (q: string) => Promise<void>, onOpen: (id: string) => void, onPin?: (followupId: string, pin: boolean) => Promise<void>}) {
  const [text,setText] = useState("")
  const [sending,setSending] = useState(false)
  const send = async (q: string) => { if (q.trim().length < 3) return; setSending(true); try { await onAsk(q.trim()); setText("") } finally { setSending(false) } }
  const items = run.followups ?? []
  return <section className="pa-panel rounded-xl border border-rule bg-sheet p-6">
    <h3 className="text-sm font-semibold">Follow-up questions</h3>
    <p className="mt-1 text-xs text-muted">Ask about this answer: rerun it elsewhere, drop control territories, explain a decision, show it by week, plot it, or split an unexplained gap. Code computes every number. The investigation above always goes into this question's report; pin the follow-ups you want in it too.</p>
    {!!items.length && <ol className="mt-4 space-y-4">{items.map(f=><li key={f.id} className="text-sm">
      <p className="font-medium">{f.question}</p>
      {f.status === "running" ? <p className="mt-1 text-muted">Working…</p> : <div className="mt-1 rounded-lg bg-paper px-3 py-2">{f.chart && f.op === "chart" ? <ForecastChart spec={f.chart}/> : <><SectionText text={f.answer ?? ""}/>{f.chart && <div className="mt-2"><ForecastChart spec={f.chart}/></div>}</>}<div className="mt-2 flex flex-wrap gap-4 text-xs">{f.child_run_id && <button type="button" onClick={()=>onOpen(f.child_run_id!)} className="text-primaryink hover:underline">Open the full rerun</button>}
        {onPin && f.status === "done" && f.op && PINNABLE_OPS.has(f.op) && (run.pins?.includes(f.id)
          ? <button type="button" onClick={()=>void onPin(f.id, false)} className="text-primaryink">Pinned to the report · unpin</button>
          : <button type="button" onClick={()=>void onPin(f.id, true)} className="text-muted hover:text-ink">Pin to the report</button>)}</div></div>}
    </li>)}</ol>}
    <form onSubmit={e=>{ e.preventDefault(); void send(text) }} className="mt-4 flex flex-col gap-2 sm:flex-row">
      <input value={text} onChange={e=>setText(e.target.value)} maxLength={300} disabled={sending} placeholder="e.g. Drop South Central from the controls and rerun" className={`${FIELD} flex-1`}/>
      <button type="submit" disabled={sending || text.trim().length < 3} className={BTN}>{sending ? "Asking…" : "Ask"}</button>
    </form>
    <div className="mt-2 flex flex-wrap gap-2">{FOLLOWUP_EXAMPLES.map(q=><button key={q} type="button" disabled={sending} onClick={()=>void send(q)} className="rounded-lg border border-edge px-3 py-1.5 text-xs text-muted transition-colors hover:bg-paper hover:text-ink disabled:opacity-60">{q}</button>)}</div>
  </section>
}

function ForecastQuestionReport({run, onFollowup, onOpen, onPin}: {run: ForecastRun, onFollowup?: (q: string) => Promise<void>, onOpen?: (id: string) => void, onPin?: (followupId: string, pin: boolean) => Promise<void>}) {
  const report = run.report
  const running = run.job_status === "running"
  const elapsed = useElapsed(running)
  const analystView = run.view === "analyst"
  if (run.job_status === "failed") return <Notice tone="error" role="alert">The investigation failed: {run.job_error ?? "unknown error"}. Ask again, or rephrase the question.</Notice>
  return <div className="space-y-4">
    <article className="pa-panel rounded-xl border border-rule bg-sheet p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted">
        <span>{forecastReviewLabel(run.review_status)}{report.investigator_mode ? ` · ${ENGINE_LABEL(report.investigator_mode)}` : ""}{report.summary_by === "model" ? " · summary worded by the model" : ""}</span>
        <ClassLabel tab={`forecast.view.${run.view}`}/>
      </div>
      {report.question && <p className="mt-3 text-sm text-muted">“{report.question}”</p>}
      {report.abstained && !running && <Flag className="mt-3">{report.out_of_scope ? "Out of scope" : "Attribution paused"}</Flag>}
      <h2 className="mt-2 text-2xl">{running ? "Investigating…" : report.headline}</h2>
      {!running && report.week_start && <p className="mt-1.5 text-sm text-muted">{labelTerritory(report.territory_id)} · {report.window_weeks === 1 ? `week of ${labelWeek(report.week_start)}` : `${report.window_weeks} weeks from ${labelWeek(report.week_start)}`}{report.set_aside_weeks?.length ? ` · ${report.set_aside_weeks.length} provisional week${report.set_aside_weeks.length > 1 ? "s" : ""} set aside` : ""}</p>}
      {!running && report.forecast_trx !== null && report.forecast_trx !== undefined && <dl className="mt-5 grid grid-cols-3 divide-x divide-rule border-y border-rule">{[["Forecast",report.forecast_trx],["Actual",report.actual_trx],["Miss",report.variance_trx]].map(([label,value])=><div key={String(label)} className="px-4 py-3 first:pl-0"><dt className="text-xs text-muted">{label} TRx</dt><dd className="mt-0.5 font-display text-2xl font-bold tabular-nums">{formatNumber(value as number | null)}</dd></div>)}</dl>}
      {!running && report.summary && report.summary.trim() !== report.headline.trim() && <p className="mt-4 text-sm leading-relaxed">{report.summary.startsWith(report.headline) ? report.summary.slice(report.headline.length).trim() : report.summary}</p>}
      {running && <div className="mt-4 space-y-3">
        <p className="text-sm text-muted">Working for {elapsed} s. Steps appear as they finish; every number is computed by code. With local Qwen, the steps marked "with the model" take the longest.</p>
        {analystView && !!run.progress?.length && <StepList progress={run.progress}/>}
      </div>}
    </article>
    {!running && !!report.charts_shown?.length && <section className="space-y-3">{report.charts_shown.map(k=>report.charts?.[k] && <ForecastChart key={k} spec={report.charts[k]} standalone/>)}{analystView && <p className="text-xs text-muted">{report.charts_by === "model" ? "Chart chosen by the model for this question; drawn from the answer's own numbers." : "Default chart for this kind of question; drawn from the answer's own numbers."}</p>}</section>}
    {!running && !!report.drivers.length && <section className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">Drivers</h3><ul className="mt-2 divide-y divide-rule">{report.drivers.map(d=><li key={(d.label ?? d.driver) + d.impact_trx} className="py-2.5 text-sm"><div className="flex flex-wrap items-baseline justify-between gap-2"><span>{d.label ?? d.driver}</span><span className="tabular-nums text-muted"><span className="text-ink">{formatNumber(d.impact_trx)} TRx</span> · <span className={CONF_TONE[d.confidence] ?? ""}>{d.confidence}</span></span></div>{analystView && !!d.confidence_reasons?.length && <p className="mt-1 text-xs text-muted">{d.confidence_reasons.join("; ")}</p>}</li>)}
      {report.bias_trx !== null && report.bias_trx !== undefined && <li className="flex flex-wrap items-baseline justify-between gap-2 py-2.5 text-sm text-muted"><span>Usual forecast bias</span><span className="tabular-nums">{formatNumber(report.bias_trx)} TRx</span></li>}
      {report.residual_trx !== null && report.residual_trx !== undefined && <li className="flex flex-wrap items-baseline justify-between gap-2 py-2.5 text-sm"><span>Unexplained residual</span><span className="tabular-nums">{formatNumber(report.residual_trx)} TRx</span></li>}</ul></section>}
    {!running && report.sections?.map(sec=><section key={sec.id} className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">{sec.title}</h3><SectionText text={sec.text}/></section>)}
    {!running && analystView && !!report.decisions?.length && <section className="pa-panel rounded-xl border border-rule bg-sheet p-6"><h3 className="text-sm font-semibold">How the investigation decided</h3><p className="mt-1 text-xs text-muted">Each decision, who made it and why. Reasons are words only: the agent cannot write a number.</p><ol className="mt-3 space-y-2">{report.decisions.map((d,i)=><li key={i} className="text-sm"><span className={`${TAG} mr-2 ${d.by.startsWith("agent") ? "border-edge text-ink" : "border-rule text-muted"}`}>{d.by}</span><span className="font-medium">{d.action.replace(/_/g, " ")}</span> <span className="text-muted">{d.target}</span><p className="mt-0.5 text-muted">{d.reason}</p></li>)}</ol></section>}
    {!running && analystView && !!report.comparisons?.length && <details className="pa-panel rounded-xl border border-rule bg-sheet p-6"><summary className="cursor-pointer text-sm font-semibold">Comparisons run ({report.comparisons.length})</summary><ul className="mt-3 space-y-3 text-xs">{report.comparisons.map(c=><li key={c.id}><p className="font-medium">{c.id} · {c.episode} · {c.method.replace(/_/g, " ")}{c.flags.length ? ` · flags: ${c.flags.join(", ")}` : ""}</p>{!!c.controls.length && <p className="text-muted">Controls: {c.controls.map(labelTerritory).join(", ")}</p>}<p className="text-muted tabular-nums">{Object.entries(c.stats).flatMap(([k,v])=>v && typeof v === "object" && !Array.isArray(v) ? Object.entries(v as Record<string, unknown>) : [[k,v] as [string, unknown]]).filter(([,v])=>v !== null && v !== undefined && typeof v !== "object").map(([k,v])=>`${k.replace(/_/g, " ")} ${String(v)}`).join(" · ")}</p></li>)}</ul></details>}
    {!running && analystView && report.verification?.checks && <p className="text-xs text-muted">Verification {report.verification.verdict}: {report.verification.checks.map(c=>`${c.detail} (${c.status})`).join("; ")}.</p>}
    {!running && analystView && run.job_status === "done" && onFollowup && onOpen && <ForecastFollowups run={run} onAsk={onFollowup} onOpen={onOpen} onPin={onPin}/>}
  </div>
}

// Each workspace keeps its sub-pages (a new run, the approved list) as tabs inside the page, not in the sidebar.
// The third item of an option is its classification key (core-009); the current tab's label sits at the row's end.
// Tabs by the APG pattern: one tab stop (the selected tab), Left/Right/Home/End move focus along the row, Enter or
// Space selects. `panelId` (optional) names the tabpanel the page renders under the row; the selected tab labels it
// (id `${panelId}-tab-${key}`). The sliding pill is decoration.
function SubTabs<T extends string>({label, value, options, onChange, panelId, aside}: {label: string, value: T, options: readonly (readonly [T, string, string?])[], onChange: (v: T) => void, panelId?: string, aside?: ReactNode}) {
  const current = options.find(o => o[0] === value)
  const list = useRef<HTMLDivElement>(null)
  const [bar,setBar] = useState<{left: number, top: number, width: number, height: number} | null>(null)
  const measure = () => {  // the pill sits behind the selected tab, wherever the row has wrapped to
    const el = list.current?.querySelector<HTMLElement>('[aria-selected="true"]')
    if (el) setBar({left: el.offsetLeft, top: el.offsetTop, width: el.offsetWidth, height: el.offsetHeight})
  }
  useLayoutEffect(measure,[value, options.length])
  useEffect(()=>{ const row = list.current; if (!row || typeof ResizeObserver === "undefined") return; const ro = new ResizeObserver(measure); ro.observe(row); return ()=>ro.disconnect() },[])
  const onKey = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    const tabs = Array.from(list.current?.querySelectorAll<HTMLElement>('[role="tab"]') ?? [])
    const at = tabs.indexOf(document.activeElement as HTMLElement)
    if (at < 0) return
    const to = e.key === "ArrowRight" ? (at + 1) % tabs.length : e.key === "ArrowLeft" ? (at + tabs.length - 1) % tabs.length : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : -1
    if (to < 0) return
    e.preventDefault(); tabs[to].focus()
  }
  return <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
    {/* The row wraps rather than scrolls, so at 320 px or 200% zoom no tab sits past an edge */}
    <div ref={list} role="tablist" aria-label={label} onKeyDown={onKey} className="pa-noprint relative flex min-w-0 flex-wrap gap-0.5 sm:gap-1">
      {options.map(([key, text]) => <button key={key} type="button" role="tab" aria-selected={value === key} tabIndex={value === key ? 0 : -1}
        id={panelId ? `${panelId}-tab-${key}` : undefined} aria-controls={panelId && value === key ? panelId : undefined} onClick={() => onChange(key)}
        className={`relative z-10 whitespace-nowrap rounded-lg px-3 py-2 text-sm sm:px-4 font-medium transition-colors duration-200 ${value === key ? "font-semibold text-primaryink" : "text-muted hover:text-ink"}`}>{text}</button>)}
      {bar && <span aria-hidden="true" className="pa-tabbar absolute rounded-lg border border-edge bg-paper shadow-[0_3px_0_var(--color-slab)]" style={{left: bar.left, top: bar.top, width: bar.width, height: bar.height}}/>}
    </div>
    {/* `aside` (the Briefing brand picker) sits left of the classification label */}
    {(aside || current?.[2]) && (
      <div className="flex shrink-0 items-center gap-4">
        {aside}
        {current?.[2] && <ClassLabel tab={current[2]}/>}
      </div>
    )}
  </div>
}

// Analyst view / Leadership preview: a small neutral switch; the open view's classification is on the report itself.
function ViewToggle({value, busy=false, onChange}: {value: "analyst" | "leadership", busy?: boolean, onChange: (v: "analyst" | "leadership") => void}) {
  // Two toggle buttons in a labelled group (aria-pressed), not tabs: nothing here is a panel. The open view stays
  // focusable; pressing it again does nothing. While busy, aria-disabled keeps the focused button where it is.
  return <div role="group" aria-label="View" aria-busy={busy} className="inline-flex gap-0.5 rounded-lg border border-edge p-0.5">
    {(["analyst", "leadership"] as const).map(v => <button key={v} type="button" aria-pressed={value === v} aria-disabled={busy || undefined} onClick={() => { if (!busy && value !== v) onChange(v) }}
      className={`rounded-[10px] px-3 py-1.5 text-xs font-medium transition-colors ${value === v ? "bg-primary font-semibold text-onprimary" : "text-muted hover:text-ink"} ${busy ? "cursor-not-allowed opacity-70" : ""}`}>
      {v === "analyst" ? "Analyst view" : "Leadership preview"}</button>)}
  </div>
}

const FORECAST_INTENTS: [string, string][] = [
  ["reliability", "Is the miss real, or a data issue?"], ["screen", "Rank the largest gaps"], ["where", "Where is the miss concentrated?"],
  ["drivers", "Which drivers plausibly contributed?"], ["attribution", "How much does each driver explain?"],
  ["unknowns", "How confident are we, and what is unexplained?"], ["next_checks", "What should be checked next, and by whom?"],
  ["assumptions", "Should forecast assumptions be reviewed?"], ["audit", "Can every finding be verified?"], ["communicate", "A summary for leadership"],
]

const FORECAST_EXAMPLES = [
  "Week of 2026-08-24: How much of the miss does each driver explain?",
  "Top 5 largest gaps in the last 3 months",
  "Mar to Sep 2026: What are the most plausible commercial drivers?",
  "Weeks of 2026-06-01 to 2026-06-29, Pacific: What supports or contradicts each hypothesis?",
  "Week of 2026-05-04, New England: Is the deviation reliable, or a data issue?",
  "Mar to Oct 2026: Should any forecast assumptions be reviewed?",
]

type ForecastSection = "workbench" | "approved" | "reports"
function ForecastWorkspace({me, section, onSection, onBusy}: {me: Me, section: ForecastSection, onSection: (s: ForecastSection) => void, onBusy?: (busy: boolean) => void}) {
  const r = me.lanes.forecast
  const analyst = !!r?.actions.includes("run")
  const canPreview = analyst && !!r?.views.includes("leadership")
  const [runs,setRuns] = useState<ForecastSummary[]>([])
  const [selected,setSelected] = useState<ForecastRun | null>(null)
  const [context,setContext] = useState<ForecastContext | null>(null)
  const [question,setQuestion] = useState("")
  const [scope,setScope] = useState<ForecastScope | null>(null)
  const [territory,setTerritory] = useState<string>("")
  const [weekFrom,setWeekFrom] = useState("")
  const [weekTo,setWeekTo] = useState("")
  const [intent,setIntent] = useState("")
  const [loading,setLoading] = useState(true)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState<string | null>(null)
  const [note,setNote] = useState("")
  // The workspace stays mounted across sub-tabs and lanes, so the open run, the scope card and the typed question
  // survive; only "All forecast questions" clears the run. The ref lets a late poll refresh the tab now showing.
  const sectionRef = useRef(section)
  sectionRef.current = section
  const [bgRunning,setBgRunning] = useState(false)  // some run of this analyst is still investigating (reported to the sidebar)
  const isRunning = (rs: ForecastSummary[]) => rs.some(x=>x.job_status === "running")
  // Match the Briefing workspace: the analyst can always return to the list of
  // their own runs, while the approved view is a strictly filtered list.
  // The workspace stays mounted, so a slow list from a section the analyst has left must not land: each refresh takes
  // a token and only the latest one may write.
  const refreshToken = useRef(0)
  const refresh = async () => { const token = ++refreshToken.current, live = () => token === refreshToken.current; setLoading(true); setError(null); try { const status = sectionRef.current === "approved" ? "approved" : analyst ? undefined : "pending_review"; const values = await Promise.all([listForecasts(status), analyst && sectionRef.current === "workbench" ? forecastContext() : Promise.resolve(null)]); if (!live()) return; setRuns(values[0]); if (values[1]) setContext(values[1]); if (analyst && !status) setBgRunning(isRunning(values[0])) } catch(e) { if (live()) setError(message(e)) } finally { if (live()) setLoading(false) } }
  useEffect(()=>{ void refresh() }, [analyst, section])
  // With no run open, a list that still shows one investigating is polled quietly until it finishes.
  useEffect(()=>{ if (!analyst || selected || !bgRunning) return; const t = setInterval(()=>{ listForecasts().then(rs=>{ setBgRunning(isRunning(rs)); if (sectionRef.current === "workbench") setRuns(rs) }).catch(()=>{}) }, 3000); return ()=>clearInterval(t) }, [analyst, selected, bgRunning])
  // Step one reads the question into a scope card; step two runs the investigation on the (possibly edited) scope.
  const readScope = async (q: string) => { setBusy(true); setError(null); try { const sc = await forecastScope({question: q}); setScope(sc); setIntent(sc.intent); setTerritory(sc.territory); setWeekFrom(sc.weeks[0] ?? ""); setWeekTo(sc.weeks[sc.weeks.length - 1] ?? "") } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  const onAsk = async (event: React.FormEvent) => { event.preventDefault(); if (question.trim().length >= 3) await readScope(question.trim()) }
  // The confirmed scope always travels with the question, so the run uses exactly what the analyst saw.
  const investigate = async () => { if (!scope) return; setBusy(true); setError(null); try { setSelected(await askForecast({question: scope.question, territory_id: territory, week_from: weekFrom || null, week_to: weekTo || null, intent: intent || null})); setScope(null); await refresh() } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  const pin = async (followupId: string, on: boolean) => { if (!selected) return; setError(null); try { setSelected(await (on ? pinFollowup : unpinFollowup)(selected.forecast_run_id, followupId)) } catch(e) { setError(message(e)) } }
  const toReport = async () => { if (!selected) return; setBusy(true); setError(null); try { const v = await createReport({run_id: selected.forecast_run_id}); pendingReport = v.id; onSection("reports") } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  useEffect(()=>{ if (pendingRun && section === "workbench") { const id = pendingRun; pendingRun = null; void open(id) } }, [section])
  const followup = async (q: string) => { if (!selected) return; setError(null); try { setSelected(await askFollowup(selected.forecast_run_id, q)) } catch(e) { setError(message(e)) } }
  const followupsRunning = !!selected?.followups?.some(f=>f.status === "running")
  const working = selected?.job_status === "running" || followupsRunning || bgRunning
  useEffect(()=>{ onBusy?.(working) }, [working])  // eslint-disable-line react-hooks/exhaustive-deps
  // A running investigation, or one with a follow-up in flight, is polled until it finishes.
  useEffect(()=>{ if (!selected || (selected.job_status !== "running" && !followupsRunning)) return; const id = selected.forecast_run_id, view = selected.view; const t = setInterval(()=>{ void openForecast(id, view).then(r=>{ setSelected(cur => cur && cur.forecast_run_id === id ? r : cur); if (r.job_status !== "running" && !r.followups?.some(f=>f.status === "running")) { void refresh(); if (analyst) listForecasts().then(rs=>setBgRunning(isRunning(rs))).catch(()=>{}) } }).catch(()=>{}) }, 2000); return ()=>clearInterval(t) }, [selected?.forecast_run_id, selected?.job_status, selected?.view, followupsRunning])
  const open = async (id: string, view?: ForecastRun["view"]) => {
    setBusy(true)
    setError(null)
    try {
      setSelected(await openForecast(id, view))
    } catch (e) {
      setError(message(e))
    } finally {
      setBusy(false)
    }
  }
  const submit = async () => { if (!selected) return; setBusy(true); setError(null); try { setSelected(await submitForecast(selected.forecast_run_id)); await refresh() } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  const decide = async (decision: "approved" | "rejected" | "returned") => { if (!selected) return; setBusy(true); setError(null); try { setSelected(await reviewForecast(selected.forecast_run_id, decision, note)); setNote(""); await refresh() } catch(e) { setError(message(e)) } finally { setBusy(false) } }
  return <div className={`${section === "reports" ? "workspace-wide" : "workspace-content"} space-y-6 py-8 sm:py-10 pa-rise`}>
    {/* One greeting per lane: on its landing section (the same one Shell opens), with no run open */}
    {section === (analyst ? "workbench" : "reports") && !selected && <Greeting detail={context ? `Forecast versus actual, through ${labelWeek(context.latest_week)}.` : undefined}/>}
    <SubTabs label="Forecast explanation" value={section} onChange={onSection} options={(analyst
      ? [["workbench", "New explanation", "forecast.new"], ["reports", "Reports", "forecast.reports"], ["approved", "Approved reports", "forecast.approved"]]
      : [["reports", "Reports to review", "forecast.review"], ["approved", "Approved reports", "forecast.approved"]]) as readonly (readonly [ForecastSection, string, string])[]}/>
    {section !== "workbench" ? <ForecastReports key={section} me={me} approvedOnly={section === "approved"} onOpenRun={id=>{ pendingRun = id; onSection("workbench") }}/> : <>
    {error && <Notice tone="error" role="alert">{error}</Notice>}
    {selected ? <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button disabled={busy} className="flex items-center gap-1.5 text-sm text-primaryink hover:underline" onClick={()=>setSelected(null)}><Icon name="back" className="h-4 w-4"/>All forecast questions</button>
      </div>
      {selected.parent_run_id && <button type="button" disabled={busy} onClick={()=>void open(selected.parent_run_id!)} className="text-xs text-primaryink hover:underline">Follow-up rerun · back to the original report</button>}
      {selected.kind === "question" ? <ForecastQuestionReport run={selected} onFollowup={analyst ? followup : undefined} onOpen={id=>void open(id)} onPin={analyst && selected.view === "analyst" ? pin : undefined}/> : <ForecastReport run={selected}/>}
      {analyst && selected.view === "analyst" && selected.kind === "question" && selected.job_status === "done" && !selected.report.out_of_scope && <div className="flex flex-wrap items-center justify-end gap-3"><span className="text-xs text-muted">{(selected.pins?.length ?? 0) + 1} item{(selected.pins?.length ?? 0) ? "s" : ""} pinned for the report</span><button type="button" disabled={busy} onClick={()=>void toReport()} className={BTN2}>{selected.report_id ? "Open report" : "Create report"}</button></div>}
      <AnswerFeedback lane="forecast" refId={selected.forecast_run_id} view={selected.view} agent={!!selected.report.investigator_mode && !/scripted/i.test(selected.report.investigator_mode)}/>
      {analyst && selected.view === "analyst" && selected.review_status === "pending_review" && <p className="text-sm text-muted"><span className="text-ink">Submitted for Brand Manager approval.</span> It can no longer be edited; the Brand Manager can approve, return or reject it.</p>}
      {analyst && selected.view === "analyst" && section === "workbench" && selected.kind !== "question" && selected.job_status !== "running" && selected.job_status !== "failed" && (selected.review_status === "not_submitted" || selected.review_status === "returned") && <div className="flex justify-end"><button disabled={busy} onClick={()=>void submit()} className={BTN}>Submit to Brand Manager</button></div>}
      {!analyst && selected.review_status === "pending_review" && <section className={`${PANEL} p-5`}>
        <label className={LABEL}>Review note (needed to return or reject)<textarea value={note} onChange={e=>setNote(e.target.value)} className={`${FIELD} mt-0.5`} rows={3}/></label>
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button disabled={busy || !note.trim()} onClick={()=>void decide("rejected")} className={BTN2}>Reject</button>
          <button disabled={busy || !note.trim()} onClick={()=>void decide("returned")} className={BTN2}>Return</button>
          <button disabled={busy} onClick={()=>void decide("approved")} className={BTN}>Approve</button>
        </div>
      </section>}
    </> : <>{analyst && section === "workbench" && <>
      <p className="text-sm text-muted">Ask about forecast versus actual TRx for {context?.brand ?? "BXA Cardiovela"}: how big a miss is, where it sits, what drove it, and what to check.</p>
      <form onSubmit={onAsk} className={`${PANEL} space-y-4 p-6`}>
        <label className={LABEL}>Your question<textarea value={question} onChange={e=>{ setQuestion(e.target.value); setScope(null) }} disabled={busy} rows={2} maxLength={400} placeholder="e.g. Why did we miss forecast in the week of 2026-08-24?" className={`${FIELD} mt-0.5`}/></label>
        <div className="flex flex-wrap gap-2">{FORECAST_EXAMPLES.map(q=><button key={q} type="button" disabled={busy} onClick={()=>{ setQuestion(q); void readScope(q) }} className="rounded-lg border border-edge px-3 py-1.5 text-xs text-muted transition-colors hover:bg-paper hover:text-ink disabled:opacity-60">{q}</button>)}</div>
        {!scope && <div className="flex justify-end border-t border-rule pt-4"><button type="submit" disabled={busy || question.trim().length < 3} className={BTN}>{busy ? "Reading…" : "Read my question"}</button></div>}
      </form>
      {scope && <section className={`${PANEL} space-y-4 p-6 pa-rise`}>
        <div><h3 className="text-sm font-semibold">How the agent reads your question</h3><p className="mt-1 text-xs text-muted">Check the scope before anything runs. Change what the question asks, the territory or the weeks if this is not what you meant.</p></div>
        {scope.out_of_scope ? <Notice tone="warn">{scope.out_of_scope}</Notice> : <>
          <dl className="grid gap-x-4 gap-y-2 text-sm sm:grid-cols-[120px_1fr]">
            <dt className="text-muted">Read by</dt><dd>{scope.read_by === "model" ? `${modelName(scope.engine) || "the model"}; code checked every field` : "keyword rules (no model is configured, or the model's reading was unusable)"}</dd>
            <dt className="text-muted">Period</dt><dd>{scope.period} · {scope.n_weeks} week{scope.n_weeks === 1 ? "" : "s"}</dd>
            <dt className="text-muted">Where</dt><dd>{scope.territory_name}</dd>
            <dt className="text-muted">Investigation</dt><dd>{scope.investigator === "model" ? "the model investigates (comparison arm)" : "the rules investigate; code computes every number"}</dd>
          </dl>
          {!!scope.notes.length && <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted">{scope.notes.map(n=><li key={n}>{n}</li>)}</ul>}
          <label className={LABEL}>The question asks<select value={intent} onChange={e=>setIntent(e.target.value)} disabled={busy} className={FIELD}>{FORECAST_INTENTS.map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className={LABEL}>Territory<select value={territory} onChange={e=>setTerritory(e.target.value)} disabled={!context || busy} className={FIELD}>{(context?.territory_ids ?? [scope.territory]).map(id=><option key={id} value={id}>{labelTerritory(id)}</option>)}</select></label>
            <label className={LABEL}>First week<select value={weekFrom} onChange={e=>setWeekFrom(e.target.value)} disabled={!context || busy} className={FIELD}>{(context?.available_weeks ?? [weekFrom]).map(w=><option key={w} value={w}>{labelWeek(w)}</option>)}</select></label>
            <label className={LABEL}>Last week<select value={weekTo} onChange={e=>setWeekTo(e.target.value)} disabled={!context || busy} className={FIELD}>{(context?.available_weeks ?? [weekTo]).filter(w=>w >= weekFrom).map(w=><option key={w} value={w}>{labelWeek(w)}</option>)}</select></label>
          </div>
        </>}
        <div className="flex flex-wrap justify-end gap-2 border-t border-rule pt-4"><button type="button" disabled={busy} onClick={()=>setScope(null)} className={BTN2}>Edit question</button>{!scope.out_of_scope && <button type="button" disabled={busy} onClick={()=>void investigate()} className={BTN}>{busy ? "Starting…" : "Investigate"}</button>}</div>
      </section>}
    </>}
    {!analyst && section === "workbench" && <p className="text-sm text-muted">Forecast reports waiting for your review are under the Reports tab.</p>}
    <section><h3 className="text-sm font-semibold">{analyst ? "Your forecast questions" : "Waiting for your review"}</h3>{loading ? <div className="mt-2"><ListSkeleton/></div> : runs.length ? <ul className={`${PANEL} pa-stagger mt-2 divide-y divide-rule`}>{runs.map(run=><li key={run.forecast_run_id}><button disabled={busy} onClick={()=>void open(run.forecast_run_id)} className="group flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left transition-colors hover:bg-paper/60"><span className="min-w-0"><span className="block text-sm">{run.question ?? run.headline}</span><span className="mt-0.5 block text-xs text-muted tabular-nums">{run.job_status === "running" ? "Investigating…" : run.job_status === "failed" ? "Failed" : <>{labelTerritory(run.territory_id)} · miss {formatNumber(run.variance_trx)} TRx · {forecastReviewLabel(run.review_status)}</>}</span></span><Icon name="chevronRight" className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-primaryink"/></button></li>)}</ul> : <p className="mt-2 text-sm text-muted">{analyst ? "No forecast questions yet. Ask one above, or start from an example." : "Nothing is waiting for your review."}</p>}</section></>}
    </>}
  </div>
}

// The sidebar is a narrow rail of icons; a toggle in the header (or Ctrl+B) opens it to full width, and the page
// re-centres beside it. The choice is remembered in this browser. On phones the same toggle opens a slide-out menu.
// Every icon has an explicit size: a className without one lets the SVG grow to fill its row.
const OPEN_KEY = "pa_sidebar_open"
const readOpen = () => { try { return window.localStorage.getItem(OPEN_KEY) === "1" } catch { return false } }

function SideNav({me, expanded, forecast, telemetry, briefingBusy, forecastBusy, onBriefing, onForecast, onTelemetry, onAnyClick}: {me: Me, expanded: boolean, forecast: boolean, telemetry: boolean, briefingBusy: boolean, forecastBusy: boolean, onBriefing?: () => void, onForecast: () => void, onTelemetry: () => void, onAnyClick?: () => void}) {
  const row = (active: boolean) => `group flex w-full items-center gap-3 rounded-lg px-[10px] py-2.5 text-left text-sm transition-colors duration-150 ${active ? "bg-primarybg font-semibold text-ink" : "text-muted hover:bg-paper hover:text-ink"}`
  const label = (text: string) => <span className={expanded ? "truncate whitespace-nowrap pa-fade" : "sr-only"}>{text}</span>
  // A run still going shows a small dot (on the icon in the rail, at the row's end when open); the words are for screen readers.
  const dot = (cls: string) => <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full bg-primary motion-safe:animate-pulse ${cls}`}/>
  const item = (icon: IconName, text: string, active: boolean, go: () => void, busy = false) =>
    <button aria-current={active ? "page" : undefined} title={expanded ? undefined : busy ? `${text} · in progress` : text} className={row(active)} onClick={()=>{go();onAnyClick?.()}}><span className="relative shrink-0"><Icon name={icon} className={`h-5 w-5 shrink-0 transition-colors ${active ? "text-primaryink" : "group-hover:text-primaryink"}`}/>{busy && !expanded && dot("absolute -right-1 -top-1")}</span>{label(text)}{busy && <span className="sr-only">, in progress</span>}{busy && expanded && dot("ml-auto")}</button>
  return <div className="flex h-full flex-col">
    <div className="flex h-16 items-center gap-3 px-[14px]">
      <BrandMark/>
      {/* The mark is decorative; the product's name is spoken once, by the text beside it or, in the narrow rail, here */}
      {expanded ? <span className="pa-fade flex-1 truncate whitespace-nowrap font-display text-[18px] font-bold tracking-tight">PharmAgentics</span> : <span className="sr-only">PharmAgentics</span>}
    </div>
    <nav className="mt-2 space-y-1 px-3" aria-label="Workspaces">
      {onBriefing && item("briefcase", "Weekly briefing", !forecast && !telemetry, onBriefing, briefingBusy)}
      {me.lanes.forecast?.available && item("trend", "Forecast explanation", forecast && !telemetry, onForecast, forecastBusy)}
      {item("clipboard", "Evaluation", telemetry, onTelemetry)}
    </nav>
    <div className="mt-auto space-y-2 px-3 pb-4">
      {me.auth_mode==="dev" && expanded && <p className="flex items-center gap-1.5 px-2.5 text-[11px] text-muted"><span className="h-1.5 w-1.5 shrink-0 rounded-full bg-muted" aria-hidden="true"/>Development sign-in</p>}
      <ShareFeedbackLink expanded={expanded} onOpen={onAnyClick}/>
    </div>
  </div>
}

// The phone menu is a modal drawer: focus moves into it, Tab stays in it, Escape or the backdrop closes it, and focus
// goes back to the button that opened it.
function MobileNav({onClose, children}: {onClose: () => void, children: ReactNode}) {
  const drawer = useRef<HTMLDivElement>(null)
  useModalFocus(drawer, onClose)
  return <div className="fixed inset-0 z-40 flex md:hidden"><button tabIndex={-1} aria-label="Close navigation" className="pa-fade absolute inset-0 bg-black/60" onClick={onClose}/>
    <div ref={drawer} role="dialog" aria-modal="true" aria-label="Navigation" tabIndex={-1} className="glass relative w-[280px] max-w-[85vw] overscroll-contain border-r border-rule pa-slide">{children}</div></div>
}

function Shell({me, onBriefingHome, children, startInForecast=false, briefingBusy=false}: {me: Me, onBriefingHome?: () => void, children: ReactNode, startInForecast?: boolean, briefingBusy?: boolean}) {
  const [mobileNav,setMobileNav] = useState(false)
  const [forecast,setForecast] = useState(startInForecast)
  const [forecastVisited,setForecastVisited] = useState(startInForecast)  // once opened, the workspace stays mounted so a running investigation survives lane switches
  const [forecastBusy,setForecastBusy] = useState(false)
  const [telemetry,setTelemetry] = useState(false)
  const forecastHome: ForecastSection = me.lanes.forecast?.actions.includes("run") ? "workbench" : "reports"
  const [forecastSection,setForecastSection] = useState<ForecastSection>(forecastHome)
  const [open,setOpen] = useState(readOpen)
  const toggle = () => setOpen(o => { try { window.localStorage.setItem(OPEN_KEY, o ? "0" : "1") } catch { /* a convenience only */ } return !o })
  const toggleNav = () => { if (window.matchMedia("(min-width: 768px)").matches) toggle(); else setMobileNav(true) }
  useEffect(()=>{
    const key = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") { e.preventDefault(); toggleNav() } }
    window.addEventListener("keydown", key)
    return () => window.removeEventListener("keydown", key)
  },[])
  const goBriefing = onBriefingHome ? () => { setTelemetry(false); setForecast(false); onBriefingHome() } : undefined
  const goForecast = () => { setTelemetry(false); setForecast(true); setForecastVisited(true); setForecastSection(forecastHome) }
  const goTelemetry = () => setTelemetry(true)
  const leader = !me.lanes.briefing?.views.includes("analyst") && !me.lanes.forecast?.views.includes("analyst")
  const title = telemetry ? "Evaluation" : forecast ? "Forecast explanation" : "Weekly briefing"
  useEffect(()=>{ document.title = `${title} · PharmAgentics` },[title])  // 2.4.2: the tab names the workspace that is open
  const content = useRef<HTMLElement>(null)
  // --rail is the width the sidebar occupies; .workspace-content uses it to centre on the whole page (0 on phones).
  return <SignedInName.Provider value={me.name}><FeedbackProvider where={forecast ? "forecast" : "briefing"}><div className={`flex h-dvh overflow-hidden text-ink max-md:[--shift:0px] ${open ? "[--shift:0px]" : "[--shift:64px]"}`}>
    <a href="#main-content" onClick={e=>{ e.preventDefault(); content.current?.focus() }} className="sr-only rounded-lg bg-primary text-sm font-semibold text-onprimary focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:px-4 focus:py-2">Skip to content</a>
    <aside aria-label="Sidebar" className={`hidden shrink-0 overflow-hidden border-r border-rule bg-sheet transition-[width] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] md:block ${open ? "w-[248px]" : "w-16"}`}>
      <SideNav me={me} expanded={open} forecast={forecast} telemetry={telemetry} briefingBusy={briefingBusy} forecastBusy={forecastBusy} onBriefing={goBriefing} onForecast={goForecast} onTelemetry={goTelemetry}/>
    </aside>
    {mobileNav && <MobileNav onClose={()=>setMobileNav(false)}><SideNav me={me} expanded forecast={forecast} telemetry={telemetry} briefingBusy={briefingBusy} forecastBusy={forecastBusy} onBriefing={goBriefing} onForecast={goForecast} onTelemetry={goTelemetry} onAnyClick={()=>setMobileNav(false)}/></MobileNav>}
    <main className="flex min-w-0 flex-1 flex-col">
      <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b border-rule px-4 sm:px-5">
        <div className="flex min-w-0 items-center gap-2">
          <button type="button" onClick={toggleNav} aria-expanded={open} aria-label={open ? "Collapse the sidebar" : "Expand the sidebar"} title={`${open ? "Collapse" : "Expand"} the sidebar (Ctrl+B)`}
            className="grid h-9 w-9 place-items-center rounded-lg text-muted transition-colors hover:bg-paper hover:text-ink"><Icon name="panel" className="h-5 w-5"/></button>
          <h1 key={telemetry ? "t" : forecast ? "f" : "b"} className="pa-fade truncate text-lg font-bold sm:text-xl">{title}</h1>
        </div>
        <AccountMenu me={me}/>
      </header>
      <section ref={content} id="main-content" tabIndex={-1} aria-label={title} className="min-h-0 flex-1 scroll-pb-44 overflow-y-auto"><div hidden={forecast || telemetry}>{children}</div>{telemetry && <TelemetryWorkspace label={<ClassLabel tab="evaluation.overview"/>} tester={me.tester}/>}{forecastVisited && <div hidden={!forecast || telemetry}><ForecastWorkspace me={me} section={forecastSection} onSection={setForecastSection} onBusy={setForecastBusy}/></div>}</section>
      <footer className="shrink-0 border-t border-rule px-5 py-2 text-center text-[11px] text-muted">PharmAgentics can make mistakes. Check important figures {leader ? "with the Commercial Analyst" : "against the evidence"}.</footer>
    </main>
    <Toaster theme="dark" position="bottom-right" closeButton toastOptions={{className: "glass !bg-transparent !text-ink !border !border-rule !font-sans !rounded-xl"}}/>
  </div></FeedbackProvider></SignedInName.Provider>
}

function Centered({children}: {children: ReactNode}) {
  return <div className="grid h-dvh place-items-center px-5 text-ink"><div className="pa-panel max-w-md rounded-xl border border-rule bg-sheet p-7 text-center"><div className="flex justify-center"><BrandMark size="lg"/></div>{children}</div></div>
}

// The intro line of a landing page, with a "How it works" disclosure at its right end: the button toggles an inline
// panel below it (aria-expanded/aria-controls); Escape inside the panel closes it and puts focus back on the button.
// `introId` lets the page send focus to the intro (tabIndex -1) after "Start a new briefing".
function IntroWithHow({introId, children}: {introId?: string, children: ReactNode}) {
  const [open,setOpen] = useState(false)
  const panel = useId()
  const button = useRef<HTMLButtonElement>(null)
  const close = () => { setOpen(false); button.current?.focus() }
  // Escape closes the panel from the button as well as from inside it.
  return <div className="space-y-3" onKeyDown={e=>{ if (e.key==="Escape" && open) { e.stopPropagation(); close() } }}>
    <div className="flex items-start justify-between gap-3">
      <p id={introId} tabIndex={introId ? -1 : undefined} className="min-w-0 text-sm text-muted outline-none">{children}</p>
      <button ref={button} type="button" aria-expanded={open} aria-controls={open ? panel : undefined} onClick={()=>open ? close() : setOpen(true)} className="flex shrink-0 items-center gap-1.5 rounded-lg text-sm text-primaryink hover:underline"><Icon name="help" className="h-4 w-4"/><span className="max-sm:sr-only">How it works</span></button>
    </div>
    {open && <section id={panel} aria-label="How it works" className="space-y-3 border-y border-rule py-4">
      <div className="flex items-center justify-between gap-3"><ClassLabel tab="briefing.how"/><button type="button" onClick={close} aria-label="Close How it works" className="grid h-8 w-8 place-items-center rounded-lg text-muted transition-colors hover:bg-paper hover:text-ink"><Icon name="close" className="h-4 w-4"/></button></div>
      <HowItWorks/>
    </section>}
  </div>
}

function SummaryCard({brief, preview=false}: {brief: LeadershipBrief, preview?: boolean}) {
  return <><article className={`${PANEL} overflow-hidden pa-rise`}>
    <div className="border-b border-rule px-6 py-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted">
        <span>{preview ? "Leadership preview" : "Executive summary"}</span>
        <ClassLabel tab="briefing.view.leadership"/>
      </div>
      <h2 className="mt-2 text-2xl">{labelTerritory(brief.territory_id)}, {periodLabel(brief.week_start, brief.week_end)}</h2>
      <p className="mt-1.5 text-sm text-muted">{brief.brand_id} · data version {brief.data_version ?? "unavailable"}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {brief.review_status==="approved" ? <span className={`${TAG} border-ok text-ok`}><Icon name="check" className="h-3.5 w-3.5"/>Approved by the Commercial Analyst · {labelTime(brief.reviewed_at)}</span> : <span className={`${TAG} border-edge text-ink`}>{REVIEW_CHIP[brief.review_status][1]}</span>}
        {brief.abstained && <Flag>Unresolved findings</Flag>}
      </div>
      {brief.process_summary && <p className="mt-3 text-xs text-muted">{processLine(brief.process_summary, brief.reviewed_at)}</p>}
    </div>
    <div className="px-6 py-6">{brief.sections?.length ? <Memo sections={brief.sections} briefId={brief.brief_id} definition={brief.definition} labelWeek={labelWeek}/> : <pre className="max-w-[68ch] whitespace-pre-wrap break-words font-sans text-[16px] leading-[1.65] text-ink">{brief.summary}</pre>}</div>
    <div className="border-t border-rule px-6 py-4 text-xs text-muted">Every figure comes from the approved analyst brief. Evidence and source queries stay with the Commercial Analyst.</div>
  </article>
  <AnswerFeedback lane="briefing" refId={brief.brief_id} view="leadership" agent={brief.engine==="agent"}/></>
}

// A short, warm start to each workspace, from the viewer's own clock.
// The signed-in person's name, from /api/me (the persona's first name in the realm: Ace, Diana, Miranda, Tester).
const SignedInName = createContext("")

function Greeting({detail}: {detail?: string}) {
  const h = new Date().getHours()
  const first = useContext(SignedInName).trim().split(/\s+/)[0]
  const part = (h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening") + (first ? `, ${first}` : "")
  // A greeting is not a section heading, so it is a paragraph; the h1 in the header names the page.
  return <div className="pa-fade mb-4"><p className="font-display text-[2rem] font-bold leading-[1.25] tracking-[-0.02em]"><span className="pa-mark">{part}.</span></p>{detail && <p className="mt-3 text-sm text-muted">{detail}</p>}</div>
}

// An agent job's real progress: the server reports queued, then running; the result arrives when it is done and
// has passed the traceability check. The clock is the real elapsed time; nothing here is simulated.
function JobProgress({kind, status, note}: {kind: "triage" | "brief", status: "queued" | "running", note: string | null}) {
  const [start] = useState(() => Date.now())
  const [now,setNow] = useState(() => Date.now())
  useEffect(()=>{ const t = setInterval(()=>setNow(Date.now()), 1000); return ()=>clearInterval(t) },[])
  const secs = Math.floor((now - start) / 1000)
  const steps = [
    ["queued", "Queued"],
    ["running", kind === "triage" ? "The manager is reviewing the plan" : "The agent team is investigating"],
    ["check", "Every number checked against its source, then shown to you"],
  ] as const
  const at = status === "queued" ? 0 : 1
  return <section role="status" aria-live="polite" className={`${PANEL} pa-fade p-6`}>
    <div className="flex items-baseline justify-between gap-3"><h3 className="text-sm font-semibold">{kind === "triage" ? "Preparing the plan" : "Writing the briefing"}</h3><span className="text-xs tabular-nums text-muted">{Math.floor(secs / 60)}:{String(secs % 60).padStart(2, "0")}</span></div>
    <ol className="mt-4 space-y-3">{steps.map(([id, text], i) => <li key={id} className={`flex items-center gap-3 text-sm transition-colors duration-300 ${i < at ? "text-muted" : i === at ? "font-medium text-ink" : "text-muted"}`}>
      <span aria-hidden="true" className="grid h-5 w-5 shrink-0 place-items-center">
        {i < at ? <svg viewBox="0 0 24 24" className="pa-draw h-4 w-4 text-primaryink" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
          : i === at ? <span className="h-2 w-2 rounded-full bg-primary pa-pulse"/> : <span className="h-2 w-2 rounded-full border border-edge"/>}
      </span>{text}</li>)}</ol>
    {note && <p className="mt-4 text-xs text-muted">{note}</p>}
  </section>
}

function ListSkeleton({rows=3}: {rows?: number}) {
  return <div role="status" className={`${PANEL} divide-y divide-rule`}><span className="sr-only">Loading…</span>{Array.from({length: rows}, (_, i) => <div key={i} className="space-y-2 px-5 py-4"><div className="pa-skeleton h-3.5 w-1/2"/><div className="pa-skeleton h-3 w-1/3"/></div>)}</div>
}

function PublishedList({onOpen}: {onOpen: (id: string) => void}) {
  const [items,setItems] = useState<PublishedBrief[] | null>(null)
  const [error,setError] = useState<string | null>(null)
  useEffect(()=>{listPublished().then(setItems).catch(e=>setError(message(e)))},[])
  if (error) return <Notice tone="error" role="alert">{error}</Notice>
  if (!items) return <ListSkeleton/>
  if (!items.length) return <p className="text-sm text-muted">No approved briefings yet. A briefing appears here once the Commercial Analyst approves it.</p>
  return <ul className={`${PANEL} pa-stagger divide-y divide-rule`}>{items.map(b=><li key={b.brief_id}><button onClick={()=>onOpen(b.brief_id)} className="group flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left transition-colors hover:bg-paper/60">
    <span className="min-w-0"><span className="block text-sm">{b.brand_id} · {labelTerritory(b.territory_id)}, {periodLabel(b.week_start, b.week_end)}</span><span className="mt-0.5 block text-xs text-muted">Approved {labelTime(b.reviewed_at)}{b.abstained ? " · unresolved findings" : ""}</span></span>
    <Icon name="chevronRight" className="h-4 w-4 shrink-0 text-muted transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-primaryink"/></button></li>)}</ul>
}

function ReviewPanel({result, onChange}: {result: BriefingResult, onChange: (r: BriefingResult) => void}) {
  const [reason,setReason] = useState("")
  const [rejecting,setRejecting] = useState(false)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState<string | null>(null)
  const decide = async (decision: "approved" | "rejected") => {
    setBusy(true); setError(null)
    try { onChange(await reviewBrief(result.brief_id, decision, reason)); setRejecting(false); setReason(""); toast.success(decision==="approved" ? "Approved. The Brand Director can now open it." : "Rejected. It stays hidden from the Brand Director.") }
    catch(e) { setError(message(e)) } finally { setBusy(false) }
  }
  return <section className="border-t border-rule px-6 py-5">
    <h3 className="text-sm font-semibold">Your review</h3>
    <p className="mt-1 text-xs text-muted">{result.review_status==="pending" ? "The Brand Director sees this briefing only after you approve it." : `${result.review_status==="approved"?"Approved":"Rejected"} ${labelTime(result.reviewed_at)}${result.review_reason?` · “${result.review_reason}”`:""}. You can change your decision.`}</p>
    {rejecting ? <div className="mt-3 space-y-2">
      <label className="block text-xs font-medium text-muted" htmlFor="reject-reason">Reason for rejecting (required)</label>
      <textarea id="reject-reason" value={reason} onChange={e=>setReason(e.target.value)} maxLength={500} rows={2} className={FIELD}/>
      <div className="flex justify-end gap-2"><button onClick={()=>setRejecting(false)} className={BTN2}>Cancel</button><button disabled={busy || !reason.trim()} onClick={()=>void decide("rejected")} className={`${BTN2} border-neg text-neg! hover:bg-paper`}>Reject briefing</button></div>
    </div> : <div className="mt-3 flex flex-wrap justify-end gap-2">
      <button disabled={busy || result.review_status==="rejected"} onClick={()=>setRejecting(true)} className={`${BTN2} text-neg!`}>Reject…</button>
      <button disabled={busy || result.review_status==="approved"} onClick={()=>void decide("approved")} className={BTN}>Approve for the Brand Director</button>
    </div>}
    {error && <p role="alert" className="mt-2 text-xs text-neg">{error}</p>}
  </section>
}

// brief-002 US8: the code triage plan, reviewed by the analyst before stage 4 runs.
const QUESTIONS = [["decision","Decision"],["population","Population"],["granularity","Granularity"],["time","Time"]] as const

function TriageReview({plan, busy, onApprove}: {plan: TriagePlan, busy: boolean, onApprove: (d: TriageDecision) => void}) {
  const proposed = plan.stories.filter(c=>c.proposed==="investigate").map(c=>c.id)
  // Agent plans start from the manager's plan (A1); P1 can still restore what the manager dropped.
  const start = plan.engine==="agent" && plan.manager_order ? plan.manager_order : proposed
  const startOrder = [...start, ...proposed.filter(id=>!start.includes(id))]
  const [order,setOrder] = useState<string[]>(startOrder)
  const [kept,setKept] = useState<Set<string>>(new Set(start))
  useEffect(()=>{setOrder(startOrder);setKept(new Set(start))},[plan.plan_id, plan.manager_order?.join()])  // eslint-disable-line react-hooks/exhaustive-deps
  const byId = new Map(plan.stories.map(c=>[c.id,c]))
  const move = (id: string, by: -1 | 1) => setOrder(o => { const i=o.indexOf(id), j=i+by; if(j<0||j>=o.length) return o; const n=[...o]; [n[i],n[j]]=[n[j],n[i]]; return n })
  const toggle = (id: string) => setKept(k => { const n=new Set(k); if(n.has(id)) n.delete(id); else n.add(id); return n })
  const decision: TriageDecision = {plan_id: plan.plan_id, stories: order.filter(id=>kept.has(id))}
  const changed = decision.stories.join() !== start.join()
  const over = plan.stories.filter(c=>c.proposed==="over_cap")
  return <div className="space-y-5 pa-rise">
    <div className="pa-panel rounded-xl bg-sheet px-6 py-5 border border-rule">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs"><span className="font-semibold uppercase tracking-[0.06em] text-human">Triage review · your decision</span><span className="text-muted">Proposed by code</span></div>
      <h2 className="mt-3 text-lg font-semibold">What should this brief investigate?</h2>
      <p className="mt-1 text-sm text-muted">Code screened every territory and proposes the stories below, ranked by impact. Keep, drop or reorder them; investigation runs only on what you approve, in your order.</p>
      <details className="mt-4 rounded-xl bg-paper p-4 text-sm"><summary className="cursor-pointer font-medium">What stages 1 to 3 found (data health, restatements, KPIs)</summary><pre className="mt-3 whitespace-pre-wrap break-words font-sans text-[13px] leading-relaxed text-ink">{plan.context}</pre></details>
      {plan.engine==="agent" && plan.state==="TRIAGE_REVIEW" && (() => { const detail = <>
        {plan.flags?.map((f,i)=><p key={i} className="mt-1">{f}</p>)}
        {plan.corrections?.map((f,i)=><p key={`c${i}`} className="mt-1"><span className="font-medium">Rule applied by code:</span> {f}</p>)}
        {plan.manager_note && <p className="mt-1">Manager's note: {plan.manager_note}</p>}
      </>
        return plan.flagged
          ? <Notice tone="warn" className="mt-4" title={<>The manager's plan is flagged for your review<span className="font-normal text-ink"> · agent ({modelName(plan.model)})</span></>}>{detail}</Notice>
          : <div className="mt-4 rounded-xl border border-rule bg-paper p-4 text-sm text-ink"><p className="font-medium">The manager kept code's plan<span className="font-normal"> · agent ({modelName(plan.model)})</span></p>{detail}</div> })()}
    </div>
    {plan.state==="OUT_OF_SCOPE" ? <Notice tone="warn" title="The data cannot answer this question as asked." className="px-6 py-5"><p className="mt-1">{plan.scope}</p><p className="mt-2">The brief will state this and give the scripted brief for the week. No investigation runs.</p></Notice> :
    plan.state!=="TRIAGE_REVIEW" ? <div className="pa-panel rounded-xl bg-sheet px-6 py-5 text-sm border border-rule">{plan.promotion_review ? "The review will compare coverage lapses and recoveries across the release." : plan.state==="CALENDAR" ? "Calendar week: lower volume is expected, so code opens no story." : "Routine week: code found no material change, so there is no story to triage."}</div> :
    <ol className="space-y-3">{order.map((id, i)=>{ const c=byId.get(id)!; const on=kept.has(id); return <li key={id} className={`${on ? PANEL : "rounded-xl border border-dashed border-edge bg-sheet"} p-5`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0"><div className="text-xs uppercase tracking-widest text-muted">{on ? `Story ${decision.stories.indexOf(id)+1}` : "Left out"} · code rank {c.rank}</div><h3 className={`mt-1 text-base font-semibold ${on ? "" : "text-muted"}`}>{c.title}</h3></div>
        <div className="flex shrink-0 items-center gap-1">
          <button aria-label={`Move ${c.title} up`} disabled={i===0} onClick={()=>move(id,-1)} className="grid h-9 w-9 place-items-center rounded-lg border border-edge text-sm transition-colors hover:bg-paper disabled:border-rule disabled:text-muted">↑</button>
          <button aria-label={`Move ${c.title} down`} disabled={i===order.length-1} onClick={()=>move(id,1)} className="grid h-9 w-9 place-items-center rounded-lg border border-edge text-sm transition-colors hover:bg-paper disabled:border-rule disabled:text-muted">↓</button>
          <label className="ml-2 flex min-h-9 cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={on} onChange={()=>toggle(id)} className="h-4 w-4"/>Investigate</label>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed">{c.what_moved}</p>
      {c.manager && <p className="mt-2 rounded-lg bg-paper px-3 py-2 text-[13px] text-ink"><span className="font-medium">Manager (agent):</span> {c.manager.keep ? `keeps it as story ${c.manager.position}` : `drops it${c.manager.why ? `: ${c.manager.why}` : ""}`}{c.manager.hypotheses.length ? ` · tests in this order: ${c.manager.hypotheses.join(", ")}` : ""}</p>}
      <dl className="mt-3 grid gap-x-4 gap-y-2 text-[13px] sm:grid-cols-[110px_1fr]">{QUESTIONS.map(([k,label])=><div key={k} className="contents"><dt className="font-medium text-muted">{label}</dt><dd className="leading-relaxed">{c[k]}</dd></div>)}</dl>
    </li>})}</ol>}
    {(over.length>0 || plan.dropped.length>0) && <div className={`${PANEL} px-6 py-5 text-sm`}>
      <h3 className="font-semibold">Dropped by code</h3><p className="mt-1 text-xs text-muted">These follow the rules; they cannot be added back to this brief.</p>
      <ul className="mt-3 space-y-1.5">{over.map(c=><li key={c.id}><span className="font-medium">{c.title}</span> <span className="text-muted">· over the story cap of this brief</span></li>)}{plan.dropped.map(d=><li key={d.territory}><span className="font-medium">{d.territory}</span> <span className="text-muted">· {d.reason}</span></li>)}</ul>
    </div>}
    <div className="flex flex-wrap items-center gap-3">
      <button disabled={busy} onClick={()=>onApprove(decision)} className={BTN}>{plan.state!=="TRIAGE_REVIEW" ? "Write the brief" : changed ? "Approve my changes and investigate" : "Approve plan and investigate"}</button>
      {changed && <span className="text-xs text-muted">Your changes are recorded as your calls in the brief's triage record.</span>}
    </div>
  </div>
}

// brief-002 US7: who did each of the seven stages (Briefing Architecture §6 states, §9 modes).
const ACTOR = {code:["Code","border-edge text-ink"], agent:["Agent","border-edge text-ink"], llm:["LLM step","border-edge text-ink"], human:["Person","border-human/60 text-human"]} as const

function FlowPanel({flow, triage}: {flow: Stage[], triage?: TriageRecord | null}) {
  return <details className="pa-panel rounded-xl bg-sheet px-6 py-5 border border-rule">
    <summary className="cursor-pointer text-sm font-semibold">How this brief was made</summary>
    <ol className="mt-4 space-y-3">{flow.map(s=><li key={s.stage} className="grid gap-1 sm:grid-cols-[28px_1fr]">
      <span className="font-mono text-xs text-muted">{s.stage}</span>
      <div><div className="flex flex-wrap items-center gap-2"><span className="text-sm font-medium">{s.name}</span>{s.states.map(st=><span key={st} className="rounded bg-paper px-1.5 py-0.5 font-mono text-[10px] text-muted border border-rule">{st}</span>)}</div>
        <div className="mt-1 flex flex-wrap gap-1.5">{s.actors.length ? s.actors.map((a,i)=><span key={i} className={`${chip} ${ACTOR[a.kind][1]}`}>{ACTOR[a.kind][0]}: {plainModels(a.name)}</span>) : <span className="text-xs text-muted">Skipped</span>}</div>
        <p className="mt-1 text-xs text-muted">{s.note}</p></div>
    </li>)}</ol>
    {triage && <div className="mt-5 border-t border-rule pt-4"><h4 className="text-xs font-semibold uppercase tracking-wider text-muted">Triage record</h4>
      <ul className="mt-2 space-y-1 text-xs">{triage.calls.map((c,i)=><li key={i} className="flex flex-wrap items-center gap-2"><span className={`${chip} ${ACTOR[c.layer][1]}`}>{({human:"You",agent:"Manager",code:"Code"} as const)[c.layer]}</span><span className="font-medium">{c.title}</span><span className="text-muted">{({investigated:"investigated as proposed",moved:c.layer==="agent"?"moved by the manager":"moved by you",dropped:c.layer==="agent"?`left out by the manager${c.why?`: ${c.why}`:""}`:"left out by you",restored:"put back by you after the manager dropped it",over_cap:"over the story cap",quiet:"within its normal range",withheld:"withheld at the feed gate"} as Record<string,string>)[c.outcome] ?? c.outcome}{c.position?` · story ${c.position}`:""}</span></li>)}</ul></div>}
  </details>
}

// Inline citations: every number in the brief is a claim; the server says where each one sits.
function CitedText({result, onOpen}: {result: BriefingResult, onOpen: (evidenceId: string) => void}) {
  const spans = [...(result.citations ?? [])].sort((a,b)=>a.start-b.start)
  if (!spans.length) return <>{result.answer}</>
  const parts: ReactNode[] = []
  let pos = 0
  spans.forEach((sp, i) => {
    const claim: Claim | undefined = result.claims[sp.claim]
    if (!claim || sp.start < pos || result.answer.slice(sp.start, sp.end) !== claim.value) return
    parts.push(result.answer.slice(pos, sp.start))
    parts.push(<button key={i} type="button" onClick={()=>onOpen(claim.evidence_id)} title={`Source ${claim.evidence_id}: open the query behind ${claim.value}`} aria-label={`${claim.value}, evidence ${claim.evidence_id.replace(/^e/, "")}`}
      className="rounded-sm font-medium underline decoration-primaryink/40 decoration-dotted underline-offset-4 hover:bg-primarybg focus:bg-primarybg">{claim.value}<sup aria-hidden="true" className="ml-px font-mono text-[9px] font-normal text-primaryink">{claim.evidence_id.replace(/^e/, "")}</sup></button>)
    pos = sp.end
  })
  parts.push(result.answer.slice(pos))
  return <>{parts}</>
}

// brief-009: story id to its card title, from the triage record, so the timeline names a story the way the memo does.
const storyTitles = (r: BriefingResult): Record<string, string> => Object.fromEntries((r.triage?.calls ?? []).map(c=>[c.story, c.title]))

function AnalystBrief({result, onChange, onAsk, openEvidence, stepsFolded = false, onStartNew}: {result: BriefingResult, onChange: (r: BriefingResult) => void, onAsk?: (c: Chip) => void, openEvidence?: {id: string} | null, stepsFolded?: boolean, onStartNew?: () => void}) {
  const [evidenceId,setEvidenceId] = useState<string | null>(null)
  useEffect(()=>{ if(openEvidence) setEvidenceId(openEvidence.id) },[openEvidence])
  const [mode,setMode] = useState<"analyst" | "leadership">("analyst")
  const [preview,setPreview] = useState<LeadershipBrief | null>(null)
  const [previewError,setPreviewError] = useState<string | null>(null)
  useEffect(()=>{setMode("analyst");setPreview(null)},[result.brief_id])
  const showPreview = async () => {
    setMode("leadership"); setPreviewError(null)
    try { setPreview(await openBrief(result.brief_id, "leadership")) } catch(e) { setPreviewError(message(e)) }
  }
  return <>
    {/* "Start a new briefing" at the left of the view toggles' row */}
    <div className="flex flex-wrap items-center justify-between gap-3">{onStartNew ? <button type="button" onClick={onStartNew} className={BTN2}>Start a new briefing</button> : <span/>}<ViewToggle value={mode} onChange={v=>{ if (v==="analyst") setMode("analyst"); else void showPreview() }}/></div>
    {mode==="leadership" ? (previewError ? <Notice tone="error" role="alert">{previewError}</Notice> : preview ? <SummaryCard brief={preview} preview/> : <p className="text-sm text-muted">Loading the leadership view…</p>) :
    <article className={`${PANEL} overflow-hidden`}>
      <div className="border-b border-rule px-6 py-5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-xs text-muted"><span>{result.engine==="agent" ? "Agent team · experimental" : "Scripted"}</span><ClassLabel tab="briefing.view.analyst"/></div>
        <h2 className="mt-2 text-2xl">{labelTerritory(result.territory_id)} · {result.question.startsWith("Promotion review in ") ? "Promotion review" : result.week_end && result.week_end > result.week_start ? `weeks ${labelWeek(result.week_start)} to ${labelWeek(result.week_end)}` : `week of ${labelWeek(result.week_start)}`}</h2>
        <p className="mt-1.5 text-sm text-muted">{result.brand_id}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2"><span key={result.review_status} className={`${REVIEW_CHIP[result.review_status][0]} inline-flex items-center gap-1 pa-fade`}>{result.review_status==="approved" && <svg viewBox="0 0 24 24" className="pa-draw h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>}{REVIEW_CHIP[result.review_status][1]}</span>{result.abstained && <Flag>Unresolved findings</Flag>}</div>
      </div>
      <div className="px-6 py-6">{result.sections?.length ? <Memo sections={result.sections} briefId={result.brief_id} claims={result.claims} evidence={result.evidence} onOpen={setEvidenceId} onAsk={onAsk} definition={result.definition} labelWeek={labelWeek}/> : <div className="max-w-[68ch] whitespace-pre-wrap break-words font-sans text-[16px] leading-[1.65] text-ink"><CitedText result={result} onOpen={setEvidenceId}/></div>}
        <p className="mt-4 text-[11px] text-muted">Each underlined number is a claim: click it, or its source number, to open the query and record behind it.</p></div>
      <section className="flex flex-wrap items-center justify-between gap-2 border-t border-rule bg-paper/60 px-6 py-3">
        {result.evidence.length>0 ? <button className="flex items-center gap-2 text-xs font-medium text-primaryink underline-offset-4 hover:underline" onClick={()=>setEvidenceId(result.evidence[0].id)}><Icon name="evidence"/>All {result.evidence.length} sources ({result.claims.length} numbers)</button> : <span className="text-xs text-muted">No numeric claims in this brief.</span>}
        <span className="rounded bg-sheet px-2 py-1 font-mono text-[11px] text-muted border border-rule" title="Pinned data version">{result.data_version??"Version unavailable"}</span>
      </section>
      <ReviewPanel result={result} onChange={onChange}/>
    </article>}
    {mode==="analyst" && <AnswerFeedback lane="briefing" refId={result.brief_id} view="analyst" agent={result.engine==="agent"}/>}
    {mode==="analyst" && (result.events?.length ? <Timeline key={result.brief_id} events={result.events} claims={result.claims} titles={storyTitles(result)} onOpenSource={setEvidenceId} collapsed={stepsFolded}/> : result.flow && <FlowPanel flow={result.flow} triage={result.triage}/>)}
    {evidenceId && <EvidenceDrawer result={result} selectedId={evidenceId} onClose={()=>setEvidenceId(null)}/>}
  </>
}

function AnalystApp({me}: {me: Me}) {
  const [context,setContext] = useState<ReleaseContext | null>(null)
  const [contextError,setContextError] = useState<string | null>(null)
  const [loadingContext,setLoadingContext] = useState(true)
  const [brand,setBrand] = useState("")
  const [territory,setTerritory] = useState("")
  const [week,setWeek] = useState("")
  const [weekEnd,setWeekEnd] = useState("")  // brief-008: the last week of the period; equal to `week` for one week
  const [pending,setPending] = useState(false)
  const [result,setResult] = useState<BriefingResult | null>(null)
  const [runError,setRunError] = useState<string | null>(null)
  const [view,setView] = useState<"overview" | "home" | "triage" | "result" | "approved">("overview")
  // The current run's own view: the New briefing tab returns to it, so a run keeps going while the analyst looks elsewhere.
  const [runView,setRunView] = useState<"triage" | "result" | null>(null)
  const [looked,setLooked] = useState(true)  // false from the moment a run starts until its finished plan or brief has been on screen
  // An approved brief opened from the list has its own state, so opening one never touches a run in progress.
  const [dock,setDock] = useState<HTMLElement | null>(null)  // the slot above the question bar where answer feedback sits
  const [opened,setOpened] = useState<BriefingResult | null>(null)
  const [openedLoading,setOpenedLoading] = useState(false)
  const [openedError,setOpenedError] = useState<string | null>(null)
  const openedToken = useRef(0)
  const [requestScope,setRequestScope] = useState<{brand:string,territory:string,week:string,weekEnd:string,promotion:boolean,question:string,
    comparison:Comparison | null,definition:BriefDefinition} | null>(null)
  const [promotion,setPromotion] = useState(false)
  const [comparisons,setComparisons] = useState<Comparison[]>([])  // brief-010: the first is the primary; empty: the server's default comparison, the one the eval scores
  // brief-010 FR-000b: territories counted, measure, grain and relative to, pre-selected and always editable. The
  // question reader only proposes values (marked until the analyst touches the field).
  const [choices,setChoices] = useState<DefinitionChoices>(DEFAULT_CHOICES)
  const [proposed,setProposed] = useState<DefinitionField[]>([])
  const reviewPromotion = brand === "BXA" && promotion
  const releaseWeeks = context?.available_weeks ?? []
  const invalidPeriod = reviewPromotion ? null : periodError(week, weekEnd, releaseWeeks)
  const period = reviewPromotion ? [] : periodWeeks(week, weekEnd, releaseWeeks)
  const invalidComparison = reviewPromotion ? null : invalidPeriod ?? comparisonsError(comparisons, period, releaseWeeks)
  const invalidChoices = choicesError(choices)
  const [plan,setPlan] = useState<TriagePlan | null>(null)
  // Agent engine (core-007 FR-028/FR-031): jobs run on teammate or cloud CPU hosts; the app only queues them.
  const [engine,setEngine] = useState<"scripted" | "agent">("scripted")
  const [ask,setAsk] = useState("")
  const [agent,setAgent] = useState<AgentStatus | null>(null)
  const [triageJob,setTriageJob] = useState<string | null>(null)
  const [jobNote,setJobNote] = useState<string | null>(null)
  const [liveEvents,setLiveEvents] = useState<RunEvent[]>([])  // brief-009: the running job's progress, shown as the live timeline
  const [chip,setChip] = useState<Chip | null>(null)  // brief-006: the message bar
  const [barEvidence,setBarEvidence] = useState<{id: string} | null>(null)
  // brief-010: the bar on the form reads the question into it; the question then rides with Generate as the brief's question.
  const reader = useQuestionReader({brand,context,onApply:(v,q)=>{ if(v.territory) setTerritory(v.territory); setWeek(v.week); setWeekEnd(v.weekEnd); setPromotion(brand==="BXA" && v.promotion); setComparisons(v.comparison)
    setChoices(c=>({...c,...v.choices})); setProposed(v.proposed); setAsk(q) }, onStart:()=>setAsk("")})
  const clearQuestion = () => { setAsk(""); reader.clear() }
  const generation = useRef(0)
  const capabilities = context?.brands.find(b=>b.id===brand)
  const agentSupported = !!capabilities?.engines.includes("agent")
  const changeBrand = (id: string) => {
    if (!context?.product_ids.includes(id)) return
    generation.current += 1 // ignore every late result or job callback from the previous selection
    setBrand(id)
    const supported = context.brands.find(b=>b.id===id)?.engines ?? []
    setEngine(e=>supported.includes(e) ? e : "scripted")
    setPlan(null); setResult(null); setRunError(null); setRequestScope(null)
    setTriageJob(null); setJobNote(null); setJobState(null); setLiveEvents([]); setPending(false)
    setChip(null); setBarEvidence(null); clearQuestion(); setPromotion(false); setComparisons([]); setChoices(DEFAULT_CHOICES); setProposed([])
    setView(v=>v==="triage" || v==="result" ? "home" : v); setRunView(null)
  }

  useEffect(()=>{
    let live = true
    const poll = () => getAgentStatus().then(s=>{ if(live) setAgent(s) }).catch(()=>{ if(live) setAgent(null) })
    poll(); const t = setInterval(poll, 15000)
    return ()=>{ live=false; clearInterval(t) }
  },[])
  // The job's real state, from the server: queued, then running, then done (shown by JobProgress).
  const [jobState,setJobState] = useState<{kind: "triage" | "brief", status: "queued" | "running"} | null>(null)
  const describeJob = (job: AgentJob) => {
    if (job.progress) setLiveEvents(job.progress)
    if (job.status === "queued" || job.status === "running") {
      setJobState({kind: job.kind === "triage" ? "triage" : "brief", status: job.status})
      setJobNote(job.status === "queued" && !agent?.online && !(agent?.cloud?.enabled && agent.cloud.seconds_left > 0)
        ? "Waiting for the agent team to become available…"
        : job.status === "running" && job.host_kind === "cloud_cpu" ? `On the cloud CPU host: allow about ${agent?.cloud?.eta_minutes ?? 15} minutes.` : null)
      return
    }
    setJobState(null)
    setJobNote(null)
  }

  const refresh = async () => {
    setLoadingContext(true); setContextError(null)
    try {
      const c=await getContext()
      setContext(c)
      setBrand(b=>c.product_ids.includes(b)?b:(c.product_ids[0] ?? ""))
      setTerritory(t=>c.territory_ids.includes(t)?t:c.territory_ids[0])
      setWeek(w=>c.available_weeks.includes(w)?w:c.latest_week)
      setWeekEnd(w=>c.available_weeks.includes(w)?w:c.latest_week)
    } catch(e) {setContext(null);setContextError(message(e))}
    finally {setLoadingContext(false)}
  }
  useEffect(()=>{void refresh()},[])
  useEffect(()=>{ setWeekEnd(e=>e < week ? week : e) },[week])  // the Overview and the message bar also set the first week
  useEffect(()=>{ const s=sharedFromLocation(); if(s) void openApproved(s.briefId) },[])  // eslint-disable-line react-hooks/exhaustive-deps

  const submit = async (event?: React.FormEvent) => {
    event?.preventDefault()
    if(pending || invalidComparison || invalidChoices || !context || !context.product_ids.includes(brand) || !context.territory_ids.includes(territory) || !context.available_weeks.includes(week)) return
    const selected={brand,territory,week:reviewPromotion ? context.latest_week : week,weekEnd:reviewPromotion ? context.latest_week : weekEnd,promotion:reviewPromotion,comparison:reviewPromotion ? null : comparisons[0] ?? null,
      definition:{...choices,first_week:reviewPromotion ? null : week,last_week:reviewPromotion ? null : weekEnd,comparison:reviewPromotion || !comparisons.length ? null : comparisons},
      question:ask.trim().length>=3 ? ask.trim().slice(0,300) : reviewPromotion ? "Review promotion across the release." : "Generate the weekly brand-performance briefing."}
    // Plan review is always on in UAT (brief-002 FR-019): stages 1 to 3 and the code triage first.
    const token=++generation.current
    const active=()=>token===generation.current
    setPending(true);setRunError(null);setResult(null);setPlan(null);setRequestScope(selected);setView("triage");setRunView("triage");setJobNote(null);setLiveEvents([])
    try {
      if (engine==="agent") {
        const job = await submitAgentJob({kind:"triage", query: query(selected)})
        if (!active()) return
        setTriageJob(job.id)
        const done = await waitAgentJob(job.id, j=>{if(active()) describeJob(j)})
        if (!active()) return
        if (done.status==="failed") throw new Error(done.error ?? "The agent's triage failed.")
        setPlan(agentPlan(done))
      } else {
        const next=await getTriage(query(selected))
        if (active()) setPlan(next)
      }
    } catch(e) {if(active()) setRunError(message(e))}
    finally {if(active()){setPending(false);setJobNote(null);setJobState(null);setLiveEvents([])}}
  }
  const query = (s: NonNullable<typeof requestScope>) => ({intent:s.promotion ? "promotion_review" as const : "weekly_brief" as const,
    brand_id:s.brand,territory_id:s.territory,week_start:s.week,week_end:s.weekEnd > s.week ? s.weekEnd : null,question:s.question,comparison:s.comparison,definition:s.definition})
  const approvePlan = async (decision: TriageDecision) => {
    if(!requestScope) return
    const token=++generation.current, active=()=>token===generation.current
    setPending(true);setRunError(null);setResult(null);setView("result");setRunView("result");setJobNote(null);setLiveEvents([])
    try {
      if (plan?.engine==="agent" && triageJob) {
        const job = await submitAgentJob({kind:"brief", query: query(requestScope), triage_job: triageJob, decision})
        if (!active()) return
        const done = await waitAgentJob(job.id, j=>{if(active()) describeJob(j)})
        if (!active()) return
        if (done.status==="failed") throw new Error(done.error ?? "The agent's run failed.")
        setResult(agentBrief(done))
      } else {
        const response=await getBriefing({...query(requestScope)}, decision)
        if (active()) setResult(response)
      }
    } catch(e) {if(active()) setRunError(message(e))}
    finally {if(active()){setPending(false);setJobNote(null);setJobState(null);setLiveEvents([])}}
  }
  const openApproved = async (id: string) => {
    const token=++openedToken.current, active=()=>token===openedToken.current
    setOpened(null);setOpenedError(null);setOpenedLoading(true);setView("approved");setChip(null);setBarEvidence(null)
    try {
      const next=await openBrief(id, "analyst")
      if (active()) setOpened(next)
    } catch(e) {if(active()) setOpenedError(message(e))} finally {if(active()) setOpenedLoading(false)}
  }
  const closeOpened = () => { openedToken.current++; setOpened(null);setOpenedError(null);setOpenedLoading(false);setChip(null);setBarEvidence(null) }
  const selectable = !!context && context.product_ids.includes(brand) && !loadingContext && !pending
  const tab = view==="approved" ? "approved" : view==="overview" ? "overview" : "new"
  const scopeText = (s: NonNullable<typeof requestScope>) => `${s.brand} · ${labelTerritory(s.territory)} · ${s.promotion ? "release-wide Promotion review" : s.weekEnd > s.week ? `weeks ${labelWeek(s.week)} to ${labelWeek(s.weekEnd)}` : `week of ${labelWeek(s.week)}`}`
  // Back on the form with nothing running, the last run is let go; while one runs, the New briefing tab still leads back to it.
  // A run "holds" the New briefing tab while it is going, while its plan waits for review, or while its finished brief or error has not been looked at.
  const held = pending || (runView==="triage" && !!plan) || !looked
  useEffect(()=>{ if (view==="home" && !held) setRunView(null) },[view])  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(()=>{ if (pending) setLooked(false); else if (view==="triage" || view==="result") setLooked(true) },[pending,view])
  // One quiet line on the other tabs while a run is going, or has finished and not been looked at yet.
  const awayFromRun = view==="home" || view==="overview" || view==="approved"
  const runLine = !awayFromRun || !runView ? null
    : pending ? {text: `A briefing is being prepared${requestScope ? ` · ${scopeText(requestScope)}` : ""}`, go: "View progress"}
    : runView==="triage" && plan ? {text: "The plan for your briefing is ready for review", go: "Review it"}
    : runView==="result" && result && !looked ? {text: `Your briefing is ready${requestScope ? ` · ${scopeText(requestScope)}` : ""}`, go: "Open it"}
    : runError && !looked ? {text: "Your briefing could not be generated", go: "See why"}
    : null
  const openedShown = !!(opened || openedLoading || openedError)
  // "Start a new briefing": the form again, from a brief just read. The analyst's choices stay; the read question and
  // the message bar's chip go. A run that is still held (see above) stays in the status line.
  const introFocus = useRef(false)
  const startNew = () => {
    clearQuestion(); closeOpened(); introFocus.current = true
    if (!held) setRunView(null)
    setView("home")
  }
  useEffect(()=>{ if (view==="home" && introFocus.current) { introFocus.current = false; document.getElementById("new-briefing-intro")?.focus() } },[view])
  const openedBack = useRef<HTMLButtonElement>(null)
  useEffect(()=>{ if (view==="approved" && openedShown) openedBack.current?.focus() },[view, openedShown])
  // When the scope form gives way to the plan or the brief, the button that was pressed is gone: put focus on the
  // first control of the new view, so a keyboard user does not start again from the top of the page.
  const scopeBack = useRef<HTMLButtonElement>(null)
  useEffect(()=>{ if (view==="triage" || view==="result") scopeBack.current?.focus() },[view])
  return <Shell me={me} onBriefingHome={()=>setView("overview")} briefingBusy={pending}><FeedbackDock slot={dock}>
    <div className={`${view==="overview" ? "workspace-wide" : "workspace-content"} pt-5 sm:pt-6`}>{/* The Overview greets with the data line under it, as the Forecast lane does; other tabs start at the tab row */}{view==="overview" && <Greeting detail={context ? `Data through ${labelWeek(context.latest_week)}, across ${context.territory_ids.length} territories.` : undefined}/>}<SubTabs aside={<label className="pa-noprint flex items-center gap-2 text-xs text-muted">Brand
      <select className={`${FIELD} w-auto`} value={brand} onChange={e=>changeBrand(e.target.value)} disabled={loadingContext || !context?.brands.length}>
        {context?.brands.map(b=><option key={b.id} value={b.id}>{b.name} ({b.id})</option>)}
      </select></label>} label="Weekly briefing" panelId="briefing-panel" value={tab} onChange={t=>{ if (t==="approved" || t==="overview") setView(t); else if (tab!=="new") setView(runView && held ? runView : "home") }} options={[["overview","Overview","briefing.overview"],["new","New briefing","briefing.new"],["approved","Approved briefings","briefing.approved"]] as const}/></div>
    {contextError && <div className="workspace-content py-4"><Notice tone="error" role="alert">{contextError}<button className="ml-2 underline" onClick={()=>void refresh()}>Retry connection</button></Notice></div>}
    {runLine && <div role="status" className="workspace-content pa-noprint pb-1 text-sm text-muted">{runLine.text} · <button type="button" className="text-primaryink hover:underline" onClick={()=>setView(runView!)}>{runLine.go}</button></div>}
    <div role="tabpanel" id="briefing-panel" aria-labelledby={`briefing-panel-tab-${tab}`}>{context && !context.product_ids.length ? <div className="workspace-content py-8"><h2 className="text-xl">No brand access</h2><p className="mt-2 text-sm text-muted">Your account has no authorized Briefing brands. Ask the project owner to assign brand access, then sign out and sign in again.</p></div> : view==="overview" ? brand && <><h2 className="sr-only">Overview</h2><Overview key={brand} brand={brand} week={week} onWeek={w=>{setWeek(w);setWeekEnd(w)}} weeks={context?.available_weeks ?? []} onGenerate={(t,w)=>{clearQuestion();setTerritory(t);setWeek(w);setWeekEnd(w);setView("home")}}/></> : view==="home" ? <div key="home" className="workspace-content pa-stagger space-y-5 py-8">
      <IntroWithHow introId="new-briefing-intro">Generate the week's brand-performance briefing, check its evidence, and approve it for the Brand Director.</IntroWithHow>

      <form onSubmit={submit} className={`${PANEL} space-y-6 p-6`} aria-busy={loadingContext}>
        <h2 className="sr-only">New briefing</h2>
        {/* The always-present region is announced when the question has been read. */}
        <div role="status" className="empty:hidden">{reader.read && ask && <div className="space-y-1.5 rounded-lg border border-rule px-4 py-3">
          <p className="text-sm text-ink">“{ask}”</p>
          <p className="text-xs text-muted"><span className="font-medium text-ink">{readByLabel(reader.read)}.</span> Check the choices below, then generate.</p>
          {!!reader.read.notes.length && <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted">{reader.read.notes.map(n=><li key={n}>{n}</li>)}</ul>}
          <button type="button" onClick={clearQuestion} className="text-xs text-primaryink hover:underline">Clear</button>
        </div>}</div>
        <fieldset className="space-y-4" aria-label="Brief definition">
          <div><h3 className="text-sm font-semibold">What the brief counts</h3><p className="mt-1 text-xs text-muted">Six choices, each pre-selected. The brief states them in its Assumptions, and the numbers follow them.</p></div>
          <PeriodPicker first={week} last={weekEnd} weeks={releaseWeeks} disabled={!selectable || reviewPromotion} onFirst={w=>{ if(weekEnd===week) setWeekEnd(w); setWeek(w) }} onLast={setWeekEnd} labelWeek={labelWeek}/>
          {!reviewPromotion && <ComparisonPicker value={comparisons} onChange={setComparisons} period={period} weeks={releaseWeeks} disabled={!selectable} labelWeek={labelWeek}/>}
          <DefinitionPicker value={choices} proposed={proposed} disabled={!selectable} onChange={(next,field)=>{ setChoices(next); setProposed(p=>p.filter(f=>f!==field)) }}/>
        </fieldset>
        <label className={LABEL}>Territory
          <select className={FIELD} value={territory} onChange={e=>setTerritory(e.target.value)} disabled={!selectable}>{context?.territory_ids.map(id=><option key={id} value={id}>{labelTerritory(id)}</option>)}</select>
        </label>
        {brand === "BXA" && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={promotion} onChange={e=>setPromotion(e.target.checked)} /> Promotion review across the release</label>}
        <fieldset><legend className="mb-1.5 text-xs font-medium text-muted">Engine</legend>
          <div className="divide-y divide-rule rounded-lg border border-rule">
            <label className="flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-paper/50"><input type="radio" name="engine" checked={engine==="scripted"} onChange={()=>setEngine("scripted")} className="mt-1"/><span><span className={`block text-sm ${engine==="scripted" ? "text-ink" : "text-muted"}`}>Scripted</span><span className="block text-xs text-muted">Instant. Runs the standard checks in a fixed order.</span></span></label>
            {agentSupported && <label className={`flex items-start gap-3 px-4 py-3 transition-colors ${!agentSupported || agent?.configured===false ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:bg-paper/50"}`}><input type="radio" name="engine" checked={engine==="agent"} disabled={!agentSupported || agent?.configured===false} onChange={()=>setEngine("agent")} className="mt-1"/><span title={agent?.model ? `Model: ${modelName(agent.model)}` : undefined}><span className={`block text-sm ${engine==="agent" ? "text-ink" : "text-muted"}`}>Agent team <span className="text-xs text-muted">· experimental</span></span><span className="block text-xs text-muted">A manager and two specialist agents investigate the week. {agent?.builtin ? "Usually a minute or two." : agent?.online ? "A few minutes per step." : agent?.cloud?.enabled && agent.cloud.seconds_left>0 ? `About ${agent.cloud.eta_minutes ?? 15} minutes for a brief.` : "Waits until an agent host is available."}</span></span></label>}
          </div>
        </fieldset>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-4">
          <span className="text-xs text-muted">{loadingContext ? "Loading the data release…" : engine==="agent" ? "You review the agents' plan before they investigate." : "You review the plan before the checks run."}</span>
          <button type="submit" disabled={!selectable || !!invalidComparison || !!invalidPeriod || !!invalidChoices} className={BTN}>Generate briefing</button>
        </div>
      </form>
    </div> : view==="approved" ? <div key="approved" className="workspace-content pa-fade space-y-4 py-8">{openedShown ? <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button ref={openedBack} className="flex items-center gap-1.5 text-sm text-primaryink hover:underline" onClick={closeOpened}><Icon name="back" className="h-4 w-4"/>All approved briefings</button>
      </div>
      {openedLoading && <p role="status" className="text-sm text-muted">Opening the briefing…</p>}
      {openedError && <Notice tone="error" role="alert">{openedError}</Notice>}
      {opened && <AnalystBrief stepsFolded onStartNew={startNew} result={opened} onChange={r=>setOpened(cur=>cur?.brief_id===r.brief_id?r:cur)} onAsk={setChip} openEvidence={barEvidence}/>}
    </> : <><p className="text-sm text-muted">What the Brand Director can open, on the current data release.</p><PublishedList onOpen={id=>void openApproved(id)}/></>}</div>
    : <div className="workspace-content space-y-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button ref={scopeBack} className="flex items-center gap-1.5 text-sm text-primaryink hover:underline" onClick={()=>{ setView("home"); if (!pending) setRunView(null) }}><Icon name="back"/>Change scope</button>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {requestScope && <span className="text-xs text-muted">{scopeText(requestScope)}</span>}
        </div>
      </div>
      {pending && (jobState
        ? <JobProgress kind={jobState.kind} status={jobState.status} note={jobNote}/>
        : <div role="status" className="space-y-3"><span className="sr-only">{view === "triage" ? "Preparing the triage plan…" : "Preparing the briefing…"}</span>
            <div className="pa-skeleton h-5 w-2/5"/><div className={`${PANEL} space-y-3 p-6`}><div className="pa-skeleton h-6 w-3/5"/><div className="pa-skeleton h-3 w-full"/><div className="pa-skeleton h-3 w-11/12"/><div className="pa-skeleton h-3 w-4/5"/></div></div>)}
      {pending && engine==="agent" && jobState && <Timeline events={liveEvents} live/>}
      {runError && <Notice tone="error" role="alert" title={view==="triage" ? "The triage plan could not be built." : "Briefing could not be generated."}><p className="mt-2">{runError}</p><p className="mt-2">No mock result was substituted.</p>{view==="result" && plan && <button className="mt-2 underline" onClick={()=>{setRunError(null);setView("triage");setRunView("triage")}}>Back to the triage plan</button>}</Notice>}
      {view==="triage" && plan && !pending && <TriageReview plan={plan} busy={pending} onApprove={d=>void approvePlan(d)}/>}
      {view==="result" && result && <AnalystBrief onStartNew={pending ? undefined : startNew} result={result} onChange={r=>setResult(cur=>cur?.brief_id===r.brief_id?r:cur)} onAsk={setChip} openEvidence={barEvidence}/>}
    </div>}</div>
    {brand && (view==="home" || (view==="result" && (!!result || agentSupported)) || (view==="triage" && agentSupported) || (view==="approved" && !!opened)) && <div className="workspace-content sticky bottom-0 z-20"><div ref={setDock} className="pa-dock"/>{/* the feedback card on the open answer sits here, on top of the bar */}<MessageBar key={brand} briefId={view==="result" && result ? result.brief_id : view==="approved" && opened ? opened.brief_id : null} pending={view==="approved" ? false : pending} chip={chip} onClearChip={()=>setChip(null)}
      onRead={view==="home" ? reader.run : undefined} readBusy={reader.busy} readError={view==="home" ? reader.error : null}
      onOfferScope={o=>{ clearQuestion(); if(o.brand && o.brand!==brand){if(!context?.product_ids.includes(o.brand)){setRunError("Your account has no access to that brand.");return}changeBrand(o.brand)} if(o.territory) setTerritory(o.territory); if(o.week){ setWeek(o.week); setWeekEnd(o.week) } setPromotion(false); setComparisons(o.comparison ? [o.comparison] : []); setView("home") }} onOpenEvidence={id=>setBarEvidence({id})} agentAvailable={agentSupported && !!agent?.builtin}/></div>}
  </FeedbackDock></Shell>
}

function LeaderApp({me}: {me: Me}) {
  const [brief,setBrief] = useState<LeadershipBrief | null>(null)
  const [error,setError] = useState<string | null>(null)
  const [loading,setLoading] = useState(false)
  const open = async (id: string) => {
    setLoading(true); setError(null)
    try { setBrief(await openBrief(id, "leadership")) } catch(e) { setError(message(e)) } finally { setLoading(false) }
  }
  return <Shell me={me} onBriefingHome={()=>{setBrief(null);setError(null)}}>
    <div className="workspace-content space-y-6 py-8 sm:py-10">
      {!me.brand_ids.length ? <><h2 className="text-xl">No brand access</h2><p className="text-sm text-muted">Ask the project owner to assign brand access, then sign out and sign in again.</p></> : brief || loading || error ? <>
        <button className="flex items-center gap-2 text-sm text-primaryink hover:underline" onClick={()=>{setBrief(null);setError(null)}}><Icon name="back"/>All approved briefings</button>
        {loading && <p role="status" className="text-sm text-muted">Opening the briefing…</p>}
        {error && <Notice tone="error" role="alert">{error}</Notice>}
        {brief && <SummaryCard brief={brief}/>}
      </> : <><Greeting/><IntroWithHow>Executive summaries the Commercial Analyst has reviewed and approved.</IntroWithHow><PublishedList onOpen={id=>void open(id)}/></>}
    </div>
  </Shell>
}

export default function App() {
  const [me,setMe] = useState<Me | null>(null)
  const [error,setError] = useState<string | null>(null)
  useEffect(()=>{
    getMe().then(setMe).catch(e=>{ if (e instanceof NotSignedIn) window.location.assign("/auth/login"); else setError(message(e)) })
  },[])
  if (error) return <Centered><h1 className="mt-5 text-lg font-semibold">Cannot reach PharmAgentics</h1><p className="mt-2 text-sm text-muted">{error}</p></Centered>
  if (!me) return <Centered><p className="mt-5 text-sm text-muted">Checking your sign-in…</p></Centered>
  const briefing = me.lanes.briefing
  if (!briefing) {
    if (me.lanes.forecast?.available) return <Shell me={me} startInForecast>{null}</Shell>
    return <Centered>
      <h1 className="mt-5 text-lg font-semibold">No access</h1>
      <p className="mt-2 text-sm text-muted">Your account has no authorized workspace. Ask the project owner to assign a workspace role and brand access.</p>
      <a className="mt-5 inline-block text-sm font-medium text-primaryink hover:underline" href="/auth/logout">Sign out</a>
    </Centered>
  }
  return briefing.actions.includes("run") ? <AnalystApp me={me}/> : <LeaderApp me={me}/>
}
