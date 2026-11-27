// The Settings workspace (2026-11-27): display choices saved in this browser only (see userSettings.ts). Nothing here
// goes to the server, and nothing here is about the model, notifications or keys.
import { useEffect, useId, useState, type ReactNode } from "react"
import { Notice } from "./agent/primitives"
import { getContext, type Me, type ReleaseContext } from "./agent/briefingApi"
import { forecastContext } from "./agent/forecastApi"
import { APP_VERSION, DEFAULTS, fmtIsoDate, updateSettings, useSettings, type Settings } from "./userSettings"

const PANEL = "pa-panel rounded-xl border border-rule bg-sheet"
const BTN2 = "inline-flex items-center justify-center gap-2 rounded-lg border border-edge px-4 py-2 text-sm font-medium text-ink shadow-[0_3px_0_var(--color-slab)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-paper active:translate-y-[3px] active:shadow-none"
const FIELD = "w-full min-w-0 rounded-lg border border-edge bg-paper px-3.5 py-2.5 text-sm text-ink placeholder:text-muted disabled:opacity-60"

// One setting: a legend, a line of help, and a row of radio buttons drawn as a segmented control (the same look as the
// brief's Analyst view / Leadership preview switch). The radios are real inputs, so arrow keys and screen readers work.
function Choice<T extends string>({ name, legend, hint, value, options, onChange }: { name: string, legend: string, hint?: ReactNode, value: T, options: readonly (readonly [T, string])[], onChange: (v: T) => void }) {
  const hintId = useId()
  // The padding sits on a wrapper: a fieldset's own top padding would land between its legend and its content.
  return <div className="py-4 first:pt-0 last:pb-0"><fieldset className="m-0 min-w-0 border-0 p-0" aria-describedby={hint ? hintId : undefined}>
    <legend className="p-0 text-sm font-semibold">{legend}</legend>
    {hint && <p id={hintId} className="mt-0.5 text-xs text-muted">{hint}</p>}
    <div className="mt-2 inline-flex max-w-full flex-wrap gap-0.5 rounded-lg border border-edge p-0.5">
      {options.map(([v, text]) => <label key={v}
        className={`cursor-pointer rounded-[10px] px-3 py-1.5 text-xs font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary ${value === v ? "bg-primary font-semibold text-onprimary" : "text-muted hover:text-ink"}`}>
        <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} className="sr-only"/>{text}
      </label>)}
    </div>
  </fieldset></div>
}

function Section({ title, note, children }: { title: string, note?: ReactNode, children: ReactNode }) {
  const id = useId()
  return <section aria-labelledby={id} className={`${PANEL} divide-y divide-rule p-6`}>
    <div className="pb-4"><h2 id={id} className="text-lg">{title}</h2>{note && <p className="mt-1 text-xs text-muted">{note}</p>}</div>
    <div className="divide-y divide-rule pt-4">{children}</div>
  </section>
}

const SHORTCUTS: [string[], string][] = [
  [["Ctrl", "B"], "Collapse or expand the sidebar (Cmd B on a Mac; on a phone it opens the menu)"],
  [["Esc"], "Close an open drawer, panel, dialog or the How it works help"],
  [["←", "→"], "Move between the tabs of a row once one is focused; Home and End jump to the first and last"],
  [["Enter"], "In the question box, send the message; Shift Enter starts a new line"],
  [["Tab"], "Move to the next control; Shift Tab goes back. The first stop is Skip to content"],
]

// What the release holds, from whichever context this sign-in can read: Briefing roles read the briefing context, a
// Forecast-only sign-in reads the Forecast one (which has no data version to show).
type Release = { first: string, latest: string, weeks: number, dataVersion: string | null }
function useRelease(me: Me) {
  const [release, setRelease] = useState<Release | null>(null)
  const [brands, setBrands] = useState<ReleaseContext["brands"]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    const done = (r: Release, b: ReleaseContext["brands"]) => { if (live) { setRelease(r); setBrands(b) } }
    const fail = (e: unknown) => { if (live) setError(e instanceof Error ? e.message : String(e)) }
    if (me.lanes.briefing) getContext().then(c => done({ first: c.first_week, latest: c.latest_week, weeks: c.available_weeks.length, dataVersion: c.data_version ?? null }, c.brands), fail)
    else if (me.lanes.forecast?.available) forecastContext().then(c => done({ first: c.available_weeks[0] ?? c.latest_week, latest: c.latest_week, weeks: c.available_weeks.length, dataVersion: null }, []), fail)
    return () => { live = false }
  }, [me])
  return { release, brands, error }
}

