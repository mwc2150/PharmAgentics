import type { Comparison } from "./agent/briefingApi"

type Props = {
  value: Comparison | null
  onChange: (value: Comparison | null) => void
  week: string
  weeks: string[]
  disabled: boolean
  labelWeek: (week: string) => string
}

const field = "block w-full rounded-lg border border-rule bg-sheet px-3 py-2 text-sm text-ink disabled:opacity-50"

function shiftWeek(week: string, count: number): string {
  const date = new Date(`${week}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + count * 7)
  return date.toISOString().slice(0, 10)
}

export function comparisonError(value: Comparison | null, week: string, weeks: string[]): string | null {
  if (value === null || !week) return null
  const available = new Set(weeks)
  if (value.kind === "last_year" && !available.has(shiftWeek(week, -52))) {
    return "The same week last year is outside the release. Choose another comparison or use the default."
  }
  if (value.kind === "previous" && !Array.from({ length: value.weeks }, (_, i) => shiftWeek(week, -1 - i))
    .every(w => available.has(w))) return "There are fewer previous weeks in the release. Choose fewer weeks or use the default."
  if (value.kind === "custom") {
    if (!value.start || !value.end) return "Choose both custom comparison weeks."
    if (value.start > value.end) return "The start week must come before or match the end week."
    if (value.end >= week) return "The comparison must end before the reporting week."
    if (!available.has(value.start) || !available.has(value.end)) return "Choose comparison weeks inside the release."
  }
  return null
}

export function ComparisonPicker({ value, onChange, week, weeks, disabled, labelWeek }: Props) {
  const earlier = weeks.filter(w => w < week)
  const error = comparisonError(value, week, weeks)

  return <fieldset className="space-y-2" disabled={disabled}>
    <label className="block space-y-1 text-xs font-medium text-muted">Comparison window
      <select className={field} value={value?.kind ?? "default"}
        aria-describedby={error ? "comparison-error" : undefined} onChange={event => {
          const kind = event.target.value
          if (kind === "previous") onChange({ kind, weeks: 4 })
          else if (kind === "last_year") onChange({ kind })
          else if (kind === "custom") onChange({ kind, start: "", end: "" })
          else onChange(null)
        }}>
        <option value="default">Default (previous four weeks)</option>
        <option value="previous">Previous weeks</option>
        <option value="last_year">Same week last year</option>
        <option value="custom">Custom weeks</option>
      </select>
    </label>
    {value?.kind === "previous" && <label className="block text-xs text-muted">Number of weeks
      <select className={field} value={value.weeks} onChange={event => onChange({ ...value, weeks: Number(event.target.value) })}>
        {Array.from({length: 13}, (_, i) => i + 1).map(n => <option key={n} value={n}>{n}</option>)}
      </select>
    </label>}
    {value?.kind === "custom" && <div className="grid gap-2 sm:grid-cols-2">
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
    {error && <p id="comparison-error" role="status" className="text-xs text-amber">{error}</p>}
  </fieldset>
}
