// brief-003: the weekly brief as a memo. Sections, charts and the data behind them come from the server;
// nothing here computes a number. Charts are plain SVG drawn from the points the server returns.
import { useState, type ReactNode } from "react"
import { DefinitionWords } from "./BriefDefinition"
import { longDates } from "./agent/primitives"
import { fmtShortDay } from "./userSettings"
import { BudgetNote, PromotionPanel } from "./Promotion"
import type { BriefDefinition, ChartPoint, ChartSpec, Claim, DataTable, Evidence, KpiTile, MemoSection, Span, StoryCardBlock, TerritoryRow, TerritoryTable } from "./agent/briefingApi"

const COLORS = ["var(--color-primary)", "var(--color-human)"]
const PANEL_COLOR = "var(--color-amber)"

function Cited({text, spans, claims, onOpen}: {text: string, spans?: Span[], claims?: Claim[], onOpen?: (evidenceId: string) => void}) {
  const sorted = [...(spans ?? [])].sort((a, b) => a.start - b.start)
  if (!sorted.length || !claims || !onOpen) return <>{longDates(text)}</>
  const parts: ReactNode[] = []
  let pos = 0
  sorted.forEach((sp, i) => {
    const claim = claims[sp.claim]
    if (!claim || sp.start < pos || text.slice(sp.start, sp.end) !== claim.value) return
    parts.push(longDates(text.slice(pos, sp.start)))
    parts.push(<button key={i} type="button" onClick={() => onOpen(claim.evidence_id)} title={`Source ${claim.evidence_id}: open the query behind ${claim.value}`}
      aria-label={`${claim.value}, evidence ${claim.evidence_id.replace(/^e/, "")}`}
      className="pa-cite rounded-sm font-medium underline decoration-primaryink/40 decoration-dotted underline-offset-4 hover:bg-primarybg focus-visible:bg-primarybg">{claim.value}<span className="sr-only"> </span><sup aria-hidden="true" className="pa-fn ml-px select-none font-mono text-[10px] font-normal text-primaryink">{claim.evidence_id.replace(/^e/, "")}</sup></button>)
    pos = sp.end
  })
  parts.push(longDates(text.slice(pos)))
  return <>{parts}</>
}

const shortWeek = fmtShortDay

function fmt(v: number, unit = "count"): string {
  if (unit === "rate") return v.toFixed(2)
  if (unit === "percent") return `${v.toFixed(1)}%`
  return Math.round(v).toLocaleString()
}

const W = 640, H = 200, PAD = {l: 48, r: 12, t: 12, b: 26}

function scale(values: number[], lo?: number, hi?: number) {
  const vs = values.concat(lo ?? [], hi ?? [])
  let min = Math.min(...vs), max = Math.max(...vs)
  if (min === max) { min -= 1; max += 1 }
  const pad = (max - min) * 0.08
  return {min: min - pad, max: max + pad, y: (v: number) => PAD.t + (H - PAD.t - PAD.b) * (1 - (v - (min - pad)) / ((max + pad) - (min - pad)))}
}

