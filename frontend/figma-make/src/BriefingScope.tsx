import { useId, useRef, useState } from "react"
import { Icon } from "./agent/primitives"
import { DEFAULT_COMPARISON_WEEKS } from "./ComparisonPicker"
import { readBriefingScope, type BriefingScope, type Comparison, type ReleaseContext } from "./agent/briefingApi"
import { asList, proposedChoices, type DefinitionChoices, type DefinitionField } from "./BriefDefinition"

// brief-008 FR-007 and FR-008. The period (First week, Last week) and the question reader for the New briefing form.
// useQuestionReader asks the API for a proposed scope (a configured model proposes, code validates, the rules read
// it otherwise) and fills the form; the message bar on the New briefing tab is its one input. Nothing runs on a
// proposal: the analyst checks the form and builds as usual.

const FIELD = "w-full min-w-0 rounded-lg border border-edge bg-paper px-3.5 py-2.5 text-sm text-ink placeholder:text-muted disabled:opacity-60"
const LABEL = "flex flex-col gap-1.5 text-xs font-medium text-muted"

/** An error for the chosen period, or null. The weeks are the release's Mondays. */
export function periodError(first: string, last: string, weeks: string[]): string | null {
  if (!first || !last) return "Choose the first and the last week."
  if (!weeks.includes(first) || !weeks.includes(last)) return "Choose weeks inside the release."
  if (last < first) return "The last week comes before the first week."
  return null
}

/** Every release week from `first` to `last`, in order. Empty when the period is invalid. */
export function periodWeeks(first: string, last: string, weeks: string[]): string[] {
  return periodError(first, last, weeks) ? [] : weeks.filter(w => w >= first && w <= last)
}

// brief-010: `choices` are the definition fields the reader proposed (territories counted, measure, grain, relative to);
// a field it left out is absent, so the form keeps the analyst's value. `proposed` names them for the "proposed" marks.
export type FormValues = { territory: string | null; week: string; weekEnd: string; promotion: boolean; comparison: Comparison[]
  choices: Partial<DefinitionChoices>; proposed: DefinitionField[] }

/** The comparisons a proposed definition names (one or a list, the first the primary), checked like the weeks count.
 *  A single previous-weeks comparison equal to what the default rule gives stays the default (an empty list). */
function proposedComparisons(def: unknown, earlier: number, weeks: string[]): Comparison[] | { error: string } {
  const list = asList(def as Comparison | Comparison[] | null | undefined)
  const out: Comparison[] = []
  for (const c of list) {
    if (c.kind === "last_year" || c.kind === "pre_launch") out.push({ kind: c.kind })
    else if (c.kind === "custom") {
      if (!c.start || !c.end || c.start > c.end || !weeks.includes(c.start) || !weeks.includes(c.end)) return { error: "The proposed comparison weeks do not fit the release." }
      out.push({ kind: "custom", start: c.start, end: c.end })
    } else if (c.kind === "previous") {
      if (!Number.isInteger(c.weeks) || c.weeks < 1 || c.weeks > 13) return { error: "The proposed comparison is not from 1 to 13 weeks." }
      out.push({ kind: "previous", weeks: c.weeks })
    } else return { error: "The proposed comparison is not one of the choices." }
  }
  const unique = out.filter((c, i) => out.findIndex(d => JSON.stringify(d) === JSON.stringify(c)) === i)
  return unique.length === 1 && unique[0].kind === "previous" && unique[0].weeks === Math.min(DEFAULT_COMPARISON_WEEKS, earlier) ? [] : unique
}

/** A proposed scope as form values, after the same checks the server made: weeks in the release and in order, a
 *  known territory, a whole comparison of 1 to 13 weeks. Anything else is refused with the reason. */
