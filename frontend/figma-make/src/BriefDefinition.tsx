import type { BriefDefinition, Comparison, GrainLevel, MeasureChoice, ProposedDefinition, RelativeTo, TerritoriesCounted } from "./agent/briefingApi"

// brief-010 FR-000b and FR-000e: the selectors of the brief definition that the period and comparison pickers do not
// cover (territories counted, measure, grain, relative to), the words that state a whole definition, and the checks on
// a definition the question reader proposes. Each selector takes one or more values; the first drives the stories and
// cards (the form calls it Main), the rest add labelled figures beside it ("Also show beside it"). Grain has no main:
// the server sorts it into a fixed order, so it is plain checkboxes. Every selector has a pre-selected value; nothing
// is locked or hidden.

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

// What each choice does, in plain words, shown beside it on the form.
const TERRITORY_NOTES: Record<TerritoriesCounted, string> = {
  like_for_like: "Only territories that report in both periods",
  all_reportable: "Every territory that reports in each period, counted separately",
  projected: "Fills in territories whose feed is incomplete",
}
const MEASURE_NOTES: Record<MeasureChoice, string> = { trx: "All prescriptions", nbrx: "Patients new to the brand" }
const RELATIVE_NOTES: Record<RelativeTo, string> = {
  other_territories: "Each territory's change against the rest", national: "Against the national change", none: "Each change stated alone",
}
const GRAIN_NOTES: Record<GrainLevel, string> = {
  national: "The KPI strip, the trend chart and the Metacora story", territory: "The territory table and territory stories",
  plan: "Payer-plan cards", channel: "Percent change by payer channel", specialty: "Percent change by prescriber specialty",
}

/** A value or a list as a list, without repeats, in the order given. */
export function asList<T>(value: T | T[] | null | undefined): T[] {
  const list = value == null ? [] : Array.isArray(value) ? value : [value]
  return list.filter((v, i) => list.indexOf(v) === i)
}

const sameList = <T,>(a: T[], b: T[]) => a.length === b.length && a.every((v, i) => v === b[i])

/** True when the choices are the pre-selected ones (the grain in any order: the server sorts it). */
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

