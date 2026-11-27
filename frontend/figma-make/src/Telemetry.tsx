import { useEffect, useState, type ReactNode } from "react"
import { FeedbackResponses } from "./FeedbackResponses"
import { FeedbackReview } from "./FeedbackReview"
import { Notice } from "./agent/primitives"
import { ForecastDriverRecovery } from "./ForecastDrivers"
import { RollIn, modelName, when } from "./agent/primitives"
import { useDrawOnView } from "./motion"
import { getTelemetry, getUsage, type CaseTable, type LaneUsage, type Spread, type Telemetry as T, type TelemetryRun, type Usage } from "./agent/telemetryApi"

const PANEL = "rounded-xl border border-rule bg-sheet"
const NAMES: Record<string, string> = {
  briefing_agent: "Briefing agent", briefing_scripted: "Briefing, scripted baseline", briefing_lowcode: "Briefing, low-code agent",
  forecast_scripted: "Forecast, scripted baseline", forecast_rules: "Forecast, rules (no model)",
  forecast_agent: "Forecast agent (model reads and writes)", forecast_investigator: "Forecast, model investigates (comparison)", reference: "Reference answers (control)", naive_llm: "Model without data (control)",
}
const RUN_LABELS: Record<string, string> = {
  key_fact_recall_pooled: "Key facts found, pooled", finding_recall_pooled: "Findings found, pooled",
  key_fact_target_met: "Key-fact target met", finding_target_met: "Findings target met", over_word_budget: "Briefs over the word budget",
}
const label = (k: string) => RUN_LABELS[k] ?? k.replace(/[_.]/g, " ").replace(/^./, c => c.toUpperCase())
// core-011: the pooled share (all golden facts or findings of the run together) is what the targets are set on; a run
// logged before pooling existed falls back to the per-case mean.
const keyFacts = (m: Record<string, number>) => m.key_fact_recall_pooled ?? m.key_fact_recall
const findings = (m: Record<string, number>) => m.finding_recall_pooled ?? m.finding_recall
// Code fills every number an agent brief states, so for an agent the key-fact score only shows what it dropped: the
// scripted engine's key facts found minus the agent's, on the latest runs (core-011 "numbers lost by the agent"; target 0).
const AGENT_SYSTEM = /_(agent|lowcode)(@[A-Z]+|$)/
const LOST_TITLE = "Numbers lost by the agent: the scripted engine's key facts found minus this run's (target 0). Code fills every number, so this shows only what the agent dropped."
const runValue = (k: string, v: number) => k.endsWith("_target_met") ? (v >= 0.5 ? "Yes" : "No") : k === "over_word_budget" ? String(Math.round(v)) : pct(v)
const pct = (v: number) => (v <= 1 && v >= 0 ? `${Math.round(v * 100)}%` : v.toFixed(2))
// A score as people read it: a share as a percent, a count as a whole number, a flag as Yes/No; no unit means a share.
const fmt = (v: number, unit?: "share" | "count" | "flag") =>
  unit === "count" ? String(Math.round(v)) : unit === "flag" ? (v >= 0.5 ? "Yes" : "No") : pct(v)
// Exported: Forecast driver recovery prints its dates the same way.
// A Briefing run names its brand: "@BXC" is a Lipidara run, no suffix a Cardiovela one (the harness's default brand).
const BRANDS: Record<string, string> = { BXA: "Cardiovela", BXC: "Lipidara", "BXA+BXC": "Cardiovela and Lipidara" }
const name = (r: TelemetryRun) => {
  const [base, brand] = r.system.split("@")
  const n = NAMES[base] ?? base
  return base.startsWith("briefing") ? `${n} · ${BRANDS[brand ?? "BXA"] ?? brand}` : n
}
// "briefing_agent:anthropic:claude-haiku-5-5" -> "Briefing agent · Haiku"
const baseOf = (system: string) => system.split(":")[0]
const tableName = (t: CaseTable) => { const base = baseOf(t.system); return [NAMES[base] ?? base, modelName(t.system.slice(base.length + 1))].filter(Boolean).join(" · ") }
const list = (o: Record<string, number> | undefined) => Object.entries(o ?? {}).map(([k, v]) => `${v} ${k}`).join(", ") || "none"
const spread = (s: Spread | undefined, unit: string, scale = 1) =>
  s ? `${((s.p50 ?? 0) / scale).toFixed(1)} ${unit} · p95 ${((s.p95 ?? 0) / scale).toFixed(1)} ${unit}` : "no data yet"

