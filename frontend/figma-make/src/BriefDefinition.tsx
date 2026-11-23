import type { BriefDefinition, Comparison, GrainLevel, MeasureChoice, ProposedDefinition, RelativeTo, TerritoriesCounted } from "./agent/briefingApi"

// brief-010 FR-000b and FR-000e: the selectors of the brief definition that the period and comparison pickers do not
// cover (territories counted, measure, grain, relative to), the words that state a whole definition, and the checks on
// a definition the question reader proposes. Each selector takes one or more values; the first is the primary.
// Every selector has a pre-selected value; nothing is locked or hidden.

export type DefinitionChoices = { territories: TerritoriesCounted[]; measure: MeasureChoice[]; grain: GrainLevel[]; relative_to: RelativeTo[] }
export type DefinitionField = keyof DefinitionChoices

export const GRAIN_LEVELS: [GrainLevel, string][] = [
  ["national", "National"], ["territory", "Territory"], ["plan", "Plan"], ["channel", "Channel"], ["specialty", "Specialty"],
]
export const TERRITORY_OPTIONS: [TerritoriesCounted, string][] = [
  ["like_for_like", "Like for like"], ["all_reportable", "All reportable"], ["projected", "Projected national"],
]
export const MEASURE_OPTIONS: [MeasureChoice, string][] = [["trx", "TRx"], ["nbrx", "NBRx (new patients)"]]
export const RELATIVE_OPTIONS: [RelativeTo, string][] = [["other_territories", "The other territories"], ["national", "National"], ["none", "Nothing"]]

/** The pre-selected values. They reproduce the brief made before brief-010. */
export const DEFAULT_CHOICES: DefinitionChoices = {
  territories: ["like_for_like"], measure: ["trx"], grain: GRAIN_LEVELS.map(([id]) => id), relative_to: ["other_territories"],
}

/** A value or a list as a list, without repeats, in the order given. */
export function asList<T>(value: T | T[] | null | undefined): T[] {
  const list = value == null ? [] : Array.isArray(value) ? value : [value]
  return list.filter((v, i) => list.indexOf(v) === i)
}

const sameList = <T,>(a: T[], b: T[]) => a.length === b.length && a.every((v, i) => v === b[i])

/** True when the choices are the pre-selected ones (the grain in any order, as its order only picks a primary). */
export function isDefaultChoices(c: DefinitionChoices): boolean {
  return sameList(c.territories, DEFAULT_CHOICES.territories) && sameList(c.measure, DEFAULT_CHOICES.measure) &&
    sameList(c.relative_to, DEFAULT_CHOICES.relative_to) && c.grain.length === GRAIN_LEVELS.length && GRAIN_LEVELS.every(([id]) => c.grain.includes(id))
}

const NONE_CHOSEN: Record<DefinitionField, string> = {
  territories: "Choose at least one way to count territories.", measure: "Choose at least one measure.",
  grain: "Choose at least one level of detail.", relative_to: "Choose at least one thing to set the change against.",
}
export function fieldError(c: DefinitionChoices, field: DefinitionField): string | null {
  return c[field].length === 0 ? NONE_CHOSEN[field] : null
}
/** The first error among the four selectors, or null. */
export function choicesError(c: DefinitionChoices): string | null {
  return (["territories", "measure", "grain", "relative_to"] as const).map(f => fieldError(c, f)).find(e => e !== null) ?? null
}

const optionLabel = <T extends string>(options: [T, string][], id: T): string => options.find(([k]) => k === id)?.[1] ?? id

/** What a question reader proposed, checked field by field. A field the reader left out stays as the form has it.
 *  Each field may be one value or a list; the old measure "both" reads as TRx then NBRx. */
