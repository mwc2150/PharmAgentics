import { Fragment, useEffect, useState } from "react"
import { getAgentsInfo, type AgentCard, type AgentComparison, type AgentsInfo, type CompareRow } from "./agent/briefingApi"
import { KIND_NAME, KIND_STYLE } from "./Timeline"
import { Notice, modelName } from "./agent/primitives"
import { fmtDate } from "./userSettings"

// brief-009 FR-006: how the briefing is made. The flow from question to brief, the four actors the architecture names
// (Manager, Data Forensics, Driver Investigator, and the Writer, which is an LLM step and not an agent), what each
// does, which tools it has and where its output lands in the memo, and what the agent team adds over the scripted
// engine. Prompts arrive only for analyst roles; the server never sends them to leadership, so this page cannot show them.

const PANEL = "rounded-xl border border-rule bg-sheet"
// An outlined word, never a filled pill (DESIGN.md).
const chip = "rounded-md border px-2 py-0.5 text-xs font-medium"
const when = fmtDate

function show(row: CompareRow, v: number | null): string {
  if (v === null || v === undefined) return "—"
  if (row.unit === "share") return `${Math.round(v * 100)}%`
  if (row.unit === "seconds") return v >= 100 ? `${Math.round(v)} s` : `${v.toFixed(1)} s`
  return v.toFixed(1)
}

function Heading({ title, note }: { title: string, note?: string }) {
  return <div className="pt-2"><h3 className="text-xs uppercase tracking-[0.06em] text-muted">{title}</h3>{note && <p className="mt-1 text-sm text-muted">{note}</p>}</div>
}

function Flow({ steps }: { steps: AgentsInfo["flow"] }) {
  return <ol className={`${PANEL} divide-y divide-rule`}>
    {steps.map(s => <li key={s.n} className="grid gap-x-4 gap-y-1 px-5 py-4 sm:grid-cols-[28px_190px_1fr]">
      <span className="font-mono text-xs text-muted">{s.n}</span>
      <span className="flex flex-wrap items-start gap-1.5"><span className={`${chip} ${KIND_STYLE[s.kind]}`}>{s.actor}</span></span>
      <div><p className="text-sm font-medium">{s.title}</p><p className="mt-0.5 text-sm text-muted">{s.note}</p></div>
    </li>)}
  </ol>
}

function Actor({ a, promptsShown }: { a: AgentCard, promptsShown: boolean }) {
  return <article className={`${PANEL} p-5`}>
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h4 className="text-base font-semibold">{a.name}</h4>
      <span className={`${chip} ${KIND_STYLE[a.kind]}`}>{a.kind === "agent" ? KIND_NAME.agent : "LLM step, not an agent"}</span>
    </div>
    <p className="mt-2 text-sm">{a.job}</p>
    <dl className="mt-4 space-y-3 text-sm">
      <div><dt className="text-xs uppercase tracking-[0.06em] text-muted">Steps in a brief</dt><dd className="mt-1">{a.steps.join(" · ")}</dd></div>
      <div><dt className="text-xs uppercase tracking-[0.06em] text-muted">Tools</dt>
        <dd className="mt-1">{a.tools.length
          ? <ul className="space-y-1">{a.tools.map(t => <li key={t.name} className="flex flex-wrap items-baseline gap-x-2"><span className="rounded border border-rule bg-paper px-1.5 py-0.5 font-mono text-[11px] text-muted">{t.name}</span><span className="text-muted">{t.does}</span></li>)}</ul>
          : <span className="text-muted">{a.tools_note ?? "None."}</span>}</dd></div>
      <div><dt className="text-xs uppercase tracking-[0.06em] text-muted">Where its output lands</dt><dd className="mt-1">{a.lands}</dd></div>
    </dl>
    {a.prompts?.length ? <div className="mt-4 border-t border-rule pt-3">
      <h5 className="text-xs uppercase tracking-[0.06em] text-muted">Prompts, word for word</h5>
      <div className="mt-2 space-y-2">{a.prompts.map(p => <details key={p.id} className="rounded-lg border border-rule bg-paper/50">
        <summary className="flex cursor-pointer flex-wrap items-baseline gap-x-3 gap-y-0.5 px-3 py-2 text-sm font-medium">{p.step}<span className="font-mono text-[11px] font-normal text-muted">{p.ref}</span></summary>
        <pre tabIndex={0} className="max-h-[28rem] overflow-auto whitespace-pre-wrap break-words border-t border-rule px-3 py-3 font-mono text-xs leading-relaxed">{p.text}</pre>
      </details>)}</div>
    </div> : !promptsShown && <p className="mt-4 border-t border-rule pt-3 text-xs text-muted">The prompts are shown to the Commercial Analyst.</p>}
  </article>
}

