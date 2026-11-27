// UAT feedback (core-008): for every generated answer, thumbs up or down and then the session rating
// (good, fine, bad), one question at a time in a card on top of the question bar; and the platform questionnaire, opened from the sidebar or the account menu.
// The server stores everything under a pseudonymous ID; this file only collects it and shows what has been given.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import { createPortal } from "react-dom"
import { toast } from "sonner"
import { Icon, Notice } from "./agent/primitives"
import {
  getFeedbackStatus, getMyVote, getMySurvey, getQuestionnaire, sendComment, sendPulse, sendSurvey, sendVote,
  type AnswerLane, type AnswerView, type Answers, type FeedbackStatus, type PulseWhere, type QItem, type Questionnaire,
  type CommentTopic, type Rating, type Vote,
} from "./agent/feedbackApi"

const message = (e: unknown) => e instanceof Error ? e.message : String(e)
// Mirror BTN, BTN2 and FIELD in App.tsx (not exported from there): keep the strings in step.
const BTN = "inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-onprimary shadow-[0_4px_0_var(--color-primarydeep)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-primaryhover active:translate-y-[3px] active:shadow-[0_1px_0_var(--color-primarydeep)] disabled:cursor-not-allowed disabled:bg-rule disabled:text-muted disabled:shadow-none"
const BTN2 = "inline-flex items-center justify-center gap-2 rounded-lg border border-edge px-4 py-2 text-sm font-medium text-ink shadow-[0_3px_0_var(--color-slab)] transition-[background-color,transform,box-shadow] duration-150 hover:bg-paper active:translate-y-[2px] active:shadow-[0_1px_0_var(--color-slab)] disabled:cursor-not-allowed disabled:text-muted disabled:shadow-none"
const FIELD = "w-full min-w-0 rounded-lg border border-edge bg-paper px-3.5 py-2.5 text-sm text-ink"
const CLOSE = "grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-paper hover:text-ink"
const LABEL: Record<Rating, string> = { good: "Good", fine: "Fine", bad: "Bad" }
const TONE: Record<Rating, string> = { good: "text-ok", fine: "text-amber", bad: "text-neg" }
const RATINGS: Rating[] = ["good", "fine", "bad"]

function Face({ kind, className = "h-5 w-5" }: { kind: Rating; className?: string }) {
  const mouth = kind === "good" ? "M8 14.5c1 1.4 2.3 2 4 2s3-.6 4-2" : kind === "fine" ? "M8.5 15.5h7" : "M8 16.5c1-1.4 2.3-2 4-2s3 .6 4 2"
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="9" /><path d="M9 10h.01M15 10h.01" /><path d={mouth} />
  </svg>
}

type Ctx = {
  status: FeedbackStatus | null
  openSurvey: () => void
  openSuggest: () => void
  signOut: () => void
  setPulse: (p: { rating: Rating; at: string }) => void
  where: PulseWhere
  inlineShown: number  // how many follow-up answers show their own vote card right now
  trackInline: (delta: 1 | -1) => void
}
const FeedbackCtx = createContext<Ctx | null>(null)
function useFeedback(): Ctx {
  const c = useContext(FeedbackCtx)
  if (!c) throw new Error("Feedback controls must be used inside FeedbackProvider")
  return c
}
// For the account menu: open the questionnaire, sign out, and whether the questionnaire is done.
export function useFeedbackActions() {
  const f = useFeedback()
  return { openSurvey: f.openSurvey, openSuggest: f.openSuggest, signOut: f.signOut, surveyDone: Boolean(f.status?.survey.submitted_at) }
}