function Heading({ title, note }: { title: string, note?: ReactNode }) {
  return <div className="pt-2"><h3 className="text-lg font-bold leading-[1.6]"><span className="pa-mark">{title}</span></h3>{note && <p className="mt-2 text-sm text-muted">{note}</p>}</div>
}

const NUMERIC = /\d/

function Figures({ items }: { items: [string, string, ReactNode, ReactNode?][] }) {
  return <section aria-label="Headline figures" className={`${PANEL} grid grid-cols-2 lg:grid-cols-4`}>
    {items.map(([k, v, sub, sub2], i) => <div key={k} className={`min-w-0 p-5 ${i % 2 ? "border-l border-rule" : ""} ${i > 1 ? "border-t border-rule lg:border-t-0" : ""} ${i === 2 ? "lg:border-l" : ""}`}>
      <div className="text-xs text-muted">{k}</div>{/* A figure spins in; a figure that is words ("Too few to rate") is plain text that wraps to the tile */}
      {NUMERIC.test(v) && !/[a-z]{3,}/i.test(v) ? <div className="mt-2 font-serif text-3xl tabular-nums"><RollIn key={v} text={v} delay={150 + i * 90}/></div>
        : <div className="mt-2 break-words font-serif text-2xl leading-tight">{v}</div>}<div className="mt-1.5 text-xs text-muted">{sub}</div>{sub2 && <div className="mt-0.5 text-xs text-muted">{sub2}</div>}
    </div>)}
  </section>
}