export function scopeToForm(scope: BriefingScope, context: ReleaseContext, brand: string): { values: FormValues } | { error: string } {
  const def = scope.definition ?? null
  // The definition's own weeks win over the older fields when the reader returned them.
  const first = def?.first_week || scope.week_start
  const last = def?.last_week || scope.week_end
  const problem = periodError(first, last, context.available_weeks)
  if (problem) return { error: `The proposed weeks do not fit the release. ${problem}` }
  if (scope.territory_id !== null && !context.territory_ids.includes(scope.territory_id)) return { error: "The proposed territory is not in the release." }
  const count = scope.comparison_weeks  // null or 0: no earlier week fits, so the default comparison applies
  if (count != null && count !== 0 && (!Number.isInteger(count) || count < 1 || count > 13)) return { error: "The proposed comparison is not from 1 to 13 weeks." }
  // A proposal equal to what the default rule gives stays the default (empty), so the brief matches the eval's.
  const earlier = context.available_weeks.filter(w => w < first).length
  let comparison: Comparison[] = !count || count === Math.min(DEFAULT_COMPARISON_WEEKS, earlier) ? [] : [{ kind: "previous", weeks: count }]
  if (def?.comparison) {
    const named = proposedComparisons(def.comparison, earlier, context.available_weeks)
    if ("error" in named) return named
    comparison = named
  }
  if (scope.promotion_review && brand !== "BXA") return { error: "The Promotion review is available for BXA only." }
  const proposal = proposedChoices(def)
  if ("error" in proposal) return proposal
  return { values: { territory: scope.territory_id, week: first, weekEnd: last, promotion: scope.promotion_review,
    comparison, choices: proposal.choices, proposed: proposal.fields } }
}

/** Who read the question, in plain words. */
export function readByLabel(scope: Pick<BriefingScope, "read_by" | "model">): string {
  if (scope.read_by === "rules") return "Read by rules"
  return /haiku/i.test(scope.model ?? "") ? "Read by Haiku" : "Read by the model"
}

type PeriodProps = {
  first: string; last: string; weeks: string[]; disabled: boolean
  onFirst: (week: string) => void; onLast: (week: string) => void; labelWeek: (week: string) => string
}

// The words of the period's "i" panel (UAT review 2026-11-27, item 1). Kept in one place so a test can read them.
export const PERIOD_INFO = "The weeks this brief reports on. Every week from First week to Last week, both included; weeks start on Monday. One week gives that week's numbers; several give weekly averages. Each number is compared with the comparison weeks below (by default, the four weeks just before First week). Holiday and plan-year-reset weeks are left out of the stories unless they make up at least half the period."

// Quick ranges end at the latest available week (weeks run oldest to newest).
export const QUICK_RANGES = [["This week", 1], ["Last 4 weeks", 4], ["Last 13 weeks", 13]] as const
export function quickRange(count: number, weeks: string[]): { first: string; last: string } | null {
  if (!weeks.length) return null
  return { first: weeks[Math.max(0, weeks.length - count)], last: weeks[weeks.length - 1] }
}

/** Weeks (newest first) grouped by the month of their Monday, newest month first: "October 2026". */
export function weeksByMonth(weeksNewestFirst: string[]): { month: string; weeks: string[] }[] {
  const groups: { month: string; weeks: string[] }[] = []
  for (const w of weeksNewestFirst) {
    const [y, m, d] = w.split("-").map(Number)
    const month = new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", { month: "long", year: "numeric", timeZone: "UTC" })
    const last = groups[groups.length - 1]
    if (last && last.month === month) last.weeks.push(w)
    else groups.push({ month, weeks: [w] })
  }
  return groups
}