export function FeedbackProvider({ where, children }: { where: PulseWhere; children: ReactNode }) {
  const [status, setStatus] = useState<FeedbackStatus | null>(null)
  const [surveyOpen, setSurveyOpen] = useState(false)
  const [suggestOpen, setSuggestOpen] = useState(false)
  const [inlineShown, setInlineShown] = useState(0)
  const trackInline = useCallback((delta: 1 | -1) => setInlineShown(n => Math.max(0, n + delta)), [])
  const refresh = useCallback(() => { getFeedbackStatus().then(setStatus).catch(() => setStatus(null)) }, [])
  useEffect(() => { refresh() }, [refresh])
  const ctx = useMemo<Ctx>(() => ({
    status, where,
    openSurvey: () => { setSuggestOpen(false); setSurveyOpen(true) },
    openSuggest: () => setSuggestOpen(true),
    signOut: () => window.location.assign("/auth/logout"),  // never asks for a rating (core-008 FR-003)
    setPulse: p => setStatus(s => s ? { ...s, pulse: p } : s),
    inlineShown, trackInline,
  }), [status, where, inlineShown, trackInline])
  return <FeedbackCtx.Provider value={ctx}>
    {children}
    {surveyOpen && <SurveyModal onClose={() => setSurveyOpen(false)} onSubmitted={refresh} />}
    {suggestOpen && <SuggestModal onClose={() => setSuggestOpen(false)} onSurvey={() => { setSuggestOpen(false); setSurveyOpen(true) }} surveyDone={Boolean(status?.survey.submitted_at)} />}
  </FeedbackCtx.Provider>
}

