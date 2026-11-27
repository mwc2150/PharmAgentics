import { useEffect, useRef, type CSSProperties, type HTMLAttributes, type ReactNode, type RefObject } from "react"
import { useDrawOnView } from "../motion"
import { fmtDate, getSettings } from "../userSettings"

/* Visual identity and SVG icon geometry. One icon set, outline style, stroke 1.6 next to 14px text.
   Always pass a size class (h-4 w-4, h-5 w-5): a className without one lets the SVG grow to fill its row. */
const PATHS={
  send:"M5 12h14M13 6l6 6-6 6",
  evidence:"M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  close:"M6 6l12 12M18 6L6 18",
  back:"M15 18l-6-6 6-6",
  menu:"M4 7h16M4 12h16M4 17h16",
  chevronRight:"M9 6l6 6-6 6",
  check:"M5 12.5l4.5 4.5L19 7.5",
  panel:"M4 5h16v14H4zM9.5 5v14",
  trend:"M4 17l5-5 4 3 7-8M15 7h5v5",
  grid:"M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  shield:"M12 3.5l7 2.8v5.2c0 4.2-2.9 7.7-7 9-4.1-1.3-7-4.8-7-9V6.3z",
  user:"M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20a7.5 7.5 0 0 1 15 0",
  info:"M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5.5M12 7.5h.01",
  help:"M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01",
  clipboard:"M8 4h8v3H8zM8 5.5H6a1 1 0 0 0-1 1V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6.5a1 1 0 0 0-1-1h-2M9 12h6M9 16h6",
  briefcase:"M4 7h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1zM9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 13h18",
  warning:"M12 4L2.8 19.5a1 1 0 0 0 .9 1.5h16.6a1 1 0 0 0 .9-1.5zM12 10v4.5M12 17.5h.01",
  alert:"M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7.5v5M12 16h.01",
  gear:"M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
} as const
export type IconName = keyof typeof PATHS
/* A headline number that rolls in like a combination lock (index.css .pa-roll, Michael 2026-11-27): each digit is a
   wheel that spins, blurred, through the digits and clicks to its value, each wheel at its own speed; commas, points and
   signs stand still. It always lands on the real figure, about a second in. Screen readers and copying get the number
   whole; with reduced motion the wheels start where they stop. Key it by its text where it is used, so a new value
   spins again. `delay` (ms) staggers several numbers. */
/* A block whose padlock numbers (RollIn) wait to spin until it first scrolls into view, the way a chart waits to draw:
   a table further down the page spins when it is reached, not unseen at load. */
export function InView({as: Tag = "div", children, ...rest}: {as?: "div" | "section", children: ReactNode} & HTMLAttributes<HTMLElement>) {
  const ref = useDrawOnView<HTMLElement>(0.05)
  return <Tag ref={ref as RefObject<HTMLDivElement>} {...rest}>{children}</Tag>
}

export function RollIn({text, delay = 0}: {text: string, delay?: number}) {
  let seed = text.length * 7 + 3
  return <><span className="pa-roll" aria-hidden="true">{[...text].map((c, i) => {
    if (!/[0-9]/.test(c)) return <span key={i} className="pa-reel"><span className="pa-reel-strip"><span>{c}</span></span></span>
    seed = (seed * 31 + c.charCodeAt(0) * 7 + i * 13) % 997
    const laps = 1 + (seed % 2), to = laps * 10 + Number(c)   // the wheel passes 0-9 once or twice, then stops on the digit
    const style = {"--from": seed % 10, "--to": to, "--dur": `${720 + (seed % 5) * 110}ms`, "--d": `${delay + i * 35}ms`} as CSSProperties
    return <span key={i} className="pa-reel"><span className="pa-reel-strip" style={style}>
      {Array.from({length: to + 1}, (_, k) => <span key={k}>{k % 10}</span>)}</span></span>
  })}</span><span className="sr-only">{text}</span></>
}

/* A person's initial in a circle (the account button, Michael 2026-11-27). `rank` picks the fill (index.css --pa-rank-N,
   a rainbow by seniority); the name always sits beside it, so the colour only helps. */