function LineChart({weeks, series, band, unit = "count", label}: {weeks: string[], series: {name: string, points: ChartPoint[], color: string, dash?: string}[], band?: ChartSpec["band"], unit?: string, label: string}) {
  const values = series.flatMap(s => s.points.map(p => p.value).filter((v): v is number => v !== null))
  if (!values.length) return null
  const sc = scale(values, band?.low, band?.high)
  const x = (w: string) => PAD.l + (W - PAD.l - PAD.r) * (weeks.length < 2 ? 0.5 : weeks.indexOf(w) / (weeks.length - 1))
  const ticks = [weeks[0], weeks[Math.floor((weeks.length - 1) / 2)], weeks[weeks.length - 1]]
  return <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={label}>
    {band && <g><rect x={PAD.l} width={W - PAD.l - PAD.r} y={sc.y(band.high)} height={Math.max(1, sc.y(band.low) - sc.y(band.high))} fill="var(--color-primary)" opacity={0.1}/>
      <text x={W - PAD.r} y={sc.y(band.high) - 3} textAnchor="end" className="fill-muted text-[10px]">baseline band</text></g>}
    {[sc.min, (sc.min + sc.max) / 2, sc.max].map((v, i) => <g key={i}>
      <line x1={PAD.l} x2={W - PAD.r} y1={sc.y(v)} y2={sc.y(v)} stroke="var(--color-rule)"/>
      <text x={PAD.l - 6} y={sc.y(v) + 3} textAnchor="end" className="fill-muted text-[10px]">{fmt(v, unit)}</text></g>)}
    {ticks.map((w, i) => <text key={i} x={x(w)} y={H - 8} textAnchor="middle" className="fill-muted text-[10px]">{shortWeek(w)}</text>)}
    {series.map((s, si) => {
      const pts = s.points.filter(p => p.value !== null)
      return <g key={si}>
        <polyline fill="none" stroke={s.color} strokeWidth={2} strokeDasharray={s.dash} points={pts.map(p => `${x(p.week)},${sc.y(p.value as number)}`).join(" ")}/>
        {pts.map((p, i) => {
          const assumed = p.basis && p.basis !== "observed"
          return <circle key={i} cx={x(p.week)} cy={sc.y(p.value as number)} r={assumed || p.restated ? 4.5 : 3}
            fill={assumed ? "var(--color-sheet)" : s.color} stroke={s.color} strokeWidth={1.5} strokeDasharray={p.restated ? "2 2" : undefined}>
            <title>{`${s.name}, week of ${p.week}: ${fmt(p.value as number, unit)}${assumed ? ` (${p.basis}, an assumption)` : ""}${p.restated ? " (restated)" : ""}`}</title>
          </circle>
        })}
      </g>
    })}
  </svg>
}

function Legend({items}: {items: {label: string, color: string, hollow?: boolean, dash?: string}[]}) {
  return <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
    {items.map((it, i) => <span key={i} className="inline-flex items-center gap-1.5">
      <svg viewBox={it.dash ? "0 0 24 10" : "0 0 10 10"} className={it.dash ? "h-2.5 w-6" : "h-2.5 w-2.5"} aria-hidden="true">{it.dash && <line x1="0" x2="24" y1="5" y2="5" stroke={it.color} strokeWidth="2" strokeDasharray={it.dash}/>}<circle cx={it.dash ? 12 : 5} cy="5" r="4" fill={it.hollow ? "none" : it.color} stroke={it.color} strokeWidth="1.5"/></svg>{it.label}</span>)}
  </div>
}

function CoverageStrip({chart}: {chart: ChartSpec}) {
  const rows = chart.rows ?? []
  const cell = 14, left = 108, top = 4
  const width = left + chart.weeks.length * cell + 4, height = top + rows.length * cell + 18
  return <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full max-w-[520px]" role="img" aria-label="Feed coverage by territory and week">
    {rows.map((r, ri) => <g key={r.territory}>
      <text x={left - 6} y={top + ri * cell + 10} textAnchor="end" className="fill-muted text-[9px]">{r.territory}</text>
      {r.cells.map(c => {
        const cx = left + chart.weeks.indexOf(c.week) * cell, cy = top + ri * cell
        return <g key={c.week}>
          <rect x={cx + 1} y={cy + 1} width={cell - 2} height={cell - 2} rx={2}
            fill={c.basis === "observed" ? "var(--color-primary)" : "var(--color-sheet)"} opacity={c.basis === "observed" ? 0.35 : 1}
            stroke={c.basis === "observed" ? "none" : "var(--color-amber)"} strokeWidth={1.2}/>
          {c.basis === "estimated" && <path d={`M${cx + 3} ${cy + 3}L${cx + cell - 3} ${cy + cell - 3}M${cx + cell - 3} ${cy + 3}L${cx + 3} ${cy + cell - 3}`} stroke="var(--color-amber)" strokeWidth={1.2}/>}
          {c.restated && <circle cx={cx + cell / 2} cy={cy + cell / 2} r={cell / 2 - 0.5} fill="none" stroke="var(--color-human)" strokeWidth={1.2}/>}
          <title>{`${r.territory}, week of ${c.week}: ${c.basis}${c.basis !== "observed" ? ", an assumption" : ""}${c.restated ? ", restated" : ""}`}</title>
        </g>
      })}
    </g>)}
    {[chart.weeks[0], chart.weeks[chart.weeks.length - 1]].map((w, i) => <text key={i} x={left + (i ? chart.weeks.length - 1 : 0) * cell + cell / 2} y={height - 4} textAnchor="middle" className="fill-muted text-[9px]">{shortWeek(w)}</text>)}
  </svg>
}

