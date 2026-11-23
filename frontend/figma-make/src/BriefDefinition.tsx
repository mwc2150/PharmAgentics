import type { BriefDefinition, Comparison, GrainLevel, MeasureChoice, RelativeTo, TerritoriesCounted } from "./agent/briefingApi"

// brief-010 FR-000b: the four selectors of the brief definition that the period and comparison pickers do not cover
// (territories counted, measure, grain, relative to), the words that state a whole definition, and the checks on a
// definition the question reader proposes. Every selector has a pre-selected value; nothing is locked or hidden.

export type DefinitionChoices = { territories: TerritoriesCounted; measure: MeasureChoice; grain: GrainLevel[]; relative_to: RelativeTo }
export type DefinitionField = "territories" | "measure" | "grain" | "relative_to"

export const GRAIN_LEVELS: [GrainLevel, string][] = [
  ["national", "National"], ["territory", "Territory"], ["plan", "Plan"], ["channel", "Channel"], ["specialty", "Specialty"],
]
export const TERRITORY_OPTIONS: [TerritoriesCounted, string][] = [
  ["like_for_like", "Like for like"], ["all_reportable", "All reportable"], ["projected", "Projected national"],
]
export const MEASURE_OPTIONS: [MeasureChoice, string][] = [["trx", "TRx"], ["nbrx", "NBRx (new patients)"], ["both", "Both"]]
export const RELATIVE_OPTIONS: [RelativeTo, string][] = [["other_territories", "The other territories"], ["national", "National"], ["none", "Nothing"]]

/** The pre-selected values. They reproduce the brief made before brief-010. */
export const DEFAULT_CHOICES: DefinitionChoices = {
  territories: "like_for_like", measure: "trx", grain: GRAIN_LEVELS.map(([id]) => id), relative_to: "other_territories",
}

/** True when the choices are the pre-selected ones. */
export function isDefaultChoices(c: DefinitionChoices): boolean {
  return c.territories === DEFAULT_CHOICES.territories && c.measure === DEFAULT_CHOICES.measure &&
    c.relative_to === DEFAULT_CHOICES.relative_to && c.grain.length === GRAIN_LEVELS.length && GRAIN_LEVELS.every(([id]) => c.grain.includes(id))
}

export function choicesError(c: DefinitionChoices): string | null {
  return c.grain.length === 0 ? "Choose at least one level of detail." : null
}

const optionLabel = <T extends string>(options: [T, string][], id: T): string => options.find(([k]) => k === id)?.[1] ?? id

/** What a question reader proposed, checked field by field. A field the reader left out stays as the form has it. */
export function proposedChoices(def: Partial<BriefDefinition> | null | undefined): { choices: Partial<DefinitionChoices>; fields: DefinitionField[] } | { error: string } {
  const choices: Partial<DefinitionChoices> = {}
  const fields: DefinitionField[] = []
  if (!def) return { choices, fields }
  if (def.territories != null) {
    if (!TERRITORY_OPTIONS.some(([id]) => id === def.territories)) return { error: "The proposed territories counted are not one of the choices." }
    choices.territories = def.territories; fields.push("territories")
  }
  if (def.measure != null) {
    if (!MEASURE_OPTIONS.some(([id]) => id === def.measure)) return { error: "The proposed measure is not one of the choices." }
    choices.measure = def.measure; fields.push("measure")
  }
  if (def.grain != null) {
    const known = new Set<string>(GRAIN_LEVELS.map(([id]) => id))
    if (!Array.isArray(def.grain) || def.grain.length === 0 || def.grain.some(g => !known.has(g))) return { error: "The proposed levels of detail are not valid." }
    choices.grain = GRAIN_LEVELS.map(([id]) => id).filter(id => def.grain!.includes(id)); fields.push("grain")
  }
  if (def.relative_to != null) {
    if (!RELATIVE_OPTIONS.some(([id]) => id === def.relative_to)) return { error: "The proposed comparison basis is not one of the choices." }
    choices.relative_to = def.relative_to; fields.push("relative_to")
  }
  return { choices, fields }
}

export function comparisonWords(c: Comparison | null | undefined, labelWeek: (iso: string) => string = w => w): string {
  if (!c) return "the previous 4 weeks"
  if (c.kind === "previous") return `the previous ${c.weeks} week${c.weeks === 1 ? "" : "s"}`
  if (c.kind === "last_year") return "the same weeks last year"
  if (c.kind === "pre_launch") return "the four weeks before Metacora launched"
  return c.start && c.end ? `the weeks ${labelWeek(c.start)} to ${labelWeek(c.end)}` : "named weeks"
}

