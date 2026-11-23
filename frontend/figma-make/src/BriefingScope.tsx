import { useState } from "react"
import { DEFAULT_COMPARISON_WEEKS } from "./ComparisonPicker"
import { readBriefingScope, type BriefingScope, type Comparison, type ReleaseContext } from "./agent/briefingApi"
import { asList, proposedChoices, type DefinitionChoices, type DefinitionField } from "./BriefDefinition"

// brief-008 FR-007 and FR-008. The period (First week, Last week) and the question reader for the New briefing form.
// "Read my question" asks the API for a proposed scope (a configured model proposes, code validates, the rules read
// it otherwise) and fills the form. Nothing runs on a proposal: the analyst checks the form and builds as usual.

const FIELD = "w-full min-w-0 rounded-lg border border-edge bg-paper px-3.5 py-2.5 text-sm text-ink placeholder:text-muted disabled:opacity-60"
const LABEL = "flex flex-col gap-1.5 text-xs font-medium text-muted"
const BTN2 = "inline-flex items-center justify-center gap-2 rounded-lg border border-edge px-5 py-2.5 text-sm font-medium text-ink shadow-[0_3px_0_var(--color-slab)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-paper active:translate-y-[2px] active:shadow-[0_1px_0_var(--color-slab)] disabled:cursor-not-allowed disabled:text-muted disabled:shadow-none"

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

export function PeriodPicker({ first, last, weeks, disabled, onFirst, onLast, labelWeek }: PeriodProps) {
  const error = periodError(first, last, weeks)
  const newestFirst = [...weeks].reverse()
  return <div className="grid gap-4 sm:grid-cols-2">
    <label className={LABEL}>First week
      <select className={FIELD} value={first} onChange={event => onFirst(event.target.value)} disabled={disabled}
        aria-invalid={!!error} aria-describedby={error ? "period-error" : undefined}>
        {newestFirst.map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}
      </select>
    </label>
    <div className="space-y-1">
      <label className={LABEL}>Last week
        <select className={FIELD} value={last} onChange={event => onLast(event.target.value)} disabled={disabled}
          aria-invalid={!!error} aria-describedby={error ? "period-error" : undefined}>
          {newestFirst.filter(w => w >= first).map(w => <option key={w} value={w}>{labelWeek(w)}</option>)}
        </select>
      </label>
      <p id="period-error" role="status" className="text-xs text-amber">{error}</p>
    </div>
  </div>
}

type ReaderProps = {
  question: string; onQuestion: (text: string) => void
  brand: string; context: ReleaseContext | null; disabled: boolean
  onApply: (values: FormValues) => void
}

/** The question box and "Read my question". The result names who read it and fills the form through onApply. */
export function QuestionReader({ question, onQuestion, brand, context, disabled, onApply }: ReaderProps) {
  const [busy, setBusy] = useState(false)
  const [read, setRead] = useState<BriefingScope | null>(null)
  const [error, setError] = useState<string | null>(null)
  const typed = question.trim()
  const run = async () => {
    if (!context || busy || typed.length < 3) return
    setBusy(true); setError(null); setRead(null)
    try {
      const scope = await readBriefingScope({ question: typed.slice(0, 300), brand_id: brand })
      const checked = scopeToForm(scope, context, brand)
      if ("error" in checked) setError(`${checked.error} The form keeps your last values.`)
      else { onApply(checked.values); setRead(scope) }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }
  return <div className="space-y-2">
    <label className={LABEL}>Your question (optional)
      <textarea value={question} onChange={event => { onQuestion(event.target.value); setRead(null); setError(null) }} maxLength={300} rows={2}
        placeholder="For example: how did the Southeast do in August, against the previous eight weeks?" className={FIELD} disabled={disabled}/>
    </label>
    <div className="flex flex-wrap items-center gap-3">
      <button type="button" onClick={() => void run()} disabled={disabled || busy || !context || typed.length < 3} className={BTN2}>{busy ? "Reading…" : "Read my question"}</button>
      <span className="text-xs text-muted">Fills the weeks, territory, comparison and the other choices from your question. You confirm them.</span>
    </div>
    {/* The region is always in the page, so a screen reader announces the text when it arrives. */}
    <div role="status" className="text-xs text-muted">{read && <><p><span className="font-medium text-ink">{readByLabel(read)}.</span> Check the form, then generate the briefing.</p>
      {!!read.notes.length && <ul className="mt-1 list-disc space-y-0.5 pl-5">{read.notes.map(n => <li key={n}>{n}</li>)}</ul>}</>}</div>
    {error && <p role="alert" className="text-xs text-amber">{error}</p>}
  </div>
}