function ChartBlock({chart, onOpen, claims, explanationSpans, bare = false}: {chart: ChartSpec, onOpen?: (id: string) => void, claims?: Claim[], explanationSpans?: Span[], bare?: boolean}) {
  // A second line is dashed as well as lavender, so the two never differ by colour alone (WCAG 1.4.1).
  const series = (chart.series ?? []).map((s, i) => ({...s, color: COLORS[i % COLORS.length], dash: i % COLORS.length ? "7 4" : undefined}))
  return <figure className={`break-inside-avoid ${bare ? "my-3" : "my-4 rounded-xl border border-rule bg-paper/40 p-4"}`}>
    {chart.kind === "coverage" ? <CoverageStrip chart={chart}/> : <>
      <LineChart weeks={chart.weeks} series={series} band={chart.band} unit={chart.kind === "share" ? "percent" : "count"} label={chart.caption}/>
      <Legend items={series.map((s): {label: string, color: string, hollow?: boolean, dash?: string} => ({label: s.name, color: s.color, dash: s.dash})).concat(series.some(s => s.points.some(p => p.basis && p.basis !== "observed")) ? [{label: "projected or estimated (an assumption)", color: "var(--color-muted)", hollow: true, dash: undefined}] : [])}/>
      {chart.panel && chart.panel.points.length > 0 && <div className="mt-3 border-t border-rule pt-3">
        <p className="mb-1 text-[11px] uppercase tracking-wider text-muted">{chart.panel.name}</p>
        <LineChart weeks={chart.weeks} series={[{name: chart.panel.name, points: chart.panel.points, color: PANEL_COLOR}]} unit={chart.panel.unit} label={chart.panel.name}/>
      </div>}
    </>}
    <figcaption className="mt-3 text-[13px] leading-relaxed text-muted">{longDates(chart.caption)}</figcaption>
    <p className="mt-1 text-[14px] leading-relaxed text-ink"><Cited text={chart.explanation} spans={explanationSpans} claims={claims} onOpen={onOpen}/></p>
  </figure>
}

function csv(table: DataTable): string {
  const cell = (v: unknown) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s }
  return [table.columns.map(cell).join(","), ...table.rows.map(r => r.map(cell).join(","))].join("\n")
}

function download(name: string, table: DataTable) {
  const url = URL.createObjectURL(new Blob([csv(table)], {type: "text/csv"}))
  const a = document.createElement("a")
  a.href = url; a.download = name; a.click()
  URL.revokeObjectURL(url)
}

