// The questionnaire responses on the Evaluation page: read-only, for the tester admin. The rows carry the
// pseudonymous participant ID and the role name, never a name or an email; the server answers 403 to anyone else.
import { useEffect, useState } from "react"
import { Notice } from "./agent/primitives"
import { getSurveyResponses, type SurveyResponses } from "./agent/feedbackApi"

const PANEL = "pa-panel rounded-xl border border-rule bg-sheet"
const cell = (v: unknown) => typeof v === "number" ? String(v) : "–"
const text = (v: unknown) => typeof v === "string" && v ? v : "–"
const stamp = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })

export function FeedbackResponses() {
  const [r, setR] = useState<SurveyResponses | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { getSurveyResponses().then(setR).catch(e => setError(e instanceof Error ? e.message : String(e))) }, [])
  const figures: [string, string][] = r ? [
    ["Responses", String(r.responses)],
    ["Usability (UMUX-Lite, SUS-equivalent)", r.umux ? r.umux.sus_equivalent_mean.toFixed(1) : "–"],
    ["Net promoter score", r.nps ? String(r.nps.nps) : "–"],
  ] : []
  return <section aria-label="Questionnaire responses" className="space-y-3">
    {error && <Notice tone="error" role="alert">{error}</Notice>}
    {r && <>
      <div className={`${PANEL} grid grid-cols-1 sm:grid-cols-3`}>
        {figures.map(([k, v], i) => <div key={k} className={`p-5 ${i ? "border-t border-rule sm:border-l sm:border-t-0" : ""}`}>
          <div className="text-xs text-muted">{k}</div><div className="mt-2 font-serif text-3xl tabular-nums">{v}</div>
        </div>)}
      </div>
      {r.umux && <p className="text-xs text-muted">UMUX-Lite uses the {r.umux.n} {r.umux.n === 1 ? "response" : "responses"} that answered both usability items.</p>}
      {r.rows.length === 0 ? <p className="text-sm text-muted">No responses yet.</p> : <div className={`${PANEL} overflow-x-auto`}>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-muted"><tr>
            <th className="px-4 py-2 font-medium">Time</th><th className="pr-4 font-medium">Role</th><th className="pr-4 font-medium">Meets needs</th>
            <th className="pr-4 font-medium">Easy to use</th><th className="pr-4 font-medium">Numbers traceable</th><th className="pr-4 font-medium">Recommend</th><th className="pr-4 font-medium">One thing to change</th>
          </tr></thead>
          <tbody>{r.rows.map(row => <tr key={row.user} className="border-t border-rule align-top">
            <td className="whitespace-nowrap px-4 py-2 tabular-nums">{stamp(row.ts)}</td><td className="whitespace-nowrap pr-4 py-2">{row.role}</td>
            <td className="pr-4 py-2 tabular-nums">{cell(row.answers.umux_needs)}</td><td className="pr-4 py-2 tabular-nums">{cell(row.answers.umux_easy)}</td>
            <td className="pr-4 py-2 tabular-nums">{cell(row.answers.t_trace)}</td><td className="pr-4 py-2 tabular-nums">{cell(row.answers.o_nps)}</td>
            <td className="min-w-64 pr-4 py-2">{text(row.answers.o_change)}</td>
          </tr>)}</tbody>
        </table>
      </div>}
    </>}
  </section>
}