function Rows({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
    {rows.map(([k, v]) => <div key={k} className="flex items-baseline justify-between gap-3 border-b border-rule py-1.5 text-sm"><dt className="text-muted">{k}</dt><dd className="text-right tabular-nums">{v}</dd></div>)}
  </dl>
}

function laneRows(lane: "briefing" | "forecast", u: LaneUsage): [string, ReactNode][] {
  const rows: [string, ReactNode][] = [
    [lane === "briefing" ? "Briefs requested" : "Forecast explanations run", u.requests],
    ["Opened", u.opens], ["Review decisions (events)", list(u.decisions)], ["Answer votes", `${u.votes.up} up, ${u.votes.down} down`],
  ]
  if (lane === "briefing") rows.push(["Engines", list(u.engines)], ["Scripted response time", spread(u.scripted_ms, "s", 1000)],
    ["Agent jobs", list(u.agent_jobs)], ["Agent brief, queue to result", spread(u.agent_seconds, "s")])
  return rows
}

function InUse({ u }: { u: Usage }) {
  const lanes = (["briefing", "forecast"] as const).filter(l => u.lanes[l])
  return <>
    <Heading title="In use" note={`${u.since ? `Since ${when(u.since)}.` : "No use recorded yet."} ${u.tester_records ? `Includes ${u.tester_records} record${u.tester_records === 1 ? "" : "s"} from the shared tester login.` : ""} Updated every 5 minutes.`}/>
    <section className={`${PANEL} divide-y divide-rule`}>
      {lanes.map(l => {
        const weeks = Object.entries(u.lanes[l]!.weekly)
        return <div key={l} className="p-5"><h4 className="text-sm font-semibold">{l === "briefing" ? "Weekly briefing" : "Forecast explanation"}</h4>
          <div className="mt-2"><Rows rows={laneRows(l, u.lanes[l]!)}/></div>
          {!!weeks.length && <p className="mt-3 text-xs text-muted">Requests by week: {weeks.map(([w, n]) => `week of ${when(w)}: ${n}`).join(" · ")}</p>}
        </div>
      })}
      <div className="p-5"><h4 className="text-sm font-semibold">Ratings</h4><div className="mt-2"><Rows rows={[
        ["Sessions rated", list(u.sessions)],
        ["Usability (SUS-equivalent, UMUX-Lite)", u.umux ? `${u.umux.sus_equivalent_mean} of 100 (${u.umux.n} responses)` : "no responses yet"],
        ...(u.sus ? [["System Usability Scale, first questionnaire", `${u.sus.mean} of 100 (${u.sus.n} responses)`] as [string, string]] : []),
        ...(u.cloud_seconds ? [["Cloud agent time this month", `${u.cloud_seconds.used.toLocaleString()} of ${u.cloud_seconds.limit.toLocaleString()} s`] as [string, ReactNode]] : []),
      ]}/></div></div>
    </section>
  </>
}

const SCORERS: Record<string, string> = {
  claims_reconcile: "Claims reconcile", golden_number_recall: "Number recall", key_fact_recall: "Key facts found",
  finding_recall: "Findings found", numbers_lost: "Numbers lost",
}
const HEADER_TITLES: Record<string, string> = {
  numbers_lost: "Key-fact recall of the scripted brief minus this agent's, on the same golden version. Positive: the agent stated fewer of the facts code already gets.",
}
const KIND_GROUPS = [["code", "Code checks"], ["agent", "Agent checks"], ["safety", "Safety"]] as const
// Score columns under Code checks, Agent checks and Safety; a snapshot with no kinds keeps one flat header.
function grouped(t: CaseTable) {
  const kinds = t.kinds
  if (!kinds) return null
  const groups = KIND_GROUPS.map(([kind, title]) => ({ kind, title, cols: t.scorers.filter(k => (kinds[k] ?? "agent") === kind) })).filter(g => g.cols.length)
  return groups.length ? groups : null
}
const NEEDS: Record<string, string> = { plan_cut: "plan cut", segment_pct: "segment percentage", restatement: "restatement", national_card: "national card" }
// "Needs a plan cut: 2 · missed: 1": what a below-target score lacks, split into a capability the system does not have and a plain miss.
function belowText(b: NonNullable<CaseRowBelow>[number]) {
  const needs = Object.entries(b.needs).map(([k, n]) => `needs ${NEEDS[k] ?? k}: ${n}`)
  return `${scorerName(b.scorer)} ${pct(b.score)}, target ${pct(b.target)} · ${[...needs, ...(b.missed ? [`missed: ${b.missed}`] : [])].join(" · ") || "no missing item recorded"}`
}
type CaseRowBelow = CaseTable["rows"][number]["below"]
const scorerName = (k: string) => SCORERS[k] ?? label(k)
const LANES: Record<string, string> = { briefing: "Briefing", forecast: "Forecast" }
const MARK = "ml-1.5 whitespace-nowrap text-xs text-muted underline decoration-dotted underline-offset-2"

function CaseScore({ v, stuck, worse, lost, unit }: { v: number | null | undefined, stuck: boolean, worse?: { previous: number; latest: number }, lost?: boolean, unit?: "share" | "count" | "flag" }) {
  if (v == null) return <span className="text-muted" title="Not scored in this run">{"—"}<span className="sr-only">not scored</span></span>
  const score = lost ? `${Math.round(v * 100)}%` : fmt(v, unit)
  return <>{stuck ? <span className="text-muted">{score}</span> : score}
    {stuck && <span className={MARK} title="Zero in every listed run">stuck</span>}
    {worse && <span className={MARK} title={`Was ${fmt(worse.previous, unit)} in the last run`}>worse<span className="sr-only"> than the last run, was {fmt(worse.previous, unit)}</span></span>}
  </>
}

function CaseTableView({ t, open }: { t: CaseTable, open: boolean }) {
  const stuck = t.rows.reduce((n, r) => n + r.stuck.length, 0)
  const worse = t.rows.reduce((n, r) => n + r.fallen.length, 0)
  const groups = grouped(t)
  const cols = groups ? groups.flatMap(g => g.cols) : t.scorers
  const edge = (k: string) => (groups?.some(g => g.cols[0] === k && g !== groups[0]) ? " border-l border-rule" : "")
  const head = (k: string) => <th key={k} scope="col" title={HEADER_TITLES[k]} className={`whitespace-nowrap px-3 py-2 text-right font-medium${edge(k)}`}>{scorerName(k)}{t.report_only.includes(k) && <span className="block font-normal">report only</span>}</th>
  return <details open={open} className={PANEL}>
    <summary className="flex cursor-pointer list-none flex-wrap items-baseline gap-x-4 gap-y-1 px-5 py-3 hover:bg-paper/60">
      <span className="text-sm font-semibold">{tableName(t)}</span>
      <span className="text-xs text-muted">{LANES[t.lane] ?? t.lane} · run {t.run_id} · {when(t.started)} · {t.rows.length} cases · {stuck} stuck · {worse} worse than the last run</span>
    </summary>
    <div role="region" tabIndex={0} aria-label={`${tableName(t)}, per-case scores`} className="relative overflow-x-auto border-t border-rule">
      <table className="w-full min-w-max text-left text-sm">
        <thead className="text-xs text-muted">
          {groups && <tr>
            <th scope="col" rowSpan={2} className="sticky left-0 bg-sheet px-5 py-2 align-bottom font-medium">Case</th>
            {groups.map((g, i) => <th key={g.kind} scope="colgroup" colSpan={g.cols.length} className={`px-3 pt-2 text-center font-medium${i ? " border-l border-rule" : ""}`}>{g.title}</th>)}
          </tr>}
          <tr>
            {!groups && <th scope="col" className="sticky left-0 bg-sheet px-5 py-2 font-medium">Case</th>}
            {cols.map(head)}
          </tr>
        </thead>
        <tbody>{t.rows.map(r => <tr key={r.case} className="border-t border-rule">
          <th scope="row" title={r.persona ? `Asked by ${r.persona.replace(/^(P[1-4]|CA|BM)\s+/, "")}` : undefined} className="sticky left-0 bg-sheet px-5 py-2 text-left font-normal"><span className="whitespace-nowrap tabular-nums">{r.case}</span>
            {r.below?.map(b => <span key={b.scorer} className="block max-w-xs text-xs text-amber">{belowText(b)}</span>)}</th>
          {cols.map(k => <td key={k} className={`px-3 py-2 text-right tabular-nums${edge(k)}`}><CaseScore v={r.scores[k]} stuck={r.stuck.includes(k)} worse={r.fallen.find(f => f.scorer === k)} lost={k === "numbers_lost"} unit={t.units?.[k]}/></td>)}
        </tr>)}</tbody>
      </table>
    </div>
  </details>
}

const tableKey = (t: CaseTable) => `${baseOf(t.system)}|${t.lane}`
function PerCase({ tables, targets }: { tables: CaseTable[], targets?: Record<string, number> }) {
  // The newest table of each system and lane leads, if it ran on the lane's current golden set (the golden version of
  // the lane's most recent run); controls, earlier tables and runs on an older golden set fold away.
  const current = new Map<string, { started: string, golden: string | null }>()
  for (const t of tables) if (!t.control && (current.get(t.lane)?.started ?? "") < t.started) current.set(t.lane, { started: t.started, golden: t.golden_version })
  const newest = new Map<string, CaseTable>()
  for (const t of tables) if (!t.control && t.golden_version === current.get(t.lane)?.golden && (newest.get(tableKey(t))?.started ?? "") < t.started) newest.set(tableKey(t), t)
  const main = tables.filter(t => newest.get(tableKey(t)) === t)
  const older = tables.filter(t => !main.includes(t))
  return <>
    <Heading title="Per-case results" note={`Latest run of each system, one row per golden question. Stuck: zero in every listed run. Worse: clearly lower than in the run before (5 points for a share, 10% or at least 1 for a count). A dash means the case was not scored.${targets ? ` Targets: key facts found ${pct(targets.key_fact_recall ?? 0)}, findings found ${pct(targets.finding_recall ?? 0)}. Under a target, a row says what is missing: a capability the system needs, or a plain miss.` : ""}`}/>
    <div className="space-y-3">
      {main.map((t, i) => <CaseTableView key={`${t.system}|${t.lane}|${t.run_id}`} t={t} open={i === 0}/>)}
      {!!older.length && <details className={`${PANEL} p-5`}><summary className="cursor-pointer text-sm font-semibold">Older runs and controls ({older.length})</summary>
        <div className="mt-3 space-y-3">{older.map(t => <CaseTableView key={`${t.system}|${t.lane}|${t.run_id}`} t={t} open={false}/>)}</div></details>}
    </div>
  </>
}

const COLS = "sm:grid-cols-[minmax(0,1fr)_7rem_6rem_6rem_6rem_6rem]"
function Scores({ runs, targets }: { runs: TelemetryRun[], targets?: Record<string, number> }) {
  const view = useDrawOnView<HTMLElement>(0.05)
  const cell = (v: number | undefined, at = 0) => { const s = v != null ? pct(v) : "–"; return <RollIn key={s} text={s} delay={150 + at * 60}/> }
  const t = (k: string) => targets?.[k] != null ? ` (target ${pct(targets[k])})` : ""
  const keyFactCell = (r: TelemetryRun, at: number) => {
    const kf = keyFacts(r.metrics)
    // the same lane's and brand's scripted run: briefing_agent@BXC is set against briefing_scripted@BXC
    const scripted = runs.find(x => x.lane === r.lane && x.system === r.system.replace(AGENT_SYSTEM, "_scripted$2"))
    const scriptedKf = scripted ? keyFacts(scripted.metrics) : undefined
    if (!AGENT_SYSTEM.test(r.system) || kf == null || scriptedKf == null) return cell(kf, at)
    const lost = `${Math.round(Math.max(0, scriptedKf - kf) * 100)} pts lost`
    return <span title={LOST_TITLE}><RollIn key={lost} text={lost} delay={150 + at * 60}/></span>
  }
  return <section ref={view} className={PANEL}>
    <div className={`hidden gap-4 border-b border-rule py-2 pl-10 pr-5 text-[11px] text-muted sm:grid ${COLS}`}>
      <span>System</span><span>Run</span><span className="text-right" title={`Share of the golden key facts the run stated, all cases pooled${t("key_fact_recall")}. Agent rows show the points lost against the scripted engine instead (target 0).`}>Key facts found</span>
      <span className="text-right" title={`Share of the golden findings the run reached, all cases pooled${t("finding_recall")}`}>Findings found</span>
      <span className="text-right">Number recall</span><span className="text-right">Claims reconcile</span>
    </div>
    <ul className="divide-y divide-rule">{runs.map((r, at) => <li key={r.run_id}>
      <details>
        <summary className={`grid cursor-pointer list-none grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 py-3 pl-10 pr-5 hover:bg-paper/60 ${COLS}`}>
          <span className="min-w-0"><span className="block truncate text-sm">{name(r)}</span>{r.model && <span className="block truncate text-xs text-muted">{modelName(r.model)}</span>}</span>
          <span className="text-xs text-muted sm:text-sm">{when(r.started)}</span>
          <span className="text-sm tabular-nums sm:text-right"><span className="text-xs text-muted sm:hidden">Key facts </span>{keyFactCell(r, at)}</span>
          <span className="text-right text-sm tabular-nums"><span className="text-xs text-muted sm:hidden">Findings </span>{cell(findings(r.metrics), at)}</span>
          <span className="text-sm tabular-nums sm:text-right"><span className="text-xs text-muted sm:hidden">Number recall </span>{cell(r.metrics.golden_number_recall, at)}</span>
          <span className="text-right text-sm tabular-nums"><span className="text-xs text-muted sm:hidden">Claims </span>{cell(r.metrics.claims_reconcile, at)}</span>
        </summary>
        <div className="pb-4 pl-10 pr-5">
          <p className="mb-2 text-xs text-muted">{r.cases} questions · {r.reruns} rerun{r.reruns > 1 ? "s" : ""}{r.minutes != null ? ` · ${r.minutes} min` : ""} · run {r.run_id} · code {r.code_version || "n/a"} · data {r.data_version || "n/a"}</p>
          <Rows rows={Object.entries(r.metrics).map(([k, v]) => [label(k), runValue(k, v)])}/>
          {!!Object.keys(r.judge_metrics).length && <p className="mt-3 text-xs text-muted">Judge scores (report only): {Object.entries(r.judge_metrics).map(([k, v]) => `${label(k)} ${pct(v)}`).join(" · ")}</p>}
        </div>
      </details>
    </li>)}</ul>
  </section>
}

// `label` is the data-classification mark (its lookup lives in App.tsx); `tester` adds Feedback review.
export function TelemetryWorkspace({ label, tester }: { label?: ReactNode, tester?: boolean }) {
  const [t, setT] = useState<T | null>(null)
  const [u, setU] = useState<Usage | null>(null)
  const [err, setErr] = useState<string[]>([])
  useEffect(() => {
    const fail = (e: unknown) => setErr(x => [...x, e instanceof Error ? e.message : String(e)])
    getTelemetry().then(setT, fail)
    getUsage().then(setU, fail)
  }, [])
  const b = u?.lanes.briefing ?? u?.lanes.forecast
  const reviewed = b ? Object.values(b.decisions).reduce((x, y) => x + y, 0) : 0
  const approved = b ? (b.decisions.signed_off ?? b.decisions.approved ?? b.decisions.approve ?? 0) : 0
  const rv = b?.review  // per brief, latest decision; the Forecast lane has none and keeps the event count
  const approvedTile: [string, string, string] = rv
    ? (rv.enough && rv.approved_pct != null
      ? ["Approved", `${Math.round(rv.approved_pct)}%`, `${rv.approved} of ${rv.briefs} briefs approved`]
      : ["Approved", rv.briefs ? (rv.label ?? "too few to rate").replace(/^./, c => c.toUpperCase()) : "–",
         rv.briefs ? `${rv.briefs} brief${rv.briefs === 1 ? "" : "s"} decided, ${rv.min_briefs} needed` : "nothing reviewed yet"])
    : ["Approved", reviewed ? `${Math.round((approved / reviewed) * 100)}%` : "–", reviewed ? `${approved} of ${reviewed} decisions` : "nothing reviewed yet"]
  const lead = t?.latest.find(r => !r.control)
  // The SUS of the first questionnaire and the UMUX-Lite SUS-equivalent of the second, weighted by responses
  const parts = [u?.sus && {n: u.sus.n, mean: u.sus.mean}, u?.umux && {n: u.umux.n, mean: u.umux.sus_equivalent_mean}].filter(Boolean) as {n: number, mean: number}[]
  const total = parts.reduce((a, x) => a + x.n, 0)
  const usability = total ? {n: total, mean: Math.round(parts.reduce((a, x) => a + x.n * x.mean, 0) / total * 10) / 10} : null
  const goldenBrief = t?.latest.find(r => !r.control && r.system === "briefing_scripted")?.metrics.latency_brief_p50
  return <div className="workspace-wide pa-stagger space-y-6 pb-12 pt-5 sm:pt-6">
    <header className="flex items-baseline justify-between gap-4"><h2 className="sr-only">Evaluation</h2>
      <p className="text-sm text-muted">How PharmAgentics is used, and how each version scored on the golden questions.</p>{label}</header>
    {err.map(e => <Notice key={e} tone="error" role="alert">{e}</Notice>)}
    {!t && !u && !err.length && <div className="pa-skeleton h-32 rounded-xl"/>}
    {u && b && <Figures items={[
      [u.lanes.briefing ? "Briefs requested" : "Explanations run", String(b.requests), u.since ? `since ${when(u.since)}` : "none yet"],
      approvedTile,
      ["Typical response (live use)", b.scripted_ms ? `${((b.scripted_ms.p50 ?? 0) / 1000).toFixed(1)} s` : "–", b.scripted_ms ? "scripted engine, median of live requests" : "no timed requests",
        goldenBrief != null && `golden set: ${goldenBrief.toFixed(1)} s a brief`],
      ["Usability (SUS scale)", usability ? String(usability.mean) : "–", usability ? `of 100, ${usability.n} response${usability.n === 1 ? "" : "s"}` : "no responses yet"],
    ]}/>}
    {u && <InUse u={u}/>}
    {t && <>
      <Heading title="Golden-set scores" note={<>{t.exported ? `Exported ${when(t.exported)}. ` : ""}{t.note}{lead ? ` Latest: ${name(lead)}, ${when(lead.started)}.` : ""}{t.targets ? ` Targets: key facts found ${pct(t.targets.key_fact_recall ?? 0)}, findings found ${pct(t.targets.finding_recall ?? 0)}, over all golden questions together.` : ""} Select a row for every score.</>}/>
      <Scores runs={t.latest.filter(r => !r.control)} targets={t.targets}/>
      {t.latest.some(r => r.control) && <><Heading title="Controls"/><Scores runs={t.latest.filter(r => r.control)} targets={t.targets}/></>}
      {!!t.cases?.systems.length && <PerCase tables={t.cases.systems} targets={t.cases.targets}/>}
      {!!t.runs.length && <details className={`${PANEL} p-5`}><summary className="cursor-pointer text-sm font-semibold">All runs ({t.runs.length})</summary>
        <div className="relative mt-3 overflow-x-auto"><table className="w-full text-left text-sm">
          <thead className="text-xs text-muted"><tr><th className="py-1 pr-4 font-medium">Date</th><th className="pr-4 font-medium">System</th><th className="pr-4 font-medium">Lane</th><th className="pr-4 font-medium">Key facts found</th><th className="pr-4 font-medium">Findings found</th><th className="pr-4 font-medium">Number recall</th><th className="font-medium">Claims reconcile</th></tr></thead>
          <tbody>{t.runs.map(r => <tr key={r.run_id} className="border-t border-rule"><td className="py-1 pr-4 tabular-nums">{when(r.started)}</td><td className="pr-4">{name(r)}</td><td className="pr-4">{LANES[r.lane] ?? r.lane}</td>
            <td className="pr-4 tabular-nums">{keyFacts(r.metrics) != null ? pct(keyFacts(r.metrics)) : "–"}</td><td className="pr-4 tabular-nums">{findings(r.metrics) != null ? pct(findings(r.metrics)) : "–"}</td>
            <td className="pr-4 tabular-nums">{r.metrics.golden_number_recall != null ? pct(r.metrics.golden_number_recall) : "–"}</td><td className="tabular-nums">{r.metrics.claims_reconcile != null ? pct(r.metrics.claims_reconcile) : "–"}</td></tr>)}</tbody>
        </table></div></details>}
    </>}
    <ForecastDriverRecovery/>
    {tester && <><Heading title="Feedback review" note="Lessons and cases proposed from answer votes and saved threads. Approving one queues it; it reaches the golden set through a reviewed pull request."/><FeedbackReview/><Heading title="Questionnaire responses"/><FeedbackResponses/></>}
  </div>
}