/** A stored definition in words, one line per choice, for the Assumptions block. No SQL, no arguments. */
export function definitionLines(d: BriefDefinition, labelWeek: (iso: string) => string = w => w): [string, string][] {
  const grain = (d.grain?.length ? GRAIN_LEVELS.filter(([id]) => d.grain.includes(id)) : GRAIN_LEVELS).map(([, label]) => label.toLowerCase())
  const lines: [string, string][] = []
  if (d.first_week) lines.push(["Period", d.last_week && d.last_week > d.first_week ? `weeks ${labelWeek(d.first_week)} to ${labelWeek(d.last_week)}` : `week of ${labelWeek(d.first_week)}`])
  lines.push(["Compared with", comparisonWords(d.comparison, labelWeek)])
  lines.push(["Territories counted", optionLabel(TERRITORY_OPTIONS, d.territories)])
  lines.push(["Measure", optionLabel(MEASURE_OPTIONS, d.measure)])
  lines.push(["Detail", grain.length === GRAIN_LEVELS.length ? "all five levels (national, territory, plan, channel, specialty)" : grain.join(", ")])
  lines.push(["Set against", d.relative_to === "none" ? "nothing" : optionLabel(RELATIVE_OPTIONS, d.relative_to).toLowerCase()])
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

const FIELD = "w-full min-w-0 rounded-lg border border-rule bg-paper px-3 py-2.5 text-sm text-ink disabled:opacity-60"
const LABEL = "flex flex-col gap-1.5 text-xs font-medium text-muted"

function Proposed({ show }: { show: boolean }) {
  return show ? <span className="ml-2 rounded bg-okbg px-1.5 py-0.5 text-[11px] font-medium text-ok">Proposed, check it</span> : null
}

type Props = {
  value: DefinitionChoices
  onChange: (value: DefinitionChoices, field: DefinitionField) => void
  proposed: DefinitionField[]  // fields the question reader filled; each shows a mark until the analyst changes it
  disabled: boolean
}

/** Territories counted, Measure, Grain and Relative to. Period and Comparison sit above it in the same form. */
export function DefinitionPicker({ value, onChange, proposed, disabled }: Props) {
  const error = choicesError(value)
  const toggle = (id: GrainLevel) => {
    const next = value.grain.includes(id) ? value.grain.filter(g => g !== id) : [...value.grain, id]
    onChange({ ...value, grain: GRAIN_LEVELS.map(([g]) => g).filter(g => next.includes(g)) }, "grain")
  }
  return <div className="space-y-4">
    <div className="grid gap-4 sm:grid-cols-3">
      <label className={LABEL}><span>Territories counted<Proposed show={proposed.includes("territories")}/></span>
        <select className={FIELD} value={value.territories} disabled={disabled}
          onChange={e => onChange({ ...value, territories: e.target.value as TerritoriesCounted }, "territories")}>
          {TERRITORY_OPTIONS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </label>
      <label className={LABEL}><span>Measure<Proposed show={proposed.includes("measure")}/></span>
        <select className={FIELD} value={value.measure} disabled={disabled}
          onChange={e => onChange({ ...value, measure: e.target.value as MeasureChoice }, "measure")}>
          {MEASURE_OPTIONS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </label>
      <label className={LABEL}><span>Relative to<Proposed show={proposed.includes("relative_to")}/></span>
        <select className={FIELD} value={value.relative_to} disabled={disabled}
          onChange={e => onChange({ ...value, relative_to: e.target.value as RelativeTo }, "relative_to")}>
          {RELATIVE_OPTIONS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </label>
    </div>
    <fieldset className="space-y-1.5" disabled={disabled} aria-describedby={error ? "grain-error" : undefined}>
      <legend className="text-xs font-medium text-muted">Grain<Proposed show={proposed.includes("grain")}/></legend>
      <div className="flex flex-wrap gap-x-5 gap-y-2">
        {GRAIN_LEVELS.map(([id, label]) => <label key={id} className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={value.grain.includes(id)} onChange={() => toggle(id)}/>{label}</label>)}
      </div>
      {error && <p id="grain-error" role="status" className="text-xs text-amber">{error}</p>}
    </fieldset>
  </div>
}
