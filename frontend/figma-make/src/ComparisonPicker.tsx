import type { Comparison } from "./agent/briefingApi"

// brief-008 FR-007: "Compare with the previous N weeks" (1 to 13, default 4) is the main choice. The brief-007
// choices, the same weeks last year and custom dates, sit under "Other comparison".
export const DEFAULT_COMPARISON: Comparison = { kind: "previous", weeks: 4 }

type Props = {
  value: Comparison
  onChange: (value: Comparison) => void
  period: string[]   // the reporting weeks, first to last
  weeks: string[]    // every week of the release
  disabled: boolean
  labelWeek: (week: string) => string
}

const field = "block w-full rounded-lg border border-rule bg-sheet px-3 py-2 text-sm text-ink disabled:opacity-50"

function shiftWeek(week: string, count: number): string {
  const date = new Date(`${week}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + count * 7)
  return date.toISOString().slice(0, 10)
}

export function comparisonError(value: Comparison | null, period: string[], weeks: string[]): string | null {
  if (value === null) return null
  const available = new Set(weeks)
  const first = period[0]
  if (value.kind === "previous") {
    if (!Number.isInteger(value.weeks) || value.weeks < 1 || value.weeks > 13) return "Enter a whole number of weeks from 1 to 13."
    if (first && !Array.from({ length: value.weeks }, (_, i) => shiftWeek(first, -1 - i)).every(w => available.has(w))) {
      return "The release has fewer earlier weeks than that. Choose fewer weeks."
    }
  }
  if (value.kind === "last_year" && period.length && !period.every(w => available.has(shiftWeek(w, -52)))) {
    return "The same weeks last year are outside the release. Choose another comparison."
  }
  if (value.kind === "custom") {
    if (!value.start || !value.end) return "Choose both custom comparison weeks."
    if (value.start > value.end) return "The start week must come before or match the end week."
    if (first && value.end >= first) return "The comparison must end before the first reporting week."
    if (!available.has(value.start) || !available.has(value.end)) return "Choose comparison weeks inside the release."
  }
  return null
}

export function ComparisonPicker({ value, onChange, period, weeks, disabled, labelWeek }: Props) {
  const earlier = weeks.filter(w => !period[0] || w < period[0])
  const error = comparisonError(value, period, weeks)
  const other = value.kind !== "previous"

  return <fieldset className="space-y-3" disabled={disabled}>
    <legend className="sr-only">Comparison</legend>
    <div className="space-y-1">
      <label className="flex flex-wrap items-center gap-2 text-sm text-ink">
        <span>Compare with the previous</span>
        <input type="number" inputMode="numeric" min={1} max={13} step={1} className={`${field} !w-20 tabular-nums`}
          value={value.kind === "previous" && Number.isFinite(value.weeks) ? value.weeks : ""}
          aria-invalid={!!error && value.kind === "previous"} aria-describedby={error ? "comparison-error" : undefined}
          onChange={event => onChange({ kind: "previous", weeks: event.target.value === "" ? Number.NaN : Number(event.target.value) })}/>
        <span>weeks</span>
      </label>
      {other && <p className="text-xs text-muted">Using {value.kind === "last_year" ? "the same weeks last year" : "custom weeks"} instead.
        {" "}<button type="button" className="underline" onClick={() => onChange(DEFAULT_COMPARISON)}>Use the previous 4 weeks</button></p>}
    </div>
    <details className="text-xs text-muted" open={other}>
      <summary className="cursor-pointer select-none">Other comparison</summary>
      <div className="mt-2 space-y-2">
        <label className="block space-y-1 text-xs font-medium text-muted">Compare with
          <select className={field} value={value.kind} onChange={event => {
            const kind = event.target.value
            if (kind === "last_year") onChange({ kind })
            else if (kind === "custom") onChange({ kind, start: "", end: "" })
            else onChange(DEFAULT_COMPARISON)
          }}>
            <option value="previous">The previous weeks, set above</option>
            <option value="last_year">The same weeks last year</option>
            <option value="custom">Custom weeks</option>
          </select>
        </label>
        {value.kind === "custom" && <div className="grid gap-2 sm:grid-cols-2">
          <label className="block text-xs text-muted">Start week
            <select className={field} value={value.start} onChange={event => onChange({ ...value, start: event.target.value })}>
              <option value="">Select a week</option>
              {earlier.map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}
            </select>
          </label>
          <label className="block text-xs text-muted">End week
            <select className={field} value={value.end} onChange={event => onChange({ ...value, end: event.target.value })}>
              <option value="">Select a week</option>
              {earlier.map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}
            </select>
          </label>
        </div>}
      </div>
    </details>
    {error && <p id="comparison-error" role="status" className="text-xs text-amber">{error}</p>}
  </fieldset>
}