export function Avatar({name, rank, size = "sm"}: {name: string, rank: number, size?: "sm" | "md"}) {
  const initial = (name.trim()[0] ?? "?").toLocaleUpperCase()
  return <span aria-hidden="true" style={{background: `var(--pa-rank-${rank})`, color: "var(--pa-onrank)"}}
    className={`grid shrink-0 select-none place-items-center rounded-full font-display font-bold leading-none ${size === "md" ? "h-9 w-9 text-base" : "h-7 w-7 text-[13px]"}`}>{initial}</span>
}

export function Icon({name,className="h-4 w-4"}:{name:IconName,className?:string}) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={PATHS[name]}/></svg>
}

/* A warning or an error: a hairline border, a leading icon and a toned title; never a tinted fill or a side bar.
   The words carry the meaning, the tone only helps. Keep role="alert" for a failure the person must hear about. */
export function Notice({tone,title,children,role,className="",action}:{tone:"warn"|"error",title?:ReactNode,children?:ReactNode,role?:"alert"|"status",className?:string,action?:ReactNode}){
  const warn=tone==="warn"
  // a caller's own padding or text size replaces the default, so the two never fight over CSS order
  const pad=/(^|\s)p[xy]?-/.test(className)?"":"px-4 py-3", size=/(^|\s)text-(xs|sm)(\s|$)/.test(className)?"":"text-sm"
  return <div role={role} className={`flex gap-3 rounded-xl border bg-sheet ${pad} ${size} ${warn?"border-amberline":"border-negline"} ${className}`}>
    <Icon name={warn?"warning":"alert"} className={`mt-0.5 h-4 w-4 shrink-0 ${warn?"text-amber":"text-neg"}`}/>
    <div className="min-w-0 flex-1 text-ink">{title&&<p className={`font-semibold ${warn?"text-amber":"text-neg"}`}>{title}</p>}{children}</div>
    {action}
  </div>
}

/* The "Pa" mark (public/pa-mark.svg): a 3D-printed tile, a flat face with a thick edge showing 6 px below and 3 px to
   the right, "Pa" in Space Grotesk outlines on it. It is drawn inline so it follows the app's theme through three
   variables (index.css): dark has a seafoam face with a teal edge, light swaps the two. public/favicon.svg carries the
   same two colourways behind a prefers-color-scheme query, since a tab icon cannot follow the in-app setting. */
const MARK={sm:"h-9 w-9",lg:"h-14 w-14"} as const
const PA_GLYPHS=[
  ["9.60",'M66 0V700H354Q420 700 470.5 673.5Q521 647 549.5 599.0Q578 551 578 485V471Q578 406 548.5 357.5Q519 309 468.5 282.5Q418 256 354 256H198V0ZM198 376H341Q388 376 417.0 402.0Q446 428 446 473V483Q446 528 417.0 554.0Q388 580 341 580H198Z'],
  ["31.29",'M224 -14Q171 -14 129.0 4.5Q87 23 62.5 58.5Q38 94 38 145Q38 196 62.5 230.5Q87 265 130.5 282.5Q174 300 230 300H366V328Q366 363 344.0 385.5Q322 408 274 408Q227 408 204.0 386.5Q181 365 174 331L58 370Q70 408 96.5 439.5Q123 471 167.5 490.5Q212 510 276 510Q374 510 431.0 461.0Q488 412 488 319V134Q488 104 516 104H556V0H472Q435 0 411.0 18.0Q387 36 387 66V67H368Q364 55 350.0 35.5Q336 16 306.0 1.0Q276 -14 224 -14ZM246 88Q299 88 332.5 117.5Q366 147 366 196V206H239Q204 206 184.0 191.0Q164 176 164 149Q164 122 185.0 105.0Q206 88 246 88Z'],
] as const
export function BrandMark({size="sm"}:{size?:keyof typeof MARK}){
  return <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false" className={`pa-logo shrink-0 select-none ${MARK[size]}`}>
    <rect x="3" y="6" width="61" height="58" rx="10" fill="var(--pa-mark-edge)"/>
    <rect x="0" y="0" width="61" height="58" rx="10" fill="var(--pa-mark-face)"/>
    <g fill="var(--pa-mark-ink)">{PA_GLYPHS.map(([x,d])=><path key={x} transform={`translate(${x} 42.00) scale(0.03714 -0.03714)`} d={d}/>)}</g>
  </svg>
}