export function SettingsWorkspace({ me }: { me: Me }) {
  const s = useSettings()
  const set = (patch: Partial<Settings>) => updateSettings(patch)
  const { release, brands, error } = useRelease(me)
  // Only a role that runs briefs (the Commercial Analyst, and the test sign-in in its analyst view) has a New briefing form to set up.
  const runsBriefs = !!me.lanes.briefing?.actions.includes("run")
  const brand = brands.find(b => b.id === s.defaultBrand) ?? brands[0]
  const agentOffered = !!brand?.engines.includes("agent")
  const engine = agentOffered ? s.defaultEngine : "scripted"
  const dated = (iso: string) => fmtIsoDate(iso)
  return <div className="workspace-content pa-stagger space-y-6 pb-12 pt-8 sm:pt-10">
    <p className="text-sm text-muted">These choices are saved in this browser only, not on your account, so a teammate who shares your sign-in keeps their own.</p>

    <Section title="Appearance">
      <Choice name="theme" legend="Theme" hint="Match system follows your device and changes with it." value={s.theme}
        options={[["light", "Light"], ["dark", "Dark"], ["system", "Match system"]]} onChange={theme => set({ theme })}/>
      <Choice name="motion" legend="Reduce motion" hint="Turns off slides, fades and the sidebar glide. Follow system uses your device's setting." value={s.motion}
        options={[["system", "Follow system"], ["on", "On"], ["off", "Off"]]} onChange={motion => set({ motion })}/>
      <Choice name="density" legend="Density" hint="Compact tightens the space in panels, lists and tables." value={s.density}
        options={[["comfortable", "Comfortable"], ["compact", "Compact"]]} onChange={density => set({ density })}/>
    </Section>

    {runsBriefs && <Section title="New briefing defaults" note="The New briefing form starts on these the next time it loads. The Overview keeps its own brand.">
      <div className="py-4 first:pt-0">
        <label htmlFor="default-brand" className="block text-sm font-semibold">Default brand</label>
        <select id="default-brand" className={`${FIELD} mt-2 max-w-xs`} disabled={!brands.length} value={brand?.id ?? ""} onChange={e => set({ defaultBrand: e.target.value, ...(brands.find(b => b.id === e.target.value)?.engines.includes("agent") ? {} : { defaultEngine: "scripted" as const }) })}>
          {brands.map(b => <option key={b.id} value={b.id}>{b.name} ({b.id})</option>)}
        </select>
        {error && <div className="mt-3"><Notice tone="error" role="alert">{error}</Notice></div>}
      </div>
      <Choice name="engine" legend="Default engine" hint={agentOffered || !brand ? "The scripted engine is the fixed baseline; the agent team investigates in more steps." : "Only the scripted engine is offered for this brand."}
        value={engine} options={agentOffered ? [["scripted", "Scripted"], ["agent", "Agent team"]] : [["scripted", "Scripted"]]} onChange={defaultEngine => set({ defaultEngine })}/>
    </Section>}

    <Section title="Reading">
      <Choice name="date-style" legend="Date style" hint="How weeks and dates read in the app. Briefs keep the server's own text; only the display changes." value={s.dateStyle}
        options={[["long", "Oct 5, 2026"], ["iso", "2026-10-05"]]} onChange={dateStyle => set({ dateStyle })}/>
      <Choice name="footnotes" legend="Evidence footnote numbers" hint="The small numbers beside figures in a brief. Hidden, each figure is still a button that opens its evidence." value={s.footnotes}
        options={[["show", "Show"], ["hide", "Hide"]]} onChange={footnotes => set({ footnotes })}/>
    </Section>

    <Section title="About">
      <dl className="grid gap-x-6 gap-y-3 py-4 text-sm first:pt-0 sm:grid-cols-[11rem_1fr]">
        <dt className="text-muted">Data version</dt><dd className="min-w-0 break-words" data-testid="about-data-version">{release ? release.dataVersion ?? "Not shown for this sign-in" : error ? "Unavailable" : "Loading…"}</dd>
        <dt className="text-muted">Release weeks</dt><dd data-testid="about-weeks">{release ? `${dated(release.first)} to ${dated(release.latest)} (${release.weeks} weeks)` : error ? "Unavailable" : "Loading…"}</dd>
        <dt className="text-muted">App version</dt><dd className="font-mono text-[13px]" data-testid="about-version">{APP_VERSION}</dd>
      </dl>
      <div className="py-4 last:pb-0">
        <h3 className="text-sm font-semibold">Keyboard shortcuts</h3>
        <dl className="mt-3 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[11rem_1fr]">
          {SHORTCUTS.map(([keys, what]) => <div key={what} className="contents">
            <dt className="flex flex-wrap items-center gap-1">{keys.map((k, i) => <span key={k} className="flex items-center gap-1">{i > 0 && <span className="sr-only">then</span>}<kbd className="rounded-md border border-edge bg-paper px-1.5 py-0.5 font-mono text-xs text-ink">{k}</kbd></span>)}</dt>
            <dd className="text-muted">{what}</dd>
          </div>)}
        </dl>
      </div>
    </Section>

    <div><button type="button" className={BTN2} onClick={() => set(DEFAULTS)}>Restore the standard settings</button></div>
  </div>
}