export function proposedChoices(def: ProposedDefinition | null | undefined): { choices: Partial<DefinitionChoices>; fields: DefinitionField[] } | { error: string } {
  const choices: Partial<DefinitionChoices> = {}
  const fields: DefinitionField[] = []
  if (!def) return { choices, fields }
  const take = (field: DefinitionField, raw: unknown, options: [string, string][], what: string): string | null => {
    if (raw == null) return null
    const list = asList(raw as string | string[])
    if (list.length === 0 || list.some(v => !options.some(([id]) => id === v))) return `The proposed ${what} are not valid choices.`
    Object.assign(choices, { [field]: list })
    fields.push(field)
    return null
  }
  const measure = def.measure == null ? null : asList(def.measure as string | string[]).flatMap(m => m === "both" ? ["trx", "nbrx"] : [m])
  const problem = take("territories", def.territories, TERRITORY_OPTIONS, "territories counted") ?? take("measure", measure, MEASURE_OPTIONS, "measures") ??
    take("grain", def.grain, GRAIN_LEVELS, "levels of detail") ?? take("relative_to", def.relative_to, RELATIVE_OPTIONS, "comparison bases")
  return problem ? { error: problem } : { choices, fields }
}

export function comparisonWords(c: Comparison | null | undefined, labelWeek: (iso: string) => string = w => w): string {
  if (!c) return "the previous 4 weeks"
  if (c.kind === "previous") return `the previous ${c.weeks} week${c.weeks === 1 ? "" : "s"}`
  if (c.kind === "last_year") return "the same weeks last year"
  if (c.kind === "pre_launch") return "the four weeks before Metacora launched"
  return c.start && c.end ? `the weeks ${labelWeek(c.start)} to ${labelWeek(c.end)}` : "named weeks"
}

/** Every chosen value in words, the primary first and marked when there are several. */
function listWords(words: string[]): string {
  return words.length > 1 ? words.map((w, i) => i === 0 ? `${w} (primary)` : w).join("; ") : words[0] ?? ""
}

/** A stored definition in words, one line per choice, for the Assumptions block. No SQL, no arguments. A definition
 *  stored with single values reads as lists of one. */
export function definitionLines(d: BriefDefinition, labelWeek: (iso: string) => string = w => w): [string, string][] {
  const lines: [string, string][] = []
  if (d.first_week) lines.push(["Period", d.last_week && d.last_week > d.first_week ? `weeks ${labelWeek(d.first_week)} to ${labelWeek(d.last_week)}` : `week of ${labelWeek(d.first_week)}`])
  const comparisons = asList(d.comparison)
  lines.push(["Compared with", listWords(comparisons.length ? comparisons.map(c => comparisonWords(c, labelWeek)) : [comparisonWords(null)])])
  lines.push(["Territories counted", listWords(asList(d.territories).map(t => optionLabel(TERRITORY_OPTIONS, t)))])
  const measures = asList(d.measure as string | string[]).flatMap(m => m === "both" ? ["trx", "nbrx"] : [m]) as MeasureChoice[]
  lines.push(["Measure", listWords(measures.map(m => optionLabel(MEASURE_OPTIONS, m)))])
  const grain = asList(d.grain)
  lines.push(["Detail", listWords((grain.length ? grain : GRAIN_LEVELS.map(([id]) => id)).map(g => optionLabel(GRAIN_LEVELS, g).toLowerCase()))])
  lines.push(["Set against", listWords(asList(d.relative_to).map(r => r === "none" ? "nothing" : optionLabel(RELATIVE_OPTIONS, r).toLowerCase()))])
  return lines
}

/** The stored definition as a short list. The Memo shows it in the Assumptions block, in both views. */
export function DefinitionWords({ definition, labelWeek }: { definition: BriefDefinition; labelWeek?: (iso: string) => string }) {
  return <div className="mt-3 rounded-lg border border-rule bg-sheet/40 px-4 py-3" data-testid="brief-definition">
    <p className="text-xs font-semibold text-ink">Brief definition</p>
    <dl className="mt-1.5 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-0.5 text-xs">
      {definitionLines(definition, labelWeek).map(([k, v]) => <div key={k} className="contents"><dt className="text-muted">{k}</dt><dd className="text-ink">{v}</dd></div>)}
    </dl>
  </div>
}

