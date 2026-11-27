// The Marketer's promotion panel (v2, Michael 2026-11-27): the promotion read under a territory story and the budget note
// after the stories. Everything shown arrives from the server; nothing here computes a number. The range is never a
// return on spend.
import { longDates } from "./agent/primitives"
import type { PromotionRead, PromotionMeasure } from "./agent/briefingApi"

const SEPARABLE: Record<string, string> = {access: "access", competitor: "the competitor launch", holiday: "the calendar"}

function list(words: string[]): string {
  return words.length < 2 ? words.join("") : `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`
}

// The verdict in plain words. An unknown verdict shows no claim at all.
function verdictLine(p: PromotionRead): {lead: string, rest: string} | null {
  switch (p.verdict) {
    case "supported": return {lead: "Supported", rest: `TRx followed the change in promotion (read at the ${p.lag_label}).`}
    case "ruled_out": return {lead: "Ruled out", rest: "a channel moved and TRx did not follow."}
    case "not_testable": return {lead: "Not testable", rest: "activity held level, so its effect cannot be measured this period."}
    case "not_separable": return {lead: "Cannot be separated", rest: `from ${list((p.separable_from ?? []).map(x => SEPARABLE[x] ?? x))}, which moved in the same weeks.`}
    case "within_range": return {lead: "Not credited", rest: "the territory moved within its normal range."}
    default: return null
  }
}

const CELL = "px-1.5 sm:px-2.5 py-1.5"

// Wide enough, the rows are table rows. On a phone each row stacks into a block (the name and the change on one line, the
// figures and the marker under it), so nothing is cut off and nothing scrolls sideways.
function Row({label, m, moved}: {label: string, m: PromotionMeasure, moved?: boolean}) {
  return <tr role="row" className="border-b border-rule/60 align-baseline max-sm:grid max-sm:grid-cols-[1fr_auto] max-sm:gap-x-3 max-sm:py-2">
    <th scope="row" role="rowheader" className={`${CELL} text-left font-medium text-ink max-sm:col-start-1 max-sm:row-start-1 max-sm:px-0 max-sm:py-0`}>{label}</th>
    <td role="cell" className={`${CELL} whitespace-nowrap text-right text-ink max-sm:col-start-1 max-sm:row-start-2 max-sm:px-0 max-sm:py-0 max-sm:text-left`}>{m.before} <span aria-hidden="true" className="text-muted">→</span><span className="sr-only"> to </span> {m.after}</td>
    <td role="cell" className={`${CELL} whitespace-nowrap text-right text-ink max-sm:col-start-2 max-sm:row-start-1 max-sm:px-0 max-sm:py-0`}>{m.change ? `${m.direction} ${m.change}` : m.direction}</td>
    <td role="cell" className={`${CELL} text-left max-sm:col-start-2 max-sm:row-start-2 max-sm:px-0 max-sm:py-0 max-sm:text-right`}>{moved && <span className="rounded-full border border-rule px-2 py-0.5 text-[11px] text-muted">moved</span>}</td>
  </tr>
}

const title = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

export function PromotionPanel({promotion: p, id}: {promotion: PromotionRead, id: string}) {
  const verdict = verdictLine(p)
  return <section aria-labelledby={id} data-testid="promotion-panel" className="pa-promotion mt-4 break-inside-avoid-page rounded-lg border border-rule bg-paper/60 p-4">
    <h5 id={id} className="font-sans text-[11px] font-medium uppercase tracking-wider text-muted">Promotion</h5>
    {verdict && <p data-testid="promotion-verdict" className="mt-1.5 max-w-[68ch] font-sans text-[15px] leading-snug text-ink"><span className="font-semibold">{verdict.lead}:</span> {verdict.rest}</p>}
    <p className="mt-3 font-sans text-[12px] text-muted sm:hidden">Weekly averages: before → after, and the change.</p>
    <div className="mt-3 overflow-x-auto max-sm:mt-1" tabIndex={0} role="region" aria-label="Promotion figures">
      {/* Explicit roles: on a phone the rows are blocks and grids, which can drop a table's semantics; the roles keep it a table */}
      <table role="table" className="w-full border-collapse max-sm:block font-sans text-[13px] tabular-nums">
        <caption className="sr-only">New patients, TRx and the four promotion channels, comparison weeks against this period, weekly averages</caption>
        <thead role="rowgroup" className="max-sm:sr-only"><tr role="row" className="border-b border-rule">
          <th scope="col" role="columnheader" className={`${CELL} text-left text-[11px] font-medium text-muted`}>Weekly average</th>
          <th scope="col" role="columnheader" className={`${CELL} text-right text-[11px] font-medium text-muted`}>Before → after</th>
          <th scope="col" role="columnheader" className={`${CELL} text-right text-[11px] font-medium text-muted`}>Change</th>
          <th scope="col" role="columnheader" className="px-1.5 sm:px-2.5 py-1.5"><span className="sr-only">Moved</span></th>
        </tr></thead>
        <tbody role="rowgroup" className="max-sm:block">
          <Row label="New patients (NBRx)" m={p.new_patients}/>
          <Row label="TRx" m={p.trx}/>
          {p.channels.map(c => <Row key={c.channel} label={title(c.channel)} m={c} moved={c.moved}/>)}
        </tbody>
      </table>
    </div>
    <p className="mt-2 font-sans text-[12px] leading-snug text-muted">Read at the {p.lag_label}. Re-check after {longDates(p.recheck)}.</p>
    {p.effect && <div data-testid="promotion-effect" className="mt-3 border-t border-rule pt-3">
      <p className="max-w-[68ch] font-sans text-[14px] leading-snug text-ink">Compared with {p.effect.territories} territories without a promotion change: {p.effect.phrase}.</p>
      <p className="mt-1 font-sans text-[12px] leading-snug text-muted">This is a range across those territories, not a return on spend.</p>
    </div>}
  </section>
}

export function BudgetNote({text}: {text: string}) {
  return <aside data-testid="budget-note" aria-label="The budget question" className="pa-noprint mt-6 max-w-[68ch] border-l-2 border-edge pl-4">
    <p className="font-sans text-[11px] font-medium uppercase tracking-wider text-muted">The budget question</p>
    <p className="mt-1 font-sans text-[14px] leading-[1.55] text-ink">{text}</p>
  </aside>
}
