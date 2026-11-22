// Forecast charts (fcst-002). Code builds every chart's data from an answer's stored numbers; a model only chooses
// which chart to show. Inline SVG, no chart library. Colours were validated for this dark surface (#131a18) with the
// dataviz palette checks: two series blue/orange; signed values blue (raises) / red (lowers) around a neutral gray.
import { useState } from "react"

export type ChartSpec = {
  kind: "waterfall" | "bars" | "lines"; title: string; unit?: string; series?: string[]
  steps?: { label: string; value: number; kind: "total" | "delta" }[]
  rows?: { label: string; a: number; b?: number; flag?: boolean }[]
}

const BLUE = "#3987e5", ORANGE = "#d95926", RED = "#e66767", GRID = "#2a3431"
const fmt = (v: number, unit?: string) => unit === "%" ? `${v.toFixed(1)}%` : Math.round(v).toLocaleString("en-US")
const short = (s: string, n = 26) => (s.length > n ? s.slice(0, n - 1) + "…" : s)

function Legend({ items }: { items: [string, string][] }) {
  return <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted">{items.map(([label, color]) =>
    <span key={label} className="inline-flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }}/>{label}</span>)}</div>
}

// Signed horizontal bars from a zero line: the contributions from forecast to actual, or territory misses.
function SignedBars({ rows, series, unit }: { rows: { label: string; values: number[]; note?: string }[]; series: string[]; unit: string }) {
  const W = 640, labelW = 190, pad = 56, band = series.length > 1 ? 30 : 24, h = 11
  // The axis spans the data and always includes zero, so one-signed data uses the full width.
  const all = rows.flatMap(r => r.values)
  const lo = Math.min(0, ...all), hi = Math.max(0, ...all), span = Math.max(1, hi - lo)
  const plot = W - labelW - pad * 2, scale = plot / span, zero = labelW + pad + -lo * scale
  const H = rows.length * band + 24
  const color = (i: number, v: number) => (series.length > 1 ? [BLUE, ORANGE][i] : v < 0 ? RED : BLUE)
  return <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={series.join(" and ")}>
    <line x1={zero} x2={zero} y1={0} y2={H - 20} stroke={GRID} strokeWidth={1}/>
    {rows.map((r, i) => {
      const y0 = i * band + 6
      return <g key={r.label}>
        <text x={labelW} y={y0 + band / 2} dominantBaseline="middle" textAnchor="end" className="fill-muted text-[11px]">{short(r.label)}</text>
        {r.values.map((v, j) => {
          const w = Math.max(1, Math.abs(v) * scale), y = y0 + (series.length > 1 ? j * (h + 2) : (band - h) / 2 - 3)
          const x = v < 0 ? zero - w : zero
          return <g key={j}>
            <rect x={x} y={y} width={w} height={h} rx={2} fill={color(j, v)}><title>{`${r.label}${series.length > 1 ? ` · ${series[j]}` : ""}: ${fmt(v, unit)}${unit === "%" ? "" : ` ${unit}`}${r.note ? ` (${r.note})` : ""}`}</title></rect>
            {(series.length === 1 || j === 0) && <text x={v < 0 ? x - 4 : x + w + 4} y={y + h / 2} dominantBaseline="middle" textAnchor={v < 0 ? "end" : "start"} className="fill-ink text-[10px] tabular-nums">{fmt(v, unit)}</text>}
          </g>
        })}
      </g>
    })}
    <text x={zero} y={H - 6} textAnchor="middle" className="fill-muted text-[10px]">0</text>
  </svg>
}

// Columns by week from a zero line; provisional weeks drawn as an outline.
function WeekColumns({ rows, unit }: { rows: { label: string; a: number; flag?: boolean }[]; unit: string }) {
  const W = 640, H = 200, left = 44, bottom = 28, top = 10
  const max = Math.max(1, ...rows.map(r => Math.abs(r.a)))
  const neg = rows.some(r => r.a < 0), pos = rows.some(r => r.a > 0)
  const zero = pos && neg ? top + (H - top - bottom) / 2 : neg ? top : H - bottom
  const scale = (pos && neg ? (H - top - bottom) / 2 : H - top - bottom) / max
  const step = (W - left) / rows.length, bw = Math.min(24, step - 2)
  const every = Math.ceil(rows.length / 8)
  return <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Miss by week">
    <line x1={left} x2={W} y1={zero} y2={zero} stroke={GRID} strokeWidth={1}/>
    <text x={left - 6} y={zero} dominantBaseline="middle" textAnchor="end" className="fill-muted text-[10px]">0</text>
    {rows.map((r, i) => {
      const hgt = Math.max(1, Math.abs(r.a) * scale), x = left + i * step + (step - bw) / 2, y = r.a < 0 ? zero : zero - hgt
      const c = r.a < 0 ? RED : BLUE
      return <g key={r.label}>
        <rect x={x} y={y} width={bw} height={hgt} rx={2} fill={r.flag ? "none" : c} stroke={r.flag ? c : "none"} strokeWidth={1.5} strokeDasharray={r.flag ? "3 2" : undefined}>
          <title>{`${r.label}: ${fmt(r.a)} ${unit}${r.flag ? " (provisional actual)" : ""}`}</title></rect>
        {i % every === 0 && <text x={x + bw / 2} y={H - 10} textAnchor="middle" className="fill-muted text-[10px]">{r.label.slice(5)}</text>}
      </g>
    })}
  </svg>
}

