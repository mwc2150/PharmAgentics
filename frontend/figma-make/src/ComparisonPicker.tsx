import type { Comparison } from "./agent/briefingApi"

// brief-008 FR-007: "Compare with the previous N weeks" (1 to 13) is the main choice; the same weeks last year,
// pre-launch weeks and custom dates are the others (brief-010 FR-000e: one or more, the first the main one).
// The default is a choice in the first row's dropdown: the form sends no comparison (empty list) and the server applies its own rule (the
// four weeks before the period, shortened where the release starts; the materiality screen uses as many preceding
// weeks as a longer period has). The same rule runs in the eval, so a brief made here matches what is scored.
export const DEFAULT_COMPARISON_WEEKS = 4

const field = "block w-full rounded-lg border border-edge bg-sheet px-3 py-2 text-sm text-ink placeholder:text-muted disabled:opacity-50"

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
    if (first && earlierWeekCount(period, weeks) === 0) return "There are no earlier weeks in the release to compare with. Choose another comparison."
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

/** The errors for a list of comparisons: each one's own, and none chosen twice. An empty list is the default. */
export function comparisonsError(value: Comparison[], period: string[], weeks: string[]): string | null {
  for (const c of value) {
    const error = comparisonError(c, period, weeks)
    if (error) return error
  }
  const seen = new Set(value.map(c => JSON.stringify(c)))
  return seen.size < value.length ? "Choose each comparison once." : null
}

const KINDS: [Comparison["kind"], string][] = [["previous", "The previous weeks"], ["last_year", "The same weeks last year"], ["pre_launch", "Pre-launch weeks"], ["custom", "Custom weeks"]]

function blank(kind: Comparison["kind"]): Comparison {
  if (kind === "previous") return { kind, weeks: DEFAULT_COMPARISON_WEEKS }
  if (kind === "custom") return { kind, start: "", end: "" }
  return { kind }
}

type ListProps = {
  value: Comparison[]   // the chosen comparisons in order, the first is the main one; empty: the default comparison
  onChange: (value: Comparison[]) => void
  period: string[]   // the reporting weeks, first to last
  weeks: string[]    // every week of the release
  disabled: boolean
  labelWeek: (week: string) => string
}

const DEFAULT_KIND = "default"

// brief-010 FR-000e: one or more comparisons, the first the main one, in one row layout. "Default" is the first
// option of row 1 while it is the only row: the previous four weeks, shortened where the release starts.
export function ComparisonPicker({ value, onChange, period, weeks, disabled, labelWeek }: ListProps) {
  const earlier = weeks.filter(w => !period[0] || w < period[0])
  const error = comparisonsError(value, period, weeks)
  const earlierCount = earlierWeekCount(period, weeks)
  const isDefault = value.length === 0
  const rows: (Comparison | null)[] = isDefault ? [null] : value  // null: the default row
  const change = (i: number, next: Comparison) => onChange(isDefault ? [next] : value.map((c, j) => j === i ? next : c))
  const choose = (i: number, kind: string) => {
    if (kind === DEFAULT_KIND) onChange([])
    else change(i, blank(kind as Comparison["kind"]))
  }
  const rowError = (c: Comparison) => comparisonError(c, period, weeks)
  // Adding to the default makes it explicit, so the whole list can be sent: the same weeks the server's default uses
  // (the four before the period, fewer where the release starts later; stages.BASELINE_WEEKS). With no earlier week
  // there is nothing to make explicit, so the analyst picks a main comparison first.
  const seed: Comparison = { kind: "previous", weeks: Math.min(DEFAULT_COMPARISON_WEEKS, earlierCount) }
  const cannotSeed = isDefault && earlierCount === 0
  const base = isDefault ? [seed] : value
  const unused = KINDS.map(([k]) => k).find(k => !base.some(c => c.kind === k))

  const row = (c: Comparison | null, i: number) => <li key={i} className="space-y-2 rounded-lg border border-rule p-3">
    <label htmlFor={`comparison-kind-${i}`} className="block text-xs text-muted">{i === 0 ? "Main comparison" : "Also compare with"}</label>
    <div className="flex flex-wrap items-center gap-2">
      <select id={`comparison-kind-${i}`} className={`${field} !w-auto`} value={c?.kind ?? DEFAULT_KIND} aria-describedby={c === null ? "comparison-default" : undefined}
        onChange={event => choose(i, event.target.value)}>
        {i === 0 && value.length <= 1 && <option value={DEFAULT_KIND}>Default: the {DEFAULT_COMPARISON_WEEKS} weeks before the period</option>}
        {KINDS.map(([k, name]) => <option key={k} value={k}>{name}</option>)}
      </select>
      {c?.kind === "previous" && <label className="flex items-center gap-2 text-sm text-ink">
        <input type="number" inputMode="numeric" min={1} max={13} step={1} className={`${field} !w-20 tabular-nums`} aria-label="Number of previous weeks"
          value={Number.isFinite(c.weeks) ? c.weeks : ""} aria-invalid={!!rowError(c)}
          onChange={event => change(i, { kind: "previous", weeks: Number(event.target.value) })}/>weeks</label>}
      {i > 0 && <button type="button" className="text-xs text-muted underline" onClick={() => onChange(value.filter((_, j) => j !== i))}>Remove</button>}
    </div>
    {c === null && <p id="comparison-default" className="text-xs text-muted">{earlierCount === 0 && period.length
      ? "There are no earlier weeks in the release to compare with. The briefing runs without a comparison period."
      : "The default shortens where the release starts later. A longer period is screened against as many preceding weeks as it has."}</p>}
    {c?.kind === "custom" && <div className="grid gap-2 sm:grid-cols-2">
      <label className="block text-xs text-muted">Start week
        <select className={field} value={c.start} onChange={event => change(i, { ...c, start: event.target.value })}>
          <option value="">Select a week</option>
          {earlier.map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}
        </select>
      </label>
      <label className="block text-xs text-muted">End week
        <select className={field} value={c.end} onChange={event => change(i, { ...c, end: event.target.value })}>
          <option value="">Select a week</option>
          {earlier.map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}
        </select>
      </label>
    </div>}
  </li>

  return <fieldset className="space-y-3" disabled={disabled}>
    <legend className="text-xs font-medium text-muted">Compare with</legend>
    <ol className="space-y-2">{rows.map(row)}</ol>
    <div className="text-xs">
      <button type="button" className="text-primaryink hover:underline disabled:cursor-not-allowed disabled:text-muted disabled:no-underline" disabled={unused === undefined || cannotSeed}
        title={cannotSeed ? "The release has no earlier weeks for the default. Choose a main comparison first." : undefined}
        onClick={() => unused && !cannotSeed && onChange([...base, blank(unused)])}>Add a comparison</button>
    </div>
    {error && <p id="comparison-error" role="status" className="text-xs text-neg">{error}</p>}
  </fieldset>
}