const SMALL_BTN = "text-xs text-agentdeep hover:underline disabled:cursor-not-allowed disabled:text-muted disabled:no-underline"

export function Proposed({ show }: { show: boolean }) {
  return show ? <span className="ml-2 rounded bg-okbg px-1.5 py-0.5 text-[11px] font-medium text-ok">Proposed, check it</span> : null
}

type MultiProps<T extends string> = {
  label: string
  options: [T, string][]
  value: T[]  // the chosen values in order; the first is the primary
  onChange: (value: T[]) => void
  proposed: boolean
  disabled: boolean
  error: string | null
  id: string
}

/** One or more choices from a list. Ticking adds a value at the end; the first value is the primary, and "Make primary"
 *  moves another value to the front. */
function MultiChoice<T extends string>({ label, options, value, onChange, proposed, disabled, error, id }: MultiProps<T>) {
  const text = (v: T) => optionLabel(options, v)
  return <fieldset className="min-w-0 space-y-1.5" disabled={disabled} aria-describedby={error ? `${id}-error` : undefined}>
    <legend className="text-xs font-medium text-muted">{label}<Proposed show={proposed}/></legend>
    <div className="flex flex-wrap gap-x-4 gap-y-1.5">
      {options.map(([opt, name]) => <label key={opt} className="flex items-center gap-2 text-sm text-ink">
        <input type="checkbox" checked={value.includes(opt)}
          onChange={() => onChange(value.includes(opt) ? value.filter(v => v !== opt) : [...value, opt])}/>{name}</label>)}
    </div>
    {value.length > 1 && <ol className="space-y-0.5 text-xs text-muted" aria-label={`${label}, in order`}>
      {value.map((v, i) => <li key={v} className="flex flex-wrap items-center gap-2">
        <span className="tabular-nums">{i + 1}.</span><span className="text-ink">{text(v)}</span>
        {i === 0 ? <span className="rounded bg-okbg px-1.5 py-0.5 text-[11px] font-medium text-ok">primary</span>
          : <button type="button" className={SMALL_BTN} aria-label={`Make ${text(v)} the primary ${label.toLowerCase()}`}
              onClick={() => onChange([v, ...value.filter(x => x !== v)])}>Make primary</button>}
      </li>)}
    </ol>}
    {error && <p id={`${id}-error`} role="status" className="text-xs text-amber">{error}</p>}
  </fieldset>
}

type Props = {
  value: DefinitionChoices
  onChange: (value: DefinitionChoices, field: DefinitionField) => void
  proposed: DefinitionField[]  // fields the question reader filled; each shows a mark until the analyst changes it
  disabled: boolean
}

/** Territories counted, Measure, Grain and Relative to, each one or more values. Period and Comparison sit above it. */
export function DefinitionPicker({ value, onChange, proposed, disabled }: Props) {
  const set = <F extends DefinitionField>(field: F) => (next: DefinitionChoices[F]) => onChange({ ...value, [field]: next }, field)
  const common = (field: DefinitionField) => ({ proposed: proposed.includes(field), disabled, error: fieldError(value, field), id: `definition-${field}` })
  return <div className="space-y-4">
    <p className="text-xs text-muted">Each choice takes one or more values. The first is the primary: the stories and cards follow it, and the others add labelled figures beside it.</p>
    <div className="grid gap-4 sm:grid-cols-3">
      <MultiChoice label="Territories counted" options={TERRITORY_OPTIONS} value={value.territories} onChange={set("territories")} {...common("territories")}/>
      <MultiChoice label="Measure" options={MEASURE_OPTIONS} value={value.measure} onChange={set("measure")} {...common("measure")}/>
      <MultiChoice label="Relative to" options={RELATIVE_OPTIONS} value={value.relative_to} onChange={set("relative_to")} {...common("relative_to")}/>
    </div>
    <MultiChoice label="Grain" options={GRAIN_LEVELS} value={value.grain} onChange={set("grain")} {...common("grain")}/>
  </div>
}