// The questionnaire invitation, quietly, at the foot of the sidebar: a dot until it is answered.
export function ShareFeedbackLink({ expanded, onOpen }: { expanded: boolean; onOpen?: () => void }) {
  const f = useFeedback()
  const pending = Boolean(f.status && !f.status.survey.submitted_at)
  return <button type="button" onClick={() => { onOpen?.(); f.openSuggest() }} title="Suggest an improvement or take the questionnaire"
    className="relative flex w-full items-center gap-3 rounded-xl px-[10px] py-2 text-left text-xs text-muted transition hover:bg-paper/60 hover:text-ink">
    <span className="relative shrink-0">
      <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" /></svg>
      {pending && <span aria-hidden="true" className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-primary ring-2 ring-sheet" />}
    </span>
    <span className={expanded ? "whitespace-nowrap" : "sr-only"}>Share feedback</span>{pending && <span className="sr-only"> (the questionnaire is not answered yet)</span>}
  </button>
}

// --- feedback on one answer: a small card on top of the question bar -------------------------------
// Two steps, one at a time: "Was this answer right?" (thumbs, then an optional note); then, for an agent answer
// when the session has no rating yet, "How is the agent team working for you this session?" (good, fine, bad,
// then an optional note). The card closes when both are done, or when it is dismissed. The mistakes notice is
// not repeated here: the page footer carries it.

// Where the card goes: the Weekly briefing puts a slot directly above its question bar. With no slot (a page
// without the bar) the card floats at the bottom of the window instead.
const DockSlot = createContext<HTMLElement | null>(null)
export function FeedbackDock({ slot, children }: { slot: HTMLElement | null; children: ReactNode }) {
  return <DockSlot.Provider value={slot}>{children}</DockSlot.Provider>
}
const dismissed = new Set<string>()  // answers whose card was closed in this tab; reopening the answer does not bring it back

const THUMB = "M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"
function Thumb({ down = false }: { down?: boolean }) {
  return <svg viewBox="0 0 24 24" className={`h-4 w-4 ${down ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={THUMB} /></svg>
}
const THUMB_BTN = "grid h-9 w-9 place-items-center rounded-lg border border-edge text-muted transition-colors hover:bg-paper hover:text-ink disabled:opacity-60"
const CHOICE = "flex items-center gap-1.5 rounded-lg border border-edge px-3 py-2 text-xs font-medium text-ink transition-colors hover:bg-paper disabled:opacity-60"

// "voted": a vote was already given (an earlier visit); the next step depends on the session rating.
type Step = "loading" | "vote" | "vote-note" | "voted" | "session" | "session-note" | "done"

export function AnswerFeedback({ lane, refId, view, agent = false, inline = false }: { lane: AnswerLane; refId: string; view: AnswerView; agent?: boolean; inline?: boolean }) {
  const f = useFeedback()
  const slot = useContext(DockSlot)
  const key = `${lane}|${refId}|${view}`
  const [step, setStep] = useState<Step>("loading")
  const [vote, setVote] = useState<Vote | null>(null)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // The session question: only for an agent answer, once per session, and only when the feedback service answers.
  const wantsSession = agent && !!f.status && !f.status.pulse
  const next: Step = wantsSession ? "session" : "done"
  useEffect(() => {
    let live = true
    setVote(null); setNote(""); setError(null)
    if (dismissed.has(key)) { setStep("done"); return }
    setStep("loading")
    getMyVote(lane, refId, view)
      .then(v => { if (live) { setVote(v.vote); setStep(v.vote ? "voted" : "vote") } })
      .catch(() => { if (live) setStep("vote") })  // an earlier vote is a convenience; voting reports its own errors
    return () => { live = false }
  }, [lane, refId, view, key])
  const step_ = step === "voted" ? next : step

  const close = () => { dismissed.add(key); setStep("done") }
  const finish = (s: Step) => { setNote(""); if (s === "done") dismissed.add(key); setStep(s) }
  const sendAnswerVote = async (v: Vote, text = "") => {
    setBusy(true); setError(null)
    try {
      const r = await sendVote({ lane, ref: refId, view, vote: v, comment: text.trim() || undefined })
      setVote(r.vote)
      if (text.trim()) { toast.success("Thanks for the note."); finish(next) } else setStep("vote-note")
    }
    catch (e) { setError(message(e)) }
    finally { setBusy(false) }
  }
  const sendRating = async (rating: Rating, text = "") => {
    setBusy(true); setError(null)
    try {
      f.setPulse(await sendPulse({ rating, comment: text.trim() || undefined, where: f.where, ref: refId }))
      if (text.trim()) { toast.success("Thanks for the note."); finish("done") } else setStep("session-note")
    }
    catch (e) { setError(message(e)) }
    finally { setBusy(false) }
  }
  const shown = step_ !== "loading" && step_ !== "done"
  const { trackInline } = f
  // One vote prompt at a time: while a follow-up answer shows its own card, the page's card steps aside, and it comes back
  // (if the page was not voted on) once the follow-up's card is answered or closed. The newest question gets the prompt.
  useEffect(() => {
    if (!inline || !shown) return
    trackInline(1)
    return () => trackInline(-1)
  }, [inline, shown, trackInline])
  if (!shown || (!inline && f.inlineShown > 0)) return null

  const rating = f.status?.pulse?.rating ?? null
  const row = "flex flex-wrap items-center justify-between gap-x-4 gap-y-2"
  const closeBtn = <button type="button" onClick={close} aria-label="Close feedback" title="Not now" className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-paper hover:text-ink"><Icon name="close" className="h-4 w-4"/></button>
  const noteStep = (label: string, onSend: () => void, skip: Step) => <div className="space-y-2">
    <div className={row}><label htmlFor={`fb-note-${key}`} className="text-sm text-ink">{label} <span className="text-muted">(optional)</span></label>{closeBtn}</div>
    <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
      <textarea id={`fb-note-${key}`} autoFocus value={note} onChange={e => setNote(e.target.value)} maxLength={step_ === "vote-note" ? 500 : 300} rows={1}
        placeholder="No names, please" className={`${FIELD} flex-1 resize-y`} />
      <div className="flex shrink-0 gap-2">
        <button type="button" disabled={busy || !note.trim()} onClick={onSend} className={BTN2}>Send</button>
        <button type="button" disabled={busy} onClick={() => finish(skip)} className="rounded-lg px-3 py-2 text-sm text-muted hover:text-ink">{skip === "done" ? "Done" : "Next"}</button>
      </div>
    </div>
  </div>

  const body = <div role="region" aria-label="Feedback on this answer" className={`pa-rise rounded-xl border border-rule bg-sheet px-4 py-3 ${inline ? "" : "shadow-[0_10px_30px_rgba(0,0,0,0.45)]"}`}>
    {step_ === "vote" && <div className={row}>
      <span className="text-sm text-ink">Was this answer right?</span>
      <div className="flex items-center gap-2">
        <div role="group" aria-label="Rate this answer" className="flex items-center gap-2">
          <button type="button" aria-label="Thumbs up" title="Right" disabled={busy} onClick={() => void sendAnswerVote("up")} className={THUMB_BTN}><Thumb /></button>
          <button type="button" aria-label="Thumbs down" title="Something is wrong" disabled={busy} onClick={() => void sendAnswerVote("down")} className={THUMB_BTN}><Thumb down /></button>
        </div>
        {closeBtn}
      </div>
    </div>}
    {step_ === "vote-note" && noteStep(vote === "down" ? "Thanks. What was wrong?" : "Thanks. What worked?", () => void sendAnswerVote(vote ?? "up", note), next)}
    {step_ === "session" && <div className={row}>
      <span className="text-sm text-ink">How is the agent team working for you this session?</span>
      <div className="flex items-center gap-2">
        <div role="group" aria-label="Session rating" className="flex gap-1.5">
          {RATINGS.map(r => <button key={r} type="button" disabled={busy} onClick={() => void sendRating(r)} className={CHOICE}>
            <Face kind={r} className={`h-4 w-4 ${TONE[r]}`} />{LABEL[r]}</button>)}
        </div>
        {closeBtn}
      </div>
    </div>}
    {step_ === "session-note" && rating && noteStep(rating === "good" ? "Thanks. What is working?" : "Thanks. What happened?", () => void sendRating(rating, note), "done")}
    {error && <p role="alert" className="mt-2 text-xs text-neg">{error}</p>}
  </div>
  if (inline) return body
  if (slot) return createPortal(<div className="pb-2">{body}</div>, slot)
  return <div className="pa-noprint sticky bottom-4 z-20">{body}</div>
}

// --- a suggestion for the platform (FR-018) ---------------------------------------------------------

const TOPICS: [CommentTopic, string][] = [["briefing", "Weekly briefing"], ["forecast", "Forecast explanation"], ["agent", "The agent team"], ["design", "Look and feel"], ["other", "Something else"]]

function SuggestModal({ onClose, onSurvey, surveyDone }: { onClose: () => void; onSurvey: () => void; surveyDone: boolean }) {
  const [text, setText] = useState("")
  const [topic, setTopic] = useState<CommentTopic>("other")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    document.addEventListener("keydown", esc)
    return () => document.removeEventListener("keydown", esc)
  }, [onClose])
  const send = async () => {
    setBusy(true); setError(null)
    try { await sendComment(text.trim(), topic); toast.success("Thank you. Your suggestion is saved."); onClose() }
    catch (e) { setError(message(e)) }
    finally { setBusy(false) }
  }
  return <div className="pa-fade fixed inset-0 z-50 grid place-items-center overscroll-contain bg-black/60 px-4">
    <div role="dialog" aria-modal="true" aria-labelledby="suggest-title" className="pa-rise pa-panel w-full max-w-lg rounded-xl border border-rule bg-sheet">
      <div className="flex items-start justify-between gap-3 border-b border-rule px-6 py-4">
        <div><h2 id="suggest-title" className="text-lg">Suggest an improvement</h2><p className="mt-1 text-sm text-muted">What should we work on next? Anything goes, big or small.</p></div>
        <button type="button" onClick={onClose} aria-label="Close" className={CLOSE}><Icon name="close" className="h-5 w-5"/></button>
      </div>
      <div className="space-y-4 px-6 py-5">
        <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">About
          <select value={topic} onChange={e => setTopic(e.target.value as CommentTopic)} className={FIELD}>{TOPICS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-muted">Your suggestion
          <textarea autoFocus value={text} onChange={e => setText(e.target.value)} maxLength={1000} rows={4} placeholder="No names or personal details, please" className={FIELD} />
        </label>
        {error && <p role="alert" className="text-xs text-neg">{error}</p>}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-rule px-6 py-3">
        <button type="button" onClick={onSurvey} className="text-xs text-primaryink underline underline-offset-4 hover:no-underline">{surveyDone ? "Update your questionnaire answers" : "Or take the one-minute questionnaire"}</button>
        <button type="button" disabled={busy || !text.trim()} onClick={() => void send()} className={BTN}>{busy ? "Sending…" : "Send"}</button>
      </div>
    </div>
  </div>
}

// --- the questionnaire ----------------------------------------------------------------------------

function Question({ item, scale, value, onChange }: { item: QItem; scale: string[]; value: unknown; onChange: (v: number | string | string[] | undefined) => void }) {
  const legend = <legend className="text-sm font-medium leading-snug">{item.text}</legend>
  const chip = (on: boolean) => `rounded-lg border px-2 py-2.5 text-xs font-medium transition-colors ${on ? "border-primary bg-primary text-onprimary" : "border-edge text-ink hover:bg-paper"}`
  if (item.type === "agree5") return <fieldset className="space-y-2">{legend}
    <div role="radiogroup" aria-label={item.text} className="grid grid-cols-5 gap-1.5">
      {[1, 2, 3, 4, 5].map(n => <button key={n} type="button" role="radio" aria-checked={value === n} title={scale[n - 1]} onClick={() => onChange(value === n ? undefined : n)} className={chip(value === n)}>{n}</button>)}
    </div>
    <div className="flex justify-between text-[11px] text-muted"><span>{scale[0]}</span><span>{scale[4]}</span></div></fieldset>
  if (item.type === "nps") return <fieldset className="space-y-2">{legend}
    <div role="radiogroup" aria-label={item.text} className="grid grid-cols-6 gap-1.5 sm:grid-cols-11 sm:gap-1">
      {Array.from({ length: 11 }, (_, n) => <button key={n} type="button" role="radio" aria-checked={value === n} onClick={() => onChange(value === n ? undefined : n)} className={chip(value === n)}>{n}</button>)}
    </div>
    <div className="flex justify-between text-[11px] text-muted"><span>{item.low}</span><span>{item.high}</span></div></fieldset>
  if (item.type === "choice") return <fieldset className="space-y-1.5">{legend}
    {item.options?.map(o => <label key={o.value} className="flex items-center gap-2 text-sm"><input type="radio" name={item.id} checked={value === o.value} onChange={() => onChange(o.value)} />{o.label}</label>)}
    {value !== undefined && <button type="button" onClick={() => onChange(undefined)} className="text-[11px] text-muted hover:underline">Clear</button>}</fieldset>
  if (item.type === "multi") {
    const picked = Array.isArray(value) ? value as string[] : []
    return <fieldset className="space-y-1.5">{legend}
      {item.options?.map(o => <label key={o.value} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={picked.includes(o.value)}
        onChange={() => onChange(picked.includes(o.value) ? picked.filter(v => v !== o.value) : [...picked, o.value])} />{o.label}</label>)}</fieldset>
  }
  const text = typeof value === "string" ? value : ""
  return <fieldset className="space-y-1.5">{legend}
    <textarea value={text} maxLength={item.max ?? 1000} rows={3} onChange={e => onChange(e.target.value)} aria-label={item.text} className={FIELD} />
    <div className="text-right text-[11px] text-muted">{text.length}/{item.max ?? 1000}</div></fieldset>
}

const filled = (v: unknown) => v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0)

function SurveyModal({ onClose, onSubmitted }: { onClose: () => void; onSubmitted: () => void }) {
  const [q, setQ] = useState<Questionnaire | null>(null)
  const [answers, setAnswers] = useState<Answers>({})
  const [loadError, setLoadError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [updating, setUpdating] = useState(false)

  const load = useCallback(() => {
    setLoadError(null); setQ(null)
    Promise.all([getQuestionnaire(), getMySurvey()]).then(([quest, mine]) => {
      const ids = new Map(quest.sections.flatMap(s => s.items).map((i): [string, QItem] => [i.id, i]))
      const prefill: Answers = {}   // earlier answers to questions that still exist, so an update starts from them
      for (const [id, v] of Object.entries(mine.answers)) {
        const item = ids.get(id)
        if (item && (typeof v === "number" || typeof v === "string" || Array.isArray(v))) prefill[id] = v as number | string | string[]
      }
      setQ(quest); setAnswers(prefill); setUpdating(Boolean(mine.submitted_at))
    }).catch(e => setLoadError(message(e)))
  }, [])
  useEffect(load, [load])
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    document.addEventListener("keydown", esc)
    return () => document.removeEventListener("keydown", esc)
  }, [onClose])

  const set = (id: string, v: number | string | string[] | undefined) => setAnswers(a => { const n = { ...a }; if (filled(v)) n[id] = v as number | string | string[]; else delete n[id]; return n })
  const count = Object.values(answers).filter(filled).length
  const total = q ? q.sections.reduce((n, s) => n + s.items.length, 0) : 0
  const submit = async () => {
    if (!q) return
    setBusy(true); setError(null)
    try { await sendSurvey(q.version, answers); setDone(true); onSubmitted(); toast.success("Questionnaire saved. Thank you.") }
    catch (e) { setError(message(e)) }
    finally { setBusy(false) }
  }

  return <div className="fixed inset-0 z-50 flex justify-center overflow-y-auto overscroll-contain bg-black/60 px-3 py-6">
    <div role="dialog" aria-modal="true" aria-labelledby="survey-title" className="pa-panel pa-rise h-fit w-full max-w-2xl rounded-xl border border-rule bg-sheet">
      <div className="flex items-start justify-between gap-3 border-b border-rule px-6 py-4">
        <div><h2 id="survey-title" className="text-lg font-semibold">{q?.title ?? "Platform questionnaire"}</h2>{q && <p className="mt-1 text-sm text-muted">{q.intro}</p>}</div>
        <button type="button" onClick={onClose} aria-label="Close questionnaire" className={CLOSE}><Icon name="close" className="h-5 w-5"/></button>
      </div>
      {loadError && <Notice tone="error" role="alert" className="m-6">{loadError}<button type="button" onClick={load} className="mt-2 block underline">Try again</button></Notice>}
      {!q && !loadError && <p role="status" className="px-6 py-8 text-sm text-muted">Loading the questionnaire…</p>}
      {q && done && <div className="px-6 py-10 text-center"><p className="text-lg font-semibold">Thank you.</p>
        <p className="mt-1 text-sm text-muted">Your answers are saved. You can reopen the questionnaire from the sidebar or your account menu to change them.</p>
        <button type="button" onClick={onClose} className={`${BTN} mt-5`}>Close</button></div>}
      {q && !done && <>
        <div className="space-y-7 px-6 py-5">
          {updating && <p className="rounded-lg border border-rule bg-paper px-3 py-2 text-xs text-ink">You answered this before. Your earlier answers are filled in; change anything and send again to replace them.</p>}
          {q.sections.map(section => <section key={section.id} className="space-y-5">
            <h3 className="border-b border-rule pb-1.5 font-sans text-xs font-semibold uppercase tracking-[0.05em] text-muted">{section.title}</h3>
            {section.items.map(item => <Question key={item.id} item={item} scale={q.scale.agree5} value={answers[item.id]} onChange={v => set(item.id, v)} />)}
          </section>)}
        </div>
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 rounded-b-xl border-t border-rule bg-sheet px-6 py-3">
          <span className="text-xs text-muted">{count} of {total} answered. Every question is optional.</span>
          <span className="flex items-center gap-3">
            {error && <span role="alert" className="max-w-[18rem] text-xs text-neg">{error}{error.includes("changed") && <button type="button" onClick={load} className="ml-1 underline">Reload</button>}</span>}
            <button type="button" disabled={busy || count === 0} onClick={() => void submit()} className={BTN}>{busy ? "Sending…" : updating ? "Send updated answers" : "Send"}</button>
          </span>
        </div>
      </>}
    </div>
  </div>
}