// Two lines on one axis (forecast and actual), with a hover readout per week.
function TwoLines({ rows, series, unit }: { rows: { label: string; a: number; b?: number }[]; series: string[]; unit: string }) {
  const [hover, setHover] = useState<number | null>(null)
  const W = 640, H = 210, left = 52, right = 12, top = 12, bottom = 28
  const vals = rows.flatMap(r => [r.a, r.b ?? r.a])
  const lo = Math.min(...vals), hi = Math.max(...vals), span = Math.max(1, hi - lo)
  const y0 = lo - span * 0.08, y1 = hi + span * 0.08
  const x = (i: number) => left + (i * (W - left - right)) / Math.max(1, rows.length - 1)
  const y = (v: number) => top + (1 - (v - y0) / (y1 - y0)) * (H - top - bottom)
  const path = (k: "a" | "b") => rows.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y((r[k] ?? r.a) as number).toFixed(1)}`).join(" ")
  const ticks = [y0 + (y1 - y0) * 0.1, (y0 + y1) / 2, y1 - (y1 - y0) * 0.1]
  const every = Math.ceil(rows.length / 8)
  return <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={series.join(" and ")} onMouseLeave={() => setHover(null)}>
    {ticks.map(t => <g key={t}><line x1={left} x2={W - right} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth={1}/><text x={left - 6} y={y(t)} dominantBaseline="middle" textAnchor="end" className="fill-muted text-[10px] tabular-nums">{fmt(t)}</text></g>)}
    <path d={path("a")} fill="none" stroke={BLUE} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"/>
    <path d={path("b")} fill="none" stroke={ORANGE} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"/>
    {rows.map((r, i) => <g key={r.label}>
      {i % every === 0 && <text x={x(i)} y={H - 10} textAnchor="middle" className="fill-muted text-[10px]">{r.label.slice(5)}</text>}
      <rect x={x(i) - (W - left) / rows.length / 2} y={top} width={(W - left) / rows.length} height={H - top - bottom} fill="transparent" onMouseEnter={() => setHover(i)}/>
    </g>)}
    {hover !== null && <g pointerEvents="none">
      <line x1={x(hover)} x2={x(hover)} y1={top} y2={H - bottom} stroke="#94a39d" strokeWidth={1}/>
      <circle cx={x(hover)} cy={y(rows[hover].a)} r={4} fill={BLUE} stroke="#131a18" strokeWidth={2}/>
      <circle cx={x(hover)} cy={y(rows[hover].b ?? rows[hover].a)} r={4} fill={ORANGE} stroke="#131a18" strokeWidth={2}/>
      <text x={Math.min(x(hover) + 8, W - 170)} y={top + 10} className="fill-ink text-[11px] tabular-nums">{`${rows[hover].label} · ${series[0]} ${fmt(rows[hover].a)} · ${series[1]} ${fmt(rows[hover].b ?? 0)}`}</text>
    </g>}
  </svg>
}

export function ForecastChart({ spec }: { spec: ChartSpec }) {
  const unit = spec.unit ?? "TRx"
  let body = null, legend: [string, string][] = [], caption = "", table: [string, string][] = []
  if (spec.kind === "waterfall" && spec.steps) {
    const totals = spec.steps.filter(s => s.kind === "total"), deltas = spec.steps.filter(s => s.kind === "delta")
    caption = totals.map(t => `${t.label} ${fmt(t.value)} ${unit}`).join(" · ")
    body = <SignedBars rows={deltas.map(d => ({ label: d.label, values: [d.value] }))} series={["Contribution"]} unit={unit}/>
    legend = [["Lowers TRx", RED], ["Raises TRx", BLUE]]
    table = spec.steps.map(s => [s.label, fmt(s.value)])
  } else if (spec.kind === "bars" && spec.rows) {
    const two = (spec.series?.length ?? 1) > 1
    body = two ? <SignedBars rows={spec.rows.map(r => ({ label: r.label, values: [r.a, r.b ?? 0] }))} series={spec.series ?? []} unit={unit}/>
      : <WeekColumns rows={spec.rows} unit={unit}/>
    legend = two ? (spec.series ?? []).map((s, i) => [s, [BLUE, ORANGE][i]] as [string, string]) : [["Below forecast", RED], ["Above forecast", BLUE]]
    if (!two && spec.rows.some(r => r.flag)) legend.push(["Provisional (outline)", "#94a39d"])
    table = spec.rows.map(r => [r.label, two ? `${fmt(r.a, unit)} · ${fmt(r.b ?? 0, unit)}` : fmt(r.a, unit) + (r.flag ? " (provisional)" : "")])
  } else if (spec.kind === "lines" && spec.rows) {
    body = <TwoLines rows={spec.rows} series={spec.series ?? ["Forecast", "Actual"]} unit={unit}/>
    legend = (spec.series ?? ["Forecast", "Actual"]).map((s, i) => [s, [BLUE, ORANGE][i]] as [string, string])
    table = spec.rows.map(r => [r.label, `${fmt(r.a)} · ${fmt(r.b ?? 0)}`])
  }
  if (!body) return null
  return <figure className="rounded-lg border border-rule bg-sheet p-4">
    <figcaption className="text-sm font-medium">{spec.title}{caption && <span className="block text-xs font-normal text-muted tabular-nums">{caption}</span>}</figcaption>
    <div className="mt-2">{body}</div>
    <Legend items={legend}/>
    <details className="mt-2"><summary className="cursor-pointer text-xs text-muted">Data</summary>
      <table className="mt-1 text-xs tabular-nums"><tbody>{table.map(([k, v]) => <tr key={k}><td className="pr-4 text-muted">{k}</td><td className="text-ink">{v}</td></tr>)}</tbody></table></details>
  </figure>
}
