import { useEffect, useRef, type RefObject } from "react"

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
  user:"M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20a7.5 7.5 0 0 1 15 0",
  help:"M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 .9-1 1.7M12 17h.01",
  clipboard:"M8 4h8v3H8zM8 5.5H6a1 1 0 0 0-1 1V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V6.5a1 1 0 0 0-1-1h-2M9 12h6M9 16h6",
  briefcase:"M4 7h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1zM9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 13h18"
} as const
export type IconName = keyof typeof PATHS
export function Icon({name,className="h-4 w-4"}:{name:IconName,className?:string}) {
  return <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={PATHS[name]}/></svg>
}

/* The "Pa" mark (public/pa-mark.svg): styled like a periodic-table tile, with the version "v1" where an element's
   number would sit. Space Grotesk outlines on teal with the teal-button shadow; it scales to any size.
   public/favicon.svg drops the version for 16px. */
const MARK={sm:"h-9 w-9",lg:"h-14 w-14"} as const
export function BrandMark({size="sm"}:{size?:keyof typeof MARK}){
  return <img src="/pa-mark.svg" alt="" width={64} height={64} draggable={false} className={`shrink-0 select-none ${MARK[size]}`}/>
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