/* A modal drawer or dialog: on open, focus moves inside; Tab and Shift+Tab wrap within it; Escape closes it; on close,
   focus returns to the control that opened it (WCAG 2.4.3, 2.1.2). Call it from the component that renders the
   drawer, with a ref to the drawer's root element (give that element tabIndex={-1} so it can take focus if it holds
   nothing focusable). `onClose` may change between renders. */
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])'
export function useModalFocus(root: RefObject<HTMLElement | null>, onClose: () => void) {
  const close = useRef(onClose)
  close.current = onClose
  useEffect(() => {
    const el = root.current
    if (!el) return
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const items = () => Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(n => n.getClientRects().length > 0)
    ;(items()[0] ?? el).focus()
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.stopPropagation(); close.current(); return }
      if (e.key !== "Tab") return
      if (!el.getClientRects().length) return  // hidden by a breakpoint (the phone drawer on a wide window): leave Tab alone
      const list = items()
      if (!list.length) { e.preventDefault(); el.focus(); return }
      const first = list[0], last = list[list.length - 1], at = document.activeElement
      if (!el.contains(at)) { e.preventDefault(); (e.shiftKey ? last : first).focus() }
      else if (e.shiftKey && at === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && at === last) { e.preventDefault(); first.focus() }
    }
    document.addEventListener("keydown", key)
    return () => { document.removeEventListener("keydown", key); if (opener?.isConnected) opener.focus() }
  }, [root])
}

// A model id in plain words ("ollama:qwen3:4b-instruct-2507-q4_K_M" -> "Qwen 3 4B", "anthropic:claude-haiku-5-5" ->
// "Haiku"). Raw ids are plumbing: the UI never prints one.
export function modelName(model: string | null | undefined): string {
  if (!model) return ""
  const provider = /^(ollama|anthropic|gemini):/.exec(model.toLowerCase())?.[1]
  const m = model.toLowerCase().replace(/^(ollama|anthropic|gemini):/, "")
  if (m.startsWith("claude")) return m.includes("haiku") ? "Haiku" : m.includes("sonnet") ? "Sonnet" : m.includes("opus") ? "Opus" : "Claude"
  if (m.startsWith("gemini") || (provider === "gemini")) return "Gemini"
  if (!m) return provider === "anthropic" ? "Claude" : ""
  const local = /^(qwen|gemma|llama)(\d+(?:\.\d+)?):(\d+(?:\.\d+)?b)/.exec(m)
  if (local) return `${local[1][0].toUpperCase()}${local[1].slice(1)} ${local[2]} ${local[3].toUpperCase()}`
  return m === "none" ? "" : model
}
const MODEL_ID = /(?:(?:ollama|anthropic|gemini):)?(?:claude-[\w.-]+|(?:qwen|gemma|llama)\d+(?:\.\d+)?:[\w.-]+|gemini-[\w.-]+)/gi
/** Free text (a step or actor name from the server) with any model id in it made readable. */
export function plainModels(text: string): string {
  return text.replace(MODEL_ID, id => modelName(id))
}

/** A date as the app prints it everywhere ("Nov 23, 2026"); a bare ISO date is read as local midnight. */
export const when = fmtDate


const ISO_DATE = /(?<![\d-])(\d{4})-(\d{2})-(\d{2})(?![\d-])/g
/** Display only: ISO dates in prose ("2026-10-05") in the long form the headers use ("Oct 5, 2026"). The server's text
 *  keeps ISO dates (it is scored); call this on the pieces between claim tokens, never on a claim's own value. */
export function longDates(text: string): string {
  if (getSettings().dateStyle === "iso") return text  // the reader chose the ISO style: the server's own dates stand
  return text.replace(ISO_DATE, (all, y, m, d) => {
    const at = new Date(Date.UTC(+y, +m - 1, +d))
    if (Number.isNaN(at.getTime()) || at.getUTCMonth() !== +m - 1 || at.getUTCDate() !== +d) return all
    return at.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })
  })
}

/** A number for reading: whole numbers as they are, others to 4 significant figures. The raw value belongs in a title. */
export function plainValue(v: unknown): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return v === null || v === undefined ? "–" : typeof v === "string" ? v : JSON.stringify(v)
  return Number.isInteger(v) ? v.toLocaleString("en-US") : v.toLocaleString("en-US", { maximumSignificantDigits: 4 })
}