function Comparison({ c }: { c: AgentComparison }) {
  if (!c.available) return <div className={`${PANEL} p-5 text-sm text-muted`}>{c.note}</div>
  const groups = [...new Set(c.rows.map(r => r.group))]
  return <div className={`${PANEL} overflow-x-auto`}>
    <table className="w-full min-w-[30rem] text-sm">
      <caption className="sr-only">Scripted engine against agent team on the same golden questions</caption>
      <thead><tr className="border-b border-rule text-left text-xs text-muted">
        <th scope="col" className="px-5 py-3 font-medium">Measure</th>
        <th scope="col" className="px-3 py-3 text-right font-medium">Scripted<span className="block font-normal">{c.scripted ? `${when(c.scripted.started)} · ${c.scripted.cases} questions` : ""}</span></th>
        <th scope="col" className="px-5 py-3 text-right font-medium">Agent team<span className="block font-normal">{c.agent ? `${when(c.agent.started)} · ${c.agent.cases} questions` : ""}</span></th>
      </tr></thead>
      <tbody>{groups.map(g => <Fragment key={g}>
        <tr className="border-b border-rule bg-paper/50"><th colSpan={3} scope="colgroup" className="px-5 py-1.5 text-left text-xs font-medium uppercase tracking-[0.06em] text-muted">{g}</th></tr>
        {c.rows.filter(r => r.group === g).map(r => <tr key={r.label} className="border-b border-rule last:border-0">
          <th scope="row" className="px-5 py-2 text-left font-normal">{r.label}{r.note && <span className="block text-xs text-muted">{r.note}</span>}</th>
          <td className="px-3 py-2 text-right tabular-nums">{show(r, r.scripted)}</td>
          <td className="px-5 py-2 text-right tabular-nums">{show(r, r.agent)}</td>
        </tr>)}
      </Fragment>)}</tbody>
    </table>
    <p className="border-t border-rule px-5 py-3 text-xs text-muted">{c.note} The full scores are on the Evaluation page.</p>
  </div>
}

function modelLine(m: AgentsInfo["model"]) {
  if (!m.spec) return <>The agent team runs on a model that is set when it is switched on. No model is set in this app now.</>
  const haiku = /haiku/i.test(m.spec)
  return <>{haiku ? "Claude Haiku, a small and fast model from Anthropic, drives the agent team: " : "The agent team runs on "}<span>{modelName(m.spec)}</span>.
    {" "}The Manager, Data Forensics, Driver Investigator and Writer all call the same model.{m.source === "evaluation" ? " (Read from the latest evaluation run; this app is not running the team itself.)" : ""}</>
}

export function HowItWorks() {
  const [info, setInfo] = useState<AgentsInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let live = true
    setError(null)
    getAgentsInfo().then(v => { if (live) setInfo(v) }).catch(e => { if (live) setError(e instanceof Error ? e.message : String(e)) })
    return () => { live = false }
  }, [attempt])
  if (error) return <Notice tone="error" role="alert">{error}<button type="button" className="ml-2 underline" onClick={() => setAttempt(n => n + 1)}>Try again</button></Notice>
  if (!info) return <div role="status" className={`${PANEL} space-y-3 p-6`}><span className="sr-only">Loading how it works…</span><div className="pa-skeleton h-5 w-2/5"/><div className="pa-skeleton h-3 w-full"/><div className="pa-skeleton h-3 w-4/5"/></div>
  const lim = info.limits
  return <div className="space-y-5">
    <section className={`${PANEL} p-6`}>
      <h2 className="text-xl">How the briefing is made</h2>
      <p className="mt-2 max-w-[68ch] text-sm">{modelLine(info.model)}</p>
      <p className="mt-2 max-w-[68ch] text-sm text-muted">No digit in a brief comes from a model. Code fills every number from a governed query and checks every sentence. The agents choose what to check and in what order; the verdicts and confidence come from code.</p>
    </section>

    <Heading title="From question to brief"/>
    <Flow steps={info.flow}/>

    <Heading title="Two engines" note="You choose one when you generate a briefing."/>
    <div className="grid gap-4 sm:grid-cols-2">
      <section className={`${PANEL} p-5`}><h4 className="text-base font-semibold">Scripted</h4><p className="mt-2 text-sm text-muted">{info.engines.scripted}</p></section>
      <section className={`${PANEL} p-5`}><h4 className="text-base font-semibold">Agent team <span className="text-xs font-normal text-muted">· experimental</span></h4>
        <p className="mt-2 text-sm text-muted">{info.engines.agent}</p>
        {lim && <p className="mt-2 text-xs text-muted">Caps: at most {lim.rounds_a_story} rounds and {lim.seconds_a_story} seconds on a story, and {lim.seconds_a_run} seconds on a run. A story left unfinished closes as unresolved.</p>}</section>
    </div>

    <Heading title="The four actors" note="Three agents and one writing step. Each card shows its job, its tools and where its output lands in the memo."/>
    <div className="grid gap-4 lg:grid-cols-2">{info.actors.map(a => <Actor key={a.id} a={a} promptsShown={info.prompts_shown}/>)}</div>

    <Heading title="What the agent team adds" note="The latest scripted and agent runs, scored on the same golden questions."/>
    <Comparison c={info.comparison}/>
  </div>
}