/** Every chosen value in words: the main one first, then "also" the others. */
function listWords(words: string[]): string {
  return words.length > 1 ? `${words[0]}; also ${words.slice(1).join(", ")}` : words[0] ?? ""
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
  lines.push(["Detail", (grain.length ? grain : GRAIN_LEVELS.map(([id]) => id)).map(g => optionLabel(GRAIN_LEVELS, g).toLowerCase()).join(", ")])  // no main: grain order means nothing
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

export function Proposed({ show }: { show: boolean }) {
  return show ? <span className="ml-2 text-xs font-normal text-muted">proposed, check it</span> : null
}

type Shared = { label: string; proposed: boolean; disabled: boolean; error: string | null; id: string }

type MainProps<T extends string> = Shared & {
  options: [T, string][]
  notes: Record<T, string>
  value: T[]  // [main, ...extras]: the shape the server takes
  onChange: (value: T[]) => void
}

/** An option's description, out of the way until it is wanted (Michael, 2026-11-27): shown in gray under the option
 *  while it is hovered or focused (keyboard, or a tap on a phone). It stays the input's accessible description
 *  (aria-describedby), so a screen reader reads it whether or not it is on screen. */
function OptionNote({ id, text }: { id: string; text: string }) {
  return <span id={id} role="tooltip" className="pointer-events-none invisible absolute left-6 top-full z-30 mt-1 w-max max-w-64 rounded-lg border border-rule bg-paper px-2.5 py-1.5 text-xs text-muted opacity-0 shadow-lg transition-opacity duration-150 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100 motion-reduce:transition-none">{text}</span>
}

/** One main choice (radios, each with what it does) and, under "Also show beside it", the others as checkboxes. A new
 *  main replaces the old one and leaves the extras; the value sent is still [main, ...extras] (brief-010 FR-000e). */
function MainChoice<T extends string>({ label, options, notes, value, onChange, proposed, disabled, error, id }: MainProps<T>) {
  const main = value[0]
  const extras = value.slice(1)
  const others = options.filter(([opt]) => opt !== main)
  return <fieldset className="min-w-0 space-y-3" disabled={disabled} aria-describedby={error ? `${id}-error` : undefined}>
    <legend className="text-xs font-medium text-muted">{label}<Proposed show={proposed}/></legend>
    <fieldset className="space-y-1.5">
      <legend className="mb-1 text-xs text-muted">Main</legend>
      {options.map(([opt, name]) => <label key={opt} className="group relative flex w-fit items-center gap-2">
        <input type="radio" name={`${id}-main`} checked={main === opt} aria-describedby={`${id}-${opt}-note`}
          onChange={() => onChange([opt, ...extras.filter(v => v !== opt)])}/>
        <span className="text-sm text-ink">{name}</span><OptionNote id={`${id}-${opt}-note`} text={notes[opt]}/>
      </label>)}
    </fieldset>
    {main !== undefined && others.length > 0 && <fieldset className="space-y-1.5">
      <legend className="mb-1 text-xs text-muted">Also show beside it</legend>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {others.map(([opt, name]) => <label key={opt} className="group relative flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={extras.includes(opt)} aria-describedby={`${id}-${opt}-extra-note`}
            onChange={() => onChange(extras.includes(opt) ? [main, ...extras.filter(v => v !== opt)] : [main, ...extras, opt])}/>{name}
          <OptionNote id={`${id}-${opt}-extra-note`} text={notes[opt]}/></label>)}
      </div>
    </fieldset>}
    {error && <p id={`${id}-error`} role="status" className="text-xs text-neg">{error}</p>}
  </fieldset>
}

/** Grain: which levels of detail the brief carries. Plain checkboxes, each with what it adds. */
function GrainChoice({ value, onChange, label, proposed, disabled, error, id }: Shared & { value: GrainLevel[]; onChange: (value: GrainLevel[]) => void }) {
  return <fieldset className="min-w-0 space-y-1.5" disabled={disabled} aria-describedby={error ? `${id}-error` : undefined}>
    <legend className="mb-1 text-xs font-medium text-muted">{label}<Proposed show={proposed}/></legend>
    {GRAIN_LEVELS.map(([level, name]) => <label key={level} className="group relative flex w-fit items-center gap-2">
      <input type="checkbox" checked={value.includes(level)} aria-describedby={`${id}-${level}-note`}
        onChange={() => onChange(value.includes(level) ? value.filter(v => v !== level) : [...value, level])}/>
      <span className="text-sm text-ink">{name}</span><OptionNote id={`${id}-${level}-note`} text={GRAIN_NOTES[level]}/>
    </label>)}
    {error && <p id={`${id}-error`} role="status" className="text-xs text-neg">{error}</p>}
  </fieldset>
}

type Props = {
  value: DefinitionChoices
  onChange: (value: DefinitionChoices, field: DefinitionField) => void
  proposed: DefinitionField[]  // fields the question reader filled; each shows a mark until the analyst changes it
  disabled: boolean
}

/** Territories counted, Measure and Relative to (a main choice and extras), and Grain (checkboxes). Period and
 *  Comparison sit above it. */
export function DefinitionPicker({ value, onChange, proposed, disabled }: Props) {
  const set = <F extends DefinitionField>(field: F) => (next: DefinitionChoices[F]) => onChange({ ...value, [field]: next }, field)
  const common = (field: DefinitionField, label: string) => ({ label, proposed: proposed.includes(field), disabled, error: fieldError(value, field), id: `definition-${field}` })
  return <div className="space-y-4">
    <p className="text-xs text-muted">The main choice drives the stories and cards. Anything you also show adds labelled figures beside it.</p>
    <div className="grid gap-6 lg:grid-cols-3">
      <MainChoice options={TERRITORY_OPTIONS} notes={TERRITORY_NOTES} value={value.territories} onChange={set("territories")} {...common("territories", "Territories counted")}/>
      <MainChoice options={MEASURE_OPTIONS} notes={MEASURE_NOTES} value={value.measure} onChange={set("measure")} {...common("measure", "Measure")}/>
      <MainChoice options={RELATIVE_OPTIONS} notes={RELATIVE_NOTES} value={value.relative_to} onChange={set("relative_to")} {...common("relative_to", "Relative to")}/>
    </div>
    <GrainChoice value={value.grain} onChange={set("grain")} {...common("grain", "Grain")}/>
  </div>
}
