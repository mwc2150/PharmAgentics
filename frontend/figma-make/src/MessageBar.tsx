// brief-006: the message bar docked under the brief column (analysts only; leaders never get it).
// On the New briefing form it is the one question box: the text is read and fills the form (onRead), and never
// starts a brief. While a brief is written it holds the message; on a brief it asks a follow-up in the analyst's
// own thread. Answers come from the server only. The suggested questions are scripted and free; free text goes to the
// agent when the app has a model (it counts toward the thread's 20) and is disabled, with the reason, when it has none.
import { useEffect, useRef, useState } from "react"
import { AnswerFeedback } from "./Feedback"
import { Icon, Notice } from "./agent/primitives"
import { askThread, continueShared, getThread, openShared, saveThread, shareLink, sharedFromLocation, type Thread, type Turn } from "./agent/threadApi"

export type Chip = { number: string; title: string }

function message(e: unknown): string { return e instanceof Error ? e.message : String(e) }

// `latest`: only the newest answer asks "Was this answer right?", so the thread shows one vote prompt at a time (brief-015 I5).
function TurnView({turn, briefId, mine, latest, onCite, onOpenEvidence, onOfferScope}: {turn: Turn, briefId: string, mine: boolean, latest: boolean,
    onCite: (n: string) => void, onOpenEvidence: (id: string) => void, onOfferScope?: (o: NonNullable<Turn["offer"]>) => void}) {
  const offer = turn.offer
  return <li className="space-y-2">
    <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-primarybg px-4 py-2 text-sm text-ink">
      {turn.section && <span className="mr-2 rounded bg-sheet px-1.5 py-0.5 font-mono text-[11px] text-primaryink">§{turn.section}</span>}{turn.question}</p>
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-rule bg-sheet px-4 py-3 text-sm">
      <p className="whitespace-pre-wrap break-words font-sans text-[15px] leading-relaxed text-ink">{turn.answer}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
        {turn.cited.map(n => <button key={n} type="button" onClick={() => onCite(n)} className="rounded bg-paper px-1.5 py-0.5 font-mono text-primaryink hover:underline" title={`Go to §${n}`} aria-label={`Go to section ${n}`}>§{n}</button>)}
        {turn.claims.map((c, i) => <button key={i} type="button" onClick={() => onOpenEvidence(c.evidence_id)} className="rounded bg-paper px-1.5 py-0.5 font-mono text-muted hover:text-ink" title={`Open the query behind ${c.value}`} aria-label={`${c.value}, open the query behind it`}>{c.value}</button>)}
        <span className="ml-auto text-muted">{turn.engine === "scripted" ? "Scripted, from this brief only" : "Agent"}</span>
      </div>
      {offer && offer.week && onOfferScope && <button type="button" onClick={() => onOfferScope(offer)} className="mt-2 text-xs font-medium text-primaryink hover:underline">
        {offer.choose_comparison ? "Set up a brief with a new comparison" : <>Generate a brief for {offer.brand} · {(offer.territory ?? "").replace(/_/g, " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase())} · week of {offer.week}</>}</button>}
    </div>
    {mine && latest && <AnswerFeedback inline lane="briefing" refId={`${briefId}:t${turn.n}`} view="analyst" agent={turn.n === 3}/>}
  </li>
}

export function MessageBar({briefId, pending, chip, onClearChip, onRead, readBusy = false, readError = null, onOfferScope, onOpenEvidence}: {
  briefId: string | null
  pending: boolean
  chip: Chip | null
  onClearChip: () => void
  onRead?: (question: string) => Promise<boolean>  // on the form: reads the question into it; true when it filled the form
  readBusy?: boolean
  readError?: string | null
  onOfferScope?: (o: NonNullable<Turn["offer"]>) => void
  onOpenEvidence: (evidenceId: string) => void
}) {
  const [thread, setThread] = useState<Thread | null>(null)
  const [text, setText] = useState("")
  const [queued, setQueued] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [working, setWorking] = useState("Asking…")
  const input = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    setThread(null); setError(null)
    if (!briefId) return
    const shared = sharedFromLocation()
    const load = shared && shared.briefId === briefId ? openShared(briefId, shared.owner) : getThread(briefId)
    load.then(t => { setThread(t); if (t.turns.length) setOpen(true) }).catch(e => setError(message(e)))
  }, [briefId])
  useEffect(() => { if (chip) input.current?.focus() }, [chip])

  const ask = async (q: string) => {
    if (!briefId) return
    setBusy(true); setError(null)
    setWorking(Object.values(thread?.suggestions ?? {}).flat().includes(q) ? "Asking…" : "Agent working…")
    try { setThread(await askThread(briefId, q, chip?.number)); setOpen(true); setText(""); onClearChip() }
    catch (e) { setError(message(e)) }  // the draft stays in the bar
    finally { setBusy(false) }
  }
  useEffect(() => {  // a message typed while the brief was being written is sent once it is ready
    if (queued && briefId && !pending && thread && thread.mine) { const q = queued; setQueued(null); void ask(q) }
  }, [queued, briefId, pending, thread])  // eslint-disable-line react-hooks/exhaustive-deps

  const send = (q: string) => {
    const question = q.trim()
    if (!question || busy) return
    if (!briefId && onRead) { void onRead(question).then(ok => { if (ok) setText("") }); return }  // a failed read keeps the draft
    if (pending) { setQueued(question); setText(""); return }
    if (!briefId) { setError("The brief is not ready yet. Ask once it is written."); return }
    void ask(question)
  }
  const cite = (n: string) => document.getElementById(`memo-${briefId}-${n}`)?.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"})
  const tips = !briefId ? [] : (thread?.suggestions[chip?.number ?? "1"] ?? []).slice(0, 3)
  const readOnly = thread && !thread.mine
  const full = thread ? thread.used_turns >= thread.max_turns : false  // free-text turns only; the chips never fill it
  const noFreeText = !!briefId && !!thread && thread.mine && !thread.free_text
  const typingOff = noFreeText || full
  const reason = noFreeText ? thread?.free_text_reason ?? null : null
  const form = !briefId && !!onRead  // the New briefing form
  const shownError = error ?? readError

  return <div className="pa-bars sticky bottom-0 z-20 -mx-2 mt-8 bg-gradient-to-t from-paper via-paper to-paper/0 px-2 pb-3 pt-6" role="region" aria-label={form ? "Ask a question" : "Follow-up questions"}>
    {thread && thread.turns.length > 0 && <div className="mb-2 rounded-2xl border border-rule bg-paper/95 shadow-2xl backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule px-4 py-2 text-xs text-muted">
        <span>{readOnly ? "Shared thread, read-only" : `Free-text follow-ups, ${thread.used_turns} of ${thread.max_turns}`}{thread.shared_from ? " · continued from a shared thread" : ""}</span>
        <span className="flex items-center gap-3">
          {readOnly && <button type="button" className="font-medium text-primaryink hover:underline" onClick={() => briefId && continueShared(briefId, thread.owner).then(t => { setThread(t); window.location.hash = "" }).catch(e => setError(message(e)))}>Continue in my thread</button>}
          {!readOnly && !thread.saved && <button type="button" className="font-medium text-primaryink hover:underline" onClick={() => briefId && saveThread(briefId).then(setThread).catch(e => setError(message(e)))}>Save thread</button>}
          {!readOnly && thread.saved && <button type="button" className="font-medium text-primaryink hover:underline" onClick={() => { void navigator.clipboard?.writeText(shareLink(thread)); setCopied(true); setTimeout(() => setCopied(false), 1500) }}>{copied ? "Link copied" : "Copy share link"}</button>}
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex items-center gap-1 text-primaryink hover:underline"><Icon name="chevronRight" className={`h-3.5 w-3.5 transition-transform duration-200 ${open ? "rotate-90" : ""}`}/>{open ? "Collapse" : "Show"}</button>
        </span>
      </div>
      {open && <ol aria-live="polite" aria-relevant="additions" className="max-h-[50vh] space-y-4 overflow-y-auto px-4 py-4">
        {thread.turns.map(t => <TurnView key={t.n} turn={t} briefId={thread.brief_id} mine={!readOnly} latest={t === thread.turns[thread.turns.length - 1]} onCite={cite} onOpenEvidence={onOpenEvidence} onOfferScope={onOfferScope}/>)}
      </ol>}
    </div>}
    {tips.length > 0 && !readOnly && <div className="mb-2 flex flex-wrap gap-2">
      {tips.map(t => <button key={t} type="button" disabled={busy} onClick={() => send(t)} className="rounded-full border border-rule bg-sheet px-3 py-1 text-xs text-ink hover:border-primary/50 disabled:opacity-40">{t}</button>)}
    </div>}
    {shownError && <Notice tone="error" role="alert" className="mb-2 px-3 py-2 text-xs">{shownError}</Notice>}
    {queued && <p role="status" className="mb-2 text-xs text-muted">Will ask when the brief is ready: “{queued}”</p>}
    {!readOnly && <form onSubmit={e => { e.preventDefault(); send(text) }} className="flex items-end gap-2 rounded-2xl border border-edge bg-sheet px-3 py-2 has-[textarea:focus-visible]:outline-2 has-[textarea:focus-visible]:outline-offset-2 has-[textarea:focus-visible]:outline-primary">
      {chip && <span className="mb-1 inline-flex shrink-0 items-center gap-1 rounded bg-primarybg px-2 py-1 font-mono text-[11px] text-primaryink">§{chip.number} {chip.title}
        <button type="button" aria-label="Remove the section" onClick={onClearChip} className="ml-1 text-muted hover:text-ink">×</button></span>}
      <label htmlFor="pa-message" className="sr-only">{form ? "Ask a question to fill the form" : "Ask about this brief"}</label>
      <textarea id="pa-message" ref={input} rows={1} value={text} maxLength={500} disabled={busy || typingOff} aria-describedby={reason ? "pa-message-why" : undefined} readOnly={readBusy}
        onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text) } }}
        placeholder={noFreeText ? "Pick a suggested question" : full ? "Free-text questions are used up. Pick a suggested question or start a new brief." : briefId ? (chip ? `Ask about §${chip.number}…` : "Ask a follow-up about this brief…") : "Ask a question, and the form fills in from it…"}
        className="max-h-32 min-h-[2.25rem] flex-1 resize-none bg-transparent py-1.5 text-sm text-ink placeholder:text-muted focus-visible:outline-none"/>
      <button type="submit" disabled={busy || readBusy || typingOff || !text.trim()} className="rounded-xl bg-primary px-3 py-1.5 text-sm font-medium text-onprimary hover:bg-primaryhover disabled:opacity-40">{readBusy ? "Reading…" : busy ? working : form ? "Read" : "Send"}</button>
    </form>}
    {reason && !readOnly && <p id="pa-message-why" className="mt-1.5 px-1 text-xs text-muted">{reason}</p>}
    {form && !readOnly && <p className="mt-1.5 px-1 text-xs text-muted">Fills the weeks, territory, comparison and the other choices. You check them, then generate.</p>}
  </div>
}