export function PeriodPicker({ first, last, weeks, disabled, onFirst, onLast, labelWeek }: PeriodProps) {
  const error = periodError(first, last, weeks)
  const newestFirst = [...weeks].reverse()
  const [infoOpen, setInfoOpen] = useState(false)
  const info = useId(), firstId = useId(), lastId = useId()
  const infoButton = useRef<HTMLButtonElement>(null)
  const closeInfo = () => { setInfoOpen(false); infoButton.current?.focus() }
  const options = (list: string[]) => weeksByMonth(list).map(g =>
    <optgroup key={g.month} label={g.month}>{g.weeks.map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}</optgroup>)
  const apply = (count: number) => { const r = quickRange(count, weeks); if (r) { onFirst(r.first); onLast(r.last) } }
  return <div className="space-y-3" onKeyDown={e => { if (e.key === "Escape" && infoOpen) { e.stopPropagation(); closeInfo() } }}>
    <div role="group" aria-label="Quick ranges" className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-muted">Quick ranges</span>
      {QUICK_RANGES.map(([text, count]) => {
        const r = quickRange(count, weeks)
        const active = !!r && r.first === first && r.last === last
        return <button key={text} type="button" disabled={disabled || !r} aria-pressed={active} onClick={() => apply(count)}
          className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-60 ${active ? "border-primary text-primaryink" : "border-edge text-muted hover:bg-paper hover:text-ink"}`}>{text}</button>
      })}
    </div>
    <div className="grid gap-4 sm:grid-cols-2">
      <div className={LABEL}>
        <span className="flex h-6 items-center gap-1.5">
          <label htmlFor={firstId}>First week</label>
          <button ref={infoButton} type="button" aria-expanded={infoOpen} aria-controls={infoOpen ? info : undefined} aria-label="What the period means"
            onClick={() => infoOpen ? closeInfo() : setInfoOpen(true)}
            className="grid h-6 w-6 place-items-center rounded-full text-muted transition-colors hover:bg-paper hover:text-ink"><Icon name="info" className="h-4 w-4"/></button>
        </span>
        <select id={firstId} className={FIELD} value={first} onChange={event => onFirst(event.target.value)} disabled={disabled}
          aria-invalid={!!error} aria-describedby={error ? "period-error" : undefined}>
          {options(newestFirst)}
        </select>
      </div>
      <div className="space-y-1">
        <div className={LABEL}>
          <span className="flex h-6 items-center"><label htmlFor={lastId}>Last week</label></span>
          <select id={lastId} className={FIELD} value={last} onChange={event => onLast(event.target.value)} disabled={disabled}
            aria-invalid={!!error} aria-describedby={error ? "period-error" : undefined}>
            {options(newestFirst.filter(w => w >= first))}
          </select>
        </div>
        <p id="period-error" role="status" className="text-xs text-neg">{error}</p>
      </div>
    </div>
    {infoOpen && <p id={info} className="max-w-[68ch] rounded-lg border border-rule bg-sheet px-4 py-3 text-xs leading-relaxed text-ink">{PERIOD_INFO}</p>}
  </div>
}

type ReaderOptions = {
  brand: string; context: ReleaseContext | null
  onApply: (values: FormValues, question: string) => void
  onStart?: () => void  // a new read begins: the earlier question no longer applies, even if this read fails
}

/** Reads a question into form values (brief-010: the bar on the form is the one question box). `run` resolves true when
 *  the form was filled; on a failed read the form keeps its values and `error` says why. `read` names who read it. */
export function useQuestionReader({ brand, context, onApply, onStart }: ReaderOptions) {
  const [busy, setBusy] = useState(false)
  const [read, setRead] = useState<BriefingScope | null>(null)
  const [error, setError] = useState<string | null>(null)
  const run = async (question: string): Promise<boolean> => {
    const typed = question.trim()
    if (busy) return false
    if (!context) { setError("The data release is not loaded yet."); return false }
    if (typed.length < 3) { setError("Ask in a few words, for example: how did the Southeast do in August?"); return false }
    setBusy(true); setError(null); setRead(null); onStart?.()
    try {
      const scope = await readBriefingScope({ question: typed.slice(0, 300), brand_id: brand })
      const checked = scopeToForm(scope, context, brand)
      if ("error" in checked) { setError(`${checked.error} The form keeps your last values.`); return false }
      onApply(checked.values, typed.slice(0, 300)); setRead(scope)
      return true
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      return false
    } finally { setBusy(false) }
  }
  const clear = () => { setRead(null); setError(null) }
  return { busy, read, error, run, clear }
}
