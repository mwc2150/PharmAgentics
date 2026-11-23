import type { Comparison } from "./agent/briefingApi"

// brief-008 FR-007: "Compare with the previous N weeks" (1 to 13) is the main choice. The brief-007 choices, the
// same weeks last year and custom dates, sit under "Other comparison".
// The default is no choice at all: the form sends no comparison (null) and the server applies its own rule (the
// four weeks before the period, shortened where the release starts; the materiality screen uses as many preceding
// weeks as a longer period has). The same rule runs in the eval, so a brief made here matches what is scored.
export const DEFAULT_COMPARISON_WEEKS = 4

type Props = {
  value: Comparison | null   // null: the default comparison
  onChange: (value: Comparison | null) => void
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

/** How many release weeks come before the period starts. */
export function earlierWeekCount(period: string[], weeks: string[]): number {
  return period[0] ? weeks.filter(w => w < period[0]).length : 0
}

export function comparisonError(value: Comparison | null, period: string[], weeks: string[]): string | null {
  if (value === null) return null  // the default is always allowed: the server shortens it to the weeks that exist
  const available = new Set(weeks)
  const first = period[0]
  if (value.kind === "previous") {
    if (!Number.isInteger(value.weeks) || value.weeks < 1 || value.weeks > 13) return "Enter a whole number of weeks from 1 to 13."
    if (first && earlierWeekCount(period, weeks) === 0) return "There are no earlier weeks in the release to compare with. Clear the number to use the default."
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
  const other = value !== null && value.kind !== "previous"
  const earlierCount = earlierWeekCount(period, weeks)

  return <fieldset className="space-y-3" disabled={disabled}>
    <legend className="sr-only">Comparison</legend>
    <div className="space-y-1">
      <label className="flex flex-wrap items-center gap-2 text-sm text-ink">
        <span>Compare with the previous</span>
        <input type="number" inputMode="numeric" min={1} max={13} step={1} className={`${field} !w-20 tabular-nums`}
          value={value?.kind === "previous" && Number.isFinite(value.weeks) ? value.weeks : ""} placeholder="Default"
          aria-invalid={!!error && value?.kind === "previous"} aria-describedby={error ? "comparison-error" : "comparison-default"}
          onChange={event => onChange(event.target.value === "" ? null : { kind: "previous", weeks: Number(event.target.value) })}/>
        <span>weeks</span>
      </label>
      {value === null && <p id="comparison-default" className="text-xs text-muted">{earlierCount === 0 && period.length
        ? "There are no earlier weeks in the release to compare with. The briefing runs without a comparison period."
        : `Default: the ${DEFAULT_COMPARISON_WEEKS} weeks before the period, or fewer where the release starts later. A longer period is screened against as many preceding weeks as it has.`}</p>}
      {other && <p className="text-xs text-muted">Using {value.kind === "last_year" ? "the same weeks last year" : value.kind === "pre_launch" ? "the four weeks before Metacora launched" : "custom weeks"} instead.
        {" "}<button type="button" className="underline" onClick={() => onChange(null)}>Use the default comparison</button></p>}
    </div>
    <details className="text-xs text-muted" open={other}>
      <summary className="cursor-pointer select-none">Other comparison</summary>
      <div className="mt-2 space-y-2">
        <label className="block space-y-1 text-xs font-medium text-muted">Compare with
          <select className={field} value={value?.kind ?? "previous"} onChange={event => {
            const kind = event.target.value
            if (kind === "last_year" || kind === "pre_launch") onChange({ kind })
            else if (kind === "custom") onChange({ kind, start: "", end: "" })
            else onChange(null)
          }}>
            <option value="previous">The previous weeks, set above (default)</option>
            <option value="last_year">The same weeks last year</option>
            <option value="pre_launch">Pre-launch weeks</option>
            <option value="custom">Custom weeks</option>
          </select>
        </label>
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
      </div>
    </details>
    {error && <p id="comparison-error" role="status" className="text-xs text-amber">{error}</p>}
  </fieldset>
}