function TableView({table, name}: {table: DataTable, name: string}) {
  const [sql, setSql] = useState(false)
  // A table whose rows each carry their own query (the claims) shows that column only on "Show query"; the CSV keeps it.
  const perRow = table.columns.includes("query")
  const shown = table.columns.map((_, j) => j).filter(j => sql || table.columns[j] !== "query")
  return <div className="rounded-lg border border-rule">
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule px-3 py-2 text-xs">
      <span className="font-mono text-xs font-medium text-ink">{table.evidence_id}</span>
      <span className="flex gap-3">
        <button type="button" className="text-primaryink hover:underline" onClick={() => setSql(!sql)} aria-expanded={sql}>{sql ? "Hide query" : "Show query"}</button>
        <button type="button" className="text-primaryink hover:underline" onClick={() => download(name, table)}>Download CSV</button>
      </span>
    </div>
    {sql && !perRow && <pre className="overflow-x-auto whitespace-pre-wrap break-all border-b border-rule bg-paper p-3 font-mono text-xs leading-relaxed">{table.query}</pre>}
    <div className="max-h-64 overflow-auto" tabIndex={0} role="region" aria-label={`Data table ${table.evidence_id}`}>
      <table className="w-full text-left font-sans text-xs tabular-nums">
        <thead className="sticky top-0 bg-sheet text-muted"><tr>{shown.map(j => <th key={j} className="px-3 py-2 font-medium">{table.columns[j]}</th>)}</tr></thead>
        <tbody>{table.rows.map((r, i) => <tr key={i} className="border-t border-rule align-top">{shown.map(j => <td key={j} className={`px-3 py-1.5 ${table.columns[j] === "query" ? "whitespace-pre-wrap break-all font-mono text-[11px] text-muted" : ""}`}>{r[j] === null ? "" : String(r[j])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  </div>
}

function DataBehind({section, claims, evidence, briefId}: {section: MemoSection, claims: Claim[], evidence: Evidence[], briefId: string}) {
  const tables = [section.chart?.table, section.chart?.panel?.table].filter((t): t is DataTable => !!t)
  const used = (section.claims ?? []).map(i => claims[i]).filter((c): c is Claim => !!c)
  if (!tables.length && !used.length) return null
  const byId = new Map(evidence.map(e => [e.id, e]))
  const claimTable: DataTable | null = used.length ? {
    evidence_id: "Numbers in this section", query: "",
    columns: ["value", "evidence_id", "tool", "query"],
    rows: used.map(c => [c.value, c.evidence_id, byId.get(c.evidence_id)?.tool ?? "", byId.get(c.evidence_id)?.query ?? ""]),
  } : null
  return <details className="pa-fold mt-3 rounded-lg bg-paper/60 px-4 py-3 text-sm">
    <summary className="cursor-pointer text-[13px] font-medium text-primaryink">Data behind this section ({used.length} number{used.length === 1 ? "" : "s"}{tables.length ? `, ${tables.length} chart table${tables.length > 1 ? "s" : ""}` : ""})</summary>
    <div className="mt-3 space-y-3">
      {claimTable && <TableView table={claimTable} name={`brief-${briefId}-section-${section.number}-claims.csv`}/>}
      {tables.map(t => <TableView key={t.evidence_id} table={t} name={`brief-${briefId}-section-${section.number}-${t.evidence_id}.csv`}/>)}
    </div>
  </details>
}

// brief-008: paragraphs and blocks. Every string below is the server's, shown as given; spans are cut to the
// piece of text they sit in, and Cited drops any span whose text no longer matches its claim.
type Chunk = {start: number, end: number}
const BULLET = /^\s*[-•*]\s+/

function chunks(text: string): Chunk[] {
  const out: Chunk[] = []
  let pos = 0, cur: Chunk | null = null, curBullet = false
  for (const line of text.split("\n")) {
    const at = pos
    pos += line.length + 1
    if (!line.trim()) { if (cur) out.push(cur); cur = null; continue }
    // a run of "- " lines is its own block, even with no blank line before or after it
    if (cur && BULLET.test(line) !== curBullet) { out.push(cur); cur = null }
    if (cur) cur.end = at + line.length
    else { cur = {start: at, end: at + line.length}; curBullet = BULLET.test(line) }
  }
  if (cur) out.push(cur)
  return out
}

function within(spans: Span[] | undefined, start: number, end: number): Span[] {
  return (spans ?? []).filter(sp => sp.start >= start && sp.end <= end).map(sp => ({...sp, start: sp.start - start, end: sp.end - start}))
}

const PROSE = "pa-prose max-w-[68ch] break-words font-sans text-[16px] leading-[1.65] text-ink"

// `flow` joins the lines of a run into one paragraph (brief-008 FR-018): code writes §1 and §2 a sentence to a line,
// and a reader takes them as prose. A newline becomes a space, one character for one, so the spans still fit.
function Paragraphs({text, spans, claims, onOpen, flow}: {text: string, spans?: Span[], claims?: Claim[], onOpen?: (evidenceId: string) => void, flow?: boolean}) {
  return <>{chunks(text).map((c, i) => {
    const raw = text.slice(c.start, c.end)
    const lines = raw.split("\n")
    if (lines.every(l => BULLET.test(l))) {
      let off = 0
      return <ul key={i} className={`${PROSE} mt-3 list-disc space-y-1 pl-5 first:mt-2`}>{lines.map((l, k) => {
        const m = BULLET.exec(l)![0].length, from = c.start + off + m, to = c.start + off + l.length
        off += l.length + 1
        return <li key={k}><Cited text={l.slice(m)} spans={within(spans, from, to)} claims={claims} onOpen={onOpen}/></li>
      })}</ul>
    }
    return <p key={i} className={`${PROSE} mt-3 ${flow ? "" : "whitespace-pre-line"} first:mt-2`}><Cited text={flow ? raw.replace(/\n/g, " ") : raw} spans={within(spans, c.start, c.end)} claims={claims} onOpen={onOpen}/></p>
  })}</>
}

const DIRECTION = {
  up: {word: "up", color: "text-primaryink", d: "M12 5l7 9H5z"},
  down: {word: "down", color: "text-neg", d: "M12 19l-7-9h14z"},
  flat: {word: "unchanged", color: "text-muted", d: "M5 11h14v2H5z"},
} as const

function KpiStrip({kpis, claims, onOpen}: {kpis: KpiTile[], claims?: Claim[], onOpen?: (evidenceId: string) => void}) {
  return <dl aria-label="Key figures" className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
    {kpis.map((k, i) => {
      const dir = k.direction ? DIRECTION[k.direction] : null
      return <div key={i} className="break-inside-avoid rounded-lg border border-rule bg-sheet/60 px-3.5 py-3">
        <dt className="font-sans text-[11px] font-medium uppercase tracking-wider text-muted">{k.label}</dt>
        <dd className="pa-kpi-value mt-1 flex items-center gap-1.5 font-display text-[28px] font-bold leading-none tabular-nums text-ink">
          <span><Cited text={k.value} spans={k.value_citation} claims={claims} onOpen={onOpen}/></span>
          {dir && <><svg viewBox="0 0 24 24" className={`h-4 w-4 shrink-0 ${dir.color}`} fill="currentColor" aria-hidden="true"><path d={dir.d}/></svg><span className="sr-only">, {dir.word}</span></>}
        </dd>
        {k.detail && <dd className="mt-1.5 font-sans text-[12px] leading-snug text-muted">{longDates(k.detail)}</dd>}
      </div>
    })}
  </dl>
}

function BasisLabel({row, text}: {row: TerritoryRow, text: string}) {
  const assumed = row.basis === "projected" || row.basis === "estimated"
  return <span className={`text-[11px] ${assumed ? "text-amber" : "text-muted"}`}>{text}</span>
}

function TerritoryTableView({table, claims, onOpen}: {table: TerritoryTable, claims?: Claim[], onOpen?: (evidenceId: string) => void}) {
  const basisAt = table.columns.findIndex(c => c.trim().toLowerCase() === "basis")
  const lastData = basisAt > 0 ? basisAt - 1 : table.columns.length - 1
  const align = (j: number) => j === 0 || j === basisAt ? "text-left" : "text-right"
  return <div className="my-4 overflow-x-auto" tabIndex={0} role="region" aria-label="Territory figures">
    <table className="w-full border-collapse font-sans text-[13px] tabular-nums">
      <caption className="sr-only">Territory figures{table.note ? `. ${longDates(table.note)}` : ""}</caption>
      <thead><tr className="border-b border-rule">{table.columns.map((c, j) =>
        <th key={j} scope="col" className={`px-1.5 sm:px-2.5 py-1.5 text-[11px] font-medium text-muted ${align(j)}`}>{c}</th>)}</tr></thead>
      <tbody>{table.rows.map((r, i) => {
        const withheld = r.basis === "withheld"
        return <tr key={i} className="break-inside-avoid border-b border-rule/60 align-baseline">
          {table.columns.map((_, j) => {
            const cell = r.cells[j] ?? ""
            if (j === 0) return <th key={j} scope="row" className="px-1.5 sm:px-2.5 py-1.5 text-left font-medium text-ink"><Cited text={cell} spans={r.cell_citations?.[j]} claims={claims} onOpen={onOpen}/></th>
            if (withheld && j >= 1 && j <= lastData) return j === 1 ? <td key={j} colSpan={lastData} className="px-1.5 sm:px-2.5 py-1.5 text-right italic text-muted">withheld</td> : null
            if (j === basisAt) return <td key={j} className="px-1.5 sm:px-2.5 py-1.5 text-left">{withheld ? <span aria-hidden="true" className="text-muted">—</span> : <BasisLabel row={r} text={cell || r.basis}/>}</td>
            return <td key={j} className="px-1.5 sm:px-2.5 py-1.5 text-right text-ink"><Cited text={cell} spans={r.cell_citations?.[j]} claims={claims} onOpen={onOpen}/></td>
          })}
        </tr>
      })}</tbody>
    </table>
    {table.note && <p className="mt-2 font-sans text-[12px] leading-snug text-muted">{longDates(table.note)}</p>}
  </div>
}

const CONFIDENCE = {
  High: "bg-okbg text-ok",
  Medium: "bg-paper text-ink",
  Low: "bg-warnbg text-neg",
} as const

function CardHead({card, claims, onOpen}: {card: StoryCardBlock, claims?: Claim[], onOpen?: (evidenceId: string) => void}) {
  return <>
    <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
      <p className="max-w-[56ch] font-sans text-[16px] font-semibold leading-snug text-ink"><Cited text={card.headline} spans={card.headline_citations} claims={claims} onOpen={onOpen}/></p>
      <span className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 font-sans text-[11px] font-medium ${CONFIDENCE[card.confidence] ?? "bg-warnbg text-muted"}`}>{card.confidence} confidence</span>
    </div>
    {card.drivers_checked.length > 0 && <p className="mt-1 font-sans text-[12px] text-muted">Checked: {longDates(card.drivers_checked.join(", "))}</p>}
  </>
}

function Detail({text, spans, claims, onOpen}: {text: string, spans?: Span[], claims?: Claim[], onOpen?: (evidenceId: string) => void}) {
  const [open, setOpen] = useState(false)
  return <details className="pa-fold mt-3 rounded-lg bg-paper/60 px-4 py-3" onToggle={e => setOpen(e.currentTarget.open)}>
    <summary className="cursor-pointer font-sans text-[13px] font-medium text-primaryink">{open ? "Hide detail" : "Show detail"}</summary>
    <div className="mt-2"><Paragraphs text={text} spans={spans} claims={claims} onOpen={onOpen}/></div>
  </details>
}

// The memo: numbered sections in order. Analysts get inline citations and the data behind each section;
// leaders get the server's cut (no claims, tables or queries) through the same component.
// brief-010 FR-000b: `definition` is what the brief was built under; it is stated in words in the Assumptions block (§6),
// in both views. A brief made before brief-010 has none, and nothing extra shows.
export function Memo({sections, briefId, claims, evidence, onOpen, onAsk, definition, labelWeek, budgetNote}: {sections: MemoSection[], briefId: string, claims?: Claim[], evidence?: Evidence[], onOpen?: (evidenceId: string) => void, onAsk?: (chip: {number: string, title: string}) => void, definition?: BriefDefinition | null, labelWeek?: (iso: string) => string, budgetNote?: string}) {
  // A brief stored before brief-008 has none of the new fields and renders as it always did: each section's text
  // as one pre-wrapped block. A brief with any of them reads as paragraphs throughout. Only analysts (who get the
  // claims) can unfold `detail`; the leader cut never carries it.
  const modern = sections.some(s => s.kpis || s.territory_table || s.card || s.detail)
  const analyst = !!claims
  const text = (s: MemoSection) => !s.text ? null : modern
    ? <Paragraphs text={s.text} spans={s.text_citations} claims={claims} onOpen={onOpen} flow={s.number === "1" || s.number === "2"}/>
    : <div className="mt-2 max-w-[68ch] whitespace-pre-wrap break-words font-sans text-[16px] leading-[1.65] text-ink"><Cited text={s.text} spans={s.text_citations} claims={claims} onOpen={onOpen}/></div>
  const rest = (s: MemoSection) => <>
    {s.prose && <p className="mt-2 max-w-[68ch] font-sans text-[16px] italic leading-[1.65] text-ink"><Cited text={s.prose} spans={s.prose_citations} claims={claims} onOpen={onOpen}/></p>}
    {s.chart && <ChartBlock chart={s.chart} claims={claims} onOpen={onOpen} explanationSpans={s.chart.explanation_citations} bare={!!s.card}/>}
    {analyst && s.detail && <Detail text={s.detail} spans={s.detail_citations} claims={claims} onOpen={onOpen}/>}
    {claims && evidence && <DataBehind section={s} claims={claims} evidence={evidence} briefId={briefId}/>}
  </>
  // A section with subsections (§3 and its stories) shows its own lines (left out, considered and dropped) after
  // them, in the order the memo's text gives them.
  const body = (s: MemoSection) => s.card
    ? <div className="pa-card mt-2 break-inside-avoid-page rounded-xl border border-rule bg-sheet/40 p-4 sm:p-5">
        <CardHead card={s.card} claims={claims} onOpen={onOpen}/>
        {text(s)}{rest(s)}
        {s.promotion && <PromotionPanel promotion={s.promotion} id={`memo-${briefId}-${s.number}-promotion`}/>}
      </div>
    : <>
        {s.kpis && s.kpis.length > 0 && <KpiStrip kpis={s.kpis} claims={claims} onOpen={onOpen}/>}
        {text(s)}
        {s.territory_table && <TerritoryTableView table={s.territory_table} claims={claims} onOpen={onOpen}/>}
        {rest(s)}
      </>
  // The page's outline is h1 (the workspace), h2 (the brief), h3 (a section), h4 (a subsection).
  const heading = (s: MemoSection, sub: boolean) => { const Tag = sub ? "h4" : "h3"; return <div className="flex items-baseline justify-between gap-3">
    <Tag id={`memo-${briefId}-${s.number}`} className={`scroll-mt-24 break-after-avoid ${sub ? "text-base font-semibold" : "text-xl font-bold leading-[1.5]"}`}>
      <span className="mr-1 font-mono text-sm text-muted">§{s.number}</span>{" "}{sub ? s.title : <span className="pa-mark">{s.title}</span>}</Tag>
    {onAsk && <button type="button" onClick={() => onAsk({number: s.number, title: s.title})} aria-label={`Ask about this: section ${s.number}, ${s.title}`} className="pa-noprint shrink-0 text-xs text-primaryink hover:underline">Ask about this</button>}
  </div> }
  // The Assumptions block lives in §6; a memo without a §6 shows the definition under its last section.
  const topLevel = sections.filter(s => !s.number.includes("."))
  const assumptionsAt = topLevel.some(s => s.number === "6") ? "6" : topLevel[topLevel.length - 1]?.number
  return <div className="pa-memo space-y-7" data-view={analyst ? "analyst" : "leader"}>
    {sections.filter(s => !s.number.includes(".")).map(s => {
      const children = sections.filter(c => c.number.startsWith(`${s.number}.`))
      return <section key={s.number} aria-labelledby={`memo-${briefId}-${s.number}`}>
        {heading(s, false)}
        {children.length > 0 && <div className="mt-4 space-y-6">{children.map(c =>
          <section key={c.number} aria-labelledby={`memo-${briefId}-${c.number}`} className={c.card ? "" : "border-l-2 border-rule pl-4"}>{heading(c, true)}{body(c)}</section>)}</div>}
        <div className={children.length ? "mt-4" : ""}>{body(s)}</div>
        {budgetNote && s.number === "3" && <BudgetNote text={budgetNote}/>}
        {definition && s.number === assumptionsAt && <DefinitionWords definition={definition} labelWeek={labelWeek}/>}
      </section>
    })}
  </div>
}
